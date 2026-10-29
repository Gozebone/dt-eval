import simpy
import random
import math
from collections import defaultdict

# Simulation parameters from requirements
WARMUP_S = 21600
WINDOW_S = 432000
REPETITIONS = 10

# Station parameters
STATION_ID = 'M1'
PROCESSING_TIME_S = 30.0
AVAILABILITY_PCT = 95.0
MTTR_S = 1800.0
POWER_WORKING_KW = 5.0
POWER_IDLE_KW = 1.0

# Buffer parameters
BUFFER_ID = 'B0'
BUFFER_CAPACITY = 10

# Source parameters
SOURCE_INTER_ARRIVAL_TIME_S = None

# Defect parameters
DEFECT_RATE = None

# Global variables for tracking
throughputs = []
wips = []
energies_per_part = []

class Part:
    def __init__(self, part_id):
        self.id = part_id
        self.arrival_time = None
        self.departure_time = None
        self.processed_stations = set()

class Station:
    def __init__(self, env, station_id, processing_time_s, availability_pct, mttr_s, power_working_kw, power_idle_kw):
        self.env = env
        self.station_id = station_id
        self.processing_time_s = processing_time_s
        self.availability_pct = availability_pct
        self.mttr_s = mttr_s
        self.power_working_kw = power_working_kw
        self.power_idle_kw = power_idle_kw
        self.is_operational = True
        self.failure_start = None
        self.total_energy_kwh = 0.0
        self.last_update = 0.0
        
        # Setup the resource for the station
        self.resource = simpy.Resource(env, capacity=1)
        
        # Start the failure process if availability is specified
        if availability_pct is not None and mttr_s is not None:
            env.process(self._failure_process())
    
    def _failure_process(self):
        while True:
            # Determine next failure time based on availability
            if self.is_operational:
                # Exponential distribution for time to failure
                time_to_failure = random.expovariate((100 - self.availability_pct) / 100)
                yield self.env.timeout(time_to_failure)
                
                # Fail the station
                self.is_operational = False
                self.failure_start = self.env.now
                # Schedule repair
                self.env.process(self._repair_process())
            else:
                # Wait until repaired
                yield self.env.timeout(1e6)  # Large timeout to avoid issues
    
    def _repair_process(self):
        # Wait for MTTR
        yield self.env.timeout(self.mttr_s)
        # Repair the station
        self.is_operational = True
        self.failure_start = None
        # Update energy for downtime period
        if self.last_update > 0:
            downtime = self.env.now - self.last_update
            self.total_energy_kwh += self.power_idle_kw * downtime / 3600.0

    def process_part(self, part):
        # Record energy usage for idle time before processing
        if self.last_update > 0:
            idle_duration = self.env.now - self.last_update
            self.total_energy_kwh += self.power_idle_kw * idle_duration / 3600.0
            
        # Wait for the station to be available
        with self.resource.request() as req:
            yield req
            # Check if operational
            if not self.is_operational:
                # Wait until repaired
                yield self.env.timeout(1e6)  # Placeholder, will be handled by failure process
                
            # Record energy usage for processing time
            start_processing = self.env.now
            yield self.env.timeout(self.processing_time_s)
            
            # Update energy consumption during processing
            processing_duration = self.env.now - start_processing
            self.total_energy_kwh += self.power_working_kw * processing_duration / 3600.0
            
            # Update last update time
            self.last_update = self.env.now

class Source:
    def __init__(self, env, inter_arrival_time_s):
        self.env = env
        self.inter_arrival_time_s = inter_arrival_time_s
        self.parts_generated = 0
        
    def generate_parts(self, buffer):
        while True:
            # Generate part
            self.parts_generated += 1
            part = Part(self.parts_generated)
            part.arrival_time = self.env.now
            yield self.env.timeout(self.inter_arrival_time_s)
            # Put part into buffer
            yield buffer.put(part)

class Buffer:
    def __init__(self, env, buffer_id, capacity):
        self.env = env
        self.buffer_id = buffer_id
        self.capacity = capacity
        self.store = simpy.Store(env, capacity=capacity)
        
    def put(self, item):
        return self.store.put(item)
    
    def get(self):
        return self.store.get()
    
    def level(self):
        return len(self.store.items)

def run_simulation(seed):
    random.seed(seed)
    env = simpy.Environment()
    
    # Create buffer
    buffer = Buffer(env, BUFFER_ID, BUFFER_CAPACITY)
    
    # Create station
    station = Station(env, STATION_ID, PROCESSING_TIME_S, AVAILABILITY_PCT, MTTR_S, POWER_WORKING_KW, POWER_IDLE_KW)
    
    # Create source
    source = Source(env, SOURCE_INTER_ARRIVAL_TIME_S)
    
    # Start source process
    env.process(source.generate_parts(buffer))
    
    # Track parts that leave the system
    parts_departed = []
    
    def station_process():
        while True:
            # Get part from buffer
            part = yield buffer.get()
            # Process part at station
            yield station.process_part(part)
            # Record departure
            part.departure_time = env.now
            parts_departed.append(part)
    
    # Start station process
    env.process(station_process())
    
    # Run simulation
    env.run(until=WARMUP_S + WINDOW_S)
    
    # Calculate KPIs
    # Throughput
    window_start = WARMUP_S
    window_end = WARMUP_S + WINDOW_S
    parts_in_window = [p for p in parts_departed if window_start <= p.departure_time <= window_end]
    throughput = len(parts_in_window) / (WINDOW_S / 3600.0)
    
    # WIP
    wip_sum = 0.0
    prev_time = window_start
    prev_wip = 0
    
    # Sample WIP at regular intervals
    sample_interval = 10.0
    for t in range(int(window_start), int(window_end), int(sample_interval)):
        # Count parts in system
        parts_in_system = 0
        # Parts in buffer
        parts_in_system += buffer.level()
        # Parts in station (assuming one part can be processed at a time)
        # We'll approximate this by checking if station is busy
        if hasattr(station, 'resource') and len(station.resource.queue) > 0:
            parts_in_system += 1
        elif hasattr(station, 'resource') and len(station.resource.users) > 0:
            parts_in_system += 1
        
        # Add contribution from previous interval
        if t > prev_time:
            wip_sum += prev_wip * (t - prev_time)
        
        prev_time = t
        prev_wip = parts_in_system
    
    # Handle final interval
    if prev_time < window_end:
        wip_sum += prev_wip * (window_end - prev_time)
    
    wip = wip_sum / WINDOW_S
    
    # Energy per part
    total_energy_kwh = station.total_energy_kwh
    energy_per_part = total_energy_kwh / len(parts_in_window) if len(parts_in_window) > 0 else 0.0
    
    return throughput, wip, energy_per_part

# Run multiple replications
for i in range(REPETITIONS):
    seed = i + 1
    throughput, wip, energy_per_part = run_simulation(seed)
    throughputs.append(throughput)
    wips.append(wip)
    energies_per_part.append(energy_per_part)

# Calculate averages
avg_throughput = sum(throughputs) / len(throughputs)
avg_wip = sum(wips) / len(wips)
avg_energy_per_part = sum(energies_per_part) / len(energies_per_part)

print(f"Throughput = {avg_throughput:.6f} parts/hour")
print(f"WIP = {avg_wip:.6f} parts")
print(f"Mean Energy Consumption per Part = {avg_energy_per_part:.6f} kWh/part")