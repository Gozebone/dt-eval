import numpy as np
import pychrono as chrono
import pychrono.irrlicht as irr
import json
import time
import datetime
from collections import defaultdict

# Initialize the PyChrono system
chrono.SetChronoDataPath("../../../data/")
chrono.SetChronoDataPath("../../../data/")

# Create the simulation system
system = chrono.ChSystemNSC()
system.Set_G_acc(chrono.ChVectorD(0, 0, 0))  # No gravity for this system

# Create materials
steel_mat = chrono.ChMaterialSurfaceNSC()
steel_mat.SetFriction(0.5)
steel_mat.SetRestitution(0.1)

refractory_mat = chrono.ChMaterialSurfaceNSC()
refractory_mat.SetFriction(0.3)
refractory_mat.SetRestitution(0.05)

# Create terrain
terrain = chrono.ChBody()
terrain.SetBodyFixed(True)
terrain.SetCollide(True)
terrain.GetCollisionModel().ClearModel()
terrain.GetCollisionModel().AddBox(10, 0.5, 10)
terrain.GetVisualModel().AddBox(10, 0.5, 10)
terrain.GetVisualModel().SetTexture(chrono.GetChronoDataFile("textures/concrete.jpg"))
terrain.SetMaterialSurface(steel_mat)
system.Add(terrain)

# Create source (part generator)
class PartGenerator:
    def __init__(self, system, inter_arrival_time_s):
        self.system = system
        self.inter_arrival_time_s = inter_arrival_time_s
        self.last_spawn_time = 0
        self.part_count = 0

    def update(self, current_time):
        if current_time - self.last_spawn_time >= self.inter_arrival_time_s:
            self.spawn_part(current_time)
            self.last_spawn_time = current_time

    def spawn_part(self, time):
        part = chrono.ChBody()
        part.SetPos(chrono.ChVectorD(0, 1, 0))
        part.SetRot(chrono.Q_from_AngAxis(0, chrono.ChVectorD(0, 1, 0)))
        part.SetMass(10)
        part.SetInertiaXX(chrono.ChVectorD(0.1, 0.1, 0.1))
        part.SetCollide(True)
        
        part.GetCollisionModel().ClearModel()
        part.GetCollisionModel().AddBox(0.5, 0.5, 0.5)
        part.GetVisualModel().AddBox(0.5, 0.5, 0.5)
        part.GetVisualModel().SetTexture(chrono.GetChronoDataFile("textures/blue.png"))
        part.SetMaterialSurface(steel_mat)
        
        self.system.Add(part)
        self.part_count += 1

# Create a part generator with inter-arrival time of 130 seconds
generator = PartGenerator(system, 130)
source_body = chrono.ChBody()
source_body.SetBodyFixed(True)
system.Add(source_body)

# Create machines with their parameters
machines_data = [
    {"id": "M1", "processing_time_s": 150, "availability_pct": 99.45, "mttr_s": 793.67, "power_working_kw": 4.0, "power_idle_kw": 0.4},
    {"id": "M2", "processing_time_s": 120, "availability_pct": 96.86, "mttr_s": 1053.95, "power_working_kw": 5.0, "power_idle_kw": 0.5},
    {"id": "M3", "processing_time_s": 180, "availability_pct": 99.03, "mttr_s": 4200.65, "power_working_kw": 6.0, "power_idle_kw": 0.6},
    {"id": "M4", "processing_time_s": 120, "availability_pct": 97.39, "mttr_s": 1894.81, "power_working_kw": 5.0, "power_idle_kw": 0.5},
    {"id": "M5", "processing_time_s": 150, "availability_pct": 99.56, "mttr_s": 641.17, "power_working_kw": 4.0, "power_idle_kw": 0.4}
]

# Create buffers with capacities
buffers_data = [
    {"id": "B0", "capacity": 20},
    {"id": "B1", "capacity": 8},
    {"id": "B2", "capacity": 8},
    {"id": "B3", "capacity": 8},
    {"id": "B4", "capacity": 8}
]

# Create machines in the simulation
machines = {}
for m_data in machines_data:
    machine = chrono.ChBody()
    machine.SetPos(chrono.ChVectorD(0, 0.5, 0))
    machine.SetRot(chrono.Q_from_AngAxis(0, chrono.ChVectorD(0, 1, 0)))
    machine.SetMass(100)
    machine.SetInertiaXX(chrono.ChVectorD(10, 10, 10))
    machine.SetCollide(True)
    
    machine.GetCollisionModel().ClearModel()
    machine.GetCollisionModel().AddBox(1, 1, 1)
    machine.GetVisualModel().AddBox(1, 1, 1)
    machine.GetVisualModel().SetTexture(chrono.GetChronoDataFile("textures/gray.png"))
    machine.SetMaterialSurface(steel_mat)
    
    system.Add(machine)
    machines[m_data["id"]] = {
        "body": machine,
        "data": m_data,
        "is_working": True,
        "work_start_time": -1,
        "total_work_time": 0,
        "total_idle_time": 0,
        "power_state": "idle",
        "last_state_change": 0
    }

# Create buffers in the simulation
buffers = {}
for b_data in buffers_data:
    buffer_body = chrono.ChBody()
    buffer_body.SetPos(chrono.ChVectorD(0, 0.5, 0))
    buffer_body.SetRot(chrono.Q_from_AngAxis(0, chrono.ChVectorD(0, 1, 0)))
    buffer_body.SetMass(1)
    buffer_body.SetInertiaXX(chrono.ChVectorD(0.01, 0.01, 0.01))
    buffer_body.SetCollide(True)
    
    buffer_body.GetCollisionModel().ClearModel()
    buffer_body.GetCollisionModel().AddBox(1, 1, 1)
    buffer_body.GetVisualModel().AddBox(1, 1, 1)
    buffer_body.GetVisualModel().SetTexture(chrono.GetChronoDataFile("textures/green.png"))
    buffer_body.SetMaterialSurface(refractory_mat)
    
    system.Add(buffer_body)
    buffers[b_data["id"]] = {
        "body": buffer_body,
        "capacity": b_data["capacity"],
        "parts": 0
    }

