import numpy as np
import pychrono as chrono
import pychrono.irrlicht as irr
import json
import time
import datetime
import sqlite3
from collections import defaultdict

# Initialize Chrono system
chrono.SetChronoDataPath('/usr/local/share/chrono/data/')
chrono.SetChronoDataPath('/opt/chrono/data/')

# Create system
system = chrono.ChSystemNSC()
system.Set_G_acc(chrono.ChVectorD(0, -9.81, 0))  # Set gravity

# Create materials
steel_mat = chrono.ChMaterialSurfaceNSC()
steel_mat.SetFriction(0.5)
steel_mat.SetRestitution(0.1)

refractory_mat = chrono.ChMaterialSurfaceNSC()
refractory_mat.SetFriction(0.3)
refractory_mat.SetRestitution(0.05)

# Setup database connection
conn = sqlite3.connect('digital_twin.db')
cursor = conn.cursor()

# Create tables if they don't exist
cursor.execute('''CREATE TABLE IF NOT EXISTS raw_ingest (
    ingested_at timestamptz NOT NULL,
    source text NOT NULL,
    payload jsonb NOT NULL
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS tag_map (
    tag_id text PRIMARY KEY,
    machine_id text NOT NULL,
    signal text NOT NULL,
    unit text NOT NULL,
    register text NOT NULL,
    scale double precision NOT NULL
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS machines (
    id text PRIMARY KEY,
    name text NOT NULL
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS buffers (
    id text PRIMARY KEY,
    capacity int NOT NULL,
    before text NOT NULL,
    after text NOT NULL
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS stations (
    id text PRIMARY KEY,
    processing_time_s double precision NOT NULL,
    availability_pct double precision NOT NULL,
    mttr_s double precision NOT NULL,
    power_working_kw double precision NOT NULL,
    power_idle_kw double precision NOT NULL
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS events (
    ts timestamptz NOT NULL,
    machine_id text NOT NULL,
    reason_code text NOT NULL,
    duration_s double precision NOT NULL,
    energy_kwh double precision NOT NULL
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS samples (
    ts timestamptz NOT NULL,
    machine_id text NOT NULL,
    tag text NOT NULL,
    value double precision NOT NULL
)''')

cursor.execute('''CREATE INDEX IF NOT EXISTS idx_raw_ingest_source ON raw_ingest(source)''')
cursor.execute('''CREATE INDEX IF NOT EXISTS idx_raw_ingest_ingested_at ON raw_ingest(ingested_at)''')
cursor.execute('''CREATE INDEX IF NOT EXISTS idx_tag_map_machine_id ON tag_map(machine_id)''')
cursor.execute('''CREATE INDEX IF NOT EXISTS idx_tag_map_tag_id ON tag_map(tag_id)''')
cursor.execute('''CREATE INDEX IF NOT EXISTS idx_events_machine_id ON events(machine_id)''')
cursor.execute('''CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts)''')
cursor.execute('''CREATE INDEX IF NOT EXISTS idx_samples_machine_id ON samples(machine_id)''')
cursor.execute('''CREATE INDEX IF NOT EXISTS idx_samples_tag ON samples(tag)''')

# Insert dimension data
cursor.execute("INSERT OR REPLACE INTO machines (id, name) VALUES ('M1', 'M1'), ('M2', 'M2'), ('M3', 'M3'), ('B0', 'B0'), ('B1', 'B1'), ('B2', 'B2')")
cursor.execute("INSERT OR REPLACE INTO buffers (id, capacity, before, after) VALUES ('B0', 15, 'source', 'M1'), ('B1', 5, 'M1', 'M2'), ('B2', 5, 'M2', 'M3')")
cursor.execute("INSERT OR REPLACE INTO stations (id, processing_time_s, availability_pct, mttr_s, power_working_kw, power_idle_kw) VALUES ('M1', 90, 99.55, 392.5, 3.0, 0.3), ('M2', 70, 100.0, 1.0, 4.5, 0.45), ('M3', 110, 100.0, 1.0, 6.0, 0.6)")
cursor.execute("INSERT OR REPLACE INTO tag_map (tag_id, machine_id, signal, unit, register, scale) VALUES ('M1_temp', 'M1', 'temperature', 'C', 'temp', 1.0), ('M1_pressure', 'M1', 'pressure', 'bar', 'pressure', 1.0), ('M2_temp', 'M2', 'temperature', 'C', 'temp', 1.0), ('M2_pressure', 'M2', 'pressure', 'bar', 'pressure', 1.0), ('M3_temp', 'M3', 'temperature', 'C', 'temp', 1.0), ('M3_pressure', 'M3', 'pressure', 'bar', 'pressure', 1.0), ('B0_level', 'B0', 'level', 'L', 'level', 1.0), ('B1_level', 'B1', 'level', 'L', 'level', 1.0), ('B2_level', 'B2', 'level', 'L', 'level', 1.0)")

conn.commit()

# Define station parameters
stations_data = {
    "M1": {"processing_time_s": 90, "availability_pct": 99.55, "mttr_s": 392.5, "power_working_kw": 3.0, "power_idle_kw": 0.3},
    "M2": {"processing_time_s": 70, "availability_pct": 100.0, "mttr_s": 1.0, "power_working_kw": 4.5, "power_idle_kw": 0.45},
    "M3": {"processing_time_s": 110, "availability_pct": 100.0, "mttr_s": 1.0, "power_working_kw": 6.0, "power_idle_kw": 0.6}
}

buffers_data = {
    "B0": {"capacity": 15, "before": "source", "after": "M1"},
    "B1": {"capacity": 5, "before": "M1", "after": "M2"},
    "B2": {"capacity": 5, "before": "M2", "after": "M3"}
}

