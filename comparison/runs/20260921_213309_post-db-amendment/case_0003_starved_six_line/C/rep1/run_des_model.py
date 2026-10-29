import random

import simpy

# --- BEGIN PARAMETERS ---
# Adapt ONLY this block to the production line in the requirements. The code
# below the block is the model, and it already computes the KPIs correctly.
#
# STATIONS: one entry per station in requirements.line.stations, in flow order.
#   processing_time_s   the station's processing time, in seconds
#   availability_pct    availability in percent (100 = never fails)
#   mttr_s              mean time to repair, in seconds
#   power_working_kw    power drawn while processing a part
#   power_idle_kw       power drawn while waiting for a part
# BUFFERS: one entry per buffer in requirements.line.buffers. BUFFERS[i] is the
#   buffer that FEEDS STATIONS[i]: BUFFERS[0] receives from the source and
#   BUFFERS[i] (i > 0) receives from STATIONS[i-1]. The last station discharges
#   into the sink.
STATIONS = [
    {"id": "M1", "processing_time_s": 199.86, "availability_pct": 98.77,
     "mttr_s": 1062.58, "power_working_kw": 5.0, "power_idle_kw": 0.5},
    {"id": "M2", "processing_time_s": 220.09, "availability_pct": 98.63,
     "mttr_s": 1184.73, "power_working_kw": 5.49, "power_idle_kw": 0.55},
    {"id": "M3", "processing_time_s": 240.01, "availability_pct": 99.78,
     "mttr_s": 314.75, "power_working_kw": 5.99, "power_idle_kw": 0.59},
    {"id": "M4", "processing_time_s": 259.99, "availability_pct": 98.85,
     "mttr_s": 1246.71, "power_working_kw": 6.99, "power_idle_kw": 0.69},
    {"id": "M5", "processing_time_s": 230.13, "availability_pct": 99.51,
     "mttr_s": 2129.84, "power_working_kw": 6.49, "power_idle_kw": 0.64},
    {"id": "M6", "processing_time_s": 209.83, "availability_pct": 98.98,
     "mttr_s": 2200.89, "power_working_kw": 6.0, "power_idle_kw": 0.6},
]
BUFFERS = [10, 10, 10, 10, 10, 10]
INTER_ARRIVAL_S = 300.0   # one part every INTER_ARRIVAL_S seconds
WARMUP_S = 21600.0       # requirements.des_horizon.warmup_s
WINDOW_S = 432000.0      # requirements.des_horizon.window_s
REPLICATIONS = 10        # requirements.des_horizon.replications
# --- END PARAMETERS ---


class Sink:
    """Collects finished parts. A list, not a store: the sink never blocks."""

    def __init__(self):
        self.left_at = []

    def take(self, now):
        self.left_at.append(now)


class Ledger:
    """Integrates the whole-system WIP and power draw over the measurement window.

    WIP and power are piecewise constant and change only at events, so every
    event that moves a part or changes a station's state calls `sync` *before*
    the change: the span since the previous sync is credited to the state that
    actually held during it. Nothing is sampled, so a state shorter than any
    sampling interval still contributes exactly its own duration. Spans before
    the warm-up boundary are discarded, which is what makes warm-up free.
    """

    def __init__(self, buffers):
        self.buffers = buffers
        self.stations = []
        self.wip_area = 0.0        # part-seconds
        self.energy_area = 0.0     # kWh
        self._t = 0.0

    def wip(self):
        return (sum(len(b.items) for b in self.buffers)
                + sum(s.in_process for s in self.stations))

    def power(self):
        return sum(s.power() for s in self.stations)

    def sync(self, now):
        lo = max(self._t, WARMUP_S)
        if now > lo:
            span = now - lo
            self.wip_area += self.wip() * span
            self.energy_area += self.power() * span / 3600.0
        self._t = now


