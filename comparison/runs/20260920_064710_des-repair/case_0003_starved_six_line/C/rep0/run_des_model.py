import simpy
import random

# Define the parameters from the requirements
class Requirements:
    line = {
        "source": {"inter_arrival_time_s": 300},
        "stations": [
            {
                "id": "M1",
                "processing_time_s": 200,
                "availability": 0.97,
                "mttr_s": 900,
                "work_power_kw": 5.0,
                "idle_power_kw": 0.5
            },
            {
                "id": "M2",
                "processing_time_s": 220,
                "availability": 0.97,
                "mttr_s": 1000,
                "work_power_kw": 5.5,
                "idle_power_kw": 0.55
            },
            {
                "id": "M3",
                "processing_time_s": 240,
                "availability": 0.96,
                "mttr_s": 1200,
                "work_power_kw": 6.0,
                "idle_power_kw": 0.6
            },
            {
                "id": "M4",
                "processing_time_s": 260,
                "availability": 0.96,
                "mttr_s": 1400,
                "work_power_kw": 7.0,
                "idle_power_kw": 0.7
            },
            {
                "id": "M5",
                "processing_time_s": 230,
                "availability": 0.97,
                "mttr_s": 1100,
                "work_power_kw": 6.5,
                "idle_power_kw": 0.65
            },
            {
                "id": "M6",
                "processing_time_s": 210,
                "availability": 0.97,
                "mttr_s": 1000,
                "work_power_kw": 6.0,
                "idle_power_kw": 0.6
            }
        ],
        "buffers": [
            {
                "id": "B0",
                "capacity": 10,
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
            },
            {
                "id": "B4",
                "capacity": 10,
                "before": "M4",
                "after": "M5"
            },
            {
                "id": "B5",
                "capacity": 10,
                "before": "M5",
                "after": "M6"
            }
        ]
    }
    
    des_horizon = {
        "warmup_s": 21600,
        "window_s": 432000,
        "replications": 10
    }

# Define part class
class Part:
    def __init__(self, part_id):
        self.id = part_id

# Define station class
class Station:
    def __init__(self, env, id, processing_time_s, availability, mttr_s, work_power_kw, idle_power_kw, buffer_before, buffer_after):
        self.env = env
        self.id = id
        self.processing_time_s = processing_time_s
        self.availability = availability
        self.mttr_s = mttr_s
        self.work_power_kw = work_power_kw
        self.idle_power_kw = idle_power_kw
        self.buffer_before = buffer_before
        self.buffer_after = buffer_after
        self.store = simpy.Store(env)
        self.is_operational = True
        self.power_draw = 0.0
        self.failure_start = None
        self.failure_duration = 0.0
        self.total_energy = 0.0
        self.active = False
        self.failure_event = None

    def run(self):
        while True:
            # Wait for a part to arrive
            part = yield self.store.get()
            
            # Check if the station is operational
            if not self.is_operational:
                # If not operational, wait until it becomes operational again
                yield self.env.timeout(self.mttr_s)
                self.is_operational = True
                
            # Process the part
            start_time = self.env.now
            yield self.env.timeout(self.processing_time_s)
            
            # Check if the station fails during processing
            if self.availability < 1.0 and random.random() > self.availability:
                # Fail the station
                self.is_operational = False
                failure_duration = self.mttr_s
                self.failure_start = self.env.now
                yield self.env.timeout(failure_duration)
                self.is_operational = True
                self.failure_duration += failure_duration
            
            # Record energy consumption
            end_time = self.env.now
            processing_time = end_time - start_time
            if self.is_operational:
                self.power_draw = self.work_power_kw
            else:
                self.power_draw = self.idle_power_kw
            self.total_energy += self.power_draw * processing_time / 3600.0  # Convert to kWh

            # Pass part to next buffer
            yield self.buffer_after.put(part)

