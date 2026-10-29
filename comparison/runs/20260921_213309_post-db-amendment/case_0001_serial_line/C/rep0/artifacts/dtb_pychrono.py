import pychrono as chrono
import pychrono.irrlicht as chronoirr
import numpy as np
import time
import json
import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict

# Initialize PyChrono system
chrono.SetChronoDataPath('/path/to/chrono/data')  # Adjust path as needed
system = chrono.ChSystemNSC()
system.SetGravitationalAcceleration(chrono.ChVectorD(0, 0, 0))  # No gravity for this simulation

# Create database connection
conn = sqlite3.connect('digital_twin.db')
cursor = conn.cursor()

# Create tables if they don't exist
cursor.execute('''CREATE TABLE IF NOT EXISTS machines (
    id TEXT PRIMARY KEY,
    process_time_s DOUBLE PRECISION,
    availability DOUBLE PRECISION,
    mttr_s DOUBLE PRECISION
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS buffers (
    id TEXT PRIMARY KEY,
    capacity INTEGER
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS stations (
    id TEXT PRIMARY KEY,
    processing_time_s DOUBLE PRECISION,
    availability_pct DOUBLE PRECISION,
    mttr_s DOUBLE PRECISION,
    power_working_kw DOUBLE PRECISION,
    power_idle_kw DOUBLE PRECISION
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS tag_map (
    tag_id TEXT PRIMARY KEY,
    machine_id TEXT,
    signal TEXT,
    unit TEXT,
    register TEXT,
    scale DOUBLE PRECISION
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS raw_ingest (
    ingested_at TIMESTAMPTZ PRIMARY KEY,
    source TEXT,
    payload JSONB
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS events (
    ts TIMESTAMPTZ,
    machine_id TEXT,
    reason_code TEXT,
    duration_s DOUBLE PRECISION,
    energy_kwh DOUBLE PRECISION,
    PRIMARY KEY (ts, machine_id)
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS samples (
    ts TIMESTAMPTZ,
    machine_id TEXT,
    tag TEXT,
    value DOUBLE PRECISION,
    PRIMARY KEY (ts, machine_id, tag)
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS ingest_watermark (
    source TEXT PRIMARY KEY,
    max_event_ts TIMESTAMPTZ
)''')

# Create indexes
cursor.execute('''CREATE INDEX IF NOT EXISTS idx_events_machine_id_ts ON events (machine_id, ts)''')
cursor.execute('''CREATE INDEX IF NOT EXISTS idx_samples_machine_id_ts ON samples (machine_id, ts)''')

# Insert static data
machines_data = [
    ('M1', 150, 0.98, 600),
    ('M2', 120, 0.97, 900),
    ('M3', 180, 0.95, 1200),
    ('M4', 120, 0.97, 900),
    ('M5', 150, 0.98, 600)
]

buffers_data = [
    ('B0', 20),
    ('B1', 8),
    ('B2', 8),
    ('B3', 8),
    ('B4', 8)
]

stations_data = [
    ('M1', 150, 99.45, 793.67, 4.0, 0.4),
    ('M2', 120, 96.86, 1053.95, 5.0, 0.5),
    ('M3', 180, 99.03, 4200.65, 6.0, 0.6),
    ('M4', 120, 97.39, 1894.81, 5.0, 0.5),
    ('M5', 150, 99.56, 641.17, 4.0, 0.4)
]

tag_map_data = [
    ('machines', 'M1', 'process_time', 's', 'process_time', 1.0),
    ('machines', 'M2', 'process_time', 's', 'process_time', 1.0),
    ('machines', 'M3', 'process_time', 's', 'process_time', 1.0),
    ('machines', 'M4', 'process_time', 's', 'process_time', 1.0),
    ('machines', 'M5', 'process_time', 's', 'process_time', 1.0),
    ('machines', 'M1', 'availability', '%', 'availability', 1.0),
    ('machines', 'M2', 'availability', '%', 'availability', 1.0),
    ('machines', 'M3', 'availability', '%', 'availability', 1.0),
    ('machines', 'M4', 'availability', '%', 'availability', 1.0),
    ('machines', 'M5', 'availability', '%', 'availability', 1.0),
    ('machines', 'M1', 'mttr', 's', 'mttr', 1.0),
    ('machines', 'M2', 'mttr', 's', 'mttr', 1.0),
    ('machines', 'M3', 'mttr', 's', 'mttr', 1.0),
    ('machines', 'M4', 'mttr', 's', 'mttr', 1.0),
    ('machines', 'M5', 'mttr', 's', 'mttr', 1.0),
    ('buffers', 'B0', 'capacity', 'units', 'capacity', 1.0),
    ('buffers', 'B1', 'capacity', 'units', 'capacity', 1.0),
    ('buffers', 'B2', 'capacity', 'units', 'capacity', 1.0),
    ('buffers', 'B3', 'capacity', 'units', 'capacity', 1.0),
    ('buffers', 'B4', 'capacity', 'units', 'capacity', 1.0)
]

cursor.executemany('INSERT OR REPLACE INTO machines VALUES (?, ?, ?, ?)', machines_data)
cursor.executemany('INSERT OR REPLACE INTO buffers VALUES (?, ?)', buffers_data)
cursor.executemany('INSERT OR REPLACE INTO stations VALUES (?, ?, ?, ?, ?, ?)', stations_data)
cursor.executemany('INSERT OR REPLACE INTO tag_map VALUES (?, ?, ?, ?, ?, ?)', tag_map_data)
conn.commit()

