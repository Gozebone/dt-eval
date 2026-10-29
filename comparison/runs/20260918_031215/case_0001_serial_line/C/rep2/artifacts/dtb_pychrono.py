import pychrono as chrono
import pychrono.irrlicht as irr
import numpy as np
import time
import threading
import sqlite3
from datetime import datetime

# Initialize PyChrono system
chrono.SetChronoDataPath('/usr/local/share/chrono/data/')
chrono.SetChronoDataPath('/opt/chrono/data/')

# Create the simulation system
system = chrono.ChSystemNSC()
system.Set_G_acc(chrono.ChVectorD(0, -9.81, 0))  # Set gravity

# Create ground body
ground = chrono.ChBody()
ground.SetFixed(True)
ground.SetBodyFixed(True)
system.Add(ground)

# Create visualization
vis = irr.ChVisualSystemIrrlicht()
vis.SetWindowSize(1024, 768)
vis.SetWindowTitle('Production Line Digital Twin')
vis.Initialize()
vis.AddLogo()
vis.AddSkyBox()
vis.AddCamera(chrono.ChVectorD(10, 10, 10), chrono.ChVectorD(0, 0, 0))
vis.AddTypicalLights()

# Create materials
steel_mat = chrono.ChMaterialSurfaceNSC()
steel_mat.SetFriction(0.5)
steel_mat.SetRestitution(0.1)

refractory_mat = chrono.ChMaterialSurfaceNSC()
refractory_mat.SetFriction(0.3)
refractory_mat.SetRestitution(0.05)

# Create machines (M1-M5)
machines = []
machine_positions = [
    chrono.ChVectorD(0, 0, 0),
    chrono.ChVectorD(5, 0, 0),
    chrono.ChVectorD(10, 0, 0),
    chrono.ChVectorD(15, 0, 0),
    chrono.ChVectorD(20, 0, 0)
]

for i in range(5):
    machine = chrono.ChBody()
    machine.SetPos(machine_positions[i])
    machine.SetMass(1000)
    machine.SetInertiaXX(chrono.ChVectorD(100, 100, 100))
    machine.GetCollisionModel().ClearModel()
    machine.GetCollisionModel().AddBox(1, 1, 1)
    machine.GetCollisionModel().BuildModel()
    machine.SetMaterialSurface(steel_mat)
    system.Add(machine)
    machines.append(machine)

# Create buffers (B0-B4)
buffers = []
buffer_positions = [
    chrono.ChVectorD(2.5, 0, 0),
    chrono.ChVectorD(7.5, 0, 0),
    chrono.ChVectorD(12.5, 0, 0),
    chrono.ChVectorD(17.5, 0, 0),
    chrono.ChVectorD(22.5, 0, 0)
]

for i in range(5):
    buffer = chrono.ChBody()
    buffer.SetPos(buffer_positions[i])
    buffer.SetMass(500)
    buffer.SetInertiaXX(chrono.ChVectorD(50, 50, 50))
    buffer.GetCollisionModel().ClearModel()
    buffer.GetCollisionModel().AddBox(1.5, 0.5, 1.5)
    buffer.GetCollisionModel().BuildModel()
    buffer.SetMaterialSurface(steel_mat)
    system.Add(buffer)
    buffers.append(buffer)

# Create sink (final product)
sink = chrono.ChBody()
sink.SetPos(chrono.ChVectorD(25, 0, 0))
sink.SetMass(1000)
sink.SetInertiaXX(chrono.ChVectorD(100, 100, 100))
sink.GetCollisionModel().ClearModel()
sink.GetCollisionModel().AddBox(1.5, 1.5, 1.5)
sink.GetCollisionModel().BuildModel()
sink.SetMaterialSurface(steel_mat)
system.Add(sink)

# Create pipeline connections between machines and buffers
connections = []
for i in range(4):
    # Create constraints between machines and buffers
    constraint = chrono.ChLinkLockRevolute()
    constraint.Initialize(machines[i], buffers[i], chrono.ChVectorD(0, 0, 0))
    system.Add(constraint)
    connections.append(constraint)
    
    # Create constraints between buffers and next machine
    constraint2 = chrono.ChLinkLockRevolute()
    constraint2.Initialize(buffers[i], machines[i+1], chrono.ChVectorD(0, 0, 0))
    system.Add(constraint2)
    connections.append(constraint2)

# Create product parts
product_parts = []
part_positions = [
    chrono.ChVectorD(0.5, 1, 0),
    chrono.ChVectorD(1.5, 1, 0),
    chrono.ChVectorD(2.5, 1, 0),
    chrono.ChVectorD(3.5, 1, 0),
    chrono.ChVectorD(4.5, 1, 0)
]

for i, pos in enumerate(part_positions):
    part = chrono.ChBody()
    part.SetPos(pos)
    part.SetMass(10)
    part.SetInertiaXX(chrono.ChVectorD(0.1, 0.1, 0.1))
    part.GetCollisionModel().ClearModel()
    part.GetCollisionModel().AddSphere(0.1)
    part.GetCollisionModel().BuildModel()
    part.SetMaterialSurface(steel_mat)
    system.Add(part)
    product_parts.append(part)

# Create sensors to monitor machines
machine_sensors = []
for i in range(5):
    sensor = {
        'machine_id': f'M{i+1}',
        'process_time': 0,
        'availability': 1.0,
        'mttr': 0,
        'power': 0,
        'last_update': datetime.now(),
        'status': 'active',
        'wip': 0
    }
    machine_sensors.append(sensor)

# Create buffer sensors
buffer_sensors = []
for i in range(5):
    sensor = {
        'buffer_id': f'B{i}',
        'capacity': 10,
        'current_level': 0,
        'max_level': 10,
        'last_update': datetime.now(),
        'status': 'empty'
    }
    buffer_sensors.append(sensor)