class Station:
    """One machine: pull a part from its input buffer, process it, push it on.

    `state` is what the station is doing; `operational` is whether it is up at
    all, so a breakdown that starts mid-part still cuts the power draw.
    """

    def __init__(self, env, spec, input_buffer, output, ledger):
        self.env = env
        self.id = spec["id"]
        self.processing_time_s = float(spec["processing_time_s"])
        self.mttr_s = spec.get("mttr_s")
        self.power_working_kw = spec.get("power_working_kw") or 0.0
        self.power_idle_kw = spec.get("power_idle_kw") or 0.0
        self.input_buffer = input_buffer
        self.output = output
        self.is_sink = isinstance(output, Sink)
        self.ledger = ledger

        pct = spec.get("availability_pct")
        self.failure_scale = None
        if pct is not None and self.mttr_s and 0.0 < float(pct) < 100.0:
            # availability = mttf / (mttf + mttr)
            self.failure_scale = float(self.mttr_s) * float(pct) / (
                100.0 - float(pct))

        self.operational = True
        self.state = "idle"        # idle | working
        self.in_process = 0        # parts currently held by this station
        self.down_until = 0.0      # clock time at which the current repair ends

    def power(self):
        if not self.operational:
            return 0.0
        return (self.power_working_kw if self.state == "working"
                else self.power_idle_kw)

    def sync(self):
        self.ledger.sync(self.env.now)

    def breakdowns(self):
        """Fail and repair, repeatedly, drawn from availability and MTTR.

        A renewal process: the time to the next failure is exponential with
        mean mttf = mttr * p / (1 - p), so the long-run availability is the
        declared `availability_pct`, and the repair then takes exactly the
        declared `mttr_s`. A failure never interrupts a part already in process
        — it delays the next one.
        """
        while True:
            yield self.env.timeout(random.expovariate(1.0 / self.failure_scale))
            if not self.operational:
                continue
            self.sync()
            self.operational = False
            self.down_until = self.env.now + float(self.mttr_s)
            yield self.env.timeout(float(self.mttr_s))
            self.sync()
            self.operational = True

    def run(self):
        while True:
            part = yield self.input_buffer.get()
            self.sync()
            self.in_process += 1
            self.state = "idle"
            if not self.operational:
                # A repair is under way; wait for the current one to finish.
                yield self.env.timeout(max(0.0, self.down_until - self.env.now))
            self.sync()
            self.state = "working"
            yield self.env.timeout(self.processing_time_s)
            self.sync()
            self.state = "idle"
            self.in_process -= 1
            if self.is_sink:
                self.output.take(self.env.now)
            else:
                yield self.output.put(part)


def source(env, entry_buffer, inter_arrival_s, ledger):
    part_id = 0
    while True:
        part_id += 1
        ledger.sync(env.now)          # the part joins the system here
        yield entry_buffer.put(part_id)
        yield env.timeout(inter_arrival_s)


def run_replication(seed):
    random.seed(seed)
    env = simpy.Environment()
    buffers = [simpy.Store(env, capacity=int(c)) for c in BUFFERS]
    sink = Sink()
    ledger = Ledger(buffers)
    for i, spec in enumerate(STATIONS):
        output = sink if i == len(STATIONS) - 1 else buffers[i + 1]
        ledger.stations.append(Station(env, spec, buffers[i], output, ledger))
    for st in ledger.stations:
        env.process(st.run())
        if st.failure_scale:
            env.process(st.breakdowns())
    env.process(source(env, buffers[0], INTER_ARRIVAL_S, ledger))

    env.run(until=WARMUP_S + WINDOW_S)
    ledger.sync(env.now)

    parts = sum(1 for t in sink.left_at if t >= WARMUP_S)
    throughput = parts / (WINDOW_S / 3600.0)
    wip_avg = ledger.wip_area / WINDOW_S
    # Energy per part divides the energy consumed inside the window by the
    # parts produced inside the same window, so warm-up cannot bias the ratio.
    energy_per_part = ledger.energy_area / parts if parts else 0.0
    return throughput, wip_avg, energy_per_part


def main():
    runs = [run_replication(seed) for seed in range(REPLICATIONS)]
    mean = [sum(col) / len(runs) for col in zip(*runs)]
    print(f"Throughput = {mean[0]} parts/hour")
    print(f"WIP = {mean[1]} parts")
    print(f"Mean Energy Consumption per Part = {mean[2]} kWh/part")


if __name__ == "__main__":
    main()