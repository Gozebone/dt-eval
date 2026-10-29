import simpy
import random

class Part:
    def __init__(self, id):
        self.id = id

class Station:
    def __init__(self, env, id, processing_time_s, availability_pct, mttr_s, 
                 power_working_kw, power_idle_kw, buffer_in, buffer_out):
        self.env = env
        self.id = id
        self.processing_time_s = processing_time_s
        self.availability_pct = availability_pct
        self.mttr_s = mttr_s
        self.power_working_kw = power_working_kw
        self.power_idle_kw = power_idle_kw
        self.buffer_in = buffer_in
        self.buffer_out = buffer_out
        self.working = False
        self.failures = 0
        self.repair_time = 0
        self.total_energy = 0
        self.parts_processed = 0
        
    def run(self):
        while True:
            # Wait for a part to arrive
            part = yield self.buffer_in.get()
            
            # Check if machine is available
            if self.availability_pct < 100:
                # Simulate availability
                if random.random() > self.availability_pct / 100:
                    # Machine fails
                    self.failures += 1
                    # Schedule repair
                    yield self.env.timeout(self.mttr_s)
                    # Repair completed
                    self.repair_time += self.mttr_s
                else:
                    # Machine works normally
                    yield self.env.timeout(self.processing_time_s)
                    self.parts_processed += 1
            else:
                # Machine always available
                yield self.env.timeout(self.processing_time_s)
                self.parts_processed += 1
            
            # Add energy consumption
            self.total_energy += self.power_working_kw * (self.processing_time_s / 3600)
            
            # Send part to next buffer
            if self.buffer_out is not None:
                yield self.buffer_out.put(part)

class Source:
    def __init__(self, env, inter_arrival_time_s, buffer_out):
        self.env = env
        self.inter_arrival_time_s = inter_arrival_time_s
        self.buffer_out = buffer_out
        self.part_count = 0
        
    def run(self):
        while True:
            # Create new part
            self.part_count += 1
            part = Part(self.part_count)
            yield self.buffer_out.put(part)
            
            # Wait for next arrival
            yield self.env.timeout(self.inter_arrival_time_s)

def run_simulation(seed):
    random.seed(seed)
    
    # Simulation parameters
    warmup_s = 21600
    window_s = 432000
    horizon_s = warmup_s + window_s
    
    # Set up environment
    env = simpy.Environment()
    
    # Create buffers
    B0 = simpy.Store(env, capacity=15)
    B1 = simpy.Store(env, capacity=5)
    B2 = simpy.Store(env, capacity=5)
    
    # Create stations
    M1 = Station(env, "M1", 90, 99, 600, 3.0, 0.3, B0, B1)
    M2 = Station(env, "M2", 70, 98, 900, 4.5, 0.45, B1, B2)
    M3 = Station(env, "M3", 110, 99, 1200, 6.0, 0.6, B2, None)
    
    # Create source
    source = Source(env, 60, B0)
    
    # Start processes
    env.process(source.run())
    env.process(M1.run())
    env.process(M2.run())
    env.process(M3.run())
    
    # Track metrics
    parts_produced = 0
    total_energy = 0
    wip_samples = []
    wip_times = []
    start_monitoring = False
    
    # Monitor WIP
    def monitor_wip():
        nonlocal start_monitoring
        while True:
            # Only start monitoring after warmup
            if env.now >= warmup_s:
                start_monitoring = True
                
            if start_monitoring:
                current_wip = sum(len(store.items) for store in [B0, B1, B2])
                # Add parts in process (this is a simplified tracking)
                current_wip += sum(1 for station in [M1, M2, M3] if station.working)
                wip_samples.append(current_wip)
                wip_times.append(env.now)
            
            yield env.timeout(10)
    
    # Monitor energy and throughput
    def monitor_metrics():
        nonlocal parts_produced, total_energy
        while True:
            # Only start monitoring after warmup
            if env.now >= warmup_s:
                # Update energy consumption
                total_energy += (M1.power_idle_kw + M2.power_idle_kw + M3.power_idle_kw) * (10 / 3600)
                # Add energy from working machines
                total_energy += (M1.power_working_kw * (M1.parts_processed / 3600)) if M1.parts_processed > 0 else 0
                total_energy += (M2.power_working_kw * (M2.parts_processed / 3600)) if M2.parts_processed > 0 else 0
                total_energy += (M3.power_working_kw * (M3.parts_processed / 3600)) if M3.parts_processed > 0 else 0
                
                # Update parts produced (only from M3)
                parts_produced += M3.parts_processed
                M3.parts_processed = 0  # reset for next measurement
            
            yield env.timeout(10)
    
    env.process(monitor_wip())
    env.process(monitor_metrics())
    
    # Run simulation
    env.run(until=horizon_s)
    
    # Calculate metrics
    throughput = parts_produced / (window_s / 3600)
    
    # Calculate WIP
    if len(wip_times) >= 2:
        wip_total = 0
        for i in range(len(wip_times) - 1):
            dt = wip_times[i+1] - wip_times[i]
            wip_total += wip_samples[i] * dt
        wip_avg = wip_total / window_s
    else:
        wip_avg = 0
    
    # Calculate energy per part
    if parts_produced > 0:
        energy_per_part = total_energy / parts_produced
    else:
        energy_per_part = 0
    
    return throughput, wip_avg, energy_per_part

# Run multiple replications
replications = 10
throughputs = []
wips = []
energies_per_part = []

for i in range(replications):
    seed = i + 1
    throughput, wip, energy_per_part = run_simulation(seed)
    throughputs.append(throughput)
    wips.append(wip)
    energies_per_part.append(energy_per_part)

# Calculate means
mean_throughput = sum(throughputs) / len(throughputs)
mean_wip = sum(wips) / len(wips)
mean_energy_per_part = sum(energies_per_part) / len(energies_per_part)

print(f"Throughput = {mean_throughput:.2f} parts/hour")
print(f"WIP = {mean_wip:.2f} parts")
print(f"Mean Energy Consumption per Part = {mean_energy_per_part:.4f} kWh/part")