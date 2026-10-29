"""Case-bundle generator.

For a case directory containing an authored `manifest.yaml`, this generates the
simulation-dependent artefacts and commits them next to the manifest:

    eventlog.csv        (B native input; workingtest.csv schema; seeded rep)
    truth_kpis.json     (KPIs averaged over reference replications + std)
    truth_structure.json(expected structural parameter table)
    station_table.md    (per-station metrics, identical definition to B)
    prompt_A.txt        (A native input describing the same plant)
    aux_B.txt           (extra free-form context for B beyond the log)
    manifest.json       (canonical machine-readable copy of the manifest)

Run under the LLM-DES venv (has simpy + pm4py for the metrics definition):
    python casegen.py cases/<case_id>
"""
from __future__ import annotations

import csv
import json
import os
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "lib"))

from lib.simpleyaml import load_yaml  # noqa: E402
from truth.plant import run_replication  # noqa: E402

# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _mean_std(values):
    vals = [v for v in values if v is not None]
    if not vals:
        return (None, None)
    return (round(statistics.fmean(vals), 6),
            round(statistics.stdev(vals), 6) if len(vals) > 1 else 0.0)


def _avg_over_reps(results):
    """results: list[PlantResult]. Returns dicts with 'mean'/'std' per value."""
    def agg(fn):
        vals = []
        for r in results:
            vals.append(fn(r))
        vals = [x for x in vals if x is not None]
        if not vals:
            return {"mean": None, "std": None}
        return {"mean": round(statistics.fmean(vals), 6),
                "std": round(statistics.stdev(vals), 6) if len(vals) > 1 else 0.0}

    def v(r, path):
        obj = r.kpis
        for p in path.split("."):
            obj = obj[p]
        return obj

    per_machines = sorted(results[0].per_machine.keys())
    return {
        "throughput_per_hour": agg(lambda r: v(r, "throughput_per_hour")),
        "wip_parts": agg(lambda r: v(r, "wip_parts")),
        "energy_per_part_kwh": agg(lambda r: v(r, "energy_per_part_kwh")),
        "utilization": {m: agg(lambda r, mm=m: r.per_machine[mm]["utilization"])
                        for m in per_machines},
        "per_machine": {
            m: {
                "working_s": agg(lambda r, mm=m: r.per_machine[mm]["working_s"]),
                "idle_s": agg(lambda r, mm=m: r.per_machine[mm]["idle_s"]),
                "stopped_s": agg(lambda r, mm=m: r.per_machine[mm]["stopped_s"]),
                "availability": agg(lambda r, mm=m: r.per_machine[mm]["availability"]),
                "processed": agg(lambda r, mm=m: r.per_machine[mm]["processed"]),
            }
            for m in per_machines
        },
    }


def _station_table_md(manifest: dict, log_csv: Path) -> str:
    """Replicate B's station metrics table (metrics.compute) on the case log."""
    repo = os.environ.get("LLMDES_REPO")
    if not repo:
        return ""   # table omitted; prompt_A falls back to the manifest table
    sys.path.insert(0, repo)
    from processmining import eventlog, metrics  # noqa: E402
    df_raw = eventlog.load(log_csv)
    df_clean = eventlog.preprocess(df_raw)
    return metrics.compute(df_clean).to_string(index=False)


def _write_prompt_A(manifest, station_md, case_dir) -> None:
    if station_md:
        station_block = station_md
    else:
        # fallback: summarize from the manifest
        lines = ["MachineName Avg_Time_per_part_s Availability"]
        for m in manifest["machines"]:
            lines.append(f"{m['id']} {m['process_time_s']} {m['availability']}")
        station_block = "\n".join(lines)
    buffer_lines = ", ".join(
        f"{b['id']}(Capacity = {b['capacity']})" for b in manifest["buffers"])
    mc = manifest["machines"]
    flow = " -> ".join([mc[0]["id"]] + [m["id"] for m in mc[1:]])
    text = f"""A manufacturing system is arranged as a serial production line with {len(mc)} machines connected in series: {flow}.

A source feeds the line and a sink collects finished parts. Every buffer has the specified capacity.

Per-station measured facts (obtained from a monitoring period of the real plant):

{station_block}

Buffer list with their capacity:
{buffer_lines}

New parts arrive at the line at a constant rate: one part every {manifest['arrival']['inter_arrival_s']} seconds.

Simulation requirements:
- Time is measured in seconds throughout the model.
- Use a single source, the {len(mc)} machines in series (each with the measured average processing time and measured availability/failure behaviour), and a single sink.
- The model must create its own simpy.Environment, build the structure, validate it, and run the simulation for at least {manifest['reference']['window_s']} seconds (about 5 days) in one go at module level.
- Only structure and the run code; no extra commentary.
"""
    (case_dir / "prompt_A.txt").write_text(text, encoding="utf-8")


def _write_aux_B(manifest, case_dir) -> None:
    buffer_lines = ", ".join(
        f"{b['id']}(Capacity = {b['capacity']})" for b in manifest["buffers"])
    text = (f"Buffer list with their capacity and processtime:\n{buffer_lines}\n"
            "Defect rate = 0.0, no defect sink\n")
    (case_dir / "aux_B.txt").write_text(text, encoding="utf-8")


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main(case_id: str) -> None:
    cases_root = ROOT / "cases"
    case_dir = cases_root / case_id
    manifest = load_yaml((case_dir / "manifest.yaml").read_text(encoding="utf-8"))
    ref = manifest["reference"]
    n_rep = int(ref.get("replications", 10))
    log_rep = int(ref.get("log_rep", 0))

    print(f"[casegen] {case_id}: {n_rep} reference replications (log from rep {log_rep})")
    results = [run_replication(manifest, r) for r in range(n_rep)]

    # truth KPIs
    truth_kpis = _avg_over_reps(results)
    (case_dir / "truth_kpis.json").write_text(
        json.dumps(truth_kpis, indent=2), encoding="utf-8")

    # structural ground truth
    structure = {
        "arrival": manifest["arrival"],
        "machines": manifest["machines"],
        "buffers": manifest["buffers"],
        "flow": "serial",
        "n_machines": len(manifest["machines"]),
    }
    (case_dir / "truth_structure.json").write_text(
        json.dumps(structure, indent=2), encoding="utf-8")

    # event log (single seeded replication)
    log_rows = results[log_rep].log_rows
    with open(case_dir / "eventlog.csv", "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(log_rows[0].keys()))
        writer.writeheader()
        writer.writerows(log_rows)

    # native inputs
    station_md = _station_table_md(manifest, case_dir / "eventlog.csv")
    (case_dir / "station_table.md").write_text(station_md, encoding="utf-8")
    _write_prompt_A(manifest, station_md, case_dir)
    _write_aux_B(manifest, case_dir)

    # canonical JSON manifest
    (case_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")

    k = truth_kpis
    print(f"  throughput_per_hour = {k['throughput_per_hour']}")
    print(f"  wip_parts          = {k['wip_parts']}")
    print(f"  energy_per_part_kwh= {k['energy_per_part_kwh']}")
    print(f"  log rows           = {len(log_rows)}")
    print(f"[casegen] wrote truth_kpis.json, eventlog.csv, station_table.md, "
          f"prompt_A.txt, aux_B.txt, manifest.json")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python casegen.py <case_id>")
        sys.exit(2)
    main(sys.argv[1])
