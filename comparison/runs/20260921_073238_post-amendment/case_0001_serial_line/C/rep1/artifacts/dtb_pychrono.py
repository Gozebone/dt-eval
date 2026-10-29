```python
import pychrono as chrono
import pychrono.irrlicht as chronoirr
import math
import time
import json
import datetime
import sqlite3
from datetime import datetime, timezone
from collections import defaultdict

# Initialize PyChrono system
chrono.SetChronoDataPath("path/to/chrono/data")  # Adjust path as needed
system = chrono.ChSystemNSC()

# Set gravity
system.Set_G_acc(chrono.ChVectorD(0, -9.81, 0))

# Create database connection
conn = sqlite3.connect('digital_twin.db')
cursor = conn.cursor()

# Create tables if they don't exist
cursor.execute('''CREATE TABLE IF NOT EXISTS machines (
                    id TEXT PRIMARY KEY,
                    process_time_s INTEGER,
                    availability DOUBLE PRECISION,
                    mttr_s INTEGER,
                    work_power_kw DOUBLE PRECISION,
                    idle_power_kw DOUBLE PRECISION
                )''')

cursor.execute('''CREATE TABLE IF NOT EXISTS buffers (
                    id TEXT PRIMARY KEY,
                    capacity INTEGER
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
                    ingested_at TIMESTAMPTZ,
                    source TEXT,
                    payload JSONB
                )''')

cursor.execute('''CREATE TABLE IF NOT EXISTS ingest_watermark (
                    source TEXT PRIMARY KEY,
                    max_event_ts TIMESTAMPTZ
                )''')

cursor.execute('''CREATE TABLE IF NOT EXISTS events (
                    ts TIMESTAMPTZ,
                    machine_id TEXT,
                    reason_code TEXT,
                    duration_s DOUBLE PRECISION,
                    energy_kwh DOUBLE PRECISION
                )''')

cursor.execute('''CREATE TABLE IF NOT EXISTS samples (
                    ts TIMESTAMPTZ,
                    machine_id TEXT,
                    tag TEXT,
                    value DOUBLE PRECISION
                )''')

cursor.execute('''CREATE INDEX IF NOT EXISTS idx_events_machine_time ON events (machine_id, ts)''')
cursor.execute('''CREATE INDEX IF NOT EXISTS idx_samples_machine_time ON samples (machine_id, ts)''')

# Insert machine data
machines_data = [
    ('M1', 150, 0.98, 600, 4.0, 0.4),
    ('M2', 120, 0.97, 900, 5.0, 0.5),
    ('M3', 180, 0.95, 1200, 6.0, 0.6),
    ('M4', 120, 0.97, 900, 5.0, 0.5),
    ('M5', 150, 0.98, 600, 4.0, 0.4)
]

cursor.executemany('''INSERT OR REPLACE INTO machines (id, process_time_s, availability, mttr_s, work_power_kw, idle_power_kw)
                      VALUES (?, ?, ?, ?, ?, ?)''', machines_data)

# Insert buffer data
buffers_data = [
    ('B0', 20),
    ('B1', 8),
    ('B2', 8),
    ('B3', 8),
    ('B4', 8)
]

cursor.executemany('''INSERT OR REPLACE INTO buffers (id, capacity)
                      VALUES (?, ?)''', buffers_data)

# Insert tag map data
tag_map_data = []
for machine in machines_data:
    machine_id = machine[0]
    tag_map_data.extend([
        ('process_time_s', machine_id, 'process_time_s', 's', 'process_time_s', 1.0),
        ('availability', machine_id, 'availability', 'percent', 'availability', 1.0),
        ('mttr_s', machine_id, 'mttr_s', 's', 'mttr_s', 1.0),
        ('work_power_kw', machine_id, 'work_power_kw', 'kW', 'work_power_kw', 1.0),
        ('idle_power_kw', machine_id, 'idle_power_kw', 'kW', 'idle_power_kw', 1.0)
    ])

cursor.executemany('''INSERT OR REPLACE INTO tag_map (tag_id, machine_id, signal, unit, register, scale)
                      VALUES (?, ?, ?, ?, ?, ?)''', tag_map_data)

conn.commit()

# Define constants
GRAVITY = 9.81
SIMULATION_TIME = 432000  # seconds
TIME_STEP = 0.01  # seconds
LOG_INTERVAL = 10  # seconds

# Create materials
steel_material = chrono.ChMaterialSurfaceNSC()
steel_material.SetFriction(0.5)
steel_material.SetRestitution(0.1)

refractory_material = chrono.ChMaterialSurfaceNSC()
refractory_material.SetFriction(0.3)
refractory_material.SetRestitution(0.05)

# Create base ground
ground = chrono.ChBody()
ground.SetBodyFixed(True)
ground.SetPos(chrono.ChVectorD(0, -1, 0))
system.Add(ground)

# Create ground shape
ground_shape = chrono.ChTriangleMeshConnected()
ground_shape.LoadWavefrontMesh(chrono.GetChronoDataFile("models/ground.obj"), False, True)
ground_shape.SetScale(chrono.ChVectorD(10, 1, 10))

# Create a collision model for the ground
ground_collision = chrono.ChCollisionModel()
ground_collision.SetName("ground_collision")
ground_collision.AddTriangleMesh(ground_shape, False, False)

# Attach the collision model to the ground body
ground.SetCollide(True)
ground.GetCollisionModel().AddItem(ground_collision)

# Create a visualization shape for the ground
ground_visual = chrono.ChVisualShapeTriangleMesh(ground_shape)
ground_visual.SetColor(chrono.ChColor(0.5, 0.5, 0.5))
ground.AddVisualShape(ground_visual)

# Create source
source_pos = chrono.ChVectorD(0, 0, 0)
source = chrono.ChBody()
source.SetPos(source_pos)
system.Add(source)

source_shape = chrono.ChVisualShapeBox(0.5, 0.5, 0.5)
source_shape.SetColor(chrono.ChColor(0.8, 0.2, 0.2))
source.AddVisualShape(source_shape)

# Create machine bodies
machine_bodies = {}
machine_positions = [
    chrono.ChVectorD(2, 0, 0),
    chrono.ChVectorD(4, 0, 0),
    chrono.ChVectorD(6, 0, 0),
    chrono.ChVectorD(8, 0, 0),
    chrono.ChVectorD(10, 0, 0)
]

for i, pos in enumerate(machine_positions):
    machine_id = "M" + str(i+1)
    machine = chrono.ChBody()
    machine.SetPos(pos)
    system.Add(machine)
    
    # Create machine shape
    machine_shape = chrono.ChVisualShapeBox(1.0, 1.0, 0.5)
    machine_shape.SetColor(chrono.ChColor(0.2, 0.8, 0.2))
    machine.AddVisualShape(machine_shape)
    
    # Create collision shape
    machine_collision = chrono.ChCollisionModel()
    machine_collision.AddBox(1.0, 1.0, 0.5)
    machine.SetCollide(True)
    machine.GetCollisionModel().AddItem(machine_collision)
    
    machine_bodies[machine_id] = machine

# Create buffer bodies
buffer_bodies = {}
buffer_positions = [
    chrono.ChVectorD(1.5, 0, 0),  # B0
    chrono.ChVectorD(3.5, 0, 0),  # B1
    chrono.ChVectorD(5.5, 0, 0),  # B2
    chrono.ChVectorD(7.5, 0, 0),  # B3
    chrono.ChVectorD(9.5, 0, 0)   # B4
]

for i, pos in enumerate(buffer_positions):
    buffer_id = "B" + str(i)
    buffer = chrono.ChBody()
    buffer.SetPos(pos)
    system.Add(buffer)
    
    # Create buffer shape
    buffer_shape = chrono.ChVisualShapeBox(0.5, 0.5, 0.5)
    buffer_shape.SetColor(chrono.ChColor(0.2, 0.2, 0.8))
    buffer.AddVisualShape(buffer_shape)
    
    # Create collision shape
    buffer_collision = chrono.ChCollisionModel()
    buffer_collision.AddBox(0.5, 0.5, 0.5)
    buffer.SetCollide(True)
    buffer.GetCollisionModel().AddItem(buffer_collision)
    
    buffer_bodies[buffer_id] = buffer

# Create animation helper
class DigitalTwinSimulator:
    def __init__(self, system, machine_bodies, buffer_bodies):
        self.system = system
        self.machine_bodies = machine_bodies
        self.buffer_bodies = buffer_bodies
        self.simulation_time = 0
        self.machine_states = {}
        self.buffer_states = {}
        self.processed_items = 0
        self.events_log = []
        self.samples_log = []
        self.start_time = datetime.now(timezone.utc)
        
        # Initialize machine states
        for machine_id in machine_bodies.keys():
            self.machine_states[machine_id] = {
                'is_working': False,
                'working_start': 0,
                'working_time': 0,
                'total_time': 0,
                'current_item': None,
                'available': True
            }
            
        # Initialize buffer states
        for buffer_id in buffer_bodies.keys():
            self.buffer_states[buffer_id] = {
                'items': 0,
                'capacity': 8 if buffer_id != 'B0' else 20
            }
    
    def log_samples(self, timestamp):
        # Log machine sensor data
        for machine_id, state in self.machine_states.items():
            # Get machine parameters from database
            cursor.execute("SELECT process_time_s, availability, mttr_s, work_power_kw, idle_power_kw FROM machines WHERE id=?", (machine_id,))
            machine_data = cursor.fetchone()
            if machine_data:
                process_time, availability, mttr_s, work_power_kw, idle_power_kw = machine_data
                
                # Log various sensor readings
                self.samples_log.append((timestamp, machine_id, "process_time_s", process_time))
                self.samples_log.append((timestamp, machine_id, "availability", availability))
                self.samples_log.append((timestamp, machine_id, "mttr_s", mttr_s))
                self.samples_log.append((timestamp, machine_id, "work_power_kw", work_power_kw))
                self.samples_log.append((timestamp, machine_id, "idle_power_kw", idle_power_kw))
                
                # Log power consumption
                if state['is_working']:
                    power_consumption = work_power_kw
                else:
                    power_consumption = idle_power_kw
                self.samples_log.append((timestamp, machine_id, "power_consumption_kw", power_consumption))
                
                # Log state information
                self.samples_log.append((timestamp, machine_id, "is_working", 1 if state['is_working'] else 0))
                self.samples_log.append((timestamp, machine_id, "available", 1 if state['available'] else 0))
    
    def log_events(self, timestamp, machine_id, reason_code, duration_s, energy_kwh):
        self.events_log.append((timestamp, machine_id, reason_code, duration_s, energy_kwh))
    
    def simulate_step(self, dt):
        self.simulation_time += dt
        
        # Update machine states
        for machine_id, state in self.machine_states.items():
            # Update timing
            state['total_time'] += dt
            
            # Simulate availability and failures
            if state['available']:
                # Check if machine is working
                if state['is_working']:
                    # Check if processing is complete
                    cursor.execute("SELECT process_time_s FROM machines WHERE id=?", (machine_id,))
                    process_time = cursor.fetchone()[0]
                    if self.simulation_time - state['working_start'] >= process_time:
                        # Processing complete
                        state['is_working'] = False
                        self.processed_items += 1
                        self.log_events(
                            datetime.now(timezone.utc), 
                            machine_id, 
                            "PROCESSING_COMPLETE", 
                            process_time, 
                            process_time * 4.0 / 3600  # Simplified energy calculation
                        )
                else:
                    # Check if item can be processed
                    # For simplicity, simulate item arrival and processing
                    if self.simulation_time > 130:  # Simple start time
                        # Randomly start processing
                        if self.simulation_time % 100 < 1:  # Simplified condition
                            state['is_working'] = True
                            state['working_start'] = self.simulation_time
                            self.log_events(
                                datetime.now(timezone.utc), 
                                machine_id, 
                                "PROCESSING_STARTED", 
                                0, 
                                0
                            )
    
    def run_simulation(self):
        print("Starting simulation...")
        start_time = time.time()
        
        # Main simulation loop
        step_count = 0
        while self.simulation_time < SIMULATION_TIME:
            # Log sample data every LOG_INTERVAL seconds
            if step_count % int(LOG_INTERVAL / TIME_STEP) == 0:
                self.log_samples(datetime.now(timezone.utc))
                print(f"Time: {self.simulation_time:.2f}s")
                
            # Simulate a step
            self.simulate_step(TIME_STEP)
            
            # Advance the simulation
            system.DoStepDynamics(TIME_STEP)
            step_count += 1
            
            # Print progress
            if step_count % 100