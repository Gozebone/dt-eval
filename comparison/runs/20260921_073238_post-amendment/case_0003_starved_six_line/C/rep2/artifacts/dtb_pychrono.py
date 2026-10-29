import pychrono as chrono
import pychrono.irrlicht as irr
import numpy as np
import time
import json
import sqlite3
from datetime import datetime, timedelta
import threading
import queue

# Initialize the Chrono system
chrono.Initialize()
chrono.SetChronoDataPath('path/to/chrono/data/')  # Update with actual path

# Database setup
conn = sqlite3.connect('digital_twin.db')
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
        reason_code TEXT NOT NULL,
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

conn.commit()

# Create and populate machines table
machines_data = [
    ('M1', 199.86, 0.9877, 1062.58, 5.0, 0.5),
    ('M2', 220.09, 0.9863, 1184.73, 5.5, 0.55),
    ('M3', 240.01, 0.9978, 314.75, 6.0, 0.6),
    ('M4', 259.99, 0.9885, 1246.71, 7.0, 0.7),
    ('M5', 230.13, 0.9951, 2129.84, 6.5, 0.65),
    ('M6', 209.83, 0.9898, 2200.89, 6.0, 0.6)
]

cursor.executemany('''
    INSERT OR REPLACE INTO machines (id, process_time_s, availability, mttr_s, work_power_kw, idle_power_kw)
    VALUES (?, ?, ?, ?, ?, ?)
''', machines_data)

# Create and populate buffers table
buffers_data = [
    ('B0', 10),
    ('B1', 10),
    ('B2', 10),
    ('B3', 10),
    ('B4', 10),
    ('B5', 10)
]

cursor.executemany('''
    INSERT OR REPLACE INTO buffers (id, capacity)
    VALUES (?, ?)
''', buffers_data)

# Create and populate tag_map table
tag_map_data = [
    ('T1', 'M1', 'process_time_s', 's', 't1', 1),
    ('T2', 'M1', 'availability', 'dimensionless', 't2', 1),
    ('T3', 'M1', 'mttr_s', 's', 't3', 1),
    ('T4', 'M1', 'work_power_kw', 'kW', 't4', 1),
    ('T5', 'M1', 'idle_power_kw', 'kW', 't5', 1),
    ('T6', 'M2', 'process_time_s', 's', 't6', 1),
    ('T7', 'M2', 'availability', 'dimensionless', 't7', 1),
    ('T8', 'M2', 'mttr_s', 's', 't8', 1),
    ('T9', 'M2', 'work_power_kw', 'kW', 't9', 1),
    ('T10', 'M2', 'idle_power_kw', 'kW', 't10', 1),
    ('T11', 'M3', 'process_time_s', 's', 't11', 1),
    ('T12', 'M3', 'availability', 'dimensionless', 't12', 1),
    ('T13', 'M3', 'mttr_s', 's', 't13', 1),
    ('T14', 'M3', 'work_power_kw', 'kW', 't14', 1),
    ('T15', 'M3', 'idle_power_kw', 'kW', 't15', 1),
    ('T16', 'M4', 'process_time_s', 's', 't16', 1),
    ('T17', 'M4', 'availability', 'dimensionless', 't17', 1),
    ('T18', 'M4', 'mttr_s', 's', 't18', 1),
    ('T19', 'M4', 'work_power_kw', 'kW', 't19', 1),
    ('T20', 'M4', 'idle_power_kw', 'kW', 't20', 1),
    ('T21', 'M5', 'process_time_s', 's', 't21', 1),
    ('T22', 'M5', 'availability', 'dimensionless', 't22', 1),
    ('T23', 'M5', 'mttr_s', 's', 't23', 1),
    ('T24', 'M5', 'work_power_kw', 'kW', 't24', 1),
    ('T25', 'M5', 'idle_power_kw', 'kW', 't25', 1),
    ('T26', 'M6', 'process_time_s', 's', 't26', 1),
    ('T27', 'M6', 'availability', 'dimensionless', 't27', 1),
    ('T28', 'M6', 'mttr_s', 's', 't28', 1),
    ('T29', 'M6', 'work_power_kw', 'kW', 't29', 1),
    ('T30', 'M6', 'idle_power_kw', 'kW', 't30', 1)
]

cursor.executemany('''
    INSERT OR REPLACE INTO tag_map (tag_id, machine_id, signal, unit, register, scale)
    VALUES (?, ?, ?, ?, ?, ?)
''', tag_map_data)

conn.commit()

# Simulation parameters
simulation_duration = 432000  # 5 days in seconds
time_step = 0.01  # 10ms time step
current_time = 0.0

