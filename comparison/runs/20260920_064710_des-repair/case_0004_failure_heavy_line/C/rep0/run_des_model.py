import simpy
import random
import math
import statistics

class Part:
    def __init__(self, id):
        self.id = id

class Station:
    def __init__(self, env, id, processing_time_s, availability, mttr_s, power_working_kw, power_idle_kw, buffer_in, buffer_out):
        self.env = env
        self.id = id
        self.processing_time_s = processing_time_s
        self.availability = availability
        self.mttr_s = mttr_s
        self.power_working_kw = power_working_kw
        self.power_idle_kw = power_idle_kw
        self.buffer_in = buffer_in
        self.buffer_out = buffer_out
        self.processing = False
        self.power_kw = power_idle_kw
        self.energy_kwh = 0.0
        self.failure_time = None
        self.is_operational = True
        self.processing_start_time = None
        self.parts_processed = 0

    def run(self):
        while True:
            # Wait for a part to arrive
            part = yield self.buffer_in.get()
            self.processing = True
            self.power_kw = self.power_working_kw
            self.processing_start_time = self.env.now

            # Simulate processing time
            yield self.env.timeout(self.processing_time_s)

            # Check if machine fails
            if self.is_operational and random.random() > self.availability:
                self.is_operational = False
                self.failure_time = self.env.now
                self.power_kw = self.power_idle_kw
                # Schedule repair
                repair_duration = self.mttr_s
                yield self.env.timeout(repair_duration)
                self.is_operational = True
                self.power_kw = self.power_working_kw

            # Part is now processed, move to next buffer
            yield self.buffer_out.put(part)

            self.parts_processed += 1
            self.processing = False
            self.power_kw = self.power_idle_kw

class Source:
    def __init__(self, env, inter_arrival_time_s, buffer_out):
        self.env = env
        self.inter_arrival_time_s = inter_arrival_time_s
        self.buffer_out = buffer_out
        self.part_count = 0

    def run(self):
        while True:
            # Create a new part
            part = Part(self.part_count)
            self.part_count += 1
            # Put part in output buffer
            yield self.buffer_out.put(part)
            # Wait for next part
            yield self.env.timeout(self.inter_arrival_time_s)

def run_simulation(replication):
    random.seed(replication)
    env = simpy.Environment()
    
    # Create buffers
    buffer_B0 = simpy.Store(env, capacity=6)
    buffer_B1 = simpy.Store(env, capacity=3)
    buffer_B2 = simpy.Store(env, capacity=3)
    buffer_B3 = simpy.Store(env, capacity=3)
    buffer_B4 = simpy.Store(env, capacity=3)
    sink = simpy.Store(env)
    
    # Create stations
    station_M1 = Station(env, 'M1', 100, 0.9258, 3206.25, 4.0, 0.4, buffer_B0, buffer_B1)
    station_M2 = Station(env, 'M2', 130, 0.9736, 2859.26, 5.0, 0.5, buffer_B1, buffer_B2)
    station_M3 = Station(env, 'M3', 90, 0.9469, 2882.82, 4.5, 0.45, buffer_B2, buffer_B3)
    station_M4 = Station(env, 'M4', 140, 1.0, 4800, 7.0, 0.7, buffer_B3, buffer_B4)
    station_M5 = Station(env, 'M5', 110, 0.9823, 1099.8, 5.5, 0.55, buffer_B4, sink)
    
    # Create source
    source = Source(env, 150, buffer_B0)
    
    # Start source process
    env.process(source.run())
    
    # Start stations
    env.process(station_M1.run())
    env.process(station_M2.run())
    env.process(station_M3.run())
    env.process(station_M4.run())
    env.process(station_M5.run())
    
    # Initialize tracking variables
    total_parts = 0
    total_energy = 0.0
    wip_samples = []
    wip_times = []
    warmup_end = 21600
    window_end = warmup_end + 432000
    
    # Sample WIP at intervals
    def sample_wip():
        while True:
            current_time = env.now
            if warmup_end <= current_time <= window_end:
                # Count parts in all buffers and in process
                in_buffers = sum(len(store.items) for store in [buffer_B0, buffer_B1, buffer_B2, buffer_B3, buffer_B4])
                in_process = sum(1 for s in [station_M1, station_M2, station_M3, station_M4, station_M5] if s.processing)
                blocked = 0  # Approximate blocked resources
                total_wip = in_buffers + in_process + blocked
                wip_samples.append(total_wip)
                wip_times.append(current_time)
            yield env.timeout(10)  # Sample every 10 seconds
            
    env.process(sample_wip())
    
    # Run simulation
    env.run(until=window_end)
    
    # Calculate throughput
    throughputs = []
    total_parts = len(sink.items)
    window_hours = 432000 / 3600
    throughput = total_parts / window_hours
    
    # Calculate WIP
    if len(wip_times) > 1:
        total_wip_time = 0.0
        for i in range(1, len(wip_times)):
            total_wip_time += wip_samples[i-1] * (wip_times[i] - wip_times[i-1])
        avg_wip = total_wip_time / 432000
    else:
        avg_wip = 0.0
    
    # Calculate energy per part
    total_energy = (station_M1.energy_kwh + station_M2.energy_kwh + station_M3.energy_kwh + 
                    station_M4.energy_kwh + station_M5.energy_kwh)
    
    if total_parts > 0:
        energy_per_part = total_energy / total_parts
    else:
        energy_per_part = 0.0
    
    return (throughput, avg_wip, energy_per_part)

def main():
    # Run multiple replications
    results = []
    for i in range(10):
        throughput, wip, energy_per_part = run_simulation(i)
        results.append((throughput, wip, energy_per_part))
    
    # Calculate averages
    throughputs = [r[0] for r in results]
    wips = [r[1] for r in results]
    energy_per_parts = [r[2] for r in results]
    
    mean_throughput = statistics.mean(throughputs)
    mean_wip = statistics.mean(wips)
    mean_energy_per_part = statistics.mean(energy_per_parts)
    
    # Print results
    print(f"Throughput = {mean_throughput:.2f} parts/hour")
    print(f"WIP = {mean_wip:.2f} parts")
    print(f"Mean Energy Consumption per Part = {mean_energy_per_part:.6f} kWh/part")

if __name__ == '__main__':
    main()