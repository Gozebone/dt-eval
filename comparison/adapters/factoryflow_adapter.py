"""Method A adapter — FactoryFlow (FactoryFlow_v2, Streamlit AMG app).

CLI (run under FactoryFlow's venv, cwd = the app/ directory):
    python factoryflow_adapter.py <mock|real> <bundle_dir> <work_dir> <rep>

Reads `config.yaml` for paths. Generation is real by calling
`IM.AMG_with_langgraph.run_amg_wrapper(DESCRIPTION=...)`; the returned state's
`code` is written to work_dir/model.py and executed headlessly via
`adapters/base.py::wrap_a_model` + a subprocess of sys.executable.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "adapters"))

import adapters.base as B  # noqa: E402
from lib.envfile import load_env_file  # noqa: E402
from lib.simpleyaml import load_yaml  # noqa: E402

load_env_file()  # real mode needs OPENROUTER_API_KEY; allow standalone runs

CFG = load_yaml((ROOT / "config.yaml").read_text(encoding="utf-8"))
APP_DIR = Path(CFG["cwd"]["A"])
FF_SRC = Path(CFG["factorysimpy_src"])
EXEC_TIMEOUT = float(CFG["A"].get("exec_timeout_s", 900))
TIME_UNIT_S = float(CFG["A"].get("model_time_unit_s", 1.0))


def _load_mock_code(case_id: str) -> str:
    mock = ROOT / "adapters" / "_mock_models" / "mock_A_serial.py"
    if case_id != "case_0001_serial_line" or not mock.exists():
        raise RuntimeError(f"no mock model shipped for case '{case_id}'")
    return mock.read_text(encoding="utf-8")


def generate(manifest: dict, bundle: Path, mode: str, workdir: Path):
    desc = (bundle / "prompt_A.txt").read_text(encoding="utf-8")
    res = B.empty_result("A", manifest["case_id"], int(rep))
    t0 = time.perf_counter()
    try:
        if mode == "mock":
            code = _load_mock_code(manifest["case_id"])
            assumptions = f"(mock) {manifest['title']}"
            llm_calls = 0
        else:
            sys.path.insert(0, str(APP_DIR))
            os.chdir(APP_DIR)
            if not os.getenv("OPENROUTER_API_KEY"):
                raise RuntimeError(
                    "OPENROUTER_API_KEY not set (real mode requires it)")
            from IM.AMG_with_langgraph import run_amg_wrapper
            state = run_amg_wrapper(DESCRIPTION=desc)
            code = state.get("code", "")
            if not code:
                raise RuntimeError("run_amg_wrapper returned empty code")
            assumptions = state.get("assumptions", "")
            llm_calls = 2  # reasoner node + amg node
        res["elapsed_generation_s"] = round(time.perf_counter() - t0, 3)
        res["llm_calls"] = llm_calls
        res["assumptions"] = assumptions
    except Exception as e:  # noqa: BLE001
        res["status"] = "generation_error"
        res["error"] = f"{type(e).__name__}: {e}"
        B.write_json(workdir / "result.json", res)
        return None
    # write + execute
    (workdir / "model.py").write_text(B.strip_code_fence(code), encoding="utf-8")
    return res, code


def execute(code: str, workdir: Path, res: dict):
    wrapped = B.wrap_a_model(code, str(FF_SRC))
    run_file = workdir / "run_model.py"
    run_file.write_text(wrapped, encoding="utf-8")
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            [sys.executable, str(run_file)],
            cwd=str(workdir), capture_output=True, text=True,
            timeout=EXEC_TIMEOUT, env=dict(os.environ, MPLBACKEND="Agg"),
        )
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        (workdir / "exec_stdout.log").write_text(stdout, encoding="utf-8")
        (workdir / "exec_stderr.log").write_text(stderr, encoding="utf-8")
        res["elapsed_simulation_s"] = round(time.perf_counter() - t0, 3)
        if proc.returncode != 0:
            res["status"] = "simulation_error"
            res["error"] = f"model exited {proc.returncode}: {stderr[-4000:]}"
            B.write_json(workdir / "result.json", res)
            return None
        probe = B.parse_a_probe_json(stdout)
        if "error" in probe:
            res["status"] = "parse_error"
            res["error"] = probe["error"]
            res["kpis"]["native"]["stdout_head"] = stdout[:1500]
            B.write_json(workdir / "result.json", res)
            return None
    except subprocess.TimeoutExpired:
        res["status"] = "timeout"
        res["error"] = f"simulation exceeded {EXEC_TIMEOUT}s"
        B.write_json(workdir / "result.json", res)
        return None
    return probe


def to_kpis(probe: dict) -> dict:
    per = probe.get("machines") or {}
    horizons = [m["horizon"] for m in per.values() if m.get("horizon")]
    util = {mid: m["utilization"] for mid, m in per.items()}
    util = {k: (round(v, 4) if v is not None else None) for k, v in util.items()}
    # serial line: all machines process (near) equal counts -> median rate
    rates = [m["throughput_per_unit"] for m in per.values()
             if m.get("throughput_per_unit") is not None]
    horizon = sum(horizons) / len(horizons) if horizons else None
    rate_per_h = (sorted(rates)[len(rates) // 2] * 3600.0 / TIME_UNIT_S
                  if rates else None)
    return {
        "throughput_per_hour": round(rate_per_h, 4) if rate_per_h else None,
        "utilization": util,
        "wip_parts": None,
        "energy_per_part_kwh": None,
        "native": {"machine_stats": {k: v for k, v in per.items()},
                   "model_horizon_s": horizon if horizon else None},
    }


def main(mode: str, bundle: str, workdir: str, rep: str) -> int:
    bundle = Path(bundle)
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    manifest = B.load_manifest(bundle)
    res, code = generate(manifest, bundle, mode, workdir)
    if code is None:
        return 0  # result.json already written by generate()
    probe = execute(code, workdir, res)
    if probe is None:
        return 0
    res["kpis"].update(to_kpis(probe))
    res["generated_model_file"] = str(workdir / "model.py")
    B.write_json(workdir / "result.json", res)
    print(f"[A] {res['status']} throughput={res['kpis']['throughput_per_hour']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("usage: python factoryflow_adapter.py <mock|real> <bundle> <workdir> <rep>")
        sys.exit(2)
    mode, bundle, workdir, rep = sys.argv[1:]
    sys.exit(main(mode, bundle, workdir, rep))
