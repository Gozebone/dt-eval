import simpy
import random
import math
from collections import defaultdict

# Simulation parameters from the database
STATIONS = [
    {'id': 'M1', 'processing_time_s': 600, 'availability_pct': 95, 'mttr_s': 300, 'power_working_kw': 100, 'power_idle_kw': 20},
    {'id': 'M2', 'processing_time_s': 450, 'availability_pct': 90, 'mttr_s': 250, 'power_working_kw': 80, 'power_idle_kw': 15},
    {'id': 'M3', 'processing_time_s': 300, 'availability_pct': 98, 'mttr_s': 150, 'power_working_kw': 60, 'power_idle_kw': 10}
]

BUFFERS = [
    {'id': 'B0', 'capacity': 50, 'before': 'source', 'after': 'M1'}
]

# DES Horizon
WARMUP_S = 21600
WINDOW_S = 432000
REPETITIONS = 10

# Global variables for tracking metrics
throughputs = []
wips = []
energy_per_part = []

class Station:
    def __init__(self, env, id, processing_time_s, availability_pct, mttr_s, power_working_kw, power_idle_kw):
        self.env = env
        self.id = id
        self.processing_time_s = processing_time_s
        self.availability_pct = availability_pct
        self.mttr_s = mttr_s
        self.power_working_kw = power_working_kw
        self.power_idle_kw = power_idle_kw
        
        # For failure modeling
        self.is_operational = True
        self.failure_times = []
        self.repair_times = []
        
        # Energy tracking
        self.total_energy_kwh = 0
        self.current_power_kw = power_idle_kw
        self.last_update_time = 0
        
        # Process
        self.process = env.process(self._run())
    
    def _run(self):
        while True:
            if self.is_operational:
                # Simulate processing time
                yield self.env.timeout(self.processing_time_s)
                
                # Update energy consumption
                self._update_energy()
            else:
                # Wait until repaired
                yield self.env.event()
    
    def _update_energy(self):
        # Calculate time since last update
        current_time = self.env.now
        delta_time_hours = (current_time - self.last_update_time) / 3600.0
        self.total_energy_kwh += self.current_power_kw * delta_time_hours
        self.last_update_time = current_time
    
    def request_failure(self):
        # Schedule failure event
        if self.availability_pct is not None:
            failure_prob = 1 - self.availability_pct / 100.0
            if random.random() < failure_prob:
                self.is_operational = False
                self.current_power_kw = self.power_idle_kw
                self.failure_times.append(self.env.now)
                repair_duration = self.mttr_s
                # Schedule repair
                self.env.process(self._repair(repair_duration))
    
    def _repair(self, duration):
        yield self.env.timeout(duration)
        self.is_operational = True
        self.current_power_kw = self.power_working_kw
        self.repair_times.append(self.env.now)

class Buffer:
    def __init__(self, env, id, capacity):
        self.env = env
        self.id = id
        self.capacity = capacity
        self.items = simpy.Store(env)
    
    def put(self, item):
        return self.items.put(item)
    
    def get(self):
        return self.items.get()

class Source:
    def __init__(self, env, inter_arrival_time_s):
        self.env = env
        self.inter_arrival_time_s = inter_arrival_time_s
        self.part_count = 0
        self.process = env.process(self._generate_parts())
    
    def _generate_parts(self):
        while True:
            yield self.env.timeout(self.inter_arrival_time_s)
            self.part_count += 1
            yield self.env.process(self._send_part())

