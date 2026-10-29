"""Comparison orchestrator.

Runs cases x methods x repetitions through each method's own adapter inside its
own virtualenv, then hands the run directory to report.py. Pure stdlib.

    python run_comparison.py --mode mock                     # plumbing
    python run_comparison.py --mode real --cases <id> ...    # LLM runs
    python run_comparison.py --mode real --methods A B --repetitions 3
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from lib.envfile import load_env_file  # noqa: E402
from lib.simpleyaml import load_yaml  # noqa: E402

load_env_file()  # seed os.environ from .env (exported vars still win)

CFG = load_yaml((ROOT / "config.yaml").read_text(encoding="utf-8"))
MODE = CFG["mode"]
METHODS = [m for m in CFG["methods"] if CFG["interpreters"].get(m)]

ADAPTER = {
    "A": "adapters/factoryflow_adapter.py",
    "B": "adapters/llmdes_adapter.py",
    "C": "adapters/method_c_adapter.py",
}


def case_artifacts_present(case_dir: Path) -> bool:
    needed = ["manifest.yaml", "eventlog.csv", "truth_kpis.json",
              "station_table.md", "prompt_A.txt", "aux_B.txt"]
    return all((case_dir / n).exists() for n in needed)


def generate_case_artifacts(case_dir: Path) -> None:
    """Run casegen.py under the B venv (has simpy + pm4py)."""
    interp = CFG["interpreters"]["B"]
    env = dict(os.environ, LLMDES_REPO=str(CFG["llmdes_repo"]))
    proc = subprocess.run(
        [interp, str(ROOT / "casegen.py"), case_dir.name],
        cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=1800)
    print(proc.stdout)
    if proc.returncode != 0:
        raise RuntimeError(f"casegen failed for {case_dir.name}:\n{proc.stderr}")


def ensure_case(case_dir: Path) -> None:
    if not case_artifacts_present(case_dir):
        print(f"[orchestrator] generating truth artefacts for {case_dir.name}")
        generate_case_artifacts(case_dir)
    else:
        print(f"[orchestrator] artefacts present for {case_dir.name}")


def run_one(method: str, mode: str, bundle: Path, workdir: Path, rep: int) -> dict:
    interp = CFG["interpreters"][method]
    cwd = CFG["cwd"].get(method) or str(ROOT)
    env = dict(os.environ)
    adapter = ROOT / ADAPTER[method]
    workdir.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            [interp, str(adapter), mode, str(bundle), str(workdir), str(rep)],
            cwd=cwd, env=env, capture_output=True, text=True, timeout=3600)
    except subprocess.TimeoutExpired:
        return {"status": "adapter_timeout", "case": bundle.name,
                "method": method, "rep": rep, "error": "adapter > 3600s"}
    if proc.stderr:
        (workdir / "adapter_stderr.log").write_text(proc.stderr, encoding="utf-8")
    res_path = workdir / "result.json"
    if res_path.exists():
        res = json.loads(res_path.read_text(encoding="utf-8"))
    else:
        res = {"status": "adapter_error", "case": bundle.name,
               "method": method, "rep": rep,
               "error": f"exit {proc.returncode}: {proc.stderr[-2000:]}"}
    res["adapter_elapsed_s"] = round(time.perf_counter() - t0, 2)
    return res


def discover_cases(cfg_cases, cases_root: Path):
    if cfg_cases:
        return [cases_root / c for c in cfg_cases]
    return sorted(p for p in cases_root.iterdir()
                  if p.is_dir() and (p / "manifest.yaml").exists())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["mock", "real"], default=None)
    ap.add_argument("--cases", nargs="*", default=None)
    ap.add_argument("--methods", nargs="*", default=None)
    ap.add_argument("--repetitions", type=int, default=None)
    ap.add_argument("--no-report", action="store_true")
    ap.add_argument("--label", default=None,
                    help="suffix for the run directory and environment.json, so "
                         "runs made under different method states are not confused "
                         "(e.g. a run after an amendment to C's repo)")
    args = ap.parse_args()

    mode = args.mode or MODE
    methods = args.methods or METHODS
    methods = [m for m in methods if CFG["interpreters"].get(m)
               and (mode != "real" or CFG["interpreters"].get(m))]
    if not methods:
        print("no usable methods (check config.yaml interpreters)", file=sys.stderr)
        return 2
    reps = args.repetitions or int(CFG.get("repetitions", 1))

    cases_root = ROOT / CFG["paths"]["cases_root"]
    cases = discover_cases(args.cases, cases_root)
    if not cases:
        print("no cases found", file=sys.stderr)
        return 2

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if args.label:
        ts = f"{ts}_{args.label}"
    out = ROOT / CFG["paths"]["output_root"] / ts
    out.mkdir(parents=True, exist_ok=True)

    meta = {
        "mode": mode, "methods": methods, "repetitions": reps,
        "cases": [c.name for c in cases], "timestamp": ts,
        "label": args.label,
        "models": {
            "A": "FactoryFlow (google/gemini-3.1-pro-preview via OpenRouter)",
            "B": "LLM-DES-Modeling (gpt-5.1 builder/inspector via OpenRouter)",
        },
    }
    (out / "environment.json").write_text(json.dumps(meta, indent=2))

    summary = []
    for case_dir in cases:
        ensure_case(case_dir)
        for method in methods:
            for rep in range(reps):
                workdir = out / case_dir.name / method / f"rep{rep}"
                print(f"[orchestrator] {case_dir.name} / {method} / rep{rep} "
                      f"({mode})")
                res = run_one(method, mode, case_dir, workdir, rep)
                summary.append(res)
    (out / "summary.json").write_text(json.dumps(summary, indent=2))

    ok = [r for r in summary if r.get("status") == "ok"]
    print(f"\n[orchestrator] done: {len(ok)}/{len(summary)} ok -> {out}")
    if not args.no_report:
        subprocess.run([sys.executable, str(ROOT / "report.py"), str(out)])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
