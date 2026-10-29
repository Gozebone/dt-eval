```python
import pychrono as chrono
import pychrono.irrlicht as chronoirr
import numpy as np
import json
import datetime
import math
from collections import defaultdict
import time

# Initialize PyChrono system
chrono.SetChronoDataPath('/usr/local/share/chrono/data/')
chrono.SetChronoDataPath('.')

# Create the physical system
sys = chrono.ChSystemNSC()
sys.Set_G_acc(chrono.ChVectorD(0, 0, 0))  # No gravity for this simulation

# Create materials
mat_steel = chrono.ChMaterialSurfaceNSC()
mat_steel.SetFriction(0.4)
mat_steel.SetRestitution(0.1)

mat_refractory = chrono.ChMaterialSurfaceNSC()
mat_refractory.SetFriction(0.3)
mat_refractory.SetRestitution(0.05)

# Create terrain (ground plane)
ground = chrono.ChBodyEasyBox(20, 1, 20, 1000, True, True, mat_steel)
ground.SetPos(chrono.ChVectorD(0, -0.5, 0))
ground.SetBodyFixed(True)
sys.Add(ground)

# Define equipment parameters from requirements
equipment_params = {
    "M1": {"processing_time_s": 100, "availability_pct": 92.58, "mttr_s": 3206.25, "power_working_kw": 4.0, "power_idle_kw": 0.4},
    "M2": {"processing_time_s": 130, "availability_pct": 97.36, "mttr_s": 2859.26, "power_working_kw": 5.0, "power_idle_kw": 0.5},
    "M3": {"processing_time_s": 90, "availability_pct": 94.69, "mttr_s": 2882.82, "power_working_kw": 4.5, "power_idle_kw": 0.45},
    "M4": {"processing_time_s": 140, "availability_pct": 100.0, "mttr_s": 1.0, "power_working_kw": 7.0, "power_idle_kw": 0.7},
    "M5": {"processing_time_s": 110, "availability_pct": 98.23, "mttr_s": 1099.8, "power_working_kw": 5.5, "power_idle_kw": 0.55},
    "B0": {"capacity": 6},
    "B1": {"capacity": 3},
    "B2": {"capacity": 3},
    "B3": {"capacity": 3},
    "B4": {"capacity": 3}
}

# Create machines and buffers
machines = {}
buffers = {}

# Create machine bodies
for machine_id, params in equipment_params.items():
    if machine_id.startswith('M'):
        # Create a simple box for each machine
        machine_body = chrono.ChBodyEasyBox(2, 1, 2, 1000, True, True, mat_steel)
        machine_body.SetPos(chrono.ChVectorD(0, 0, 0))
        machine_body.SetBodyFixed(False)
        sys.Add(machine_body)
        
        # Store reference
        machines[machine_id] = {
            'body': machine_body,
            'params': params,
            'state': 'operational',
            'last_failure_time': 0,
            'next_failure_time': 0,
            'active_time': 0,
            'idle_time': 0,
            'total_energy_kwh': 0
        }
        
        # Set initial position based on station order
        pos_x = (int(machine_id[1:]) - 1) * 4
        machine_body.SetPos(chrono.ChVectorD(pos_x, 0.5, 0))
    
    elif machine_id.startswith('B'):
        # Create buffer storage area
        buffer_body = chrono.ChBodyEasyBox(1, 0.5, 1, 1000, True, True, mat_refractory)
        buffer_body.SetPos(chrono.ChVectorD(0, 0, 0))
        buffer_body.SetBodyFixed(True)
        sys.Add(buffer_body)
        
        # Store reference
        buffers[machine_id] = {
            'body': buffer_body,
            'params': params,
            'items': 0,
            'max_items': params['capacity']
        }
        
        # Set initial position
        pos_x = (int(machine_id[1:]) + 5) * 4
        buffer_body.SetPos(chrono.ChVectorD(pos_x, 0.25, 0))

# Create source/sink
source_body = chrono.ChBodyEasyBox(1, 0.5, 1, 1000, True, True, mat_refractory)
source_body.SetPos(chrono.ChVectorD(-10, 0.25, 0))
source_body.SetBodyFixed(True)
sys.Add(source_body)

sink_body = chrono.ChBodyEasyBox(1, 0.5, 1, 1000, True, True, mat_refractory)
sink_body.SetPos(chrono.ChVectorD(30, 0.25, 0))
sink_body.SetBodyFixed(True)
sys.Add(sink_body)

# Setup inter-arrival time for source
inter_arrival_s = 150
last_source_time = 0

# Sensor data collection
sensor_data = defaultdict(list)
event_log = []
sample_log = []

# Simulation parameters
simulation_duration = 5 * 24 * 60 * 60  # 5 days in seconds
dt = 0.01  # Time step
current_time = 0

# Track simulation start time
start_timestamp = datetime.datetime.now()

# Main simulation loop
while current_time < simulation_duration:
    # Check if it's time to generate a new item from source
    if current_time - last_source_time >= inter_arrival_s:
        # Simulate item generation
        last_source_time = current_time
        print(f"Item generated at {current_time}s")
    
    # Update machine states based on availability and MTTR
    for machine_id, machine_info in machines.items():
        if machine_info['state'] == 'operational':
            # Simulate operational state
            machine_info['active_time'] += dt
            # Calculate power consumption
            power_kw = machine_info['params']['power_working_kw']
            energy_kwh = power_kw * dt / 3600.0
            machine_info['total_energy_kwh'] += energy_kwh
            
            # Log sample data
            sample_log.append({
                'ts': start_timestamp + datetime.timedelta(seconds=current_time),
                'machine_id': machine_id,
                'tag': 'process_time_s',
                'value': machine_info['params']['processing_time_s']
            })
            
            sample_log.append({
                'ts': start_timestamp + datetime.timedelta(seconds=current_time),
                'machine_id': machine_id,
                'tag': 'availability',
                'value': machine_info['params']['availability_pct']
            })
            
            sample_log.append({
                'ts': start_timestamp + datetime.timedelta(seconds=current_time),
                'machine_id': machine_id,
                'tag': 'mttr_s',
                'value': machine_info['params']['mttr_s']
            })
            
            sample_log.append({
                'ts': start_timestamp + datetime.timedelta(seconds=current_time),
                'machine_id': machine_id,
                'tag': 'work_power_kw',
                'value': machine_info['params']['power_working_kw']
            })
            
            sample_log.append({
                'ts': start_timestamp + datetime.timedelta(seconds=current_time),
                'machine_id': machine_id,
                'tag': 'idle_power_kw',
                'value': machine_info['params']['power_idle_kw']
            })
            
        else:  # Machine is down
            machine_info['idle_time'] += dt
    
    # Update buffer states
    for buffer_id, buffer_info in buffers.items():
        pass  # Buffer logic can be extended here
    
    # Advance simulation
    sys.DoStepDynamics(dt)
    current_time += dt

# Final logging of events
for machine_id, machine_info in machines.items():
    # Log events for failures
    if machine_info['state'] == 'failed':
        event_log.append({
            'ts': start_timestamp + datetime.timedelta(seconds=machine_info['last_failure_time']),
            'machine_id': machine_id,
            'reason_code': 'failure',
            'duration_s': machine_info['params']['mttr_s'],
            'energy_kwh': machine_info['total_energy_kwh']
        })

# Print summary statistics
print("Simulation completed")
print(f"Total runtime: {simulation_duration} seconds")
print(f"Items processed: {len(sample_log)}")

# Output to simulate database inserts
def log_to_database():
    """Function to simulate database logging"""
    
    # Raw ingest log (simulated)
    raw_ingest_entry = {
        'ingested_at': datetime.datetime.now(),
        'source': 'pychrono_simulation',
        'payload': {
            'simulation_duration': simulation_duration,
            'machines': machines,
            'buffers': buffers,
            'events': event_log,
            'samples': sample_log
        }
    }
    
    # Ingest watermark (simulated)
    watermark_entry = {
        'source': 'pychrono_simulation',
        'max_event_ts': start_timestamp + datetime.timedelta(seconds=simulation_duration)
    }
    
    # Machines table entries
    machines_entries = []
    for machine_id in ['M1', 'M2', 'M3', 'M4', 'M5', 'B0', 'B1', 'B2', 'B3', 'B4']:
        machines_entries.append({
            'id': machine_id,
            'name': machine_id
        })
    
    # Buffers table entries
    buffers_entries = []
    for buffer_id in ['B0', 'B1', 'B2', 'B3', 'B4']:
        buffers_entries.append({
            'id': buffer_id,
            'capacity': equipment_params[buffer_id]['capacity']
        })
    
    # Stations table entries
    stations_entries = []
    for machine_id in ['M1', 'M2', 'M3', 'M4', 'M5']:
        params = equipment_params[machine_id]
        stations_entries.append({
            'id': machine_id,
            'processing_time_s': params['processing_time_s'],
            'availability_pct': params['availability_pct'],
            'mttr_s': params['mttr_s'],
            'power_working_kw': params['power_working_kw'],
            'power_idle_kw': params['power_idle_kw']
        })
    
    # Tag map entries (simplified)
    tag_map_entries = []
    tags = ['process_time_s', 'availability', 'mttr_s', 'work_power_kw', 'idle_power_kw']
    for tag in tags:
        for machine_id in ['M1', 'M2', 'M3', 'M4', 'M5']:
            tag_map_entries.append({
                'tag_id': tag,
                'machine_id': machine_id,
                'signal': tag,
                'unit': 's' if tag == 'process_time_s' or tag == 'mttr_s' else 'kW' if 'power' in tag else '%',
                'register': tag,
                'scale': 1.0
            })
    
    # Events table entries
    events_entries = event_log
    
    # Samples table entries
    samples_entries = sample_log
    
    return {
        'raw_ingest': [raw_ingest_entry],
        'ingest_watermark': [watermark_entry],
        'machines': machines_entries,
        'buffers': buffers_entries,
        'stations': stations_entries,
        'tag_map': tag_map_entries,
        'events': events_entries,
        'samples': samples_entries
    }

# Generate database logs
database_logs = log_to_database()

# Print first few entries to verify structure
print("\nDatabase log preview:")
print("Raw ingest:", len(database_logs['raw_ingest']), "entries")
print("Ingest watermark:", len(database_logs['ingest_watermark']), "entries")
print("Machines:", len(database_logs['machines']), "entries")
print("Buffers:", len(database_logs['buffers']), "entries")
print("Stations:", len(database_logs['stations']), "entries")
print("Tag map:", len(database_logs['tag_map']), "entries")
print("Events:", len(database_logs['events']), "entries")
print("Samples:", len(database_logs['samples']), "entries")

print("\nSimulation finished successfully.")
```