class LineModel:
    def __init__(self, env):
        self.env = env
        self.stations = {}
        self.buffers = {}
        self.source = None
        self.parts_produced = 0
        self.total_energy_kwh = 0
        self.wip_samples = []
        self.wip_sample_time = 0
        
        # Initialize components
        self._initialize_components()
        
        # Start monitoring WIP
        self.env.process(self._monitor_wip())
    
    def _initialize_components(self):
        # Create buffers
        for buf_config in BUFFERS:
            self.buffers[buf_config['id']] = Buffer(self.env, buf_config['id'], buf_config['capacity'])
        
        # Create stations
        for station_config in STATIONS:
            self.stations[station_config['id']] = Station(
                self.env,
                station_config['id'],
                station_config['processing_time_s'],
                station_config['availability_pct'],
                station_config['mttr_s'],
                station_config['power_working_kw'],
                station_config['power_idle_kw']
            )
        
        # Connect components
        self.source = Source(self.env, 300)  # Default inter-arrival time
        
        # Connect source to first buffer
        self.env.process(self._connect_source_to_buffer())
        
        # Connect buffers to stations
        self.env.process(self._connect_buffers_to_stations())
    
    def _connect_source_to_buffer(self):
        while True:
            # Wait for a part to be generated
            yield self.env.timeout(1)
            
            # Check if there's space in the first buffer
            if len(self.buffers['B0'].items.items) < self.buffers['B0'].capacity:
                # Put part into buffer
                part = f"Part_{self.source.part_count}"
                yield self.buffers['B0'].put(part)
                
                # Request next part
                self.env.process(self._process_part_in_station('M1', part))
            else:
                # Buffer full, wait
                yield self.env.timeout(1)
    
    def _connect_buffers_to_stations(self):
        # This is a simplified connection logic
        pass
    
    def _process_part_in_station(self, station_id, part):
        station = self.stations[station_id]
        
        # Simulate processing
        yield self.env.timeout(station.processing_time_s)
        
        # Update energy
        station._update_energy()
        self.total_energy_kwh += station.total_energy_kwh
        
        # If it's the last station, count as completed
        if station_id == 'M3':
            self.parts_produced += 1
    
    def _monitor_wip(self):
        while True:
            # Sample WIP every second
            yield self.env.timeout(1)
            
            wip_count = 0
            
            # Count parts in all buffers
            for buf in self.buffers.values():
                wip_count += len(buf.items.items)
            
            # Count parts in all stations
            for station in self.stations.values():
                # This is a simplification - in a real model we would track what parts are in process
                pass
            
            # Add to samples
            self.wip_samples.append((self.env.now, wip_count))
    
    def run(self, warmup_s, window_s):
        # Run for warmup period
        yield self.env.timeout(warmup_s)
        
        # Reset counters
        self.parts_produced = 0
        self.total_energy_kwh = 0
        self.wip_samples = []
        
        # Run for measurement window
        yield self.env.timeout(window_s)
        
        # Calculate final metrics
        # Throughput
        throughput = self.parts_produced / (window_s / 3600.0)
        
        # WIP
        total_wip = sum([count for _, count in self.wip_samples])
        avg_wip = total_wip / len(self.wip_samples) if self.wip_samples else 0
        
        # Energy per part
        energy_per_part = self.total_energy_kwh / self.parts_produced if self.parts_produced > 0 else 0
        
        return throughput, avg_wip, energy_per_part

def run_simulation(seed):
    random.seed(seed)
    env = simpy.Environment()
    model = LineModel(env)
    
    # Run simulation
    throughput, wip, energy_pp = env.run(until=WARMUP_S + WINDOW_S)
    
    return throughput, wip, energy_pp

def main():
    global throughputs, wips, energy_per_part
    
    for i in range(REPETITIONS):
        seed = 42 + i  # Fixed seeds
        throughput, wip, energy_pp = run_simulation(seed)
        
        throughputs.append(throughput)
        wips.append(wip)
        energy_per_part.append(energy_pp)
    
    # Compute means
    mean_throughput = sum(throughputs) / len(throughputs)
    mean_wip = sum(wips) / len(wips)
    mean_energy_per_part = sum(energy_per_part) / len(energy_per_part)
    
    print(f"Throughput = {mean_throughput:.2f} parts/hour")
    print(f"WIP = {mean_wip:.2f} parts")
    print(f"Mean Energy Consumption per Part = {mean_energy_per_part:.2f} kWh/part")

if __name__ == "__main__":
    main()