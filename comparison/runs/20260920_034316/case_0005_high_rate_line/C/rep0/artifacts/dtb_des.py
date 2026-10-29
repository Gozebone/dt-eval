import simpy
import random
import math
from collections import defaultdict

# Simulation parameters
WARMUP_S = 21600
WINDOW_S = 432000
REPETITIONS = 10
SAMPLE_INTERVAL = 10

# Machine and buffer configurations
machines_config = {
    'M1': {
        'processing_time_s': 60,
        'availability': 0.995,
        'mttr_s': 300,
        'power_working_kw': 3.0,
        'power_idle_kw': 0.3
    },
    'M2': {
        'processing_time_s': 80,
        'availability': 0.99,
        'mttr_s': 600,
        'power_working_kw': 5.0,
        'power_idle_kw': 0.5
    },
    'M3': {
        'processing_time_s': 70,
        'availability': 0.99,
        'mttr_s': 600,
        'power_working_kw': 4.5,
        'power_idle_kw': 0.45
    },
    'M4': {
        'processing_time_s': 75,
        'availability': 0.995,
        'mttr_s': 300,
        'power_working_kw': 4.0,
        'power_idle_kw': 0.4
    }
}

buffers_config = {
    'B0': {'capacity': 25, 'before': 'source', 'after': 'M1'},
    'B1': {'capacity': 10, 'before': 'M1', 'after': 'M2'},
    'B2': {'capacity': 10, 'before': 'M2', 'after': 'M3'},
    'B3': {'capacity': 10, 'before': 'M3', 'after': 'M4'}
}

SOURCE_INTERARRIVAL_S = 45

# Global variables to collect KPIs
throughputs = []
wips = []
energy_per_parts = []

class Source:
    def __init__(self, env, buffer_out):
        self.env = env
        self.buffer_out = buffer_out
        self.parts_produced = 0
        
    def run(self):
        while True:
            yield self.env.timeout(SOURCE_INTERARRIVAL_S)
            part = f"part_{self.parts_produced}"
            self.parts_produced += 1
            # Try to put part into buffer
            if self.buffer_out.capacity > len(self.buffer_out.items):
                self.buffer_out.put(part)
            else:
                # Buffer full - drop the part or handle differently
                pass

class Station:
    def __init__(self, env, id, buffer_in, buffer_out, config):
        self.env = env
        self.id = id
        self.buffer_in = buffer_in
        self.buffer_out = buffer_out
        self.processing_time_s = config['processing_time_s']
        self.availability = config['availability']
        self.mttr_s = config['mttr_s']
        self.power_working_kw = config['power_working_kw']
        self.power_idle_kw = config['power_idle_kw']
        self.is_operational = True
        self.energy_consumed = 0.0
        self.total_processing_time = 0.0
        self.processing_start_time = None
        self.working = False
        
    def run(self):
        while True:
            # Wait for a part to arrive
            part = yield self.buffer_in.get()
            
            # Check if machine is operational
            if not self.is_operational:
                # Machine is down, wait for repair
                yield self.env.timeout(self.mttr_s)
                self.is_operational = True
            
            # Process part
            start_time = self.env.now
            yield self.env.timeout(self.processing_time_s)
            end_time = self.env.now
            
            # Record processing time
            self.total_processing_time += (end_time - start_time)
            
            # Check if we can put part into next buffer
            if self.buffer_out.capacity > len(self.buffer_out.items):
                self.buffer_out.put(part)
            else:
                # Buffer full - drop or handle differently
                pass

class Buffer:
    def __init__(self, env, id, capacity):
        self.env = env
        self.id = id
        self.capacity = capacity
        self.items = []
        
    def put(self, item):
        if len(self.items) < self.capacity:
            self.items.append(item)
        else:
            # Buffer full - drop item or handle differently
            pass
            
    def get(self):
        if self.items:
            return self.items.pop(0)
        else:
            # No items - wait until one arrives
            pass

def run_simulation(seed):
    random.seed(seed)
    
    # Create environment
    env = simpy.Environment()
    
    # Create buffers
    buffers = {}
    for bid, config in buffers_config.items():
        buffers[bid] = Buffer(env, bid, config['capacity'])
    
    # Create stations
    stations = {}
    for sid, config in machines_config.items():
        # Connect buffers to stations
        if sid == 'M1':
            buffer_in = buffers['B0']
        else:
            prev_sid = None
            for bid, bconfig in buffers_config.items():
                if bconfig['after'] == sid:
                    prev_sid = bid
                    break
            buffer_in = buffers[prev_sid]
            
        # Find next buffer
        next_bid = None
        for bid, bconfig in buffers_config.items():
            if bconfig['before'] == sid:
                next_bid = bid
                break
        buffer_out = buffers[next_bid] if next_bid else None
        
        stations[sid] = Station(env, sid, buffer_in, buffer_out, config)
    
    # Create source
    source_buffer = buffers['B0']
    source = Source(env, source_buffer)
    
    # Start all processes
    env.process(source.run())
    for station in stations.values():
        env.process(station.run())
    
    # Initialize tracking variables
    part_count = 0
    total_energy = 0.0
    wip_values = []
    last_wip_update = 0
    
    # Start monitoring WIP
    def monitor_wip():
        nonlocal last_wip_update
        while True:
            now = env.now
            if now >= WARMUP_S:
                # Calculate current WIP
                current_wip = sum(len(buffer.items) for buffer in buffers.values())
                wip_values.append((now, current_wip))
            yield env.timeout(SAMPLE_INTERVAL)
    
    env.process(monitor_wip())
    
    # Run simulation
    env.run(until=WARMUP_S + WINDOW_S)
    
    # Calculate KPIs
    # Throughput
    throughput = part_count / (WINDOW_S / 3600)
    
    # WIP
    if wip_values:
        total_wip = 0
        for i in range(1, len(wip_values)):
            dt = wip_values[i][0] - wip_values[i-1][0]
            total_wip += wip_values[i-1][1] * dt
        avg_wip = total_wip / WINDOW_S
    else:
        avg_wip = 0
    
    # Energy per part
    energy_per_part = total_energy / part_count if part_count > 0 else 0
    
    return throughput, avg_wip, energy_per_part

# Run multiple replications
for r in range(REPETITIONS):
    seed = r + 1
    throughput, wip, energy_per_part = run_simulation(seed)
    throughputs.append(throughput)
    wips.append(wip)
    energy_per_parts.append(energy_per_part)

# Calculate means
mean_throughput = sum(throughputs) / len(throughputs)
mean_wip = sum(wips) / len(wips)
mean_energy_per_part = sum(energy_per_parts) / len(energy_per_parts)

print(f"Throughput = {mean_throughput:.2f} parts/hour")
print(f"WIP = {mean_wip:.2f} parts")
print(f"Mean Energy Consumption per Part = {mean_energy_per_part:.4f} kWh/part")