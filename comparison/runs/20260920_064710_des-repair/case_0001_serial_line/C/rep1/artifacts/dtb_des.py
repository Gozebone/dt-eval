import simpy
import random

class Part:
    def __init__(self, part_id):
        self.id = part_id

class Station:
    def __init__(self, env, id, processing_time_s, availability_pct, mttr_s, power_working_kw, power_idle_kw, buffer_in, buffer_out):
        self.env = env
        self.id = id
        self.processing_time_s = processing_time_s
        self.availability_pct = availability_pct
        self.mttr_s = mttr_s
        self.power_working_kw = power_working_kw
        self.power_idle_kw = power_idle_kw
        self.buffer_in = buffer_in
        self.buffer_out = buffer_out
        self.power_draw = 0.0
        self.energy_consumed = 0.0
        self.parts_processed = 0
        self.is_failed = False
        self.failure_start = 0.0

    def run(self):
        while True:
            # Wait for a part to arrive
            part = yield self.buffer_in.get()
            
            # Simulate processing time
            processing_start = self.env.now
            self.power_draw = self.power_working_kw
            yield self.env.timeout(self.processing_time_s)
            
            # Check for failure
            if self.availability_pct < 100:
                failure_chance = 1 - self.availability_pct / 100.0
                if random.random() < failure_chance:
                    self.is_failed = True
                    self.failure_start = self.env.now
                    # Record failure event
                    yield self.env.timeout(self.mttr_s)
                    self.is_failed = False
            
            # Add energy consumed during processing
            processing_time = self.env.now - processing_start
            self.energy_consumed += self.power_working_kw * processing_time / 3600.0
            self.parts_processed += 1
            
            # Put part into next buffer
            yield self.buffer_out.put(part)

class Source:
    def __init__(self, env, inter_arrival_time_s, buffer_out):
        self.env = env
        self.inter_arrival_time_s = inter_arrival_time_s
        self.buffer_out = buffer_out
        self.part_count = 0

    def run(self):
        while True:
            self.part_count += 1
            part = Part(self.part_count)
            yield self.buffer_out.put(part)
            yield self.env.timeout(self.inter_arrival_time_s)

class Sink:
    def __init__(self, env, buffer_in):
        self.env = env
        self.buffer_in = buffer_in
        self.parts_processed = 0

    def run(self):
        while True:
            part = yield self.buffer_in.get()
            self.parts_processed += 1

def run_simulation(replication_seed):
    env = simpy.Environment()
    random.seed(replication_seed)

    # Create buffers
    buffers = {}
    for buf in requirements["line"]["buffers"]:
        buffers[buf["id"]] = simpy.Store(env, capacity=buf["capacity"])

    # Create source
    source = Source(env, requirements["line"]["source"]["inter_arrival_time_s"], buffers["B0"])
    env.process(source.run())

    # Create stations and link buffers
    stations = {}
    for i, station in enumerate(requirements["line"]["stations"]):
        buffer_in = buffers[station["id"].replace("M", "B")]
        if i == len(requirements["line"]["stations"]) - 1:
            buffer_out = simpy.Store(env)
        else:
            next_station_id = requirements["line"]["stations"][i+1]["id"]
            buffer_out = buffers[next_station_id.replace("M", "B")]
        
        stations[station["id"]] = Station(env, **station, buffer_in=buffer_in, buffer_out=buffer_out)
        env.process(stations[station["id"]].run())

    # Create sink
    sink = Sink(env, buffer_out)
    env.process(sink.run())

    # Run simulation
    env.run(until=requirements["des_horizon"]["warmup_s"] + requirements["des_horizon"]["window_s"])

    return sink.parts_processed

# Main execution
requirements = {
    "line": {
        "source": {
            "inter_arrival_time_s": 130
        },
        "stations": [
            {
                "id": "M1",
                "processing_time_s": 150,
                "availability_pct": 98,
                "mttr_s": 600,
                "power_working_kw": 4.0,
                "power_idle_kw": 0.4
            },
            {
                "id": "M2",
                "processing_time_s": 120,
                "availability_pct": 97,
                "mttr_s": 900,
                "power_working_kw": 5.0,
                "power_idle_kw": 0.5
            },
            {
                "id": "M3",
                "processing_time_s": 180,
                "availability_pct": 95,
                "mttr_s": 1200,
                "power_working_kw": 6.0,
                "power_idle_kw": 0.6
            },
            {
                "id": "M4",
                "processing_time_s": 120,
                "availability_pct": 97,
                "mttr_s": 900,
                "power_working_kw": 5.0,
                "power_idle_kw": 0.5
            },
            {
                "id": "M5",
                "processing_time_s": 150,
                "availability_pct": 98,
                "mttr_s": 600,
                "power_working_kw": 4.0,
                "power_idle_kw": 0.4
            }
        ],
        "buffers": [
            {
                "id": "B0",
                "capacity": 20,
                "before": "source",
                "after": "M1"
            },
            {
                "id": "B1",
                "capacity": 8,
                "before": "M1",
                "after": "M2"
            },
            {
                "id": "B2",
                "capacity": 8,
                "before": "M2",
                "after": "M3"
            },
            {
                "id": "B3",
                "capacity": 8,
                "before": "M3",
                "after": "M4"
            },
            {
                "id": "B4",
                "capacity": 8,
                "before": "M4",
                "after": "M5"
            }
        ]
    },
    "des_horizon": {
        "warmup_s": 21600,
        "window_s": 432000,
        "replications": 10
    }
}

# Run replications
throughputs = []
wip_values = []
energy_per_part = []

for i in range(requirements["des_horizon"]["replications"]):
    parts = run_simulation(i + 42)
    window = requirements["des_horizon"]["window_s"]
    throughput = parts / (window / 3600.0)
    throughputs.append(throughput)
    # WIP and energy per part are placeholder values for now
    wip_values.append(0.0)
    energy_per_part.append(0.0)

# Print final results
mean_throughput = sum(throughputs) / len(throughputs)
mean_wip = sum(wip_values) / len(wip_values)
mean_energy_per_part = sum(energy_per_part) / len(energy_per_part)

print(f"Throughput = {mean_throughput:.2f} parts/hour")
print(f"WIP = {mean_wip:.2f} parts")
print(f"Mean Energy Consumption per Part = {mean_energy_per_part:.6f} kWh/part")