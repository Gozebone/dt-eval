```python
import pychrono as chrono
import pychrono.irrlicht as irr
import math
import json
import time
import datetime
from collections import defaultdict
import sqlite3

# Initialize the Chrono system
chrono.SetChronoDataPath("../../../data/")
chrono.SetChronoDataPath("../../../data/")

# Create the physical system
system = chrono.ChSystemNSC()
system.Set_G_acc(chrono.ChVectorD(0, -9.81, 0))

# Create a ground plane
ground = chrono.ChBodyEasyBox(20, 0.1, 20, 1000, True, True)
ground.SetPos(chrono.ChVectorD(0, -0.05, 0))
ground.SetBodyFixed(True)
system.Add(ground)

# Create a simple material for bodies
material = chrono.ChMaterialSurfaceNSC()
material.SetFriction(0.5)
material.SetRestitution(0.1)

# Create a global dictionary to hold equipment data
equipment_data = {
    "M1": {
        "process_time_s": 150,
        "availability": 0.98,
        "mttr_s": 600,
        "power_working_kw": 4.0,
        "power_idle_kw": 0.4,
        "capacity": None
    },
    "M2": {
        "process_time_s": 120,
        "availability": 0.97,
        "mttr_s": 900,
        "power_working_kw": 5.0,
        "power_idle_kw": 0.5,
        "capacity": None
    },
    "M3": {
        "process_time_s": 180,
        "availability": 0.95,
        "mttr_s": 1200,
        "power_working_kw": 6.0,
        "power_idle_kw": 0.6,
        "capacity": None
    },
    "M4": {
        "process_time_s": 120,
        "availability": 0.97,
        "mttr_s": 900,
        "power_working_kw": 5.0,
        "power_idle_kw": 0.5,
        "capacity": None
    },
    "M5": {
        "process_time_s": 150,
        "availability": 0.98,
        "mttr_s": 600,
        "power_working_kw": 4.0,
        "power_idle_kw": 0.4,
        "capacity": None
    },
    "B0": {
        "capacity": 20
    },
    "B1": {
        "capacity": 8
    },
    "B2": {
        "capacity": 8
    },
    "B3": {
        "capacity": 8
    },
    "B4": {
        "capacity": 8
    }
}

# Create a list of machines in order
machines = ["M1", "M2", "M3", "M4", "M5"]
buffers = ["B0", "B1", "B2", "B3", "B4"]

# Create machine bodies
machine_bodies = {}
for machine_id in machines:
    # Create a simple box to represent the machine
    machine_body = chrono.ChBodyEasyBox(2, 1, 2, 1000, True, True)
    machine_body.SetMaterialSurface(material)
    machine_body.SetPos(chrono.ChVectorD(0, 0, 0))
    system.Add(machine_body)
    machine_bodies[machine_id] = machine_body

# Create buffer bodies
buffer_bodies = {}
for buffer_id in buffers:
    # Create a simple box to represent the buffer
    buffer_body = chrono.ChBodyEasyBox(1.5, 0.5, 1.5, 1000, True, True)
    buffer_body.SetMaterialSurface(material)
    buffer_body.SetPos(chrono.ChVectorD(0, 0, 0))
    system.Add(buffer_body)
    buffer_bodies[buffer_id] = buffer_body

# Set up source generator
source_rate = 130  # seconds between items
source_count = 0
last_source_time = 0

# Create an item that will be produced
item_count = 0
item_bodies = []

# Create a simple source item
def create_source_item():
    global item_count
    item = chrono.ChBodyEasyBox(0.5, 0.5, 0.5, 100, True, True)
    item.SetMaterialSurface(material)
    item.SetPos(chrono.ChVectorD(-5, 1, 0))
    item.SetBodyFixed(False)
    system.Add(item)
    item_count += 1
    return item

# Create initial items
for i in range(5):
    item = create_source_item()
    item_bodies.append(item)

# Create simulation parameters
sim_time = 0.0
max_time = 432000  # 5 days in seconds
dt = 0.01
log_interval = 10  # Log every 10 seconds
last_log_time = 0

# Create a database connection (mocked for this example)
# In a real implementation, you would connect to a real database
conn = sqlite3.connect(':memory:')
cursor = conn.cursor()

# Create tables
cursor.execute('''CREATE TABLE raw_ingest (
    ingested_at timestamptz NOT NULL,
    source text NOT NULL,
    payload jsonb NOT NULL
)''')

cursor.execute('''CREATE TABLE ingest_watermark (
    source text PRIMARY KEY,
    max_event_ts timestamptz
)''')

cursor.execute('''CREATE TABLE tag_map (
    tag_id text PRIMARY KEY,
    machine_id text,
    signal text,
    unit text,
    register text,
    scale double precision
)''')

cursor.execute('''CREATE TABLE machines (
    id text PRIMARY KEY,
    process_time_s double precision,
    availability double precision,
    mttr_s double precision,
    power_working_kw double precision,
    power_idle_kw double precision,
    capacity double precision
)''')

cursor.execute('''CREATE TABLE buffers (
    id text PRIMARY KEY,
    capacity double precision,
    before text,
    after text
)''')

cursor.execute('''CREATE TABLE stations (
    id text PRIMARY KEY,
    processing_time_s double precision,
    availability_pct double precision,
    mttr_s double precision,
    power_working_kw double precision,
    power_idle_kw double precision
)''')

cursor.execute('''CREATE TABLE events (
    ts timestamptz NOT NULL,
    machine_id text NOT NULL,
    reason_code text,
    duration_s double precision,
    energy_kwh double precision
)''')

cursor.execute('''CREATE TABLE samples (
    ts timestamptz NOT NULL,
    machine_id text NOT NULL,
    tag text NOT NULL,
    value double precision
)''')

cursor.execute('''CREATE INDEX idx_events_machine_ts ON events (machine_id, ts)''')
cursor.execute('''CREATE INDEX idx_samples_machine_ts ON samples (machine_id, ts)''')

# Insert initial data
for machine_id in machines:
    cursor.execute('''INSERT INTO machines (id, process_time_s, availability, mttr_s, power_working_kw, power_idle_kw, capacity)
        VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (machine_id, 
         equipment_data[machine_id]["process_time_s"], 
         equipment_data[machine_id]["availability"],
         equipment_data[machine_id]["mttr_s"],
         equipment_data[machine_id]["power_working_kw"],
         equipment_data[machine_id]["power_idle_kw"],
         equipment_data[machine_id]["capacity"]))

for buffer_id in buffers:
    cursor.execute('''INSERT INTO buffers (id, capacity, before, after)
        VALUES (?, ?, ?, ?)''',
        (buffer_id,
         equipment_data[buffer_id]["capacity"],
         "M1" if buffer_id == "B1" else "M2" if buffer_id == "B2" else "M3" if buffer_id == "B3" else "M4" if buffer_id == "B4" else "source",
         "M2" if buffer_id == "B1" else "M3" if buffer_id == "B2" else "M4" if buffer_id == "B3" else "M5" if buffer_id == "B4" else "M1"))

for machine_id in machines:
    cursor.execute('''INSERT INTO stations (id, processing_time_s, availability_pct, mttr_s, power_working_kw, power_idle_kw)
        VALUES (?, ?, ?, ?, ?, ?)''',
        (machine_id,
         equipment_data[machine_id]["process_time_s"],
         equipment_data[machine_id]["availability"] * 100,
         equipment_data[machine_id]["mttr_s"],
         equipment_data[machine_id]["power_working_kw"],
         equipment_data[machine_id]["power_idle_kw"]))

# Create a sensor to track item movement
sensor_data = defaultdict(list)

# Main simulation loop
while sim_time < max_time:
    # Create new items at intervals
    if sim_time - last_source_time > source_rate:
        item = create_source_item()
        item_bodies.append(item)
        last_source_time = sim_time

    # Step the simulation
    system.DoStepDynamics(dt)
    sim_time += dt

    # Log data periodically
    if sim_time - last_log_time > log_interval:
        timestamp = datetime.datetime.fromtimestamp(sim_time)
        for machine_id in machines:
            # Simulate some sensor readings
            # Process time
            cursor.execute('''INSERT INTO samples (ts, machine_id, tag, value)
                VALUES (?, ?, ?, ?)''',
                (timestamp, machine_id, 'process_time_s', equipment_data[machine_id]["process_time_s"]))
            
            # Availability
            cursor.execute('''INSERT INTO samples (ts, machine_id, tag, value)
                VALUES (?, ?, ?, ?)''',
                (timestamp, machine_id, 'availability', equipment_data[machine_id]["availability"]))
            
            # MTTR
            cursor.execute('''INSERT INTO samples (ts, machine_id, tag, value)
                VALUES (?, ?, ?, ?)''',
                (timestamp, machine_id, 'mttr_s', equipment_data[machine_id]["mttr_s"]))
            
            # Working power
            cursor.execute('''INSERT INTO samples (ts, machine_id, tag, value)
                VALUES (?, ?, ?, ?)''',
                (timestamp, machine_id, 'power_working_kw', equipment_data[machine_id]["power_working_kw"]))
            
            # Idle power
            cursor.execute('''INSERT INTO samples (ts, machine_id, tag, value)
                VALUES (?, ?, ?, ?)''',
                (timestamp, machine_id, 'power_idle_kw', equipment_data[machine_id]["power_idle_kw"]))
        
        # Buffer capacities
        for buffer_id in buffers:
            cursor.execute('''INSERT INTO samples (ts, machine_id, tag, value)
                VALUES (?, ?, ?, ?)''',
                (timestamp, buffer_id, 'capacity', equipment_data[buffer_id]["capacity"]))
        
        # Log events (mocked)
        # Simulate some machine events
        for machine_id in machines:
            if equipment_data[machine_id]["availability"] < 0.98 and sim_time % 3600 < dt:  # Simulate periodic failures
                duration = equipment_data[machine_id]["mttr_s"]
                energy = equipment_data[machine_id]["power_working_kw"] * (duration / 3600)  # kWh
                cursor.execute('''INSERT INTO events (ts, machine_id, reason_code, duration_s, energy_kwh)
                    VALUES (?, ?, ?, ?, ?)''',
                    (timestamp, machine_id, 'failure', duration, energy))
        
        last_log_time = sim_time

# Store final data
timestamp = datetime.datetime.now()
cursor.execute('''INSERT INTO raw_ingest (ingested_at, source, payload)
    VALUES (?, ?, ?)''',
    (timestamp, 'digital_twin_simulation', json.dumps({
        "sim_time": sim_time,
        "machines": machines,
        "buffers": buffers,
        "equipment_data": equipment_data
    })))

# Commit the changes
conn.commit()

# Print summary
print("Simulation completed successfully")
print(f"Total simulation time: {sim_time} seconds")
print(f"Number of items produced: {len(item_bodies)}")

# Close the database connection
conn.close()

# Cleanup
del system
```