# Equipment definitions
equipment = {
    "M1": {"process_time": 199.86, "availability": 0.9877, "mttr": 1062.58, "work_power": 5.0, "idle_power": 0.5},
    "M2": {"process_time": 220.09, "availability": 0.9863, "mttr": 1184.73, "work_power": 5.5, "idle_power": 0.55},
    "M3": {"process_time": 240.01, "availability": 0.9978, "mttr": 314.75, "work_power": 6.0, "idle_power": 0.6},
    "M4": {"process_time": 259.99, "availability": 0.9885, "mttr": 1246.71, "work_power": 7.0, "idle_power": 0.7},
    "M5": {"process_time": 230.13, "availability": 0.9951, "mttr": 2129.84, "work_power": 6.5, "idle_power": 0.65},
    "M6": {"process_time": 209.83, "availability": 0.9898, "mttr": 2200.89, "work_power": 6.0, "idle_power": 0.6}
}

# Create simulation environment
system = chrono.ChSystemNSC()
system.Set_G_acc(chrono.ChVectorD(0, 0, 0))  # No gravity

# Create ground
ground = chrono.ChBody()
ground.SetBodyFixed(True)
ground.SetPos(chrono.ChVectorD(0, -1, 0))
system.Add(ground)

# Create materials
steel_mat = chrono.ChMaterialSurfaceNSC()
steel_mat.SetFriction(0.5)
steel_mat.SetRestitution(0.1)

refractory_mat = chrono.ChMaterialSurfaceNSC()
refractory_mat.SetFriction(0.3)
refractory_mat.SetRestitution(0.05)

# Create a simple representation of machines and buffers
machines_bodies = {}
buffers_bodies = {}

# Create machine bodies
for i, (machine_id, params) in enumerate(equipment.items()):
    # Create a machine body
    machine_body = chrono.ChBody()
    machine_body.SetPos(chrono.ChVectorD(i * 5, 0, 0))
    machine_body.SetMass(100)
    machine_body.SetInertiaXX(chrono.ChVectorD(10, 10, 10))
    machine_body.GetCollisionModel().ClearModel()
    machine_body.GetCollisionModel().AddBox(1, 1, 1)
    machine_body.GetCollisionModel().BuildModel()
    machine_body.SetMaterialSurface(steel_mat)
    system.Add(machine_body)

    # Store reference
    machines_bodies[machine_id] = machine_body

# Create buffer bodies
for i in range(6):
    buffer_body = chrono.ChBody()
    buffer_body.SetPos(chrono.ChVectorD(i * 5 + 2.5, 0, 0))
    buffer_body.SetMass(50)
    buffer_body.SetInertiaXX(chrono.ChVectorD(5, 5, 5))
    buffer_body.GetCollisionModel().ClearModel()
    buffer_body.GetCollisionModel().AddBox(0.5, 0.5, 0.5)
    buffer_body.GetCollisionModel().BuildModel()
    buffer_body.SetMaterialSurface(steel_mat)
    system.Add(buffer_body)

    buffers_bodies[f"B{i}"] = buffer_body

# Create sensors
class Sensor:
    def __init__(self, machine_id, signal, tag_id):
        self.machine_id = machine_id
        self.signal = signal
        self.tag_id = tag_id
        self.value = 0.0

    def read(self, params):
        self.value = params.get(self.signal, 0.0)
        return self.value

# Create sensors for each machine parameter
sensors = []
tag_id_counter = 1
for machine_id, params in equipment.items():
    for signal in ['process_time_s', 'availability', 'mttr_s', 'work_power_kw', 'idle_power_kw']:
        tag_id = f"T{tag_id_counter}"
        sensors.append(Sensor(machine_id, signal, tag_id))
        tag_id_counter += 1

# Simulation loop
start_time = time.time()
event_queue = queue.Queue()

# Function to log events
def log_event(machine_id, reason_code, duration_s, energy_kwh):
    timestamp = datetime.now()
    cursor.execute('''
        INSERT INTO events (ts, machine_id, reason_code, duration_s, energy_kwh)
        VALUES (?, ?, ?, ?, ?)
    ''', (timestamp, machine_id, reason_code, duration_s, energy_kwh))
    conn.commit()

# Function to log samples
def log_sample(machine_id, tag, value):
    timestamp = datetime.now()
    cursor.execute('''
        INSERT INTO samples (ts, machine_id, tag, value)
        VALUES (?, ?, ?, ?)
    ''', (timestamp, machine_id, tag, value))
    conn.commit()

# Function to handle processing
def process_machine(machine_id, params, current_time):
    # Simulate machine operation
    process_time = params['process_time']
    availability = params['availability']
    mttr = params['mttr']
    work_power = params['work_power']
    idle_power = params['idle_power']

    # Simulate machine being in production state
    is_operational = np.random.rand() < availability
    if is_operational:
        # Production process
        start_time = current_time
        # Simulate processing
        while current_time - start_time < process_time:
            # Collect power consumption data
            current_power = work_power
            energy_kwh =