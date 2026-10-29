```python
import pychrono as chrono
import pychrono.irrlicht as irr
import pychrono.fsi as fsi
import math
import json
import time
import datetime
import sqlite3
import numpy as np

# Initialize PyChrono system
chrono.SetChronoDataPath("../../../data/")
chrono.SetChronoDataPath("../../../data/")

# Create the physical system
system = chrono.ChSystemNSC()
system.Set_G_acc(chrono.ChVectorD(0, 0, 0))  # No gravity for this model

# Create materials
steel_mat = chrono.ChMaterialSurfaceNSC()
steel_mat.SetFriction(0.4)
steel_mat.SetRestitution(0.1)

refractory_mat = chrono.ChMaterialSurfaceNSC()
refractory_mat.SetFriction(0.3)
refractory_mat.SetRestitution(0.05)

# Create terrain (ground plane)
ground = chrono.ChBody()
ground.SetBodyFixed(True)
ground.SetPos(chrono.ChVectorD(0, -1, 0))
system.Add(ground)

# Create ground shape
ground_shape = chrono.ChTriangleMeshConnected()
ground_shape.LoadWavefrontMesh(chrono.GetChronoDataFile("models/ground.obj"), False, True)
ground_shape.Transform(chrono.ChVectorD(0, 0, 0), chrono.ChMatrix33D(1))
ground_shape.GetMaterialSurface() = refractory_mat
ground.AddAsset(chrono.ChVisualAsset(ground_shape))

# Create machines (M1, M2, M3)
machines = {}
buffers = {}

# Machine parameters from requirements
machine_params = [
    {
        "id": "M1",
        "processing_time_s": 90,
        "availability": 0.99,
        "mttr_s": 600,
        "work_power_kw": 3.0,
        "idle_power_kw": 0.3
    },
    {
        "id": "M2",
        "processing_time_s": 70,
        "availability": 0.98,
        "mttr_s": 900,
        "work_power_kw": 4.5,
        "idle_power_kw": 0.45
    },
    {
        "id": "M3",
        "processing_time_s": 110,
        "availability": 0.99,
        "mttr_s": 1200,
        "work_power_kw": 6.0,
        "idle_power_kw": 0.6
    }
]

# Buffer parameters from requirements
buffer_params = [
    {"id": "B0", "capacity": 15},
    {"id": "B1", "capacity": 5},
    {"id": "B2", "capacity": 5}
]

# Create machine bodies
for param in machine_params:
    machine = chrono.ChBody()
    machine.SetPos(chrono.ChVectorD(0, 0, 0))
    machine.SetMass(1000)
    machine.SetInertiaXX(chrono.ChVectorD(100, 100, 100))
    machine.SetMaterialSurface(steel_mat)
    system.Add(machine)
    machines[param["id"]] = machine

# Create buffer bodies
for param in buffer_params:
    buffer = chrono.ChBody()
    buffer.SetPos(chrono.ChVectorD(0, 0, 0))
    buffer.SetMass(50)
    buffer.SetInertiaXX(chrono.ChVectorD(10, 10, 10))
    buffer.SetMaterialSurface(steel_mat)
    system.Add(buffer)
    buffers[param["id"]] = buffer

# Create production line setup
# Position machines and buffers in a serial line
machine_positions = [chrono.ChVectorD(0, 0, 0), chrono.ChVectorD(2, 0, 0), chrono.ChVectorD(4, 0, 0)]
buffer_positions = [chrono.ChVectorD(1, 0, 0), chrono.ChVectorD(3, 0, 0)]

for i, (machine_id, machine) in enumerate(machines.items()):
    machine.SetPos(machine_positions[i])
    machine.SetRot(chrono.QUNIT)

for i, (buffer_id, buffer) in enumerate(buffers.items()):
    buffer.SetPos(buffer_positions[i])
    buffer.SetRot(chrono.QUNIT)

# Create source (input part generator)
source_part = chrono.ChBody()
source_part.SetPos(chrono.ChVectorD(-1, 0, 0))
source_part.SetMass(10)
source_part.SetInertiaXX(chrono.ChVectorD(1, 1, 1))
source_part.SetMaterialSurface(steel_mat)
system.Add(source_part)

# Create product (output part)
product_part = chrono.ChBody()
product_part.SetPos(chrono.ChVectorD(5, 0, 0))
product_part.SetMass(10)
product_part.SetInertiaXX(chrono.ChVectorD(1, 1, 1))
product_part.SetMaterialSurface(steel_mat)
system.Add(product_part)

# Create constraints/joints between machines and buffers
# Connect source to M1
source_joint = chrono.ChLinkLockLock()
source_joint.Initialize(source_part, machines["M1"], chrono.ChFrameD(chrono.ChVectorD(0, 0, 0), chrono.QUNIT))
system.Add(source_joint)

# Connect M1 to B1
m1b1_joint = chrono.ChLinkLockLock()
m1b1_joint.Initialize(machines["M1"], buffers["B1"], chrono.ChFrameD(chrono.ChVectorD(0, 0, 0), chrono.QUNIT))
system.Add(m1b1_joint)

# Connect B1 to M2
b1m2_joint = chrono.ChLinkLockLock()
b1m2_joint.Initialize(buffers["B1"], machines["M2"], chrono.ChFrameD(chrono.ChVectorD(0, 0, 0), chrono.QUNIT))
system.Add(b1m2_joint)

# Connect M2 to B2
m2b2_joint = chrono.ChLinkLockLock()
m2b2_joint.Initialize(machines["M2"], buffers["B2"], chrono.ChFrameD(chrono.ChVectorD(0, 0, 0), chrono.QUNIT))
system.Add(m2b2_joint)

# Connect B2 to M3
b2m3_joint = chrono.ChLinkLockLock()
b2m3_joint.Initialize(buffers["B2"], machines["M3"], chrono.ChFrameD(chrono.ChVectorD(0, 0, 0), chrono.QUNIT))
system.Add(b2m3_joint)

# Connect M3 to product
m3product_joint = chrono.ChLinkLockLock()
m3product_joint.Initialize(machines["M3"], product_part, chrono.ChFrameD(chrono.ChVectorD(0, 0, 0), chrono.QUNIT))
system.Add(m3product_joint)

# Define part generation function
def generate_part():
    part = chrono.ChBody()
    part.SetPos(chrono.ChVectorD(-1, 0, 0))
    part.SetMass(10)
    part.SetInertiaXX(chrono.ChVectorD(1, 1, 1))
    part.SetMaterialSurface(steel_mat)
    return part

# Define sensor class for logging data
class SensorLogger:
    def __init__(self, db_path="digital_twin.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS machines (
                id TEXT PRIMARY KEY,
                processing_time_s DOUBLE PRECISION,
                availability DOUBLE PRECISION,
                mttr_s DOUBLE PRECISION,
                work_power_kw DOUBLE PRECISION,
                idle_power_kw DOUBLE PRECISION
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS buffers (
                id TEXT PRIMARY KEY,
                capacity INTEGER
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tag_map (
                tag_id TEXT PRIMARY KEY,
                machine_id TEXT,
                signal TEXT,
                unit TEXT,
                register TEXT,
                scale DOUBLE PRECISION
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS raw_ingest (
                ingested_at TIMESTAMPTZ NOT NULL,
                source TEXT NOT NULL,
                payload JSONB NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                ts TIMESTAMPTZ NOT NULL,
                machine_id TEXT NOT NULL,
                reason_code TEXT,
                duration_s DOUBLE PRECISION,
                energy_kwh DOUBLE PRECISION
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS samples (
                ts TIMESTAMPTZ NOT NULL,
                machine_id TEXT NOT NULL,
                tag TEXT NOT NULL,
                value DOUBLE PRECISION
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_machine_ts ON events (machine_id, ts);
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_samples_machine_ts ON samples (machine_id, ts);
        """)
        
        # Insert machine data
        for param in machine_params:
            cursor.execute("""
                INSERT OR REPLACE INTO machines (id, processing_time_s, availability, mttr_s, work_power_kw, idle_power_kw)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (param["id"], param["processing_time_s"], param["availability"], 
                  param["mttr_s"], param["work_power_kw"], param["idle_power_kw"]))
        
        # Insert buffer data
        for param in buffer_params:
            cursor.execute("""
                INSERT OR REPLACE INTO buffers (id, capacity)
                VALUES (?, ?)
            """, (param["id"], param["capacity"]))
        
        # Insert tag map data
        tags = [
            ("processing_time_s", "M1", "processing_time_s", "s", "processing_time_s", 1.0),
            ("availability", "M1", "availability", "unitless", "availability", 1.0),
            ("mttr_s", "M1", "mttr_s", "s", "mttr_s", 1.0),
            ("work_power_kw", "M1", "work_power_kw", "kW", "work_power_kw", 1.0),
            ("idle_power_kw", "M1", "idle_power_kw", "kW", "idle_power_kw", 1.0),
            ("buffer_capacity", "B0", "buffer_capacity", "unitless", "buffer_capacity", 1.0),
            ("processing_time_s", "M2", "processing_time_s", "s", "processing_time_s", 1.0),
            ("availability", "M2", "availability", "unitless", "availability", 1.0),
            ("mttr_s", "M2", "mttr_s", "s", "mttr_s", 1.0),
            ("work_power_kw", "M2", "work_power_kw", "kW", "work_power_kw", 1.0),
            ("idle_power_kw", "M2", "idle_power_kw", "kW", "idle_power_kw", 1.0),
            ("processing_time_s", "M3", "processing_time_s", "s", "processing_time_s", 1.0),
            ("availability", "M3", "availability", "unitless", "availability", 1.0),
            ("mttr_s", "M3", "mttr_s", "s", "mttr_s", 1.0),
            ("work_power_kw", "M3", "work_power_kw", "kW", "work_power_kw", 1.0),
            ("idle_power_kw", "M3", "idle_power_kw", "kW", "idle_power_kw", 1.0),
        ]
        
        for tag in tags:
            cursor.execute("""
                INSERT OR REPLACE INTO tag_map (tag_id, machine_id, signal, unit, register, scale)
                VALUES (?, ?, ?, ?, ?, ?)
            """, tag)
        
        conn.commit()
        conn.close()
    
    def log_machine_data(self, machine_id, processing_time_s, availability, mttr_s, work_power_kw, idle_power_kw):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        timestamp = datetime.datetime.now()
        
        cursor.execute("""
            INSERT INTO samples (ts, machine_id, tag, value)
            VALUES (?, ?, ?, ?)
        """, (timestamp, machine_id, "processing_time_s", processing_time_s))
        
        cursor.execute("""
            INSERT INTO samples (ts, machine_id, tag, value)
            VALUES (?, ?, ?, ?)
        """, (timestamp, machine_id, "availability", availability))
        
        cursor.execute("""
            INSERT INTO samples (ts, machine_id, tag, value)
            VALUES (?, ?, ?, ?)
        """, (timestamp, machine_id, "mttr_s", mttr_s))
        
        cursor.execute("""
            INSERT INTO samples (ts, machine_id, tag, value)
            VALUES (?, ?, ?, ?)
        """, (timestamp, machine_id, "work_power_kw", work_power_kw))
        
        cursor.execute("""
            INSERT INTO samples (ts, machine_id, tag, value)
            VALUES (?, ?, ?, ?)
        """, (timestamp, machine_id, "idle_power_kw", idle_power_kw))
        
        conn.commit()
        conn.close()
    
    def log_buffer_data(self, buffer_id, capacity):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        timestamp = datetime.datetime.now()
        
        cursor.execute("""
            INSERT INTO samples (ts, machine_id, tag, value)
            VALUES (?, ?, ?, ?)
        """, (timestamp, buffer_id, "buffer_capacity", capacity))
        
        conn.commit()
        conn.close()
    
    def log_event(self, machine_id, reason_code, duration_s, energy_kwh):
        conn = sqlite3.connect(self.db_path)
        cursor =