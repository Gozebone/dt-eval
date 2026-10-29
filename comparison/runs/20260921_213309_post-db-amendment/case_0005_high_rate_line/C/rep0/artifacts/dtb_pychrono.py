```python
import pychrono as chrono
import pychrono.irrlicht as irr
import math
import numpy as np
import json
import time
from datetime import datetime, timedelta
import sqlite3

# Initialize PyChrono system
chrono.SetChronoDataPath('/path/to/chrono/data')  # Adjust path as needed
system = chrono.ChSystemNSC()
system.Set_G_acc(chrono.ChVectorD(0, 0, 0))  # No gravity for this simulation

# Define constants
SIMULATION_TIME = 5 * 24 * 60 * 60  # 5 days in seconds
DT = 0.01  # Time step
LOG_INTERVAL = 1.0  # Log every second

# Database setup
conn = sqlite3.connect('digital_twin.db')
cursor = conn.cursor()

# Create tables if they don't exist
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
        name text NOT NULL
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS buffers (
        id text PRIMARY KEY,
        capacity int NOT NULL,
        before text NOT NULL,
        after text NOT NULL
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS stations (
        id text PRIMARY KEY,
        processing_time_s int NOT NULL,
        availability_pct double precision NOT NULL,
        mttr_s int NOT NULL,
        power_working_kw double precision NOT NULL,
        power_idle_kw double precision NOT NULL
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS tag_map (
        tag_id text PRIMARY KEY,
        machine_id text NOT NULL,
        signal text NOT NULL,
        unit text NOT NULL,
        register text NOT NULL,
        scale double precision NOT NULL
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS events (
        ts timestamptz NOT NULL,
        machine_id text NOT NULL,
        reason_code text NOT NULL,
        duration_s double precision NOT NULL,
        energy_kwh double precision NOT NULL
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS samples (
        ts timestamptz NOT NULL,
        machine_id text NOT NULL,
        tag text NOT NULL,
        value double precision NOT NULL
    )
''')

cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_events_machine_time ON events (machine_id, ts)
''')

cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_samples_machine_time ON samples (machine_id, ts)
''')

# Insert dimension data from requirements
machines_data = [
    ('M1', 'M1'), ('M2', 'M2'), ('M3', 'M3'), ('M4', 'M4'),
    ('B0', 'B0'), ('B1', 'B1'), ('B2', 'B2'), ('B3', 'B3')
]

stations_data = [
    ('M1', 60, 0.995, 300, 3.0, 0.3),
    ('M2', 80, 0.99, 600, 5.0, 0.5),
    ('M3', 70, 0.99, 600, 4.5, 0.45),
    ('M4', 75, 0.995, 300, 4.0, 0.4)
]

buffers_data = [
    ('B0', 25, 'source', 'M1'),
    ('B1', 10, 'M1', 'M2'),
    ('B2', 10, 'M2', 'M3'),
    ('B3', 10, 'M3', 'M4')
]

tag_map_data = [
    ('process_time_s', 'M1', 'process_time_s', 's', 'process_time_s', 1),
    ('availability', 'M1', 'availability', 'pct', 'availability', 1),
    ('mttr_s', 'M1', 'mttr_s', 's', 'mttr_s', 1),
    ('work_power_kw', 'M1', 'work_power_kw', 'kW', 'work_power_kw', 1),
    ('idle_power_kw', 'M1', 'idle_power_kw', 'kW', 'idle_power_kw', 1),
    ('capacity', 'M1', 'capacity', 'units', 'capacity', 1),
    ('process_time_s', 'M2', 'process_time_s', 's', 'process_time_s', 1),
    ('availability', 'M2', 'availability', 'pct', 'availability', 1),
    ('mttr_s', 'M2', 'mttr_s', 's', 'mttr_s', 1),
    ('work_power_kw', 'M2', 'work_power_kw', 'kW', 'work_power_kw', 1),
    ('idle_power_kw', 'M2', 'idle_power_kw', 'kW', 'idle_power_kw', 1),
    ('capacity', 'M2', 'capacity', 'units', 'capacity', 1),
    ('process_time_s', 'M3', 'process_time_s', 's', 'process_time_s', 1),
    ('availability', 'M3', 'availability', 'pct', 'availability', 1),
    ('mttr_s', 'M3', 'mttr_s', 's', 'mttr_s', 1),
    ('work_power_kw', 'M3', 'work_power_kw', 'kW', 'work_power_kw', 1),
    ('idle_power_kw', 'M3', 'idle_power_kw', 'kW', 'idle_power_kw', 1),
    ('capacity', 'M3', 'capacity', 'units', 'capacity', 1),
    ('process_time_s', 'M4', 'process_time_s', 's', 'process_time_s', 1),
    ('availability', 'M4', 'availability', 'pct', 'availability', 1),
    ('mttr_s', 'M4', 'mttr_s', 's', 'mttr_s', 1),
    ('work_power_kw', 'M4', 'work_power_kw', 'kW', 'work_power_kw', 1),
    ('idle_power_kw', 'M4', 'idle_power_kw', 'kW', 'idle_power_kw', 1),
    ('capacity', 'M4', 'capacity', 'units', 'capacity', 1)
]

cursor.executemany('INSERT OR REPLACE INTO machines VALUES (?, ?)', machines_data)
cursor.executemany('INSERT OR REPLACE INTO stations VALUES (?, ?, ?, ?, ?, ?)', stations_data)
cursor.executemany('INSERT OR REPLACE INTO buffers VALUES (?, ?, ?, ?)', buffers_data)
cursor.executemany('INSERT OR REPLACE INTO tag_map VALUES (?, ?, ?, ?, ?, ?)', tag_map_data)
conn.commit()

# Equipment parameters
machine_params = {
    'M1': {'processing_time_s': 60, 'availability_pct': 0.995, 'mttr_s': 300,
           'power_working_kw': 3.0, 'power_idle_kw': 0.3},
    'M2': {'processing_time_s': 80, 'availability_pct': 0.99, 'mttr_s': 600,
           'power_working_kw': 5.0, 'power_idle_kw': 0.5},
    'M3': {'processing_time_s': 70, 'availability_pct': 0.99, 'mttr_s': 600,
           'power_working_kw': 4.5, 'power_idle_kw': 0.45},
    'M4': {'processing_time_s': 75, 'availability_pct': 0.995, 'mttr_s': 300,
           'power_working_kw': 4.0, 'power_idle_kw': 0.4}
}

buffer_params = {
    'B0': {'capacity': 25, 'before': 'source', 'after': 'M1'},
    'B1': {'capacity': 10, 'before': 'M1', 'after': 'M2'},
    'B2': {'capacity': 10, 'before': 'M2', 'after': 'M3'},
    'B3': {'capacity': 10, 'before': 'M3', 'after': 'M4'}
}

# Create materials
steel_mat = chrono.ChMaterialSurfaceNSC()
steel_mat.SetFriction(0.5)
steel_mat.SetDampingF(0.1)
steel_mat.SetCompliance(1e-8)
steel_mat.SetComplianceT(1e-8)

# Create base body for simulation
ground = chrono.ChBodyEasyBox(10, 1, 10, 1000, True, True, steel_mat)
ground.SetPos(chrono.ChVectorD(0, -0.5, 0))
ground.SetFixed(True)
system.Add(ground)

# Create machines
machines = {}
for m_id, params in machine_params.items():
    # Create machine body (cube)
    machine_body = chrono.ChBodyEasyBox(2, 2, 2, 1000, True, True, steel_mat)
    machine_body.SetPos(chrono.ChVectorD(0, 1, 0))
    machine_body.SetFixed(False)
    system.Add(machine_body)
    machines[m_id] = {
        'body': machine_body,
        'params': params,
        'status': 'idle',  # idle, processing, failed
        'last_start_time': 0,
        'last_end_time': 0,
        'processing_start': 0,
        'energy_consumed': 0,
        'current_power': 0,
        'available': True,
        'failure_time': 0,
        'repair_time': 0
    }

# Create buffers
buffers = {}
for b_id, params in buffer_params.items():
    buffer_body = chrono.ChBodyEasyBox(3, 0.5, 3, 100, True, True, steel_mat)
    buffer_body.SetPos(chrono.ChVectorD(0, 0.5, 0))
    buffer_body.SetFixed(True)
    system.Add(buffer_body)
    buffers[b_id] = {
        'body': buffer_body,
        'params': params,
        'items': 0
    }

# Connect machines and buffers in serial topology
# M1 -> B1 -> M2 -> B2 -> M3 -> B3 -> M4
# Buffer B0 is before M1

# Position machines
positions = [
    chrono.ChVectorD(-8, 1, 0),  # M1
    chrono.ChVectorD(-4, 1, 0),  # M2
    chrono.ChVectorD(0, 1, 0),   # M3
    chrono.ChVectorD(4, 1, 0)    # M4
]

for i, m_id in enumerate(['M1', 'M2', 'M3', 'M4']):
    machines[m_id]['body'].SetPos(positions[i])

# Position buffers
buffer_positions = [
    chrono.ChVectorD(-6, 0.5, 0),  # B1
    chrono.ChVectorD(-2, 0.5, 0),  # B2
    chrono.ChVectorD(2, 0.5, 0),   # B3
]

for i, b_id in enumerate(['B1', 'B2', 'B3']):
    buffers[b_id]['body'].SetPos(buffer_positions[i])

# Create source for parts
source_part = chrono.ChBodyEasyBox(0.5, 0.5, 0.5, 100, True, True, steel_mat)
source_part.SetPos(chrono.ChVectorD(-10, 1, 0))
source_part.SetFixed(True)
system.Add(source_part)

# Create the part source (arrivals)
inter_arrival_time = 45.0  # seconds
last_arrival = 0
part_count = 0

# Create sensors for each machine
sensors = {}

# Log initial data
timestamp = datetime.now()
for m_id in ['M1', 'M2', 'M3', 'M4']:
    sensors[m_id] = {
        'process_time_s': machine_params[m_id]['processing_time_s'],
        'availability': machine_params[m_id]['availability_pct'],
        'mttr_s': machine_params[m_id]['mttr_s'],
        'work_power_kw': machine_params[m_id]['power_working_kw'],
        'idle_power_kw': machine_params[m_id]['power_idle_kw'],
        'capacity': buffer_params[f'B{int(m_id[1])-1}']['capacity'] if m_id[1].isdigit() else 0
    }
    
    # Log initial sample data
    for tag, value in sensors[m_id].items():
        cursor.execute('''
            INSERT INTO samples VALUES (?, ?, ?, ?)
        ''', (timestamp, m_id, tag, value))
        
conn.commit()

# Simulation loop
start_time = time.time()
current_time = 0
log_time = 0

# Initialize machine states
for m_id in machines:
    machines[m_id]['available'] = True

while current_time < SIMULATION_TIME:
    # Step the system
    system.DoStepDynamics(DT)
    current_time += DT
    
    # Handle arrivals
    if current_time - last_arrival >= inter_arrival_time