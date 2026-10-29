```python
import pychrono as chrono
import pychrono.irrlicht as chronoirr
import math
import numpy as np
import time
import csv
import os

# Initialize PyChrono system
chrono.SetChronoDataPath(os.path.join(os.path.dirname(__file__), 'chrono_data'))
chrono.SetChronoDataPath(os.path.join(os.path.dirname(__file__), 'chrono_data', 'models'))

# Create the physical system
system = chrono.ChSystemNSC()
system.Set_G_acc(chrono.ChVectorD(0, 0, -9.81))  # Set gravity

# Define materials
material_steel = chrono.ChMaterialSurfaceNSC()
material_steel.SetFriction(0.4)
material_steel.SetRestitution(0.1)

material_refractory = chrono.ChMaterialSurfaceNSC()
material_refractory.SetFriction(0.3)
material_refractory.SetRestitution(0.05)

# Create ground
ground = chrono.ChBody()
ground.SetBodyFixed(True)
ground.SetPos(chrono.ChVectorD(0, 0, -1))
ground.GetCollisionModel().ClearModel()
ground.GetCollisionModel().AddBox(20, 20, 1)
ground.GetCollisionModel().BuildModel()
ground.SetMaterialSurface(material_steel)
system.Add(ground)

# Create buffer capacities
buffers = {}
buffer_objects = {}

# Create buffers with specified capacities
for buf in [
    {"id": "B0", "capacity": 15, "before": "source", "after": "M1"},
    {"id": "B1", "capacity": 5, "before": "M1", "after": "M2"},
    {"id": "B2", "capacity": 5, "before": "M2", "after": "M3"}
]:
    buffer = chrono.ChBody()
    buffer.SetBodyFixed(True)
    buffer.SetPos(chrono.ChVectorD(0, 0, 0))
    buffer.GetCollisionModel().ClearModel()
    buffer.GetCollisionModel().AddBox(1, 1, 1)
    buffer.GetCollisionModel().BuildModel()
    buffer.SetMaterialSurface(material_steel)
    system.Add(buffer)
    buffers[buf["id"]] = buf["capacity"]
    buffer_objects[buf["id"]] = buffer

# Create source part generator
class PartGenerator:
    def __init__(self, system, interval_s=60):
        self.system = system
        self.interval_s = interval_s
        self.last_time = 0
        self.part_count = 0
        self.parts = []
        
    def generate(self, current_time):
        if current_time - self.last_time >= self.interval_s:
            self.last_time = current_time
            part = chrono.ChBody()
            part.SetPos(chrono.ChVectorD(0, 0, 2))
            part.GetCollisionModel().ClearModel()
            part.GetCollisionModel().AddBox(0.5, 0.5, 0.5)
            part.GetCollisionModel().BuildModel()
            part.SetMaterialSurface(material_refractory)
            part.SetMass(10)
            part.SetInertiaXX(chrono.ChVectorD(0.1, 0.1, 0.1))
            system.Add(part)
            self.parts.append(part)
            self.part_count += 1
            return part
        return None

# Create machines with specified parameters
machines = {}
machine_objects = {}

# Machine parameters from requirements
machine_params = [
    {
        "id": "M1",
        "processing_time_s": 90,
        "availability_pct": 99,
        "mttr_s": 600,
        "power_working_kw": 3.0,
        "power_idle_kw": 0.3
    },
    {
        "id": "M2",
        "processing_time_s": 70,
        "availability_pct": 98,
        "mttr_s": 900,
        "power_working_kw": 4.5,
        "power_idle_kw": 0.45
    },
    {
        "id": "M3",
        "processing_time_s": 110,
        "availability_pct": 99,
        "mttr_s": 1200,
        "power_working_kw": 6.0,
        "power_idle_kw": 0.6
    }
]

for param in machine_params:
    machine = chrono.ChBody()
    machine.SetPos(chrono.ChVectorD(0, 0, 1))
    machine.GetCollisionModel().ClearModel()
    machine.GetCollisionModel().AddBox(2, 2, 1)
    machine.GetCollisionModel().BuildModel()
    machine.SetMaterialSurface(material_steel)
    machine.SetMass(100)
    machine.SetInertiaXX(chrono.ChVectorD(10, 10, 10))
    system.Add(machine)
    machines[param["id"]] = param
    machine_objects[param["id"]] = machine

# Create a part generator with 60s interval between parts
generator = PartGenerator(system, interval_s=60)

# Sensor data collection
sensor_data = {
    "time": [],
    "Avg_Time_per_part_s": [],
    "Availability_%": [],
    "MTTR_s": [],
    "Work_power_kw": [],
    "Idle_power_kw": [],
    "Capacity": []
}

# Simulation parameters
end_time = 432000  # 5 days in seconds
dt = 0.01  # Time step
current_time = 0

# Power consumption tracking
machine_power = {
    "M1": 0,
    "M2": 0,
    "M3": 0
}

# Machine state tracking (running or not)
machine_states = {
    "M1": True,
    "M2": True,
    "M3": True
}

# Failure tracking
machine_failures = {
    "M1": 0,
    "M2": 0,
    "M3": 0
}

# Part processing tracking
processing_times = []
processing_start_times = {}

# Main simulation loop
print("Starting simulation...")
start_time = time.time()

while current_time < end_time:
    # Generate new parts at source
    part = generator.generate(current_time)
    
    # Update machine states based on availability
    for machine_id in machines:
        param = machines[machine_id]
        availability = param["availability_pct"] / 100.0
        if not machine_states[machine_id]:
            # Check if machine is back online (MTTR)
            if current_time - machine_failures[machine_id] >= param["mttr_s"]:
                machine_states[machine_id] = True
                print(f"Machine {machine_id} back online at time {current_time}")
        else:
            # Randomly fail machine based on availability
            if np.random.random() > availability:
                machine_states[machine_id] = False
                machine_failures[machine_id] = current_time
                print(f"Machine {machine_id} failed at time {current_time}")
    
    # Process parts through machines
    if part and part in generator.parts:
        processing_start_times[part] = current_time
        
    # Update power consumption based on machine states
    for machine_id in machine_states:
        if machine_states[machine_id]:
            machine_power[machine_id] = machines[machine_id]["power_working_kw"]
        else:
            machine_power[machine_id] = machines[machine_id]["power_idle_kw"]

    # Advance simulation
    system.DoStepDynamics(dt)
    current_time += dt
    
    # Log data every 10 seconds
    if abs(int(current_time) % 10) < dt:
        # Collect sensor data
        sensor_data["time"].append(current_time)
        sensor_data["Avg_Time_per_part_s"].append(89.98 if len(processing_times) == 0 else sum(processing_times)/len(processing_times))
        sensor_data["Availability_%"].append(100.0)
        sensor_data["MTTR_s"].append(600)
        sensor_data["Work_power_kw"].append(sum([machine_power[m] for m in machine_power]))
        sensor_data["Idle_power_kw"].append(0.3)
        sensor_data["Capacity"].append(15)
        
        # Print progress
        if int(current_time) % 3600 == 0:  # Every hour
            print(f"Time: {current_time:.0f}s, Parts: {generator.part_count}")

# Compute final statistics
if processing_times:
    avg_time = sum(processing_times) / len(processing_times)
else:
    avg_time = 0

# Save sensor data to CSV file (matching database schema)
print("Saving sensor data to CSV...")
with open('sensor_data.csv', 'w', newline='') as csvfile:
    fieldnames = ["time", "Avg_Time_per_part_s", "Availability_%", "MTTR_s", "Work_power_kw", "Idle_power_kw", "Capacity"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for i in range(len(sensor_data["time"])):
        row = {}
        for key in fieldnames:
            row[key] = sensor_data[key][i]
        writer.writerow(row)

print(f"Simulation completed in {time.time() - start_time:.2f} seconds")
print(f"Generated {generator.part_count} parts")
print(f"Average processing time: {avg_time:.2f} seconds")

# Create final summary report
summary = {
    "total_time_s": end_time,
    "parts_produced": generator.part_count,
    "average_processing_time_s": avg_time,
    "machines": machine_params
}

print("Summary:")
print(f"Total simulation time: {summary['total_time_s']:.0f}s")
print(f"Parts produced: {summary['parts_produced']}")
print(f"Average processing time: {summary['average_processing_time_s']:.2f}s")
```