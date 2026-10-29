```python
import pychrono as chrono
import pychrono.irrlicht as chronoirr
import numpy as np
import time
import json
from datetime import datetime, timedelta
import sqlite3

# Initialize PyChrono system
chrono.SetChronoDataPath("../../../data/")
chrono.SetChronoDataPath("../../../data/")
chrono.SetChronoDataPath("../../../data/")

# Create the simulation system
sys = chrono.ChSystemNSC()

# Set gravity
sys.Set_G_acc(chrono.ChVectorD(0, -9.81, 0))

# Create a ground body
ground = chrono.ChBody()
ground.SetFixed(True)
ground.SetPos(chrono.ChVectorD(0, -1, 0))
sys.Add(ground)

# Materials
steel_mat = chrono.ChMaterialSurfaceNSC()
steel_mat.SetFriction(0.4)
steel_mat.SetRestitution(0.1)

# Create equipment bodies
equipment_bodies = {}
equipment_params = {
    'M1': {'pos': chrono.ChVectorD(0, 0, 0), 'size': chrono.ChVectorD(1, 1, 1), 'mass': 100},
    'M2': {'pos': chrono.ChVectorD(3, 0, 0), 'size': chrono.ChVectorD(1, 1, 1), 'mass': 100},
    'M3': {'pos': chrono.ChVectorD(6, 0, 0), 'size': chrono.ChVectorD(1, 1, 1), 'mass': 100},
    'M4': {'pos': chrono.ChVectorD(9, 0, 0), 'size': chrono.ChVectorD(1, 1, 1), 'mass': 100},
    'B0': {'pos': chrono.ChVectorD(-2, 0, 0), 'size': chrono.ChVectorD(0.5, 0.5, 0.5), 'mass': 50},
    'B1': {'pos': chrono.ChVectorD(1.5, 0, 0), 'size': chrono.ChVectorD(0.5, 0.5, 0.5), 'mass': 50},
    'B2': {'pos': chrono.ChVectorD(4.5, 0, 0), 'size': chrono.ChVectorD(0.5, 0.5, 0.5), 'mass': 50},
    'B3': {'pos': chrono.ChVectorD(7.5, 0, 0), 'size': chrono.ChVectorD(0.5, 0.5, 0.5), 'mass': 50}
}

# Create bodies for all equipment
for id, params in equipment_params.items():
    body = chrono.ChBody()
    body.SetPos(params['pos'])
    body.SetMass(params['mass'])
    body.SetInertiaXX(chrono.ChVectorD(1, 1, 1) * params['mass'] * 0.1)
    body.GetMaterialSurfaceNSC().SetFriction(0.5)
    body.GetMaterialSurfaceNSC().SetRestitution(0.2)
    
    # Add collision shape
    shape = chrono.ChCollisionModel()
    shape.AddBox(steel_mat, params['size'].x, params['size'].y, params['size'].z)
    body.SetCollisionModel(shape)
    
    # Add visualization shape
    vis_shape = chrono.ChVisualShapeBox(params['size'].x, params['size'].y, params['size'].z)
    vis_shape.SetColor(chrono.ChColor(0.5, 0.5, 0.5))
    body.AddVisualShape(vis_shape)
    
    sys.Add(body)
    equipment_bodies[id] = body

# Setup simulation parameters
simulation_duration = 5 * 24 * 60 * 60  # 5 days in seconds
time_step = 0.01
current_time = 0

# Create a source for parts
source_pos = chrono.ChVectorD(-4, 0, 0)
part_counter = 0
part_interval = 45  # seconds between parts

# Create parts that will be produced
parts = []

# Create a simple sensor system to collect data
sensor_data = {
    'Avg_Time_per_part_s': {},
    'Availability_%': {},
    'MTTR_s': {},
    'EnergyIdling': {},
    'EnergyWorking': {}
}

# Create a database connection for logging
conn = sqlite3.connect('digital_twin.db')
cursor = conn.cursor()

# Create database tables
cursor.execute('''CREATE TABLE IF NOT EXISTS tag_map (
    tag_id TEXT PRIMARY KEY,
    machine_id TEXT,
    signal TEXT,
    unit TEXT,
    register TEXT,
    scale DOUBLE PRECISION
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS raw_ingest (
    ingested_at TIMESTAMPTZ,
    source TEXT,
    payload JSONB
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS ingest_watermark (
    source TEXT PRIMARY KEY,
    max_event_ts TIMESTAMPTZ
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS machines (
    id TEXT PRIMARY KEY,
    process_time_s DOUBLE PRECISION,
    availability_pct DOUBLE PRECISION,
    mttr_s DOUBLE PRECISION,
    power_working_kw DOUBLE PRECISION,
    power_idle_kw DOUBLE PRECISION
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS buffers (
    id TEXT PRIMARY KEY,
    capacity INTEGER,
    before TEXT,
    after TEXT
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS stations (
    id TEXT PRIMARY KEY,
    processing_time_s DOUBLE PRECISION,
    availability_pct DOUBLE PRECISION,
    mttr_s DOUBLE PRECISION,
    power_working_kw DOUBLE PRECISION,
    power_idle_kw DOUBLE PRECISION
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS events (
    ts TIMESTAMPTZ,
    machine_id TEXT,
    reason_code TEXT,
    duration_s DOUBLE PRECISION,
    energy_kwh DOUBLE PRECISION
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS samples (
    ts TIMESTAMPTZ,
    machine_id TEXT,
    tag TEXT,
    value DOUBLE PRECISION
)''')

# Insert tag map data
tag_map_data = [
    ('Avg_Time_per_part_s', 'M1', 'Avg_Time_per_part_s', 's', 'Avg_Time_per_part_s', 1),
    ('Availability_%', 'M1', 'Availability_%', '%', 'Availability_%', 1),
    ('MTTR_s', 'M1', 'MTTR_s', 's', 'MTTR_s', 1),
    ('EnergyIdling', 'M1', 'EnergyIdling', 'kW', 'EnergyIdling', 1),
    ('EnergyWorking', 'M1', 'EnergyWorking', 'kW', 'EnergyWorking', 1),
    ('Avg_Time_per_part_s', 'M2', 'Avg_Time_per_part_s', 's', 'Avg_Time_per_part_s', 1),
    ('Availability_%', 'M2', 'Availability_%', '%', 'Availability_%', 1),
    ('MTTR_s', 'M2', 'MTTR_s', 's', 'MTTR_s', 1),
    ('EnergyIdling', 'M2', 'EnergyIdling', 'kW', 'EnergyIdling', 1),
    ('EnergyWorking', 'M2', 'EnergyWorking', 'kW', 'EnergyWorking', 1),
    ('Avg_Time_per_part_s', 'M3', 'Avg_Time_per_part_s', 's', 'Avg_Time_per_part_s', 1),
    ('Availability_%', 'M3', 'Availability_%', '%', 'Availability_%', 1),
    ('MTTR_s', 'M3', 'MTTR_s', 's', 'MTTR_s', 1),
    ('EnergyIdling', 'M3', 'EnergyIdling', 'kW', 'EnergyIdling', 1),
    ('EnergyWorking', 'M3', 'EnergyWorking', 'kW', 'EnergyWorking', 1),
    ('Avg_Time_per_part_s', 'M4', 'Avg_Time_per_part_s', 's', 'Avg_Time_per_part_s', 1),
    ('Availability_%', 'M4', 'Availability_%', '%', 'Availability_%', 1),
    ('MTTR_s', 'M4', 'MTTR_s', 's', 'MTTR_s', 1),
    ('EnergyIdling', 'M4', 'EnergyIdling', 'kW', 'EnergyIdling', 1),
    ('EnergyWorking', 'M4', 'EnergyWorking', 'kW', 'EnergyWorking', 1)
]

cursor.executemany('INSERT OR REPLACE INTO tag_map VALUES (?, ?, ?, ?, ?, ?)', tag_map_data)

# Insert machine data
machines_data = [
    ('M1', 59.99, 0.995, 46.14, 3.00, 0.30),
    ('M2', 80.28, 0.99, 1.00, 4.98, 0.45),
    ('M3', 70.16, 0.99, 272.07, 4.49, 0.42),
    ('M4', 75.03, 0.995, 1.00, 4.00, 0.40)
]

cursor.executemany('INSERT OR REPLACE INTO machines VALUES (?, ?, ?, ?, ?, ?)', machines_data)

# Insert station data
stations_data = [
    ('M1', 60, 0.995, 300, 3.0, 0.3),
    ('M2', 80, 0.99, 600, 5.0, 0.5),
    ('M3', 70, 0.99, 600, 4.5, 0.45),
    ('M4', 75, 0.995, 300, 4.0, 0.4)
]

cursor.executemany('INSERT OR REPLACE INTO stations VALUES (?, ?, ?, ?, ?, ?)', stations_data)

# Insert buffer data
buffers_data = [
    ('B0', 25, 'source', 'M1'),
    ('B1', 10, 'M1', 'M2'),
    ('B2', 10, 'M2', 'M3'),
    ('B3', 10, 'M3', 'M4')
]

cursor.executemany('INSERT OR REPLACE INTO buffers VALUES (?, ?, ?, ?)', buffers_data)

# Commit and close the connection
conn.commit()

# Simulation logic
start_time = time.time()
part_start_time = current_time

# Main simulation loop
while current_time < simulation_duration:
    # Add new parts to the system if needed
    if current_time - part_start_time >= part_interval:
        # Create a new part
        part = chrono.ChBody()
        part.SetPos(source_pos)
        part.SetMass(10)
        part.SetInertiaXX(chrono.ChVectorD(0.1, 0.1, 0.1))
        part.GetMaterialSurfaceNSC().SetFriction(0.3)
        part.GetMaterialSurfaceNSC().SetRestitution(0.1)
        
        # Add collision and visualization
        shape = chrono.ChCollisionModel()
        shape.AddSphere(steel_mat, 0.2)
        part.SetCollisionModel(shape)
        
        vis_shape = chrono.ChVisualShapeSphere(0.2)
        vis_shape.SetColor(chrono.ChColor(0.2, 0.2, 0.8))
        part.AddVisualShape(vis_shape)
        
        sys.Add(part)
        parts.append(part)
        
        part_counter += 1
        part_start_time = current_time

    # Step the simulation
    sys.DoStepDynamics(time_step)
    current_time += time_step
    
    # Collect data at regular intervals
    if current_time % 10 < time_step:  # Every 10 seconds
        # Log sample data for sensors
        timestamp = datetime.utcnow()
        for machine_id in ['M1', 'M2', 'M3', 'M4']:
            data_to_log = [
                ('Avg_Time_per_part_s', machine_id, 60.0),
                ('Availability_%', machine_id, 99.5),
                ('MTTR_s', machine_id, 300.0),
                ('EnergyIdling', machine_id, 0.3),
                ('EnergyWorking', machine_id, 3.0)
            ]
            
            for tag, mid, value in data_to_log:
                cursor.execute('INSERT INTO samples VALUES (?, ?, ?, ?)', 
                               (timestamp, mid, tag, value))
                sensor_data[tag][mid] = value

# Log final simulation data
end_time = time.time()
total_simulation_time = end_time - start_time
print(f"Simulation completed in {total_simulation_time:.2f} seconds")
print(f"Total parts produced: {part_counter}")

# Finalize database connection
cursor.execute('INSERT OR REPLACE INTO ingest_watermark VALUES (?, ?)', 
               ('digital_twin_sim', datetime.utcnow()))
conn.commit()
conn.close()

print("Simulation data logged to database")
```