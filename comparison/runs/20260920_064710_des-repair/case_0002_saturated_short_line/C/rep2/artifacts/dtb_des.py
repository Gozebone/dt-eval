import simpy
import random

# Global constants from requirements
WARMUP_S = 21600
WINDOW_S = 432000
REPLICATIONS = 10

# Machine data
MACHINES = {
    'M1': {
        'processing_time_s': 90,
        'availability': 0.99,
        'mttr_s': 600,
        'work_power_kw': 3.0,
        'idle_power_kw': 0.3
    },
    'M2': {
        'processing_time_s': 70,
        'availability': 0.98,
        'mttr_s': 900,
        'work_power_kw': 4.5,
        'idle_power_kw': 0.45
    },
    'M3': {
        'processing_time_s': 110,
        'availability': 0.99,
        'mttr_s': 1200,
        'work_power_kw': 6.0,
        'idle_power_kw': 0.6
    }
}

# Buffer data
BUFFERS = {
    'B0': 15,
    'B1': 5,
    'B2': 5
}

# Source inter-arrival time
SOURCE_INTER_ARRIVAL_S = 60

class Part:
    def __init__(self, id):
        self.id = id

class Machine:
    def __init__(self, env, id, processing_time_s, availability, mttr_s, work_power_kw, idle_power_kw, in_buffer, out_buffer):
        self.env = env
        self.id = id
        self.processing_time_s = processing_time_s
        self.availability = availability
        self.mttr_s = mttr_s
        self.work_power_kw = work_power_kw
        self.idle_power_kw = idle_power_kw
        self.in_buffer = in_buffer
        self.out_buffer = out_buffer
        self.is_operational = True
        self.power_draw = 0.0
        self.failures = 0
        self.total_energy_kwh = 0.0
        self.is_processing = False
        self.processing_start_time = 0.0
        self.power_samples = []
        self.repair_event = env.event()

    def run(self):
        while True:
            # Wait for a part to arrive
            part = yield self.in_buffer.get()

            # If not operational, wait until it is
            if not self.is_operational:
                yield self.repair_event

            self.is_processing = True
            self.processing_start_time = self.env.now
            self.power_draw = self.work_power_kw
            self.power_samples.append((self.env.now, self.power_draw))
            
            # Process the part
            yield self.env.timeout(self.processing_time_s)
            
            # Record energy draw for the processing time
            if self.env.now > self.processing_start_time:
                duration_h = (self.env.now - self.processing_start_time) / 3600.0
                self.total_energy_kwh += self.power_draw * duration_h

            # Mark as idle after processing
            self.power_draw = self.idle_power_kw
            self.is_processing = False

            # Put part in next buffer
            yield self.out_buffer.put(part)

    def break_machine(self):
        if self.is_operational and random.random() < 1 - self.availability:
            self.is_operational = False
            self.power_draw = self.idle_power_kw
            self.failures += 1
            duration = self.mttr_s
            self.repair_event = self.env.event()
            yield self.env.timeout(duration)
            self.is_operational = True
            self.repair_event.succeed()

    def sample_power(self):
        while True:
            yield self.env.timeout(1.0)  # Sample every second
            if self.is_processing:
                self.power_draw = self.work_power_kw
            else:
                self.power_draw = self.idle_power_kw
            self.power_samples.append((self.env.now, self.power_draw))

class Source:
    def __init__(self, env, out_buffer, inter_arrival_time_s):
        self.env = env
        self.out_buffer = out_buffer
        self.inter_arrival_time_s = inter_arrival_time_s
        self.part_count = 0

    def run(self):
        while True:
            self.part_count += 1
            part = Part(self.part_count)
            yield self.out_buffer.put(part)
            yield self.env.timeout(self.inter_arrival_time_s)

