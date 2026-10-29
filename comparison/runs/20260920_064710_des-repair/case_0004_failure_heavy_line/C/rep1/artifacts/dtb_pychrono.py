```python
import pychrono as chrono
import numpy as np
import datetime
import json
import time
from collections import defaultdict

# Initialize PyChrono system
chrono.Initialize()

# Create the physical system
system = chrono.ChSystemNSC()
system.Set_G_acc(chrono.ChVectorD(0, -9.81, 0))  # Set gravity

# Define materials
steel_mat = chrono.ChMaterialSurfaceNSC()
steel_mat.SetFriction(0.5)
steel_mat.SetRestitution(0.1)

refractory_mat = chrono.ChMaterialSurfaceNSC()
refractory_mat.SetFriction(0.3)
refractory_mat.SetRestitution(0.05)

# Machine parameters from requirements
machines_data = {
    'M1': {'process_time_s': 100, 'availability': 0.9, 'mttr_s': 2400, 'work_power_kw': 4.0, 'idle_power_kw': 0.4},
    'M2': {'process_time_s': 130, 'availability': 0.92, 'mttr_s': 3000, 'work_power_kw': 5.0, 'idle_power_kw': 0.5},
    'M3': {'process_time_s': 90, 'availability': 0.88, 'mttr_s': 3600, 'work_power_kw': 4.5, 'idle_power_kw': 0.45},
    'M4': {'process_time_s': 140, 'availability': 0.91, 'mttr_s': 4800, 'work_power_kw': 7.0, 'idle_power_kw': 0.7},
    'M5': {'process_time_s': 110, 'availability': 0.93, 'mttr_s': 2400, 'work_power_kw': 5.5, 'idle_power_kw': 0.55}
}

# Buffer parameters
buffers_data = {
    'B0': {'capacity': 6, 'before': 'source', 'after': 'M1'},
    'B1': {'capacity': 3, 'before': 'M1', 'after': 'M2'},
    'B2': {'capacity': 3, 'before': 'M2', 'after': 'M3'},
    'B3': {'capacity': 3, 'before': 'M3', 'after': 'M4'},
    'B4': {'capacity': 3, 'before': 'M4', 'after': 'M5'}
}

# Create station bodies
station_bodies = {}
for machine_id in machines_data.keys():
    body = chrono.ChBody()
    body.SetIdentifier(int(machine_id[1:]))  # M1 -> 1, etc.
    body.SetMass(1000)
    body.SetInertiaXX(chrono.ChVectorD(100, 100, 100))
    body.GetCollisionModel().ClearModel()
    body.GetCollisionModel().AddBox(0.5, 0.5, 0.5)
    body.GetCollisionModel().BuildModel()
    body.SetCollide(True)
    body.SetMaterialSurface(steel_mat)
    
    # Position machines in a line
    x_pos = (int(machine_id[1:]) - 1) * 3.0
    body.SetPos(chrono.ChVectorD(x_pos, 0, 0))
    
    system.Add(body)
    station_bodies[machine_id] = body

# Create buffer bodies
buffer_bodies = {}
for buffer_id, buffer_info in buffers_data.items():
    body = chrono.ChBody()
    body.SetIdentifier(ord(buffer_id[-1]))  # B0 -> 0, etc.
    body.SetMass(500)
    body.SetInertiaXX(chrono.ChVectorD(50, 50, 50))
    body.GetCollisionModel().ClearModel()
    body.GetCollisionModel().AddBox(0.3, 0.3, 0.3)
    body.GetCollisionModel().BuildModel()
    body.SetCollide(True)
    body.SetMaterialSurface(refractory_mat)
    
    # Position buffers between machines
    if buffer_info['before'] == 'source':
        before_idx = 0
    else:
        before_idx = int(buffer_info['before'][1:]) - 1
        
    if buffer_info['after'] == 'M5':
        after_idx = 5
    else:
        after_idx = int(buffer_info['after'][1:])
        
    x_pos = (before_idx + after_idx) / 2.0 * 3.0
    body.SetPos(chrono.ChVectorD(x_pos, 0.5, 0))
    
    system.Add(body)
    buffer_bodies[buffer_id] = body

# Create source object
source_body = chrono.ChBody()
source_body.SetIdentifier(-1)
source_body.SetMass(100)
source_body.SetInertiaXX(chrono.ChVectorD(10, 10, 10))
source_body.GetCollisionModel().ClearModel()
source_body.GetCollisionModel().AddBox(0.2, 0.2, 0.2)
source_body.GetCollisionModel().BuildModel()
source_body.SetCollide(True)
source_body.SetMaterialSurface(refractory_mat)
source_body.SetPos(chrono.ChVectorD(-1.5, 0, 0))
system.Add(source_body)

# Create output area
output_body = chrono.ChBody()
output_body.SetIdentifier(10)
output_body.SetMass(100)
output_body.SetInertiaXX(chrono.ChVectorD(10, 10, 10))
output_body.GetCollisionModel().ClearModel()
output_body.GetCollisionModel().AddBox(0.2, 0.2, 0.2)
output_body.GetCollisionModel().BuildModel()
output_body.SetCollide(True)
output_body.SetMaterialSurface(refractory_mat)
output_body.SetPos(chrono.ChVectorD(13.5, 0, 0))
system.Add(output_body)

# Create sensors for tracking metrics
class MachineSensor:
    def __init__(self, machine_id, process_time, availability, mttr_s, work_power_kw, idle_power_kw):
        self.machine_id = machine_id
        self.process_time = process_time
        self.availability = availability
        self.mttr_s = mttr_s
        self.work_power_kw = work_power_kw
        self.idle_power_kw = idle_power_kw
        self.is_operational = True
        self.last_start_time = 0
        self.total_operational_time = 0
        self.total_downtime = 0
        self.current_state = "IDLE"  # IDLE or WORKING
        self.working_start_time = 0
        self.downtime_start_time = 0
        self.power_consumption = 0
        self.total_energy = 0
        self.processed_items = 0

    def update(self, current_time, is_processing=False):
        # Simulate machine state changes based on availability
        if self.is_operational:
            if is_processing:
                if self.current_state != "WORKING":
                    self.current_state = "WORKING"
                    self.working_start_time = current_time
                # Simulate processing time
                if current_time - self.working_start_time >= self.process_time:
                    self.processed_items += 1
                    self.current_state = "IDLE"
                    self.working_start_time = 0
                    self.total_operational_time += self.process_time
                    self.power_consumption = self.work_power_kw
                    self.total_energy += self.work_power_kw * self.process_time / 3600.0
            else:
                if self.current_state == "WORKING":
                    self.current_state = "IDLE"
                    self.total_operational_time += current_time - self.working_start_time
                    self.working_start_time = 0
                    self.power_consumption = self.idle_power_kw
                    self.total_energy += self.idle_power_kw * (current_time - self.downtime_start_time) / 3600.0
                elif self.current_state == "IDLE":
                    self.power_consumption = self.idle_power_kw
        else:
            if self.current_state != "DOWN":
                self.current_state = "DOWN"
                self.downtime_start_time = current_time
            self.total_downtime += current_time - self.downtime_start_time
            self.power_consumption = 0

    def get_metrics(self, current_time):
        return {
            'machine_id': self.machine_id,
            'state': self.current_state,
            'operational_time': self.total_operational_time,
            'downtime': self.total_downtime,
            'energy_consumption': self.total_energy,
            'items_processed': self.processed_items,
            'power_kw': self.power_consumption
        }

# Create sensors for each machine
sensors = {}
for machine_id, params in machines_data.items():
    sensors[machine_id] = MachineSensor(
        machine_id,
        params['process_time_s'],
        params['availability'],
        params['mttr_s'],
        params['work_power_kw'],
        params['idle_power_kw']
    )

# Simulation parameters
simulation_duration = 3600  # 1 hour of simulation
dt = 0.01  # Time step
current_time = 0

# Create logging mechanism
log_entries = []
start_time = datetime.datetime.now()

# Main simulation loop
print("Starting simulation...")
while current_time < simulation_duration:
    # Update source item generation
    if current_time % 150 < dt:
        # Generate new item at source
        pass
    
    # Update machine states
    for machine_id, sensor in sensors.items():
        # Determine if this machine is currently processing
        is_processing = False
        if sensor.current_state == "WORKING":
            is_processing = True
        sensor.update(current_time, is_processing)
    
    # Step the simulation
    system.DoStepDynamics(dt)
    current_time += dt
    
    # Log sensor data every second
    if int(current_time) % 1 == 0:
        log_entry = {
            'ts': datetime.datetime.utcnow(),
            'machine_id': '',
            'reason_code': '',
            'duration_s': 0,
            'energy_kwh': 0
        }
        
        # Log sample data
        sample_entry = {
            'ts': datetime.datetime.utcnow(),
            'machine_id': '',
            'tag': '',
            'value': 0
        }
        
        for machine_id, sensor in sensors.items():
            metrics = sensor.get_metrics(current_time)
            
            # Log event data
            event_entry = {
                'ts': datetime.datetime.utcnow(),
                'machine_id': machine_id,
                'reason_code': metrics['state'],
                'duration_s': metrics['operational_time'] if metrics['state'] == 'WORKING' else metrics['downtime'],
                'energy_kwh': metrics['energy_consumption']
            }
            log_entries.append(('events', event_entry))
            
            # Log sample data
            sample_entry['machine_id'] = machine_id
            sample_entry['tag'] = 'power_kw'
            sample_entry['value'] = metrics['power_kw']
            log_entries.append(('samples', sample_entry.copy()))
            
            sample_entry['tag'] = 'items_processed'
            sample_entry['value'] = metrics['items_processed']
            log_entries.append(('samples', sample_entry.copy()))

# Finalize simulation
print(f"Simulation completed at {datetime.datetime.now()}")
print(f"Total items processed: {[s.processed_items for s in sensors.values()]}")

# Output simulated data to match database schema
print("\nSimulated Data for Database Tables:")
print("=" * 50)

# Machines table
print("\nMachines Table:")
for machine_id, params in machines_data.items():
    print(f"('{machine_id}', {params['process_time_s']}, {params['availability']}, {params['mttr_s']}, {params['work_power_kw']}, {params['idle_power_kw']})")

# Stations table
print("\nStations Table:")
for machine_id, params in machines_data.items():
    print(f"('{machine_id}', {params['process_time_s']}, {params['availability']}, {params['mttr_s']}, {params['work_power_kw']}, {params['idle_power_kw']})")

# Buffers table
print("\nBuffers Table:")
for buffer_id, params in buffers_data.items():
    print(f"('{buffer_id}', {params['capacity']}, '{params['before']}', '{params['after']}')")

# Events view (simulated)
print("\nEvents View (Sample):")
for entry in log_entries[:5]:  # Show first 5 entries
    if entry[0] == 'events':
        e = entry[1]
        print(f"ts: {e['ts']}, machine_id: {e['machine_id']}, reason_code: {e['reason_code']}, duration_s: {e['duration_s']}, energy_kwh: {e['energy_kwh']}")

# Samples view (simulated)
print("\nSamples View (Sample):")
for entry in log_entries[:5]:  # Show first 5 entries
    if entry[0] == 'samples':
        s = entry[1]
        print(f"ts: {s['ts']}, machine_id: {s['machine_id']}, tag: {s['tag']}, value: {s['value']}")

# Cleanup
del system
chrono.Terminate()
```