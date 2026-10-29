import simpy
import random
from collections import defaultdict

# Simulation parameters
des_horizon = {
    "warmup_s": 21600,
    "window_s": 432000,
    "replications": 10
}

# Equipment data from requirements.line
stations_data = [
    {
        "id": "M1",
        "processing_time_s": 90,
        "availability_pct": 99.0,
        "mttr_s": 600,
        "power_working_kw": 3.0,
        "power_idle_kw": 0.3
    },
    {
        "id": "M2",
        "processing_time_s": 70,
        "availability_pct": 98.0,
        "mttr_s": 900,
        "power_working_kw": 4.5,
        "power_idle_kw": 0.45
    },
    {
        "id": "M3",
        "processing_time_s": 110,
        "availability_pct": 99.0,
        "mttr_s": 1200,
        "power_working_kw": 6.0,
        "power_idle_kw": 0.6
    }
]

buffers_data = [
    {
        "id": "B0",
        "capacity": 15,
        "before": "source",
        "after": "M1"
    },
    {
        "id": "B1",
        "capacity": 5,
        "before": "M1",
        "after": "M2"
    },
    {
        "id": "B2",
        "capacity": 5,
        "before": "M2",
        "after": "M3"
    }
]

source_data = {
    "inter_arrival_time_s": 60
}

class Part:
    def __init__(self, part_id):
        self.id = part_id

class Station:
    def __init__(self, env, name, processing_time_s, availability_pct, mttr_s, power_working_kw, power_idle_kw, input_buffer, output_buffer):
        self.env = env
        self.name = name
        self.processing_time_s = processing_time_s
        self.availability_pct = availability_pct
        self.mttr_s = mttr_s
        self.power_working_kw = power_working_kw
        self.power_idle_kw = power_idle_kw
        self.input_buffer = input_buffer
        self.output_buffer = output_buffer
        self.is_operational = True
        self.power_draw = 0.0
        self.total_energy = 0.0
        self.processing_start = None
        self.processing_end = None
        self.is_processing = False
        self.processing_time = 0
        self.failure_count = 0
        self.repair_count = 0

    def run(self):
        while True:
            # Wait for a part to arrive
            part = yield self.input_buffer.get()
            
            # Check if the station is operational
            if not self.is_operational:
                # Schedule a repair event if not operational
                yield self.env.timeout(self.mttr_s)
                self.is_operational = True

            # Start processing
            self.is_processing = True
            self.processing_start = self.env.now
            yield self.env.timeout(self.processing_time_s)
            self.processing_end = self.env.now
            self.is_processing = False
            
            # Calculate energy consumed during processing
            self.total_energy += self.power_working_kw * (self.processing_time_s / 3600.0)
            
            # Send part to the next buffer
            yield self.output_buffer.put(part)

class Buffer:
    def __init__(self, env, name, capacity):
        self.env = env
        self.name = name
        self.capacity = capacity
        self.store = simpy.Store(env, capacity=capacity)

    def get(self):
        return self.store.get()

    def put(self, item):
        return self.store.put(item)

def source(env, inter_arrival_time_s, output_buffer, part_counter):
    part_id = 0
    while True:
        yield env.timeout(inter_arrival_time_s)
        part = Part(part_id)
        part_id += 1
        yield output_buffer.put(part)
        part_counter[0] += 1

def simulate_replication(replication_id):
    env = simpy.Environment()
    
    # Create buffers
    buffers = {}
    for buf_data in buffers_data:
        buffers[buf_data["id"]] = Buffer(env, buf_data["id"], buf_data["capacity"])
    
    # Create stations
    stations = {}
    for station_data in stations_data:
        station_name = station_data["id"]
        stations[station_name] = Station(
            env,
            station_name,
            station_data["processing_time_s"],
            station_data["availability_pct"],
            station_data["mttr_s"],
            station_data["power_working_kw"],
            station_data["power_idle_kw"],
            None,  # Will be set after buffers are created
            None   # Will be set after buffers are created
        )
    
    # Set up station input and output buffers according to topology
    # B0 -> M1
    # M1 -> B1 -> M2
    # M2 -> B2 -> M3
    # M3 -> sink (no buffer needed)
    
    # Connect buffers to stations
    # M1
    stations["M1"].input_buffer = buffers["B0"]
    stations["M1"].output_buffer = buffers["B1"]
    
    # M2
    stations["M2"].input_buffer = buffers["B1"]
    stations["M2"].output_buffer = buffers["B2"]
    
    # M3
    stations["M3"].input_buffer = buffers["B2"]
    # M3's output goes to a sink, not a buffer
    
    # Create sink buffer
    sink_buffer = simpy.Store(env)
    
    # Connect M3 output to sink
    stations["M3"].output_buffer = sink_buffer
    
    # Create source
    part_counter = [0]
    env.process(source(env, source_data["inter_arrival_time_s"], buffers["B0"].store, part_counter))
    
    # Start stations
    for station in stations.values():
        env.process(station.run())
    
    # Track WIP
    wip_values = []
    wip_sample_interval = 10
    
    # Track energy consumption
    total_energy = 0.0
    
    # Start WIP tracking
    def track_wip():
        while True:
            current_wip = sum(len(buffer.store.items) for buffer in buffers.values())
            # For parts in processing in stations
            for station in stations.values():
                if station.is_processing:
                    current_wip += 1
            wip_values.append((env.now, current_wip))
            yield env.timeout(wip_sample_interval)
    
    env.process(track_wip())
    
    # Run simulation
    env.run(until=des_horizon["warmup_s"] + des_horizon["window_s"])
    
    # Calculate KPIs
    # Throughput
    throughput = part_counter[0] / (des_horizon["window_s"] / 3600.0)
    
    # WIP
    total_time = 0
    sum_wip = 0
    last_time = des_horizon["warmup_s"]
    for t, wip in wip_values:
        if t >= des_horizon["warmup_s"] and t <= des_horizon["warmup_s"] + des_horizon["window_s"]:
            total_time += (t - last_time)
            sum_wip += wip * (t - last_time)
            last_time = t
    wip = sum_wip / total_time if total_time > 0 else 0
    
    # Energy per part
    # Sum energy from all machines
    total_energy = sum(station.total_energy for station in stations.values())
    energy_per_part = total_energy / part_counter[0] if part_counter[0] > 0 else 0
    
    # Return KPIs
    return throughput, wip, energy_per_part

# Run replications
throughput_sum = 0
wip_sum = 0
energy_per_part_sum = 0

for i in range(des_horizon["replications"]):
    random.seed(i)
    throughput, wip, energy_per_part = simulate_replication(i)
    throughput_sum += throughput
    wip_sum += wip
    energy_per_part_sum += energy_per_part

# Calculate averages
avg_throughput = throughput_sum / des_horizon["replications"]
avg_wip = wip_sum / des_horizon["replications"]
avg_energy_per_part = energy_per_part_sum / des_horizon["replications"]

# Print results
print(f"Throughput = {avg_throughput:.2f} parts/hour")
print(f"WIP = {avg_wip:.2f} parts")
print(f"Mean Energy Consumption per Part = {avg_energy_per_part:.6f} kWh/part")