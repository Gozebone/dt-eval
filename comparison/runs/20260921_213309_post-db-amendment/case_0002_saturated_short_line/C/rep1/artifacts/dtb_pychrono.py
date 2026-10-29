```python
import pychrono as chrono
import pychrono.irrlicht as irr
import pychrono.fea as fea
import numpy as np
import time
import json
from datetime import datetime, timedelta
import sqlite3
import os

# Create database connection
def create_db_connection():
    conn = sqlite3.connect(':memory:')  # In-memory database for this example
    return conn

# Create tables for our database schema
def create_tables(conn):
    cursor = conn.cursor()
    
    # Raw ingest table
    cursor.execute('''
        CREATE TABLE raw_ingest (
            ingested_at timestamptz NOT NULL,
            source text NOT NULL,
            payload jsonb NOT NULL
        )
    ''')
    
    # Ingest watermark table
    cursor.execute('''
        CREATE TABLE ingest_watermark (
            source text PRIMARY KEY,
            max_event_ts timestamptz
        )
    ''')
    
    # Machines table
    cursor.execute('''
        CREATE TABLE machines (
            id text PRIMARY KEY,
            name text
        )
    ''')
    
    # Buffers table
    cursor.execute('''
        CREATE TABLE buffers (
            id text PRIMARY KEY,
            capacity int,
            before text,
            after text
        )
    ''')
    
    # Stations table
    cursor.execute('''
        CREATE TABLE stations (
            id text PRIMARY KEY,
            processing_time_s int,
            availability_pct int,
            mttr_s int,
            power_working_kw double precision,
            power_idle_kw double precision
        )
    ''')
    
    # Tag map table
    cursor.execute('''
        CREATE TABLE tag_map (
            tag_id text PRIMARY KEY,
            machine_id text,
            signal text,
            unit text,
            register text,
            scale double precision
        )
    ''')
    
    # Events table
    cursor.execute('''
        CREATE TABLE events (
            ts timestamptz NOT NULL,
            machine_id text NOT NULL,
            reason_code text,
            duration_s double precision,
            energy_kwh double precision
        )
    ''')
    
    # Samples table
    cursor.execute('''
        CREATE TABLE samples (
            ts timestamptz NOT NULL,
            machine_id text NOT NULL,
            tag text NOT NULL,
            value double precision
        )
    ''')
    
    # Indexes
    cursor.execute('CREATE INDEX idx_events_machine_time ON events (machine_id, ts)')
    cursor.execute('CREATE INDEX idx_samples_machine_time ON samples (machine_id, ts)')
    
    conn.commit()

# Insert initial data into database
def insert_initial_data(conn):
    cursor = conn.cursor()
    
    # Insert machines
    machines_data = [
        ('M1', 'M1'),
        ('M2', 'M2'),
        ('M3', 'M3'),
        ('B0', 'B0'),
        ('B1', 'B1'),
        ('B2', 'B2')
    ]
    cursor.executemany('INSERT INTO machines VALUES (?, ?)', machines_data)
    
    # Insert buffers
    buffers_data = [
        ('B0', 15, 'source', 'M1'),
        ('B1', 5, 'M1', 'M2'),
        ('B2', 5, 'M2', 'M3')
    ]
    cursor.executemany('INSERT INTO buffers VALUES (?, ?, ?, ?)', buffers_data)
    
    # Insert stations
    stations_data = [
        ('M1', 90, 100, 600, 3.0, 0.3),
        ('M2', 70, 99, 900, 4.5, 0.45),
        ('M3', 110, 100, 1200, 6.0, 0.6)
    ]
    cursor.executemany('INSERT INTO stations VALUES (?, ?, ?, ?, ?, ?)', stations_data)
    
    # Insert tag map
    tag_map_data = [
        ('Avg_Time_per_part_s', 'M1', 'Avg_Time_per_part_s', 's', 'Avg_Time_per_part_s', 1),
        ('Availability_%', 'M1', 'Availability_%', '%', 'Availability_%', 1),
        ('MTTR_s', 'M1', 'MTTR_s', 's', 'MTTR_s', 1),
        ('EnergyIdling', 'M1', 'EnergyIdling', 'kW', 'EnergyIdling', 1),
        ('EnergyWorking', 'M1', 'EnergyWorking', 'kW', 'EnergyWorking', 1)
    ]
    cursor.executemany('INSERT INTO tag_map VALUES (?, ?, ?, ?, ?, ?)', tag_map_data)
    
    conn.commit()

# Machine class to represent each production station
class ProductionMachine:
    def __init__(self, id, processing_time, availability, mttr, power_working, power_idle):
        self.id = id
        self.processing_time = processing_time
        self.availability = availability / 100.0  # Convert percentage to decimal
        self.mttr = mttr
        self.power_working = power_working
        self.power_idle = power_idle
        self.is_operational = True
        self.operational_time = 0
        self.downtime = 0
        self.start_time = 0
        self.last_update = 0
        self.energy_consumed = 0
        self.parts_processed = 0
        
    def update(self, current_time, dt):
        if self.is_operational:
            # Simulate processing time
            self.operational_time += dt
            
            # Check if part is finished processing
            if self.operational_time >= self.processing_time:
                self.parts_processed += 1
                self.operational_time = 0
                # Randomly decide if machine fails based on availability
                if np.random.rand() > self.availability:
                    self.is_operational = False
                    self.start_time = current_time
                    self.downtime = 0
                    
        else:
            # Machine is down, simulate repair
            self.downtime += dt
            if self.downtime >= self.mttr:
                self.is_operational = True
                self.operational_time = 0
                
    def get_energy_consumption(self, dt):
        if self.is_operational:
            return self.power_working * dt / 3600.0  # Convert to kWh
        else:
            return self.power_idle * dt / 3600.0  # Convert to kWh
            
    def get_sensor_data(self, current_time):
        # Return sensor data for this machine
        return {
            'Avg_Time_per_part_s': self.processing_time,
            'Availability_%': self.availability * 100,
            'MTTR_s': self.mttr,
            'EnergyIdling': self.power_idle,
            'EnergyWorking': self.power_working
        }

# Buffer class to represent storage areas
class ProductionBuffer:
    def __init__(self, id, capacity):
        self.id = id
        self.capacity = capacity
        self.contents = []
        
    def add_part(self, part):
        if len(self.contents) < self.capacity:
            self.contents.append(part)
            return True
        return False
        
    def remove_part(self):
        if self.contents:
            return self.contents.pop(0)
        return None
        
    def get_count(self):
        return len(self.contents)

# Source class to generate parts
class PartSource:
    def __init__(self, inter_arrival_time):
        self.inter_arrival_time = inter_arrival_time
        self.last_arrival = 0
        self.parts_generated = 0
        
    def update(self, current_time, dt):
        if current_time - self.last_arrival >= self.inter_arrival_time:
            self.parts_generated += 1
            self.last_arrival = current_time
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
        self.end_time = 432000  # 5 days in seconds
        
        # Create database
        self.db_conn = create_db_connection()
        create_tables(self.db_conn)
        insert_initial_data(self.db_conn)
        
        # Create production elements
        self.source = PartSource(60)  # 60 second inter-arrival time
        self.machines = {}
        self.buffers = {}
        
        # Initialize machines
        self.machines['M1'] = ProductionMachine(
            'M1', 90, 100, 600, 3.0, 0.3)
        self.machines['M2'] = ProductionMachine(
            'M2', 70, 99, 900, 4.5, 0.45)
        self.machines['M3'] = ProductionMachine(
            'M3', 110, 100, 1200, 6.0, 0.6)
            
        # Initialize buffers
        self.buffers['B0'] = ProductionBuffer('B0', 15)
        self.buffers['B1'] = ProductionBuffer('B1', 5)
        self.buffers['B2'] = ProductionBuffer('B2', 5)
        
        # Track state changes
        self.events = []
        self.samples = []
        
    def log_event(self, machine_id, reason_code, duration, energy_kwh):
        timestamp = datetime.now()
        self.events.append({
            'ts': timestamp,
            'machine_id': machine_id,
            'reason_code': reason_code,
            'duration_s': duration,
            'energy_kwh': energy_kwh
        })
        
        # Insert into database
        cursor = self.db_conn.cursor()
        cursor.execute('''
            INSERT INTO events VALUES (?, ?, ?, ?, ?)
        ''', (timestamp, machine_id, reason_code, duration, energy_kwh))
        self.db_conn.commit()
        
    def log_sample(self, machine_id, tag, value):
        timestamp = datetime.now()
        self.samples.append({
            'ts': timestamp,
            'machine_id': machine_id,
            'tag': tag,
            'value': value
        })
        
        # Insert into database
        cursor = self.db_conn.cursor()
        cursor.execute('''
            INSERT INTO samples VALUES (?, ?, ?, ?)
        ''', (timestamp, machine_id, tag, value))
        self.db_conn.commit()
        
    def run_simulation(self):
        print("Starting production line simulation...")
        start_time = time.time()
        
        while self.simulation_time < self.end_time:
            # Update source
            if self.source.update(self.simulation_time, self.dt):
                # Add part to first buffer
                if self.buffers['B0'].add_part('part'):
                    print(f"Part generated at {self.simulation_time}s")
                    
            # Process through buffers and machines
            # Move parts from B0 to M1
            if self.buffers['B0'].get_count() > 0 and self.machines['M1'].is_operational:
                part = self.buffers['B0'].remove_part()
                if part:
                    # Simulate processing
                    pass
                    
            # Move parts from B1 to M2
            if self.buffers['B1'].get_count() > 0 and self.machines['M2'].is_operational:
                part = self.buffers['B1'].remove_part()
                if part:
                    # Simulate processing
                    pass
                    
            # Move parts from B2 to sink
            if self.buffers['B2'].get_count() > 0 and self.machines['M3'].is_operational:
                part = self.buffers['B2'].remove_part()
                if part:
                    # Part completed
                    print(f"Part completed at {self.simulation_time}s")
                    
            # Update all machines
            for machine_id, machine in self.machines.items():
                machine.update(self.simulation_time, self.dt)
                
                # Log sensor data
                sensor_data = machine.get_sensor_data(self.simulation_time)
                for tag, value in sensor_data.items():
                    self.log_sample(machine_id, tag, value)
                    
                # Log energy consumption
                energy_kwh = machine.get_energy_consumption(self.dt)
                self.log_event(machine_id, 'ENERGY_CONSUMPTION', self.dt, energy_kwh)
                
            # Advance time
            self.simulation_time += self.dt
            
            # Print progress every 1000 steps
            if int(self.simulation_time) % 1000 == 0:
                print(f"Time: {self.simulation_time:.0f}s")
                
        end_time = time.time()
        print(f"Simulation completed in {end_time - start_time:.2f} seconds")
        print(f"Total parts processed: {sum(m.parts_processed for m in self.machines.values())}")
        
        # Output final statistics
        for machine_id, machine in self.machines.items():
            print(f"Machine {machine_id}:")
            print(f"  Parts processed: {machine.parts_processed}")
            print(f"  Operational time: {machine.operational_time:.2f}s")
            print(f"  Downtime: {machine.downtime:.2f}s")
            print(f"  Availability: {(machine.operational_time/(machine.operational_time+machine.downtime)*100):.2f}%")

# Run the simulation
if __name__ == "__main__":
    try:
        sim = ProductionLineSimulation()
        sim.run_simulation()
        print("Simulation completed successfully.")
    except Exception as e:
        print(f"Error during simulation: {str(e)}")
        raise
```