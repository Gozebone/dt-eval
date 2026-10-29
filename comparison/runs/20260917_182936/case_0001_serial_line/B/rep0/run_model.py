import simpy
import random
import statistics
from collections import Counter
 
RANDOM_SEED = 11

SIM_TIME = 691200          # given simulation time
WARMUP_SECONDS = 86400     # given warm-up
MEASURE_UNTIL = SIM_TIME
 

def production_wait_time(now: float) -> float:
    """
    7-day periodic schedule; here: always allowed to produce.
    """
    return 0.0
   
def _has_free_capacity(buf):
    # Works for both DelayBuffer and plain Store
    return (getattr(buf, "free_capacity", None) and buf.free_capacity() > 0) \
           or len(buf.items) < buf.capacity

def splitter(env, input_store, out1, out2):
    toggle = 0
    while True:
        part = yield input_store.get()
        first, second = (out1, out2) if toggle == 0 else (out2, out1)
        if _has_free_capacity(first):
            yield first.put(part)
            toggle ^= 1
        else:
            yield second.put(part)
 
def forwarder(env, src, dst):
    while True:
        part = yield src.get()
        yield dst.put(part)
 
def merger(env, a, b, out):
    env.process(forwarder(env, a, out))
    env.process(forwarder(env, b, out))
 
def reset_machine_stats(m):
    m.working_time = 0
    m.failed_time_total = 0
    m.wait_input_time = 0
    m.blocked_time = 0
    m.processed_count = 0
    m.window_wait_time = 0

class DelayBuffer:
    """Single store with a global capacity cap that includes in-transit + ready."""
    def __init__(self, env, cap, delay):
        self.env = env
        self.delay = delay
        self.cap = cap
        self.store = simpy.Store(env, capacity=cap)   # holds 'ready' items
        self.tokens = simpy.Container(env, init=cap, capacity=cap)  # global slots
        self._in_transit = 0

    # --- SimPy-like API so existing code continues to work ---

    def put(self, part):
        # returns an Event (so callers can 'yield' it), but reserves capacity up-front
        return self.env.process(self._delayed_put(part))

    def get(self):
        # returns an Event (so callers can 'yield' it)
        return self.env.process(self._get_and_release())

    @property
    def items(self):
        # behave like a Store: this is the 'ready' queue
        return self.store.items

    @property
    def capacity(self):
        # behave like a Store: nominal ready queue cap
        return self.store.capacity

    # --- Extras useful to you ---

    def in_transit_count(self):
        return self._in_transit

    def free_capacity(self):
        # true free slots across in-transit + ready
        return int(self.tokens.level)

    # --- internals ---

    def _delayed_put(self, part):
        # wait for a global slot
        yield self.tokens.get(1)
        self._in_transit += 1
        try:
            yield self.env.timeout(self.delay)
            # once delay elapses, the part moves into the ready queue
            yield self.store.put(part)
        finally:
            self._in_transit -= 1

    def _get_and_release(self):
        part = yield self.store.get()
        # when a consumer takes a ready part, the segment frees one global slot
        yield self.tokens.put(1)
        return part

