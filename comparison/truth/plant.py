"""Ground-truth plant engine (pure SimPy, stdlib only besides simpy).

A `manifest` defines a serial production line with known parameters. For a given
replication index we run one seeded simulation and, over the measurement window
(excluding warmup), produce:
  - an interval event log in the `workingtest.csv` schema
  - ground-truth KPIs (throughput, WIP, utilisation, energy, per-machine states)

Semantics:
  * deterministic processing times, deterministic inter-arrival
  * machine failures (down periods) are drawn from a renewal process
    (exponential MTBF / MTTR) and are honoured only while the machine is free,
    so a `Working` window always covers exactly one un-interrupted part
  * down time is rendered as `Stopped` rows, non-working time as `Idle`

Used by `casegen.py`; imported by nothing else in the toolchain under test.
"""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import simpy

ISO_ANCHOR = datetime(2024, 1, 1, 0, 0, 0)


def _tag_for_gap(pw, seg_start):
    """Part tag for a non-working gap: last worked part at this machine, else next."""
    prev = None
    for pa, _pb, it in pw:
        if pa <= seg_start + 1e-9:
            prev = it
        else:
            break
    if prev is not None:
        return prev
    return pw[0][2] if pw else None


# --------------------------------------------------------------------------- #
# Blocking buffer with explicit waiter lists (no races, no lost wakeups)
# --------------------------------------------------------------------------- #
class Buffer:
    def __init__(self, env: simpy.Environment, capacity: int):
        self.env = env
        self.capacity = capacity
        self.items: list = []
        self.get_waiters: list = []   # env.Event objects waiting for an item
        self.put_waiters: list = []   # (env.Event, item) waiting for space
        # occupancy tracking for WIP integration
        self._occ_t: float = 0.0
        self._occ_level: int = 0
        self.occupied_time: dict = {}   # level -> seconds (filled per run window)

    def _note_change(self, t_new_level: int) -> None:
        now = self.env.now
        self.occupied_time[self._occ_level] = (
            self.occupied_time.get(self._occ_level, 0.0) + now - self._occ_t
        )
        self._occ_t = now
        self._occ_level = t_new_level

    def reset_occupancy(self) -> None:
        self.occupied_time = {}
        self._occ_t = self.env.now

    def close_occupancy(self) -> None:
        """Close the bookkeeping interval at the measurement-window end."""
        self._note_change(self._occ_level)

    def try_get(self):
        if self.items:
            item = self.items.pop(0)
            self._note_change(len(self.items))
            # wake one waiting putter, if any
            if self.put_waiters and len(self.items) < self.capacity:
                e, it = self.put_waiters.pop(0)
                self.items.append(it)
                self._note_change(len(self.items))
                e.succeed()
            return item
        return None

    def wait_get_event(self):
        e = self.env.event()
        self.get_waiters.append(e)
        return e

    def cancel_waiter(self, e) -> None:
        if e in self.get_waiters:
            self.get_waiters.remove(e)

    def try_put(self, item) -> bool:
        if len(self.items) < self.capacity:
            self.items.append(item)
            self._note_change(len(self.items))
            if self.get_waiters:
                w = self.get_waiters.pop(0)
                w.succeed()
            return True
        return False

    def wait_put_event(self, item):
        e = self.env.event()
        self.put_waiters.append((e, item))
        return e

    def cancel_put_waiter(self, e) -> None:
        self.put_waiters[:] = [(w, it) for (w, it) in self.put_waiters if w is not e]

    @property
    def avg_level(self) -> float:
        """Time-average level over the measurement window (0..1 if unmeasured)."""
        total = sum(lvl * sec for lvl, sec in self.occupied_time.items())
        run = sum(self.occupied_time.values())
        return total / run if run > 0 else 0.0


# --------------------------------------------------------------------------- #
# Plant
# --------------------------------------------------------------------------- #
@dataclass
class PlantResult:
    kpis: dict
    per_machine: dict
    log_rows: list   # rows for the event log (single replication)
    completed: int
    window_s: float