# Define source class
class Source:
    def __init__(self, env, inter_arrival_time_s, buffer):
        self.env = env
        self.inter_arrival_time_s = inter_arrival_time_s
        self.buffer = buffer
        self.part_counter = 0

    def run(self):
        while True:
            # Create a new part
            self.part_counter += 1
            part = Part(self.part_counter)
            
            # Put part into the first buffer
            yield self.buffer.put(part)
            
            # Wait for next arrival
            yield self.env.timeout(self.inter_arrival_time_s)

# Run simulation
def run_simulation(seed):
    env = simpy.Environment()
    random.seed(seed)
    
    # Create buffers
    buffers = {}
    for buf in Requirements.line["buffers"]:
        buffers[buf["id"]] = simpy.Store(env, capacity=buf["capacity"])
    
    # Create source
    source_buffer = buffers["B0"]
    source = Source(env, Requirements.line["source"]["inter_arrival_time_s"], source_buffer)
    env.process(source.run())
    
    # Create stations
    stations = {}
    for i, station_data in enumerate(Requirements.line["stations"]):
        station_id = station_data["id"]
        before_buffer_id = Requirements.line["buffers"][i]["before"]
        after_buffer_id = Requirements.line["buffers"][i]["after"]
        
        # Special handling for the source buffer
        if before_buffer_id == "source":
            before_buffer = source_buffer
        else:
            before_buffer = buffers[before_buffer_id]
            
        after_buffer = buffers[after_buffer_id]
        
        station = Station(
            env,
            station_id,
            station_data["processing_time_s"],
            station_data["availability"],
            station_data["mttr_s"],
            station_data["work_power_kw"],
            station_data["idle_power_kw"],
            before_buffer,
            after_buffer
        )
        stations[station_id] = station
        
        # Connect buffers to stations
        env.process(station.run())
    
    # Create sink (last buffer)
    sink = simpy.Store(env)
    
    # Connect last buffer to sink
    env.process(connect_buffer_to_sink(env, buffers["B5"], sink))
    
    # Track metrics
    throughput_count = 0
    wip_total = 0.0
    wip_samples = 0
    total_energy = 0.0
    
    # Sample WIP every 10 seconds
    def sample_wip():
        nonlocal wip_total, wip_samples
        while True:
            yield env.timeout(10)
            wip = sum(len(buf.items) for buf in buffers.values())
            wip_total += wip * 10
            wip_samples += 1
    
    # Start sampling
    env.process(sample_wip())
    
    # Warm-up period
    env.run(until=Requirements.des_horizon["warmup_s"])
    
    # Reset counters for measurement period
    throughput_count = 0
    wip_total = 0.0
    wip_samples = 0
    total_energy = 0.0
    
    # Measurement period
    start_time = env.now
    while env.now < start_time + Requirements.des_horizon["window_s"]:
        # Sample WIP
        wip = sum(len(buf.items) for buf in buffers.values())
        wip_total += wip * (env.now - start_time)
        wip_samples += 1
        
        # Update energy
        for station in stations.values():
            total_energy += station.total_energy
        
        # Process events
        yield env.timeout(10)  # Sample every 10 seconds
    
    # Final WIP sample
    wip = sum(len(buf.items) for buf in buffers.values())
    wip_total += wip * (env.now - start_time)
    wip_samples += 1
    
    # Count parts that left the system
    throughput_count = len(sink.items)
    
    # Calculate final metrics
    window_hours = Requirements.des_horizon["window_s"] / 3600.0
    throughput = throughput_count / window_hours
    
    avg_wip = wip_total / Requirements.des_horizon["window_s"] if wip_samples > 0 else 0
    
    energy_per_part = total_energy / throughput_count if throughput_count > 0 else 0
    
    return throughput, avg_wip, energy_per_part

def connect_buffer_to_sink(env, buffer, sink):
    while True:
        part = yield buffer.get()
        yield sink.put(part)

# Run all replications
throughputs = []
wips = []
energy_per_parts = []

for i in range(Requirements.des_horizon["replications"]):
    seed = i + 1
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