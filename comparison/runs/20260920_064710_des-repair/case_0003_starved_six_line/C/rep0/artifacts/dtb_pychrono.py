```python
import numpy as np
import pychrono as chrono
import pychrono.irrlicht as chronoirr
import json
import time
from datetime import datetime, timedelta
import sqlite3

# Initialize PyChrono system
chrono.SetChronoDataPath('path_to_chrono_data')  # Adjust to your Chrono data path
system = chrono.ChSystemNSC()
system.Set_G_acc(chrono.ChVectorD(0, -9.81, 0))  # Set gravity

# Define materials
material_steel = chrono.ChMaterialSurfaceNSC()
material_steel.SetFriction(0.4)
material_steel.SetRestitution(0.1)

material_refractory = chrono.ChMaterialSurfaceNSC()
material_refractory.SetFriction(0.3)
material_refractory.SetRestitution(0.05)

# Create a database connection for logging
conn = sqlite3.connect('digital_twin.db')
cursor = conn.cursor()

# Create tables as per schema
cursor.execute('''CREATE TABLE IF NOT EXISTS tag_map (
    tag_id TEXT PRIMARY KEY,
    machine_id TEXT,
    signal TEXT,
    unit TEXT,
    register TEXT,
    scale DOUBLE PRECISION
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS machines (
    id TEXT PRIMARY KEY,
    process_time_s DOUBLE PRECISION,
    availability DOUBLE PRECISION,
    mttr_s DOUBLE PRECISION,
    work_power_kw DOUBLE PRECISION,
    idle_power_kw DOUBLE PRECISION
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS buffers (
    id TEXT PRIMARY KEY,
    capacity INTEGER
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS stations (
    id TEXT PRIMARY KEY,
    processing_time_s DOUBLE PRECISION,
    availability DOUBLE PRECISION,
    mttr_s DOUBLE PRECISION,
    work_power_kw DOUBLE PRECISION,
    idle_power_kw DOUBLE PRECISION
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

# Create indexes
cursor.execute('''CREATE INDEX IF NOT EXISTS idx_events_machine_id_ts ON events (machine_id, ts)''')
cursor.execute('''CREATE INDEX IF NOT EXISTS idx_samples_machine_id_ts ON samples (machine_id, ts)''')

# Define equipment data from requirements
equipment_data = {
    "M1": {
        "process_time_s": 200,
        "availability": 0.97,
        "mttr_s": 900,
        "work_power_kw": 5.0,
        "idle_power_kw": 0.5
    },
    "M2": {
        "process_time_s": 220,
        "availability": 0.97,
        "mttr_s": 1000,
        "work_power_kw": 5.5,
        "idle_power_kw": 0.55
    },
    "M3": {
        "process_time_s": 240,
        "availability": 0.96,
        "mttr_s": 1200,
        "work_power_kw": 6.0,
        "idle_power_kw": 0.6
    },
    "M4": {
        "process_time_s": 260,
        "availability": 0.96,
        "mttr_s": 1400,
        "work_power_kw": 7.0,
        "idle_power_kw": 0.7
    },
    "M5": {
        "process_time_s": 230,
        "availability": 0.97,
        "mttr_s": 1100,
        "work_power_kw": 6.5,
        "idle_power_kw": 0.65
    },
    "M6": {
        "process_time_s": 210,
        "availability": 0.97,
        "mttr_s": 1000,
        "work_power_kw": 6.0,
        "idle_power_kw": 0.6
    },
    "B0": {
        "capacity": 10
    },
    "B1": {
        "capacity": 10
    },
    "B2": {
        "capacity": 10
    },
    "B3": {
        "capacity": 10
    },
    "B4": {
        "capacity": 10
    },
    "B5": {
        "capacity": 10
    }
}

# Insert data into database
for machine_id, data in equipment_data.items():
    if machine_id.startswith('M'):
        cursor.execute('''INSERT OR REPLACE INTO machines 
                         (id, process_time_s, availability, mttr_s, work_power_kw, idle_power_kw) 
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (machine_id, data["process_time_s"], data["availability"], 
                       data["mttr_s"], data["work_power_kw"], data["idle_power_kw"]))
    else:
        cursor.execute('''INSERT OR REPLACE INTO buffers 
                         (id, capacity) 
                         VALUES (?, ?)''',
                      (machine_id, data["capacity"]))

    cursor.execute('''INSERT OR REPLACE INTO stations 
                     (id, processing_time_s, availability, mttr_s, work_power_kw, idle_power_kw) 
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (machine_id, data["process_time_s"], data["availability"], 
                   data["mttr_s"], data["work_power_kw"], data["idle_power_kw"]))

# Insert tag mappings
tag_mappings = [
    ("M1_process_time", "M1", "processing_time_s", "s", "0x0001", 1.0),
    ("M1_availability", "M1", "availability", "", "0x0002", 1.0),
    ("M1_mttr", "M1", "mttr_s", "s", "0x0003", 1.0),
    ("M1_work_power", "M1", "work_power_kw", "kW", "0x0004", 1.0),
    ("M1_idle_power", "M1", "idle_power_kw", "kW", "0x0005", 1.0),
    ("B0_capacity", "B0", "buffer_capacity", "", "0x0006", 1.0),
    ("B1_capacity", "B1", "buffer_capacity", "", "0x0007", 1.0),
    ("B2_capacity", "B2", "buffer_capacity", "", "0x0008", 1.0),
    ("B3_capacity", "B3", "buffer_capacity", "", "0x0009", 1.0),
    ("B4_capacity", "B4", "buffer_capacity", "", "0x000A", 1.0),
    ("B5_capacity", "B5", "buffer_capacity", "", "0x000B", 1.0)
]

for tag_id, machine_id, signal, unit, register, scale in tag_mappings:
    cursor.execute('''INSERT OR REPLACE INTO tag_map 
                     (tag_id, machine_id, signal, unit, register, scale) 
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (tag_id, machine_id, signal, unit, register, scale))

conn.commit()

# Create equipment objects
machines = {}
buffers = {}

# Create machine bodies
for machine_id in ['M1', 'M2', 'M3', 'M4', 'M5', 'M6']:
    # Create rigid body for machine
    machine_body = chrono.ChBody()
    machine_body.SetMass(1000)
    machine_body.SetInertiaXX(chrono.ChVectorD(100, 100, 100))
    machine_body.SetPos(chrono.ChVectorD(0, 0, 0))
    machine_body.SetMaterialSurface(material_steel)
    system.AddBody(machine_body)
    
    # Store in dictionary
    machines[machine_id] = {
        'body': machine_body,
        'state': 'idle',  # idle or processing
        'process_start_time': 0,
        'process_duration': equipment_data[machine_id]["process_time_s"],
        'power_kW': equipment_data[machine_id]["idle_power_kw"],
        'availability': equipment_data[machine_id]["availability"],
        'mttr_s': equipment_data[machine_id]["mttr_s"]
    }

# Create buffer bodies
for buffer_id in ['B0', 'B1', 'B2', 'B3', 'B4', 'B5']:
    # Create rigid body for buffer
    buffer_body = chrono.ChBody()
    buffer_body.SetMass(100)
    buffer_body.SetInertiaXX(chrono.ChVectorD(10, 10, 10))
    buffer_body.SetPos(chrono.ChVectorD(0, 0, 0))
    buffer_body.SetMaterialSurface(material_refractory)
    system.AddBody(buffer_body)
    
    # Store in dictionary
    buffers[buffer_id] = {
        'body': buffer_body,
        'capacity': equipment_data[buffer_id]["capacity"],
        'contents': []
    }

# Define source object (input)
source_body = chrono.ChBody()
source_body.SetMass(100)
source_body.SetInertiaXX(chrono.ChVectorD(10, 10, 10))
source_body.SetPos(chrono.ChVectorD(0, 0, 0))
source_body.SetMaterialSurface(material_steel)
system.AddBody(source_body)

# Define inter-arrival time (300 seconds)
inter_arrival_time = 300.0  # seconds
last_arrival = 0
last_event_time = 0

# Simulation parameters
simulation_duration = 432000  # 5 days in seconds
time_step = 0.01  # seconds
current_time = 0

# Create Irrlicht visualization
vis = chronoirr.ChVisualSystemIrrlicht()
vis.AttachSystem(system)
vis.SetWindowSize(1024, 768)
vis.SetWindowTitle('Digital Twin Production Line')
vis.Initialize()
vis.AddLogo()
vis.AddSkyBox()
vis.AddCamera(chrono.ChVectorD(5, 5, 5), chrono.ChVectorD(0, 0, 0))
vis.AddTypicalLights()

# Simulation loop
while current_time < simulation_duration:
    # Check for new item arrival at source
    if current_time - last_arrival >= inter_arrival_time:
        # Simulate item arriving at source
        last_arrival = current_time
        # Add item to source buffer
        if 'source_item' not in locals():
            source_item = chrono.ChBody()
            source_item.SetMass(10)
            source_item.SetInertiaXX(chrono.ChVectorD(1, 1, 1))
            source_item.SetPos(chrono.ChVectorD(0, 0, 0))
            source_item.SetMaterialSurface(material_steel)
            system.AddBody(source_item)
            # Assign to buffer B0
            if 'B0' in buffers:
                buffers['B0']['contents'].append(source_item)
    
    # Process machines (simple state machine)
    for machine_id in ['M1', 'M2', 'M3', 'M4', 'M5', 'M6']:
        machine = machines[machine_id]
        if machine['state'] == 'idle':
            # Check if we can start processing
            buffer_id = 'B0' if machine_id == 'M1' else f'B{ord(machine_id[1]) - ord("1")}'
            if buffer_id in buffers and buffers[buffer_id]['contents']:
                # Start processing
                machine['state'] = 'processing'
                machine['process_start_time'] = current_time
                # Remove item from buffer
                item = buffers[buffer_id]['contents'].pop(0)
                if hasattr(item, 'SetBody'):
                    system.RemoveBody(item)
                machine['power_kW'] = equipment_data[machine_id]["work_power_kw"]
        elif machine['state'] == 'processing':
            # Check if processing is complete
            if current_time - machine['process_start_time'] >= machine['process_duration']:
                # Finish processing
                machine['state'] = 'idle'
                machine['power_kW'] = equipment_data[machine_id]["idle_power_kw"]
                # Move item to next buffer
                if machine_id != 'M6':
                    next_buffer_id = f'B{ord(machine_id[1]) - ord("1") + 1}'
                    if next_buffer_id in buffers and len(buffers[next_buffer_id]['contents']) < buffers[next_buffer_id]['capacity']:
                        # Re-add item to next buffer
                        buffers[next_buffer_id]['contents'].append(item)
    
    # Collect sensor data and log to database
    timestamp = datetime.now()
    for machine_id in ['M1', 'M2', 'M3', 'M4', 'M5', 'M6']:
        machine = machines[machine_id]
        # Log samples
        cursor.execute('''INSERT INTO samples (ts, machine_id, tag, value) VALUES (?, ?, ?, ?)''',
                      (timestamp, machine_id, "processing_time_s", machine['process_duration']))
        cursor.execute('''INSERT INTO samples (ts, machine_id, tag, value) VALUES (?,