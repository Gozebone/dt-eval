```python
import pychrono as chrono
import pychrono.irrlicht as chronoirr
import numpy as np
import math
import time
from datetime import datetime, timedelta
import json
import sqlite3
import threading
import queue

# Database setup
def init_database():
    conn = sqlite3.connect('digital_twin.db')
    cursor = conn.cursor()
    
    # Create tables matching the schema
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS machine_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            machine_name TEXT,
            status TEXT,
            power_kw REAL,
            process_time_s INTEGER
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS buffer_levels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            buffer_name TEXT,
            level INTEGER
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS throughput_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            parts_processed INTEGER,
            parts_defective INTEGER
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS energy_consumption (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            total_energy_kwh REAL,
            energy_per_part REAL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS availability_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            machine_name TEXT,
            availability_percent REAL
        )
    ''')
    
    conn.commit()
    conn.close()

# Sensor class to collect data
class DigitalTwinSensor:
    def __init__(self, name):
        self.name = name
        self.data_queue = queue.Queue()
        
    def log_data(self, data):
        self.data_queue.put(data)
        
    def get_latest_data(self):
        if not self.data_queue.empty():
            return self.data_queue.queue[-1]
        return None

# Machine class representing each processing station
class ProductionMachine:
    def __init__(self, name, process_time_s, availability, mttr_s, work_power_kw, idle_power_kw):
        self.name = name
        self.process_time_s = process_time_s
        self.availability = availability
        self.mttr_s = mttr_s
        self.work_power_kw = work_power_kw
        self.idle_power_kw = idle_power_kw
        
        # State tracking
        self.is_operational = True
        self.is_processing = False
        self.last_start_time = 0
        self.total_operating_time = 0
        self.total_downtime = 0
        self.total_energy_consumed = 0
        self.parts_processed = 0
        self.parts_defective = 0
        
        # Sensors
        self.machine_sensor = DigitalTwinSensor(f"{name}_status")
        self.energy_sensor = DigitalTwinSensor(f"{name}_energy")
        
    def update_state(self, current_time, dt):
        if self.is_operational and not self.is_processing:
            # Simulate random failure based on availability
            if np.random.random() > self.availability:
                self.is_operational = False
                self.last_start_time = current_time
                self.machine_sensor.log_data({
                    'timestamp': current_time,
                    'machine_name': self.name,
                    'status': 'failure',
                    'power_kw': 0,
                    'process_time_s': 0
                })
                
        elif not self.is_operational and (current_time - self.last_start_time) >= self.mttr_s:
            self.is_operational = True
            self.machine_sensor.log_data({
                'timestamp': current_time,
                'machine_name': self.name,
                'status': 'operational',
                'power_kw': self.idle_power_kw,
                'process_time_s': 0
            })
            
        # Update energy consumption
        if self.is_operational:
            if self.is_processing:
                self.total_energy_consumed += self.work_power_kw * dt / 3600  # Convert to kWh
                self.machine_sensor.log_data({
                    'timestamp': current_time,
                    'machine_name': self.name,
                    'status': 'processing',
                    'power_kw': self.work_power_kw,
                    'process_time_s': self.process_time_s
                })
            else:
                self.total_energy_consumed += self.idle_power_kw * dt / 3600
                self.machine_sensor.log_data({
                    'timestamp': current_time,
                    'machine_name': self.name,
                    'status': 'idle',
                    'power_kw': self.idle_power_kw,
                    'process_time_s': 0
                })
        else:
            self.machine_sensor.log_data({
                'timestamp': current_time,
                'machine_name': self.name,
                'status': 'down',
                'power_kw': 0,
                'process_time_s': 0
            })
            
    def start_processing(self, current_time):
        if self.is_operational:
            self.is_processing = True
            self.last_start_time = current_time
            return True
        return False
        
    def finish_processing(self, current_time):
        if self.is_processing:
            self.is_processing = False
            self.parts_processed += 1
            # Randomly decide if part is defective
            if np.random.random() < 0.02:  # 2% defect rate
                self.parts_defective += 1
            return True
        return False
        
    def get_availability_percentage(self):
        if self.total_operating_time + self.total_downtime == 0:
            return 100.0
        return (self.total_operating_time / (self.total_operating_time + self.total_downtime)) * 100

# Buffer class for storing parts
class Buffer:
    def __init__(self, name, capacity=10):
        self.name = name
        self.capacity = capacity
        self.level = 0
        self.buffer_sensor = DigitalTwinSensor(f"{name}_level")
        
    def add_part(self):
        if self.level < self.capacity:
            self.level += 1
            self.buffer_sensor.log_data({
                'timestamp': time.time(),
                'buffer_name': self.name,
                'level': self.level
            })
            return True
        return False
        
    def remove_part(self):
        if self.level > 0:
            self.level -= 1
            self.buffer_sensor.log_data({
                'timestamp': time.time(),
                'buffer_name': self.name,
                'level': self.level
            })
            return True
        return False

# Main simulation class
class ProductionLineSimulation:
    def __init__(self):
        # Initialize Chrono system
        self.system = chrono.ChSystemNSC()
        self.system.SetGravitationalAcceleration(chrono.ChVectorD(0, 0, 0))
        
        # Simulation parameters
        self.simulation_time = 0
        self.dt = 0.01  # Time step
        self.running = False
        
        # Production line components
        self.machines = {}
        self.buffers = {}
        self.part_generator = None
        self.parts_in_system = []
        self.parts_processed = 0
        self.parts_defective = 0
        self.total_energy_consumed = 0
        self.start_time = time.time()
        
        # Setup machines
        self.setup_machines()
        
        # Setup buffers
        self.setup_buffers()
        
        # Setup part generator
        self.setup_part_generator()
        
        # Initialize database
        init_database()
        
        # Data logging thread
        self.log_thread = threading.Thread(target=self.log_to_database, daemon=True)
        self.log_thread.start()
        
    def setup_machines(self):
        equipment_config = {
            "M1": {"process_time_s": 150, "availability": 0.98, "mttr_s": 600, "work_power_kw": 4.0, "idle_power_kw": 0.4},
            "M2": {"process_time_s": 120, "availability": 0.97, "mttr_s": 900, "work_power_kw": 5.0, "idle_power_kw": 0.5},
            "M3": {"process_time_s": 180, "availability": 0.95, "mttr_s": 1200, "work_power_kw": 6.0, "idle_power_kw": 0.6},
            "M4": {"process_time_s": 120, "availability": 0.97, "mttr_s": 900, "work_power_kw": 5.0, "idle_power_kw": 0.5},
            "M5": {"process_time_s": 150, "availability": 0.98, "mttr_s": 600, "work_power_kw": 4.0, "idle_power_kw": 0.4}
        }
        
        for name, config in equipment_config.items():
            self.machines[name] = ProductionMachine(
                name=name,
                process_time_s=config["process_time_s"],
                availability=config["availability"],
                mttr_s=config["mttr_s"],
                work_power_kw=config["work_power_kw"],
                idle_power_kw=config["idle_power_kw"]
            )
            
    def setup_buffers(self):
        for i in range(5):  # B0 to B4
            name = f"B{i}"
            self.buffers[name] = Buffer(name=name, capacity=10)
            
    def setup_part_generator(self):
        self.part_generator = PartGenerator(self)
        
    def run_simulation(self, duration_seconds=3600):
        self.running = True
        print("Starting simulation...")
        
        # Initialize parts in system
        self.parts_in_system = []
        
        # Start time tracking
        start_time = time.time()
        
        while self.running and (time.time() - start_time) < duration_seconds:
            # Update simulation time
            self.simulation_time = time.time() - start_time
            
            # Update all machines
            for machine in self.machines.values():
                machine.update_state(self.simulation_time, self.dt)
                
            # Process parts through the line
            self.process_parts()
            
            # Generate new parts at intervals
            self.part_generator.generate_parts(self.simulation_time)
            
            # Sleep to control simulation speed
            time.sleep(self.dt)
            
        self.stop_simulation()
        
    def process_parts(self):
        # Simple logic for moving parts through the line
        # In a real implementation, this would be more complex with proper state management
        
        # For now, simulate simple progression through machines
        pass
        
    def stop_simulation(self):
        self.running = False
        print("Simulation stopped.")
        
    def log_to_database(self):
        while self.running:
            try:
                # Log machine statuses
                for machine in self.machines.values():
                    latest_data = machine.machine_sensor.get_latest_data()
                    if latest_data:
                        self.log_machine_status(latest_data)
                        
                    # Log energy consumption
                    latest_energy = machine.energy_sensor.get_latest_data()
                    if latest_energy:
                        self.log_energy_consumption(machine.name, machine.total_energy_consumed)
                        
                # Log buffer levels
                for buffer in self.buffers.values():
                    latest_level = buffer.buffer_sensor.get_latest_data()
                    if latest_level:
                        self.log_buffer_level(latest_level)
                        
                # Log throughput data
                self.log_throughput_data(self.parts_processed, self.parts_defective)
                
                # Log availability data
                for machine_name, machine in self.machines.items():
                    self.log_availability_data(machine_name, machine.get_availability_percentage())
                
                time.sleep(1)  # Log every second
                
            except Exception as e:
                print(f"Error in logging thread: {e}")
                time.sleep(1)
                
    def log_machine_status(self, data):
        conn = sqlite3.connect('digital_twin.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO machine_status (timestamp, machine_name, status, power_kw, process_time_s)
            VALUES (?, ?, ?, ?, ?)
        ''', (datetime.fromtimestamp(data['timestamp']), 
              data['machine_name'], 
              data['status'], 
              data['power_kw'], 
              data['process_time_s']))
        conn.commit()
        conn.close()
        
    def log_buffer_level(self, data):
        conn = sqlite3.connect('digital_twin.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO buffer_levels (timestamp, buffer_name, level)
            VALUES (?, ?, ?)
        ''', (datetime.fromtimestamp(data['timestamp']), 
              data['buffer_name'], 
              data['level']))
        conn.commit()
        conn.close()
        
    def log_throughput_data(self, processed, defective):
        conn = sqlite3.connect('digital_twin.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO throughput_data (timestamp, parts_processed, parts_defective)
            VALUES (?, ?, ?)
        ''', (datetime.now(), processed, defective))
        conn.commit()
        conn.close()
        
    def log_energy_consumption(self, machine_name, total_energy):
        conn = sqlite3.connect('digital_twin.db')
        cursor = conn.cursor()
        # Calculate average energy per part (simple approximation)
        energy_per_part = total_energy / max(1, self.parts_processed)
        cursor.execute('''
            INSERT INTO energy_consumption (timestamp, total_energy_kwh, energy_per_part)
            VALUES (?, ?, ?)
        ''', (datetime.now(), total_energy, energy_per_part))
        conn.commit()
        conn.close()
        
    def log_availability_data(self, machine_name, availability_percent):
        conn = sqlite3.connect('digital_twin.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO availability_data (timestamp, machine_name, availability_percent)
            VALUES (?, ?, ?)
        ''', (datetime.now(), machine_name, availability_percent))
        conn.commit()
        conn.close()

# Part generator class
class PartGenerator:
    def __init__(self,