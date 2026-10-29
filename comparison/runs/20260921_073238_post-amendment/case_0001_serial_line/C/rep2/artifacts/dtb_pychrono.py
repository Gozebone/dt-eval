```python
import pychrono as chrono
import pychrono.core as core
import pychrono.irrlicht as irr
import pychrono.fsi as fsi
import pychrono.vehicle as vehicle
import math
import json
import time
from datetime import datetime, timezone
import numpy as np

# Simulation parameters
SIMULATION_TIME = 432000  # 5 days in seconds
DT = 0.01  # Time step
GRAVITY = chrono.ChVectorD(0, -9.81, 0)
GROUND_HEIGHT = 0

# Equipment data from requirements
machines_data = {
    'M1': {'processing_time_s': 150, 'availability': 0.98, 'mttr_s': 600, 'power_working_kw': 4.0, 'power_idle_kw': 0.4},
    'M2': {'processing_time_s': 120, 'availability': 0.97, 'mttr_s': 900, 'power_working_kw': 5.0, 'power_idle_kw': 0.5},
    'M3': {'processing_time_s': 180, 'availability': 0.95, 'mttr_s': 1200, 'power_working_kw': 6.0, 'power_idle_kw': 0.6},
    'M4': {'processing_time_s': 120, 'availability': 0.97, 'mttr_s': 900, 'power_working_kw': 5.0, 'power_idle_kw': 0.5},
    'M5': {'processing_time_s': 150, 'availability': 0.98, 'mttr_s': 600, 'power_working_kw': 4.0, 'power_idle_kw': 0.4}
}

buffers_data = {
    'B0': {'capacity': 20, 'before': 'source', 'after': 'M1'},
    'B1': {'capacity': 8, 'before': 'M1', 'after': 'M2'},
    'B2': {'capacity': 8, 'before': 'M2', 'after': 'M3'},
    'B3': {'capacity': 8, 'before': 'M3', 'after': 'M4'},
    'B4': {'capacity': 8, 'before': 'M4', 'after': 'M5'}
}

# Initialize PyChrono system
chrono.SetChronoDataPath('/usr/local/share/chrono/data/')
system = chrono.ChSystemNSC()
system.Set_G_acc(GRAVITY)

# Create materials
steel_mat = chrono.ChMaterialSurfaceNSC()
steel_mat.SetFriction(0.5)
steel_mat.SetRestitution(0.1)

# Create ground
ground = chrono.ChBodyEasyBox(20, 1, 20, 1000, True, True, steel_mat)
ground.SetPos(chrono.ChVectorD(0, GROUND_HEIGHT - 0.5, 0))
ground.SetBodyFixed(True)
system.Add(ground)

# Create source (part generator)
source_pos = chrono.ChVectorD(0, GROUND_HEIGHT + 1, 0)
source = chrono.ChBodyEasyBox(1, 1, 1, 100, True, True, steel_mat)
source.SetPos(source_pos)
source.SetBodyFixed(True)
system.Add(source)

# Create machines and buffers as bodies with appropriate properties
machines = {}
buffers = {}

# Create machine bodies
for machine_id, params in machines_data.items():
    machine_pos = chrono.ChVectorD(0, GROUND_HEIGHT + 1, 0)
    machine_body = chrono.ChBodyEasyBox(2, 1, 2, 1000, True, True, steel_mat)
    machine_body.SetPos(machine_pos)
    machine_body.SetBodyFixed(True)
    system.Add(machine_body)
    machines[machine_id] = {
        'body': machine_body,
        'params': params,
        'state': 'working',  # working, failed, idle
        'time_in_state': 0,
        'last_event_time': 0,
        'energy_idle_kwh': 0,
        'energy_working_kwh': 0,
        'parts_processed': 0,
        'processing_start': 0,
        'processing_duration': params['processing_time_s']
    }

# Create buffer bodies
for buffer_id, params in buffers_data.items():
    buffer_pos = chrono.ChVectorD(0, GROUND_HEIGHT + 1, 0)
    buffer_body = chrono.ChBodyEasyBox(1, 1, 1, 100, True, True, steel_mat)
    buffer_body.SetPos(buffer_pos)
    buffer_body.SetBodyFixed(True)
    system.Add(buffer_body)
    buffers[buffer_id] = {
        'body': buffer_body,
        'params': params,
        'part_count': 0
    }

# Create part representation
part_count = 0
part_radius = 0.1
parts = []

# Create simple part bodies that will move through the line
def create_part():
    global part_count
    part_pos = chrono.ChVectorD(0, GROUND_HEIGHT + 2, 0)
    part_body = chrono.ChBodyEasySphere(part_radius, 100, True, True, steel_mat)
    part_body.SetPos(part_pos)
    part_body.SetBodyFixed(False)
    system.Add(part_body)
    part_count += 1
    return part_body

# Part generator
source_timer = 0
inter_arrival_time = 130

# Simulation data collection
events_data = []
samples_data = []
ingest_watermarks = {}

# Main simulation loop
current_time = 0
print("Starting simulation for 5 days (432000 seconds)...")
print("Simulation time step:", DT)

while current_time < SIMULATION_TIME:
    # Part generation
    source_timer += DT
    if source_timer >= inter_arrival_time:
        part = create_part()
        parts.append(part)
        source_timer = 0
        
        # Log part generation event
        event = {
            'ts': datetime.now(timezone.utc),
            'machine_id': 'source',
            'reason_code': 'part_generated',
            'duration_s': 0,
            'energy_kwh': 0
        }
        events_data.append(event)

    # Process machines and buffers
    for machine_id, machine in machines.items():
        machine_params = machine['params']
        machine_body = machine['body']
        
        # State machine simulation
        if machine['state'] == 'working':
            machine['time_in_state'] += DT
            if machine['time_in_state'] >= machine['processing_duration']:
                # Machine processing complete
                machine['state'] = 'idle'
                machine['time_in_state'] = 0
                machine['parts_processed'] += 1
                
                # Log processing complete event
                event = {
                    'ts': datetime.now(timezone.utc),
                    'machine_id': machine_id,
                    'reason_code': 'processing_complete',
                    'duration_s': machine['processing_duration'],
                    'energy_kwh': machine['energy_working_kwh']
                }
                events_data.append(event)
                
                machine['energy_working_kwh'] = 0
                
        elif machine['state'] == 'idle':
            machine['time_in_state'] += DT
            # Log energy usage for idle state
            machine['energy_idle_kwh'] += machine_params['power_idle_kw'] * DT / 3600  # Convert to kWh
            
        elif machine['state'] == 'failed':
            machine['time_in_state'] += DT
            # Log failure event
            if machine['time_in_state'] >= machine_params['mttr_s']:
                machine['state'] = 'idle'
                machine['time_in_state'] = 0
                
                event = {
                    'ts': datetime.now(timezone.utc),
                    'machine_id': machine_id,
                    'reason_code': 'repair_complete',
                    'duration_s': machine_params['mttr_s'],
                    'energy_kwh': 0
                }
                events_data.append(event)

    # Buffer management (simplified)
    for buffer_id, buffer in buffers.items():
        buffer_body = buffer['body']
        buffer_params = buffer['params']
        
        # Check capacity
        if buffer['part_count'] > buffer_params['capacity']:
            # Handle overfilling (simplified: remove excess)
            buffer['part_count'] = buffer_params['capacity']

    # Step the simulation
    system.DoStepDynamics(DT)
    current_time += DT

    # Sample data every 10 seconds
    if current_time % 10 < DT:
        for machine_id, machine in machines.items():
            machine_params = machine['params']
            
            # Collect sensor data
            sample_data = {
                'ts': datetime.now(timezone.utc),
                'machine_id': machine_id,
                'tag': 'MachineName',
                'value': machine_id
            }
            samples_data.append(sample_data)
            
            sample_data = {
                'ts': datetime.now(timezone.utc),
                'machine_id': machine_id,
                'tag': 'Avg_Time_per_part_s',
                'value': machine_params['processing_time_s']
            }
            samples_data.append(sample_data)
            
            sample_data = {
                'ts': datetime.now(timezone.utc),
                'machine_id': machine_id,
                'tag': 'Availability_%',
                'value': machine_params['availability'] * 100
            }
            samples_data.append(sample_data)
            
            sample_data = {
                'ts': datetime.now(timezone.utc),
                'machine_id': machine_id,
                'tag': 'MTTR_s',
                'value': machine_params['mttr_s']
            }
            samples_data.append(sample_data)
            
            sample_data = {
                'ts': datetime.now(timezone.utc),
                'machine_id': machine_id,
                'tag': 'EnergyIdling',
                'value': machine['energy_idle_kwh']
            }
            samples_data.append(sample_data)
            
            sample_data = {
                'ts': datetime.now(timezone.utc),
                'machine_id': machine_id,
                'tag': 'EnergyWorking',
                'value': machine['energy_working_kwh']
            }
            samples_data.append(sample_data)

# Finalize simulation data
print("Simulation complete.")
print(f"Total parts processed: {part_count}")
print(f"Total simulation time: {current_time} seconds")

# Print critical parameter checks
print("\nCritical Parameter Checks:")
for machine_id, params in machines_data.items():
    if 'mttr_s' in params:
        mttr = params['mttr_s']
        threshold = 0
        if machine_id in ['M1', 'M2', 'M3', 'M4', 'M5']:
            threshold = 600 if machine_id in ['M1', 'M5'] else 900 if machine_id in ['M2', 'M4'] else 1200
        print(f"Machine {machine_id} MTTR: {mttr} seconds (threshold: {threshold})")

for buffer_id, params in buffers_data.items():
    if 'capacity' in params:
        capacity = params['capacity']
        threshold = 0
        if buffer_id in ['B0', 'B1', 'B2', 'B3', 'B4']:
            threshold = 20 if buffer_id == 'B0' else 8
        print(f"Buffer {buffer_id} capacity: {capacity} (threshold: {threshold})")

# Output data to JSON (simulating database insertions)
import os

# Create sample data for raw ingest table
raw_ingest_data = []
ingest_watermark_data = {}
tag_map_data = []

# Simulate raw ingest data
for event in events_data:
    raw_ingest_data.append({
        'ingested_at': event['ts'].isoformat(),
        'source': 'production_line',
        'payload': json.dumps({
            'event': event,
            'type': 'event'
        })
    })

for sample in samples_data:
    raw_ingest_data.append({
        'ingested_at': sample['ts'].isoformat(),
        'source': 'production_line',
        'payload': json.dumps({
            'sample': sample,
            'type': 'sample'
        })
    })

# Update ingest watermark
ingest_watermark_data = {
    'source': 'production_line',
    'max_event_ts': datetime.now(timezone.utc).isoformat()
}

# Create tag_map data
for machine_id, params in machines_data.items():
    sensors = ['MachineName', 'Avg_Time_per_part_s', 'Availability_%', 'MTTR_s', 'EnergyIdling', 'EnergyWorking']
    for sensor in sensors:
        tag_map_data.append({
            'tag_id': sensor,
            'machine_id': machine_id,
            'signal': sensor,
            'unit': 'string' if sensor == 'MachineName' else ('s' if sensor == 'Avg_Time_per_part_s' or sensor == 'MTTR_s' else ('%' if sensor == 'Availability_%' else 'kWh')),
            'register': sensor,
            'scale': 1
        })

# Create machines table data
machines_table_data = []
for machine_id, params in machines_data.items():
    machines_table_data.append({
        'id': machine_id,
        'type': 'machine'
    })

for buffer_id, params in buffers_data.items():
    machines_table_data.append({
        'id': buffer_id,
        'type': 'buffer'
    })

# Create stations table data
stations_table_data = []
for machine_id, params in machines_data.items():
    stations_table_data.append({
        'id': machine_id,
        'processing_time_s': params['processing_time_s'],
        'availability': params['availability'],
        'mttr_s': params['mttr_s'],
        'power_working_kw': params['power_working_kw'],
        'power_idle_kw': params['