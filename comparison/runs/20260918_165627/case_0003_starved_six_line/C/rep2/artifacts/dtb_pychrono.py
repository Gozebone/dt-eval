```python
import pychrono as chrono
import pychrono.irrlicht as chronoirr
import numpy as np
import time
import csv
from datetime import datetime
import threading
import queue

# Initialize PyChrono system
chrono.SetChronoDataPath('path_to_chrono_data')  # Replace with actual path
system = chrono.ChSystemNSC()
system.SetGravitationalAcceleration(chrono.ChVectorD(0, 0, 0))

# Constants
TIME_STEP = 0.01
SIMULATION_TIME = 36000  # 10 hours of simulation

# Equipment parameters
machine_params = {
    'M1': {'processing_time': 200, 'availability': 0.97, 'mttr': 900, 'power_working': 5.0, 'power_idle': 0.5},
    'M2': {'processing_time': 220, 'availability': 0.97, 'mttr': 1000, 'power_working': 5.5, 'power_idle': 0.55},
    'M3': {'processing_time': 240, 'availability': 0.97, 'mttr': 1200, 'power_working': 6.0, 'power_idle': 0.6},
    'M4': {'processing_time': 260, 'availability': 0.97, 'mttr': 1400, 'power_working': 7.0, 'power_idle': 0.7},
    'M5': {'processing_time': 230, 'availability': 0.97, 'mttr': 1100, 'power_working': 6.5, 'power_idle': 0.65},
    'M6': {'processing_time': 210, 'availability': 0.97, 'mttr': 1000, 'power_working': 6.0, 'power_idle': 0.6}
}

buffer_capacity = 10  # seconds worth of parts

# Global data storage
sensor_data = []
machine_states = {}
machine_power_data = {}

class Part:
    def __init__(self, part_id):
        self.id = part_id
        self.processing_start_time = None
        self.processing_end_time = None
        self.current_machine = None
        self.buffer_entry_time = None
        self.wip_start_time = None

class Machine:
    def __init__(self, name, processing_time, availability, mttr, power_working, power_idle):
        self.name = name
        self.processing_time = processing_time
        self.availability = availability
        self.mttr = mttr
        self.power_working = power_working
        self.power_idle = power_idle
        self.is_operational = True
        self.failure_time = 0
        self.last_failure_start = 0
        self.total_downtime = 0
        self.state = 'IDLE'  # IDLE, PROCESSING, FAILED
        self.parts_processed = 0
        self.energy_consumed = 0.0
        self.power_state = 'IDLE'
        
    def update_state(self, current_time):
        if self.state == 'FAILED':
            if current_time - self.failure_time >= self.mttr:
                self.state = 'IDLE'
                self.is_operational = True
                self.total_downtime += current_time - self.failure_time
        elif self.state == 'PROCESSING':
            pass  # Processing continues until completion
            
    def simulate_failure(self, current_time):
        if self.is_operational and np.random.rand() < (1 - self.availability) * TIME_STEP:
            self.is_operational = False
            self.state = 'FAILED'
            self.failure_time = current_time
            return True
        return False
        
    def get_power_consumption(self):
        if self.power_state == 'WORKING':
            return self.power_working
        else:
            return self.power_idle

class Buffer:
    def __init__(self, name, capacity):
        self.name = name
        self.capacity = capacity
        self.parts = []
        self.current_fill = 0
        self.entry_times = []
        
    def add_part(self, part, entry_time):
        if len(self.parts) < self.capacity:
            self.parts.append(part)
            self.current_fill += 1
            self.entry_times.append(entry_time)
            return True
        return False
        
    def remove_part(self):
        if self.parts:
            part = self.parts.pop(0)
            self.current_fill -= 1
            return part
        return None

class Source:
    def __init__(self, interval):
        self.interval = interval
        self.last_spawn_time = 0
        self.part_counter = 0
        
    def should_spawn(self, current_time):
        return current_time - self.last_spawn_time >= self.interval

# Create machines
machines = {}
for name, params in machine_params.items():
    machines[name] = Machine(name, **params)

# Create buffers
buffers = {}
for i in range(6):
    buffers[f'B{i}'] = Buffer(f'B{i}', buffer_capacity)

# Create source
source = Source(300)  # 300 seconds interval

# Create parts list
parts = []

# Simulation data logging
def log_sensor_data(part, machine_name, event_type, timestamp):
    """Log sensor data according to database schema"""
    data = {
        'timestamp': timestamp,
        'part_id': part.id,
        'machine_name': machine_name,
        'event_type': event_type,
        'processing_time': part.processing_end_time - part.processing_start_time if part.processing_end_time else 0,
        'wip': len(parts),
        'buffer_fill': {name: buf.current_fill for name, buf in buffers.items()},
        'energy_consumption': machines[machine_name].energy_consumed if machine_name in machines else 0,
        'availability': machines[machine_name].availability if machine_name in machines else 0,
        'mttr': machines[machine_name].mttr if machine_name in machines else 0,
        'power_state': machines[machine_name].power_state if machine_name in machines else 'IDLE'
    }
    sensor_data.append(data)

# Main simulation loop
current_time = 0
part_counter = 0

# Initialize parts list
for i in range(10):
    parts.append(Part(i+1))

# Start simulation
print("Starting simulation...")
start_time = time.time()

while current_time < SIMULATION_TIME:
    # Spawn new parts from source
    if source.should_spawn(current_time):
        part_counter += 1
        part = Part(part_counter)
        part.wip_start_time = current_time
        parts.append(part)
        source.last_spawn_time = current_time
        log_sensor_data(part, 'SOURCE', 'PART_SPAWNED', current_time)
    
    # Process each machine
    for name, machine in machines.items():
        machine.update_state(current_time)
        
        # Simulate machine failure
        if machine.simulate_failure(current_time):
            log_sensor_data(part, name, 'FAILURE', current_time)
            
        # If machine is operational and idle, try to process a part
        if machine.is_operational and machine.state == 'IDLE':
            # Find first available part in buffer
            buffer_name = f'B{ord(name[1]) - ord("1")}'
            if buffer_name in buffers and buffers[buffer_name].parts:
                part = buffers[buffer_name].remove_part()
                if part:
                    part.processing_start_time = current_time
                    part.current_machine = name
                    machine.state = 'PROCESSING'
                    machine.parts_processed += 1
                    machine.power_state = 'WORKING'
                    log_sensor_data(part, name, 'PROCESSING_STARTED', current_time)
                    
        # Check if processing is done
        elif machine.state == 'PROCESSING':
            if current_time - part.processing_start_time >= machine.processing_time:
                part.processing_end_time = current_time
                machine.state = 'IDLE'
                machine.power_state = 'IDLE'
                machine.energy_consumed += machine.power_working * machine.processing_time
                
                # Move to next buffer
                next_buffer = f'B{ord(name[1]) - ord("1") + 1}'
                if next_buffer in buffers:
                    if not buffers[next_buffer].add_part(part, current_time):
                        # If buffer full, put back in same buffer
                        buffers[buffer_name].add_part(part, current_time)
                        
                log_sensor_data(part, name, 'PROCESSING_COMPLETED', current_time)
    
    # Update buffer states
    for name, buffer in buffers.items():
        buffer.current_fill = len(buffer.parts)
    
    # Update time
    current_time += TIME_STEP
    
    # Log continuous data every second
    if int(current_time) % 1 == 0:
        timestamp = current_time
        for name, machine in machines.items():
            machine_data = {
                'timestamp': timestamp,
                'machine_name': name,
                'state': machine.state,
                'is_operational': machine.is_operational,
                'total_downtime': machine.total_downtime,
                'parts_processed': machine.parts_processed,
                'energy_consumption': machine.energy_consumed,
                'current_power': machine.get_power_consumption()
            }
            machine_power_data.setdefault(timestamp, []).append(machine_data)

# Write data to CSV files
with open('sensor_data.csv', 'w', newline='') as csvfile:
    fieldnames = ['timestamp', 'part_id', 'machine_name', 'event_type', 'processing_time', 
                  'wip', 'buffer_fill', 'energy_consumption', 'availability', 'mttr', 'power_state']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for row in sensor_data:
        writer.writerow(row)

with open('machine_power_data.csv', 'w', newline='') as csvfile:
    fieldnames = ['timestamp', 'machine_name', 'state', 'is_operational', 'total_downtime',
                  'parts_processed', 'energy_consumption', 'current_power']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for timestamp, machine_list in machine_power_data.items():
        for machine in machine_list:
            writer.writerow(machine)

print("Simulation completed.")
print(f"Total runtime: {time.time() - start_time:.2f} seconds")
print(f"Total parts processed: {len(sensor_data)}")
print("Data saved to sensor_data.csv and machine_power_data.csv")

# Print summary statistics
print("\nSummary Statistics:")
for name, machine in machines.items():
    print(f"{name}: Parts processed = {machine.parts_processed}, "
          f"Energy consumed = {machine.energy_consumed:.2f} kWh, "
          f"Total downtime = {machine.total_downtime:.2f} s")
```