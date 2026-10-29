import simpy
import random
import math
import statistics

# Simulation parameters
WARMUP_S = 21600
WINDOW_S = 432000
REPETITIONS = 10
SIMULATION_TIME = WARMUP_S + WINDOW_S

# Machine parameters
machines = {
    'M1': {'processing_time_s': 200, 'availability': 0.97, 'mttr_s': 900, 'work_power_kw': 5.0, 'idle_power_kw': 0.5},
    'M2': {'processing_time_s': 220, 'availability': 0.97, 'mttr_s': 1000, 'work_power_kw': 5.5, 'idle_power_kw': 0.55},
    'M3': {'processing_time_s': 240, 'availability': 0.96, 'mttr_s': 1200, 'work_power_kw': 6.0, 'idle_power_kw': 0.6},
    'M4': {'processing_time_s': 260, 'availability': 0.96, 'mttr_s': 1400, 'work_power_kw': 7.0, 'idle_power_kw': 0.7},
    'M5': {'processing_time_s': 230, 'availability': 0.97, 'mttr_s': 1100, 'work_power_kw': 6.5, 'idle_power_kw': 0.65},
    'M6': {'processing_time_s': 210, 'availability': 0.97, 'mttr_s': 1000, 'work_power_kw': 6.0, 'idle_power_kw': 0.6}
}

# Buffer parameters
buffers = {
    'B0': {'capacity': 10},
    'B1': {'capacity': 10},
    'B2': {'capacity': 10},
    'B3': {'capacity': 10},
    'B4': {'capacity': 10},
    'B5': {'capacity': 10}
}

# Source inter-arrival time
INTER_ARRIVAL_TIME_S = 300

class Machine:
    def __init__(self, env, id, processing_time_s, availability, mttr_s, work_power_kw, idle_power_kw):
        self.env = env
        self.id = id
        self.processing_time_s = processing_time_s
        self.availability = availability
        self.mttr_s = mttr_s
        self.work_power_kw = work_power_kw
        self.idle_power_kw = idle_power_kw
        self.is_operational = True
        self.power_kw = self.idle_power_kw
        self.processing_start_time = None
        self.processing_end_time = None
        self.failed = False
        self.failure_start_time = None
        self.failures = 0
        self.total_energy_kwh = 0.0
        self.energy_samples = []
    
    def process_part(self, part_id):
        self.processing_start_time = self.env.now
        self.power_kw = self.work_power_kw
        yield self.env.timeout(self.processing_time_s)
        self.processing_end_time = self.env.now
        self.power_kw = self.idle_power_kw
        self.total_energy_kwh += (self.processing_time_s / 3600.0) * self.work_power_kw
    
    def simulate_failure(self):
        while True:
            if self.is_operational:
                # Exponential time to failure
                time_to_failure = random.expovariate(1.0 / (self.processing_time_s / (1.0 - self.availability)))
                yield self.env.timeout(time_to_failure)
                self.is_operational = False
                self.failed = True
                self.failure_start_time = self.env.now
                self.power_kw = self.idle_power_kw
                # Exponential time to repair
                repair_time = random.expovariate(1.0 / self.mttr_s)
                yield self.env.timeout(repair_time)
                self.is_operational = True
                self.failed = False
                self.power_kw = self.idle_power_kw
            else:
                yield self.env.timeout(1)  # wait a bit to check again

class Buffer:
    def __init__(self, env, id, capacity):
        self.env = env
        self.id = id
        self.capacity = capacity
        self.parts = []
    
    def put(self, part_id):
        if len(self.parts) < self.capacity:
            self.parts.append(part_id)
            return True
        return False
    
    def get(self):
        if self.parts:
            return self.parts.pop(0)
        return None

class Source:
    def __init__(self, env, inter_arrival_time_s):
        self.env = env
        self.inter_arrival_time_s = inter_arrival_time_s
        self.parts_created = 0
    
    def generate_parts(self):
        while True:
            part_id = self.parts_created
            self.parts_created += 1
            yield self.env.timeout(self.inter_arrival_time_s)
            # Create new part
            yield self.env.process(self.env.process(self.create_part(part_id)))
    
    def create_part(self, part_id):
        pass

class ProductionLineSimulation:
    def __init__(self, env, machines, buffers, inter_arrival_time_s):
        self.env = env
        self.machines = {id: Machine(env, id, **params) for id, params in machines.items()}
        self.buffers = {id: Buffer(env, id, capacity) for id, capacity in buffers.items()}
        self.source = Source(env, inter_arrival_time_s)
        self.parts_produced = 0
        self.wip_timeseries = []
        self.wip_total = 0.0
        self.wip_count = 0
        self.total_energy_kwh = 0.0
        self.total_parts = 0
    
    def run(self):
        # Start all machines' failure simulations
        for machine in self.machines.values():
            self.env.process(machine.simulate_failure())
        
        # Start source
        self.env.process(self.source.generate_parts())
        
        # Run simulation
        while self.env.now < SIMULATION_TIME:
            yield self.env.timeout(1)  # Small time step for sampling WIP
            
            # Sample WIP
            if self.env.now >= WARMUP_S:
                current_wip = sum(len(buf.parts) for buf in self.buffers.values())
                self.wip_timeseries.append((self.env.now, current_wip))
                self.wip_total += current_wip
                self.wip_count += 1
            
            # Process parts through the line
            self.process_parts()
    
    def process_parts(self):
        # For simplicity, assume parts move in a serial fashion
        # In a real implementation, this would be more complex
        pass

def run_simulation(replication):
    random.seed(replication)
    env = simpy.Environment()
    
    # Initialize simulation
    sim = ProductionLineSimulation(env, machines, buffers, INTER_ARRIVAL_TIME_S)
    
    # Run simulation
    env.run(until=SIMULATION_TIME)
    
    # Calculate KPIs
    if sim.wip_count > 0:
        wip_avg = sim.wip_total / sim.wip_count
    else:
        wip_avg = 0
    
    # Calculate throughput
    throughput = sim.parts_produced / (WINDOW_S / 3600.0)
    
    # Calculate energy per part
    if sim.parts_produced > 0:
        energy_per_part = sim.total_energy_kwh / sim.parts_produced
    else:
        energy_per_part = 0.0
    
    return throughput, wip_avg, energy_per_part

def main():
    throughputs = []
    wips = []
    energy_per_part = []
    
    for i in range(REPETITIONS):
        results = run_simulation(i)
        throughputs.append(results[0])
        wips.append(results[1])
        energy_per_part.append(results[2])
    
    avg_throughput = statistics.mean(throughputs)
    avg_wip = statistics.mean(wips)
    avg_energy_per_part = statistics.mean(energy_per_part)
    
    print(f"Throughput = {avg_throughput:.2f} parts/hour")
    print(f"WIP = {avg_wip:.2f} parts")
    print(f"Mean Energy Consumption per Part = {avg_energy_per_part:.6f} kWh/part")

if __name__ == "__main__":
    main()