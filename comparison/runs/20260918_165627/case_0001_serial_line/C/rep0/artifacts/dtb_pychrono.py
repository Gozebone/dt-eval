```python
import pychrono as chrono
import pychrono.irrlicht as irr
import math
import numpy as np
import time
import csv
from datetime import datetime

# Initialize PyChrono system
chrono.SetChronoDataPath('path/to/chronodata')  # Update path as needed
sys = chrono.ChSystemNSC()
sys.SetGravitationalAcceleration(chrono.ChVectorD(0, -9.81, 0))

# Create materials
mat_steel = chrono.ChMaterialSurfaceNSC()
mat_steel.SetFriction(0.4)
mat_steel.SetRestitution(0.1)

mat_refractory = chrono.ChMaterialSurfaceNSC()
mat_refractory.SetFriction(0.3)
mat_refractory.SetRestitution(0.05)

# Create ground plane
ground = chrono.ChBodyEasyBox(20, 1, 20, 1000, True, True, mat_steel)
ground.SetPos(chrono.ChVectorD(0, -0.5, 0))
ground.SetFixed(True)
sys.Add(ground)

# Machine parameters
machine_length = 2.0
machine_width = 1.0
machine_height = 1.5

# Buffer parameters
buffer_length = 2.0
buffer_width = 1.0
buffer_height = 1.0

# Create machines M1-M5
machines = []
for i in range(5):
    machine = chrono.ChBodyEasyBox(machine_length, machine_height, machine_width, 1000, True, True, mat_steel)
    machine.SetPos(chrono.ChVectorD(i * 3.0, 0.5, 0))
    machine.SetFixed(False)
    sys.Add(machine)
    machines.append(machine)

# Create buffers B0-B4
buffers = []
for i in range(5):
    buffer = chrono.ChBodyEasyBox(buffer_length, buffer_height, buffer_width, 1000, True, True, mat_refractory)
    buffer.SetPos(chrono.ChVectorD(i * 3.0 + 1.5, 0.5, 0))
    buffer.SetFixed(False)
    sys.Add(buffer)
    buffers.append(buffer)

# Create part (product) to simulate production flow
part_mass = 10.0
part_radius = 0.1
part = chrono.ChBodyEasySphere(part_radius, part_mass, True, True, mat_steel)
part.SetPos(chrono.ChVectorD(-1.0, 1.0, 0))
sys.Add(part)

# Simulation parameters
simulation_duration = 432000  # seconds
time_step = 0.01  # seconds
current_time = 0.0

# Sensor data storage
sensor_data = []

# Define event logging function
def log_sensor_data(time, machine_states, buffer_levels, energy_consumption):
    entry = {
        'timestamp': time,
        'machine_states': machine_states,
        'buffer_levels': buffer_levels,
        'energy_consumption': energy_consumption
    }
    sensor_data.append(entry)

# Define machine processing times and MTTR
machine_processing_times = [30, 40, 35, 45, 50]  # seconds per part
machine_mttr = [10, 15, 12, 18, 20]  # seconds for repair
machine_fail_prob = [0.01, 0.015, 0.012, 0.018, 0.02]  # probability of failure per second

# Track machine states: 0=idle, 1=working, 2=failed
machine_states = [0] * 5
machine_failures = [False] * 5
machine_repair_times = [0.0] * 5
machine_processing_start_times = [0.0] * 5

# Buffer capacities
buffer_capacities = [20, 8, 8, 8, 8]
buffer_fill_levels = [0] * 5  # B0-B4

# Energy consumption tracking (Watts)
machine_energy_idle = 100  # Watts when idle
machine_energy_active = 500  # Watts when active
total_energy_consumption = 0.0

# Part arrival mechanism
part_arrival_interval = 130  # seconds
last_part_arrival = 0.0

# Main simulation loop
while current_time < simulation_duration:
    # Check if new part arrives
    if current_time - last_part_arrival >= part_arrival_interval:
        part.SetPos(chrono.ChVectorD(-1.0, 1.0, 0))  # Reset part position
        last_part_arrival = current_time
        # Update buffer level for B0
        buffer_fill_levels[0] += 1
        if buffer_fill_levels[0] > buffer_capacities[0]:
            buffer_fill_levels[0] = buffer_capacities[0]

    # Process machines
    for i in range(5):
        if machine_states[i] == 0:  # Idle
            if buffer_fill_levels[i] > 0:
                machine_states[i] = 1  # Start working
                machine_processing_start_times[i] = current_time
                buffer_fill_levels[i] -= 1  # Remove part from buffer
        elif machine_states[i] == 1:  # Working
            if current_time - machine_processing_start_times[i] >= machine_processing_times[i]:
                machine_states[i] = 0  # Finished processing
                # Move part to next station or finish
                if i < 4:
                    buffer_fill_levels[i+1] += 1
                    if buffer_fill_levels[i+1] > buffer_capacities[i+1]:
                        buffer_fill_levels[i+1] = buffer_capacities[i+1]
        elif machine_states[i] == 2:  # Failed
            if current_time - machine_repair_times[i] >= machine_mttr[i]:
                machine_states[i] = 0  # Repair completed
        else:
            # Randomly fail machines
            if not machine_failures[i] and np.random.rand() < machine_fail_prob[i]:
                machine_failures[i] = True
                machine_states[i] = 2  # Mark as failed
                machine_repair_times[i] = current_time

    # Calculate energy consumption
    energy_active = sum([1 if s == 1 else 0 for s in machine_states]) * machine_energy_active
    energy_idle = sum([1 if s == 0 else 0 for s in machine_states]) * machine_energy_idle
    total_energy_consumption += (energy_active + energy_idle) * time_step

    # Log sensor data every 10 seconds
    if int(current_time) % 10 == 0:
        log_sensor_data(
            current_time,
            machine_states.copy(),
            buffer_fill_levels.copy(),
            total_energy_consumption
        )

    # Step simulation
    sys.DoStepDynamics(time_step)
    current_time += time_step

# Export sensor data to CSV
with open('sensor_data.csv', 'w', newline='') as csvfile:
    fieldnames = ['timestamp', 'machine_states', 'buffer_levels', 'energy_consumption']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for entry in sensor_data:
        writer.writerow(entry)

print(f"Simulation completed. Total runtime: {simulation_duration} seconds.")
print(f"Total energy consumption: {total_energy_consumption:.2f} Joules")

# Print summary statistics
print("\nSummary Statistics:")
print(f"Average buffer fill levels: {[sum(levels)/len(sensor_data) for levels in zip(*[entry['buffer_levels'] for entry in sensor_data])] if sensor_data else []}")
print(f"Machine availability: {[sum([1 if state == 1 else 0 for state in entry['machine_states']]) / len(entry['machine_states']) for entry in sensor_data]}")
```