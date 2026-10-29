import simpy
import random
import statistics
from collections import Counter
 
RANDOM_SEED = 11

SIM_TIME = 453600          # given
WARMUP_SECONDS = 21600     # given
MEASURE_UNTIL = SIM_TIME
 

def production_wait_time(now: float) -> float:
    SEC_PER_DAY = 86400
    day = int((now // SEC_PER_DAY) % 7)     # 0=Mon ... 6=Sun
    time_of_day = now % SEC_PER_DAY
    # Weekday stop window: 16:00–24:00 (Mon–Fri)
    if day in (0, 1, 2, 3, 4):
        stop_start = 16 * 3600
        stop_end   = 24 * 3600
        if stop_start <= time_of_day < stop_end:
            return max(0.0, stop_end - time_of_day)
        return 0.0
    # Weekend: no stop windows
    return 0.0
   
def _has_free_capacity(buf):
    return getattr(buf, "capacity", None) is not None and len(buf.items) < buf.capacity

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
    def __init__(self, env, cap, delay):
        self.env = env
        self.delay = delay
        self.cap = cap
        self.store = simpy.Store(env, capacity=cap)
        self.tokens = simpy.Container(env, init=cap, capacity=cap)
        self._in_transit = 0

    def put(self, part):
        return self.env.process(self._delayed_put(part))

    def get(self):
        return self.env.process(self._get_and_release())

    @property
    def items(self):
        return self.store.items

    @property
    def capacity(self):
        return self.store.capacity

    def in_transit_count(self):
        return self._in_transit

    def free_capacity(self):
        return int(self.tokens.level)

    def _delayed_put(self, part):
        yield self.tokens.get(1)
        self._in_transit += 1
        try:
            yield self.env.timeout(self.delay)
            yield self.store.put(part)
        finally:
            self._in_transit -= 1

    def _get_and_release(self):
        part = yield self.store.get()
        yield self.tokens.put(1)
        return part

class Machine:
    def __init__(self, env, name, input_buffer, output_buffer, process_time,
                 availability, mttr, working_power, waiting_power,
                 defect_rate=None, defect_sink=None, capacity=1):
 
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
        for _ in range(capacity):
            env.process(self.run())
 
    def _breakdown_cycle(self):
        while True:
            t_up = random.expovariate(1.0 / self.mtbf)
            yield self.env.timeout(t_up)
            self.is_up = False
            t_repair = random.expovariate(1.0 / self.mttr)
            yield self.env.timeout(t_repair)
            self.failed_time_total += t_repair
            self.is_up = True
 
    def run(self):
        while True:
            with self.resource.request() as req:
                yield req
                part = None
                while part is None:
                    if self.is_up and len(self.input_buffer.items):
                        part = yield self.input_buffer.get()
                    else:
                        if self.is_up:
                            self.wait_input_time += 1
                        yield self.env.timeout(1)
 
                self.processed_count += 1
                self.active_count += 1
               
                w = production_wait_time(self.env.now)
                self.window_wait_time += w
                if w:
                    yield self.env.timeout(w)
 
                pt = self.process_time() if callable(self.process_time) else self.process_time
                remaining = pt
                while remaining > 0:
                    if not self.is_up:
                        yield self.env.timeout(1)
                    else:
                        yield self.env.timeout(1)
                        self.working_time += 1
                        remaining -= 1
 
            start_block = self.env.now
 
            if self.defect_rate is not None and self.defect_sink is not None:
                if random.random() < self.defect_rate:
                    part["defect"] = 1
                    yield self.defect_sink.put(part)
                else:
                    part["defect"] = 0
                    yield self.output_buffer.put(part)
            else:
                yield self.output_buffer.put(part)
 
            self.blocked_time += (self.env.now - start_block)
            self.active_count -= 1
 
    def waiting_energy_consumption(self):
        return self.waiting_power * (
            self.wait_input_time + self.failed_time_total +
            self.blocked_time + self.window_wait_time
        )
   
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

    # Buffers (all capacities 10 as specified; small delay to model transfer)
    B0 = DelayBuffer(env, cap=10, delay=1)  # raw -> M1
    B1 = DelayBuffer(env, cap=10, delay=1)  # M1 -> M2
    B2 = DelayBuffer(env, cap=10, delay=1)  # M2 -> parallel (M3/M4)
    B3 = DelayBuffer(env, cap=10, delay=1)  # parallel (M3/M4) -> M5
    B4 = DelayBuffer(env, cap=10, delay=1)  # M5 -> M6
    B5 = DelayBuffer(env, cap=10, delay=1)  # M6 -> sink

    # Raw input/sink (source/sink can be unbounded; but we keep explicit caps if desired)
    raw_input = simpy.Store(env)     # source (no capacity constraint)
    sink = simpy.Store(env)          # final sink (no capacity constraint)

    # Helper stores for parallel routing (bounded capacities)
    preM3 = simpy.Store(env, capacity=5)
    preM4 = simpy.Store(env, capacity=5)
    postM3 = simpy.Store(env, capacity=5)
    postM4 = simpy.Store(env, capacity=5)

    # Splitter from B2 to M3/M4 input buffers (even split)
    env.process(splitter(env, B2.store, preM3, preM4))

    # Machines (no defects)
    M1 = Machine(env, "M1", input_buffer=B0, output_buffer=B1,
        process_time=199.86, availability=98.77, mttr=1062.58,
        working_power=kwh_per_sec(5.00), waiting_power=kwh_per_sec(0.50),
    )

    M2 = Machine(env, "M2", input_buffer=B1, output_buffer=B2,
        process_time=220.09, availability=98.63, mttr=1184.73,
        working_power=kwh_per_sec(5.49), waiting_power=kwh_per_sec(0.55),
    )

    M3 = Machine(env, "M3", input_buffer=preM3, output_buffer=postM3,
        process_time=240.01, availability=99.78, mttr=314.75,
        working_power=kwh_per_sec(5.99), waiting_power=kwh_per_sec(0.59),
    )

    M4 = Machine(env, "M4", input_buffer=preM4, output_buffer=postM4,
        process_time=259.99, availability=98.85, mttr=1246.71,
        working_power=kwh_per_sec(6.99), waiting_power=kwh_per_sec(0.69),
    )

    # Merge outputs of M3/M4 into B3 (parallel section)
    merger(env, postM3, postM4, B3.store)

    M5 = Machine(env, "M5", input_buffer=B3, output_buffer=B4,
        process_time=230.13, availability=99.51, mttr=2129.84,
        working_power=kwh_per_sec(6.49), waiting_power=kwh_per_sec(0.64),
        defect_rate=0.0, defect_sink=None,
    )

    M6 = Machine(env, "M6", input_buffer=B4, output_buffer=B5,
        process_time=209.83, availability=98.98, mttr=2200.89,
        working_power=kwh_per_sec(6.00), waiting_power=kwh_per_sec(0.60),
        defect_rate=0.0, defect_sink=None,
    )

    machines_list = [M1, M2, M3, M4, M5, M6]

    # Forward from raw_input to B0 (B0 already capacity-limited)
    def raw_forwarder(env, src, dst):
        while True:
            p = yield src.get()
            yield dst.put(p)
    env.process(raw_forwarder(env, raw_input, B0))

    # Forward from B5 to final sink
    env.process(forwarder(env, B5.store, sink))

    env.process(part_generator(env, raw_input))

    env.run(until=warmup)

    for m in machines_list:
        reset_machine_stats(m)

    produced_count_before = len(sink.items)

    wip_samples = []
    delay_buffers = [B0, B1, B2, B3, B4, B5]

    def sample_wip(env):
        while True:
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
            "produced_parts": total_produced},
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
    runs = 10
    overall_results = []
    machine_results = {}
    bottleneck_results = []
    energy_per_part_list = []
 
    for i in range(runs):
        seed = RANDOM_SEED + i
        res = run_simulation(seed)
        overall_results.append(res["overall"])
        for machine_name, _data in res["bottleneck"]["top_3"]:
            bottleneck_results.append(machine_name)
        for mname, mdata in res["machine_energy"].items():
            machine_results.setdefault(mname, []).append(mdata)
        total_energy_run = sum(machine_results[mname][i]["total_energy"] for mname in machine_results)
        total_energy_kwh = total_energy_run
        produced_parts = overall_results[i]["produced_parts"]
        energy_per_part_list.append(total_energy_kwh / produced_parts if produced_parts > 0 else 0)
 
    mean_energy_per_part = statistics.mean(energy_per_part_list)
    mean_overall = {"throughput": statistics.mean(o["throughput"] for o in overall_results),
        "wip": statistics.mean(o["wip"] for o in overall_results)}
 
    print(f"\n=== Mean Overall KPIs over {runs} runs ===")
    print(f"Throughput = {mean_overall['throughput']:.2f} parts/hour")
    print(f"WIP = {mean_overall['wip']:.2f} parts")
    print(f"Mean Energy Consumption per Part = {mean_energy_per_part:.4f} kWh/part")
 
    bottleneck_counter = Counter(bottleneck_results)
    print("\n=== Bottleneck Frequency over runs ===")
    for machine, count in bottleneck_counter.items():
        print(f"{machine}: {count} times")