```python
import pychrono as chrono
import pychrono.irrlicht as irr
import math
import numpy as np
import json
import time
from datetime import datetime, timedelta

# Initialize PyChrono system
chrono.Initialize()

# Create a physical system
sys = chrono.ChSystemNSC()
sys.SetGravitationalAcceleration(chrono.ChVectorD(0, 0, 0))

# Create a visualization system
vis = irr.ChVisualSystemIrrlicht()
vis.SetWindowSize(1024, 768)
vis.SetWindowTitle('Production Line Digital Twin')
vis.Initialize()
vis.AddLogo()
vis.AddSkyBox()
vis.AddCamera(chrono.ChVectorD(0, 5, 10), chrono.ChVectorD(0, 0, 0))
vis.AddTypicalLights()

# Define materials
mat_steel = chrono.ChMaterialSurfaceNSC()
mat_steel.SetFriction(0.4)
mat_steel.SetRestitution(0.2)
sys.SetMaterialSurface(chrono.ChMaterialSurfaceNSC())

# Machine parameters
machine_params = [
    {
        "id": "M1",
        "process_time_s": 200,
        "availability": 0.97,
        "mttr_s": 900,
        "work_power_kw": 5.0,
        "idle_power_kw": 0.5
    },
    {
        "id": "M2",
        "process_time_s": 220,
        "availability": 0.97,
        "mttr_s": 1000,
        "work_power_kw": 5.5,
        "idle_power_kw": 0.55
    },
    {
        "id": "M3",
        "process_time_s": 240,
        "availability": 0.96,
        "mttr_s": 1200,
        "work_power_kw": 6.0,
        "idle_power_kw": 0.6
    },
    {
        "id": "M4",
        "process_time_s": 260,
        "availability": 0.96,
        "mttr_s": 1400,
        "work_power_kw": 7.0,
        "idle_power_kw": 0.7
    },
    {
        "id": "M5",
        "process_time_s": 230,
        "availability": 0.97,
        "mttr_s": 1100,
        "work_power_kw": 6.5,
        "idle_power_kw": 0.65
    },
    {
        "id": "M6",
        "process_time_s": 210,
        "availability": 0.97,
        "mttr_s": 1000,
        "work_power_kw": 6.0,
        "idle_power_kw": 0.6
    }
]

# Buffer parameters
buffer_params = [
    {"id": "B0", "capacity": 10},
    {"id": "B1", "capacity": 10},
    {"id": "B2", "capacity": 10},
    {"id": "B3", "capacity": 10},
    {"id": "B4", "capacity": 10},
    {"id": "B5", "capacity": 10}
]

# Create machines
machines = {}
for param in machine_params:
    # Create machine body
    machine_body = chrono.ChBody()
    machine_body.SetPos(chrono.ChVectorD(0, 0, 0))
    machine_body.SetRot(chrono.Q_from_AngAxis(0, chrono.ChVectorD(0, 0, 1)))
    machine_body.SetMass(1000)
    machine_body.SetInertiaXX(chrono.ChVectorD(100, 100, 100))
    sys.AddBody(machine_body)
    
    # Add collision shape
    collision_shape = chrono.ChCollisionModel()
    collision_shape.AddBox(1, 1, 1)
    machine_body.SetCollide(True)
    machine_body.SetCollisionModel(collision_shape)
    
    # Store machine data
    machines[param["id"]] = {
        "body": machine_body,
        "process_time": param["process_time_s"],
        "availability": param["availability"],
        "mttr": param["mttr_s"],
        "work_power": param["work_power_kw"],
        "idle_power": param["idle_power_kw"],
        "status": "available",
        "processing_time_remaining": 0,
        "last_updated": 0,
        "power_consumed": 0
    }

# Create buffers
buffers = {}
for param in buffer_params:
    buffer_body = chrono.ChBody()
    buffer_body.SetPos(chrono.ChVectorD(0, 0, 0))
    buffer_body.SetRot(chrono.Q_from_AngAxis(0, chrono.ChVectorD(0, 0, 1)))
    buffer_body.SetMass(100)
    buffer_body.SetInertiaXX(chrono.ChVectorD(10, 10, 10))
    sys.AddBody(buffer_body)
    
    # Add collision shape
    collision_shape = chrono.ChCollisionModel()
    collision_shape.AddBox(1, 1, 1)
    buffer_body.SetCollide(True)
    buffer_body.SetCollisionModel(collision_shape)
    
    # Store buffer data
    buffers[param["id"]] = {
        "body": buffer_body,
        "capacity": param["capacity"],
        "parts": 0,
        "last_updated": 0
    }

# Create source part generator
source_part = chrono.ChBody()
source_part.SetPos(chrono.ChVectorD(0, 0, 0))
source_part.SetRot(chrono.Q_from_AngAxis(0, chrono.ChVectorD(0, 0, 1)))
source_part.SetMass(10)
source_part.SetInertiaXX(chrono.ChVectorD(1, 1, 1))
sys.AddBody(source_part)
source_part.SetCollide(True)

# Add collision shape for source part
collision_shape = chrono.ChCollisionModel()
collision_shape.AddBox(0.5, 0.5, 0.5)
source_part.SetCollisionModel(collision_shape)

# Create part generation system
inter_arrival_time = 300
last_part_time = 0

# Simulation parameters
simulation_duration = 432000  # 5 days in seconds
time_step = 0.1
current_time = 0

# Data logging system
machine_logs = []
buffer_logs = []
event_logs = []

# Main simulation loop
print("Starting simulation...")
start_time = time.time()

while current_time < simulation_duration:
    # Generate new parts at source
    if current_time - last_part_time >= inter_arrival_time:
        # Create a new part body with some randomness
        part = chrono.ChBody()
        part.SetPos(chrono.ChVectorD(0, 0, 0))
        part.SetRot(chrono.Q_from_AngAxis(0, chrono.ChVectorD(0, 0, 1)))
        part.SetMass(5)
        part.SetInertiaXX(chrono.ChVectorD(0.5, 0.5, 0.5))
        sys.AddBody(part)
        part.SetCollide(True)
        
        # Add collision shape
        collision_shape = chrono.ChCollisionModel()
        collision_shape.AddBox(0.5, 0.5, 0.5)
        part.SetCollisionModel(collision_shape)
        
        # Reset the time for next part
        last_part_time = current_time
        
    # Update each machine
    for machine_id, machine in machines.items():
        # Check if machine is currently processing
        if machine["processing_time_remaining"] > 0:
            machine["processing_time_remaining"] -= time_step
            # Simulate power consumption during processing
            machine["power_consumed"] += machine["work_power"] * time_step / 3600.0
            # Check if processing is complete
            if machine["processing_time_remaining"] <= 0:
                # Mark machine as available
                machine["status"] = "available"
                # Log event
                event_logs.append({
                    "ts": datetime.fromtimestamp(current_time + start_time),
                    "machine_id": machine_id,
                    "reason_code": "processing_complete",
                    "duration_s": machine["process_time"],
                    "energy_kwh": machine["power_consumed"]
                })
                machine["power_consumed"] = 0
        else:
            # Check if machine is available and can process a part
            if machine["status"] == "available":
                # Simulate availability check
                if np.random.rand() < (1 - machine["availability"]):
                    # Machine failure
                    machine["status"] = "failed"
                    machine["processing_time_remaining"] = machine["mttr"]
                    # Log failure event
                    event_logs.append({
                        "ts": datetime.fromtimestamp(current_time + start_time),
                        "machine_id": machine_id,
                        "reason_code": "machine_failure",
                        "duration_s": machine["mttr"],
                        "energy_kwh": 0
                    })
                else:
                    # Machine available for processing
                    machine["status"] = "available"
        
        # Log machine data
        machine_logs.append({
            "ts": datetime.fromtimestamp(current_time + start_time),
            "machine_id": machine_id,
            "tag": "process_time_s",
            "value": machine["process_time"]
        })
        machine_logs.append({
            "ts": datetime.fromtimestamp(current_time + start_time),
            "machine_id": machine_id,
            "tag": "availability",
            "value": machine["availability"]
        })
        machine_logs.append({
            "ts": datetime.fromtimestamp(current_time + start_time),
            "machine_id": machine_id,
            "tag": "mttr_s",
            "value": machine["mttr"]
        })
        machine_logs.append({
            "ts": datetime.fromtimestamp(current_time + start_time),
            "machine_id": machine_id,
            "tag": "work_power_kw",
            "value": machine["work_power"]
        })
        machine_logs.append({
            "ts": datetime.fromtimestamp(current_time + start_time),
            "machine_id": machine_id,
            "tag": "idle_power_kw",
            "value": machine["idle_power"]
        })
    
    # Update buffers
    for buffer_id, buffer in buffers.items():
        # Log buffer data
        buffer_logs.append({
            "ts": datetime.fromtimestamp(current_time + start_time),
            "machine_id": buffer_id,
            "tag": "capacity",
            "value": buffer["capacity"]
        })
    
    # Advance simulation
    sys.DoStepDynamics(time_step)
    current_time += time_step
    
    # Update visualization
    if vis.Run():
        vis.BeginScene()
        vis.Render()
        vis.EndScene()
    else:
        break

# Save data logs to simulate database inserts
print("Saving data logs...")

# Simulate inserting into machines table
for param in machine_params:
    print(f"Machine {param['id']} inserted into machines table")

# Simulate inserting into buffers table
for param in buffer_params:
    print(f"Buffer {param['id']} inserted into buffers table")

# Simulate inserting into events table
for event in event_logs:
    print(f"Event {event['machine_id']} inserted into events table")

# Simulate inserting into samples table
for log in machine_logs:
    print(f"Sample for {log['machine_id']}.{log['tag']} inserted into samples table")
    
for log in buffer_logs:
    print(f"Sample for {log['machine_id']}.{log['tag']} inserted into samples table")

print("Simulation completed successfully.")
print(f"Total simulation time: {simulation_duration} seconds")
print(f"Elapsed real time: {time.time() - start_time:.2f} seconds")

# Cleanup
vis.GetSystem().Clear()
chrono.Finalize()
```