# Create sink (destination)
sink_body = chrono.ChBody()
sink_body.SetPos(chrono.ChVectorD(0, 0.5, 0))
sink_body.SetRot(chrono.Q_from_AngAxis(0, chrono.ChVectorD(0, 1, 0)))
sink_body.SetMass(1)
sink_body.SetInertiaXX(chrono.ChVectorD(0.01, 0.01, 0.01))
sink_body.SetCollide(True)

sink_body.GetCollisionModel().ClearModel()
sink_body.GetCollisionModel().AddBox(1, 1, 1)
sink_body.GetVisualModel().AddBox(1, 1, 1)
sink_body.GetVisualModel().SetTexture(chrono.GetChronoDataFile("textures/red.png"))
sink_body.SetMaterialSurface(steel_mat)
system.Add(sink_body)

# Define sensor data structures
sensor_data = {
    "Avg_Time_per_part_s": defaultdict(list),
    "Availability_%": defaultdict(list),
    "MTTR_s": defaultdict(list),
    "EnergyIdling": defaultdict(list),
    "EnergyWorking": defaultdict(list)
}

# Define machine states
machine_states = defaultdict(lambda: {
    "is_working": True,
    "work_start_time": -1,
    "total_work_time": 0,
    "total_idle_time": 0,
    "power_state": "idle",
    "last_state_change": 0
})

# Simulation parameters
total_time = 432000  # seconds
dt = 0.01  # timestep
current_time = 0
last_log_time = 0
log_interval = 10  # seconds

# Main simulation loop
print("Starting simulation...")
start_time = time.time()

while current_time < total_time:
    # Update the part generator
    generator.update(current_time)
    
    # Advance the simulation
    system.DoStepDynamics(dt)
    current_time += dt
    
    # Log data every log_interval seconds
    if current_time - last_log_time >= log_interval:
        # Log machine states and sensor data
        for machine_id, machine_info in machines.items():
            # Update states and log data
            current_state = machine_info["is_working"]
            if current_state != machine_info["is_working"]:
                machine_info["is_working"] = current_state
                machine_info["last_state_change"] = current_time
                
            # Calculate availability
            if machine_info["is_working"]:
                machine_info["total_work_time"] += log_interval
                machine_info["power_state"] = "working"
            else:
                machine_info["total_idle_time"] += log_interval
                machine_info["power_state"] = "idle"
            
            # Calculate availability percentage
            total_time = machine_info["total_work_time"] + machine_info["total_idle_time"]
            if total_time > 0:
                availability = (machine_info["total_work_time"] / total_time) * 100
            else:
                availability = 100.0
            
            # Log sensor data
            sensor_data["Availability_%"][machine_id].append({
                "timestamp": current_time,
                "value": availability
            })
            
            # Log energy data
            if machine_info["power_state"] == "idle":
                sensor_data["EnergyIdling"][machine_id].append({
                    "timestamp": current_time,
                    "value": machine_info["data"]["power_idle_kw"]
                })
                sensor_data["EnergyWorking"][machine_id].append({
                    "timestamp": current_time,
                    "value": 0.0
                })
            else:
                sensor_data["EnergyIdling"][machine_id].append({
                    "timestamp": current_time,
                    "value": 0.0
                })
                sensor_data["EnergyWorking"][machine_id].append({
                    "timestamp": current_time,
                    "value": machine_info["data"]["power_working_kw"]
                })
            
            # Log processing time
            sensor_data["Avg_Time_per_part_s"][machine_id].append({
                "timestamp": current_time,
                "value": machine_info["data"]["processing_time_s"]
            })
            
            # Log MTTR
            sensor_data["MTTR_s"][machine_id].append({
                "timestamp": current_time,
                "value": machine_info["data"]["mttr_s"]
            })
        
        # Log data to output file
        log_timestamp = datetime.datetime.utcnow()
        for machine_id in machines.keys():
            # Create a JSON-like output structure matching the database schema
            raw_data = {
                "ingested_at": log_timestamp.isoformat() + "Z",
                "source": "digital_twin_simulation",
                "payload": {
                    "machine_id": machine_id,
                    "samples": {
                        "Avg_Time_per_part_s": sensor_data["Avg_Time_per_part_s"][machine_id],
                        "Availability_%": sensor_data["Availability_%"][machine_id],
                        "MTTR_s": sensor_data["MTTR_s"][machine_id],
                        "EnergyIdling": sensor_data["EnergyIdling"][machine_id],
                        "EnergyWorking": sensor_data["EnergyWorking"][machine_id]
                    }
                }
            }
            
            # Print to stdout for debugging/monitoring
            print(json.dumps(raw_data, indent=2))
            
        last_log_time = current_time

# Print simulation results
end_time = time.time()
print(f"Simulation completed in {end_time - start_time:.2f} seconds")
print(f"Total parts generated: {generator.part_count}")

# Final log for all machines
if last_log_time < total_time:
    for machine_id, machine_info in machines.items():
        # Log final availability
        total_time = machine_info["total_work_time"] + machine_info["total_idle_time"]
        if total_time > 0:
            availability = (machine_info["total_work_time"] / total_time) * 100
        else:
            availability = 100.0
        
        sensor_data["Availability_%"][machine_id].append({
            "timestamp": total_time,
            "value": availability
        })

print("Simulation data logged successfully.")
print("Simulation complete.")