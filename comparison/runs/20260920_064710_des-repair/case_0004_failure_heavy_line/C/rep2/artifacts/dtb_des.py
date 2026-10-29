import simpy
import random
import math

# Global variables for the simulation
env = None
replication = 0
warmup_s = 21600
window_s = 432000
replications = 10

# Data structures for storing results
throughput_sum = 0
wip_sum = 0
energy_per_part_sum = 0

# Simulation parameters
source_inter_arrival_s = 150

# Station data
stations_data = [
    {
        'id': 'M1',
        'processing_time_s': 100,
        'availability': 0.9,
        'mttr_s': 2400,
        'power_working_kw': 4.0,
        'power_idle_kw': 0.4
    },
    {
        'id': 'M2',
        'processing_time_s': 130,
        'availability': 0.92,
        'mttr_s': 3000,
        'power_working_kw': 5.0,
        'power_idle_kw': 0.5
    },
    {
        'id': 'M3',
        'processing_time_s': 90,
        'availability': 0.88,
        'mttr_s': 3600,
        'power_working_kw': 4.5,
        'power_idle_kw': 0.45
    },
    {
        'id': 'M4',
        'processing_time_s': 140,
        'availability': 0.91,
        'mttr_s': 4800,
        'power_working_kw': 7.0,
        'power_idle_kw': 0.7
    },
    {
        'id': 'M5',
        'processing_time_s': 110,
        'availability': 0.93,
        'mttr_s': 2400,
        'power_working_kw': 5.5,
        'power_idle_kw': 0.55
    }
]

# Buffer data
buffers_data = [
    {'id': 'B0', 'capacity': 6},
    {'id': 'B1', 'capacity': 3},
    {'id': 'B2', 'capacity': 3},
    {'id': 'B3', 'capacity': 3},
    {'id': 'B4', 'capacity': 3}
]

# Stores for the buffers
buffers = {}

# Stores for the stations
stations = {}

# Sink for finished parts
sink = None

# Track WIP over time
wip_samples = []
wip_sample_interval = 10

# Track energy consumption
total_energy_kwh = 0

# Track part count
parts_count = 0

class Part:
    def __init__(self, id):
        self.id = id

class Station:
    def __init__(self, env, station_id, processing_time_s, availability, mttr_s, power_working_kw, power_idle_kw, input_buffer, output_buffer):
        self.env = env
        self.id = station_id
        self.processing_time_s = processing_time_s
        self.availability = availability
        self.mttr_s = mttr_s
        self.power_working_kw = power_working_kw
        self.power_idle_kw = power_idle_kw
        self.input_buffer = input_buffer
        self.output_buffer = output_buffer
        self.is_operational = True
        self.failure_start_time = None
        self.total_energy_kwh = 0
        self.current_power_kw = power_idle_kw
        self.processing_start_time = None
        self.parts_processed = 0

    def run(self):
        global total_energy_kwh
        while True:
            # Wait for a part to arrive
            part = yield self.input_buffer.get()
            
            # Check if station is operational
            if not self.is_operational:
                # Wait until it becomes operational again
                yield self.env.timeout(self.mttr_s)
                self.is_operational = True
            
            # Check if station fails during processing
            if random.random() > self.availability:
                # Fail the station
                self.is_operational = False
                failure_duration = self.mttr_s
                yield self.env.timeout(failure_duration)
                self.is_operational = True
            
            # Start processing
            self.processing_start_time = self.env.now
            self.current_power_kw = self.power_working_kw
            yield self.env.timeout(self.processing_time_s)
            self.parts_processed += 1
            
            # End processing
            self.current_power_kw = self.power_idle_kw
            
            # Record energy consumed during processing
            processing_duration = self.env.now - self.processing_start_time
            energy_consumed = (self.power_working_kw * processing_duration) / 3600.0
            self.total_energy_kwh += energy_consumed
            total_energy_kwh += energy_consumed
            
            # Put the part in the next buffer
            yield self.output_buffer.put(part)

