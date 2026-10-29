```python
import pychrono as chrono
import numpy as np
import datetime
import json
import time
from collections import defaultdict

# Initialize the Chrono system
chrono.Initialize()

# Create the physical system
system = chrono.ChSystemNSC()
system.Set_G_acc(chrono.ChVectorD(0, 0, 0))  # No gravity

# Define materials
material_steel = chrono.ChMaterialSurfaceNSC()
material_steel.SetFriction(0.4)
material_steel.SetRestitution(0.1)

material_refractory = chrono.ChMaterialSurfaceNSC()
material_refractory.SetFriction(0.3)
material_refractory.SetRestitution(0.05)

# Equipment parameters from requirements
equipment_params = {
    'M1': {'processing_time_s': 60, 'availability_pct': 99.99, 'mttr_s': 300, 'power_working_kw': 3.0, 'power_idle_kw': 0.3},
    'M2': {'processing_time_s': 80, 'availability_pct': 100.0, 'mttr_s': 600, 'power_working_kw': 5.0, 'power_idle_kw': 0.5},
    'M3': {'processing_time_s': 70, 'availability_pct': 99.88, 'mttr_s': 600, 'power_working_kw': 4.5, 'power_idle_kw': 0.45},
    'M4': {'processing_time_s': 75, 'availability_pct': 100.0, 'mttr_s': 300, 'power_working_kw': 4.0, 'power_idle_kw': 0.4},
    'B0': {'capacity': 25},
    'B1': {'capacity': 10},
    'B2': {'capacity': 10},
    'B3': {'capacity': 10}
}

# Create station objects
class Station:
    def __init__(self, id, params):
        self.id = id
        self.params = params
        self.state = 'idle'  # idle, processing, failed
        self.processing_start = None
        self.failure_start = None
        self.failure_duration = 0
        self.energy_consumed = 0
        self.processed_items = 0
        self.failed_items = 0
        self.is_operational = True

# Create buffer objects
class Buffer:
    def __init__(self, id, capacity):
        self.id = id
        self.capacity = capacity
        self.items = []
    
    def add_item(self, item):
        if len(self.items) < self.capacity:
            self.items.append(item)
            return True
        return False
    
    def remove_item(self):
        if self.items:
            return self.items.pop(0)
        return None

# Create stations and buffers
stations = {}
buffers = {}

for id, params in equipment_params.items():
    if id.startswith('M'):
        stations[id] = Station(id, params)
    elif id.startswith('B'):
        buffers[id] = Buffer(id, params['capacity'])

# Create source for items
source_interval = 45  # seconds
next_source_time = source_interval
items_in_system = 0

# Simulation parameters
simulation_time = 0
max_simulation_time = 432000  # 120 hours in seconds
log_data = []

# Helper function to log events
def log_event(machine_id, reason_code, duration_s, energy_kwh):
    event_data = {
        'ts': datetime.datetime.now().isoformat(),
        'machine_id': machine_id,
        'reason_code': reason_code,
        'duration_s': duration_s,
        'energy_kwh': energy_kwh
    }
    log_data.append(('events', event_data))

# Helper function to log samples
def log_sample(machine_id, tag, value):
    sample_data = {
        'ts': datetime.datetime.now().isoformat(),
        'machine_id': machine_id,
        'tag': tag,
        'value': value
    }
    log_data.append(('samples', sample_data))

# Main simulation loop
while simulation_time < max_simulation_time:
    current_time = datetime.datetime.now()
    
    # Handle item generation at source
    if simulation_time >= next_source_time:
        items_in_system += 1
        # Log item arrival
        log_sample('source', 'item_count', items_in_system)
        next_source_time += source_interval
    
    # Process each station
    for station_id, station in stations.items():
        if station.state == 'idle':
            # Check if there's an item to process in the buffer before this station
            prev_buffer_id = None
            if station_id == 'M1':
                prev_buffer_id = 'B0'
            elif station_id == 'M2':
                prev_buffer_id = 'B1'
            elif station_id == 'M3':
                prev_buffer_id = 'B2'
            elif station_id == 'M4':
                prev_buffer_id = 'B3'
            
            if prev_buffer_id and buffers[prev_buffer_id].items:
                # Remove item from buffer
                item = buffers[prev_buffer_id].remove_item()
                if item:
                    # Start processing
                    station.state = 'processing'
                    station.processing_start = simulation_time
                    # Log processing start
                    log_event(station_id, 'start_processing', 0, 0)
        
        elif station.state == 'processing':
            # Check if processing is complete
            if simulation_time - station.processing_start >= station.params['processing_time_s']:
                # Complete processing
                station.state = 'idle'
                station.processed_items += 1
                # Calculate energy consumption
                energy_used = (station.params['processing_time_s'] * station.params['power_working_kw']) / 3600.0
                station.energy_consumed += energy_used
                # Log processing completion
                log_event(station_id, 'completed_processing', station.params['processing_time_s'], energy_used)
                
                # Move item to next buffer or end of line
                next_buffer_id = None
                if station_id == 'M1':
                    next_buffer_id = 'B1'
                elif station_id == 'M2':
                    next_buffer_id = 'B2'
                elif station_id == 'M3':
                    next_buffer_id = 'B3'
                elif station_id == 'M4':
                    # Item completed, no buffer needed
                    pass
                
                if next_buffer_id:
                    # Try to add item to next buffer
                    if buffers[next_buffer_id].add_item('processed_item'):
                        # Successfully added to buffer
                        pass
                    else:
                        # Buffer full, item gets lost or waits
                        station.failed_items += 1
                        # Log buffer overflow
                        log_event(station_id, 'buffer_overflow', 0, 0)
        
        # Handle failures based on availability
        if station.is_operational:
            # Simulate random failure based on availability
            availability = station.params['availability_pct'] / 100.0
            if np.random.rand() > availability:
                station.is_operational = False
                station.state = 'failed'
                station.failure_start = simulation_time
                # Log failure
                log_event(station_id, 'failure', 0, 0)
        
        # Handle repair
        if not station.is_operational:
            if simulation_time - station.failure_start >= station.params['mttr_s']:
                station.is_operational = True
                station.state = 'idle'
                # Log repair
                log_event(station_id, 'repaired', station.params['mttr_s'], 0)
    
    # Update buffer states
    for buffer_id, buffer in buffers.items():
        log_sample(buffer_id, 'current_capacity', len(buffer.items))
    
    # Update station states
    for station_id, station in stations.items():
        if station.state == 'processing':
            log_sample(station_id, 'status', 1)  # Processing
        elif station.state == 'idle':
            log_sample(station_id, 'status', 0)  # Idle
        elif station.state == 'failed':
            log_sample(station_id, 'status', 2)  # Failed
    
    # Advance simulation time
    simulation_time += 1
    time.sleep(0.001)  # Small delay for simulation pacing

# Final logging
print("Simulation completed")
print(f"Total items processed: {items_in_system}")
for station_id, station in stations.items():
    print(f"Station {station_id}: Processed {station.processed_items}, Failed {station.failed_items}")

# Output logs to simulate database entries
print("\nGenerated log data:")
for table, data in log_data:
    print(f"{table}: {json.dumps(data)}")

# Cleanup
chrono.Finalize()
```