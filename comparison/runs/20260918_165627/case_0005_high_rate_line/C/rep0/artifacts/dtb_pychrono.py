```python
import pychrono as chrono
import pychrono.irrlicht as irr
import pychrono.fea as fea
import math
import numpy as np
import matplotlib.pyplot as plt
import time
import csv

# Initialize the Chrono system
chrono.SetChronoDataPath('path_to_chrono_data')
chrono.SetChronoDataPath('path_to_chrono_data')

# Create the physical system
system = chrono.ChSystemNSC()
system.Set_G_acc(chrono.ChVectorD(0, -9.81, 0))  # Set gravity

# Define materials
material_steel = chrono.ChMaterialSurfaceNSC()
material_steel.SetFriction(0.4)
material_steel.SetRestitution(0.1)

material_concrete = chrono.ChMaterialSurfaceNSC()
material_concrete.SetFriction(0.6)
material_concrete.SetRestitution(0.05)

# Create a ground plane
ground = chrono.ChBody()
ground.SetBodyFixed(True)
ground.SetPos(chrono.ChVectorD(0, -1, 0))
ground.GetCollisionModel().ClearModel()
ground.GetCollisionModel().AddBox(50, 1, 50)
ground.SetMaterialSurface(material_concrete)
system.Add(ground)

# Create buffers B0-B3
buffers = {}
for i in range(4):
    buffer = chrono.ChBody()
    buffer.SetPos(chrono.ChVectorD(-10 + i*5, 0.5, 0))
    buffer.GetCollisionModel().ClearModel()
    buffer.GetCollisionModel().AddBox(2, 1, 2)
    buffer.SetMaterialSurface(material_steel)
    buffer.SetMass(100)
    buffer.SetInertiaXX(chrono.ChVectorD(10, 10, 10))
    system.Add(buffer)
    buffers[f'B{i}'] = buffer

# Create machines M1-M5
machines = {}
for i in range(1, 6):
    machine = chrono.ChBody()
    machine.SetPos(chrono.ChVectorD(10 + i*3, 0.5, 0))
    machine.GetCollisionModel().ClearModel()
    machine.GetCollisionModel().AddBox(1, 1, 1)
    machine.SetMaterialSurface(material_steel)
    machine.SetMass(500)
    machine.SetInertiaXX(chrono.ChVectorD(50, 50, 50))
    system.Add(machine)
    machines[f'M{i}'] = machine

# Create a conveyor belt to move parts
conveyor = chrono.ChBody()
conveyor.SetPos(chrono.ChVectorD(0, 0, 0))
conveyor.SetRot(chrono.Q_from_AngAxis(math.pi/2, chrono.ChVectorD(1, 0, 0)))
conveyor.GetCollisionModel().ClearModel()
conveyor.GetCollisionModel().AddBox(20, 0.1, 1)
conveyor.SetMaterialSurface(material_concrete)
system.Add(conveyor)

# Create parts (workpieces) to simulate the production
parts = []
part_count = 0
part_rate = 10  # parts per second
part_interval = 1.0 / part_rate
last_part_time = 0

# Create sensors to collect data
class ProductionSensor:
    def __init__(self):
        # Simulated sensor data storage
        self.data_log = {
            'part_arrivals': [],
            'part_completions': [],
            'buffer_levels': [],
            'machine_status': {},
            'energy_consumption': [],
            'mttr': [],
            'availability': [],
            'processing_times': []
        }
        self.time = 0
        self.total_energy = 0
        self.working_energy = 0
        self.idle_energy = 0
        self.total_parts = 0
        self.completed_parts = 0
        self.last_processing_time = 0
        
    def log_part_arrival(self, timestamp, part_id):
        self.data_log['part_arrivals'].append((timestamp, part_id))
        self.total_parts += 1
        
    def log_part_completion(self, timestamp, part_id):
        self.data_log['part_completions'].append((timestamp, part_id))
        self.completed_parts += 1
        
    def log_buffer_level(self, timestamp, buffer_id, level):
        self.data_log['buffer_levels'].append((timestamp, buffer_id, level))
        
    def log_machine_status(self, timestamp, machine_id, status, processing_time):
        self.data_log['machine_status'][machine_id] = (timestamp, status, processing_time)
        self.last_processing_time = processing_time
        self.data_log['processing_times'].append((timestamp, machine_id, processing_time))
        
    def log_energy_consumption(self, timestamp, consumption):
        self.data_log['energy_consumption'].append((timestamp, consumption))
        self.total_energy += consumption
        
    def log_mtt(self, timestamp, mttr):
        self.data_log['mttr'].append((timestamp, mttr))
        
    def log_availability(self, timestamp, availability):
        self.data_log['availability'].append((timestamp, availability))
        
    def calculate_metrics(self):
        # Calculate average processing time
        avg_processing_time = np.mean([pt[2] for pt in self.data_log['processing_times']]) if self.data_log['processing_times'] else 0
        
        # Calculate availability 
        availability = self.completed_parts / self.total_parts if self.total_parts > 0 else 0
        
        # Calculate energy per part
        energy_per_part = self.total_energy / self.total_parts if self.total_parts > 0 else 0
        
        # Calculate WIP (Work in Progress)
        wip = self.total_parts - self.completed_parts
        
        return {
            'avg_processing_time': avg_processing_time,
            'availability': availability,
            'energy_per_part': energy_per_part,
            'wip': wip
        }

# Initialize sensors
sensor = ProductionSensor()

# Create a part generator
def generate_part(time):
    global part_count, last_part_time
    if time - last_part_time >= part_interval:
        part_count += 1
        part = chrono.ChBody()
        part.SetPos(chrono.ChVectorD(-20, 0.5, 0))
        part.GetCollisionModel().ClearModel()
        part.GetCollisionModel().AddSphere(0.2)
        part.SetMaterialSurface(material_steel)
        part.SetMass(1)
        part.SetInertiaXX(chrono.ChVectorD(0.1, 0.1, 0.1))
        system.Add(part)
        parts.append(part)
        last_part_time = time
        sensor.log_part_arrival(time, part_count)
        return True
    return False

# Create connection between machines and buffers
# This represents a simple production line
# In a real simulation, these would be actual joints or constraints

# Main simulation loop
time_step = 0.01
end_time = 100
current_time = 0
iteration = 0

# Create Irrlicht visualization (optional)
# vis = irr.ChVisualSystemIrrlicht()
# vis.SetWindowSize(1024, 768)
# vis.SetWindowTitle('Production Line Simulation')
# vis.Initialize()
# vis.AddSkyBox()
# vis.AddCamera(chrono.ChVectorD(0, 5, -10))
# vis.AddLight(chrono.ChVectorD(20, 20, 20), 100, chrono.ChVectorD(1,1,1))

# Simulation data logging
log_file = open('production_simulation_log.csv', 'w', newline='')
log_writer = csv.writer(log_file)
log_writer.writerow([
    'timestamp', 'part_id', 'buffer_level_B0', 'buffer_level_B1', 
    'buffer_level_B2', 'buffer_level_B3', 'machine_status_M1', 
    'machine_status_M2', 'machine_status_M3', 'machine_status_M4', 
    'machine_status_M5', 'energy_consumption', 'availability', 
    'processing_time_M1', 'processing_time_M2', 'processing_time_M3', 
    'processing_time_M4', 'processing_time_M5'
])

# Simulation loop
while current_time < end_time:
    # Generate new parts
    generate_part(current_time)
    
    # Move parts along the conveyor
    for part in parts:
        pos = part.GetPos()
        part.SetPos(chrono.ChVectorD(pos.x + 0.1, pos.y, pos.z))
        
        # If part reaches the end, remove it
        if pos.x > 20:
            system.Remove(part)
            parts.remove(part)
            sensor.log_part_completion(current_time, part_count)
    
    # Update simulation
    system.DoStepDynamics(time_step)
    
    # Collect data every 0.5 seconds
    if iteration % 50 == 0:
        # Log buffer levels
        for i in range(4):
            buffer = buffers[f'B{i}']
            pos = buffer.GetPos()
            sensor.log_buffer_level(current_time, f'B{i}', pos.x)
            
        # Log machine statuses
        for i in range(1, 6):
            machine = machines[f'M{i}']
            pos = machine.GetPos()
            sensor.log_machine_status(current_time, f'M{i}', 'running' if pos.x < 15 else 'idle',
                                    sensor.last_processing_time)
            
        # Log energy consumption
        energy_consumption = 100 if current_time > 50 else 50  # Simulated data
        sensor.log_energy_consumption(current_time, energy_consumption)
        
        # Log availability (simplified)
        availability = sensor.completed_parts / sensor.total_parts if sensor.total_parts > 0 else 0
        sensor.log_availability(current_time, availability)
        
        # Write to CSV
        log_writer.writerow([
            current_time, sensor.total_parts,
            3 if current_time > 50 else 0, 2, 1, 0,
            'running' if current_time > 30 else 'idle',
            'running' if current_time > 35 else 'idle',
            'running' if current_time > 40 else 'idle',
            'running' if current_time > 45 else 'idle',
            'running' if current_time > 50 else 'idle',
            energy_consumption, availability,
            sensor.last_processing_time, sensor.last_processing_time,
            sensor.last_processing_time, sensor.last_processing_time,
            sensor.last_processing_time
        ])
    
    current_time += time_step
    iteration += 1

# Calculate final metrics
metrics = sensor.calculate_metrics()
print("Simulation Results:")
print(f"Average Processing Time: {metrics['avg_processing_time']:.2f}")
print(f"Availability: {metrics['availability']:.2%}")
print(f"Energy per Part: {metrics['energy_per_part']:.2f}")
print(f"Work in Progress: {metrics['wip']}")

# Close log file
log_file.close()

# Cleanup
# vis.RemoveAll()
```