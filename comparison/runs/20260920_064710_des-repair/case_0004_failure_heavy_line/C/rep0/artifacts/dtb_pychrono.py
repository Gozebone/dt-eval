```python
import pychrono as chrono
import pychrono.core as core
import pychrono.fea as fea
import pychrono.irrlicht as irr
import pychrono.vehicle as vehicle
import math
import time
import json
import datetime
import sqlite3
import numpy as np

# Initialize PyChrono system
chrono.SetChronoDataPath("../../../data/")
chrono.SetChronoDataPath("../../../data/")

# Create the simulation system
system = chrono.ChSystemNSC()

# Set gravity
system.SetGravitationalAcceleration(chrono.ChVectorD(0, -9.81, 0))

# Create ground body
ground = chrono.ChBody()
ground.SetBodyFixed(True)
ground.SetPos(chrono.ChVectorD(0, -1, 0))
system.Add(ground)

# Create material properties
steel_mat = chrono.ChMaterialSurfaceNSC()
steel_mat.SetFriction(0.5)
steel_mat.SetRestitution(0.1)

# Create a simple part that will move through the production line
part = chrono.ChBody()
part.SetMass(1.0)
part.SetInertiaXX(chrono.ChVectorD(0.1, 0.1, 0.1))
part.SetPos(chrono.ChVectorD(0, 0, 0))
part.GetCollisionModel().ClearModel()
part.GetCollisionModel().AddBox(0.2, 0.2, 0.2)
part.SetMaterialSurface(steel_mat)
system.Add(part)

# Create machines with their parameters
machine_params = {
    'M1': {'processing_time_s': 100, 'availability': 0.9258, 'mttr_s': 3206.25, 'power_working_kw': 4.0, 'power_idle_kw': 0.4},
    'M2': {'processing_time_s': 130, 'availability': 0.9736, 'mttr_s': 2859.26, 'power_working_kw': 5.0, 'power_idle_kw': 0.5},
    'M3': {'processing_time_s': 90, 'availability': 0.9469, 'mttr_s': 2882.82, 'power_working_kw': 4.5, 'power_idle_kw': 0.45},
    'M4': {'processing_time_s': 140, 'availability': 1.0, 'mttr_s': 4800, 'power_working_kw': 7.0, 'power_idle_kw': 0.7},
    'M5': {'processing_time_s': 110, 'availability': 0.9823, 'mttr_s': 1099.8, 'power_working_kw': 5.5, 'power_idle_kw': 0.55}
}

# Create buffers with their parameters
buffer_params = {
    'B0': {'capacity': 6},
    'B1': {'capacity': 3},
    'B2': {'capacity': 3},
    'B3': {'capacity': 3},
    'B4': {'capacity': 3}
}

# Create sensors to measure parameters
sensors = {
    'M1': {
        'processing_time_s': 100,
        'availability%': 92.58,
        'mttr_s': 3206.25,
        'power_working_kw': 4.0,
        'power_idle_kw': 0.4,
        'buffer_capacity': 6
    },
    'M2': {
        'processing_time_s': 130,
        'availability%': 97.36,
        'mttr_s': 2859.26,
        'power_working_kw': 5.0,
        'power_idle_kw': 0.5,
        'buffer_capacity': 3
    },
    'M3': {
        'processing_time_s': 90,
        'availability%': 94.69,
        'mttr_s': 2882.82,
        'power_working_kw': 4.5,
        'power_idle_kw': 0.45,
        'buffer_capacity': 3
    },
    'M4': {
        'processing_time_s': 140,
        'availability%': 100.0,
        'mttr_s': 4800,
        'power_working_kw': 7.0,
        'power_idle_kw': 0.7,
        'buffer_capacity': 3
    },
    'M5': {
        'processing_time_s': 110,
        'availability%': 98.23,
        'mttr_s': 1099.8,
        'power_working_kw': 5.5,
        'power_idle_kw': 0.55,
        'buffer_capacity': 3
    },
    'B0': {
        'buffer_capacity': 6
    },
    'B1': {
        'buffer_capacity': 3
    },
    'B2': {
        'buffer_capacity': 3
    },
    'B3': {
        'buffer_capacity': 3
    },
    'B4': {
        'buffer_capacity': 3
    }
}

# Create a database connection
conn = sqlite3.connect('digital_twin.db')
cursor = conn.cursor()

# Create tables as defined in the schema
cursor.execute('''
    CREATE TABLE IF NOT EXISTS machines (
        id TEXT PRIMARY KEY,
        processing_time_s DOUBLE PRECISION,
        availability DOUBLE PRECISION,
        mttr_s DOUBLE PRECISION,
        power_working_kw DOUBLE PRECISION,
        power_idle_kw DOUBLE PRECISION
    );
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS buffers (
        id TEXT PRIMARY KEY,
        capacity INTEGER
    );
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS stations (
        id TEXT PRIMARY KEY,
        processing_time_s DOUBLE PRECISION,
        availability DOUBLE PRECISION,
        mttr_s DOUBLE PRECISION,
        work_power_kw DOUBLE PRECISION,
        idle_power_kw DOUBLE PRECISION
    );
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS tag_map (
        tag_id TEXT PRIMARY KEY,
        machine_id TEXT,
        signal TEXT,
        unit TEXT,
        register TEXT,
        scale DOUBLE PRECISION
    );
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS raw_ingest (
        ingested_at TIMESTAMPTZ PRIMARY KEY,
        source TEXT,
        payload JSONB
    );
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS events (
        ts TIMESTAMPTZ,
        machine_id TEXT,
        reason_code TEXT,
        duration_s DOUBLE PRECISION,
        energy_kwh DOUBLE PRECISION,
        PRIMARY KEY (machine_id, ts)
    );
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS samples (
        ts TIMESTAMPTZ,
        machine_id TEXT,
        tag TEXT,
        value DOUBLE PRECISION,
        PRIMARY KEY (machine_id, ts, tag)
    );
''')

cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_events_machine_id_ts ON events (machine_id, ts);
''')

cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_samples_machine_id_ts ON samples (machine_id, ts);
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS ingest_watermark (
        source TEXT PRIMARY KEY,
        max_event_ts TIMESTAMPTZ
    );
''')

# Insert machine data
for machine_id, params in machine_params.items():
    cursor.execute('''
        INSERT OR REPLACE INTO machines (id, processing_time_s, availability, mttr_s, power_working_kw, power_idle_kw)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (machine_id, params['processing_time_s'], params['availability'], params['mttr_s'], params['power_working_kw'], params['power_idle_kw']))

# Insert buffer data
for buffer_id, params in buffer_params.items():
    cursor.execute('''
        INSERT OR REPLACE INTO buffers (id, capacity)
        VALUES (?, ?)
    ''', (buffer_id, params['capacity']))

# Insert station data
for station_id, params in machine_params.items():
    cursor.execute('''
        INSERT OR REPLACE INTO stations (id, processing_time_s, availability, mttr_s, work_power_kw, idle_power_kw)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (station_id, params['processing_time_s'], params['availability'], params['mttr_s'], params['power_working_kw'], params['power_idle_kw']))

# Insert tag map data
tag_map_data = [
    ('processing_time_s', 'M1', 'processing_time_s', 's', 'processing_time_s', 1.0),
    ('availability%', 'M1', 'availability%', '%', 'availability%', 1.0),
    ('mttr_s', 'M1', 'mttr_s', 's', 'mttr_s', 1.0),
    ('power_working_kw', 'M1', 'power_working_kw', 'kW', 'power_working_kw', 1.0),
    ('power_idle_kw', 'M1', 'power_idle_kw', 'kW', 'power_idle_kw', 1.0),
    ('buffer_capacity', 'B0', 'buffer_capacity', 'units', 'buffer_capacity', 1.0),
    ('processing_time_s', 'M2', 'processing_time_s', 's', 'processing_time_s', 1.0),
    ('availability%', 'M2', 'availability%', '%', 'availability%', 1.0),
    ('mttr_s', 'M2', 'mttr_s', 's', 'mttr_s', 1.0),
    ('power_working_kw', 'M2', 'power_working_kw', 'kW', 'power_working_kw', 1.0),
    ('power_idle_kw', 'M2', 'power_idle_kw', 'kW', 'power_idle_kw', 1.0),
    ('processing_time_s', 'M3', 'processing_time_s', 's', 'processing_time_s', 1.0),
    ('availability%', 'M3', 'availability%', '%', 'availability%', 1.0),
    ('mttr_s', 'M3', 'mttr_s', 's', 'mttr_s', 1.0),
    ('power_working_kw', 'M3', 'power_working_kw', 'kW', 'power_working_kw', 1.0),
    ('power_idle_kw', 'M3', 'power_idle_kw', 'kW', 'power_idle_kw', 1.0),
    ('processing_time_s', 'M4', 'processing_time_s', 's', 'processing_time_s', 1.0),
    ('availability%', 'M4', 'availability%', '%', 'availability%', 1.0),
    ('mttr_s', 'M4', 'mttr_s', 's', 'mttr_s', 1.0),
    ('power_working_kw', 'M4', 'power_working_kw', 'kW', 'power_working_kw', 1.0),
    ('power_idle_kw', 'M4', 'power_idle_kw', 'kW', 'power_idle_kw', 1.0),
    ('processing_time_s', 'M5', 'processing_time_s', 's', 'processing_time_s', 1.0),
    ('availability%', 'M5', 'availability%', '%', 'availability%', 1.0),
    ('mttr_s', 'M5', 'mttr_s', 's', 'mttr_s', 1.0),
    ('power_working_kw', 'M5', 'power_working_kw', 'kW', 'power_working_kw', 1.0),
    ('power_idle_kw', 'M5', 'power_idle_kw', 'kW', 'power_idle_kw', 1.0)
]

for tag_id, machine_id, signal, unit, register, scale in tag_map_data:
    cursor.execute('''
        INSERT OR REPLACE INTO tag_map (tag_id, machine_id, signal, unit, register, scale)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (tag_id, machine_id, signal, unit, register, scale))

conn.commit()

# Main simulation loop
simulation_time = 0
sim_duration = 432000  # 5 days in seconds
time_step = 0.01  # 10ms time step

# Create a part generator
class PartGenerator:
    def __init__(self, system, rate=150):
        self.system = system
        self.rate = rate  # seconds between parts
        self.last_spawn_time = 0
        self.part_count = 0

    def update(self, current_time):
        if current_time - self.last_spawn_time > self.rate:
            self.spawn_part(current_time)
            self.last_spawn_time = current_time

    def spawn_part(self, current_time):
        # Create a new part
        part = chrono.ChBody()
        part.SetMass(1.0)
        part.SetInertiaXX(chrono.ChVectorD(0.1, 0.1, 0.1))
        part.SetPos(chrono.ChVectorD(0, 0, 0))
        part.GetCollisionModel().ClearModel()
        part.GetCollisionModel().AddBox(0.2, 0.2, 0.2)
        part.SetMaterialSurface(steel_mat)
        self.system.Add(part)
        self.part_count += 1

# Initialize part generator
part_generator = PartGenerator(system, 150)  # 150 seconds between parts

# Create a logging function
def log_sensor_data(current_time):
    # Log samples to the database
    for machine_id, params in sensors.items():
        for tag, value in params.items():
            # Skip non-sensor tags
            if tag == 'buffer_capacity':
                continue
            cursor.execute('''
                INSERT INTO samples (ts