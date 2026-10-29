```python
import pychrono as chrono
import pychrono.irrlicht as irr
import math
import numpy as np
import time
import json
from datetime import datetime, timedelta
import sqlite3
import os

# Initialize PyChrono system
chrono.SetChronoDataPath(os.path.join(os.path.dirname(__file__), 'chrono_data'))

# Create the physical system
system = chrono.ChSystemNSC()
system.Set_G_acc(chrono.ChVectorD(0, 0, 0))  # No gravity for this simulation

# Create a ground body (terrain)
ground = chrono.ChBody()
ground.SetBodyFixed(True)
ground.SetPos(chrono.ChVectorD(0, -1, 0))
system.Add(ground)

# Create a visualization environment
vis = irr.ChVisualSystemIrrlicht()
vis.AttachSystem(system)
vis.SetWindowSize(1024, 768)
vis.SetWindowTitle('Production Line Simulation')
vis.Initialize()
vis.AddSkyBox()
vis.AddLogo()
vis.AddCamera(chrono.ChVectorD(0, 5, 10), chrono.ChVectorD(0, 0, 0))
vis.AddTypicalLights()

# Define equipment parameters from requirements
machines_data = {
    'M1': {
        'process_time_s': 150,
        'availability': 0.98,
        'mttr_s': 600,
        'work_power_kw': 4.0,
        'idle_power_kw': 0.4
    },
    'M2': {
        'process_time_s': 120,
        'availability': 0.97,
        'mttr_s': 900,
        'work_power_kw': 5.0,
        'idle_power_kw': 0.5
    },
    'M3': {
        'process_time_s': 180,
        'availability': 0.95,
        'mttr_s': 1200,
        'work_power_kw': 6.0,
        'idle_power_kw': 0.6
    },
    'M4': {
        'process_time_s': 120,
        'availability': 0.97,
        'mttr_s': 900,
        'work_power_kw': 5.0,
        'idle_power_kw': 0.5
    },
    'M5': {
        'process_time_s': 150,
        'availability': 0.98,
        'mttr_s': 600,
        'work_power_kw': 4.0,
        'idle_power_kw': 0.4
    }
}

buffers_data = {
    'B0': {'capacity': 20, 'before': 'source', 'after': 'M1'},
    'B1': {'capacity': 8, 'before': 'M1', 'after': 'M2'},
    'B2': {'capacity': 8, 'before': 'M2', 'after': 'M3'},
    'B3': {'capacity': 8, 'before': 'M3', 'after': 'M4'},
    'B4': {'capacity': 8, 'before': 'M4', 'after': 'M5'}
}

# Create machines as bodies with properties
machines = {}
for machine_id, params in machines_data.items():
    # Create a body for the machine
    machine_body = chrono.ChBody()
    machine_body.SetPos(chrono.ChVectorD(0, 0, 0))
    machine_body.SetMass(1000)
    machine_body.SetInertiaXX(chrono.ChVectorD(100, 100, 100))
    system.Add(machine_body)
    
    # Create a visualization shape
    machine_shape = chrono.ChVisualShapeBox(1, 1, 1)
    machine_shape.SetColor(chrono.ChColor(0.8, 0.2, 0.2))
    machine_body.AddVisualShape(machine_shape, chrono.ChFramed())
    
    machines[machine_id] = {
        'body': machine_body,
        'params': params,
        'status': 'idle',  # idle or working
        'processing_start': 0,
        'power_state': 'idle',
        'power_kw': params['idle_power_kw'],
        'next_failure_time': 0,
        'last_failure_start': 0
    }

# Create buffers as simple empty containers
buffers = {}
for buffer_id, params in buffers_data.items():
    buffers[buffer_id] = {
        'count': 0,
        'capacity': params['capacity'],
        'before': params['before'],
        'after': params['after']
    }

# Create a source that generates items at specified intervals
source_interval = 130  # seconds
last_source_time = 0

# Initialize sensors (we'll track these in a dictionary)
sensors = {tag: [] for tag in [
    'inter_arrival_s', 'M1', 'M2', 'M3', 'M4', 'M5',
    'B0', 'B1', 'B2', 'B3', 'B4'
]}

# Create database connection
conn = sqlite3.connect('digital_twin.db')
cursor = conn.cursor()

# Create tables as per schema
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
        capacity INTEGER,
        before TEXT,
        after TEXT
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
    CREATE TABLE IF NOT EXISTS tag_map (
        tag_id TEXT PRIMARY KEY,
        machine_id TEXT,
        signal TEXT,
        unit TEXT,
        register TEXT,
        scale DOUBLE PRECISION
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS raw_ingest (
        ingested_at TIMESTAMPTZ NOT NULL,
        source TEXT NOT NULL,
        payload JSONB NOT NULL
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS ingest_watermark (
        source TEXT PRIMARY KEY,
        max_event_ts TIMESTAMPTZ
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS events (
        ts TIMESTAMPTZ NOT NULL,
        machine_id TEXT NOT NULL,
        reason_code TEXT,
        duration_s DOUBLE PRECISION,
        energy_kwh DOUBLE PRECISION
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS samples (
        ts TIMESTAMPTZ NOT NULL,
        machine_id TEXT NOT NULL,
        tag TEXT NOT NULL,
        value DOUBLE PRECISION
    )
''')

# Populate initial data in the database
for machine_id, params in machines_data.items():
    cursor.execute('''
        INSERT OR REPLACE INTO machines 
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        machine_id,
        params['process_time_s'],
        params['availability'],
        params['mttr_s'],
        params['work_power_kw'],
        params['idle_power_kw']
    ))

for buffer_id, params in buffers_data.items():
    cursor.execute('''
        INSERT OR REPLACE INTO buffers 
        VALUES (?, ?, ?, ?)
    ''', (
        buffer_id,
        params['capacity'],
        params['before'],
        params['after']
    ))

for machine_id, params in machines_data.items():
    cursor.execute('''
        INSERT OR REPLACE INTO stations 
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        machine_id,
        params['process_time_s'],
        params['availability'],
        params['mttr_s'],
        params['work_power_kw'],
        params['idle_power_kw']
    ))

# Add tag map entries
tag_map_entries = [
    ('inter_arrival_s', None, 'inter_arrival_s', 's', 'inter_arrival_s', 1.0),
    ('M1', 'M1', 'M1', 's', 'M1', 1.0),
    ('M2', 'M2', 'M2', 's', 'M2', 1.0),
    ('M3', 'M3', 'M3', 's', 'M3', 1.0),
    ('M4', 'M4', 'M4', 's', 'M4', 1.0),
    ('M5', 'M5', 'M5', 's', 'M5', 1.0),
    ('B0', None, 'B0', 'count', 'B0', 1.0),
    ('B1', None, 'B1', 'count', 'B1', 1.0),
    ('B2', None, 'B2', 'count', 'B2', 1.0),
    ('B3', None, 'B3', 'count', 'B3', 1.0),
    ('B4', None, 'B4', 'count', 'B4', 1.0)
]

for entry in tag_map_entries:
    cursor.execute('''
        INSERT OR REPLACE INTO tag_map 
        VALUES (?, ?, ?, ?, ?, ?)
    ''', entry)

conn.commit()

# Simulation parameters
simulation_time = 432000  # 5 days in seconds
dt = 0.01  # Time step
current_time = 0

# Track processing times and failures
machine_processing_times = {id: [] for id in machines_data.keys()}
machine_failures = {id: [] for id in machines_data.keys()}

# Track energy consumption
total_energy_kwh = 0

# Simulation loop
last_visualization_time = 0
last_buffer_update = 0
inter_arrival_times = []

print("Starting simulation...")

while current_time < simulation_time:
    # Step the simulation
    system.DoStepDynamics(dt)
    current_time += dt
    
    # Update visualization every 1 second
    if current_time - last_visualization_time >= 1.0:
        vis.Run()
        vis.BeginScene()
        vis.Render()
        vis.EndScene()
        last_visualization_time = current_time
    
    # Generate new items at the source
    if current_time - last_source_time >= source_interval:
        # Add an item to buffer B0
        buffers['B0']['count'] += 1
        inter_arrival_times.append(source_interval)
        last_source_time = current_time
    
    # Process items through the line
    # Check if there's an item in B0 to move to M1
    if buffers['B0']['count'] > 0 and machines['M1']['status'] == 'idle':
        # Move item to M1
        buffers['B0']['count'] -= 1
        machines['M1']['status'] = 'working'
        machines['M1']['processing_start'] = current_time
        machines['M1']['power_state'] = 'working'
        machines['M1']['power_kw'] = machines['M1']['params']['work_power_kw']
    
    # Check each machine's status and process items
    for machine_id in ['M1', 'M2', 'M3', 'M4', 'M5']:
        if machines[machine_id]['status'] == 'working':
            # Check if processing is complete
            processing_time = current_time - machines[machine_id]['processing_start']
            if processing_time >= machines[machine_id]['params']['process_time_s']:
                # Processing complete
                machines[machine_id]['status'] = 'idle'
                machines[machine_id]['power_state'] = 'idle'
                machines[machine_id]['power_kw'] = machines[machine_id]['params']['idle_power_kw']
                
                # Record processing time
                machine_processing_times[machine_id].append(processing_time)
                
                # Move item to next buffer
                if machine_id == 'M1':
                    buffer_id = 'B1'
                elif machine_id == 'M2':
                    buffer_id = 'B2'
                elif machine_id == 'M3':
                    buffer_id = 'B3'
                elif machine_id == 'M4':
                    buffer_id = 'B4'
                else:
                    # M5 is the last station - no buffer after it
                    continue
                
                # Add to next buffer if space available
                if buffers[buffer_id]['count'] < buffers[buffer_id]['capacity']:
                    buffers[buffer_id]['count'] += 1
    
    # Monitor power consumption and energy
    for machine_id in machines_data.keys():
        power_kw = machines[machine_id]['power_kw']
        # Convert to kWh
        energy_kwh = (power_kw * dt) / 3600.0
        total_energy_kwh += energy_kwh
    
    # Check for failure events based on availability
    for machine_id in machines_data.keys():
        machine = machines[machine_id]
        if machine['status'] == 'idle':
            # Check if failure occurs
            if machine['next_failure_time'] == 0:
                # Determine when next failure might occur
                # Using the reliability model: work = availability, MTTR = mean time to repair
                # For simplicity, we'll just use a Poisson process
                if np.random.random() < (1 - machine['params']['availability']) * dt:
                    machine['status'] = 'failed'
                    machine['next_failure_time'] = current_time + np.random.exponential(machine['params']['mttr_s'])
                    machine['last_failure_start'] = current_time
                    machine['power_state'] = 'failed'
                    machine['power_kw'] = 0
                    # Record failure event
                    cursor.execute('''
                        INSERT INTO events (ts, machine_id, reason_code, duration