class Plant:
    def __init__(self, manifest: dict, replication: int):
        self.m = manifest
        ref = manifest["reference"]
        seed = int(ref["seed"]) + int(replication) * 10013
        self.env = simpy.Environment()
        self.rng = __import__("random").Random(seed)
        self.rep = replication
        self.warmup_s = float(ref["warmup_s"])
        self.window_s = float(ref["window_s"])
        self.T = self.warmup_s + self.window_s
        self.machines = manifest["machines"]
        self.buffers = manifest["buffers"]
        self.inter_arrival_s = float(manifest["arrival"]["inter_arrival_s"])
        self.completed = 0
        self.completed_times: list[float] = []

    # -- down-window scheduling helpers ------------------------------------- #
    def _expo(self, mean: float) -> float:
        return self.rng.expovariate(1.0 / mean) if mean > 0 else 0.0

    # -- flow ---------------------------------------------------------------- #
    def build(self):
        env = self.env
        n = len(self.machines)
        assert len(self.buffers) == n, "need one buffer feeding each machine"

        buffs = [Buffer(env, int(b["capacity"])) for b in self.buffers]
        # per-machine dynamic state
        mstate = [{
            "down_start": None, "down_dur": None, "mtbf": self._mtbf(i),
            "mttr": float(self.machines[i]["mttr_s"]),
            "pt": float(self.machines[i]["process_time_s"]),
            "work_power": float(self.machines[i]["work_power_kw"]),
            "idle_power": float(self.machines[i]["idle_power_kw"]),
            "down_windows": [],          # (start, end) honoured down periods
            "part_windows": [],          # (start, end) working periods
            "busy": False, "busy_since": None,
            "busy_intervals": [],        # machine holds a part (work or blocked)
        } for i in range(n)]

        def mtbf_of(i):  # used during build via closure
            return mstate[i]["mtbf"]

        # --- source ---------------------------------------------------------
        def source_proc():
            i = 0
            while True:
                if env.now >= self.T:
                    return
                if not buffs[0].try_put(f"part-{i}"):
                    e = buffs[0].wait_put_event(f"part-{i}")
                    # put may also be interrupted by nothing downstream; simple wait
                    yield e
                i += 1
                yield env.timeout(self.inter_arrival_s)

        # --- machine i -------------------------------------------------------
        def arm_down(i):
            """Sample the next down attempt starting from now."""
            st = mstate[i]
            st["down_start"] = env.now + self._expo(st["mtbf"])
            st["down_dur"] = None

        def set_busy(i, on):
            st = mstate[i]
            if on and not st["busy"]:
                st["busy"] = True
                st["busy_since"] = env.now
            elif not on and st["busy"]:
                st["busy_intervals"].append((st["busy_since"], env.now))
                st["busy"] = False

        def wait_for_item(i):
            """Yield until an item is available; returns it. Down periods that
            start while waiting are honoured (rendered as Stopped)."""
            b = buffs[i]
            while True:
                item = b.try_get()
                if item is not None:
                    return item
                ge = b.wait_get_event()
                st = mstate[i]
                arm_down(i)
                downev = env.timeout(max(st["down_start"] - env.now, 0.0))
                res = yield env.any_of([ge, downev])
                if ge in res:
                    # woken by an item arriving; take it
                    item = b.try_get()
                    if item is not None:
                        st["down_start"] = None  # defer re-arming to next free time
                        return item
                    continue  # spurious; loop again
                # a down period started while we were idle-waiting
                b.cancel_waiter(ge)  # drop the stale get request
                st["down_dur"] = self._expo(st["mttr"])
                st["down_windows"].append(
                    (st["down_start"], st["down_start"] + st["down_dur"])
                )
                yield env.timeout(st["down_dur"])
                st["down_start"] = None
                # re-arm handled at next free moment

        def release_item(i):
            """Yield until the processed item can be handed downstream."""
            if i == n - 1:
                self.completed += 1
                self.completed_times.append(env.now)
                return
            b = buffs[i + 1]
            while True:
                if b.try_put(f"p"):
                    return
                pe = b.wait_put_event("p")
                st = mstate[i]
                arm_down(i)
                downev = env.timeout(max(st["down_start"] - env.now, 0.0))
                res = yield env.any_of([pe, downev])
                if pe in res:
                    return
                b.cancel_put_waiter(pe)  # drop the stale put request + its item
                st["down_dur"] = self._expo(st["mttr"])
                st["down_windows"].append(
                    (st["down_start"], st["down_start"] + st["down_dur"])
                )
                yield env.timeout(st["down_dur"])
                st["down_start"] = None

        def machine_proc(i):
            st = mstate[i]
            while True:
                # 1. free moment: arm a down attempt
                arm_down(i)
                # 2. wait for an item (idle; down periods honoured inside)
                if env.now >= self.T:
                    return
                item = yield from wait_for_item(i)
                if item is None:
                    return
                # 3. if we are down right now (down started before the part), wait
                if st["down_start"] is not None and st["down_start"] <= env.now + 1e-9:
                    st["down_dur"] = self._expo(st["mttr"])
                    st["down_windows"].append(
                        (st["down_start"], st["down_start"] + st["down_dur"])
                    )
                    yield env.timeout(st["down_dur"])
                    st["down_start"] = None
                # 4. process (a pending down that would fall inside processing is
                #    postponed until after this part)
                if env.now + st["pt"] > self.T:
                    return
                set_busy(i, True)
                start = env.now
                yield env.timeout(st["pt"])
                st["part_windows"].append((start, env.now, item))
                # 5. release downstream
                yield from release_item(i)
                set_busy(i, False)

        env.process(source_proc())
        for i in range(n):
            env.process(machine_proc(i))
        self.buffs = buffs
        self.mstate = mstate

    def _mtbf(self, i):
        av = float(self.machines[i]["availability"])
        mttr = float(self.machines[i]["mttr_s"])
        av = min(max(av, 0.01), 0.999)
        return mttr * av / (1.0 - av)

    # -- measurement --------------------------------------------------------- #
    def run(self):
        self.build()
        # phase 1: warm-up (occupancy bookkeeping starts at the window start)
        self.env.run(until=self.warmup_s)
        for b in self.buffs:
            b.reset_occupancy()
        # phase 2: measurement window
        self.env.run(until=self.T)
        for b in self.buffs:
            b.close_occupancy()
        for st in self.mstate:
            if st["busy"]:
                st["busy_intervals"].append((st["busy_since"], self.T))
        # clip down/part windows & busy intervals to the measurement window
        for st in self.mstate:
            st["down_windows"] = [
                (max(a, self.warmup_s), min(b, self.T))
                for (a, b) in st["down_windows"]
                if b > self.warmup_s and a < self.T
            ]
            st["part_windows"] = [
                (max(a, self.warmup_s), min(b, self.T), it)
                for (a, b, it) in st["part_windows"]
                if b > self.warmup_s and a < self.T
            ]
            st["busy_intervals"] = [
                (max(a, self.warmup_s), min(b, self.T))
                for (a, b) in st["busy_intervals"]
                if b > self.warmup_s and a < self.T
            ]
        return self._measure()

    def _state_rows(self, i):
        """Merge per-machine event boundaries into (start, end, state, part) rows.

        `part` tags each segment with a part identity so that the event log can
        be keyed by part (one ID per part route, mirroring the reference data
        schema): Working segments carry the part being processed; non-working
        segments carry the part the machine most recently worked (or the next
        one for a leading gap before the first in-window part).
        """
        st = self.mstate[i]
        pw = st["part_windows"]   # clipped (start, end, item), chronological
        pts = sorted(set([self.warmup_s, self.T]))
        for a, b in st["down_windows"]:
            pts += [a, b]
        for a, b, _it in pw:
            pts += [a, b]
        pts = sorted(pts)
        rows = []
        for a, b in zip(pts, pts[1:]):
            if b - a < 1e-9:
                continue
            mid = (a + b) / 2
            in_down = any(da <= mid < db for da, db in st["down_windows"])
            in_part = any(pa <= mid < pb for pa, pb, _ in pw)
            state = "Stopped" if in_down else ("Working" if in_part else "Idle")
            if state == "Working":
                item = next(it for pa, pb, it in pw if pa <= mid < pb)
            else:
                item = _tag_for_gap(pw, a)
            rows.append((a, b, state, item))
        merged = []
        for r in rows:
            if merged and r[2] != "Working" and merged[-1][2] == r[2] \
                    and merged[-1][3] == r[3]:
                pr = merged[-1]
                merged[-1] = (pr[0], r[1], pr[2], pr[3])
            else:
                merged.append(r)
        return merged

    def _measure(self) -> PlantResult:
        m = self.m
        win = self.window_s
        per = {}
        energy_work = 0.0
        energy_idle = 0.0
        for i, mch in enumerate(self.machines):
            st = self.mstate[i]
            work = sum(b - a for a, b, _ in st["part_windows"])
            down = sum(b - a for a, b in st["down_windows"])
            idle = win - work - down
            w_p = float(mch["work_power_kw"])
            i_p = float(mch["idle_power_kw"])
            energy_work += work * w_p
            energy_idle += idle * i_p
            per[mch["id"]] = {
                "working_s": round(work, 3),
                "idle_s": round(idle, 3),
                "stopped_s": round(down, 3),
                "processed": len(st["part_windows"]),
                "availability": round(1 - down / win, 4) if win else None,
                "utilization": round(work / win, 4) if win else None,
            }
        completed = sum(1 for t in self.completed_times if self.warmup_s <= t <= self.T)
        wip_integrals = []
        for b in self.buffs:
            wip_integrals.append(b.avg_level * win)
        busy = sum(b - a for i in range(len(self.machines))
                   for a, b in self.mstate[i]["busy_intervals"])
        mean_wip = (sum(wip_integrals) + busy) / win
        energy_per_part = ((energy_work + energy_idle) / 3600.0) / completed \
            if completed else None
        kpis = {
            "throughput_per_hour": completed / (win / 3600.0) if win else None,
            "wip_parts": round(mean_wip, 4),
            "energy_per_part_kwh": round(energy_per_part, 6)
            if energy_per_part is not None else None,
            "utilization": {mch["id"]: per[mch["id"]]["utilization"]
                            for mch in self.machines},
            "energy_work_kwh": round(energy_work / 3600.0, 4),
            "energy_idle_kwh": round(energy_idle / 3600.0, 4),
            "completed": completed,
            "window_s": win,
        }
        return PlantResult(
            kpis=kpis, per_machine=per,
            log_rows=self._log_rows(per, energy_work, energy_idle),
            completed=completed, window_s=win,
        )

    def _log_rows(self, per, energy_work, energy_idle):
        """Build interval rows in the workingtest.csv schema for this rep."""
        rows = []
        for i, mch in enumerate(self.machines):
            mid = mch["id"]
            for (a, b, state, item) in self._state_rows(i):
                dt = b - a
                if dt < 1e-6 or item is None:
                    continue
                power = {"Working": float(mch["work_power_kw"]),
                         "Idle": float(mch["idle_power_kw"]),
                         "Stopped": 0.0}[state]
                t0 = ISO_ANCHOR + timedelta(seconds=a)
                t1 = ISO_ANCHOR + timedelta(seconds=b)
                rows.append({
                    "ID": item,
                    "MachineName": mid,
                    "StartTime": t0.isoformat(timespec="microseconds"),
                    "EndTime": t1.isoformat(timespec="microseconds"),
                    "ReasonCode": state,
                    "EnergyConsumption": round(power * dt, 3),
                })
        rows.sort(key=lambda r: (r["StartTime"], r["MachineName"]))
        return rows


def run_replication(manifest: dict, replication: int) -> PlantResult:
    plant = Plant(manifest, replication)
    return plant.run()
