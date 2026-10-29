import simpy
import random
import math
from collections import defaultdict
import statistics

# Simulation parameters from requirements
des_horizon = {
    "warmup_s": 21600,
    "window_s": 432000,
    "replications": 10
}

line = {
    "topology": "serial",
    "source": {
        "inter_arrival_time_s": 60
    },
    "stations": [
        {
            "id": "M1",
            "processing_time_s": 90,
            "availability_pct": 0.99,
            "mttr_s": 600,
            "power_working_kw": 3.0,
            "power_idle_kw": 0.3
        },
        {
            "id": "M2",
            "processing_time_s": 70,
            "availability_pct": 0.98,
            "mttr_s": 900,
            "power_working_kw": 4.5,
            "power_idle_kw": 0.45
        },
        {
            "id": "M3",
            "processing_time_s": 110,
            "availability_pct": 0.99,
            "mttr_s": 1200,
            "power_working_kw": 6.0,
            "power_idle_kw": 0.6
        }
    ],
    "buffers": [
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
}

# KPI storage
throughputs = []
wips = []
energy_per_part = []

# WIP sampling interval
wip_sample_interval = 10

class Part:
    def __init__(self, id):
        self.id = id
        self.arrival_time = None
        self.departure_time = None

class Station:
    def __init__(self, env, id, processing_time_s, availability_pct, mttr_s, power_working_kw, power_idle_kw):
        self.env = env
        self.id = id
        self.processing_time_s = processing_time_s
        self.availability_pct = availability_pct
        self.mttr_s = mttr_s
        self.power_working_kw = power_working_kw
        self.power_idle_kw = power_idle_kw
        self.is_operational = True
        self.processing_start_time = None
        self.energy_consumption = 0.0
        self.power_state = 'idle'  # 'idle' or 'working'
        self.failure_event = None

    def process_part(self, part):
        if not self.is_operational:
            return

        # Update power state to 'working'
        self.power_state = 'working'
        self.processing_start_time = self.env.now

        # Simulate processing time
        yield self.env.timeout(self.processing_time_s)

        # Update energy consumption - power during processing
        processing_duration = self.env.now - self.processing_start_time
        self.energy_consumption += self.power_working_kw * processing_duration / 3600.0

        # Update power state to 'idle'
        self.power_state = 'idle'

    def start_failure_process(self):
        # Generate random time until next failure based on availability
        if self.availability_pct is not None:
            # Probability of failure per second
            failure_rate = 1.0 - self.availability_pct
            time_to_failure = -math.log(random.random()) / failure_rate
            # Wait for failure to happen
            yield self.env.timeout(time_to_failure)
            # Fail the machine
            self.is_operational = False
            self.power_state = 'idle'
            self.energy_consumption += self.power_idle_kw * self.mttr_s / 3600.0
            # Schedule repair
            self.env.process(self.repair())

    def repair(self):
        yield self.env.timeout(self.mttr_s)
        self.is_operational = True
        self.power_state = 'idle'

class Buffer:
    def __init__(self, env, id, capacity):
        self.env = env
        self.id = id
        self.capacity = capacity
        self.parts = simpy.Store(env)

    def put(self, part):
        if len(self.parts.items) < self.capacity:
            self.parts.put(part)
            return True
        else:
            return False

    def get(self):
        if self.parts.items:
            return self.parts.get()
        else:
            return None

class Source:
    def __init__(self, env, inter_arrival_time_s):
        self.env = env
        self.inter_arrival_time_s = inter_arrival_time_s
        self.part_id = 0

    def generate_part(self):
        while True:
            yield self.env.timeout(self.inter_arrival_time_s)
            part = Part(self.part_id)
            part.arrival_time = self.env.now
            self.part_id += 1
            yield self.env.process(self.env.process(self.send_to_buffer(part)))

    def send_to_buffer(self, part):
        # Send to B0
        yield b0.put(part)

class Sink:
    def __init__(self, env):
        self.env = env
        self.parts = []
        self.energy_consumption = 0.0

    def receive_part(self, part):
        part.departure_time = self.env.now
        self.parts.append(part)

def run_simulation(replication_id):
    # Set seed for reproducibility
    random.seed(replication_id)
    env = simpy.Environment()
    global b0, b1, b2, source, sink, stations

    # Initialize buffers
    b0 = Buffer(env, 'B0', line['buffers'][0]['capacity'])
    b1 = Buffer(env, 'B1', line['buffers'][1]['capacity'])
    b2 = Buffer(env, 'B2', line['buffers'][2]['capacity'])

    # Initialize stations
    stations = {}
    for s in line['stations']:
        stations[s['id']] = Station(
            env,
            s['id'],
            s['processing_time_s'],
            s['availability_pct'],
            s['mttr_s'],
            s['power_working_kw'],
            s['power_idle_kw']
        )

    # Initialize source and sink
    source = Source(env, line['source']['inter_arrival_time_s'])
    sink = Sink(env)

    # Start source
    env.process(source.generate_part())

    # Start stations with failure simulation if applicable
    for station_id, station in stations.items():
        if station.availability_pct is not None:
            env.process(station.start_failure_process())

    # Connect stations in serial with buffers
    def station_process(station_id, buffer_before, buffer_after):
        station = stations[station_id]
        while True:
            # Wait for part from buffer_before
            part = yield buffer_before.get()
            if part is None:
                continue

            # Process part
            yield env.process(station.process_part(part))

            # Put part in buffer_after
            success = buffer_after.put(part)
            if not success:
                # Handle buffer full - this is a blocking condition
                # For simplicity, we assume it can always proceed
                pass

    # Start processes for stations
    for i, s in enumerate(line['stations']):
        buffer_before = b0 if i == 0 else b1 if i == 1 else b2
        buffer_after = b1 if i == 0 else b2 if i == 1 else None  # None for last station (sink)
        env.process(station_process(s['id'], buffer_before, buffer_after))

    # Process for last station going to sink
    def final_station_process():
        while True:
            part = yield b2.get()
            if part is None:
                continue
            sink.receive_part(part)

    env.process(final_station_process())

    # WIP tracking
    wip_times = []
    wip_values = []

    def track_wip():
        while True:
            # Calculate current WIP
            current_wip = len(b0.parts.items) + len(b1.parts.items) + len(b2.parts.items)
            for station in stations.values():
                if station.power_state == 'working':
                    current_wip += 1  # Part in process
            wip_values.append(current_wip)
            wip_times.append(env.now)
            yield env.timeout(wip_sample_interval)

    env.process(track_wip())

    # Run simulation
    env.run(until=des_horizon['warmup_s'] + des_horizon['window_s'])

    # Calculate KPIs
    # Throughput
    window_start = des_horizon['warmup_s']
    window_end = des_horizon['warmup_s'] + des_horizon['window_s']
    parts_in_window = [p for p in sink.parts if window_start <= p.departure_time <= window_end]
    throughput = len(parts_in_window) / (des_horizon['window_s'] / 3600.0)

    # WIP
    total_wip_time = 0.0
    for i in range(1, len(wip_times)):
        time_diff = wip_times[i] - wip_times[i-1]
        total_wip_time += wip_values[i-1] * time_diff
    wip = total_wip_time / des_horizon['window_s']

    # Energy consumption
    total_energy = 0.0
    for station in stations.values():
        total_energy += station.energy_consumption
    energy_per_part_value = total_energy / len(parts_in_window) if parts_in_window else 0.0

    return throughput, wip, energy_per_part_value

# Run all replications
for i in range(des_horizon['replications']):
    throughput, wip, energy = run_simulation(i)
    throughputs.append(throughput)
    wips.append(wip)
    energy_per_part.append(energy)

# Calculate mean values
mean_throughput = statistics.mean(throughputs)
mean_wip = statistics.mean(wips)
mean_energy_per_part = statistics.mean(energy_per_part)

print(f"Throughput = {mean_throughput:.2f} parts/hour")
print(f"WIP = {mean_wip:.2f} parts")
print(f"Mean Energy Consumption per Part = {mean_energy_per_part:.6f} kWh/part")