```python
import pychrono as chrono
import pychrono.irrlicht as irr
import json
import math
import time
from datetime import datetime, timedelta
import random

# Define simulation parameters
SIMULATION_DURATION = 5 * 24 * 60 * 60  # 5 days in seconds
TIME_STEP = 0.01  # 10ms time step
GRAVITY = chrono.ChVectorD(0, -9.81, 0)  # Gravity vector

# Define machine parameters
MACHINE_PARAMS = {
    'M1': {'processing_time_s': 90, 'availability_pct': 99, 'mttr_s': 600, 'power_working_kw': 3.0, 'power_idle_kw': 0.3},
    'M2': {'processing_time_s': 70, 'availability_pct': 98, 'mttr_s': 900, 'power_working_kw': 4.5, 'power_idle_kw': 0.45},
    'M3': {'processing_time_s': 110, 'availability_pct': 99, 'mttr_s': 1200, 'power_working_kw': 6.0, 'power_idle_kw': 0.6}
}

# Define buffer parameters
BUFFER_PARAMS = {
    'B0': {'capacity': 15, 'before': 'source', 'after': 'M1'},
    'B1': {'capacity': 5, 'before': 'M1', 'after': 'M2'},
    'B2': {'capacity': 5, 'before': 'M2', 'after': 'M3'}
}

# Initialize the Chrono system
system = chrono.ChSystemNSC()
system.Set_G_acc(GRAVITY)

# Create a ground body
ground = chrono.ChBody()
ground.SetBodyFixed(True)
ground.SetPos(chrono.ChVectorD(0, -1, 0))
system.Add(ground)

# Create materials
steel_material = chrono.ChMaterialSurfaceNSC()
steel_material.SetFriction(0.5)
steel_material.SetRestitution(0.1)

# Create machine bodies (simplified as boxes)
machines = {}
for machine_id, params in MACHINE_PARAMS.items():
    # Create a machine body
    machine_body = chrono.ChBody()
    machine_body.SetPos(chrono.ChVectorD(0, 0, 0))
    machine_body.SetMass(100)
    machine_body.SetInertiaXX(chrono.ChVectorD(1, 1, 1))
    machine_body.GetCollisionModel().ClearModel()
    machine_body.GetCollisionModel().AddBox(0.5, 0.5, 0.5)
    machine_body.GetCollisionModel().BuildModel()
    machine_body.SetMaterialSurface(steel_material)
    system.Add(machine_body)
    machines[machine_id] = machine_body

# Create buffer bodies (simplified as boxes)
buffers = {}
for buffer_id, params in BUFFER_PARAMS.items():
    # Create a buffer body
    buffer_body = chrono.ChBody()
    buffer_body.SetPos(chrono.ChVectorD(0, 0, 0))
    buffer_body.SetMass(50)
    buffer_body.SetInertiaXX(chrono.ChVectorD(0.1, 0.1, 0.1))
    buffer_body.GetCollisionModel().ClearModel()
    buffer_body.GetCollisionModel().AddBox(0.3, 0.3, 0.3)
    buffer_body.GetCollisionModel().BuildModel()
    buffer_body.SetMaterialSurface(steel_material)
    system.Add(buffer_body)
    buffers[buffer_id] = buffer_body

# Create a source object that generates items
source_body = chrono.ChBody()
source_body.SetPos(chrono.ChVectorD(0, 0, 0))
source_body.SetBodyFixed(True)
system.Add(source_body)

# Define sensors for each machine
machine_sensors = {}
for machine_id, params in MACHINE_PARAMS.items():
    machine_sensors[machine_id] = {
        'processing_time_s': params['processing_time_s'],
        'availability_pct': params['availability_pct'],
        'mttr_s': params['mttr_s'],
        'power_working_kw': params['power_working_kw'],
        'power_idle_kw': params['power_idle_kw'],
        'processing_start_time': 0,
        'processing_end_time': 0,
        'is_processing': False,
        'last_failure_time': 0,
        'is_operational': True,
        'energy_consumed_kwh': 0,
        'total_processing_time_s': 0
    }

# Define buffer states
buffer_states = {}
for buffer_id, params in BUFFER_PARAMS.items():
    buffer_states[buffer_id] = {
        'items': [],
        'capacity': params['capacity']
    }

# Simulate production
start_time = time.time()
current_time = 0
item_counter = 0
inter_arrival_time_s = 60  # seconds
last_arrival_time = 0
event_log = []
sample_log = []

# Create sample log entry for initial state
sample_log.append({
    'ts': datetime.now(),
    'machine_id': 'M1',
    'tag': 'power',
    'value': MACHINE_PARAMS['M1']['power_idle_kw']
})

sample_log.append({
    'ts': datetime.now(),
    'machine_id': 'M2',
    'tag': 'power',
    'value': MACHINE_PARAMS['M2']['power_idle_kw']
})

sample_log.append({
    'ts': datetime.now(),
    'machine_id': 'M3',
    'tag': 'power',
    'value': MACHINE_PARAMS['M3']['power_idle_kw']
})

# Main simulation loop
while current_time < SIMULATION_DURATION:
    # Add new items based on arrival rate
    if current_time - last_arrival_time >= inter_arrival_time_s:
        item_counter += 1
        last_arrival_time = current_time
        event_log.append({
            'ts': datetime.now(),
            'machine_id': 'source',
            'reason_code': 'item_arrival',
            'duration_s': 0,
            'energy_kwh': 0
        })

    # Check and update machine states
    for machine_id, sensor_data in machine_sensors.items():
        # Determine if the machine is operational
        if not sensor_data['is_operational']:
            # Machine is in failure state
            if current_time - sensor_data['last_failure_time'] >= sensor_data['mttr_s']:
                # Machine is repaired
                sensor_data['is_operational'] = True
                event_log.append({
                    'ts': datetime.now(),
                    'machine_id': machine_id,
                    'reason_code': 'machine_repair',
                    'duration_s': sensor_data['mttr_s'],
                    'energy_kwh': 0
                })
        else:
            # Machine is operational, check for random failures
            failure_probability = 1 - (sensor_data['availability_pct'] / 100)
            if random.random() < failure_probability * TIME_STEP:
                # Machine fails
                sensor_data['is_operational'] = False
                sensor_data['last_failure_time'] = current_time
                event_log.append({
                    'ts': datetime.now(),
                    'machine_id': machine_id,
                    'reason_code': 'machine_failure',
                    'duration_s': 0,
                    'energy_kwh': 0
                })

        # Sample power consumption
        if sensor_data['is_processing']:
            power_val = sensor_data['power_working_kw']
        else:
            power_val = sensor_data['power_idle_kw']
        
        sample_log.append({
            'ts': datetime.now(),
            'machine_id': machine_id,
            'tag': 'power',
            'value': power_val
        })

    # Update buffer states
    for buffer_id, buffer_state in buffer_states.items():
        # Simulate items moving between buffers and machines
        pass  # Simplified for this example

    # Step the simulation
    system.DoStepDynamics(TIME_STEP)
    current_time += TIME_STEP

    # Log events and samples periodically
    if int(current_time) % 10 == 0:  # Log every 10 seconds
        for machine_id, sensor_data in machine_sensors.items():
            # Log processing time
            sample_log.append({
                'ts': datetime.now(),
                'machine_id': machine_id,
                'tag': 'processing_time',
                'value': sensor_data['processing_time_s']
            })
            
            # Log availability
            sample_log.append({
                'ts': datetime.now(),
                'machine_id': machine_id,
                'tag': 'availability',
                'value': sensor_data['availability_pct']
            })
            
            # Log MTTR
            sample_log.append({
                'ts': datetime.now(),
                'machine_id': machine_id,
                'tag': 'mttr',
                'value': sensor_data['mttr_s']
            })

# Final summary
print(f"Simulation completed after {current_time:.2f} seconds.")
print(f"Total items produced: {item_counter}")
print(f"Events logged: {len(event_log)}")
print(f"Samples logged: {len(sample_log)}")

# Export event log to JSON (simulating database insertion)
event_data = []
for event in event_log:
    event_data.append({
        'ts': event['ts'].isoformat(),
        'machine_id': event['machine_id'],
        'reason_code': event['reason_code'],
        'duration_s': event['duration_s'],
        'energy_kwh': event['energy_kwh']
    })

# Export sample log to JSON (simulating database insertion)
sample_data = []
for sample in sample_log:
    sample_data.append({
        'ts': sample['ts'].isoformat(),
        'machine_id': sample['machine_id'],
        'tag': sample['tag'],
        'value': sample['value']
    })

# Simulate database export
machines_data = [
    {
        'id': 'M1',
        'processing_time_s': 90,
        'availability_pct': 99,
        'mttr_s': 600,
        'power_working_kw': 3.0,
        'power_idle_kw': 0.3
    },
    {
        'id': 'M2',
        'processing_time_s': 70,
        'availability_pct': 98,
        'mttr_s': 900,
        'power_working_kw': 4.5,
        'power_idle_kw': 0.45
    },
    {
        'id': 'M3',
        'processing_time_s': 110,
        'availability_pct': 99,
        'mttr_s': 1200,
        'power_working_kw': 6.0,
        'power_idle_kw': 0.6
    }
]

buffers_data = [
    {
        'id': 'B0',
        'capacity': 15,
        'before': 'source',
        'after': 'M1'
    },
    {
        'id': 'B1',
        'capacity': 5,
        'before': 'M1',
        'after': 'M2'
    },
    {
        'id': 'B2',
        'capacity': 5,
        'before': 'M2',
        'after': 'M3'
    }
]

tag_map_data = [
    {'tag_id': 'time', 'machine_id': 'M1', 'signal': 'machine processing time', 'unit': 's', 'register': 'time', 'scale': 1},
    {'tag_id': 'time', 'machine_id': 'M2', 'signal': 'machine processing time', 'unit': 's', 'register': 'time', 'scale': 1},
    {'tag_id': 'time', 'machine_id': 'M3', 'signal': 'machine processing time', 'unit': 's', 'register': 'time', 'scale': 1},
    {'tag_id': 'availability', 'machine_id': 'M1', 'signal': 'machine availability', '%', 'register': 'availability', 'scale': 1},
    {'tag_id': 'availability', 'machine_id': 'M2', 'signal': 'machine availability', '%', 'register': 'availability', 'scale': 1},
    {'tag_id': 'availability', 'machine_id': 'M3', 'signal': 'machine availability', '%', 'register': 'availability', 'scale': 1},
    {'tag_id': 'mttr', 'machine_id': 'M1', 'signal': 'machine MTTR', 's', 'register': 'mttr', 'scale': 1},
    {'tag_id': 'mttr', 'machine_id': 'M2', 'signal': 'machine MTTR', 's', 'register': 'mttr', 'scale': 1},
    {'tag_id': 'mttr', 'machine_id': 'M3', 'signal': 'machine MTTR', 's', 'register': 'mttr', 'scale': 1},
    {'tag_id': 'power', 'machine_id': 'M1', 'signal': 'machine power', 'kW', 'register': 'power', 'scale': 1},
    {'tag_id': 'power', 'machine_id': 'M2', 'signal': 'machine power', 'kW', 'register': 'power', 'scale': 1},
    {'tag_id': 'power', 'machine_id': 'M3', 'signal': 'machine power', 'kW', 'register': 'power', 'scale': 1}
]

# Print out the data that would be inserted into the database
print("\n=== Machines Data ===")
print(json.dumps(machines_data, indent=2))

print("\n=== Buffers Data ===")
print(json.dumps(buffers_data, indent=2))

print("\n=== Tag Map Data ===")
print(json.dumps(tag_map_data, indent=2))

print("\n=== Events Data ===")
print(json.dumps(event_data, indent=2))

print("\n=== Samples Data