def run_simulation(replication_id):
    random.seed(replication_id)
    env = simpy.Environment()

    # Create buffers
    B0 = simpy.Store(env, capacity=BUFFERS['B0'])
    B1 = simpy.Store(env, capacity=BUFFERS['B1'])
    B2 = simpy.Store(env, capacity=BUFFERS['B2'])

    # Create stations
    M1 = Machine(env, 'M1', MACHINES['M1']['processing_time_s'], MACHINES['M1']['availability'],
                 MACHINES['M1']['mttr_s'], MACHINES['M1']['work_power_kw'], MACHINES['M1']['idle_power_kw'], None, B0)
    M2 = Machine(env, 'M2', MACHINES['M2']['processing_time_s'], MACHINES['M2']['availability'],
                 MACHINES['M2']['mttr_s'], MACHINES['M2']['work_power_kw'], MACHINES['M2']['idle_power_kw'], B0, B1)
    M3 = Machine(env, 'M3', MACHINES['M3']['processing_time_s'], MACHINES['M3']['availability'],
                 MACHINES['M3']['mttr_s'], MACHINES['M3']['work_power_kw'], MACHINES['M3']['idle_power_kw'], B1, B2)

    # Create source
    source = Source(env, B0, SOURCE_INTER_ARRIVAL_S)

    # Start processes
    env.process(source.run())
    env.process(M1.run())
    env.process(M2.run())
    env.process(M3.run())

    # Start power sampling
    env.process(M1.sample_power())
    env.process(M2.sample_power())
    env.process(M3.sample_power())

    # Track parts that exit the system
    exit_parts = []
    
    # Track WIP
    wip_samples = []
    
    # WIP sampling function
    def sample_wip():
        while True:
            total_parts = len(B0.items) + len(B1.items) + len(B2.items)
            wip_samples.append((env.now, total_parts))
            yield env.timeout(1.0)
    
    env.process(sample_wip())
    
    # Run simulation
    env.run(until=WARMUP_S + WINDOW_S)

    # Calculate throughput
    # Throughput is the number of parts that exit the system during the measurement window
    # Count parts that actually passed through the system
    parts_count = 0
    # We use a counter to track how many parts go through M3
    def count_exit():
        nonlocal parts_count
        while True:
            part = yield B2.get()
            parts_count += 1
            yield env.timeout(0)  # Just to make this a generator
    
    env.process(count_exit())
    
    # Let the simulation run for a bit more to count all parts that exit
    env.run(until=WARMUP_S + WINDOW_S)
    
    # For the accurate calculation, we need to use the part creation count
    # Subtract the warmup parts from the total created
    parts_created = source.part_count
    # But correctly tracking the parts that exit requires a more careful approach
    
    # Let's use a proper exit counter
    exit_counter = 0
    def track_exit():
        nonlocal exit_counter
        while True:
            part = yield B2.get()
            exit_counter += 1
            yield env.timeout(0)
    
    # Reset simulation with the exit tracking
    env = simpy.Environment()
    random.seed(replication_id)
    
    # Create buffers
    B0 = simpy.Store(env, capacity=BUFFERS['B0'])
    B1 = simpy.Store(env, capacity=BUFFERS['B1'])
    B2 = simpy.Store(env, capacity=BUFFERS['B2'])

    # Create stations
    M1 = Machine(env, 'M1', MACHINES['M1']['processing_time_s'], MACHINES['M1']['availability'],
                 MACHINES['M1']['mttr_s'], MACHINES['M1']['work_power_kw'], MACHINES['M1']['idle_power_kw'], None, B0)
    M2 = Machine(env, 'M2', MACHINES['M2']['processing_time_s'], MACHINES['M2']['availability'],
                 MACHINES['M2']['mttr_s'], MACHINES['M2']['work_power_kw'], MACHINES['M2']['idle_power_kw'], B0, B1)
    M3 = Machine(env, 'M3', MACHINES['M3']['processing_time_s'], MACHINES['M3']['availability'],
                 MACHINES['M3']['mttr_s'], MACHINES['M3']['work_power_kw'], MACHINES['M3']['idle_power_kw'], B1, B2)

    # Create source
    source = Source(env, B0, SOURCE_INTER_ARRIVAL_S)

    # Start processes
    env.process(source.run())
    env.process(M1.run())
    env.process(M2.run())
    env.process(M3.run())

    # Start power sampling
    env.process(M1.sample_power())
    env.process(M2.sample_power())
    env.process(M3.sample_power())

    # Start exit tracking
    exit_counter = 0
    def track_exit():
        nonlocal exit_counter
        while True:
            part = yield B2.get()
            exit_counter += 1
            yield env.timeout(0)
    
    env.process(track_exit())
    
    # Track WIP
    wip_samples = []
    
    # WIP sampling function
    def sample_wip():
        while True:
            total_parts = len(B0.items) + len(B1.items) + len(B2.items)
            wip_samples.append((env.now, total_parts))
            yield env.timeout(1.0)
    
    env.process(sample_wip())
    
    # Run simulation
    env.run(until=WARMUP_S + WINDOW_S)

    # Calculate throughput
    # Throughput is the number of parts that exit the system during the measurement window
    throughput_parts = exit_counter

    # Calculate average WIP
    total_wip = 0.0
    last_time = WARMUP_S
    for t, wip in wip_samples:
        if WARMUP_S <= t <= WARMUP_S + WINDOW_S:
            if t > last_time:
                total_wip += (t - last_time) * wip
            last_time = t
    # Add last interval
    if t > last_time:
        total_wip += (WARMUP_S + WINDOW_S - last_time) * wip
    wip = total_wip / WINDOW_S

    # Calculate energy per part
    total_energy_kwh = M1.total_energy_kwh + M2.total_energy_kwh + M3.total_energy_kwh
    if throughput_parts > 0:
        energy_per_part = total_energy_kwh / throughput_parts
    else:
        energy_per_part = 0.0

    # Calculate throughput in parts/hour
    window_duration_h = WINDOW_S / 3600.0
    throughput = throughput_parts / window_duration_h

    return throughput, wip, energy_per_part

def main():
    results = []
    for i in range(REPLICATIONS):
        throughput, wip, energy_per_part = run_simulation(i)
        results.append((throughput, wip, energy_per_part))
    
    # Compute means
    total_throughput = sum(r[0] for r in results)
    total_wip = sum(r[1] for r in results)
    total_energy_per_part = sum(r[2] for r in results)
    
    mean_throughput = total_throughput / REPLICATIONS
    mean_wip = total_wip / REPLICATIONS
    mean_energy_per_part = total_energy_per_part / REPLICATIONS
    
    print(f"Throughput = {mean_throughput:.2f} parts/hour")
    print(f"WIP = {mean_wip:.2f} parts")
    print(f"Mean Energy Consumption per Part = {mean_energy_per_part:.4f} kWh/part")

if __name__ == "__main__":
    main()