# Define equipment parameters
machine_params = {
    'M1': {'process_time_s': 150, 'availability': 0.98, 'mttr_s': 600, 'power_working_kw': 4.0, 'power_idle_kw': 0.4},
    'M2': {'process_time_s': 120, 'availability': 0.97, 'mttr_s': 900, 'power_working_kw': 5.0, 'power_idle_kw': 0.5},
    'M3': {'process_time_s': 180, 'availability': 0.95, 'mttr_s': 1200, 'power_working_kw': 6.0, 'power_idle_kw': 0.6},
    'M4': {'process_time_s': 120, 'availability': 0.97, 'mttr_s': 900, 'power_working_kw': 5.0, 'power_idle_kw': 0.5},
    'M5': {'process_time_s': 150, 'availability': 0.98, 'mttr_s': 600, 'power_working_kw': 4.0, 'power_idle_kw': 0.4}
}

buffer_params = {
    'B0': {'capacity': 20},
    'B1': {'capacity': 8},
    'B2': {'capacity': 8},
    'B3': {'capacity': 8},
    'B4': {'capacity': 8}
}

# Create materials
steel_material = chrono.ChMaterialSurfaceNSC()
steel_material.SetFriction(0.6)
steel_material.SetRestitution(0.1)

refractory_material = chrono.ChMaterialSurfaceNSC()
refractory_material.SetFriction(0.4)
refractory_material.SetRestitution(0.05)

# Create bodies for equipment
bodies = {}
joints = {}

# Create source (item generator)
source_body = chrono.ChBodyEasyBox(0.5, 0.5, 0.5, 1000, True, True)
source_body.SetPos(chrono.ChVectorD(0, 0, 0))
source_body.SetMaterialSurface(steel_material)
system.Add(source_body)

# Create machines
machine_positions = {
    'M1': chrono.ChVectorD(2, 0, 0),
    'M2': chrono.ChVectorD(5, 0, 0),
    'M3': chrono.ChVectorD(8, 0, 0),
    'M4': chrono.ChVectorD(11, 0, 0),
    'M5': chrono.ChVectorD(14, 0, 0)
}

for machine_id, pos in machine_positions.items():
    machine_body = chrono.ChBodyEasyBox(2, 1, 1, 1000, True, True)
    machine_body.SetPos(pos)
    machine_body.SetMaterialSurface(steel_material)
    machine_body.SetIdentifier(machine_id)
    system.Add(machine_body)
    bodies[machine_id] = machine_body

# Create buffers
buffer_positions = {
    'B0': chrono.ChVectorD(1.5, 0, 3),
    'B1': chrono.ChVectorD(4.5, 0, 3),
    'B2': chrono.ChVectorD(7.5, 0, 3),
    'B3': chrono.ChVectorD(10.5, 0, 3),
    'B4': chrono.ChVectorD(13.5, 0, 3)
}

for buffer_id, pos in buffer_positions.items():
    buffer_body = chrono.ChBodyEasyBox(2, 1, 1, 1000, True, True)
    buffer_body.SetPos(pos)
    buffer_body.SetMaterialSurface(steel_material)
    buffer_body.SetIdentifier(buffer_id)
    system.Add(buffer_body)
    bodies[buffer_id] = buffer_body

# Create sink
sink_body = chrono.ChBodyEasyBox(0.5, 0.5, 0.5, 1000, True, True)
sink_body.SetPos(chrono.ChVectorD(16, 0, 0))
sink_body.SetMaterialSurface(steel_material)
system.Add(sink_body)

# Create constraints between machines and buffers
# This is a simplified model - in a real application, these would be more complex
# For now, we'll simulate the production line behavior using time-based logic

# Track simulation and machine states
machine_states = {machine_id: {'active': False, 'start_time': 0, 'processing_time': params['process_time_s'], 'available': True} 
                  for machine_id, params in machine_params.items()}

buffer_states = {buffer_id: {'items': 0, 'capacity': params['capacity']} 
                 for buffer_id, params in buffer_params.items()}

# Simulate production line
def simulate_production_line(sim_time):
    global machine_states, buffer_states
    
    # Log initial sensor readings
    log_sensor_data(sim_time)
    
    # Simulate item generation (source)
    if sim_time % 130 < 1:  # Approximate inter-arrival time of 130s
        item = 'item_' + str(sim_time)
        # Log item generation event
        log_event(sim_time, 'source', 'item_generated', 0, 0)
        # Update buffer B0
        buffer_states['B0']['items'] = min(buffer_states['B0']['items'] + 1, buffer_states['B0']['capacity'])
    
    # Process items through the line
    for i, machine_id in enumerate(['M1', 'M2', 'M3', 'M4', 'M5']):
        current_buffer = 'B' + str(i)
        next_buffer = 'B' + str(i+1) if i < 4 else 'sink'
        
        # Check if machine can start processing
        if (machine_states[machine_id]['available'] and 
            buffer_states[current_buffer]['items'] > 0):
            
            # Start processing
            if not machine_states[machine_id]['active']:
                machine_states[machine_id]['active'] = True
                machine_states[machine_id]['start_time'] = sim_time
                buffer_states[current_buffer]['items'] -= 1
                log_event(sim_time, machine_id, 'processing_started', 0, 0)
            
            # Check if processing is complete
            if sim_time - machine_states[machine_id]['start_time'] >= machine_states[machine_id]['processing_time']:
                machine_states[machine_id]['active'] = False
                machine_states[machine_id]['available'] = True
                
                # Move item to next buffer or sink
                if i == 4:  # Last station - sink
                    log_event(sim_time, machine_id, 'processing_completed', 0, 0)
                else:
                    # Move to next buffer
                    if buffer_states[next_buffer]['items'] < buffer_states[next_buffer]['capacity']:
                        buffer_states[next_buffer]['items'] += 1
                        log_event(sim_time, machine_id, 'item_moved', 0, 0)
                
                # Log processing completion
                log_event(sim_time, machine