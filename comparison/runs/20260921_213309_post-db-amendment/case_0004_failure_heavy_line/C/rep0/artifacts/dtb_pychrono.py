```python
import pychrono as chrono
import pychrono.fea as fea
import pychrono.irrlicht as irr
import math
import json
import time
import datetime
import sqlite3
import random

# Initialize PyChrono system
chrono.SetChronoDataPath('/path/to/chrono/data')  # Replace with your Chrono data path
system = chrono.ChSystemNSC()
system.SetGravitationalAcceleration(chrono.ChVectorD(0, 0, 0))  # No gravity for this simulation

# Initialize Irrlicht visualization (optional)
vis = irr.ChVisualSystemIrrlicht()
vis.SetWindowSize(1024, 768)
vis.SetWindowTitle('Production Line Simulation')
vis.Initialize()
vis.AddLogo()
vis.AddSkyBox()
vis.AddCamera(chrono.ChVectorD(10, 10, 10), chrono.ChVectorD(0, 0, 0))
vis.AddTypicalLights()

# Database setup
conn = sqlite3.connect('digital_twin.db')
cursor = conn.cursor()

# Create tables if they don't exist (matching schema)
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
        capacity integer NOT NULL,
        before text NOT NULL,
        after text NOT NULL
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS stations (
        id text PRIMARY KEY,
        processing_time_s double precision NOT NULL,
        availability_pct double precision NOT NULL,
        mttr_s double precision NOT NULL,
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

cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_events_machine_ts ON events (machine_id, ts)
''')

cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_samples_machine_ts ON samples (machine_id, ts)
''')

conn.commit()

# Insert machines
machines_data = [
    ('M1', 'M1'), ('M2', 'M2'), ('M3', 'M3'), ('M4', 'M4'), ('M5', 'M5')
]
cursor.executemany('INSERT OR REPLACE INTO machines (id, name) VALUES (?, ?)', machines_data)

# Insert buffers
buffers_data = [
    ('B0', 6, 'source', 'M1'),
    ('B1', 3, 'M1', 'M2'),
    ('B2', 3, 'M2', 'M3'),
    ('B3', 3, 'M3', 'M4'),
    ('B4', 3, 'M4', 'M5')
]
cursor.executemany('INSERT OR REPLACE INTO buffers (id, capacity, before, after) VALUES (?, ?, ?, ?)', buffers_data)

# Insert stations
stations_data = [
    ('M1', 99.96, 92.58, 3206.25, 4.0, 0.4),
    ('M2', 130.16, 97.36, 2859.26, 5.0, 0.5),
    ('M3', 90.14, 94.69, 2882.82, 4.5, 0.45),
    ('M4', 140.19, 100.0, 1099.8, 7.0, 0.7),
    ('M5', 109.82, 98.23, 2400, 5.5, 0.55)
]
cursor.executemany('INSERT OR REPLACE INTO stations (id, processing_time_s, availability_pct, mttr_s, power_working_kw, power_idle_kw) VALUES (?, ?, ?, ?, ?, ?)', stations_data)

conn.commit()

# Define simulation constants
TIME_STEP = 0.01
SIMULATION_TIME = 10000  # seconds
INTER_ARRIVAL_TIME = 150  # seconds
LOG_INTERVAL = 10  # seconds

# Define equipment properties
equipment_properties = {
    "M1": {
        "processing_time": 99.96,
        "availability": 0.9258,
        "mttr": 3206.25,
        "power_working_kw": 4.0,
        "power_idle_kw": 0.4
    },
    "M2": {
        "processing_time": 130.16,
        "availability": 0.9274,
        "mttr": 2859.26,
        "power_working_kw": 5.0,
        "power_idle_kw": 0.5
    },
    "M3": {
        "processing_time": 90.14,
        "availability": 0.8862,
        "mttr": 2882.82,
        "power_working_kw": 4.5,
        "power_idle_kw": 0.45
    },
    "M4": {
        "processing_time": 140.19,
        "availability": 0.9091,
        "mttr": 1099.8,
        "power_working_kw": 7.0,
        "power_idle_kw": 0.7
    },
    "M5": {
        "processing_time": 109.82,
        "availability": 0.9333,
        "mttr": 2400,
        "power_working_kw": 5.5,
        "power_idle_kw": 0.55
    }
}

# Create physical bodies for equipment
bodies = {}
materials = {}

# Create base material for equipment
steel_material = chrono.ChMaterialSurfaceNSC()
steel_material.SetFriction(0.4)
steel_material.SetRestitution(0.1)

# Create equipment bodies (simplified as boxes)
for machine_id in ["M1", "M2", "M3", "M4", "M5"]:
    # Create a box for each machine
    body = chrono.ChBody()
    body.SetPos(chrono.ChVectorD(0, 0, 0))
    body.SetMass(1000)
    body.SetInertiaXX(chrono.ChVectorD(100, 100, 100))
    body.GetCollisionModel().ClearModel()
    body.GetCollisionModel().AddBox(1, 1, 1)  # Simplified box
    body.GetCollisionModel().BuildModel()
    body.SetMaterialSurface(steel_material)
    system.Add(body)
    bodies[machine_id] = body

# Create buffers as simple physical objects
buffers = {}
for buffer_id in ["B0", "B1", "B2", "B3", "B4"]:
    buffer_body = chrono.ChBody()
    buffer_body.SetPos(chrono.ChVectorD(0, 0, 0))
    buffer_body.SetMass(100)
    buffer_body.SetInertiaXX(chrono.ChVectorD(10, 10, 10))
    buffer_body.GetCollisionModel().ClearModel()
    buffer_body.GetCollisionModel().AddBox(2, 1, 1)  # Simplified box
    buffer_body.GetCollisionModel().BuildModel()
    buffer_body.SetMaterialSurface(steel_material)
    system.Add(buffer_body)
    buffers[buffer_id] = buffer_body

# Create parts for components (simplified)
part_material = chrono.ChMaterialSurfaceNSC()
part_material.SetFriction(0.3)
part_material.SetRestitution(0.05)

# Create source part
source_part = chrono.ChBody()
source_part.SetPos(chrono.ChVectorD(0, 0, 0))
source_part.SetMass(50)
source_part.SetInertiaXX(chrono.ChVectorD(5, 5, 5))
source_part.GetCollisionModel().ClearModel()
source_part.GetCollisionModel().AddBox(0.5, 0.5, 0.5)
source_part.GetCollisionModel().BuildModel()
source_part.SetMaterialSurface(part_material)
system.Add(source_part)

# Create a simple conveyor belt
conveyor_material = chrono.ChMaterialSurfaceNSC()
conveyor_material.SetFriction(0.5)
conveyor_material.SetRestitution(0.1)

# Create a simple conveyor belt component
conveyor_belt = chrono.ChBody()
conveyor_belt.SetPos(chrono.ChVectorD(0, 0, 0))
conveyor_belt.SetMass(200)
conveyor_belt.SetInertiaXX(chrono.ChVectorD(20, 20, 20))
conveyor_belt.GetCollisionModel().ClearModel()
conveyor_belt.GetCollisionModel().AddBox(5, 0.5, 0.5)
conveyor_belt.GetCollisionModel().BuildModel()
conveyor_belt.SetMaterialSurface(conveyor_material)
system.Add(conveyor_belt)

# Create a simple product part
product_part = chrono.ChBody()
product_part.SetPos(chrono.ChVectorD(0, 0, 0))
product_part.SetMass(10)
product_part.SetInertiaXX(chrono.ChVectorD(1, 1, 1))
product_part.GetCollisionModel().ClearModel()
product_part.GetCollisionModel().AddBox(0.2, 0.2, 0.2)
product_part.GetCollisionModel().BuildModel()
product_part.SetMaterialSurface(part_material)
system.Add(product_part)

# Create sensors
sensors = {}

# Create an object to track simulation time
sim_start_time = datetime.datetime.now()
current_time = sim_start_time

# Create a mock simulation controller
class EquipmentController:
    def __init__(self, machine_id, properties):
        self.machine_id = machine_id
        self.properties = properties
        self.is_operational = True
        self.last_failure_time = 0
        self.failure_duration = 0
        self.power_consumption = 0.0
        self.is_processing = False
        self.processing_start_time = 0
        self.processing_duration = 0
        self.production_count = 0

    def simulate_state(self, current_time):
        # Simulate availability
        if not self.is_operational:
            if current_time - self.last_failure_time > self.properties["mttr"]:
                self.is_operational = True
                self.failure_duration = 0
                self.send_event("REPAIR", 0, 0)
        else:
            # Simulate potential failure
            if random.random() > self.properties["availability"]:
                self.is_operational = False
                self.last_failure_time = current_time
                self.send_event("FAILURE", 0, 0)

        # Update power consumption
        if self.is_operational:
            if self.is_processing:
                self.power_consumption = self.properties["power_working_kw"]
            else:
                self.power_consumption = self.properties["power_idle_kw"]
        else:
            self.power_consumption = 0.0

        # Check if processing is complete
        if self.is_processing and current_time - self.processing_start_time >= self.properties["processing_time"]:
            self.is_processing = False
            self.production_count += 1
            self.processing_duration = current_time - self.processing_start_time
            self.send_event("PROCESSING_COMPLETE", self.processing_duration, self.power_consumption * self.processing_duration / 3600)

    def start_processing(self, start_time):
        if self.is_operational:
            self.is_processing = True
            self.processing_start_time = start_time
            self.send_event("PROCESSING_START", 0, self.power_consumption)

    def send_event(self, reason_code, duration, energy):
        event_time = datetime.datetime.now()
        cursor.execute('''
            INSERT INTO events (ts, machine_id, reason_code, duration_s, energy_kwh)
            VALUES (?, ?, ?, ?, ?)
        ''', (event_time, self.machine_id, reason_code, duration, energy))
        conn.commit()

# Create controllers for each machine
controllers = {}
for machine_id, properties in equipment_properties.items():
    controllers[machine_id] = EquipmentController(machine_id, properties)

# Create source simulation
source_last_arrival = 0
source_count = 0

# Create loggers for sensors and data
def log_data():
    current_time = datetime.datetime.now()
    for machine_id, controller in controllers.items():
        # Log samples for each machine
        cursor.execute('''
            INSERT INTO samples (ts, machine_id, tag, value)
            VALUES (?, ?, ?, ?)
        ''', (current_time, machine_id, "POWER_CONSUMPTION", controller.power_consumption))
        cursor.execute('''
            INSERT INTO samples (