# Create sink sensor
sink_sensor = {
    'sink_id': 'SINK',
    'products_count': 0,
    'last_update': datetime.now(),
    'status': 'ready'
}

# Database setup
def setup_database():
    conn = sqlite3.connect('production_line.db')
    cursor = conn.cursor()
    
    # Create machine status table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS machine_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id TEXT,
            process_time REAL,
            availability REAL,
            mttr REAL,
            power REAL,
            status TEXT,
            wip INTEGER,
            timestamp DATETIME
        )
    ''')
    
    # Create buffer status table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS buffer_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            buffer_id TEXT,
            capacity INTEGER,
            current_level INTEGER,
            max_level INTEGER,
            status TEXT,
            timestamp DATETIME
        )
    ''')
    
    # Create sink status table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sink_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sink_id TEXT,
            products_count INTEGER,
            status TEXT,
            timestamp DATETIME
        )
    ''')
    
    # Create production statistics table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS production_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME,
            throughput INTEGER,
            wip INTEGER,
            energy_consumption REAL,
            machine_utilization REAL
        )
    ''')
    
    conn.commit()
    conn.close()

# Insert data into database
def insert_machine_status(sensor_data):
    conn = sqlite3.connect('production_line.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO machine_status 
        (machine_id, process_time, availability, mttr, power, status, wip, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        sensor_data['machine_id'],
        sensor_data['process_time'],
        sensor_data['availability'],
        sensor_data['mttr'],
        sensor_data['power'],
        sensor_data['status'],
        sensor_data['wip'],
        sensor_data['last_update']
    ))
    
    conn.commit()
    conn.close()

def insert_buffer_status(sensor_data):
    conn = sqlite3.connect('production_line.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO buffer_status 
        (buffer_id, capacity, current_level, max_level, status, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        sensor_data['buffer_id'],
        sensor_data['capacity'],
        sensor_data['current_level'],
        sensor_data['max_level'],
        sensor_data['status'],
        sensor_data['last_update']
    ))
    
    conn.commit()
    conn.close()

def insert_sink_status(sensor_data):
    conn = sqlite3.connect('production_line.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO sink_status 
        (sink_id, products_count, status, timestamp)
        VALUES (?, ?, ?, ?)
    ''', (
        sensor_data['sink_id'],
        sensor_data['products_count'],
        sensor_data['status'],
        sensor_data['last_update']
    ))
    
    conn.commit()
    conn.close()

def insert_production_stats(throughput, wip, energy_consumption, machine_utilization):
    conn = sqlite3.connect('production_line.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO production_stats 
        (timestamp, throughput, wip, energy_consumption, machine_utilization)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        datetime.now(),
        throughput,
        wip,
        energy_consumption,
        machine_utilization
    ))
    
    conn.commit()
    conn.close()

# Simulate machine operation
def simulate_machine_operation(machine_index, process_time, availability, mttr):
    # Simulate machine behavior
    time.sleep(process_time)
    
    # Simulate breakdowns
    if np.random.rand() > availability:
        # Simulate machine breakdown
        time.sleep(mttr)
        return False
    return True

# Main simulation loop
def run_simulation():
    print("Starting production line simulation...")
    
    # Setup database
    setup_database()
    
    # Simulation parameters
    sim_time = 0
    dt = 0.01
    max_time = 1000
    
    try:
        while sim_time < max_time:
            # Update simulation
            system.DoStepDynamics(dt)
            
            # Update sensors
            for i, machine in enumerate(machines):
                # Update machine status
                machine_sensors[i]['process_time'] = np.random.uniform(1, 3)
                machine_sensors[i]['availability'] = np.random.uniform(0.9, 1.0)
                machine_sensors[i]['mttr'] = np.random.uniform(0.5, 2.0)
                machine_sensors[i]['power'] = np.random.uniform(50, 100)
                machine_sensors[i]['wip'] = np.random.randint(0, 5)
                machine_sensors[i]['last_update'] = datetime.now()
                
                # Log machine data
                insert_machine_status(machine_sensors[i])
            
            # Update buffer sensors
            for i, buffer in enumerate(buffers):
                buffer_sensors[i]['current_level'] = np.random.randint(0, 10)
                buffer_sensors[i]['status'] = 'full' if buffer_sensors[i]['current_level'] >= 8 else 'normal' if buffer_sensors[i]['current_level'] >= 2 else 'empty'
                buffer_sensors[i]['last_update'] = datetime.now()
                
                # Log buffer data
                insert_buffer_status(buffer_sensors[i])
            
            # Update sink sensor
            sink_sensor['products_count'] = np.random.randint(0, 100)
            sink_sensor['status'] = 'ready'
            sink_sensor['last_update'] = datetime.now()
            
            # Log sink data
            insert_sink_status(sink_sensor)
            
            # Calculate statistics
            throughput = np.random.randint(1, 10)
            wip = sum([s['wip'] for s in machine_sensors])
            energy_consumption = sum([s['power'] for s in machine_sensors])
            machine_utilization = np.mean([s['availability'] for s in machine_sensors])
            
            # Log production statistics
            insert_production_stats(throughput, wip, energy_consumption, machine_utilization)
            
            # Update visualization
            if vis.Run():
                vis.Render()
            
            sim_time += dt
            
            # Add delay for visualization
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        print("Simulation interrupted by user")
    except Exception as e:
        print(f"Simulation error: {e}")
    finally:
        # Cleanup
        print("Simulation finished")
        print("Data saved to database: production_line.db")

# Run the simulation
if __name__ == "__main__":
    run_simulation()