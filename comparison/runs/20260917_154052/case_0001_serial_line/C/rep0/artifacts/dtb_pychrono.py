```python
import pychrono as chrono
import pychrono.fsi as fsi
import pychrono.irrlicht as irr
import numpy as np
import math
import datetime
import time
import csv

# Initialize PyChrono system
chrono.SetChronoDataPath('path/to/chronodata')  # Update path if needed
sys = chrono.ChSystemNSC()

# Set gravity
sys.SetGravitationalAcceleration(chrono.Vector3d(0, -9.81, 0))

# Create a ground body
ground = chrono.ChBody()
ground.SetFixed(True)
ground.SetIdentifier(-1)
ground.SetPos(chrono.Vector3d(0, -1, 0))
sys.Add(ground)

# Add a visualization asset to the ground
ground_asset = chrono.ChVisualAsset()
ground_asset.SetColor(chrono.ChColor(0.5, 0.5, 0.5))
ground.AddAsset(ground_asset)

# Define material properties
steel_mat = chrono.ChMaterialSurfaceNSC()
steel_mat.SetFriction(0.5)
steel_mat.SetRestitution(0.1)

refractory_mat = chrono.ChMaterialSurfaceNSC()
refractory_mat.SetFriction(0.3)
refractory_mat.SetRestitution(0.05)

# Define machine parameters from requirements
machine_params = {
    'M1': {'time_per_part': 120},  # seconds per part
    'M2': {'time_per_part': 150},
    'M3': {'time_per_part': 180},
    'M4': {'time_per_part': 200},
    'M5': {'time_per_part': 220}
}

buffer_params = {
    'B0': {'capacity': 10},
    'B1': {'capacity': 10},
    'B2': {'capacity': 10},
    'B3': {'capacity': 10},
    'B4': {'capacity': 10}
}

# Create machines (M1-M5)
machines = {}
for name, params in machine_params.items():
    # Create machine body
    machine_body = chrono.ChBody()
    machine_body.SetPos(chrono.Vector3d(0, 0, 0))
    machine_body.SetIdentifier(ord(name[1]) - ord('0'))  # Unique ID for each machine
    sys.Add(machine_body)
    
    # Add visual asset
    machine_asset = chrono.ChVisualAsset()
    machine_asset.SetColor(chrono.ChColor(0.8, 0.2, 0.2))  # Red for machines
    machine_body.AddAsset(machine_asset)
    
    # Store machine data
    machines[name] = {
        'body': machine_body,
        'params': params,
        'status': 'idle',  # idle, processing
        'last_processed': 0,
        'total_energy_consumption': 0,
        'processing_time': 0
    }

# Create buffers (B0-B4)
buffers = {}
for name, params in buffer_params.items():
    # Create buffer body
    buffer_body = chrono.ChBody()
    buffer_body.SetPos(chrono.Vector3d(0, 0, 0))
    buffer_body.SetIdentifier(ord(name[1]) - ord('0') + 100)  # Unique ID for buffers
    sys.Add(buffer_body)
    
    # Add visual asset
    buffer_asset = chrono.ChVisualAsset()
    buffer_asset.SetColor(chrono.ChColor(0.2, 0.8, 0.2))  # Green for buffers
    buffer_body.AddAsset(buffer_asset)
    
    # Store buffer data
    buffers[name] = {
        'body': buffer_body,
        'params': params,
        'current_parts': 0
    }

# Create conveyor belts between machines and buffers
conveyor_belts = []

# Connect M1 to B0
belt1 = {
    'from_machine': 'M1',
    'to_buffer': 'B0',
    'length': 1.0,
    'speed': 0.5
}
conveyor_belts.append(belt1)

# Connect B0 to M2
belt2 = {
    'from_buffer': 'B0',
    'to_machine': 'M2',
    'length': 1.0,
    'speed': 0.5
}
conveyor_belts.append(belt2)

# Continue connecting other machines and buffers...
belt3 = {
    'from_machine': 'M2',
    'to_buffer': 'B1',
    'length': 1.0,
    'speed': 0.5
}
conveyor_belts.append(belt3)

belt4 = {
    'from_buffer': 'B1',
    'to_machine': 'M3',
    'length': 1.0,
    'speed': 0.5
}
conveyor_belts.append(belt4)

belt5 = {
    'from_machine': 'M3',
    'to_buffer': 'B2',
    'length': 1.0,
    'speed': 0.5
}
conveyor_belts.append(belt5)

belt6 = {
    'from_buffer': 'B2',
    'to_machine': 'M4',
    'length': 1.0,
    'speed': 0.5
}
conveyor_belts.append(belt6)

belt7 = {
    'from_machine': 'M4',
    'to_buffer': 'B3',
    'length': 1.0,
    'speed': 0.5
}
conveyor_belts.append(belt7)

belt8 = {
    'from_buffer': 'B3',
    'to_machine': 'M5',
    'length': 1.0,
    'speed': 0.5
}
conveyor_belts.append(belt8)

belt9 = {
    'from_machine': 'M5',
    'to_buffer': 'B4',
    'length': 1.0,
    'speed': 0.5
}
conveyor_belts.append(belt9)

# Create parts to process (similar to batch input)
parts = []
part_counter = 0

# Sensor data collection lists
sensor_events = []  # Event logs for processed parts
state_intervals = []  # State interval logs for machines
energy_records = []  # Continuous energy consumption records

# Start simulation time
sim_start_time = time.time()

# Main simulation loop
simulation_duration = 432000  # 5 days in seconds
dt = 0.01  # Time step
step_count = 0

while True:
    current_time = time.time() - sim_start_time
    
    if current_time >= simulation_duration:
        break
    
    # Step the simulation
    sys.DoStepDynamics(dt)
    
    # Process events every 10 steps
    if step_count % 10 == 0:
        # Simulate part arrival
        if len(parts) < 100:  # Limit total parts to avoid memory issues
            part_id = part_counter
            part_counter += 1
            
            # Create part body
            part = chrono.ChBody()
            part.SetPos(chrono.Vector3d(0, 0, 0))
            part.SetIdentifier(part_id)
            
            # Add visual asset
            part_asset = chrono.ChVisualAsset()
            part_asset.SetColor(chrono.ChColor(0.2, 0.2, 0.8))  # Blue for parts
            part.AddAsset(part_asset)
            
            sys.Add(part)
            parts.append({'id': part_id, 'body': part, 'position': 'input_queue'})
        
        # Check machines for processing
        for machine_name, machine_data in machines.items():
            machine_body = machine_data['body']
            
            # Determine if machine is idle
            if machine_data['status'] == 'idle':
                # Try to find a part to process
                for part in parts:
                    if part['position'] == 'input_queue' and machine_name == 'M1':
                        # Move part to machine
                        part['position'] = machine_name
                        machine_data['status'] = 'processing'
                        machine_data['last_processed'] = current_time
                        
                        # Record event
                        event_entry = {
                            'event_type': 'part_processing_started',
                            'machine': machine_name,
                            'part_id': part['id'],
                            'timestamp': current_time
                        }
                        sensor_events.append(event_entry)
                        
                        break
            elif machine_data['status'] == 'processing':
                # Check if processing is complete
                elapsed_time = current_time - machine_data['last_processed']
                expected_time = machine_data['params']['time_per_part']
                
                if elapsed_time >= expected_time:
                    # Processing complete
                    machine_data['status'] = 'idle'
                    
                    # Find and remove part
                    part_to_remove = None
                    for part in parts:
                        if part['position'] == machine_name:
                            part_to_remove = part
                            break
                    
                    if part_to_remove:
                        # Remove part from system
                        sys.Remove(part_to_remove['body'])
                        parts.remove(part_to_remove)
                        
                        # Record completion event
                        event_entry = {
                            'event_type': 'part_processed',
                            'machine': machine_name,
                            'part_id': part_to_remove['id'],
                            'timestamp': current_time
                        }
                        sensor_events.append(event_entry)
                        
                        # Update energy consumption (approximate)
                        machine_data['total_energy_consumption'] += 10 * expected_time  # kWh
                        
                        # Move to next buffer or final output
                        next_buffer = ''
                        if machine_name == 'M1':
                            next_buffer = 'B0'
                        elif machine_name == 'M2':
                            next_buffer = 'B1'
                        elif machine_name == 'M3':
                            next_buffer = 'B2'
                        elif machine_name == 'M4':
                            next_buffer = 'B3'
                        elif machine_name == 'M5':
                            next_buffer = 'B4'
                        
                        # Move part to next buffer
                        if next_buffer:
                            for part in parts:
                                if part['position'] == machine_name:
                                    part['position'] = next_buffer
                                    break

    # Log state intervals
    if step_count % 50 == 0:  # Every 50 steps
        for machine_name, machine_data in machines.items():
            state_interval = {
                'machine': machine_name,
                'state': machine_data['status'],
                'timestamp': current_time,
                'duration': dt
            }
            state_intervals.append(state_interval)
    
    # Log continuous energy records
    if step_count % 10 == 0:  # Every 10 steps
        for machine_name, machine_data in machines.items():
            energy_record = {
                'machine': machine_name,
                'energy_kwh': machine_data['total_energy_consumption'],
                'timestamp': current_time
            }
            energy_records.append(energy_record)
    
    step_count += 1

# Write sensor data to CSV files (simulate database logging)
# Events log
with open('sensor_events.csv', 'w', newline='') as csvfile:
    fieldnames = ['event_type', 'machine', 'part_id', 'timestamp']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for row in sensor_events:
        writer.writerow(row)

# State intervals log
with open('state_intervals.csv', 'w', newline='') as csvfile:
    fieldnames = ['machine', 'state', 'timestamp', 'duration']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for row in state_intervals:
        writer.writerow(row)

# Energy records log
with open('energy_records.csv', 'w', newline='') as csvfile:
    fieldnames = ['machine', 'energy_kwh', 'timestamp']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for row in energy_records:
        writer.writerow(row)

print("Simulation completed.")
print(f"Total parts processed: {len(sensor_events)}")
print(f"Total simulation time: {simulation_duration} seconds")
print(f"Average energy consumption per machine: {sum([m['total_energy_consumption'] for m in machines.values()])/len(machines)} kWh")

# Cleanup
del sys
```