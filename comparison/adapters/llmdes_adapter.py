"""Method B adapter — LLM-DES-Modeling.

CLI (run under LLM-DES's venv, cwd = the LLM-DES repo root):
    python llmdes_adapter.py <mock|real> <bundle_dir> <work_dir> <rep>

Mirrors main.py's headless generation path: eventlog pre-processing + metrics +
sequence text, then `ModelBuilder(client).build(...)`. The produced model is
executed as a subprocess (the repo's own convention) and its stdout KPIs are
parsed per the retrieve_KPIs contract.
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
LLMDES = Path(CFG["llmdes_repo"])
sys.path.insert(0, str(LLMDES))
sys.path.insert(0, str(LLMDES / "adapters"))
EXEC_TIMEOUT = float(CFG["B"].get("exec_timeout_s", 900))
SIM_TIME = int(CFG["B"].get("sim_time_s", 8 * 24 * 3600))
WARMUP = int(CFG["B"].get("warmup_s", 24 * 3600))
REPS = int(CFG["B"].get("replications", 10))

MOCK_MARKER = "__TRUTH_JSON__"


def _horizon(manifest: dict) -> tuple[int, int]:
    """The simulation horizon B is told to use, taken from the case's `reference`.

    The reference plant simulates `warmup_s + window_s` and reports KPIs over
    `[warmup_s, warmup_s + window_s]` (truth/plant.py:144, :401). B has to be told
    the same total and the same warm-up or its KPIs are not the same measurement:
    with config's 8 d / 24 h it measured 7 days after a 1-day warm-up while the
    truth measured 5 days after 6 h, which is a different number for any
    window- or transient-sensitive indicator (WIP most of all). config's values
    stay as the fallback for a bundle that carries no `reference` block.

    `reference.replications` is deliberately *not* read here: that is how many
    independent runs the truth's mean was averaged over, whereas `B.replications`
    is how many internal runs B averages into one number of its own. Coupling them
    would vary B's internal precision per case (case_0001's reference uses 6, the
    others 10) for no measurement reason.
    """
    ref = manifest.get("reference") or {}
    warmup_s = ref.get("warmup_s")
    window_s = ref.get("window_s")
    # Explicit `is None` rather than truthiness: a reference that genuinely says
    # `warmup_s: 0` (no warm-up) must be honoured, not silently swapped for
    # config's 86400. Only an absent key falls back.
    warmup = WARMUP if warmup_s is None else int(warmup_s)
    sim_time = SIM_TIME if window_s is None else warmup + int(window_s)
    return sim_time, warmup


def _mock_model(manifest: dict) -> str:
    mock = ROOT / "adapters" / "_mock_models" / "mock_B_serial.py"
    if manifest["case_id"] != "case_0001_serial_line" or not mock.exists():
        raise RuntimeError(f"no mock model shipped for case '{manifest['case_id']}'")
    template = mock.read_text(encoding="utf-8")
    truth = json.loads((manifest_dir / "truth_kpis.json").read_text(encoding="utf-8"))
    payload = {
        "throughput": truth["throughput_per_hour"]["mean"],
        "wip": truth["wip_parts"]["mean"],
        "energy": truth["energy_per_part_kwh"]["mean"],
    }
    return template.replace(MOCK_MARKER, json.dumps(payload))


def generate(manifest: dict, bundle: Path, mode: str, workdir: Path, client=None):
    res = B.empty_result("B", manifest["case_id"], int(rep))
    t0 = time.perf_counter()
    try:
        if mode == "mock":
            code = _mock_model(manifest)
            llm_calls = 0
        else:
            from processmining import eventlog, metrics
            from agents.builder import ModelBuilder
            df_raw = eventlog.load(bundle / "eventlog.csv")
            df_clean = eventlog.preprocess(df_raw)
            stations_md = metrics.compute(df_clean).to_string(index=False)
            sequence_text = eventlog.to_sequence_text(df_clean)
            blueprint_code = (Path(CFG["blueprint_model"])
                              .read_text(encoding="utf-8"))
            aux = (bundle / "aux_B.txt").read_text(encoding="utf-8").strip()
            sim_time, warmup = _horizon(manifest)
            builder = ModelBuilder(client)
            code = builder.build(
                blueprint_code=blueprint_code,
                stations_table_md=stations_md,
                sequence_text=sequence_text,
                buffers=aux,
                defects="Defect rate = 0.0, no defect sink",
                manual_note="Simulation time in seconds; time unit is seconds.",
                sim_time=sim_time, warmup_seconds=warmup, replications=REPS,
            )
            llm_calls = 2  # builder + inspector
        res["elapsed_generation_s"] = round(time.perf_counter() - t0, 3)
        res["llm_calls"] = llm_calls
    except Exception as e:  # noqa: BLE001
        res["status"] = "generation_error"
        res["error"] = f"{type(e).__name__}: {e}"
        B.write_json(workdir / "result.json", res)
        return None
    (workdir / "model.py").write_text(B.strip_code_fence(code), encoding="utf-8")
    return res, code


def execute(code: str, workdir: Path, res: dict):
    run_file = workdir / "run_model.py"
    run_file.write_text(B.strip_code_fence(code), encoding="utf-8")
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            [sys.executable, str(run_file)],
            cwd=str(workdir), capture_output=True, text=True,
            timeout=EXEC_TIMEOUT,
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
    except subprocess.TimeoutExpired:
        res["status"] = "timeout"
        res["error"] = f"simulation exceeded {EXEC_TIMEOUT}s"
        B.write_json(workdir / "result.json", res)
        return None
    return stdout


def to_kpis(stdout: str) -> dict:
    parsed = B.parse_b_stdout(stdout)
    return {
        "throughput_per_hour": parsed["throughput_per_hour"],
        "utilization": None,
        "wip_parts": parsed["wip_parts"],
        "energy_per_part_kwh": parsed["energy_per_part_kwh"],
        "native": {"stdout_head": stdout[:3000]},
    }


def main(mode: str, bundle: str, workdir: str, rep: str) -> int:
    global manifest_dir
    bundle = Path(bundle)
    workdir = Path(workdir)
    manifest_dir = bundle
    workdir.mkdir(parents=True, exist_ok=True)
    manifest = B.load_manifest(bundle)
    client = None
    if mode == "real":
        key = os.getenv("OPENROUTER_API_KEY")
        if not key:
            res = B.empty_result("B", manifest["case_id"], int(rep))
            res["status"] = "generation_error"
            res["error"] = "OPENROUTER_API_KEY not set (real mode requires it)"
            B.write_json(workdir / "result.json", res)
            return 0
        from openai import OpenAI
        client = OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1")
    res, code = generate(manifest, bundle, mode, workdir, client)
    if code is None:
        return 0
    stdout = execute(code, workdir, res)
    if stdout is None:
        return 0
    res["kpis"].update(to_kpis(stdout))
    res["generated_model_file"] = str(workdir / "model.py")
    B.write_json(workdir / "result.json", res)
    print(f"[B] {res['status']} throughput={res['kpis']['throughput_per_hour']}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("usage: python llmdes_adapter.py <mock|real> <bundle> <workdir> <rep>")
        sys.exit(2)
    mode, bundle, workdir, rep = sys.argv[1:]
    sys.exit(main(mode, bundle, workdir, rep))