# Create buffers as rigid bodies
buffers = {}
for buf_id, buf_data in buffers_data.items():
    body = chrono.ChBodyEasyBox(1, 1, 1, 1000, True, True)
    body.SetPos(chrono.ChVectorD(0, 0, 0))
    body.SetMaterialSurface(steel_mat)
    system.Add(body)
    buffers[buf_id] = {
        "body": body,
        "capacity": buf_data["capacity"],
        "level": 0
    }

# Create stations as rigid bodies
stations = {}
for station_id, params in stations_data.items():
    body = chrono.ChBodyEasyBox(1, 1, 1, 1000, True, True)
    body.SetPos(chrono.ChVectorD(0, 0, 0))
    body.SetMaterialSurface(steel_mat)
    system.Add(body)
    stations[station_id] = {
        "body": body,
        "processing_time": params["processing_time_s"],
        "availability": params["availability_pct"] / 100.0,
        "mttr": params["mttr_s"],
        "power_working": params["power_working_kw"],
        "power_idle": params["power_idle_kw"],
        "status": "running",  # Assume initially running
        "next_process": 0,
        "energy_consumed": 0.0,
        "events": []
    }

# Create source (item generator)
source_timer = 0
item_count = 0

# Create an item
def create_item():
    global item_count
    item_count += 1
    body = chrono.ChBodyEasyBox(0.5, 0.5, 0.5, 100, True, True)
    body.SetPos(chrono.ChVectorD(0, 1, 0))
    body.SetMaterialSurface(steel_mat)
    system.Add(body)
    return body

# Initialize items
items = []
for _ in range(10):
    items.append(create_item())

# Sensor system
sensors = {}

# Log data to database
def log_to_db(table, data):
    timestamp = datetime.datetime.now(datetime.timezone.utc)
    if table == "raw_ingest":
        cursor.execute(
            "INSERT INTO raw_ingest (ingested_at, source, payload) VALUES (?, ?, ?)",
            (timestamp, data["source"], json.dumps(data["payload"]))
        )
    elif table == "events":
        cursor.execute(
            "INSERT INTO events (ts, machine_id, reason_code, duration_s, energy_kwh) VALUES (?, ?, ?, ?, ?)",
            (timestamp, data["machine_id"], data["reason_code"], data["duration_s"], data["energy_kwh"])
        )
    elif table == "samples":
        cursor.execute(
            "INSERT INTO samples (ts, machine_id, tag, value) VALUES (?, ?, ?, ?)",
            (timestamp, data["machine_id"], data["tag"], data["value"])
        )
    conn.commit()

# Simulation parameters
sim_time = 0
max_time = 432000  # 5 days
dt = 0.01
log_interval = 1.0

# Main simulation loop
while sim_time < max_time:
    # Source item generation
    source_timer += dt
    if source_timer >= 60:  # 60 second interval
        item = create_item()
        items.append(item)
        source_timer = 0
        print(f"Generated item {item_count} at time {sim_time}")

    # Process items through the production line
    for item in items:
        # Move items through buffers and stations
        item_pos = item.GetPos()
        current_x = item_pos.x

        # Determine which station/buffer this item is in
        # Simple logic for demonstration
        if current_x < 5:  # Before first station
            # Move towards first station
            item.SetPos(chrono.ChVectorD(current_x + 0.1 * dt, item_pos.y, item_pos.z))
        elif current_x < 10:  # First station area
            # Station processing
            if "M1" in stations:
                station = stations["M1"]
                if station["next_process"] <= sim_time:
                    # Process item
                    station["next_process"] = sim_time + station["processing_time"]
                    print(f"Item processed by M1 at time {sim_time}")
                    # Simulate energy consumption
                    station["energy_consumed"] += station["power_working"] * station["processing_time"] / 3600.0
                    # Log sensor data
                    log_to_db("samples", {
                        "machine_id": "M1",
                        "tag": "M1_temp",
                        "value": 89.98
                    })
                    log_to_db("samples", {
                        "machine_id": "M1",
                        "tag": "M1_pressure",
                        "value": 12.5
                    })
        elif current_x < 15:  # Between stations
            # Move towards next
            item.SetPos(chrono.ChVectorD(current_x + 0.1 * dt, item_pos.y, item_pos.z))
        else:  # After final station
            # Remove item
            items.remove(item)
            print(f"Item finished at time {sim_time}")

    # Update station statuses and log data
    for station_id, station in stations.items():
        # Simulate availability and MTTR
        if station["status"] == "running" and np.random.random() > station["availability"]:
            station["status"] = "down"
            # Log failure event
            event_data = {
                "machine_id": station_id,
                "reason_code": "FAILURE",
                "duration_s": station["mttr"],
                "energy_kwh": station["energy_consumed"]
            }
            log_to_db("events", event_data)
            print(f"{station_id} failed at time {sim_time}")

        elif station["status"] == "down" and np.random.random() > 0.999:
            station["status"] = "running"
            print(f"{station_id} recovered at time {sim_time}")

        # Log sensor data
        if station_id == "M1":
            log_to_db("samples", {
                "machine_id": station_id,
                "tag": "M1_temp",
                "value": 89.98
            })
            log_to_db("samples", {
                "machine_id": station_id,
                "tag": "M1_pressure",
                "value": 12.5
            })
        elif station_id == "M2":
            log_to_db("samples", {
                "machine_id": station_id,
                "tag": "M2_temp",
                "value": 69.98
            })
            log_to_db("samples", {
                "machine_id": station_id,
                "tag": "M2_pressure",
                "value": 11.2
            })
        elif station_id == "M3":
            log_to_db("samples", {
                "machine_id": station_id,
                "tag": "M3_temp",
                "value": 110.28
            })
            log_to_db("samples", {
                "machine_id": station_id,
                "tag": "M3_pressure",
