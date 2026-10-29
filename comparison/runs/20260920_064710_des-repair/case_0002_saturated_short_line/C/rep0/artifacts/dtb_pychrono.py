```python
import pychrono as chrono
import pychrono.irrlicht as irr
import pychrono.fea as fea
import pychrono.vehicle as vehicle
import math
import json
import time
import datetime
import numpy as np
import sqlite3

# Initialize PyChrono system
system = chrono.ChSystemNSC()
system.SetGravitationalAcceleration(chrono.ChVectorD(0, 0, 0))  # No gravity

# Simulation parameters
SIMULATION_TIME = 432000.0  # 5 days in seconds
TIME_STEP = 0.01
LOG_INTERVAL = 1.0

# Equipment configuration
machines_config = {
    "M1": {
        "process_time_s": 90.0,
        "availability": 0.99,
        "mttr_s": 600.0,
        "work_power_kw": 3.0,
        "idle_power_kw": 0.3
    },
    "M2": {
        "process_time_s": 70.0,
        "availability": 0.98,
        "mttr_s": 900.0,
        "work_power_kw": 4.5,
        "idle_power_kw": 0.45
    },
    "M3": {
        "process_time_s": 110.0,
        "availability": 0.99,
        "mttr_s": 1200.0,
        "work_power_kw": 6.0,
        "idle_power_kw": 0.6
    }
}

buffers_config = {
    "B0": {"capacity": 15},
    "B1": {"capacity": 5},
    "B2": {"capacity": 5}
}

# Create database connection for logging
conn = sqlite3.connect('digital_twin_data.db')
cursor = conn.cursor()

# Create tables if they don't exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS machines (
        id TEXT PRIMARY KEY,
        process_time_s DOUBLE PRECISION,
        availability DOUBLE PRECISION,
        mttr_s DOUBLE PRECISION,
        work_power_kw DOUBLE PRECISION,
        idle_power_kw DOUBLE PRECISION
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS buffers (
        id TEXT PRIMARY KEY,
        capacity INTEGER
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS stations (
        id TEXT PRIMARY KEY,
        processing_time_s DOUBLE PRECISION,
        availability_pct DOUBLE PRECISION,
        mttr_s DOUBLE PRECISION,
        power_working_kw DOUBLE PRECISION,
        power_idle_kw DOUBLE PRECISION
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS events (
        ts TIMESTAMPTZ,
        machine_id TEXT,
        reason_code TEXT,
        duration_s DOUBLE PRECISION,
        energy_kwh DOUBLE PRECISION,
        PRIMARY KEY (ts, machine_id)
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS samples (
        ts TIMESTAMPTZ,
        machine_id TEXT,
        tag TEXT,
        value DOUBLE PRECISION,
        PRIMARY KEY (ts, machine_id, tag)
    )
''')

# Insert machine data
for machine_id, params in machines_config.items():
    cursor.execute(
        "INSERT OR REPLACE INTO machines VALUES (?, ?, ?, ?, ?, ?)",
        (machine_id, params['process_time_s'], params['availability'],
         params['mttr_s'], params['work_power_kw'], params['idle_power_kw'])
    )

# Insert buffer data
for buffer_id, params in buffers_config.items():
    cursor.execute(
        "INSERT OR REPLACE INTO buffers VALUES (?, ?)",
        (buffer_id, params['capacity'])
    )

# Insert station data
for machine_id, params in machines_config.items():
    cursor.execute(
        "INSERT OR REPLACE INTO stations VALUES (?, ?, ?, ?, ?, ?)",
        (machine_id, params['process_time_s'], params['availability']*100,
         params['mttr_s'], params['work_power_kw'], params['idle_power_kw'])
    )

conn.commit()

# Create a source object to feed parts into the system
class Source:
    def __init__(self, system, interval):
        self.system = system
        self.interval = interval
        self.next_arrival = interval
        self.part_count = 0
        
    def update(self, time):
        if time >= self.next_arrival:
            self.create_part()
            self.next_arrival += self.interval
            
    def create_part(self):
        # Create a simple part body
        part = chrono.ChBody()
        part.SetPos(chrono.ChVectorD(0, 0, 0))
        part.SetFixed(False)
        part.SetMass(1.0)
        part.SetInertiaXX(chrono.ChVectorD(0.01, 0.01, 0.01))
        part.SetBodyFixed(False)
        
        # Add a shape for visualization
        part_shape = chrono.ChVisualShapeBox(0.5, 0.5, 0.5)
        part_shape.SetColor(chrono.ChColor(1, 0, 0))  # Red
        part.AddVisualShape(part_shape)
        
        self.system.Add(part)
        self.part_count += 1
        
        # Log part creation event
        timestamp = datetime.datetime.now()
        cursor.execute(
            "INSERT INTO samples VALUES (?, ?, ?, ?)",
            (timestamp, "source", "part_count", self.part_count)
        )
        conn.commit()

# Create a machine object
class Machine:
    def __init__(self, system, machine_id, process_time, availability, mttr, work_power, idle_power):
        self.system = system
        self.id = machine_id
        self.process_time = process_time
        self.availability = availability
        self.mttr = mttr
        self.work_power = work_power
        self.idle_power = idle_power
        self.is_processing = False
        self.process_start = 0.0
        self.is_operational = True
        self.failure_time = 0.0
        self.repair_time = 0.0
        self.last_activity_time = 0.0
        
        # Machine body
        self.body = chrono.ChBody()
        self.body.SetPos(chrono.ChVectorD(0, 0, 0))
        self.body.SetFixed(False)
        self.body.SetMass(100.0)
        self.body.SetInertiaXX(chrono.ChVectorD(1.0, 1.0, 1.0))
        
        # Add shape for visualization
        machine_shape = chrono.ChVisualShapeBox(2.0, 1.0, 1.0)
        machine_shape.SetColor(chrono.ChColor(0, 0, 1))  # Blue
        self.body.AddVisualShape(machine_shape)
        
        self.system.Add(self.body)
        
    def update(self, time):
        # Check if machine needs to be repaired or restored
        if not self.is_operational and time >= self.repair_time:
            self.is_operational = True
            self.repair_time = 0.0
            # Log event
            timestamp = datetime.datetime.now()
            cursor.execute(
                "INSERT INTO events VALUES (?, ?, ?, ?, ?)",
                (timestamp, self.id, "repair", 0.0, 0.0)
            )
            conn.commit()
            
        # Check if machine fails (randomly based on availability)
        if self.is_operational and time > self.last_activity_time + 1.0:
            # Simple availability model
            if np.random.random() > self.availability:
                self.is_operational = False
                self.failure_time = time
                self.repair_time = time + self.mttr
                # Log event
                timestamp = datetime.datetime.now()
                cursor.execute(
                    "INSERT INTO events VALUES (?, ?, ?, ?, ?)",
                    (timestamp, self.id, "failure", self.mttr, 0.0)
                )
                conn.commit()
                
        # Log power consumption
        if self.is_operational:
            power = self.work_power if self.is_processing else self.idle_power
            energy = power * TIME_STEP / 3600.0  # kWh
            timestamp = datetime.datetime.now()
            cursor.execute(
                "INSERT INTO samples VALUES (?, ?, ?, ?)",
                (timestamp, self.id, "power_kw", power)
            )
            cursor.execute(
                "INSERT INTO samples VALUES (?, ?, ?, ?)",
                (timestamp, self.id, "energy_kwh", energy)
            )
            conn.commit()
            
        self.last_activity_time = time

# Create a buffer object
class Buffer:
    def __init__(self, system, buffer_id, capacity):
        self.system = system
        self.id = buffer_id
        self.capacity = capacity
        self.parts = []
        
        # Create a simple visual representation of the buffer
        self.body = chrono.ChBody()
        self.body.SetPos(chrono.ChVectorD(0, 0, 0))
        self.body.SetFixed(True)
        self.body.SetMass(0.0)
        self.body.SetInertiaXX(chrono.ChVectorD(0.0, 0.0, 0.0))
        
        # Add shape for visualization
        buffer_shape = chrono.ChVisualShapeBox(3.0, 1.5, 1.0)
        buffer_shape.SetColor(chrono.ChColor(0.5, 0.5, 0.5))  # Gray
        self.body.AddVisualShape(buffer_shape)
        
        self.system.Add(self.body)
        
    def update(self, time):
        # Log buffer status
        timestamp = datetime.datetime.now()
        cursor.execute(
            "INSERT INTO samples VALUES (?, ?, ?, ?)",
            (timestamp, self.id, "part_count", len(self.parts))
        )
        cursor.execute(
            "INSERT INTO samples VALUES (?, ?, ?, ?)",
            (timestamp, self.id, "capacity", self.capacity)
        )
        conn.commit()

# Create source
source = Source(system, 60.0)  # 60 second interval between parts

# Create machines
machines = {}
for machine_id, params in machines_config.items():
    machines[machine_id] = Machine(
        system, machine_id, params['process_time_s'], params['availability'],
        params['mttr_s'], params['work_power_kw'], params['idle_power_kw']
    )

# Create buffers
buffers = {}
for buffer_id, params in buffers_config.items():
    buffers[buffer_id] = Buffer(system, buffer_id, params['capacity'])

# Main simulation loop
print("Starting simulation...")
start_time = time.time()
current_time = 0.0

while current_time < SIMULATION_TIME:
    # Update source
    source.update(current_time)
    
    # Update machines
    for machine in machines.values():
        machine.update(current_time)
        
    # Update buffers
    for buffer in buffers.values():
        buffer.update(current_time)
        
    # Step the simulation
    system.DoStepDynamics(TIME_STEP)
    current_time += TIME_STEP
    
    # Log data at intervals
    if current_time % LOG_INTERVAL < TIME_STEP:
        timestamp = datetime.datetime.now()
        # Log system-wide status
        cursor.execute(
            "INSERT INTO samples VALUES (?, ?, ?, ?)",
            (timestamp, "system", "time_sec", current_time)
        )
        conn.commit()

print("Simulation finished.")
print(f"Total simulated time: {current_time:.2f} seconds")
print(f"Execution time: {time.time() - start_time:.2f} seconds")

# Close database connection
conn.close()
```