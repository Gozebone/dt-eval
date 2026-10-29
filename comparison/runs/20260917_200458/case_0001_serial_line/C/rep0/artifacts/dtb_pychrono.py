```python
import pychrono as chrono
import pychrono.irrlicht as chronoirr
import numpy as np
import json
import datetime
import sqlite3
from typing import Dict, List, Tuple

# Initialize PyChrono system
chrono.SetChronoDataPath('path/to/chronodata')  # Adjust path as needed
sys = chrono.ChSystemNSC()
sys.SetGravitationalAcceleration(chrono.ChVectorD(0, -9.81, 0))

# Create database connection
conn = sqlite3.connect('digital_twin.db')
cursor = conn.cursor()

# Create tables if they don't exist
cursor.execute('''CREATE TABLE IF NOT EXISTS production_type (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS process (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS equipment (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS sensor (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS critical_parameter (
                    id INTEGER PRIMARY KEY,
                    parameter_name TEXT UNIQUE NOT NULL,
                    target_value TEXT NOT NULL)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS part_specification (
                    id INTEGER PRIMARY KEY,
                    part_type TEXT UNIQUE NOT NULL,
                    specifications TEXT)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS sensor_data (
                    id INTEGER PRIMARY KEY,
                    sensor_id INTEGER,
                    timestamp TEXT,
                    temperature REAL,
                    humidity REAL,
                    pressure REAL,
                    speed REAL,
                    data_source TEXT)''')

# Insert initial data if tables are empty
cursor.execute("SELECT COUNT(*) FROM production_type")
if cursor.fetchone()[0] == 0:
    cursor.execute("INSERT INTO production_type (name) VALUES (?)", ("производство автомобильных комплектующих",))

cursor.execute("SELECT COUNT(*) FROM process")
if cursor.fetchone()[0] == 0:
    processes = ["обработка металлов", "прокат", "покрашивание", "тестирование"]
    for p in processes:
        cursor.execute("INSERT INTO process (name) VALUES (?)", (p,))

cursor.execute("SELECT COUNT(*) FROM equipment")
if cursor.fetchone()[0] == 0:
    equipment = ["гравировальные станки", "покрашальные машины", "тестовые системы"]
    for e in equipment:
        cursor.execute("INSERT INTO equipment (name) VALUES (?)", (e,))

cursor.execute("SELECT COUNT(*) FROM sensor")
if cursor.fetchone()[0] == 0:
    sensors = ["датчик температуры", "датчик влажности", "датчик давления", "датчик скорости"]
    for s in sensors:
        cursor.execute("INSERT INTO sensor (name) VALUES (?)", (s,))

cursor.execute("SELECT COUNT(*) FROM critical_parameter")
if cursor.fetchone()[0] == 0:
    params = [("температура", "40°C"), ("давление", "0.5 МПа"), ("скорость", "100 км/ч")]
    for param, value in params:
        cursor.execute("INSERT INTO critical_parameter (parameter_name, target_value) VALUES (?, ?)", (param, value))

cursor.execute("SELECT COUNT(*) FROM part_specification")
if cursor.fetchone()[0] == 0:
    parts = [
        ("деталь 1", {"длина": "100 мм", "ширина": "50 мм", "толщина": "10 мм"}),
        ("деталь 2", {"длина": "150 мм", "ширина": "75 мм", "толщина": "15 мм"}),
        ("деталь 3", {"длина": "200 мм", "ширина": "100 мм", "толщина": "20 мм"}),
        ("деталь 4", {"длина": "250 мм", "ширина": "125 мм", "толщина": "25 мм"}),
        ("деталь 5", {"длина": "300 мм", "ширина": "150 мм", "толщина": "30 мм"}),
        ("деталь 6", {"длина": "350 мм", "ширина": "175 мм", "толщина": "35 мм"}),
        ("деталь 7", {"длина": "400 мм", "ширина": "200 мм", "толщина": "40 мм"}),
        ("деталь 8", {"длина": "450 мм", "ширина": "225 мм", "толщина": "45 мм"}),
        ("деталь 9", {"длина": "500 мм", "ширина": "250 мм", "толщина": "50 мм"}),
        ("деталь 10", {"длина": "550 мм", "ширина": "275 мм", "толщина": "55 мм"}),
        ("деталь 11", {"длина": "600 мм", "ширина": "300 мм", "толщина": "60 мм"}),
        ("деталь 12", {"длина": "650 мм", "ширина": "325 мм", "толщина": "65 мм"}),
        ("деталь 13", {"длина": "700 мм", "ширина": "350 мм", "толщина": "70 мм"}),
        ("деталь 14", {"длина": "750 мм", "ширина": "375 мм", "толщина": "75 мм"}),
        ("деталь 15", {"длина": "800 мм", "ширина": "400 мм", "толщина": "80 мм"})
    ]
    for part_type, specs in parts:
        cursor.execute("INSERT INTO part_specification (part_type, specifications) VALUES (?, ?)", 
                      (part_type, json.dumps(specs)))

conn.commit()

# Material definitions
mat_steel = chrono.ChMaterialSurfaceNSC()
mat_steel.SetFriction(0.5)
mat_steel.SetRestitution(0.1)

mat_refractory = chrono.ChMaterialSurfaceNSC()
mat_refractory.SetFriction(0.3)
mat_refractory.SetRestitution(0.05)

# Create physical bodies representing equipment
# Furnace (for metal processing)
furnace_body = chrono.ChBodyEasyBox(2, 2, 2, 1000, True, True, mat_steel)
furnace_body.SetPos(chrono.ChVectorD(0, 1, 0))
furnace_body.SetBodyFixed(True)
sys.Add(furnace_body)

# Crystallizer (for rolling process)
crystallizer_body = chrono.ChBodyEasyBox(1.5, 0.5, 1.5, 1000, True, True, mat_steel)
crystallizer_body.SetPos(chrono.ChVectorD(3, 1, 0))
crystallizer_body.SetBodyFixed(True)
sys.Add(crystallizer_body)

# Painting machine
painting_machine = chrono.ChBodyEasyBox(2, 1, 1, 1000, True, True, mat_steel)
painting_machine.SetPos(chrono.ChVectorD(6, 1, 0))
painting_machine.SetBodyFixed(True)
sys.Add(painting_machine)

# Testing system
testing_system = chrono.ChBodyEasyBox(2, 1, 1, 1000, True, True, mat_steel)
testing_system.SetPos(chrono.ChVectorD(9, 1, 0))
testing_system.SetBodyFixed(True)
sys.Add(testing_system)

# Conveyor belt for moving parts
belt_length = 10
belt_width = 0.5
belt_height = 0.1
belt_body = chrono.ChBodyEasyBox(belt_length, belt_height, belt_width, 1000, True, True, mat_steel)
belt_body.SetPos(chrono.ChVectorD(0, 0.5, -2))
belt_body.SetBodyFixed(False)
sys.Add(belt_body)

# Add motor constraint to simulate conveyor movement
motor_constraint = chrono.ChLinkMotorRotation()
motor_constraint.Initialize(belt_body, sys.Get_body(0), chrono.ChFrameD(chrono.ChVectorD(0, 0.5, -2)))
motor_constraint.SetSpeed(1.0)  # 1 m/s
sys.Add(motor_constraint)

# Create a sample part to simulate
part = chrono.ChBodyEasyBox(0.1, 0.1, 0.1, 1000, True, True, mat_steel)
part.SetPos(chrono.ChVectorD(0, 1.5, -2))
sys.Add(part)

# Create sensors to measure parameters
class Sensor:
    def __init__(self, name: str):
        self.name = name
        self.id = None
    
    def read(self) -> Dict[str, float]:
        return {}

# Temperature sensor
temp_sensor = Sensor("датчик температуры")

# Humidity sensor  
humidity_sensor = Sensor("датчик влажности")

# Pressure sensor
pressure_sensor = Sensor("датчик давления")

# Speed sensor
speed_sensor = Sensor("датчик скорости")

# Simulation parameters
time_step = 0.01
simulation_time = 100.0
current_time = 0.0

# Main simulation loop
print("Starting simulation...")

try:
    while current_time < simulation_time:
        # Step the simulation
        sys.DoStepDynamics(time_step)
        
        # Update current time
        current_time += time_step
        
        # Simulate sensor readings
        timestamp = datetime.datetime.now().isoformat()
        
        # Read sensor values (these would come from actual physics in real implementation)
        temp_reading = 35.0 + 5.0 * np.sin(current_time / 10.0)  # Simulated temperature
        humidity_reading = 40.0 + 10.0 * np.cos(current_time / 15.0)  # Simulated humidity
        pressure_reading = 0.4 + 0.2 * np.sin(current_time / 20.0)  # Simulated pressure
        speed_reading = 90.0 + 10.0 * np.cos(current_time / 30.0)  # Simulated speed
        
        # Store sensor data
        cursor.execute("INSERT INTO sensor_data (sensor_id, timestamp, temperature, humidity, pressure, speed, data_source) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (1, timestamp, temp_reading, humidity_reading, pressure_reading, speed_reading, "реальное время"))
        
        # Print progress
        if int(current_time) % 10 == 0:
            print(f"Time: {current_time:.2f}s")
            
except Exception as e:
    print(f"Error during simulation: {str(e)}")
finally:
    # Close database connection
    conn.commit()
    conn.close()
    
    # Print summary
    print("Simulation completed.")
    print(f"Total time simulated: {current_time:.2f} seconds")
    print("Sensor data logged to database.")

print("PyChrono simulation finished successfully.")
```