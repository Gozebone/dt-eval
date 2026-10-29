```python
import pychrono as chrono
import pychrono.irrlicht as chronoirr
import numpy as np
import sqlite3
import datetime
import time

# Initialize PyChrono system
chrono.SetChronoDataPath("../../../data/")
chrono.SetChronoDataPath("../../../data/")

# Create the physical system
sys = chrono.ChSystemNSC()
sys.SetGravitationalAcceleration(chrono.ChVectorD(0, -9.81, 0))
sys.SetSolverType(chrono.ChSolver.Type_BARZILAIBORWEIN)
sys.SetMaxItersSolverSpeed(100)
sys.SetMaxItersSolverStab(100)

# Create a database connection
conn = sqlite3.connect('digital_twin.db')
cursor = conn.cursor()

# Create tables if they don't exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS production_type (
        id INTEGER PRIMARY KEY,
        name TEXT UNIQUE NOT NULL
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS process (
        id INTEGER PRIMARY KEY,
        name TEXT UNIQUE NOT NULL
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS equipment (
        id INTEGER PRIMARY KEY,
        name TEXT UNIQUE NOT NULL
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS sensor (
        id INTEGER PRIMARY KEY,
        name TEXT UNIQUE NOT NULL
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS goal (
        id INTEGER PRIMARY KEY,
        description TEXT NOT NULL
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS data_source (
        id INTEGER PRIMARY KEY,
        type TEXT NOT NULL
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS update_frequency (
        id INTEGER PRIMARY KEY,
        frequency TEXT NOT NULL
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS critical_parameter (
        id INTEGER PRIMARY KEY,
        sensor_id INTEGER,
        value REAL,
        FOREIGN KEY (sensor_id) REFERENCES sensor(id)
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS additional_info (
        id INTEGER PRIMARY KEY,
        content TEXT NOT NULL
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS simulation_data (
        id INTEGER PRIMARY KEY,
        timestamp DATETIME,
        equipment_id INTEGER,
        sensor_id INTEGER,
        value REAL,
        FOREIGN KEY (equipment_id) REFERENCES equipment(id),
        FOREIGN KEY (sensor_id) REFERENCES sensor(id)
    )
''')

# Insert initial data into tables
cursor.execute("INSERT OR IGNORE INTO production_type (id, name) VALUES (1, 'производство автомобильных двигателей')")
cursor.execute("INSERT OR IGNORE INTO process (id, name) VALUES (1, 'плавка стали'), (2, 'фрезерование'), (3, 'покраска'), (4, 'каталазирование')")
cursor.execute("INSERT OR IGNORE INTO equipment (id, name) VALUES (1, 'плавильный дом'), (2, 'фрезерный станок'), (3, 'покрасочный цех'), (4, 'каталазный цех')")
cursor.execute("INSERT OR IGNORE INTO sensor (id, name) VALUES (1, 'температура стали'), (2, 'температура фрезерного станка'), (3, 'плотность покраски'), (4, 'температура каталазного цеха')")
cursor.execute("INSERT OR IGNORE INTO goal (id, description) VALUES (1, 'оптимизация производственного процесса, снижение затрат, улучшение качества продукции')")
cursor.execute("INSERT OR IGNORE INTO data_source (id, type) VALUES (1, 'датчики на оборудовании'), (2, 'системы управления производством (MES)'), (3, 'системные журналы')")
cursor.execute("INSERT OR IGNORE INTO update_frequency (id, frequency) VALUES (1, 'время от времени, в зависимости от типа задачи')")
cursor.execute("INSERT OR IGNORE INTO critical_parameter (id, sensor_id, value) VALUES (1, 1, 100.00), (2, 2, 120.00), (3, 3, 0.50)")
cursor.execute("INSERT OR IGNORE INTO additional_info (id, content) VALUES (1, 'важно учитывать сезонные колебания температуры и потребность в точном контроле качества покраски в зимний период')")

conn.commit()

# Create materials
mat_steel = chrono.ChMaterialSurfaceNSC()
mat_steel.SetFriction(0.4)
mat_steel.SetRestitution(0.1)

mat_refractory = chrono.ChMaterialSurfaceNSC()
mat_refractory.SetFriction(0.6)
mat_refractory.SetRestitution(0.05)

# Create ground
ground = chrono.ChBodyEasyBox(20, 1, 20, 1000, True, True)
ground.SetPos(chrono.ChVectorD(0, -0.5, 0))
ground.GetVisualModel().SetFaceColor(chrono.ChColor(0.5, 0.5, 0.5))
ground.SetMaterialSurface(mat_steel)
sys.Add(ground)

# Create furnace (for steel melting)
furnace = chrono.ChBodyEasyBox(4, 3, 4, 2000, True, True)
furnace.SetPos(chrono.ChVectorD(-5, 1.5, 0))
furnace.GetVisualModel().SetFaceColor(chrono.ChColor(0.8, 0.2, 0.2))
furnace.SetMaterialSurface(mat_refractory)
sys.Add(furnace)

# Create milling machine (for machining)
milling_machine = chrono.ChBodyEasyBox(3, 2, 3, 1500, True, True)
milling_machine.SetPos(chrono.ChVectorD(0, 1, 0))
milling_machine.GetVisualModel().SetFaceColor(chrono.ChColor(0.2, 0.6, 0.8))
milling_machine.SetMaterialSurface(mat_steel)
sys.Add(milling_machine)

# Create painting booth (for coating)
painting_booth = chrono.ChBodyEasyBox(5, 3, 5, 1200, True, True)
painting_booth.SetPos(chrono.ChVectorD(5, 1.5, 0))
painting_booth.GetVisualModel().SetFaceColor(chrono.ChColor(0.2, 0.8, 0.2))
painting_booth.SetMaterialSurface(mat_steel)
sys.Add(painting_booth)

# Create catalysis chamber (for catalyst treatment)
catalysis_chamber = chrono.ChBodyEasyBox(4, 2, 4, 1800, True, True)
catalysis_chamber.SetPos(chrono.ChVectorD(10, 1, 0))
catalysis_chamber.GetVisualModel().SetFaceColor(chrono.ChColor(0.8, 0.8, 0.2))
catalysis_chamber.SetMaterialSurface(mat_refractory)
sys.Add(catalysis_chamber)

# Create a simple steel ball for melting demonstration
steel_ball = chrono.ChBodyEasySphere(0.5, 7800, True, True)
steel_ball.SetPos(chrono.ChVectorD(-5, 3, 0))
steel_ball.GetVisualModel().SetFaceColor(chrono.ChColor(0.9, 0.9, 0.9))
steel_ball.SetMaterialSurface(mat_steel)
sys.Add(steel_ball)

# Add some constraints between bodies
# Fix furnace to ground
fix_furnace = chrono.ChLinkLockFixed()
fix_furnace.Initialize(furnace, ground, chrono.ChFrameD(chrono.ChVectorD(-5, 1.5, 0)))
sys.Add(fix_furnace)

# Fix milling machine to ground
fix_milling = chrono.ChLinkLockFixed()
fix_milling.Initialize(milling_machine, ground, chrono.ChFrameD(chrono.ChVectorD(0, 1, 0)))
sys.Add(fix_milling)

# Fix painting booth to ground
fix_painting = chrono.ChLinkLockFixed()
fix_painting.Initialize(painting_booth, ground, chrono.ChFrameD(chrono.ChVectorD(5, 1.5, 0)))
sys.Add(fix_painting)

# Fix catalysis chamber to ground
fix_catalysis = chrono.ChLinkLockFixed()
fix_catalysis.Initialize(catalysis_chamber, ground, chrono.ChFrameD(chrono.ChVectorD(10, 1, 0)))
sys.Add(fix_catalysis)

# Create sensors
class Sensor:
    def __init__(self, name, equipment_id):
        self.name = name
        self.equipment_id = equipment_id
        # Get sensor ID from DB
        cursor.execute("SELECT id FROM sensor WHERE name=?", (name,))
        result = cursor.fetchone()
        self.sensor_id = result[0] if result else None

    def read_value(self, time_step):
        # Simulate sensor readings
        if self.name == 'температура стали':
            # Simulate heating process
            base_temp = 20
            heat_increase = 0.1 * time_step
            return base_temp + heat_increase
        
        elif self.name == 'температура фрезерного станка':
            # Simulate steady state operation
            return 120 + 5 * np.sin(time_step * 0.01)
        
        elif self.name == 'плотность покраски':
            # Simulate constant density
            return 0.5
        
        elif self.name == 'температура каталазного цеха':
            # Simulate ambient temperature with variation
            return 25 + 3 * np.sin(time_step * 0.005)
        
        return 0

# Create sensors for each equipment
sensors = [
    Sensor('температура стали', 1),
    Sensor('температура фрезерного станка', 2),
    Sensor('плотность покраски', 3),
    Sensor('температура каталазного цеха', 4)
]

# Create Irrlicht visualization
vis = chronoirr.ChVisualSystemIrrlicht()
vis.AttachSystem(sys)
vis.SetWindowSize(1024, 768)
vis.SetWindowTitle('Digital Twin Simulation')
vis.Initialize()
vis.AddLogo()
vis.AddSkyBox()
vis.AddCamera(chrono.ChVectorD(0, 5, 10))
vis.AddTypicalLights()

# Simulation settings
time_step = 0.01
end_time = 100
current_time = 0
log_interval = 1.0
last_log_time = 0

# Main simulation loop
while vis.Run():
    # Step the system
    sys.DoStepDynamics(time_step)
    current_time += time_step
    
    # Update visualization
    vis.Update()
    
    # Log data at specified intervals
    if current_time - last_log_time >= log_interval:
        timestamp = datetime.datetime.now()
        last_log_time = current_time
        
        # Log sensor data
        for sensor in sensors:
            value = sensor.read_value(current_time)
            
            # Insert into database
            cursor.execute(
                "INSERT INTO simulation_data (timestamp, equipment_id, sensor_id, value) VALUES (?, ?, ?, ?)",
                (timestamp, sensor.equipment_id, sensor.sensor_id, value)
            )
            
            print(f"Time: {current_time:.2f}s | Equipment: {sensor.equipment_id} | Sensor: {sensor.name} | Value: {value:.2f}")
        
        conn.commit()
    
    # Check for critical parameters
    for sensor in sensors:
        value = sensor.read_value(current_time)
        if sensor.name == 'температура стали' and value > 110:
            print(f"CRITICAL: Steel temperature ({value:.2f}°C) exceeds limit!")
        elif sensor.name == 'температура фрезерного станка' and value > 130:
            print(f"CRITICAL: Milling machine temperature ({value:.2f}°C) exceeds limit!")
        elif sensor.name == 'плотность покраски' and value < 0.45:
            print(f"CRITICAL: Paint density ({value:.2f}) is below acceptable range!")

# Clean up
conn.close()
```