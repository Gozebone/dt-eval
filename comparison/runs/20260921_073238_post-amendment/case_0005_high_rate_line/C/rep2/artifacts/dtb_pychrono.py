```python
import pychrono as chrono
import numpy as np
import math
import json
from datetime import datetime, timedelta
import time

# Initialize PyChrono system
chrono.Initialize()

# Create the physical system
system = chrono.ChSystemNSC()
system.Set_G_acc(chrono.ChVectorD(0, 0, 0))  # No gravity for this simulation

# Define materials
material_steel = chrono.ChMaterialSurfaceNSC()
material_steel.SetFriction(0.5)
material_steel.SetRestitution(0.1)

material_refractory = chrono.ChMaterialSurfaceNSC()
material_refractory.SetFriction(0.3)
material_refractory.SetRestitution(0.05)

# Machine parameters from requirements
machines_data = {
    'M1': {'processing_time_s': 60, 'availability': 0.995, 'mttr_s': 300, 'work_power_kw': 3.0, 'idle_power_kw': 0.3},
    'M2': {'processing_time_s': 80, 'availability': 0.99, 'mttr_s': 600, 'work_power_kw': 5.0, 'idle_power_kw': 0.5},
    'M3': {'processing_time_s': 70, 'availability': 0.99, 'mttr_s': 600, 'work_power_kw': 4.5, 'idle_power_kw': 0.45},
    'M4': {'processing_time_s': 75, 'availability': 0.995, 'mttr_s': 300, 'work_power_kw': 4.0, 'idle_power_kw': 0.4}
}

buffers_data = {
    'B0': {'capacity': 25, 'before': 'source', 'after': 'M1'},
    'B1': {'capacity': 10, 'before': 'M1', 'after': 'M2'},
    'B2': {'capacity': 10, 'before': 'M2', 'after': 'M3'},
    'B3': {'capacity': 10, 'before': 'M3', 'after': 'M4'}
}

# Create buffers as simple boxes with collision detection
buffers = {}
for buffer_id, data in buffers_data.items():
    # Create a box for the buffer
    buffer_body = chrono.ChBody()
    buffer_body.SetIdentifier(int(buffer_id.replace('B', '')))
    buffer_body.SetPos(chrono.ChVectorD(0, 0, 0))
    buffer_body.SetMass(100)
    buffer_body.SetInertiaXX(chrono.ChVectorD(1, 1, 1))
    
    # Create collision shape
    collision_shape = chrono.ChCollisionModel()
    collision_shape.AddBox(material_steel, 2, 2, 0.5)  # width, height, depth
    buffer_body.SetCollide(True)
    buffer_body.GetCollisionModel().SetFamily(1)
    buffer_body.GetCollisionModel().SetFamilyMaskNoCollisionWithFamily(1)
    
    # Add to system
    system.Add(buffer_body)
    buffers[buffer_id] = {
        'body': buffer_body,
        'capacity': data['capacity'],
        'items': []
    }

# Create machines
machines = {}
for machine_id, data in machines_data.items():
    # Create machine body
    machine_body = chrono.ChBody()
    machine_body.SetIdentifier(ord(machine_id[-1]))  # Unique identifier
    machine_body.SetPos(chrono.ChVectorD(0, 0, 0))
    machine_body.SetMass(1000)
    machine_body.SetInertiaXX(chrono.ChVectorD(100, 100, 100))
    
    # Create collision shape
    collision_shape = chrono.ChCollisionModel()
    collision_shape.AddBox(material_steel, 2, 2, 1)  # width, height, depth
    machine_body.SetCollide(True)
    machine_body.GetCollisionModel().SetFamily(2)
    machine_body.GetCollisionModel().SetFamilyMaskNoCollisionWithFamily(2)
    
    # Add to system
    system.Add(machine_body)
    machines[machine_id] = {
        'body': machine_body,
        'processing_time': data['processing_time_s'],
        'availability': data['availability'],
        'mttr': data['mttr_s'],
        'work_power_kw': data['work_power_kw'],
        'idle_power_kw': data['idle_power_kw'],
        'status': 'idle',  # idle, working, broken
        'last_change': 0,
        'start_processing': None,
        'total_energy_kwh': 0,
        'current_energy_kwh': 0
    }

# Source item generator
class ItemGenerator:
    def __init__(self, inter_arrival_time_s):
        self.inter_arrival_time = inter_arrival_time_s
        self.last_generation = 0
        self.item_count = 0
    
    def generate(self, current_time):
        if current_time - self.last_generation >= self.inter_arrival_time:
            self.item_count += 1
            self.last_generation = current_time
            return f"item_{self.item_count}"
        return None

generator = ItemGenerator(45)  # Inter-arrival time of 45 seconds

# Sensor class to collect data
class Sensor:
    def __init__(self, machine_id, signal, unit, register, scale=1.0):
        self.machine_id = machine_id
        self.signal = signal
        self.unit = unit
        self.register = register
        self.scale = scale
        self.data_log = []
        
    def log_value(self, timestamp, value):
        scaled_value = value * self.scale
        self.data_log.append({
            'ts': timestamp,
            'machine_id': self.machine_id,
            'tag': self.signal,
            'value': scaled_value
        })

# Create sensors for each machine
sensors = [
    Sensor('M1', 'temperature', 'C', 'temp1', 1.0),
    Sensor('M2', 'vibration', 'mm/s', 'vib1', 1.0),
    Sensor('M3', 'pressure', 'bar', 'pres1', 1.0),
    Sensor('M4', 'flow', 'L/min', 'flow1', 1.0)
]

# Simulation parameters
sim_duration = 432000  # 5 days in seconds
step_size = 0.1
current_time = 0

# Event log for storing events
events_log = []

# Sample log for storing samples
samples_log = []

# Main simulation loop
while current_time < sim_duration:
    # Generate new items
    item = generator.generate(current_time)
    if item:
        # Simulate item entering buffer B0
        buffer_b0 = buffers['B0']
        if len(buffer_b0['items']) < buffer_b0['capacity']:
            buffer_b0['items'].append(item)
            print(f"Item {item} entered buffer B0 at time {current_time}")
    
    # Process each machine in order
    for machine_id in ['M1', 'M2', 'M3', 'M4']:
        machine = machines[machine_id]
        
        # Update machine status based on availability
        if machine['status'] == 'broken':
            # Check if repair is done
            if current_time - machine['last_change'] >= machine['mttr']:
                machine['status'] = 'idle'
                machine['last_change'] = current_time
                print(f"Machine {machine_id} repaired at time {current_time}")
        elif machine['status'] == 'idle':
            # Check if there's an item in the previous buffer
            prev_buffer_id = None
            if machine_id == 'M1':
                prev_buffer_id = 'B0'
            elif machine_id == 'M2':
                prev_buffer_id = 'B1'
            elif machine_id == 'M3':
                prev_buffer_id = 'B2'
            elif machine_id == 'M4':
                prev_buffer_id = 'B3'
            
            if prev_buffer_id and len(buffers[prev_buffer_id]['items']) > 0:
                # Start processing
                item = buffers[prev_buffer_id]['items'].pop(0)
                machine['status'] = 'working'
                machine['start_processing'] = current_time
                machine['last_change'] = current_time
                print(f"Machine {machine_id} started processing item {item} at time {current_time}")
                
                # Log event
                events_log.append({
                    'ts': current_time,
                    'machine_id': machine_id,
                    'reason_code': 'start',
                    'duration_s': 0,
                    'energy_kwh': 0
                })
        elif machine['status'] == 'working':
            # Check if processing is complete
            if current_time - machine['start_processing'] >= machine['processing_time']:
                # Complete processing
                machine['status'] = 'idle'
                machine['last_change'] = current_time
                
                # Calculate energy consumption
                duration = machine['processing_time']
                energy_kwh = (machine['work_power_kw'] * duration) / 3600  # kWh
                machine['total_energy_kwh'] += energy_kwh
                machine['current_energy_kwh'] = energy_kwh
                
                # Log event
                events_log.append({
                    'ts': current_time,
                    'machine_id': machine_id,
                    'reason_code': 'complete',
                    'duration_s': duration,
                    'energy_kwh': energy_kwh
                })
                
                # Move item to next buffer if available
                next_buffer_id = None
                if machine_id == 'M1':
                    next_buffer_id = 'B1'
                elif machine_id == 'M2':
                    next_buffer_id = 'B2'
                elif machine_id == 'M3':
                    next_buffer_id = 'B3'
                elif machine_id == 'M4':
                    # End of line - item completed
                    pass
                
                if next_buffer_id:
                    if len(buffers[next_buffer_id]['items']) < buffers[next_buffer_id]['capacity']:
                        # Simulate item moving to next buffer
                        buffers[next_buffer_id]['items'].append(f"processed_item_{machine_id}")
                        print(f"Item moved to buffer {next_buffer_id} from machine {machine_id} at time {current_time}")
                
                # Simulate random failure based on availability
                if np.random.rand() > machine['availability']:
                    machine['status'] = 'broken'
                    machine['last_change'] = current_time
                    print(f"Machine {machine_id} failed at time {current_time}")
                    
                    # Log event
                    events_log.append({
                        'ts': current_time,
                        'machine_id': machine_id,
                        'reason_code': 'failure',
                        'duration_s': 0,
                        'energy_kwh': 0
                    })
    
    # Collect sensor data
    for sensor in sensors:
        if sensor.machine_id in machines:
            machine = machines[sensor.machine_id]
            # Simulate different values based on machine status
            if sensor.signal == 'temperature':
                value = 20 + (machine['status'] == 'working') * 50  # Base 20°C, working adds 50°C
            elif sensor.signal == 'vibration':
                value = 0.1 + (machine['status'] == 'working') * 0.5  # Base 0.1 mm/s, working adds 0.5 mm/s
            elif sensor.signal == 'pressure':
                value = 10 + (machine['status'] == 'working') * 100  # Base 10 bar, working adds 100 bar
            elif sensor.signal == 'flow':
                value = 100 + (machine['status'] == 'working') * 500  # Base 100 L/min, working adds 500 L/min
            
            sensor.log_value(current_time, value)
            samples_log.extend(sensor.data_log)
            sensor.data_log.clear()
    
    # Step the simulation
    system.DoStepDynamics(step_size)
    current_time += step_size

# Output logs to match database schema
print("\n=== Events Log ===")
for event in events_log:
    print(event)

print("\n=== Samples Log ===")
for sample in samples_log:
    print(sample)

# Export logs to JSON files for database ingestion
with open('events.json', 'w') as f:
    json.dump(events_log, f, indent=2)

with open('samples.json', 'w') as f:
    json.dump(samples_log, f, indent=2)

# Print summary statistics
print("\n=== Simulation Summary ===")
for machine_id, machine in machines.items():
    print(f"Machine {machine_id}:")
    print(f"  Total Energy Consumed: {machine['total_energy_kwh']:.2f} kWh")
    print(f"  Status: {machine['status']}")

print(f"\nTotal Items Generated: {generator.item_count}")
print(f"Simulation Duration: {sim_duration} seconds")
print("Simulation completed successfully.")
```