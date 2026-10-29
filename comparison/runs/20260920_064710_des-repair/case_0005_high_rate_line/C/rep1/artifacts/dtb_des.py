import simpy
import random
import math
from collections import defaultdict

# Simulation parameters
class Params:
    def __init__(self):
        self.source_inter_arrival = 45
        self.stations = [
            {
                "id": "M1",
                "processing_time_s": 60,
                "availability_pct": 99.99,
                "mttr_s": 300,
                "power_working_kw": 3.0,
                "power_idle_kw": 0.3
            },
            {
                "id": "M2",
                "processing_time_s": 80,
                "availability_pct": 100.0,
                "mttr_s": 600,
                "power_working_kw": 5.0,
                "power_idle_kw": 0.5
            },
            {
                "id": "M3",
                "processing_time_s": 70,
                "availability_pct": 99.88,
                "mttr_s": 600,
                "power_working_kw": 4.5,
                "power_idle_kw": 0.45
            },
            {
                "id": "M4",
                "processing_time_s": 75,
                "availability_pct": 100.0,
                "mttr_s": 300,
                "power_working_kw": 4.0,
                "power_idle_kw": 0.4
            }
        ]
        self.buffers = [
            {
                "id": "B0",
                "capacity": 25,
                "before": "source",
                "after": "M1"
            },
            {
                "id": "B1",
                "capacity": 10,
                "before": "M1",
                "after": "M2"
            },
            {
                "id": "B2",
                "capacity": 10,
                "before": "M2",
                "after": "M3"
            },
            {
                "id": "B3",
                "capacity": 10,
                "before": "M3",
                "after": "M4"
            }
        ]
        self.warmup_s = 21600
        self.window_s = 432000
        self.replications = 10

params = Params()

class Part:
    def __init__(self, id):
        self.id = id

class Station:
    def __init__(self, env, id, processing_time_s, availability_pct, mttr_s, 
                 power_working_kw, power_idle_kw, input_buffer, output_buffer):
        self.env = env
        self.id = id
        self.processing_time_s = processing_time_s
        self.availability_pct = availability_pct
        self.mttr_s = mttr_s
        self.power_working_kw = power_working_kw
        self.power_idle_kw = power_idle_kw
        self.input_buffer = input_buffer
        self.output_buffer = output_buffer
        self.is_operational = True
        self.failure_start = None
        self.total_energy_kwh = 0.0
        self.energy_sample_interval = 10.0  # Sample every 10 seconds
        self.last_energy_sample = 0.0
        self.parts_processed = 0
        self.processing = False
        
    def run(self):
        while True:
            # Wait for a part to arrive
            part = yield self.input_buffer.get()
            
            # Record start time for energy calculation
            start_time = self.env.now
            
            # Check if the station is operational
            if not self.is_operational:
                # Wait until it becomes operational again
                yield self.env.timeout(self.mttr_s)
                self.is_operational = True
                
            # Process the part
            yield self.env.timeout(self.processing_time_s)
            
            # Calculate energy consumption during processing
            processing_duration = self.env.now - start_time
            self.total_energy_kwh += (self.power_working_kw * processing_duration) / 3600.0
            
            # Increment parts processed
            self.parts_processed += 1
            
            # Put the part into the next buffer
            yield self.output_buffer.put(part)
            
            # Check for failure based on availability
            if self.availability_pct < 100.0:
                if random.random() > (self.availability_pct / 100.0):
                    # Failure occurred
                    self.is_operational = False
                    failure_duration = self.mttr_s
                    yield self.env.timeout(failure_duration)
                    self.is_operational = True

class Source:
    def __init__(self, env, inter_arrival_time_s, output_buffer, part_counter):
        self.env = env
        self.inter_arrival_time_s = inter_arrival_time_s
        self.output_buffer = output_buffer
        self.part_counter = part_counter
        
    def run(self):
        part_id = 0
        while True:
            # Generate a new part
            part = Part(part_id)
            part_id += 1
            
            # Put the part into the first buffer
            yield self.output_buffer.put(part)
            
            # Increment the part counter
            self.part_counter += 1
            
            # Wait for the next part arrival
            yield self.env.timeout(self.inter_arrival_time_s)

def run_simulation(replication_id):
    env = simpy.Environment()
    
    # Create buffers
    buffers = {}
    for buf in params.buffers:
        buffers[buf["id"]] = simpy.Store(env, capacity=buf["capacity"])
    
    # Create counters
    part_counter = 0
    
    # Create source
    source = Source(env, params.source_inter_arrival, buffers["B0"], part_counter)
    env.process(source.run())
    
    # Create stations
    stations = {}
    for i, station_data in enumerate(params.stations):
        station_id = station_data["id"]
        processing_time_s = station_data["processing_time_s"]
        availability_pct = station_data["availability_pct"]
        mttr_s = station_data["mttr_s"]
        power_working_kw = station_data["power_working_kw"]
        power_idle_kw = station_data["power_idle_kw"]
        
        if i == 0:
            input_buffer = buffers["B0"]
        else:
            input_buffer = buffers[params.buffers[i-1]["id"]]
            
        if i == len(params.stations) - 1:
            output_buffer = simpy.Store(env)  # Sink
        else:
            output_buffer = buffers[params.buffers[i]["id"]]
            
        station = Station(env, station_id, processing_time_s, availability_pct, mttr_s,
                          power_working_kw, power_idle_kw, input_buffer, output_buffer)
        stations[station_id] = station
        env.process(station.run())
    
    # Track WIP
    wip_samples = []
    wip_times = []
    
    def sample_wip():
        while True:
            yield env.timeout(10.0)  # Sample every 10 seconds
            total_parts = sum(len(buf.items) for buf in buffers.values())
            # Add parts being processed (assuming 1 part per active station)
            total_parts += sum(1 for s in stations.values() if s.processing)
            wip_samples.append(total_parts)
            wip_times.append(env.now)
    
    env.process(sample_wip())
    
    # Run simulation
    env.run(until=params.warmup_s + params.window_s)
    
    # Calculate results
    throughput = 0
    total_energy = 0.0
    total_parts = 0
    
    # Count parts that went through the last station
    throughput = len(output_buffer.items) if hasattr(output_buffer, 'items') else 0
    
    # Sum up all energy consumption
    for station in stations.values():
        total_energy += station.total_energy_kwh
    
    # Calculate WIP
    if len(wip_times) >= 2:
        wip_sum = 0.0
        for i in range(1, len(wip_times)):
            wip_sum += wip_samples[i-1] * (wip_times[i] - wip_times[i-1])
        wip_avg = wip_sum / params.window_s
    else:
        wip_avg = 0.0
    
    # Calculate energy per part
    energy_per_part = total_energy / throughput if throughput > 0 else 0.0
    
    return throughput, wip_avg, energy_per_part

def main():
    total_throughputs = []
    total_wips = []
    total_energy_per_part = []
    
    for i in range(params.replications):
        random.seed(i)
        throughput, wip, energy_per_part = run_simulation(i)
        total_throughputs.append(throughput)
        total_wips.append(wip)
        total_energy_per_part.append(energy_per_part)
    
    avg_throughput = sum(total_throughputs) / len(total_throughputs)
    avg_wip = sum(total_wips) / len(total_wips)
    avg_energy_per_part = sum(total_energy_per_part) / len(total_energy_per_part)
    
    print(f"Throughput = {avg_throughput} parts/hour")
    print(f"WIP = {avg_wip} parts")
    print(f"Mean Energy Consumption per Part = {avg_energy_per_part} kWh/part")

if __name__ == "__main__":
    main()