```python
import pychrono as chrono
import pychrono.irrlicht as irr
import math
import numpy as np
import time
import json
from datetime import datetime, timezone
import sqlite3

# Initialize PyChrono system
chrono.SetLogToConsole(True)
chrono.SetLogToFile("chrono_simulation.log")

# Create the physical system
system = chrono.ChSystemNSC()
system.Set_G_acc(chrono.ChVectorD(0, 0, 0))  # No gravity for this setup

# Create materials
material_steel = chrono.ChMaterialSurfaceNSC()
material_steel.SetFriction(0.4)
material_steel.SetRestitution(0.1)

material_refractory = chrono.ChMaterialSurfaceNSC()
material_refractory.SetFriction(0.3)
material_refractory.SetRestitution(0.05)

# Create ground
ground = chrono.ChBody()
ground.SetBodyFixed(True)
ground.SetPos(chrono.ChVectorD(0, -1, 0))
system.Add(ground)

# Create ground shape
ground_shape = chrono.ChTriangleMeshConnected()
ground_shape.LoadWavefrontMesh(chrono.GetChronoDataFile("models/ground.obj"), False, True)
ground_shape.SetScale(chrono.ChVectorD(10, 1, 10))

ground_collision = chrono.ChTriangleMeshShape()
ground_collision.SetMesh(ground_shape)
ground_collision.SetBody(ground)
ground.AddAsset(ground_collision)

# Create a simple chamber for the furnace
furnace_chamber = chrono.ChBody()
furnace_chamber.SetPos(chrono.ChVectorD(0, 0, 0))
furnace_chamber.SetMass(100)
furnace_chamber.SetInertiaXX(chrono.ChVectorD(10, 10, 10))
system.Add(furnace_chamber)

# Create furnace chamber geometry
furnace_shape = chrono.ChBoxShape()
furnace_shape.GetBoxGeometry().Size = chrono.ChVectorD(2, 1, 2)
furnace_shape.SetBody(furnace_chamber)
furnace_chamber.AddAsset(furnace_shape)

# Create furnace material
furnace_material = chrono.ChMaterialSurfaceNSC()
furnace_material.SetFriction(0.2)
furnace_material.SetRestitution(0.01)
furnace_chamber.GetAssets().front().SetMaterial(0, furnace_material)

# Create a crystallizer body
crystallizer = chrono.ChBody()
crystallizer.SetPos(chrono.ChVectorD(4, 0, 0))
crystallizer.SetMass(100)
crystallizer.SetInertiaXX(chrono.ChVectorD(10, 10, 10))
system.Add(crystallizer)

# Create crystallizer geometry
crystallizer_shape = chrono.ChBoxShape()
crystallizer_shape.GetBoxGeometry().Size = chrono.ChVectorD(2, 1, 2)
crystallizer_shape.SetBody(crystallizer)
crystallizer.AddAsset(crystallizer_shape)

# Create crystallizer material
crystallizer_material = chrono.ChMaterialSurfaceNSC()
crystallizer_material.SetFriction(0.3)
crystallizer_material.SetRestitution(0.02)
crystallizer.AddAsset(crystallizer_material)

# Create a roller body
roller = chrono.ChBody()
roller.SetPos(chrono.ChVectorD(8, 0, 0))
roller.SetMass(100)
roller.SetInertiaXX(chrono.ChVectorD(10, 10, 10))
system.Add(roller)

# Create roller geometry
roller_shape = chrono.ChCylinderShape()
roller_shape.GetCylinderGeometry().rad = 0.5
roller_shape.GetCylinderGeometry().p1 = chrono.ChVectorD(0, 0.5, 0)
roller_shape.GetCylinderGeometry().p2 = chrono.ChVectorD(0, -0.5, 0)
roller_shape.SetBody(roller)
roller.AddAsset(roller_shape)

# Create roller material
roller_material = chrono.ChMaterialSurfaceNSC()
roller_material.SetFriction(0.4)
roller_material.SetRestitution(0.01)
roller.AddAsset(roller_material)

# Create the production line components
# First buffer (B0)
buffer0 = chrono.ChBody()
buffer0.SetPos(chrono.ChVectorD(-2, 0, 0))
buffer0.SetMass(50)
buffer0.SetInertiaXX(chrono.ChVectorD(5, 5, 5))
system.Add(buffer0)

# Create buffer0 geometry
buffer0_shape = chrono.ChBoxShape()
buffer0_shape.GetBoxGeometry().Size = chrono.ChVectorD(1, 0.2, 1)
buffer0_shape.SetBody(buffer0)
buffer0.AddAsset(buffer0_shape)

# Create buffer0 material
buffer0_material = chrono.ChMaterialSurfaceNSC()
buffer0_material.SetFriction(0.2)
buffer0_material.SetRestitution(0.01)
buffer0.AddAsset(buffer0_material)

# Second buffer (B1)
buffer1 = chrono.ChBody()
buffer1.SetPos(chrono.ChVectorD(2, 0, 0))
buffer1.SetMass(50)
buffer1.SetInertiaXX(chrono.ChVectorD(5, 5, 5))
system.Add(buffer1)

# Create buffer1 geometry
buffer1_shape = chrono.ChBoxShape()
buffer1_shape.GetBoxGeometry().Size = chrono.ChVectorD(1, 0.2, 1)
buffer1_shape.SetBody(buffer1)
buffer1.AddAsset(buffer1_shape)

# Create buffer1 material
buffer1_material = chrono.ChMaterialSurfaceNSC()
buffer1_material.SetFriction(0.2)
buffer1_material.SetRestitution(0.01)
buffer1.AddAsset(buffer1_material)

# Create a product item
product = chrono.ChBody()
product.SetPos(chrono.ChVectorD(-5, 0.5, 0))
product.SetMass(10)
product.SetInertiaXX(chrono.ChVectorD(1, 1, 1))
system.Add(product)

# Create product geometry
product_shape = chrono.ChBoxShape()
product_shape.GetBoxGeometry().Size = chrono.ChVectorD(0.5, 0.5, 0.5)
product_shape.SetBody(product)
product.AddAsset(product_shape)

# Create joints
# Joint between product and buffer0
joint_product_buffer = chrono.ChLinkLockRevolute()
joint_product_buffer.Initialize(buffer0, product, chrono.ChVectorD(-2, 0.5, 0))
system.Add(joint_product_buffer)

# Joint between buffer0 and furnace
joint_buffer_furnace = chrono.ChLinkLockRevolute()
joint_buffer_furnace.Initialize(buffer0, furnace_chamber, chrono.ChVectorD(0, 0, 0))
system.Add(joint_buffer_furnace)

# Joint between furnace and crystallizer
joint_furnace_crystallizer = chrono.ChLinkLockRevolute()
joint_furnace_crystallizer.Initialize(furnace_chamber, crystallizer, chrono.ChVectorD(2, 0, 0))
system.Add(joint_furnace_crystallizer)

# Joint between crystallizer and roller
joint_crystallizer_roller = chrono.ChLinkLockRevolute()
joint_crystallizer_roller.Initialize(crystallizer, roller, chrono.ChVectorD(2, 0, 0))
system.Add(joint_crystallizer_roller)

# Joint between roller and buffer1
joint_roller_buffer = chrono.ChLinkLockRevolute()
joint_roller_buffer.Initialize(roller, buffer1, chrono.ChVectorD(2, 0, 0))
system.Add(joint_roller_buffer)

# Create a sensor to monitor the product movement
class ProductionSensor:
    def __init__(self, machine_id, parameter, value):
        self.machine_id = machine_id
        self.parameter = parameter
        self.value = value
        self.timestamp = datetime.now(timezone.utc)
        
    def get_data(self):
        return {
            'machine_id': self.machine_id,
            'parameter': self.parameter,
            'value': self.value,
            'timestamp': self.timestamp.isoformat()
        }

# Initialize sensors
sensors = []
sensors.append(ProductionSensor('M1', 'processing_time_s', 60))
sensors.append(ProductionSensor('M1', 'availability', 0.995))
sensors.append(ProductionSensor('M1', 'mttr_s', 300))
sensors.append(ProductionSensor('M1', 'power_working_kw', 3.0))
sensors.append(ProductionSensor('M2', 'processing_time_s', 80))
sensors.append(ProductionSensor('M2', 'availability', 0.99))
sensors.append(ProductionSensor('M2', 'mttr_s', 600))
sensors.append(ProductionSensor('M2', 'power_working_kw', 5.0))
sensors.append(ProductionSensor('M3', 'processing_time_s', 70))
sensors.append(ProductionSensor('M3', 'availability', 0.99))
sensors.append(ProductionSensor('M3', 'mttr_s', 600))
sensors.append(ProductionSensor('M3', 'power_working_kw', 4.5))
sensors.append(ProductionSensor('M4', 'processing_time_s', 75))
sensors.append(ProductionSensor('M4', 'availability', 0.995))
sensors.append(ProductionSensor('M4', 'mttr_s', 300))
sensors.append(ProductionSensor('M4', 'power_working_kw', 4.0))

# Initialize SQLite database
def init_database():
    conn = sqlite3.connect('digital_twin.db')
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''CREATE TABLE IF NOT EXISTS machines (
        id TEXT PRIMARY KEY,
        processing_time_s DOUBLE PRECISION,
        availability DOUBLE PRECISION,
        mttr_s DOUBLE PRECISION,
        power_working_kw DOUBLE PRECISION,
        power_idle_kw DOUBLE PRECISION
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS buffers (
        id TEXT PRIMARY KEY,
        capacity INTEGER
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS stations (
        id TEXT PRIMARY KEY,
        processing_time_s DOUBLE PRECISION,
        availability DOUBLE PRECISION,
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
        ingested_at TIMESTAMPTZ NOT NULL,
        source TEXT NOT NULL,
        payload JSONB NOT NULL
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS ingest_watermark (
        source TEXT PRIMARY KEY,
        max_event_ts TIMESTAMPTZ
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS events (
        ts TIMESTAMPTZ NOT NULL,
        machine_id TEXT NOT NULL,
        reason_code TEXT,
        duration_s DOUBLE PRECISION,
        energy_kwh DOUBLE PRECISION
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS samples (
        ts TIMESTAMPTZ NOT NULL,
        machine_id TEXT NOT NULL,
        tag TEXT NOT NULL,
        value DOUBLE PRECISION
    )''')
    
    # Create indexes
    cursor.execute('''CREATE INDEX IF NOT EXISTS idx_events_machine_ts ON events (machine_id, ts)''')
    cursor.execute('''CREATE INDEX IF NOT EXISTS idx_samples_machine_ts ON samples (machine_id, ts)''')
    
    # Insert default data
    machines_data = [
        ('M1', 60, 0.995, 300, 3.0, 0.3),
        ('M2', 80, 0.99, 600, 5.0, 0.5),
        ('M3', 70, 0.99, 600, 4.5, 0.45),
        ('M4', 75, 0.995, 300, 4.0, 0.4)
    ]
    
    buffers_data = [
        ('B0', 25),
        ('B1', 10),
        ('B2', 10),
        ('B3', 10)
    ]
    
    stations_data = machines_data
    
    tag_map_data = [
        ('M1_proc_time', 'M1', 'processing_time_s', 's', 'proc_time', 1),
        ('M1_avail', 'M1', 'availability', 'ratio', 'avail', 1),
        ('M1_mttr', 'M1', 'mttr_s', 's', 'mttr', 1),
        ('M1_power_w', 'M1', 'power_working_kw', 'kW', 'power_w', 1),
        ('M2_proc_time', 'M2', 'processing_time_s', 's', 'proc_time', 1),
        ('M2_avail', 'M2', 'availability', 'ratio', 'avail', 1),
        ('M2_mttr', 'M2', 'mttr_s', 's', 'mttr', 1),
        ('M2_power_w', 'M2', 'power_working_kw', 'kW', 'power_w', 1),
        ('M3_proc_time', 'M3', 'processing_time_s', 's', 'proc_time', 1),
        ('M3_avail', 'M3', 'availability', 'ratio', 'avail', 1),
        ('M3_mttr', 'M3', 'mttr_s',