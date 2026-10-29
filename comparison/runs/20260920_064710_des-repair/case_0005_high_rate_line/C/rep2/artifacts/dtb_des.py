import simpy
import random

# Simulation parameters
class Requirements:
    class Line:
        class Source:
            inter_arrival_time_s = 45
        
        class Stations:
            def __init__(self):
                self.M1 = {
                    "id": "M1",
                    "processing_time_s": 60,
                    "availability_pct": 0.995,
                    "mttr_s": 300,
                    "power_working_kw": 3.0,
                    "power_idle_kw": 0.3
                }
                self.M2 = {
                    "id": "M2",
                    "processing_time_s": 80,
                    "availability_pct": 0.99,
                    "mttr_s": 600,
                    "power_working_kw": 5.0,
                    "power_idle_kw": 0.5
                }
                self.M3 = {
                    "id": "M3",
                    "processing_time_s": 70,
                    "availability_pct": 0.99,
                    "mttr_s": 600,
                    "power_working_kw": 4.5,
                    "power_idle_kw": 0.45
                }
                self.M4 = {
                    "id": "M4",
                    "processing_time_s": 75,
                    "availability_pct": 0.995,
                    "mttr_s": 300,
                    "power_working_kw": 4.0,
                    "power_idle_kw": 0.4
                }
                
        class Buffers:
            def __init__(self):
                self.B0 = {
                    "id": "B0",
                    "capacity": 25,
                    "before": "source",
                    "after": "M1"
                }
                self.B1 = {
                    "id": "B1",
                    "capacity": 10,
                    "before": "M1",
                    "after": "M2"
                }
                self.B2 = {
                    "id": "B2",
                    "capacity": 10,
                    "before": "M2",
                    "after": "M3"
                }
                self.B3 = {
                    "id": "B3",
                    "capacity": 10,
                    "before": "M3",
                    "after": "M4"
                }

        stations = [Stations().M1, Stations().M2, Stations().M3, Stations().M4]
        buffers = [Buffers().B0, Buffers().B1, Buffers().B2, Buffers().B3]
        source = Source()
        
    class DesHorizon:
        warmup_s = 21600
        window_s = 432000
        replications = 10

requirements = Requirements()

class Part:
    def __init__(self, id):
        self.id = id

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
        self.is_operational = True
        self.power_draw = 0.0
        self.total_energy_consumed = 0.0
        self.parts_processed = 0
        self.failure_events = []
        self.working = False
        self.last_start_time = 0.0
        self.processing = False

    def run(self):
        while True:
            # Wait for a part to arrive
            part = yield self.buffer_in.get()
            
            # Check if machine is operational
            if not self.is_operational:
                # Schedule repair
                yield self.env.timeout(self.mttr_s)
                self.is_operational = True
                self.working = False
                
            # Process the part
            start_processing = self.env.now
            yield self.env.timeout(self.processing_time_s)
            
            # Check for failure during processing
            if random.random() > self.availability_pct:
                # Failure occurred
                self.is_operational = False
                self.working = False
                # Record failure event
                self.failure_events.append((start_processing, self.env.now))
                # Wait for repair
                yield self.env.timeout(self.mttr_s)
                self.is_operational = True
                
            # Update energy consumption
            self.total_energy_consumed += (self.env.now - start_processing) * self.power_working_kw / 3600.0
            
            # Send part to next buffer
            if self.buffer_out is not None:
                yield self.buffer_out.put(part)
            
            # Increment processed parts
            self.parts_processed += 1

class Source:
    def __init__(self, env, inter_arrival_time_s, buffer_out):
        self.env = env
        self.inter_arrival_time_s = inter_arrival_time_s
        self.buffer_out = buffer_out
        self.part_counter = 0

    def run(self):
        while True:
            # Create new part
            self.part_counter += 1
            part = Part(self.part_counter)
            
            # Put part in buffer
            yield self.buffer_out.put(part)
            
            # Wait for next arrival
            yield self.env.timeout(self.inter_arrival_time_s)

