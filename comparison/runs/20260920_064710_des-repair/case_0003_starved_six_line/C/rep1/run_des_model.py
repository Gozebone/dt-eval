import simpy
import random
import math

# Simulation parameters
class Requirements:
    class Line:
        class Source:
            inter_arrival_time_s = 300
            
        class Stations:
            def __init__(self):
                self.M1 = {"id": "M1", "processing_time_s": 200, "availability_pct": 97, "mttr_s": 900, "power_working_kw": 5.0, "power_idle_kw": 0.5}
                self.M2 = {"id": "M2", "processing_time_s": 220, "availability_pct": 97, "mttr_s": 1000, "power_working_kw": 5.5, "power_idle_kw": 0.55}
                self.M3 = {"id": "M3", "processing_time_s": 240, "availability_pct": 96, "mttr_s": 1200, "power_working_kw": 6.0, "power_idle_kw": 0.6}
                self.M4 = {"id": "M4", "processing_time_s": 260, "availability_pct": 96, "mttr_s": 1400, "power_working_kw": 7.0, "power_idle_kw": 0.7}
                self.M5 = {"id": "M5", "processing_time_s": 230, "availability_pct": 97, "mttr_s": 1100, "power_working_kw": 6.5, "power_idle_kw": 0.65}
                self.M6 = {"id": "M6", "processing_time_s": 210, "availability_pct": 97, "mttr_s": 1000, "power_working_kw": 6.0, "power_idle_kw": 0.6}
                
        class Buffers:
            def __init__(self):
                self.B0 = {"id": "B0", "capacity": 10, "before": "source", "after": "M1"}
                self.B1 = {"id": "B1", "capacity": 10, "before": "M1", "after": "M2"}
                self.B2 = {"id": "B2", "capacity": 10, "before": "M2", "after": "M3"}
                self.B3 = {"id": "B3", "capacity": 10, "before": "M3", "after": "M4"}
                self.B4 = {"id": "B4", "capacity": 10, "before": "M4", "after": "M5"}
                self.B5 = {"id": "B5", "capacity": 10, "before": "M5", "after": "M6"}
                
        class Defects:
            rate = None
            
        source = Source()
        stations = Stations()
        buffers = Buffers()
        defects = Defects()
        
    class DesHorizon:
        warmup_s = 21600
        window_s = 432000
        replications = 10
        
    line = Line()
    des_horizon = DesHorizon()

class Part:
    def __init__(self, part_id):
        self.id = part_id

class Station:
    def __init__(self, env, id, processing_time_s, availability_pct, mttr_s, power_working_kw, power_idle_kw, buffer_before, buffer_after):
        self.env = env
        self.id = id
        self.processing_time_s = processing_time_s
        self.availability_pct = availability_pct
        self.mttr_s = mttr_s
        self.power_working_kw = power_working_kw
        self.power_idle_kw = power_idle_kw
        self.buffer_before = buffer_before
        self.buffer_after = buffer_after
        self.is_operational = True
        self.failure_start = None
        self.total_energy_consumed = 0.0
        self.energy_sampled = 0.0
        self.parts_processed = 0
        self.power_state = 'idle'
        
    def run(self):
        while True:
            # Wait for a part to arrive
            part = yield self.buffer_before.get()
            
            # Check if the station is operational
            if not self.is_operational:
                # Schedule repair
                yield self.env.timeout(self.mttr_s)
                self.is_operational = True
                
            # Process the part
            start_time = self.env.now
            yield self.env.timeout(self.processing_time_s)
            
            # Record energy consumption
            elapsed_time = self.env.now - start_time
            if self.power_state == 'working':
                self.total_energy_consumed += self.power_working_kw * elapsed_time / 3600.0
            else:
                self.total_energy_consumed += self.power_idle_kw * elapsed_time / 3600.0
                
            # Update power state for next cycle
            self.power_state = 'working'
            
            # Increment processed parts
            self.parts_processed += 1
            
            # Put the part in the next buffer
            yield self.buffer_after.put(part)

class Source:
    def __init__(self, env, inter_arrival_time_s, buffer_out):
        self.env = env
        self.inter_arrival_time_s = inter_arrival_time_s
        self.buffer_out = buffer_out
        self.part_counter = 0
        
    def run(self):
        while True:
            # Create a new part
            self.part_counter += 1
            part = Part(self.part_counter)
            
            # Put the part in the output buffer
            yield self.buffer_out.put(part)
            
            # Wait for the next arrival
            yield self.env.timeout(self.inter_arrival_time_s)

