```python
import pychrono as chrono
import pychrono.irrlicht as irr
import pychrono.fsi as fsi
import numpy as np
import json
import time
import datetime
import sqlite3
from collections import defaultdict

# Initialize PyChrono system
chrono.SetChronoDataPath('path/to/chronodata')  # Set to actual path

# Create the physical system
system = chrono.ChSystemNSC()
system.Set_G_acc(chrono.ChVectorD(0, 0, 0))  # No gravity

# Create ground body
ground = chrono.ChBody()
ground.SetBodyFixed(True)
ground.SetPos(chrono.ChVectorD(0, 0, 0))
system.Add(ground)

# Create material properties
steel_mat = chrono.ChMaterialSurfaceNSC()
steel_mat.SetFriction(0.5)
steel_mat.SetRestitution(0.1)

# Create machine bodies with equipment components
machines = {
    'M1': {'pos': chrono.ChVectorD(0, 0, 0), 'size': chrono.ChVectorD(1, 1, 1)},
    'M2': {'pos': chrono.ChVectorD(2, 0, 0), 'size': chrono.ChVectorD(1, 1, 1)},
    'M3': {'pos': chrono.ChVectorD(4, 0, 0), 'size': chrono.ChVectorD(1, 1, 1)},
    'M4': {'pos': chrono.ChVectorD(6, 0, 0), 'size': chrono.ChVectorD(1, 1, 1)},
    'M5': {'pos': chrono.ChVectorD(8, 0, 0), 'size': chrono.ChVectorD(1, 1, 1)},
    'M6': {'pos': chrono.ChVectorD(10, 0, 0), 'size': chrono.ChVectorD(1, 1, 1)}
}

machine_bodies = {}
for machine_id, params in machines.items():
    body = chrono.ChBody()
    body.SetPos(params['pos'])
    body.SetMass(100)
    body.SetInertiaXX(chrono.ChVectorD(1, 1, 1))
    body.GetCollisionModel().ClearModel()
    body.GetCollisionModel().AddBox(steel_mat, params['size'].x, params['size'].y, params['size'].z)
    body.GetCollisionModel().BuildModel()
    body.SetCollide(True)
    system.Add(body)
    machine_bodies[machine_id] = body

# Create buffers
buffers = {
    'B0': {'pos': chrono.ChVectorD(-1, 0, 0), 'size': chrono.ChVectorD(0.5, 0.5, 0.5)},
    'B1': {'pos': chrono.ChVectorD(1, 0, 0), 'size': chrono.ChVectorD(0.5, 0.5, 0.5)},
    'B2': {'pos': chrono.ChVectorD(3, 0, 0), 'size': chrono.ChVectorD(0.5, 0.5, 0.5)},
    'B3': {'pos': chrono.ChVectorD(5, 0, 0), 'size': chrono.ChVectorD(0.5, 0.5, 0.5)},
    'B4': {'pos': chrono.ChVectorD(7, 0, 0), 'size': chrono.ChVectorD(0.5, 0.5, 0.5)},
    'B5': {'pos': chrono.ChVectorD(9, 0, 0), 'size': chrono.ChVectorD(0.5, 0.5, 0.5)}
}

buffer_bodies = {}
for buffer_id, params in buffers.items():
    body = chrono.ChBody()
    body.SetPos(params['pos'])
    body.SetMass(50)
    body.SetInertiaXX(chrono.ChVectorD(0.5, 0.5, 0.5))
    body.GetCollisionModel().ClearModel()
    body.GetCollisionModel().AddBox(steel_mat, params['size'].x, params['size'].y, params['size'].z)
    body.GetCollisionModel().BuildModel()
    body.SetCollide(True)
    system.Add(body)
    buffer_bodies[buffer_id] = body

# Create part source
source_pos = chrono.ChVectorD(-2, 0, 0)
part_source = chrono.ChBody()
part_source.SetPos(source_pos)
part_source.SetMass(10)
part_source.SetInertiaXX(chrono.ChVectorD(0.1, 0.1, 0.1))
part_source.GetCollisionModel().ClearModel()
part_source.GetCollisionModel().AddSphere(steel_mat, 0.2)
part_source.GetCollisionModel().BuildModel()
part_source.SetCollide(True)
system.Add(part_source)

# Sensor setup - create sensors attached to machines
machine_sensors = {}
for machine_id in machines:
    sensor = chrono.ChSensor()
    sensor.SetName(f"sensor_{machine_id}")
    machine_sensors[machine_id] = sensor

# Database setup
def create_database():
    conn = sqlite3.connect('production_line.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS raw_ingest (
            ingested_at TIMESTAMP NOT NULL,
            source TEXT NOT NULL,
            payload TEXT NOT NULL
        );
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ingest_watermark (
            source TEXT PRIMARY KEY,
            max_event_ts TIMESTAMP
        );
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tag_map (
            tag_id TEXT PRIMARY KEY,
            machine_id TEXT,
            signal TEXT,
            unit TEXT,
            register TEXT,
            scale REAL
        );
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS machines (
            id TEXT PRIMARY KEY,
            processing_time_s REAL,
            availability REAL,
            mttr_s REAL,
            work_power_kw REAL,
            idle_power_kw REAL
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
            processing_time_s REAL,
            availability REAL,
            mttr_s REAL,
            work_power_kw REAL,
            idle_power_kw REAL
        );
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            ts TIMESTAMP NOT NULL,
            machine_id TEXT NOT NULL,
            reason_code TEXT,
            duration_s REAL,
            energy_kwh REAL
        );
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS samples (
            ts TIMESTAMP NOT NULL,
            machine_id TEXT NOT NULL,
            tag TEXT NOT NULL,
            value REAL
        );
    ''')
    
    conn.commit()
    conn.close()

# Insert sample data into database
def insert_initial_data():
    conn = sqlite3.connect('production_line.db')
    cursor = conn.cursor()
    
    # Insert tag_map data
    tag_map_data = [
        ('processing_time_s', 'M1', 'processing_time_s', 's', 'processing_time_s', 1),
        ('availability', 'M1', 'availability', 'dimensionless', 'availability', 1),
        ('mttr_s', 'M1', 'mttr_s', 's', 'mttr_s', 1),
        ('work_power_kw', 'M1', 'work_power_kw', 'kW', 'work_power_kw', 1),
        ('idle_power_kw', 'M1', 'idle_power_kw', 'kW', 'idle_power_kw', 1),
        ('processing_time_s', 'M2', 'processing_time_s', 's', 'processing_time_s', 1),
        ('availability', 'M2', 'availability', 'dimensionless', 'availability', 1),
        ('mttr_s', 'M2', 'mttr_s', 's', 'mttr_s', 1),
        ('work_power_kw', 'M2', 'work_power_kw', 'kW', 'work_power_kw', 1),
        ('idle_power_kw', 'M2', 'idle_power_kw', 'kW', 'idle_power_kw', 1),
        ('processing_time_s', 'M3', 'processing_time_s', 's', 'processing_time_s', 1),
        ('availability', 'M3', 'availability', 'dimensionless', 'availability', 1),
        ('mttr_s', 'M3', 'mttr_s', 's', 'mttr_s', 1),
        ('work_power_kw', 'M3', 'work_power_kw', 'kW', 'work_power_kw', 1),
        ('idle_power_kw', 'M3', 'idle_power_kw', 'kW', 'idle_power_kw', 1),
        ('processing_time_s', 'M4', 'processing_time_s', 's', 'processing_time_s', 1),
        ('availability', 'M4', 'availability', 'dimensionless', 'availability', 1),
        ('mttr_s', 'M4', 'mttr_s', 's', 'mttr_s', 1),
        ('work_power_kw', 'M4', 'work_power_kw', 'kW', 'work_power_kw', 1),
        ('idle_power_kw', 'M4', 'idle_power_kw', 'kW', 'idle_power_kw', 1),
        ('processing_time_s', 'M5', 'processing_time_s', 's', 'processing_time_s', 1),
        ('availability', 'M5', 'availability', 'dimensionless', 'availability', 1),
        ('mttr_s', 'M5', 'mttr_s', 's', 'mttr_s', 1),
        ('work_power_kw', 'M5', 'work_power_kw', 'kW', 'work_power_kw', 1),
        ('idle_power_kw', 'M5', 'idle_power_kw', 'kW', 'idle_power_kw', 1),
        ('processing_time_s', 'M6', 'processing_time_s', 's', 'processing_time_s', 1),
        ('availability', 'M6', 'availability', 'dimensionless', 'availability', 1),
        ('mttr_s', 'M6', 'mttr_s', 's', 'mttr_s', 1),
        ('work_power_kw', 'M6', 'work_power_kw', 'kW', 'work_power_kw', 1),
        ('idle_power_kw', 'M6', 'idle_power_kw', 'kW', 'idle_power_kw', 1)
    ]
    
    cursor.executemany('''
        INSERT OR REPLACE INTO tag_map (tag_id, machine_id, signal, unit, register, scale)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', tag_map_data)
    
    # Insert machines data
    machines_data = [
        ('M1', 200, 0.97, 900, 5.0, 0.5),
        ('M2', 220, 0.97, 1000, 5.5, 0.55),
        ('M3', 240, 0.96, 1200, 6.0, 0.6),
        ('M4', 260, 0.96, 1400, 7.0, 0.7),
        ('M5', 230, 0.97, 1100, 6.5, 0.65),
        ('M6', 210, 0.97, 1000, 6.0, 0.6)
    ]
    
    cursor.executemany('''
        INSERT OR REPLACE INTO machines (id, processing_time_s, availability, mttr_s, work_power_kw, idle_power_kw)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', machines_data)
    
    # Insert buffers data
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
    
    # Insert stations data
    cursor.executemany('''
        INSERT OR REPLACE INTO stations (id, processing_time_s, availability, mttr_s, work_power_kw, idle_power_kw)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', machines_data)
    
    conn.commit()
    conn.close()

# Simulate machine operation
class Machine:
    def __init__(self, name, processing_time, availability, mttr):
        self.name = name
        self.processing_time = processing_time
        self.availability = availability
        self.mttr = mttr
        self.is_operational = True
        self.time_operational = 0
        self.time_down = 0
        self.processing_start = None
        self.current_part = None
        self.production_count = 0
        self.energy_consumption = 0.0
        
    def update(self, dt):
        if self.is_operational:
            self.time_operational += dt
            if self.processing_start is not None:
                elapsed = time.time() - self.processing_start
                if elapsed >= self.processing_time:
                    self.complete_processing()
        else:
            self.time_down += dt
            if self.time_down >= self.mttr:
                self.restart()
    
    def start_processing(self, part):
        self.processing_start = time.time()
        self.current_part = part