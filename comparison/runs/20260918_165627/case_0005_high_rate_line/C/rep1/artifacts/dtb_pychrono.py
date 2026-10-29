```python
import pychrono as chrono
import pychrono.irrlicht as irr
import pychrono.fsi as fsi
import numpy as np
import time
import math
import csv
import os

# Initialize PyChrono system
chrono.SetChronoDataPath(os.path.join(os.path.dirname(__file__), "chrono_data"))

# Create the physical system
sys = chrono.ChSystemNSC()

# Set gravity
sys.Set_G_acc(chrono.ChVectorD(0, -9.81, 0))

# Create materials
steel_mat = chrono.ChMaterialSurfaceNSC()
steel_mat.SetFriction(0.5)
steel_mat.SetRestitution(0.1)

# Create terrain
terrain = chrono.ChBody()
terrain.SetFixed(True)
terrain.SetBodyFixed(True)
terrain.SetCollide(True)
terrain.AddAsset(chrono.ChVisualShapeBox(20, 0.1, 20))
terrain.GetVisualShape(0).SetColor(chrono.ChColor(0.3, 0.3, 0.3))
sys.Add(terrain)

# Create input buffer B0
buffer_B0 = chrono.ChBody()
buffer_B0.SetPos(chrono.ChVectorD(0, 0, 0))
buffer_B0.SetFixed(True)
buffer_B0.SetCollide(True)
buffer_B0.AddAsset(chrono.ChVisualShapeBox(5, 2, 5))
buffer_B0.GetVisualShape(0).SetColor(chrono.ChColor(0.8, 0.8, 0.8))
sys.Add(buffer_B0)

# Create machines M1, M2, M3, M4
machine_positions = [
    chrono.ChVectorD(10, 0, 0),
    chrono.ChVectorD(20, 0, 0),
    chrono.ChVectorD(30, 0, 0),
    chrono.ChVectorD(40, 0, 0)
]

machines = []
for i, pos in enumerate(machine_positions):
    machine = chrono.ChBody()
    machine.SetPos(pos)
    machine.SetFixed(True)
    machine.SetCollide(True)
    machine.AddAsset(chrono.ChVisualShapeBox(3, 3, 3))
    machine.GetVisualShape(0).SetColor(chrono.ChColor(0.5, 0.5, 1.0))
    sys.Add(machine)
    machines.append(machine)

# Create buffers B1, B2, B3
buffer_positions = [
    chrono.ChVectorD(15, 0, 0),
    chrono.ChVectorD(25, 0, 0),
    chrono.ChVectorD(35, 0, 0)
]

buffers = []
for i, pos in enumerate(buffer_positions):
    buffer = chrono.ChBody()
    buffer.SetPos(pos)
    buffer.SetFixed(True)
    buffer.SetCollide(True)
    buffer.AddAsset(chrono.ChVisualShapeBox(3, 2, 3))
    buffer.GetVisualShape(0).SetColor(chrono.ChColor(0.5, 0.5, 0.5))
    sys.Add(buffer)
    buffers.append(buffer)

# Create parts
parts = []
part_counter = 0
part_interval = 45.0  # seconds
last_part_time = 0.0

# Create output file for logging
log_filename = "digital_twin_simulation.csv"
with open(log_filename, 'w', newline='') as csvfile:
    fieldnames = [
        'timestamp', 'part_id', 'machine_id', 'buffer_id', 'status', 
        'wip', 'throughput', 'energy_consumption', 'availability'
    ]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

# Simulation parameters
dt = 0.01
simulation_time = 0.0
end_time = 1000.0  # seconds

# For tracking WIP
wip_count = 0
throughput = 0
total_energy_consumption = 0.0
machine_states = [True] * 4  # True means available
machine_working_time = [0.0] * 4
machine_total_time = [0.0] * 4

def log_data(timestamp, part_id, machine_id, buffer_id, status, wip, throughput, energy, availability):
    with open(log_filename, 'a', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=[
            'timestamp', 'part_id', 'machine_id', 'buffer_id', 'status', 
            'wip', 'throughput', 'energy_consumption', 'availability'
        ])
        writer.writerow({
            'timestamp': timestamp,
            'part_id': part_id,
            'machine_id': machine_id,
            'buffer_id': buffer_id,
            'status': status,
            'wip': wip,
            'throughput': throughput,
            'energy_consumption': energy,
            'availability': availability
        })

# Main simulation loop
while simulation_time < end_time:
    # Add new parts at regular intervals
    if simulation_time - last_part_time >= part_interval:
        part = chrono.ChBody()
        part.SetPos(chrono.ChVectorD(0, 2, 0))
        part.SetFixed(False)
        part.SetCollide(True)
        part.AddAsset(chrono.ChVisualShapeBox(0.5, 0.5, 0.5))
        part.GetVisualShape(0).SetColor(chrono.ChColor(1.0, 0.0, 0.0))
        sys.Add(part)
        parts.append(part)
        part_counter += 1
        wip_count += 1
        last_part_time = simulation_time
        log_data(
            simulation_time, 
            part_counter, 
            -1, 
            0, 
            "entered_line", 
            wip_count, 
            throughput, 
            total_energy_consumption, 
            sum(machine_states)/len(machine_states)
        )

    # Advance the simulation
    sys.DoStepDynamics(dt)
    simulation_time += dt

    # Update machine states and energy consumption
    for i in range(len(machines)):
        machine_total_time[i] += dt
        if machine_states[i]:  # Machine is currently working
            machine_working_time[i] += dt
            total_energy_consumption += 1.0  # Arbitrary energy consumption value

    # Update WIP and throughput
    wip_count = len(parts)
    if simulation_time % 10.0 < dt:  # Log every 10 seconds
        throughput = len(parts) / simulation_time * 60 if simulation_time > 0 else 0
        log_data(
            simulation_time, 
            -1, 
            -1, 
            -1, 
            "state_update", 
            wip_count, 
            throughput, 
            total_energy_consumption, 
            sum(machine_states)/len(machine_states)
        )

    # Check part processing through machines
    for i, part in enumerate(parts):
        if part.GetPos().x > 45:  # Part has passed through all machines
            sys.RemoveBody(part)
            parts.pop(i)
            throughput += 1
            wip_count -= 1
            log_data(
                simulation_time, 
                i+1, 
                -1, 
                -1, 
                "completed", 
                wip_count, 
                throughput, 
                total_energy_consumption, 
                sum(machine_states)/len(machine_states)
            )
            break

# Calculate final availability
final_availability = []
for i in range(len(machine_states)):
    if machine_total_time[i] > 0:
        availability = machine_working_time[i] / machine_total_time[i]
        final_availability.append(availability)
    else:
        final_availability.append(0.0)

print("Simulation completed.")
print(f"Total throughput: {throughput} parts")
print(f"Final WIP: {wip_count} parts")
print(f"Total energy consumption: {total_energy_consumption} kWh")
print(f"Machine availability: {final_availability}")

# Cleanup
for part in parts:
    sys.RemoveBody(part)
```