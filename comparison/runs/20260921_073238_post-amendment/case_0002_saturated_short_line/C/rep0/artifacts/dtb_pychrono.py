```python
import pychrono as chrono
import pychrono.irrlicht as irr
import numpy as np
import json
import time
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import Json
import threading
import queue

# Database connection settings (update these with your actual database settings)
DB_CONFIG = {
    'dbname': 'digital_twin',
    'user': 'your_user',
    'password': 'your_password',
    'host': 'localhost',
    'port': '5432'
}

# Global variables for simulation data
machine_data = {
    'M1': {
        'process_time_s': 90,
        'availability': 0.99,
        'mttr_s': 600,
        'work_power_kw': 3.0,
        'idle_power_kw': 0.3
    },
    'M2': {
        'process_time_s': 70,
        'availability': 0.98,
        'mttr_s': 900,
        'work_power_kw': 4.5,
        'idle_power_kw': 0.45
    },
    'M3': {
        'process_time_s': 110,
        'availability': 0.99,
        'mttr_s': 1200,
        'work_power_kw': 6.0,
        'idle_power_kw': 0.6
    }
}

buffer_data = {
    'B0': {'capacity': 15, 'before': 'source', 'after': 'M1'},
    'B1': {'capacity': 5, 'before': 'M1', 'after': 'M2'},
    'B2': {'capacity': 5, 'before': 'M2', 'after': 'M3'}
}

# Sensor data collection queues
sensor_data_queue = queue.Queue()
event_data_queue = queue.Queue()

class MachineModel:
    def __init__(self, id, process_time, availability, mttr, work_power, idle_power):
        self.id = id
        self.process_time = process_time
        self.availability = availability
        self.mttr = mttr
        self.work_power = work_power
        self.idle_power = idle_power
        self.is_working = True
        self.working_time = 0
        self.idle_time = 0
        self.last_state_change = 0
        self.total_time = 0
        self.processed_count = 0
        self.uptime = 0
        self.downtime = 0
        self.total_energy = 0
        self.current_energy_kwh = 0

    def get_power(self):
        if self.is_working:
            return self.work_power
        else:
            return self.idle_power

    def update_state(self, current_time):
        # Simulate machine state changes based on availability and MTTR
        if self.is_working:
            self.working_time += 1
            self.total_time += 1
            self.total_energy += self.work_power * 1/3600  # kW * hours = kWh
        else:
            self.idle_time += 1
            self.total_time += 1
            self.total_energy += self.idle_power * 1/3600

        # Check if machine should fail or recover
        if self.is_working:
            # Simulate random failure based on availability
            if np.random.rand() > self.availability:
                self.is_working = False
                self.last_state_change = current_time
                self.uptime += current_time - self.last_state_change
                # Log event
                event_data_queue.put({
                    'ts': current_time,
                    'machine_id': self.id,
                    'reason_code': 'FAILURE',
                    'duration_s': self.mttr,
                    'energy_kwh': self.current_energy_kwh
                })
        else:
            # Simulate recovery after MTTR
            if current_time - self.last_state_change >= self.mttr:
                self.is_working = True
                self.last_state_change = current_time
                self.downtime += current_time - self.last_state_change
                # Log event
                event_data_queue.put({
                    'ts': current_time,
                    'machine_id': self.id,
                    'reason_code': 'RECOVERY',
                    'duration_s': 0,
                    'energy_kwh': self.current_energy_kwh
                })

    def record_processing(self):
        self.processed_count += 1
        self.current_energy_kwh = self.total_energy

class BufferModel:
    def __init__(self, id, capacity, before, after):
        self.id = id
        self.capacity = capacity
        self.before = before
        self.after = after
        self.contents = []

    def add_item(self, item):
        if len(self.contents) < self.capacity:
            self.contents.append(item)
            return True
        return False

    def remove_item(self):
        if self.contents:
            return self.contents.pop(0)
        return None

    def get_count(self):
        return len(self.contents)

class SimulationLogger:
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.connect()

    def connect(self):
        try:
            self.conn = psycopg2.connect(**DB_CONFIG)
            self.cursor = self.conn.cursor()
            print("Connected to database successfully")
        except Exception as e:
            print(f"Failed to connect to database: {e}")

    def log_machines(self):
        for machine_id, data in machine_data.items():
            try:
                self.cursor.execute("""
                    INSERT INTO machines (id, process_time_s, availability, mttr_s, work_power_kw, idle_power_kw)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        process_time_s = EXCLUDED.process_time_s,
                        availability = EXCLUDED.availability,
                        mttr_s = EXCLUDED.mttr_s,
                        work_power_kw = EXCLUDED.work_power_kw,
                        idle_power_kw = EXCLUDED.idle_power_kw;
                """, (
                    machine_id,
                    data['process_time_s'],
                    data['availability'],
                    data['mttr_s'],
                    data['work_power_kw'],
                    data['idle_power_kw']
                ))
                self.conn.commit()
            except Exception as e:
                print(f"Error logging machine {machine_id}: {e}")

    def log_buffers(self):
        for buf_id, data in buffer_data.items():
            try:
                self.cursor.execute("""
                    INSERT INTO buffers (id, capacity, before, after)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        capacity = EXCLUDED.capacity,
                        before = EXCLUDED.before,
                        after = EXCLUDED.after;
                """, (
                    buf_id,
                    data['capacity'],
                    data['before'],
                    data['after']
                ))
                self.conn.commit()
            except Exception as e:
                print(f"Error logging buffer {buf_id}: {e}")

    def log_station(self):
        for machine_id, data in machine_data.items():
            try:
                self.cursor.execute("""
                    INSERT INTO stations (id, processing_time_s, availability_pct, mttr_s, power_working_kw, power_idle_kw)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        processing_time_s = EXCLUDED.processing_time_s,
                        availability_pct = EXCLUDED.availability_pct,
                        mttr_s = EXCLUDED.mttr_s,
                        power_working_kw = EXCLUDED.power_working_kw,
                        power_idle_kw = EXCLUDED.power_idle_kw;
                """, (
                    machine_id,
                    data['process_time_s'],
                    data['availability'] * 100,
                    data['mttr_s'],
                    data['work_power_kw'],
                    data['idle_power_kw']
                ))
                self.conn.commit()
            except Exception as e:
                print(f"Error logging station {machine_id}: {e}")

    def log_samples(self, current_time):
        # Log machine sensor data
        for machine_id, machine in machines.items():
            try:
                self.cursor.execute("""
                    INSERT INTO samples (ts, machine_id, tag, value)
                    VALUES (%s, %s, %s, %s);
                """, (
                    datetime.fromtimestamp(current_time),
                    machine_id,
                    'avg_processing_time',
                    machine.process_time
                ))
                self.cursor.execute("""
                    INSERT INTO samples (ts, machine_id, tag, value)
                    VALUES (%s, %s, %s, %s);
                """, (
                    datetime.fromtimestamp(current_time),
                    machine_id,
                    'availability',
                    machine.availability * 100
                ))
                self.cursor.execute("""
                    INSERT INTO samples (ts, machine_id, tag, value)
                    VALUES (%s, %s, %s, %s);
                """, (
                    datetime.fromtimestamp(current_time),
                    machine_id,
                    'mttr',
                    machine.mttr
                ))
                self.cursor.execute("""
                    INSERT INTO samples (ts, machine_id, tag, value)
                    VALUES (%s, %s, %s, %s);
                """, (
                    datetime.fromtimestamp(current_time),
                    machine_id,
                    'idle_power',
                    machine.idle_power
                ))
                self.conn.commit()
            except Exception as e:
                print(f"Error logging sample for {machine_id}: {e}")

    def log_events(self):
        while not event_data_queue.empty():
            try:
                event = event_data_queue.get_nowait()
                self.cursor.execute("""
                    INSERT INTO events (ts, machine_id, reason_code, duration_s, energy_kwh)
                    VALUES (%s, %s, %s, %s, %s);
                """, (
                    datetime.fromtimestamp(event['ts']),
                    event['machine_id'],
                    event['reason_code'],
                    event['duration_s'],
                    event['energy_kwh']
                ))
                self.conn.commit()
            except queue.Empty:
                break
            except Exception as e:
                print(f"Error logging event: {e}")

    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

# Create models
machines = {}
buffers = {}

for machine_id, data in machine_data.items():
    machines[machine_id] = MachineModel(
        machine_id,
        data['process_time_s'],
        data['availability'],
        data['mttr_s'],
        data['work_power_kw'],
        data['idle_power_kw']
    )

for buf_id, data in buffer_data.items():
    buffers[buf_id] = BufferModel(
        buf_id,
        data['capacity'],
        data['before'],
        data['after']
    )

# Create simulation logger
logger = SimulationLogger()

# Initialize Chrono system
chrono.SetChronoDataPath('./chrono/data/')
chrono.SetChronoDataPath('/usr/local/share/chrono/data/')

# Create a physical system
system = chrono.ChSystemNSC()
system.Set_G_acc(chrono.ChVectorD(0, -9.81, 0))

# Create a ground body
ground = chrono.ChBody()
ground.SetFixed(True)
ground.SetIdentifier(1)
system.Add(ground)

# Create a box to represent part
part = chrono.ChBody()
part.SetIdentifier(2)
part.SetMass(1)
part.SetInertiaXX(chrono.ChVectorD(0.1, 0.1, 0.1))
part.SetPos(chrono.ChVectorD(0, 0, 0))
system.Add(part)

# Create a material
material = chrono.ChMaterialSurfaceNSC()
material.SetFriction(0.5)
material.SetRestitution(0.1)

# Create a part shape
part_shape = chrono.ChTriangleMeshConnected()
part_shape.LoadWavefrontMesh(chrono.GetChronoDataFile("models/cube.obj"))
part_shape.Transform(chrono.ChVectorD(0, 0, 0), chrono.ChMatrix33D(1))

# Add shape to part
part.GetCollisionModel().ClearModel()
part.GetCollisionModel().AddTriangleMesh(part_shape, False, False)
part.GetCollisionModel().BuildModel()
part.SetCollide(True)

# Create a visualization system
irrlicht_system = irr.ChIrrApp(system, 'Production Line Simulation', irr.dimension2d(1024, 768))
irrlicht_system.AddTypicalLogo()
irrlicht_system.AddTypicalSky()
irrlicht_system.AddTypicalCamera(irr.vector3df(10, 5, 10))
irrlicht_system.AddLight(irr.vector3df(10, 10, 10), irr.SColorf(1, 1, 1, 1))

# Set up the simulation
time_step = 0.01
total_simulation_time = 432000  # 5 days in seconds
current_time = 0
last_arrival_time = 0
inter_arrival_time = 60  # seconds
part_count = 0

# Initialize logger with data
logger.log_machines()
logger.log_buffers()
logger.log_station()

# Main simulation loop
print("Starting simulation...")
start_time = time.time()

while current_time <= total_simulation_time:
    # Check for new part arrival
    if current_time - last_arrival_time >= inter_arrival_time:
        part_count += 1
        part.SetPos(chrono.ChVectorD(0, 0, 0))
        part.SetRot(chrono.Q_from_AngX(0))
        part.SetPos(chrono.ChVectorD(0, 0, 0))  # Reset part position
        last_arrival_time = current_time

    # Update machine states
    for machine_id, machine in machines.items():
        machine.update_state(current_time)
        
        # Log samples periodically
        if current_time % 10 == 0:  # Log every 10 seconds
            logger.log_samples(current_time)

    # Check for events and log them
    logger.log_events()