class Source:
    def __init__(self, env, inter_arrival_time_s, output_buffer):
        self.env = env
        self.inter_arrival_time_s = inter_arrival_time_s
        self.output_buffer = output_buffer
        self.part_id = 0

    def run(self):
        while True:
            # Create a new part
            part = Part(self.part_id)
            self.part_id += 1
            
            # Put the part in the first buffer
            yield self.output_buffer.put(part)
            
            # Wait for the next arrival
            yield self.env.timeout(self.inter_arrival_time_s)

def setup_simulation(rep_num):
    global env, buffers, stations, sink, total_energy_kwh, parts_count
    
    # Set up the simulation environment
    env = simpy.Environment()
    random.seed(rep_num)
    
    # Initialize all stores
    buffers.clear()
    stations.clear()
    total_energy_kwh = 0
    parts_count = 0
    
    # Create buffers
    for buf_data in buffers_data:
        buffers[buf_data['id']] = simpy.Store(env, capacity=buf_data['capacity'])
    
    # Create stations
    prev_buffer = buffers['B0']
    for i, station_data in enumerate(stations_data):
        station_id = station_data['id']
        processing_time_s = station_data['processing_time_s']
        availability = station_data['availability']
        mttr_s = station_data['mttr_s']
        power_working_kw = station_data['power_working_kw']
        power_idle_kw = station_data['power_idle_kw']
        
        # Determine the output buffer
        if i == len(stations_data) - 1:
            # This is the last station, output to sink
            output_buffer = None
        else:
            output_buffer = buffers[f'B{i+1}']
        
        # Create the station
        station = Station(
            env, 
            station_id, 
            processing_time_s, 
            availability, 
            mttr_s, 
            power_working_kw, 
            power_idle_kw, 
            prev_buffer, 
            output_buffer
        )
        stations[station_id] = station
        
        # Start the station process
        env.process(station.run())
        
        # Update the previous buffer for the next iteration
        prev_buffer = output_buffer
    
    # Create the sink
    sink = simpy.Store(env)
    
    # Connect the last station to the sink
    last_station = stations[stations_data[-1]['id']]
    last_station.output_buffer = sink
    
    # Create the source
    source = Source(env, source_inter_arrival_s, buffers['B0'])
    env.process(source.run())
    
    # Start sampling WIP
    env.process(sample_wip())

def sample_wip():
    global wip_samples
    while True:
        current_wip = sum(len(buffer.items) for buffer in buffers.values())
        wip_samples.append((env.now, current_wip))
        yield env.timeout(wip_sample_interval)

def run_replication(rep_num):
    global throughput_sum, wip_sum, energy_per_part_sum, parts_count
    
    setup_simulation(rep_num)
    
    # Run the simulation
    env.run(until=warmup_s + window_s)
    
    # Calculate KPIs
    # Throughput
    throughput = parts_count / (window_s / 3600.0)
    
    # WIP
    total_wip = 0
    for t, wip in wip_samples:
        if t >= warmup_s and t <= warmup_s + window_s:
            total_wip += wip
    avg_wip = total_wip / (window_s / wip_sample_interval)
    
    # Energy per part
    if parts_count > 0:
        energy_per_part = total_energy_kwh / parts_count
    else:
        energy_per_part = 0
    
    # Add to sums for averaging
    throughput_sum += throughput
    wip_sum += avg_wip
    energy_per_part_sum += energy_per_part

def main():
    global throughput_sum, wip_sum, energy_per_part_sum
    
    # Run all replications
    for i in range(replications):
        run_replication(i)
    
    # Calculate averages
    avg_throughput = throughput_sum / replications
    avg_wip = wip_sum / replications
    avg_energy_per_part = energy_per_part_sum / replications
    
    # Print results
    print(f'Throughput = {avg_throughput:.2f} parts/hour')
    print(f'WIP = {avg_wip:.2f} parts')
    print(f'Mean Energy Consumption per Part = {avg_energy_per_part:.4f} kWh/part')

main()