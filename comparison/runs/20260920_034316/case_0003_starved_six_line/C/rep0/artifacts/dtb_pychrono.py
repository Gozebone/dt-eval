```python
import pychrono as chrono
import pychrono.irrlicht as irr
import pychrono.fsi as fsi
import math
import time
import json
from datetime import datetime, timedelta
import numpy as np

# Initialize PyChrono system
chrono.SetChronoDataPath("path/to/chrono/data")  # Replace with actual path to Chrono data files
system = chrono.ChSystemNSC()
system.Set_G_acc(chrono.ChVectorD(0, -9.81, 0))  # Set gravity

# Set simulation parameters
simulation_time = 432000  # 5 days in seconds
time_step = 0.01  # Time step for simulation
current_time = 0.0

# Define machine properties from JSON
machines_data = {
    "M1": {"processing_time_s": 200, "availability": 0.97, "mttr_s": 900, "work_power_kw": 5.0, "idle_power_kw": 0.5},
    "M2": {"processing_time_s": 220, "availability": 0.97, "mttr_s": 1000, "work_power_kw": 5.5, "idle_power_kw": 0.55},
    "M3": {"processing_time_s": 240, "availability": 0.96, "mttr_s": 1200, "work_power_kw": 6.0, "idle_power_kw": 0.6},
    "M4": {"processing_time_s": 260, "availability": 0.96, "mttr_s": 1400, "work_power_kw": 7.0, "idle_power_kw": 0.7},
    "M5": {"processing_time_s": 230, "availability": 0.97, "mttr_s": 1100, "work_power_kw": 6.5, "idle_power_kw": 0.65},
    "M6": {"processing_time_s": 210, "availability": 0.97, "mttr_s": 1000, "work_power_kw": 6.0, "idle_power_kw": 0.6}
}

buffers_data = {
    "B0": {"capacity": 10},
    "B1": {"capacity": 10},
    "B2": {"capacity": 10},
    "B3": {"capacity": 10},
    "B4": {"capacity": 10},
    "B5": {"capacity": 10}
}

# Create material properties
steel_material = chrono.ChMaterialSurfaceNSC()
steel_material.SetFriction(0.4)
steel_material.SetRestitution(0.1)

refractory_material = chrono.ChMaterialSurfaceNSC()
refractory_material.SetFriction(0.6)
refractory_material.SetRestitution(0.05)

# Create machine bodies
machines = {}
for machine_id, params in machines_data.items():
    body = chrono.ChBody()
    body.SetPos(chrono.ChVectorD(0, 0, 0))
    body.SetRot(chrono.QUNIT)
    body.SetMass(1000)
    body.SetInertiaXX(chrono.ChVectorD(100, 100, 100))
    body.GetVisualModel().SetBodyColor(chrono.ChColor(0, 0.5, 1))
    body.SetMaterialSurface(steel_material)
    system.Add(body)
    machines[machine_id] = {
        "body": body,
        "processing_time_s": params["processing_time_s"],
        "availability": params["availability"],
        "mttr_s": params["mttr_s"],
        "work_power_kw": params["work_power_kw"],
        "idle_power_kw": params["idle_power_kw"],
        "is_operational": True,
        "last_failure_time": 0.0,
        "total_operational_time": 0.0,
        "total_failure_time": 0.0,
        "processing_start_time": 0.0,
        "is_processing": False
    }

# Create buffer bodies
buffers = {}
for buffer_id, params in buffers_data.items():
    body = chrono.ChBody()
    body.SetPos(chrono.ChVectorD(0, 0, 0))
    body.SetRot(chrono.QUNIT)
    body.SetMass(500)
    body.SetInertiaXX(chrono.ChVectorD(50, 50, 50))
    body.GetVisualModel().SetBodyColor(chrono.ChColor(0.5, 0.5, 0.5))
    body.SetMaterialSurface(refractory_material)
    system.Add(body)
    buffers[buffer_id] = {
        "body": body,
        "capacity": params["capacity"],
        "current_items": 0
    }

# Create a source object for generating parts
source = chrono.ChBody()
source.SetPos(chrono.ChVectorD(0, 0, 0))
source.SetRot(chrono.QUNIT)
source.SetMass(100)
source.SetInertiaXX(chrono.ChVectorD(10, 10, 10))
source.GetVisualModel().SetBodyColor(chrono.ChColor(1, 0, 0))
source.SetMaterialSurface(steel_material)
system.Add(source)

# Create a simple conveyor belt system using constraints
# This is a simplified representation - actual implementation would be more complex
# Create a simple constraint to represent the conveyor
conveyor_constraint = chrono.ChLinkLockRevolute()
conveyor_constraint.Initialize(source, machines["M1"]["body"], chrono.ChVectorD(0, 0, 0))
system.Add(conveyor_constraint)

# Create sensors
sensors = {}
sensor_tags = ["processing_time_s", "availability", "mttr_s", "work_power_kw", "idle_power_kw", "buffer_capacity"]

# Create tag map with default values
tag_map = {
    "processing_time_s": {"machine_id": "M1", "signal": "processing_time_s", "unit": "s", "register": "processing_time_s", "scale": 1.0},
    "availability": {"machine_id": "M1", "signal": "availability", "unit": "unitless", "register": "availability", "scale": 1.0},
    "mttr_s": {"machine_id": "M1", "signal": "mttr_s", "unit": "s", "register": "mttr_s", "scale": 1.0},
    "work_power_kw": {"machine_id": "M1", "signal": "work_power_kw", "unit": "kW", "register": "work_power_kw", "scale": 1.0},
    "idle_power_kw": {"machine_id": "M1", "signal": "idle_power_kw", "unit": "kW", "register": "idle_power_kw", "scale": 1.0},
    "buffer_capacity": {"machine_id": "B0", "signal": "buffer_capacity", "unit": "unitless", "register": "buffer_capacity", "scale": 1.0}
}

# Initialize data structures to match database schema
machines_db = []
for machine_id, params in machines_data.items():
    machines_db.append({
        "id": machine_id,
        "processing_time_s": params["processing_time_s"],
        "availability": params["availability"],
        "mttr_s": params["mttr_s"],
        "work_power_kw": params["work_power_kw"],
        "idle_power_kw": params["idle_power_kw"]
    })

buffers_db = []
for buffer_id, params in buffers_data.items():
    buffers_db.append({
        "id": buffer_id,
        "capacity": params["capacity"]
    })

tag_map_db = []
for tag, mapping in tag_map.items():
    tag_map_db.append({
        "tag_id": tag,
        "machine_id": mapping["machine_id"],
        "signal": mapping["signal"],
        "unit": mapping["unit"],
        "register": mapping["register"],
        "scale": mapping["scale"]
    })

# Create event and sample data structures
events = []
samples = []

# Create simulation loop
start_time = time.time()
print("Starting simulation...")

# Main simulation loop
while current_time < simulation_time:
    # Step the simulation
    system.DoStepDynamics(time_step)
    
    # Update machine states (simplified logic)
    for machine_id, machine in machines.items():
        # Determine if machine is operational based on availability
        if not machine["is_operational"]:
            # Check if machine is ready to recover from failure
            if current_time - machine["last_failure_time"] >= machine["mttr_s"]:
                machine["is_operational"] = True
                machine["total_failure_time"] += machine["mttr_s"]
                # Record the recovery event
                events.append({
                    "ts": datetime.now() + timedelta(seconds=current_time),
                    "machine_id": machine_id,
                    "reason_code": "RECOVERY",
                    "duration_s": machine["mttr_s"],
                    "energy_kwh": 0.0
                })
        else:
            # Simulate processing of a part
            if not machine["is_processing"]:
                # Randomly determine if machine starts processing (based on availability)
                if np.random.rand() < machine["availability"]:
                    machine["is_processing"] = True
                    machine["processing_start_time"] = current_time
                    # Record processing start event
                    events.append({
                        "ts": datetime.now() + timedelta(seconds=current_time),
                        "machine_id": machine_id,
                        "reason_code": "PROCESS_START",
                        "duration_s": machine["processing_time_s"],
                        "energy_kwh": 0.0
                    })
                else:
                    # Simulate machine failure
                    machine["is_operational"] = False
                    machine["last_failure_time"] = current_time
                    machine["total_operational_time"] += time_step
                    # Record failure event
                    events.append({
                        "ts": datetime.now() + timedelta(seconds=current_time),
                        "machine_id": machine_id,
                        "reason_code": "FAILURE",
                        "duration_s": time_step,
                        "energy_kwh": 0.0
                    })
            else:
                # Check if processing is complete
                if current_time - machine["processing_start_time"] >= machine["processing_time_s"]:
                    machine["is_processing"] = False
                    machine["total_operational_time"] += machine["processing_time_s"]
                    # Record processing end event
                    events.append({
                        "ts": datetime.now() + timedelta(seconds=current_time),
                        "machine_id": machine_id,
                        "reason_code": "PROCESS_COMPLETE",
                        "duration_s": machine["processing_time_s"],
                        "energy_kwh": 0.0
                    })
    
    # Collect sensor data
    for machine_id, machine in machines.items():
        samples.append({
            "ts": datetime.now() + timedelta(seconds=current_time),
            "machine_id": machine_id,
            "tag": "processing_time_s",
            "value": machine["processing_time_s"]
        })
        samples.append({
            "ts": datetime.now() + timedelta(seconds=current_time),
            "machine_id": machine_id,
            "tag": "availability",
            "value": machine["availability"]
        })
        samples.append({
            "ts": datetime.now() + timedelta(seconds=current_time),
            "machine_id": machine_id,
            "tag": "mttr_s",
            "value": machine["mttr_s"]
        })
        samples.append({
            "ts": datetime.now() + timedelta(seconds=current_time),
            "machine_id": machine_id,
            "tag": "work_power_kw",
            "value": machine["work_power_kw"]
        })
        samples.append({
            "ts": datetime.now() + timedelta(seconds=current_time),
            "machine_id": machine_id,
            "tag": "idle_power_kw",
            "value": machine["idle_power_kw"]
        })
    
    # Record buffer capacities
    for buffer_id, buffer in buffers.items():
        samples.append({
            "ts": datetime.now() + timedelta(seconds=current_time),
            "machine_id": buffer_id,
            "tag": "buffer_capacity",
            "value": buffer["capacity"]
        })
    
    # Increment time
    current_time += time_step

# End simulation
end_time = time.time()

# Print summary
print(f"Simulation completed in {end_time - start_time:.2f} seconds")
print(f"Total simulated time: {current_time:.2f} seconds")
print(f"Number of events recorded: {len(events)}")
print(f"Number of samples recorded: {len(samples)}")

# Print some sample data that matches database schema
print("\nSample Machines Data:")
for machine in machines_db[:2]:  # Show first two machines
    print(f"ID: {machine['id']}, Processing Time: {machine['processing_time_s']}s, Availability: {machine['availability']}")

print("\nSample Buffers Data:")
for buffer in buffers_db[:2]:  # Show first two buffers
    print(f"ID: {buffer['id']}, Capacity: {buffer['capacity']}")

print("\nSample Events Data:")
for event in events[:5]:  # Show first 5 events
    print(f"Time: {event['ts']}, Machine: {event['machine_id']}, Reason: {event['reason_code']}")

print("\nSample Samples Data:")
for sample in samples[:5]:  # Show first 5 samples
    print(f"Time: {sample['ts']}, Machine: {sample['machine_id']}, Tag: {sample['tag']}, Value: {sample['value']}")
```