def run_simulation(seed):
    env = simpy.Environment()
    random.seed(seed)
    
    # Create buffers
    B0 = simpy.Store(env, capacity=Requirements.line.buffers.B0['capacity'])
    B1 = simpy.Store(env, capacity=Requirements.line.buffers.B1['capacity'])
    B2 = simpy.Store(env, capacity=Requirements.line.buffers.B2['capacity'])
    B3 = simpy.Store(env, capacity=Requirements.line.buffers.B3['capacity'])
    B4 = simpy.Store(env, capacity=Requirements.line.buffers.B4['capacity'])
    B5 = simpy.Store(env, capacity=Requirements.line.buffers.B5['capacity'])
    
    # Create stations
    M1 = Station(env, 
                 Requirements.line.stations.M1['id'],
                 Requirements.line.stations.M1['processing_time_s'],
                 Requirements.line.stations.M1['availability_pct'],
                 Requirements.line.stations.M1['mttr_s'],
                 Requirements.line.stations.M1['power_working_kw'],
                 Requirements.line.stations.M1['power_idle_kw'],
                 B0, B1)
    
    M2 = Station(env,
                 Requirements.line.stations.M2['id'],
                 Requirements.line.stations.M2['processing_time_s'],
                 Requirements.line.stations.M2['availability_pct'],
                 Requirements.line.stations.M2['mttr_s'],
                 Requirements.line.stations.M2['power_working_kw'],
                 Requirements.line.stations.M2['power_idle_kw'],
                 B1, B2)
    
    M3 = Station(env,
                 Requirements.line.stations.M3['id'],
                 Requirements.line.stations.M3['processing_time_s'],
                 Requirements.line.stations.M3['availability_pct'],
                 Requirements.line.stations.M3['mttr_s'],
                 Requirements.line.stations.M3['power_working_kw'],
                 Requirements.line.stations.M3['power_idle_kw'],
                 B2, B3)
    
    M4 = Station(env,
                 Requirements.line.stations.M4['id'],
                 Requirements.line.stations.M4['processing_time_s'],
                 Requirements.line.stations.M4['availability_pct'],
                 Requirements.line.stations.M4['mttr_s'],
                 Requirements.line.stations.M4['power_working_kw'],
                 Requirements.line.stations.M4['power_idle_kw'],
                 B3, B4)
    
    M5 = Station(env,
                 Requirements.line.stations.M5['id'],
                 Requirements.line.stations.M5['processing_time_s'],
                 Requirements.line.stations.M5['availability_pct'],
                 Requirements.line.stations.M5['mttr_s'],
                 Requirements.line.stations.M5['power_working_kw'],
                 Requirements.line.stations.M5['power_idle_kw'],
                 B4, B5)
    
    M6 = Station(env,
                 Requirements.line.stations.M6['id'],
                 Requirements.line.stations.M6['processing_time_s'],
                 Requirements.line.stations.M6['availability_pct'],
                 Requirements.line.stations.M6['mttr_s'],
                 Requirements.line.stations.M6['power_working_kw'],
                 Requirements.line.stations.M6['power_idle_kw'],
                 B5, simpy.Store(env))  # Sink
    
    # Create source
    source = Source(env, 
                    Requirements.line.source.inter_arrival_time_s,
                    B0)
    
    # Start processes
    env.process(source.run())
    env.process(M1.run())
    env.process(M2.run())
    env.process(M3.run())
    env.process(M4.run())
    env.process(M5.run())
    env.process(M6.run())
    
    # Run simulation
    env.run(until=Requirements.des_horizon.warmup_s + Requirements.des_horizon.window_s)
    
    # Calculate KPIs
    total_parts = M6.parts_processed
    total_energy = M1.total_energy_consumed + M2.total_energy_consumed + M3.total_energy_consumed + \
                   M4.total_energy_consumed + M5.total_energy_consumed + M6.total_energy_consumed
    
    # Calculate throughput (parts/hour)
    throughput = total_parts / (Requirements.des_horizon.window_s / 3600.0)
    
    # Calculate WIP (time average)
    # We'll calculate it by sampling the WIP count periodically
    wip_samples = []
    for i in range(100):  # Sample 100 times during the window
        time_point = Requirements.des_horizon.warmup_s + (i * Requirements.des_horizon.window_s / 99.0)
        wip_count = 0
        # Count parts in all stores
        wip_count += len(B0.items)
        wip_count += len(B1.items)
        wip_count += len(B2.items)
        wip_count += len(B3.items)
        wip_count += len(B4.items)
        wip_count += len(B5.items)
        wip_samples.append(wip_count)
    
    avg_wip = sum(wip_samples) / len(wip_samples)
    
    # Calculate energy per part
    if total_parts > 0:
        energy_per_part = total_energy / total_parts
    else:
        energy_per_part = 0.0
        
    return throughput, avg_wip, energy_per_part

# Main execution
if __name__ == "__main__":
    results = []
    for i in range(Requirements.des_horizon.replications):
        seed = i + 1
        throughput, wip, energy_per_part = run_simulation(seed)
        results.append((throughput, wip, energy_per_part))
    
    # Compute means
    total_throughput = sum(r[0] for r in results)
    total_wip = sum(r[1] for r in results)
    total_energy_per_part = sum(r[2] for r in results)
    
    mean_throughput = total_throughput / Requirements.des_horizon.replications
    mean_wip = total_wip / Requirements.des_horizon.replications
    mean_energy_per_part = total_energy_per_part / Requirements.des_horizon.replications
    
    print(f"Throughput = {mean_throughput:.2f} parts/hour")
    print(f"WIP = {mean_wip:.2f} parts")
    print(f"Mean Energy Consumption per Part = {mean_energy_per_part:.6f} kWh/part")