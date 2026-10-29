import pychrono as chrono
import pychrono.irrlicht as chronoirr
import numpy as np
import datetime
import sqlite3
import json
from typing import Dict, List, Tuple
import time

# Initialize PyChrono system
chrono.SetChronoDataPath('path/to/chronodata')  # Adjust path as needed
sys = chrono.ChSystemNSC()
sys.SetGravitationalAcceleration(chrono.ChVectorD(0, -9.81, 0))

# Create database connection
conn = sqlite3.connect('digital_twin.db')
cursor = conn.cursor()

# Create tables if they don't exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS process_line (
        id INTEGER PRIMARY KEY,
        production_type TEXT NOT NULL,
        processes TEXT NOT NULL,
        equipment TEXT NOT NULL,
        goals TEXT NOT NULL,
        data_sources TEXT NOT NULL,
        update_frequency TEXT NOT NULL,
        critical_parameters TEXT NOT NULL
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS machine (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        type TEXT,
        status TEXT DEFAULT 'available',
        availability REAL,
        mttr TEXT,
        work_power_kw REAL,
        idle_power_kw REAL
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS sensor_data (
        id INTEGER PRIMARY KEY,
        machine_id INTEGER NOT NULL,
        sensor_type TEXT NOT NULL,
        value REAL,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (machine_id) REFERENCES machine(id)
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS production_event (
        id INTEGER PRIMARY KEY,
        machine_id INTEGER NOT NULL,
        process_step TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT,
        status TEXT DEFAULT 'completed',
        FOREIGN KEY (machine_id) REFERENCES machine(id)
    )
''')

# Insert process line data
process_line_data = {
    "production_type": "последовательная (конвейерная) линия обработки дискретных деталей",
    "processes": "M1 → M2 → M3 → M4 → M5",
    "equipment": "M1, M2, M3, M4, M5 (типы оборудования не указаны)",
    "goals": "оценивать пропускную способность линии, незавершённое производство (WIP) и удельное энергопотребление на деталь, а также отслеживать доступность машин M1-M5",
    "data_sources": "пер-станционные измеренные факты, полученные в период мониторинга реального участка (исторические наблюдения)",
    "update_frequency": "события регистрируются по каждой обработанной детали, интервалы состояний и энергопотребление записываются непрерывно",
    "critical_parameters": {"M1": "доступность", "M2": "доступность", "M3": "доступность", "M4": "доступность", "M5": "доступность", "система": "доступность"}
}
cursor.execute('''
    INSERT OR REPLACE INTO process_line 
    (id, production_type, processes, equipment, goals, data_sources, update_frequency, critical_parameters)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
''', (1, process_line_data["production_type"], process_line_data["processes"],
      process_line_data["equipment"], process_line_data["goals"], process_line_data["data_sources"],
      process_line_data["update_frequency"], json.dumps(process_line_data["critical_parameters"])))

# Insert machine data
machines_data = [
    ("M1", "не указано", "available", 0.95, "00:15:00", 2.5, 0.5),
    ("M2", "не указано", "available", 0.92, "00:20:00", 3.0, 0.6),
    ("M3", "не указано", "available", 0.90, "00:25:00", 2.8, 0.4),
    ("M4", "не указано", "available", 0.88, "00:30:00", 3.2, 0.7),
    ("M5", "не указано", "available", 0.94, "00:18:00", 2.6, 0.5)
]

for machine in machines_data:
    cursor.execute('''
        INSERT OR REPLACE INTO machine 
        (id, name, type, status, availability, mttr, work_power_kw, idle_power_kw)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (machines_data.index(machine)+1, machine[0], machine[1], machine[2],
          machine[3], machine[4], machine[5], machine[6]))

conn.commit()

# Create materials
mat_steel = chrono.ChMaterialSurfaceNSC()
mat_steel.SetFriction(0.5)
mat_steel.SetRestitution(0.1)

mat_concrete = chrono.ChMaterialSurfaceNSC()
mat_concrete.SetFriction(0.6)
mat_concrete.SetRestitution(0.05)

# Create ground plane
ground = chrono.ChBodyEasyBox(20, 1, 20, 1000, True, True)
ground.SetPos(chrono.ChVectorD(0, -0.5, 0))
ground.GetVisualModel().SetTexture("textures/concrete.jpg")
ground.SetMaterialSurface(mat_concrete)
sys.Add(ground)

# Create conveyor belt components
def create_conveyor_belt(length: float, width: float, height: float):
    belt = chrono.ChBodyEasyBox(length, height, width, 1000, True, True)
    belt.SetPos(chrono.ChVectorD(0, 0, 0))
    belt.SetMaterialSurface(mat_steel)
    return belt

# Create equipment bodies (simplified representation)
equipment_bodies = {}
for i in range(1, 6):
    body = chrono.ChBodyEasyBox(2, 1, 2, 1000, True, True)
    body.SetPos(chrono.ChVectorD((i-3)*5, 0.5, 0))
    body.SetMaterialSurface(mat_steel)
    sys.Add(body)
    equipment_bodies[f'M{i}'] = body

# Create a simple part that will go through the line
part = chrono.ChBodyEasyBox(0.5, 0.5, 0.5, 100, True, True)
part.SetPos(chrono.ChVectorD(-8, 1, 0))
part.SetMaterialSurface(mat_steel)
sys.Add(part)

# Add some constraints between parts to simulate the line
# This is a simplified approach using fixed constraints
constraint1 = chrono.ChLinkLockLock()
constraint1.Initialize(equipment_bodies['M1'], ground, chrono.ChFrameD(chrono.ChVectorD(-3, 0, 0), chrono.Q_from_AngZ(0)))
sys.Add(constraint1)

constraint2 = chrono.ChLinkLockLock()
constraint2.Initialize(equipment_bodies['M2'], ground, chrono.ChFrameD(chrono.ChVectorD(-1, 0, 0), chrono.Q_from_AngZ(0)))
sys.Add(constraint2)

constraint3 = chrono.ChLinkLockLock()
constraint3.Initialize(equipment_bodies['M3'], ground, chrono.ChFrameD(chrono.ChVectorD(1, 0, 0), chrono.Q_from_AngZ(0)))
sys.Add(constraint3)

constraint4 = chrono.ChLinkLockLock()
constraint4.Initialize(equipment_bodies['M4'], ground, chrono.ChFrameD(chrono.ChVectorD(3, 0, 0), chrono.Q_from_AngZ(0)))
sys.Add(constraint4)

constraint5 = chrono.ChLinkLockLock()
constraint5.Initialize(equipment_bodies['M5'], ground, chrono.ChFrameD(chrono.ChVectorD(5, 0, 0), chrono.Q_from_AngZ(0)))
sys.Add(constraint5)

# Create sensors for each machine
class MachineSensor:
    def __init__(self, machine_name: str, machine_id: int):
        self.machine_name = machine_name
        self.machine_id = machine_id
        self.process_start_time = None
        self.process_end_time = None
        self.total_processing_time = 0
        self.failure_count = 0
        self.work_power = 0
        self.idle_power = 0
        
    def log_sensor_data(self, sensor_type: str, value: float):
        timestamp = datetime.datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO sensor_data (machine_id, sensor_type, value, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (self.machine_id, sensor_type, value, timestamp))
        
    def log_production_event(self, process_step: str, start_time: datetime.datetime, end_time: datetime.datetime = None):
        timestamp = datetime.datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO production_event (machine_id, process_step, start_time, end_time)
            VALUES (?, ?, ?, ?)
        ''', (self.machine_id, process_step, start_time.isoformat(), end_time.isoformat() if end_time else None))
        
    def get_availability(self) -> float:
        # Simplified availability calculation
        return 0.95  # Placeholder value

# Create sensors for all machines
sensors = {}
for i in range(1, 6):
    sensors[f'M{i}'] = MachineSensor(f'M{i}', i)

# Main simulation loop
time_step = 0.01
simulation_time = 0
part_moving = False
part_position = -8
part_speed = 0.5
last_log_time = 0

print("Starting simulation...")
start_time = time.time()

while simulation_time < 100:  # Run for 100 seconds
    # Update part position
    if not part_moving:
        part.SetPos(chrono.ChVectorD(part_position, 1, 0))
        part_position += part_speed * time_step
        if part_position > 10:
            part_moving = True
            part_position = -8
            
    # Check which machine the part is at
    current_machine = None
    if -3.5 <= part_position <= -2.5:
        current_machine = 'M1'
    elif -1.5 <= part_position <= -0.5:
        current_machine = 'M2'
    elif 0.5 <= part_position <= 1.5:
        current_machine = 'M3'
    elif 2.5 <= part_position <= 3.5:
        current_machine = 'M4'
    elif 4.5 <= part_position <= 5.5:
        current_machine = 'M5'
    
    # Log sensor data continuously
    if simulation_time - last_log_time >= 0.1:  # Log every 0.1 seconds
        for sensor_name, sensor in sensors.items():
            # Simulate power consumption
            if current_machine == sensor_name:
                sensor.log_sensor_data("energy_consumption", sensor.work_power)
            else:
                sensor.log_sensor_data("energy_consumption", sensor.idle_power)
                
            # Simulate availability
            availability = sensor.get_availability()
            sensor.log_sensor_data("availability", availability)
            
        last_log_time = simulation_time
    
    # Log production events when part moves to a new station
    if current_machine and current_machine in sensors:
        sensor = sensors[current_machine]
        if not sensor.process_start_time:
            sensor.process_start_time = datetime.datetime.now()
            sensor.log_production_event(current_machine, sensor.process_start_time)
        elif sensor.process_end_time is None:
            # Simulate processing time
            if simulation_time - sensor.process_start_time.timestamp() > 5:  # 5 second processing time
                sensor.process_end_time = datetime.datetime.now()
                sensor.log_production_event(current_machine, sensor.process_start_time, sensor.process_end_time)
    
    # Step the simulation
    sys.DoStepDynamics(time_step)
    simulation_time += time_step
    
    # Print progress
    if simulation_time % 10 < time_step:
        elapsed = time.time() - start_time
        print(f"Simulation time: {simulation_time:.2f}s, Elapsed time: {elapsed:.2f}s")

# Commit all changes to database
conn.commit()
conn.close()

print("Simulation completed.")
print("Data has been logged to the database.")

# Cleanup
del sys