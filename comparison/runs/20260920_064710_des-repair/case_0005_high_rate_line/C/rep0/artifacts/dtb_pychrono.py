```python
import pychrono as chrono
import pychrono.irrlicht as irr
import math
import json
import time
from datetime import datetime, timezone
import sqlite3
import os

# Database setup
def init_db():
    conn = sqlite3.connect('digital_twin.db')
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS raw_ingest (
            ingested_at timestamptz NOT NULL,
            source text NOT NULL,
            payload jsonb NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ingest_watermark (
            source text PRIMARY KEY,
            max_event_ts timestamptz
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS machines (
            id text PRIMARY KEY,
            process_time_s double precision,
            availability double precision,
            mttr_s double precision,
            work_power_kw double precision,
            idle_power_kw double precision
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS buffers (
            id text PRIMARY KEY,
            capacity int,
            before text,
            after text
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tag_map (
            tag_id text PRIMARY KEY,
            machine_id text,
            signal text,
            unit text,
            register text,
            scale double precision
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            ts timestamptz NOT NULL,
            machine_id text NOT NULL,
            reason_code text,
            duration_s double precision,
            energy_kwh double precision
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS samples (
            ts timestamptz NOT NULL,
            machine_id text NOT NULL,
            tag text NOT NULL,
            value double precision
        )
    ''')
    
    # Insert initial data
    machines_data = [
        ('M1', 60.0, 0.995, 300.0, 3.0, 0.3),
        ('M2', 80.0, 0.99, 600.0, 5.0, 0.5),
        ('M3', 70.0, 0.99, 600.0, 4.5, 0.45),
        ('M4', 75.0, 0.995, 300.0, 4.0, 0.4)
    ]
    
    buffers_data = [
        ('B0', 25, 'source', 'M1'),
        ('B1', 10, 'M1', 'M2'),
        ('B2', 10, 'M2', 'M3'),
        ('B3', 10, 'M3', 'M4')
    ]
    
    tag_map_data = [
        ('Avg_Time_per_part_s', 'M1', 'Avg_Time_per_part_s', 's', 'Avg_Time_per_part_s', 1.0),
        ('Availability_%', 'M1', 'Availability_%', '%', 'Availability_%', 1.0),
        ('MTTR_s', 'M1', 'MTTR_s', 's', 'MTTR_s', 1.0),
        ('EnergyIdling', 'M1', 'EnergyIdling', 'kWh', 'EnergyIdling', 1.0),
        ('EnergyWorking', 'M1', 'EnergyWorking', 'kWh', 'EnergyWorking', 1.0)
    ]
    
    cursor.executemany(
        'INSERT OR REPLACE INTO machines VALUES (?, ?, ?, ?, ?, ?)',
        machines_data
    )
    
    cursor.executemany(
        'INSERT OR REPLACE INTO buffers VALUES (?, ?, ?, ?)',
        buffers_data
    )
    
    cursor.executemany(
        'INSERT OR REPLACE INTO tag_map VALUES (?, ?, ?, ?, ?, ?)',
        tag_map_data
    )
    
    conn.commit()
    conn.close()

# Sensor class to collect data
class Sensor:
    def __init__(self, machine_id, tag, unit):
        self.machine_id = machine_id
        self.tag = tag
        self.unit = unit
        self.values = []
        
    def add_value(self, timestamp, value):
        self.values.append((timestamp, value))
        
    def log_to_db(self, conn):
        cursor = conn.cursor()
        for ts, value in self.values:
            cursor.execute(
                'INSERT INTO samples VALUES (?, ?, ?, ?)',
                (ts, self.machine_id, self.tag, value)
            )
        conn.commit()

# Machine class representing production equipment
class Machine:
    def __init__(self, id, process_time_s, availability, mttr_s, work_power_kw, idle_power_kw):
        self.id = id
        self.process_time_s = process_time_s
        self.availability = availability
        self.mttr_s = mttr_s
        self.work_power_kw = work_power_kw
        self.idle_power_kw = idle_power_kw
        self.is_operational = True
        self.start_time = 0
        self.total_energy_kwh = 0
        self.active_time = 0
        self.idle_time = 0
        
        # Create sensors
        self.sensors = {
            'Avg_Time_per_part_s': Sensor(id, 'Avg_Time_per_part_s', 's'),
            'Availability_%': Sensor(id, 'Availability_%', '%'),
            'MTTR_s': Sensor(id, 'MTTR_s', 's'),
            'EnergyIdling': Sensor(id, 'EnergyIdling', 'kWh'),
            'EnergyWorking': Sensor(id, 'EnergyWorking', 'kWh')
        }
        
    def update_status(self, current_time, is_active):
        if is_active:
            self.active_time += 1
        else:
            self.idle_time += 1
            
        # Simulate machine failure based on availability
        if not self.is_operational and current_time - self.start_time >= self.mttr_s:
            self.is_operational = True
            
        elif not self.is_operational:
            pass  # Still in repair mode
            
        elif not self.is_operational and current_time - self.start_time < self.mttr_s:
            pass  # Still in repair mode
            
        elif not self.is_operational:
            self.start_time = current_time
            
    def get_current_power(self, is_active):
        return self.work_power_kw if is_active else self.idle_power_kw
    
    def calculate_energy(self, dt, is_active):
        power = self.get_current_power(is_active)
        energy_kwh = (power * dt) / 3600  # Convert Wh to kWh
        self.total_energy_kwh += energy_kwh
        return energy_kwh
        
    def log_metrics(self, timestamp, conn):
        cursor = conn.cursor()
        
        # Log events
        if not self.is_operational:
            cursor.execute(
                'INSERT INTO events VALUES (?, ?, ?, ?, ?)',
                (timestamp, self.id, 'FAILURE', self.mttr_s, 0.0)
            )
            
        # Log sample values
        self.sensors['Avg_Time_per_part_s'].add_value(timestamp, self.process_time_s)
        self.sensors['Availability_%'].add_value(timestamp, self.availability * 100)
        self.sensors['MTTR_s'].add_value(timestamp, self.mttr_s)
        self.sensors['EnergyIdling'].add_value(timestamp, self.total_energy_kwh)
        self.sensors['EnergyWorking'].add_value(timestamp, self.total_energy_kwh)
        
        # Commit all samples
        for sensor in self.sensors.values():
            sensor.log_to_db(conn)

# Buffer class for material storage
class Buffer:
    def __init__(self, id, capacity, before, after):
        self.id = id
        self.capacity = capacity
        self.before = before
        self.after = after
        self.contents = []
        
    def add_item(self, item):
        if len(self.contents) < self.capacity:
            self.contents.append(item)
            return True
        return False
        
    def remove_item(self):
        if self.contents:
            return self.contents.pop(0)
        return None
        
    def is_full(self):
        return len(self.contents) >= self.capacity
        
    def is_empty(self):
        return len(self.contents) == 0

# Source class for producing items
class Source:
    def __init__(self, inter_arrival_time_s):
        self.inter_arrival_time_s = inter_arrival_time_s
        self.last_production_time = 0
        self.production_count = 0
        
    def should_produce(self, current_time):
        return current_time - self.last_production_time >= self.inter_arrival_time_s
        
    def produce(self, current_time):
        self.last_production_time = current_time
        self.production_count += 1
        return f"Part_{self.production_count}"

# Simulation class
class ProductionLineSimulation:
    def __init__(self):
        # Initialize Chrono system
        self.system = chrono.ChSystemNSC()
        self.system.SetGravitationalAcceleration(chrono.ChVectorD(0, 0, 0))
        
        # Setup Irrlicht visualization
        self.visualizer = None
        
        # Create machines
        self.machines = {}
        machines_config = [
            ('M1', 60.0, 0.995, 300.0, 3.0, 0.3),
            ('M2', 80.0, 0.99, 600.0, 5.0, 0.5),
            ('M3', 70.0, 0.99, 600.0, 4.5, 0.45),
            ('M4', 75.0, 0.995, 300.0, 4.0, 0.4)
        ]
        
        for config in machines_config:
            machine = Machine(*config)
            self.machines[config[0]] = machine
            
        # Create buffers
        self.buffers = {}
        buffer_configs = [
            ('B0', 25, 'source', 'M1'),
            ('B1', 10, 'M1', 'M2'),
            ('B2', 10, 'M2', 'M3'),
            ('B3', 10, 'M3', 'M4')
        ]
        
        for config in buffer_configs:
            buffer = Buffer(*config)
            self.buffers[config[0]] = buffer
            
        # Create source
        self.source = Source(45)
        
        # Simulation state
        self.current_time = 0
        self.running = True
        
        # Database connection
        self.conn = sqlite3.connect('digital_twin.db')
        
    def run_simulation(self, total_time=432000):
        print("Starting simulation...")
        start_time = time.time()
        
        try:
            while self.current_time < total_time:
                # Record simulation time
                timestamp = datetime.now(timezone.utc)
                
                # Handle source production
                if self.source.should_produce(self.current_time):
                    part = self.source.produce(self.current_time)
                    if self.buffers['B0'].add_item(part):
                        print(f"Produced {part} at time {self.current_time}")
                    
                # Process through buffers and machines
                self.process_production_line()
                
                # Update machine statuses
                for machine in self.machines.values():
                    machine.update_status(self.current_time, False)  # Default to idle
                    
                # Log metrics
                for machine in self.machines.values():
                    machine.log_metrics(timestamp, self.conn)
                    
                # Step simulation time
                self.current_time += 1
                
                # Print progress every 3600 seconds (1 hour)
                if self.current_time % 3600 == 0:
                    elapsed = time.time() - start_time
                    print(f"Simulated {self.current_time}s in {elapsed:.2f}s")
                    
        except Exception as e:
            print(f"Error during simulation: {e}")
        finally:
            self.cleanup()
            
    def process_production_line(self):
        # Process parts through the line
        # This is a simplified version - in a real implementation, 
        # this would involve more complex logic with actual processing times
        for i, buffer_name in enumerate(['B0', 'B1', 'B2', 'B3']):
            buffer = self.buffers[buffer_name]
            if not buffer.is_empty():
                # Move item to next stage
                item = buffer.remove_item()
                if i < 3:  # Not the last buffer
                    next_buffer = self.buffers[f'B{i+1}']
                    if next_buffer.add_item(item):
                        print(f"Moved {item} from {buffer_name} to B{i+1}")
                        
    def cleanup(self):
        if self.conn:
            self.conn.close()
        print("Simulation completed")

# Main execution function
def main():
    # Initialize database
    init_db()
    
    # Create and run simulation
    sim = ProductionLineSimulation()
    sim.run_simulation(432000)  # Run for 432000 seconds (5 days)
    
    print("Simulation finished successfully")

if __name__ == "__main__":
    main()
```