class Sink:
    def __init__(self, env, buffer_in):
        self.env = env
        self.buffer_in = buffer_in
        self.parts_count = 0

    def run(self):
        while True:
            # Get part from buffer
            part = yield self.buffer_in.get()
            
            # Increment count
            self.parts_count += 1

def run_simulation(seed):
    random.seed(seed)
    
    # Initialize environment
    env = simpy.Environment()
    
    # Create buffers
    B0 = simpy.Store(env, capacity=requirements.Line.Buffers().B0["capacity"])
    B1 = simpy.Store(env, capacity=requirements.Line.Buffers().B1["capacity"])
    B2 = simpy.Store(env, capacity=requirements.Line.Buffers().B2["capacity"])
    B3 = simpy.Store(env, capacity=requirements.Line.Buffers().B3["capacity"])
    
    # Create stations
    M1 = Station(
        env,
        requirements.Line.Stations().M1["id"],
        requirements.Line.Stations().M1["processing_time_s"],
        requirements.Line.Stations().M1["availability_pct"],
        requirements.Line.Stations().M1["mttr_s"],
        requirements.Line.Stations().M1["power_working_kw"],
        requirements.Line.Stations().M1["power_idle_kw"],
        B0,
        B1
    )
    
    M2 = Station(
        env,
        requirements.Line.Stations().M2["id"],
        requirements.Line.Stations().M2["processing_time_s"],
        requirements.Line.Stations().M2["availability_pct"],
        requirements.Line.Stations().M2["mttr_s"],
        requirements.Line.Stations().M2["power_working_kw"],
        requirements.Line.Stations().M2["power_idle_kw"],
        B1,
        B2
    )
    
    M3 = Station(
        env,
        requirements.Line.Stations().M3["id"],
        requirements.Line.Stations().M3["processing_time_s"],
        requirements.Line.Stations().M3["availability_pct"],
        requirements.Line.Stations().M3["mttr_s"],
        requirements.Line.Stations().M3["power_working_kw"],
        requirements.Line.Stations().M3["power_idle_kw"],
        B2,
        B3
    )
    
    M4 = Station(
        env,
        requirements.Line.Stations().M4["id"],
        requirements.Line.Stations().M4["processing_time_s"],
        requirements.Line.Stations().M4["availability_pct"],
        requirements.Line.Stations().M4["mttr_s"],
        requirements.Line.Stations().M4["power_working_kw"],
        requirements.Line.Stations().M4["power_idle_kw"],
        B3,
        None  # Last station, no buffer out
    )
    
    # Create source and sink
    source = Source(env, requirements.Line.Source().inter_arrival_time_s, B0)
    sink = Sink(env, B3)  # Sink connected to last buffer
    
    # Start processes
    env.process(source.run())
    env.process(M1.run())
    env.process(M2.run())
    env.process(M3.run())
    env.process(M4.run())
    env.process(sink.run())
    
    # Run simulation
    env.run(until=requirements.DesHorizon.warmup_s + requirements.DesHorizon.window_s)
    
    # Return results
    return {
        "throughput": sink.parts_count,
        "energy_consumed": sum([M1.total_energy_consumed, M2.total_energy_consumed, M3.total_energy_consumed, M4.total_energy_consumed]),
        "parts_processed": M4.parts_processed
    }

# Run replications
results = []
for i in range(requirements.DesHorizon.replications):
    seed = i + 1
    result = run_simulation(seed)
    results.append(result)

# Calculate averages
total_throughput = sum(r["throughput"] for r in results)
total_energy = sum(r["energy_consumed"] for r in results)
total_parts = sum(r["parts_processed"] for r in results)

# Calculate final metrics
throughput = total_throughput / (requirements.DesHorizon.window_s / 3600)
wip = total_parts / requirements.DesHorizon.window_s
energy_per_part = total_energy / total_parts if total_parts > 0 else 0

print(f"Throughput = {throughput:.2f} parts/hour")
print(f"WIP = {wip:.2f} parts")
print(f"Mean Energy Consumption per Part = {energy_per_part:.6f} kWh/part")