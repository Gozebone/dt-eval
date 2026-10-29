```python
import pychrono as chrono
import pychrono.irrlicht as irr
import pychrono.fea as fea
import numpy as np
import json
import time
from datetime import datetime, timedelta
import math

# Set the path to the Chrono data directory
chrono.SetChronoDataPath('path/to/chrono/data')

# Initialize the Chrono system
system = chrono.ChSystemNSC()
system.Set_G_acc(chrono.ChVectorD(0, 0, 0))  # No gravity

# Define simulation parameters
sim_duration = 432000.0  # 5 days in seconds
time_step = 0.01  # Time step for simulation
current_time = 0.0

# Define equipment data
equipment_data = {
    "M1": {
        "processing_time_s": 90.0,
        "availability_pct": 0.99,
        "mttr_s": 600.0,
        "power_working_kw": 3.0,
        "power_idle_kw": 0.3
    },
    "M2": {
        "processing_time_s": 70.0,
        "availability_pct": 0.98,
        "mttr_s": 900.0,
        "power_working_kw": 4.5,
        "power_idle_kw": 0.45
    },
    "M3": {
        "processing_time_s": 110.0,
        "availability_pct": 0.99,
        "mttr_s": 1200.0,
        "power_working_kw": 6.0,
        "power_idle_kw": 0.6
    },
    "B0": {
        "capacity": 15,
        "before": "source",
        "after": "M1"
    },
    "B1": {
        "capacity": 5,
        "before": "M1",
        "after": "M2"
    },
    "B2": {
        "capacity": 5,
        "before": "M2",
        "after": "M3"
    }
}

# Create a class for a machine
class Machine:
    def __init__(self, id, processing_time, availability, mttr, power_working, power_idle):
        self.id = id
        self.processing_time = processing_time
        self.availability = availability
        self.mttr = mttr
        self.power_working = power_working
        self.power_idle = power_idle
        self.is_operational = True
        self.last_start_time = 0.0
        self.total_operational_time = 0.0
        self.total_downtime = 0.0
        self.parts_processed = 0
        self.working_time = 0.0
        self.idle_time = 0.0
        self.is_processing = False
        self.process_start_time = 0.0

# Create machines
machines = {}
for machine_id, params in equipment_data.items():
    if machine_id in ['M1', 'M2', 'M3']:
        machines[machine_id] = Machine(
            machine_id,
            params['processing_time_s'],
            params['availability_pct'],
            params['mttr_s'],
            params['power_working_kw'],
            params['power_idle_kw']
        )

# Create buffers
buffers = {}
for buffer_id, params in equipment_data.items():
    if buffer_id in ['B0', 'B1', 'B2']:
        buffers[buffer_id] = {
            'capacity': params['capacity'],
            'content': 0,
            'before': params['before'],
            'after': params['after']
        }

# Create source part generator
class PartGenerator:
    def __init__(self, inter_arrival_time):
        self.inter_arrival_time = inter_arrival_time
        self.last_generation_time = 0.0
        self.part_count = 0

    def generate_part(self, time):
        if time - self.last_generation_time >= self.inter_arrival_time:
            self.last_generation_time = time
            self.part_count += 1
            return True
        return False

# Initialize part generator
part_generator = PartGenerator(60.0)

# Create a part class
class Part:
    def __init__(self, id):
        self.id = id
        self.creation_time = 0.0
        self.current_station = None
        self.processing_start_time = 0.0
        self.processing_end_time = 0.0
        self.status = 'created'

# Create parts list
parts = []
part_id_counter = 0

# Create a simple body for the part (using a sphere)
def create_part_body():
    part_body = chrono.ChBody()
    part_body.SetBodyFixed(False)
    part_body.SetPos(chrono.ChVectorD(0, 0, 0))
    part_body.SetMass(1)
    part_body.SetInertiaXX(chrono.ChVectorD(0.1, 0.1, 0.1))
    
    # Add a collision shape
    part_shape = chrono.ChSphereShape()
    part_shape.GetSphereGeometry().rad = 0.1
    part_body.AddAsset(part_shape)
    
    return part_body

# Sensor data storage and logging
sensor_data_log = []
events_log = []
samples_log = []

# Helper function to log events
def log_event(machine_id, reason_code, duration_s, energy_kwh):
    event = {
        'ts': datetime.now(),
        'machine_id': machine_id,
        'reason_code': reason_code,
        'duration_s': duration_s,
        'energy_kwh': energy_kwh
    }
    events_log.append(event)
    # Print to console for debugging
    print(f"Event: {machine_id} - {reason_code} - Duration: {duration_s}s - Energy: {energy_kwh}kWh")

# Helper function to log samples
def log_sample(machine_id, tag, value):
    sample = {
        'ts': datetime.now(),
        'machine_id': machine_id,
        'tag': tag,
        'value': value
    }
    samples_log.append(sample)
    # Print to console for debugging
    print(f"Sample: {machine_id} - {tag} - Value: {value}")

# Helper function to log raw ingest for debugging
def log_raw_ingest(source, payload):
    ingest = {
        'ingested_at': datetime.now(),
        'source': source,
        'payload': payload
    }
    # For now, just print it
    print(f"Raw ingest from {source}: {payload}")

# Start the simulation loop
print("Starting simulation...")
start_time = time.time()

# Main simulation loop
while current_time < sim_duration:
    # Determine if we should generate a new part
    if part_generator.generate_part(current_time):
        part = Part(part_id_counter)
        part_id_counter += 1
        part.creation_time = current_time
        part.current_station = 'source'
        parts.append(part)
        # Log part generation as raw ingest
        log_raw_ingest('part_generator', {'part_id': part.id, 'creation_time': part.creation_time, 'source': 'source'})

    # Process each machine
    for machine_id, machine in machines.items():
        if machine.is_operational:
            # Simulate processing
            if machine.is_processing:
                if current_time - machine.process_start_time >= machine.processing_time:
                    # Processing complete
                    machine.is_processing = False
                    machine.parts_processed += 1
                    machine.working_time += machine.processing_time
                    machine.total_operational_time += machine.processing_time
                    log_event(machine_id, 'processing_complete', machine.processing_time, 
                              machine.processing_time * machine.power_working / 3600.0)
                    log_sample(machine_id, 'process_time_s', machine.processing_time)
                    log_sample(machine_id, 'availability', machine.availability)
                    log_sample(machine_id, 'mttr_s', machine.mttr)
                    log_sample(machine_id, 'work_power_kw', machine.power_working)
                    log_sample(machine_id, 'idle_power_kw', machine.power_idle)
                    log_sample(machine_id, 'capacity', equipment_data[machine_id]['capacity'] if machine_id in ['M1', 'M2', 'M3'] else 0)
            else:
                # Check if we can activate processing based on availability
                if np.random.rand() < machine.availability:
                    # Simulate a random processing start
                    if np.random.rand() < 0.1:  # 10% chance to start processing
                        machine.is_processing = True
                        machine.process_start_time = current_time
                        machine.working_time += 0.1  # Small amount due to simulation
                        log_sample(machine_id, 'work_power_kw', machine.power_working)
                        log_sample(machine_id, 'idle_power_kw', machine.power_idle)
                else:
                    # Simulate a failure
                    if np.random.rand() < 0.001:  # 0.1% chance of failure
                        machine.is_operational = False
                        log_event(machine_id, 'failure', machine.mttr, 0.0)
                        log_sample(machine_id, 'availability', machine.availability)
                        # Simulate repair
                        machine.total_downtime += machine.mttr
                        if np.random.rand() < 0.01:  # 1% chance to restart immediately after repair
                            machine.is_operational = True
                            log_event(machine_id, 'repaired', 0.0, 0.0)
                            log_sample(machine_id, 'availability', machine.availability)
        else:
            # Simulate repair
            if np.random.rand() < 0.001:  # 0.1% chance to repair
                machine.is_operational = True
                log_event(machine_id, 'repaired', 0.0, 0.0)
                log_sample(machine_id, 'availability', machine.availability)
    
    # Update buffer content
    for buffer_id, buffer in buffers.items():
        # For simplicity, assume buffer fills and empties based on part flow
        if buffer_id == 'B0':
            # B0 receives parts from source and sends to M1
            if len(parts) > 0 and parts[0].current_station == 'source':
                if buffer['content'] < buffer['capacity']:
                    buffer['content'] += 1
                    parts[0].current_station = 'B0'
        elif buffer_id == 'B1':
            # B1 receives parts from M1 and sends to M2
            pass
        elif buffer_id == 'B2':
            # B2 receives parts from M2 and sends to M3
            pass

    # Increment time and step simulation
    current_time += time_step

    # Log machine status
    for machine_id, machine in machines.items():
        log_sample(machine_id, 'availability', machine.availability)
        log_sample(machine_id, 'process_time_s', machine.processing_time)
        log_sample(machine_id, 'mttr_s', machine.mttr)
        log_sample(machine_id, 'work_power_kw', machine.power_working)
        log_sample(machine_id, 'idle_power_kw', machine.power_idle)
        log_sample(machine_id, 'capacity', equipment_data[machine_id]['capacity'] if machine_id in ['M1', 'M2', 'M3'] else 0)

# Calculate final metrics
print("Simulation complete.")
end_time = time.time()
print(f"Total simulation time: {end_time - start_time:.2f} seconds")

# Print summary statistics
for machine_id, machine in machines.items():
    print(f"Machine {machine_id}:")
    print(f"  Parts processed: {machine.parts_processed}")
    print(f"  Operational time: {machine.total_operational_time:.2f}s")
    print(f"  Downtime: {machine.total_downtime:.2f}s")
    print(f"  Availability: {machine.total_operational_time/(machine.total_operational_time + machine.total_downtime):.2%}")
    print(f"  Working time: {machine.working_time:.2f}s")
    print(f"  Idle time: {machine.idle_time:.2f}s")

# Print buffer status
for buffer_id, buffer in buffers.items():
    print(f"Buffer {buffer_id}: {buffer['content']}/{buffer['capacity']} parts")

# Print samples and events for debugging purposes
print(f"Total samples logged: {len(samples_log)}")
print(f"Total events logged: {len(events_log)}")

# Save logs to JSON files (simulated)
try:
    with open('samples.json', 'w') as f:
        json.dump(samples_log, f, default=str)
    with open('events.json', 'w') as f:
        json.dump(events_log, f, default=str)
    print("Logs saved to samples.json and events.json")
except Exception as e:
    print(f"Error saving logs: {e}")

print("Simulation finished.")
```