class Machine:
    def __init__(self, env, name, input_buffer, output_buffer, process_time,
                 availability, mttr, working_power, waiting_power, defect_rate = None, defect_sink = None, capacity=1):
        """
        :param env: SimPy environment.
        :param name: Machine name.
        :param input_buffer: Input channel (simpy.Store).
        :param output_buffer: Output channel (simpy.Store).
        :param process_time: Constant processing time.
        :param availability: Percentage availability (below 100 may trigger breakdowns).
        :param mttr: Mean time to repair.
        :param working_power: Power consumption (per sec) while processing.
        :param waiting_power: Power consumption (per sec) when idle.
        :param capacity: Concurrency level.
        """
 
        self.env = env
        self.name = name
        self.input_buffer = input_buffer
        self.output_buffer = output_buffer
        self.process_time = process_time
        self.availability = availability
        self.mttr = mttr
        self.defect_rate = defect_rate
        self.defect_sink = defect_sink
        self.working_power = working_power
        self.waiting_power = waiting_power
        self.resource = simpy.Resource(env, capacity=capacity)
        self.is_up = True
 
        # Time tracking
        self.working_time = 0
        self.failed_time_total = 0
        self.wait_input_time = 0
        self.blocked_time = 0
        self.active_count = 0
        self.processed_count = 0
        self.window_wait_time = 0
 
        if availability < 100:
            avail_frac = availability / 100.0
            self.mtbf = mttr * (avail_frac / (1 - avail_frac))
            env.process(self._breakdown_cycle())
        else:
            self.mtbf = float('inf')
        # launch workers
        for _ in range(capacity):
            env.process(self.run())
 
    def _breakdown_cycle(self):
        while True:
            # up‐time
            t_up = random.expovariate(1.0 / self.mtbf)
            yield self.env.timeout(t_up)
            # go down
            self.is_up = False
            # repair
            t_repair = random.expovariate(1.0 / self.mttr)
            yield self.env.timeout(t_repair)
            self.failed_time_total += t_repair
            # back up
            self.is_up = True
 
    def run(self):
        while True:
            with self.resource.request() as req:
                yield req
                part = None
                while part is None:                   # loop until we get a part
                    if self.is_up and len(self.input_buffer.items):
                        part = yield self.input_buffer.get()
                    else:
                        if self.is_up:                # only tick starvation when up
                            self.wait_input_time += 1
                        yield self.env.timeout(1)     # tick; either no part or machine is down
 
                # track it
                self.processed_count += 1
                self.active_count += 1
               
                # respect shift schedule
                w = production_wait_time(self.env.now)
                self.window_wait_time += w
                if w:
                    yield self.env.timeout(w)
 
                pt = self.process_time() if callable(self.process_time) else self.process_time
                remaining = pt
                while remaining > 0:
                    if not self.is_up:
                        # you’re broken—wait (and accumulate waiting_time elsewhere)
                        yield self.env.timeout(1)
                    else:
                        # actually do 1 s of work
                        yield self.env.timeout(1)
                        self.working_time += 1
                        remaining -= 1
 
            # now part is processed, start timing any blocking
            start_block = self.env.now
 
            # route to defect or downstream
            if self.defect_rate is not None and self.defect_sink is not None:
                if random.random() < self.defect_rate:
                    part["defect"] = 1
                    yield self.defect_sink.put(part)
                else:
                    part["defect"] = 0
                    yield self.output_buffer.put(part)
            else:
                yield self.output_buffer.put(part)
 
            # record blocked time and free up the slot
            self.blocked_time += (self.env.now - start_block)
            self.active_count -= 1
 
    def waiting_energy_consumption(self):
        return self.waiting_power * (self.wait_input_time + self.failed_time_total + self.blocked_time + self.window_wait_time)
   
    def working_energy_consumption(self):
        return self.working_power * self.working_time
 
def part_generator(env, output_buffer):
    part_id = 0
    while True:
        part = {"id": part_id}
        yield output_buffer.put(part)
        part_id += 1
        yield env.timeout(1)
 
def kwh_per_sec(x):
    return x / 3600.0

