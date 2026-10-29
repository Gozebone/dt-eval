```python
import pychrono as chrono
import pychrono.irrlicht as chronoirr
import numpy as np
import json
import time
from datetime import datetime, timedelta
import sqlite3
import os

# Define simulation parameters
SIMULATION_TIME = 432000.0  # 5 days in seconds
DT = 0.01  # Time step
GRAVITY = chrono.ChVectorD(0, -9.81, 0)

# Database setup
def setup_database():
    conn = sqlite3.connect('digital_twin.db')
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''CREATE TABLE IF NOT EXISTS tag_map (
        tag_id TEXT PRIMARY KEY,
        machine_id TEXT,
        signal TEXT,
        unit TEXT,
        register TEXT,
        scale REAL
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS machines (
        id TEXT PRIMARY KEY,
        processing_time_s REAL,
        availability_pct REAL,
        mttr_s REAL,
        power_working_kw REAL,
        power_idle_kw REAL
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS buffers (
        id TEXT PRIMARY KEY,
        capacity INTEGER
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS raw_ingest (
        ingested_at TEXT,
        source TEXT,
        payload TEXT
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS ingest_watermark (
        source TEXT PRIMARY KEY,
        max_event_ts TEXT
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS events (
        ts TEXT,
        machine_id TEXT,
        reason_code TEXT,
        duration_s REAL,
        energy_kwh REAL
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS samples (
        ts TEXT,
        machine_id TEXT,
        tag TEXT,
        value REAL
    )''')
    
    # Insert dimension data
    machines_data = [
        ('M1', 60.0, 99.99, 300.0, 3.0, 0.3),
        ('M2', 80.0, 99.0, 600.0, 5.0, 0.5),
        ('M3', 70.0, 99.0, 600.0, 4.5, 0.45),
        ('M4', 75.0, 99.99, 300.0, 4.0, 0.4)
    ]
    
    buffers_data = [
        ('B0', 25),
        ('B1', 10),
        ('B2', 10),
        ('B3', 10)
    ]
    
    tag_map_data = [
        ('inter_arrival_s', 'M1', 'inter_arrival_s', 's', 'inter_arrival_s', 1.0),
        ('arrival_time_s', 'M1', 'arrival_time_s', 's', 'arrival_time_s', 1.0),
        ('process_time_s', 'M1', 'process_time_s', 's', 'process_time_s', 1.0),
        ('availability', 'M1', 'availability', 'pct', 'availability', 1.0),
        ('mttr_s', 'M1', 'mttr_s', 's', 'mttr_s', 1.0),
        ('work_power_kw', 'M1', 'work_power_kw', 'kW', 'work_power_kw', 1.0),
        ('idle_power_kw', 'M1', 'idle_power_kw', 'kW', 'idle_power_kw', 1.0)
    ]
    
    cursor.executemany('INSERT OR REPLACE INTO machines VALUES (?, ?, ?, ?, ?, ?)', machines_data)
    cursor.executemany('INSERT OR REPLACE INTO buffers VALUES (?, ?)', buffers_data)
    cursor.executemany('INSERT OR REPLACE INTO tag_map VALUES (?, ?, ?, ?, ?, ?)', tag_map_data)
    
    conn.commit()
    conn.close()

# Machine class
class Machine:
    def __init__(self, id, processing_time, availability_pct, mttr_s, power_working_kw, power_idle_kw):
        self.id = id
        self.processing_time = processing_time
        self.availability_pct = availability_pct
        self.mttr_s = mttr_s
        self.power_working_kw = power_working_kw
        self.power_idle_kw = power_idle_kw
        self.is_operational = True
        self.next_failure_time = 0
        self.last_failure_time = 0
        self.total_downtime = 0
        self.total_energy = 0
        self.current_energy = 0
        self.is_working = False
        self.start_processing_time = 0
        self.processing_duration = 0
        
    def update_status(self, current_time):
        # Check if machine should be in failure
        if self.is_operational:
            # Calculate probability of failure for this time step
            failure_prob = (100 - self.availability_pct) / 100.0
            # Simplified failure check (in real case would be more complex)
            if np.random.random() < failure_prob * DT:
                self.is_operational = False
                self.last_failure_time = current_time
                self.next_failure_time = current_time + self.mttr_s
                self.is_working = False
        else:
            # Check if machine should recover
            if current_time >= self.next_failure_time:
                self.is_operational = True
                self.total_downtime += current_time - self.last_failure_time
                
    def start_processing(self, start_time):
        self.is_working = True
        self.start_processing_time = start_time
        self.processing_duration = self.processing_time
        
    def stop_processing(self, end_time):
        self.is_working = False
        self.current_energy += self.power_working_kw * self.processing_duration / 3600.0  # Convert to kWh
        self.total_energy = self.current_energy
        
    def get_power(self):
        if self.is_working:
            return self.power_working_kw
        else:
            return self.power_idle_kw
            
    def log_event(self, conn, event_time, reason_code, duration_s, energy_kwh):
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO events VALUES (?, ?, ?, ?, ?)''', 
                      (event_time, self.id, reason_code, duration_s, energy_kwh))
        conn.commit()

# Buffer class
class Buffer:
    def __init__(self, id, capacity):
        self.id = id
        self.capacity = capacity
        self.items = []
        
    def add_item(self):
        if len(self.items) < self.capacity:
            self.items.append('item')
            return True
        return False
        
    def remove_item(self):
        if len(self.items) > 0:
            self.items.pop()
            return True
        return False
        
    def get_count(self):
        return len(self.items)

# Source class
class Source:
    def __init__(self, inter_arrival_time):
        self.inter_arrival_time = inter_arrival_time
        self.last_arrival = 0
        self.item_count = 0
        
    def should_generate(self, current_time):
        if current_time - self.last_arrival >= self.inter_arrival_time:
            self.last_arrival = current_time
            self.item_count += 1
            return True
        return False

# Sensor class
class Sensor:
    def __init__(self, machine_id, tag, signal, unit, register, scale):
        self.machine_id = machine_id
        self.tag = tag
        self.signal = signal
        self.unit = unit
        self.register = register
        self.scale = scale
        
    def log_sample(self, conn, timestamp, value):
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO samples VALUES (?, ?, ?, ?)''', 
                      (timestamp, self.machine_id, self.tag, value))
        conn.commit()

# Main simulation function
def run_simulation():
    # Setup database
    setup_database()
    
    # Initialize PyChrono system
    chrono.SetChronoDataPath('data/')
    system = chrono.ChSystemNSC()
    system.SetGravitationalAcceleration(GRAVITY)
    
    # Create materials
    mat = chrono.ChMaterialSurfaceNSC()
    mat.SetFriction(0.5)
    mat.SetRestitution(0.1)
    
    # Set up simulation parameters
    machines_data = [
        {'id': 'M1', 'processing_time': 60.0, 'availability_pct': 99.99, 'mttr_s': 300.0, 
         'power_working_kw': 3.0, 'power_idle_kw': 0.3},
        {'id': 'M2', 'processing_time': 80.0, 'availability_pct': 99.0, 'mttr_s': 600.0, 
         'power_working_kw': 5.0, 'power_idle_kw': 0.5},
        {'id': 'M3', 'processing_time': 70.0, 'availability_pct': 99.0, 'mttr_s': 600.0, 
         'power_working_kw': 4.5, 'power_idle_kw': 0.45},
        {'id': 'M4', 'processing_time': 75.0, 'availability_pct': 99.99, 'mttr_s': 300.0, 
         'power_working_kw': 4.0, 'power_idle_kw': 0.4}
    ]
    
    buffers_data = [
        {'id': 'B0', 'capacity': 25},
        {'id': 'B1', 'capacity': 10},
        {'id': 'B2', 'capacity': 10},
        {'id': 'B3', 'capacity': 10}
    ]
    
    # Create machines
    machines = {}
    for data in machines_data:
        machines[data['id']] = Machine(**data)
        
    # Create buffers
    buffers = {}
    for data in buffers_data:
        buffers[data['id']] = Buffer(**data)
        
    # Create source
    source = Source(inter_arrival_time=45.0)
    
    # Create sensors
    sensors = []
    tag_map = [
        ('inter_arrival_s', 'M1', 'inter_arrival_s', 's', 'inter_arrival_s', 1.0),
        ('arrival_time_s', 'M1', 'arrival_time_s', 's', 'arrival_time_s', 1.0),
        ('process_time_s', 'M1', 'process_time_s', 's', 'process_time_s', 1.0),
        ('availability', 'M1', 'availability', 'pct', 'availability', 1.0),
        ('mttr_s', 'M1', 'mttr_s', 's', 'mttr_s', 1.0),
        ('work_power_kw', 'M1', 'work_power_kw', 'kW', 'work_power_kw', 1.0),
        ('idle_power_kw', 'M1', 'idle_power_kw', 'kW', 'idle_power_kw', 1.0)
    ]
    
    for tag_id, machine_id, signal, unit, register, scale in tag_map:
        sensors.append(Sensor(machine_id, tag_id, signal, unit, register, scale))
    
    # Connect sensors to machines
    machine_sensors = {}
    for sensor in sensors:
        if sensor.machine_id not in machine_sensors:
            machine_sensors[sensor.machine_id] = []
        machine_sensors[sensor.machine_id].append(sensor)
    
    # Simulation loop
    current_time = 0.0
    conn = sqlite3.connect('digital_twin.db')
    
    try:
        while current_time < SIMULATION_TIME:
            # Check for new items from source
            if source.should_generate(current_time):
                # Add item to first buffer
                if buffers['B0'].add_item():
                    # Log arrival
                    timestamp = datetime.now().isoformat()
                    for sensor in machine_sensors['M1']:
                        if sensor.tag == 'arrival_time_s':
                            sensor.log_sample(conn, timestamp, current_time)
            
            # Simulate each machine
            for machine_id, machine in machines.items():
                # Update machine status
                machine.update_status(current_time)
                
                # Log machine data
                timestamp = datetime.now().isoformat()
                for sensor in machine_sensors[machine_id]:
                    if sensor.tag == 'availability':
                        sensor.log_sample(conn, timestamp, machine.availability_pct)
                    elif sensor.tag == 'work_power_kw':
                        sensor.log_sample(conn, timestamp, machine.power_working_kw)
                    elif sensor.tag == 'idle_power_kw':
                        sensor.log_sample(conn, timestamp, machine.power_idle_kw)
                    elif sensor.tag == 'mttr_s':
                        sensor.log_sample(conn, timestamp, machine.mttr_s)
                        
                # Process items if operational and working
                if machine.is_operational and machine.is_working:
                    # Check if process is complete
                    if current_time - machine.start_processing_time >= machine.processing_time:
                        machine.stop_processing(current_time)
                        # Move item to next buffer
                        if machine_id == 'M1':
                            buffers['B1'].add_item()
                        elif machine_id == 'M2':
                            buffers['B2'].add_item()
                        elif machine_id == 'M3':
                            buffers['B3'].add_item()
                        elif machine_id == 'M4':
                            # Final station, remove item
                            pass
                elif machine.is_operational and not machine.is_working:
                    # Check if an item exists in the buffer and start processing
                    if machine_id == 'M1' and buffers['B0'].get_count() > 0:
                        buffers['B0'].remove_item()
                        machine.start_processing(current_time)
                    elif machine_id == 'M2' and buffers