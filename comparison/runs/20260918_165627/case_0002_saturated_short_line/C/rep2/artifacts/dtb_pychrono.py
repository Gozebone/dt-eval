```python
import pychrono as chrono
import pychrono.irrlicht as chronoirr
import numpy as np
import time
import csv
import os

# Define constants for the simulation
SIMULATION_TIME = 432000  # 5 days in seconds
TIME_STEP = 0.01
LOG_INTERVAL = 1.0  # Log every second
SOURCE_INTERVAL = 60.0  # New parts every 60 seconds

# Create the Chrono system
system = chrono.ChSystemNSC()
system.Set_G_acc(chrono.ChVectorD(0, 0, 0))  # No gravity for this line

# Create materials
steel_mat = chrono.ChMaterialSurfaceNSC()
steel_mat.SetFriction(0.5)
steel_mat.SetRestitution(0.1)

# Create the ground
ground = chrono.ChBody()
ground.SetFixed(True)
ground.GetCollisionModel().ClearModel()
ground.GetCollisionModel().AddBox(100, 1, 100)
ground.SetPos(chrono.ChVectorD(0, -1, 0))
ground.SetMaterialSurface(steel_mat)
system.Add(ground)

# Create part source
class PartSource:
    def __init__(self, system, pos, part_id):
        self.system = system
        self.pos = pos
        self.part_id = part_id
        self.next_spawn_time = 0.0
        self.spawned_count = 0
        
    def update(self, current_time):
        if current_time >= self.next_spawn_time:
            self.spawn_part(current_time)
            self.next_spawn_time = current_time + SOURCE_INTERVAL
            
    def spawn_part(self, current_time):
        part = chrono.ChBody()
        part.SetPos(self.pos)
        part.GetCollisionModel().ClearModel()
        part.GetCollisionModel().AddBox(0.5, 0.5, 0.5)
        part.SetMaterialSurface(steel_mat)
        part.SetMass(1.0)
        part.SetInertiaXX(chrono.ChVectorD(0.1, 0.1, 0.1))
        part.SetBodyFixed(False)
        self.system.Add(part)
        
        # Create a sensor to track this part
        part_sensor = PartSensor(part, self.part_id, current_time)
        self.part_id += 1
        self.spawned_count += 1
        
        return part, part_sensor

# Create machine M1
class MachineM1:
    def __init__(self, system, pos):
        self.system = system
        self.pos = pos
        self.is_operational = True
        self.processing_time = 120.0  # 2 minutes to process
        self.power_consumption = 1000.0  # 1 kW
        self.energy_consumed = 0.0
        self.processing_started = 0.0
        self.processing_part = None
        self.in_queue = []
        self.status = "IDLE"
        
        # Machine body
        self.machine_body = chrono.ChBody()
        self.machine_body.SetPos(pos)
        self.machine_body.GetCollisionModel().ClearModel()
        self.machine_body.GetCollisionModel().AddBox(2, 1, 1)
        self.machine_body.SetMaterialSurface(steel_mat)
        self.machine_body.SetMass(100.0)
        self.machine_body.SetBodyFixed(True)
        self.system.Add(self.machine_body)
        
        # Machine motor (simple representation)
        self.motor = chrono.ChBody()
        self.motor.SetPos(pos + chrono.ChVectorD(0, 0.5, 0))
        self.motor.GetCollisionModel().ClearModel()
        self.motor.GetCollisionModel().AddBox(0.5, 0.2, 0.2)
        self.motor.SetMaterialSurface(steel_mat)
        self.motor.SetMass(10.0)
        self.motor.SetBodyFixed(True)
        self.system.Add(self.motor)
        
    def update(self, current_time):
        # Update power consumption
        if self.status == "PROCESSING":
            self.energy_consumed += self.power_consumption * TIME_STEP
            
        # Check if processing is complete
        if self.status == "PROCESSING" and current_time - self.processing_started >= self.processing_time:
            self.status = "IDLE"
            self.processing_part = None
            
    def start_processing(self, part):
        self.processing_part = part
        self.processing_started = time.time()
        self.status = "PROCESSING"

# Create buffer B0
class BufferB0:
    def __init__(self, system, pos, capacity):
        self.system = system
        self.pos = pos
        self.capacity = capacity
        self.parts = []
        self.current_count = 0
        
        # Buffer structure
        self.buffer_body = chrono.ChBody()
        self.buffer_body.SetPos(pos)
        self.buffer_body.GetCollisionModel().ClearModel()
        self.buffer_body.GetCollisionModel().AddBox(3, 0.5, 2)
        self.buffer_body.SetMaterialSurface(steel_mat)
        self.buffer_body.SetMass(50.0)
        self.buffer_body.SetBodyFixed(True)
        self.system.Add(self.buffer_body)
        
    def add_part(self, part):
        if self.current_count < self.capacity:
            self.parts.append(part)
            self.current_count += 1
            return True
        return False
        
    def remove_part(self):
        if self.current_count > 0:
            part = self.parts.pop(0)
            self.current_count -= 1
            return part
        return None

# Part sensor to track details
class PartSensor:
    def __init__(self, part, part_id, start_time):
        self.part_id = part_id
        self.part = part
        self.start_time = start_time
        self.processing_start_times = []
        self.processing_end_times = []
        self.positions = []
        self.recorded = False
        
    def update(self, current_time):
        self.positions.append((current_time, self.part.GetPos()))
        
    def mark_processed(self, process_time):
        self.processing_end_times.append(process_time)

# Logging system to record data to CSV files
class DataLogger:
    def __init__(self, base_path="simulation_data"):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
        
        # Create log files
        self.machine_log = open(os.path.join(base_path, "machine_status.csv"), "w", newline="")
        self.energy_log = open(os.path.join(base_path, "energy_consumption.csv"), "w", newline="")
        self.buffer_log = open(os.path.join(base_path, "buffer_status.csv"), "w", newline="")
        self.part_log = open(os.path.join(base_path, "part_events.csv"), "w", newline="")
        
        # Write headers
        self.machine_writer = csv.writer(self.machine_log)
        self.machine_writer.writerow(["timestamp", "machine", "status", "energy_consumed"])
        
        self.energy_writer = csv.writer(self.energy_log)
        self.energy_writer.writerow(["timestamp", "machine", "power_consumption"])
        
        self.buffer_writer = csv.writer(self.buffer_log)
        self.buffer_writer.writerow(["timestamp", "buffer", "part_count", "capacity"])
        
        self.part_writer = csv.writer(self.part_log)
        self.part_writer.writerow(["timestamp", "part_id", "event_type", "location"])
        
    def log_machine_status(self, timestamp, machine, status, energy_consumed):
        self.machine_writer.writerow([timestamp, machine, status, energy_consumed])
        
    def log_energy_consumption(self, timestamp, machine, power_consumption):
        self.energy_writer.writerow([timestamp, machine, power_consumption])
        
    def log_buffer_status(self, timestamp, buffer, part_count, capacity):
        self.buffer_writer.writerow([timestamp, buffer, part_count, capacity])
        
    def log_part_event(self, timestamp, part_id, event_type, location):
        self.part_writer.writerow([timestamp, part_id, event_type, location])
        
    def close(self):
        self.machine_log.close()
        self.energy_log.close()
        self.buffer_log.close()
        self.part_log.close()

# Initialize simulation components
part_id_counter = 0
source = PartSource(system, chrono.ChVectorD(-40, 0, 0), part_id_counter)
machine_m1 = MachineM1(system, chrono.ChVectorD(-20, 0, 0))
buffer_b0 = BufferB0(system, chrono.ChVectorD(0, 0, 0), 10)
machine_m2 = MachineM2(system, chrono.ChVectorD(20, 0, 0))
buffer_b1 = BufferB0(system, chrono.ChVectorD(40, 0, 0), 10)
machine_m3 = MachineM3(system, chrono.ChVectorD(60, 0, 0))
buffer_b2 = BufferB0(system, chrono.ChVectorD(80, 0, 0), 10)

# Create additional machines and buffers as needed
class MachineM2:
    def __init__(self, system, pos):
        self.system = system
        self.pos = pos
        self.is_operational = True
        self.processing_time = 180.0  # 3 minutes to process
        self.power_consumption = 1200.0  # 1.2 kW
        self.energy_consumed = 0.0
        self.processing_started = 0.0
        self.processing_part = None
        self.status = "IDLE"
        
        # Machine body
        self.machine_body = chrono.ChBody()
        self.machine_body.SetPos(pos)
        self.machine_body.GetCollisionModel().ClearModel()
        self.machine_body.GetCollisionModel().AddBox(2, 1, 1)
        self.machine_body.SetMaterialSurface(steel_mat)
        self.machine_body.SetMass(100.0)
        self.machine_body.SetBodyFixed(True)
        self.system.Add(self.machine_body)
        
    def update(self, current_time):
        # Update power consumption
        if self.status == "PROCESSING":
            self.energy_consumed += self.power_consumption * TIME_STEP
            
        # Check if processing is complete
        if self.status == "PROCESSING" and current_time - self.processing_started >= self.processing_time:
            self.status = "IDLE"
            self.processing_part = None
            
    def start_processing(self, part):
        self.processing_part = part
        self.processing_started = time.time()
        self.status = "PROCESSING"

class MachineM3:
    def __init__(self, system, pos):
        self.system = system
        self.pos = pos
        self.is_operational = True
        self.processing_time = 150.0  # 2.5 minutes to process
        self.power_consumption = 1100.0  # 1.1 kW
        self.energy_consumed = 0.0
        self.processing_started = 0.0
        self.processing_part = None
        self.status = "IDLE"
        
        # Machine body
        self.machine_body = chrono.ChBody()
        self.machine_body.SetPos(pos)
        self.machine_body.GetCollisionModel().ClearModel()
        self.machine_body.GetCollisionModel().AddBox(2, 1, 1)
        self.machine_body.SetMaterialSurface(steel_mat)
        self.machine_body.SetMass(100.0)
        self.machine_body.SetBodyFixed(True)
        self.system.Add(self.machine_body)
        
    def update(self, current_time):
        # Update power consumption
        if self.status == "PROCESSING":
            self.energy_consumed += self.power_consumption * TIME_STEP
            
        # Check if processing is complete
        if self.status == "PROCESSING" and current_time - self.processing_started >= self.processing_time:
            self.status = "IDLE"
            self.processing_part = None
            
    def start_processing(self, part):
        self.processing_part = part
        self.processing_started = time.time()
        self.status = "PROCESSING"

# Initialize data logger
logger = DataLogger()

# Simulation time tracking
current_time = 0.0
last_log_time = 0.0
last_part_source_time = 0.0

# Main simulation loop
while current_time < SIMULATION_TIME:
    # Step the system
    system.DoStepDynamics(TIME_STEP)
    
    # Update the source
    source.update(current_time)
    
    # Update machines and buffers
    machine_m1.update(current_time)
    machine_m2.update(current_time)
    machine_m3.update(current_time)
    
    # Log data periodically
    if current_time - last_log_time >= LOG_INTERVAL:
        logger.log_machine_status(current_time, "M1", machine_m1.status, machine_m1.energy_consumed)
        logger.log_energy_consumption(current_time, "M1", machine_m1.power_consumption)
        logger.log_buffer_status(current_time, "B0", buffer_b0.current_count, buffer_b0.capacity)
        logger.log_machine_status(current_time, "M2", machine_m2.status, machine_m2.energy_consumed)
        logger.log_energy_consumption(current_time, "M2", machine_m2.power_consumption)
        logger.log_buffer_status(current_time, "B1", buffer_b1.current_count, buffer_b1.capacity)
        logger.log_machine_status(current_time, "M3", machine_m3.status, machine_m3.energy_consumed)
        logger.log_energy_consumption(current_time, "M3", machine_m3.power_consumption)
        logger.log_buffer_status(current_time, "B2", buffer_b2.current_count, buffer_b2.capacity)
        
        last_log_time = current_time
    
    current_time += TIME_STEP

# Close log files
logger.close()
print("Simulation completed successfully.")
```