def run_simulation(seed, warmup=WARMUP_SECONDS, measure_until=MEASURE_UNTIL):
    random.seed(seed)
    env = simpy.Environment()

    # Topology:
    #   Raw -> B0 -> M1 -> B1 -> splitter -> (B2 -> M2 -> B3) || (B2b -> M3 -> B4) -> merger -> B5 -> M4 -> sink
    #
    # Buffers (given capacities; here no transport delay, so delay=0):
    B0 = DelayBuffer(env, cap=20, delay=0)  # raw buffer
    B1 = DelayBuffer(env, cap=8,  delay=0)
    B2 = DelayBuffer(env, cap=8,  delay=0)
    B2b = DelayBuffer(env, cap=8, delay=0)   # parallel branch helper, same capacity as B2
    B3 = DelayBuffer(env, cap=8,  delay=0)
    B4 = DelayBuffer(env, cap=8,  delay=0)
    B5 = DelayBuffer(env, cap=8,  delay=0)   # buffer before final machine

    # Raw input and sinks
    raw_input = simpy.Store(env, capacity=20)  # match B0 capacity
    sink = simpy.Store(env, capacity=100000)   # final sink; large but defined

    # Parallel splitter: B1 -> (B2, B2b)
    env.process(splitter(env, B1, B2, B2b))

    # Merge outputs of parallel machines into B5.
    branch2_out = DelayBuffer(env, cap=8, delay=0)
    merger(env, B3, branch2_out, B5)

    # Machines (times in seconds, availability %, MTTR in seconds, energies in kWh/h converted to kWh/s):
    M1 = Machine(env, "M1", input_buffer=B0, output_buffer=B1,
        process_time=149.90, availability=99.45, mttr=793.67,
        working_power=kwh_per_sec(4.00), waiting_power=kwh_per_sec(0.40),
    )

    # Parallel section: M2 and M3
    M2 = Machine(env, "M2", input_buffer=B2, output_buffer=B3,
        process_time=120.50, availability=96.86, mttr=1053.95,
        working_power=kwh_per_sec(4.98), waiting_power=kwh_per_sec(0.49),
    )

    M3 = Machine(env, "M3", input_buffer=B2b, output_buffer=branch2_out,
        process_time=180.59, availability=99.03, mttr=4200.65,
        working_power=kwh_per_sec(5.97), waiting_power=kwh_per_sec(0.60),
    )

    # Final machine M4 (table’s M5) after merger buffer B5
    M4 = Machine(env, "M4", input_buffer=B5, output_buffer=sink,
        process_time=149.89, availability=99.56, mttr=641.17,
        working_power=kwh_per_sec(4.00), waiting_power=kwh_per_sec(0.39),
        defect_rate=0.0, defect_sink=None,
    )

    machines_list = [M1, M2, M3, M4]

    # Start part generation into raw_input, then route into B0 with its capacity
    env.process(part_generator(env, raw_input))

    def raw_to_B0(env, src, dst):
        while True:
            part = yield src.get()
            yield dst.put(part)
    env.process(raw_to_B0(env, raw_input, B0))

    # Run the model to fill pipelines/buffers and reach steady-state
    env.run(until=warmup)

    # Zero machine counters so everything after is measured stats
    for m in machines_list:
        reset_machine_stats(m)

    # Zero sinks for measured production counts
    produced_count_before = len(sink.items)

    wip_samples = []
    delay_buffers = [B0, B1, B2, B2b, B3, B4, B5, branch2_out]

    def sample_wip(env):
        while True:
            # WIP definition: items in delay buffers + items in process
            ready = sum(len(b.items) for b in delay_buffers)
            in_transit = sum(b.in_transit_count() for b in delay_buffers)
            in_machines = sum(m.active_count for m in machines_list)

            wip_samples.append(ready + in_transit + in_machines)
            yield env.timeout(60)

    env.process(sample_wip(env))

    env.run(until=measure_until)
    

    total_produced = len(sink.items) - produced_count_before
    hours = (measure_until - warmup) / 3600.0
    throughput = (total_produced / hours) if hours > 0 else 0.0
    avg_wip = statistics.mean(wip_samples) if wip_samples else 0.0
 
    result = {"overall": {
            "throughput": throughput,
            "wip": avg_wip,
            "produced_parts":total_produced},
        "machine_energy": {}}
 
    for m in machines_list:
        waiting_energy = m.waiting_energy_consumption()
        working_energy = m.working_energy_consumption()
        total_energy = waiting_energy + working_energy
        result["machine_energy"][m.name] = {
            "working_time": m.working_time,
            "waiting_time": m.failed_time_total + m.blocked_time,
            "working_energy": working_energy,
            "waiting_energy": waiting_energy,
            "total_energy": total_energy}
        
    bottleneck_data = {}
    for m in machines_list:
        m_th = m.processed_count / hours if hours > 0 else 0.0
        util = (m.working_time / (measure_until - warmup)) * 100.0 if (measure_until > warmup) else 0.0
        bottleneck_data[m.name] = {"throughput": m_th, "utilization": util, "processed_count": m.processed_count}

    result["bottleneck"] = {
        "top_3": sorted(bottleneck_data.items(), key=lambda kv: kv[1]["utilization"], reverse=True)[:3],
        "all": bottleneck_data
    }
    return result
 
if __name__ == "__main__":
    runs = 10   # user-defined replications
    overall_results = []
    machine_results = {}
    bottleneck_results = []
    energy_per_part_list = []
 
    for i in range(runs):
        seed = RANDOM_SEED + i  # Different seed for each run.
        res = run_simulation(seed)
        overall_results.append(res["overall"])
        for machine_name, _ in res["bottleneck"]["top_3"]:
            bottleneck_results.append(machine_name)
        for mname, mdata in res["machine_energy"].items():
            machine_results.setdefault(mname, []).append(mdata)
        # Compute mean energy consumption per produced part over all runs.
        total_energy_run = sum(machine_results[mname][i]["total_energy"] for mname in machine_results)
        total_energy_kwh = total_energy_run
        produced_parts = overall_results[i]["produced_parts"]
        energy_per_part_list.append(total_energy_kwh / produced_parts if produced_parts > 0 else 0)
 
    mean_energy_per_part = statistics.mean(energy_per_part_list)
    # Compute mean values for overall KPIs.
    mean_overall = {"throughput": statistics.mean(o["throughput"] for o in overall_results),
        "wip": statistics.mean(o["wip"] for o in overall_results)}
 
    print(f"\n=== Mean Overall KPIs over {runs} runs ===")
    print(f"Throughput = {mean_overall['throughput']:.2f} parts/hour")
    print(f"WIP = {mean_overall['wip']:.2f} parts")
    print(f"Mean Energy Consumption per Part = {mean_energy_per_part:.4f} kWh/part")
 
    # --- Bottleneck Aggregation ---
    bottleneck_counter = Counter(bottleneck_results)
    print("\n=== Bottleneck Frequency over runs ===")
    for machine, count in bottleneck_counter.items():
         print(f"{machine}: {count} times")