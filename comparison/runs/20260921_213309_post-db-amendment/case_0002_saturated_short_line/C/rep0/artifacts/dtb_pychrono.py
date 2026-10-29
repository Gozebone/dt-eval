```python
import pychrono as chrono
import pychrono.irrlicht as chronoirr
import pychrono.fea as fea
import numpy as np
import time
import json
from datetime import datetime, timedelta
import sqlite3
import threading

# Initialize PyChrono system
chrono.SetChronoDataPath('/usr/local/share/chrono/data/')
chrono.SetChronoDataPath('chrono/data')

# Create the physical system
sys = chrono.ChSystemNSC()
sys.Set_G_acc(chrono.ChVectorD(0, -9.81, 0))  # Gravity

# Create ground
ground = chrono.ChBody()
ground.SetFixed(True)
ground.SetBodyFixed(True)
sys.Add(ground)

# Create materials
steel_mat = chrono.ChMaterialSurfaceNSC()
steel_mat.SetFriction(0.5)
steel_mat.SetRestitution(0.1)

# Create a simple part to represent products
def create_part():
    part = chrono.ChBody()
    part.SetMass(1.0)
    part.SetInertiaXX(chrono.ChVectorD(0.01, 0.01, 0.01))
    part.SetBodyFixed(False)
    
    # Create a collision shape
    shape = chrono.ChCollisionModel()
    shape.SetShape(chrono.ChSphere(0.05))
    part.AddAsset(shape)
    
    # Add a visual shape
    vis = chrono.ChVisualShape()
    vis.SetGeometry(chrono.ChSphere(0.05))
    vis.SetColor(chrono.ChColor(0.8, 0.2, 0.2))
    part.AddAsset(vis)
    
    return part

# Create source that emits parts every 60 seconds
class PartSource:
    def __init__(self, system, inter_arrival_s=60):
        self.system = system
        self.inter_arrival_s = inter_arrival_s
        self.last_emission_time = 0
        self.part_count = 0
        
    def update(self, current_time):
        if current_time - self.last_emission_time >= self.inter_arrival_s:
            part = create_part()
            part.SetPos(chrono.ChVectorD(-2, 0.5, 0))
            part.SetRot(chrono.QUNIT)
            self.system.Add(part)
            self.last_emission_time = current_time
            self.part_count += 1
            return part
        return None

# Create buffer with capacity constraint
class Buffer:
    def __init__(self, id, capacity):
        self.id = id
        self.capacity = capacity
        self.parts = []
        self.position = chrono.ChVectorD(0, 0, 0)
        
    def add_part(self, part):
        if len(self.parts) < self.capacity:
            self.parts.append(part)
            return True
        return False
        
    def remove_part(self):
        if self.parts:
            return self.parts.pop(0)
        return None
        
    def get_count(self):
        return len(self.parts)

# Create machines with failure modeling
class Machine:
    def __init__(self, id, process_time_s, availability, mttr_s, work_power_kw, idle_power_kw):
        self.id = id
        self.process_time_s = process_time_s
        self.availability = availability
        self.mttr_s = mttr_s
        self.work_power_kw = work_power_kw
        self.idle_power_kw = idle_power_kw
        self.is_working = True
        self.is_failed = False
        self.failure_start_time = 0
        self.failure_duration = 0
        self.last_process_start = 0
        self.parts_processed = 0
        self.total_energy_kwh = 0
        self.current_part = None
        self.process_start_time = 0
        self.processing = False
        
    def update(self, current_time, buffer_in, buffer_out, system):
        # Check for machine failures
        if not self.is_failed and not self.is_working:
            # Check if machine should be repaired
            if current_time - self.failure_start_time >= self.mttr_s:
                self.is_failed = False
                self.is_working = True
                self.failure_duration = current_time - self.failure_start_time
                
        elif not self.is_failed and self.is_working:
            # Check if machine should fail based on availability
            if np.random.random() < (1 - self.availability) * 0.01:  # 1% chance per second
                self.is_failed = True
                self.is_working = False
                self.failure_start_time = current_time
                
        # Handle part processing
        if not self.processing and buffer_in.get_count() > 0 and self.is_working and not self.is_failed:
            part = buffer_in.remove_part()
            if part:
                self.current_part = part
                self.processing = True
                self.process_start_time = current_time
                self.last_process_start = current_time
                
        elif self.processing and current_time - self.process_start_time >= self.process_time_s:
            # Process complete
            if self.current_part and buffer_out.add_part(self.current_part):
                self.parts_processed += 1
                self.current_part = None
                self.processing = False
                self.total_energy_kwh += self.work_power_kw * self.process_time_s / 3600.0
            else:
                # Move part back to input buffer if output is full
                if self.current_part:
                    buffer_in.add_part(self.current_part)
                    self.current_part = None
                    self.processing = False
                    
        elif self.is_failed or not self.is_working:
            # Machine is not working, consume idle power
            self.total_energy_kwh += self.idle_power_kw * 0.1 / 3600.0  # 0.1s step
            
        return self.is_working

# Create simulation objects
machine_configs = [
    {
        'id': 'M1',
        'process_time_s': 90,
        'availability': 0.99,
        'mttr_s': 600,
        'work_power_kw': 3.0,
        'idle_power_kw': 0.3
    },
    {
        'id': 'M2',
        'process_time_s': 70,
        'availability': 0.98,
        'mttr_s': 900,
        'work_power_kw': 4.5,
        'idle_power_kw': 0.45
    },
    {
        'id': 'M3',
        'process_time_s': 110,
        'availability': 0.99,
        'mttr_s': 1200,
        'work_power_kw': 6.0,
        'idle_power_kw': 0.6
    }
]

# Create buffers
buffers = [
    Buffer('B0', 15),
    Buffer('B1', 5),
    Buffer('B2', 5)
]

# Create machines
machines = []
for config in machine_configs:
    machine = Machine(
        config['id'],
        config['process_time_s'],
        config['availability'],
        config['mttr_s'],
        config['work_power_kw'],
        config['idle_power_kw']
    )
    machines.append(machine)

# Setup source
source = PartSource(sys, 60)

# Create visualization
vis = chronoirr.ChVisualSystemIrrlicht()
vis.AttachSystem(sys)
vis.SetWindowSize(1024, 768)
vis.SetWindowTitle('Production Line Simulation')
vis.Initialize()
vis.AddLogo()
vis.AddSkyBox()
vis.AddCamera(chrono.ChVectorD(0, 2, -5), chrono.ChVectorD(0, 1, 0))
vis.AddTypicalLights()

# Setup logging
def log_to_database(timestamp, machine_id, reason_code, duration_s, energy_kwh):
    """Log event to database"""
    pass  # In a real implementation, this would insert into database

def log_sample(timestamp, machine_id, tag, value):
    """Log sample to database"""
    pass  # In a real implementation, this would insert into database

# Simulation parameters
sim_time = 0
time_step = 0.1  # seconds
max_sim_time = 432000  # 5 days in seconds

# Connect buffers to machines
buffer_connections = [
    (buffers[0], machines[0]),  # B0 to M1
    (machines[0], machines[1]), # M1 to M2
    (machines[1], machines[2]), # M2 to M3
    (machines[2], buffers[2])   # M3 to B2
]

# Sensor data collection
sensor_data = {
    'temp_M1': 25.0,
    'pressure_M1': 1.0,
    'temp_M2': 25.0,
    'pressure_M2': 1.0,
    'temp_M3': 25.0,
    'pressure_M3': 1.0
}

# Main simulation loop
start_time = time.time()
print("Starting simulation...")

while sim_time < max_sim_time:
    # Update simulation time
    sim_time += time_step
    
    # Update source
    source.update(sim_time)
    
    # Update machines and buffers
    for machine in machines:
        if machine.id == 'M1':
            machine.update(sim_time, buffers[0], buffers[1], sys)
        elif machine.id == 'M2':
            machine.update(sim_time, buffers[1], buffers[2], sys)
        elif machine.id == 'M3':
            machine.update(sim_time, buffers[2], None, sys)
    
    # Log sensor data every second
    if int(sim_time) % 1 == 0:
        timestamp = datetime.now()
        for tag, value in sensor_data.items():
            # In a real implementation, this would log to database
            pass
    
    # Log machine events every 10 seconds
    if int(sim_time) % 10 == 0:
        for machine in machines:
            if machine.is_failed:
                log_to_database(
                    timestamp,
                    machine.id,
                    'FAILURE',
                    machine.failure_duration,
                    machine.total_energy_kwh
                )
    
    # Step the simulation
    sys.DoStepDynamics(time_step)
    
    # Update visualization
    if vis.Run():
        vis.Update()
    else:
        break

# Final statistics
print("Simulation completed")
print(f"Total time: {sim_time:.1f} seconds")
print("Machine statistics:")
for machine in machines:
    print(f"  {machine.id}: Processed {machine.parts_processed} parts, "
          f"Energy: {machine.total_energy_kwh:.2f} kWh")

# Cleanup
vis.Shutdown()
```