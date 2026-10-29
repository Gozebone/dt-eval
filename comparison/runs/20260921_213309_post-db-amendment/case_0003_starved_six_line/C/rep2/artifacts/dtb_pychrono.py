```python
import pychrono as chrono
import pychrono.irrlicht as irr
import numpy as np
import time
import json
from datetime import datetime, timedelta
import sqlite3

# Initialize PyChrono system
chrono.SetChronoDataPath('.')

# Create the physical system
system = chrono.ChSystemNSC()
system.Set_G_acc(chrono.ChVectorD(0, 0, 0))  # No gravity

# Create materials
steel_mat = chrono.ChMaterialSurfaceNSC()
steel_mat.SetFriction(0.4)
steel_mat.SetRestitution(0.1)

refractory_mat = chrono.ChMaterialSurfaceNSC()
refractory_mat.SetFriction(0.2)
refractory_mat.SetRestitution(0.2)

# Define machine data
machine_data = {
    "M1": {"processing_time_s": 200, "availability_pct": 97, "mttr_s": 900, "power_working_kw": 5.0, "power_idle_kw": 0.5},
    "M2": {"processing_time_s": 220, "availability_pct": 97, "mttr_s": 1000, "power_working_kw": 5.5, "power_idle_kw": 0.55},
    "M3": {"processing_time_s": 240, "availability_pct": 96, "mttr_s": 1200, "power_working_kw": 6.0, "power_idle_kw": 0.6},
    "M4": {"processing_time_s": 260, "availability_pct": 96, "mttr_s": 1400, "power_working_kw": 7.0, "power_idle_kw": 0.7},
    "M5": {"processing_time_s": 230, "availability_pct": 97, "mttr_s": 1100, "power_working_kw": 6.5, "power_idle_kw": 0.65},
    "M6": {"processing_time_s": 210, "availability_pct": 97, "mttr_s": 1000, "power_working_kw": 6.0, "power_idle_kw": 0.6}
}

# Define buffer data
buffer_data = {
    "B0": {"capacity": 10},
    "B1": {"capacity": 10},
    "B2": {"capacity": 10},
    "B3": {"capacity": 10},
    "B4": {"capacity": 10},
    "B5": {"capacity": 10}
}

# Create machines
machines = {}
for machine_id, params in machine_data.items():
    # Create a rigid body for machine
    machine_body = chrono.ChBody()
    machine_body.SetIdentifier(int(machine_id[1:]))  # Use machine number as identifier
    machine_body.SetPos(chrono.ChVectorD(0, 0, 0))  # Initial position
    machine_body.SetRot(chrono.QUNIT)  # Initial rotation
    machine_body.SetBodyFixed(False)  # Not fixed
    
    # Add material to machine body
    machine_body.GetMaterialSurfaceNSC().SetFriction(0.4)
    machine_body.GetMaterialSurfaceNSC().SetRestitution(0.1)
    
    # Add to system
    system.Add(machine_body)
    
    # Store machine reference
    machines[machine_id] = {
        "body": machine_body,
        "params": params,
        "is_operational": True,
        "last_start_time": 0,
        "active_duration": 0,
        "idle_duration": 0,
        "total_energy_kwh": 0,
        "status": "idle"  # 'idle', 'processing'
    }

# Create buffers
buffers = {}
for buffer_id, params in buffer_data.items():
    # Create a rigid body for buffer
    buffer_body = chrono.ChBody()
    buffer_body.SetIdentifier(int(buffer_id[1:]))  # Use buffer number as identifier
    buffer_body.SetPos(chrono.ChVectorD(0, 0, 0))  # Initial position
    buffer_body.SetRot(chrono.QUNIT)  # Initial rotation
    buffer_body.SetBodyFixed(False)  # Not fixed
    
    # Add material to buffer body
    buffer_body.GetMaterialSurfaceNSC().SetFriction(0.2)
    buffer_body.GetMaterialSurfaceNSC().SetRestitution(0.2)
    
    # Add to system
    system.Add(buffer_body)
    
    # Store buffer reference
    buffers[buffer_id] = {
        "body": buffer_body,
        "params": params,
        "items": []
    }

# Create source
source_body = chrono.ChBody()
source_body.SetIdentifier(0)
source_body.SetPos(chrono.ChVectorD(0, 0, 0))
source_body.SetRot(chrono.QUNIT)
source_body.SetBodyFixed(False)
system.Add(source_body)

# Create sink
sink_body = chrono.ChBody()
sink_body.SetIdentifier(999)
sink_body.SetPos(chrono.ChVectorD(0, 0, 0))
sink_body.SetRot(chrono.QUNIT)
sink_body.SetBodyFixed(False)
system.Add(sink_body)

# Create a simple conveyor belt simulation
# Here we'll create a simplified model where products flow from source to sink
# with processing at each machine and buffering between machines

# Simulate inter-arrival time of 300 seconds
inter_arrival_time = 300.0

# Simulation parameters
simulation_duration = 432000  # 5 days in seconds
time_step = 0.01  # Time step for simulation
current_time = 0.0
last_product_time = 0.0

# Sensor data containers
sensor_data = {
    "samples": [],
    "events": []
}

# Connect to database
conn = sqlite3.connect('digital_twin.db')
cursor = conn.cursor()

# Create tables if they don't exist
cursor.execute('''CREATE TABLE IF NOT EXISTS machines (
                    id TEXT PRIMARY KEY,
                    processing_time_s DOUBLE PRECISION,
                    availability_pct DOUBLE PRECISION,
                    mttr_s DOUBLE PRECISION,
                    power_working_kw DOUBLE PRECISION,
                    power_idle_kw DOUBLE PRECISION)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS buffers (
                    id TEXT PRIMARY KEY,
                    capacity INTEGER)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS tag_map (
                    tag_id TEXT PRIMARY KEY,
                    machine_id TEXT,
                    signal TEXT,
                    unit TEXT,
                    register TEXT,
                    scale DOUBLE PRECISION)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS raw_ingest (
                    ingested_at TIMESTAMPTZ PRIMARY KEY,
                    source TEXT,
                    payload JSONB)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS events (
                    ts TIMESTAMPTZ,
                    machine_id TEXT,
                    reason_code TEXT,
                    duration_s DOUBLE PRECISION,
                    energy_kwh DOUBLE PRECISION,
                    PRIMARY KEY (machine_id, ts))''')

cursor.execute('''CREATE TABLE IF NOT EXISTS samples (
                    ts TIMESTAMPTZ,
                    machine_id TEXT,
                    tag TEXT,
                    value DOUBLE PRECISION,
                    PRIMARY KEY (machine_id, ts, tag))''')

# Create indexes
cursor.execute('''CREATE INDEX IF NOT EXISTS idx_events_machine_time ON events (machine_id, ts)''')
cursor.execute('''CREATE INDEX IF NOT EXISTS idx_samples_machine_time ON samples (machine_id, ts)''')

# Insert machine data into database
for machine_id, params in machine_data.items():
    cursor.execute(
        "INSERT OR REPLACE INTO machines VALUES (?, ?, ?, ?, ?, ?)",
        (machine_id, params["processing_time_s"], params["availability_pct"], params["mttr_s"],
         params["power_working_kw"], params["power_idle_kw"])
    )

# Insert buffer data into database
for buffer_id, params in buffer_data.items():
    cursor.execute("INSERT OR REPLACE INTO buffers VALUES (?, ?)", (buffer_id, params["capacity"]))

# Insert tag map data into database
tags = ["process_time_s", "availability_pct", "mttr_s", "power"]

for tag in tags:
    for machine_id in machine_data.keys():
        cursor.execute(
            "INSERT OR REPLACE INTO tag_map VALUES (?, ?, ?, ?, ?, ?)",
            (tag, machine_id, tag, "s" if tag == "process_time_s" else "%", tag, 1.0)
        )

# Commit initial inserts
conn.commit()

# Create a product class
class Product:
    def __init__(self, id):
        self.id = id
        self.created_at = current_time
        self.current_machine = None
        self.process_start_time = None
        self.process_end_time = None

products = []
product_counter = 0

# Create a simulation loop
print("Starting simulation...")
start_time = time.time()

while current_time < simulation_duration:
    # Generate new products at source based on inter-arrival time
    if current_time - last_product_time >= inter_arrival_time:
        product_counter += 1
        product = Product(product_counter)
        products.append(product)
        last_product_time = current_time
        print(f"Product {product_counter} created at time {current_time}")

    # Update machines
    for machine_id, machine_info in machines.items():
        if not machine_info["is_operational"]:
            # Check if machine is being repaired
            if current_time - machine_info["last_start_time"] >= machine_info["params"]["mttr_s"]:
                machine_info["is_operational"] = True
                machine_info["status"] = "idle"
                print(f"Machine {machine_id} repaired")
                # Log event
                event_data = {
                    "ts": current_time,
                    "machine_id": machine_id,
                    "reason_code": "repair_complete",
                    "duration_s": machine_info["params"]["mttr_s"],
                    "energy_kwh": 0
                }
                cursor.execute(
                    "INSERT INTO events VALUES (?, ?, ?, ?, ?)",
                    (event_data["ts"], event_data["machine_id"], event_data["reason_code"],
                     event_data["duration_s"], event_data["energy_kwh"])
                )
                sensor_data["events"].append(event_data)
        else:
            # Check machine availability
            availability = machine_info["params"]["availability_pct"] / 100.0
            if np.random.random() > availability:
                machine_info["is_operational"] = False
                machine_info["last_start_time"] = current_time
                machine_info["status"] = "broken"
                print(f"Machine {machine_id} failed at time {current_time}")
                # Log event
                event_data = {
                    "ts": current_time,
                    "machine_id": machine_id,
                    "reason_code": "failure",
                    "duration_s": 0,
                    "energy_kwh": 0
                }
                cursor.execute(
                    "INSERT INTO events VALUES (?, ?, ?, ?, ?)",
                    (event_data["ts"], event_data["machine_id"], event_data["reason_code"],
                     event_data["duration_s"], event_data["energy_kwh"])
                )
                sensor_data["events"].append(event_data)
    
    # Update product movement through the line
    for product in products[:]:
        # Move product through the line
        current_machine_index = 0 if product.current_machine is None else int(product.current_machine[1:])
        
        # If product is not at any machine, put it at source
        if product.current_machine is None:
            product.current_machine = "M1"
            product.process_start_time = current_time
            print(f"Product {product.id} moved to M1")
        
        # If product is at a machine, check if it finishes processing
        machine_id = product.current_machine
        if machine_id in machines:
            machine_info = machines[machine_id]
            if machine_info["status"] == "processing":
                if current_time - machine_info["last_start_time"] >= machine_info["params"]["processing_time_s"]:
                    # Product finishes processing
                    machine_info["status"] = "idle"
                    product.process_end_time = current_time
                    print(f"Product {product.id} finished processing at {machine_id}")
                    
                    # Move to next machine or sink
                    if current_machine_index < 5:  # Not at last machine
                        next_machine_id = f"M{current_machine_index + 2}"
                        product.current_machine = next_machine_id
                        print(f"Product {product.id} moved to {next_machine_id}")
                    else:  # At last machine
                        product.current_machine = "sink"
                        # Product is finished
                        products.remove(product)
                        print(f"Product {product.id} finished at sink")
        
        # If machine is operational and idle, start processing
        if machine_id in machines and machines[machine_id]["is_operational"]:
            if machines[machine_id]["status"] == "idle":
                # Try to start processing if there are products to process
                # For simplicity, assume product is already in machine
                if current_time - product.process_start_time >= 0:
                    machines[machine_id]["status"] = "processing"
                    machines[machine_id]["last_start_time"] = current_time
                    print(f"Product {product.id} started processing at {machine_id}")
    
    # Log sample data
    for machine_id, machine_info in machines.items():
        # Log process time
        cursor.execute(
            "INSERT INTO samples VALUES (?, ?, ?, ?)",
            (current_time, machine_id, "process_time_s", machine_info["params"]["processing_time_s"])
        )
        # Log availability
        cursor.execute(
            "INSERT INTO samples VALUES (?, ?, ?, ?)",
            (current_time, machine_id, "availability_pct", machine_info["params"]["availability_pct"])
        )
        # Log MTTR
        cursor.execute(
            "INSERT INTO samples VALUES (?, ?, ?, ?)",
            (current_time, machine_id, "mttr_s", machine_info["params"]["mttr_s"])
        )
        # Log power
        if machine_info["status"] ==