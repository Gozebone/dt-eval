"""Shared adapter helpers — stdlib only.

Everything here must import cleanly under BOTH method virtualenvs and under any
other interpreter, because adapters are executed inside the method's own venv.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

METHODS = {"A": "factoryflow", "B": "llmdes", "C": "method_c"}


def load_manifest(case_dir: Path) -> dict:
    p = case_dir / "manifest.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    from lib.simpleyaml import load_yaml
    return load_yaml((case_dir / "manifest.yaml").read_text(encoding="utf-8"))


def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def strip_code_fence(code: str) -> str:
    code = code.strip()
    if code.startswith("```"):
        code = code.split("\n", 1)[1] if "\n" in code else ""
        if code.endswith("```"):
            code = code.rsplit("```", 1)[0]
    return code.strip()


# --------------------------------------------------------------------------- #
# Method B stdout contract (see helpers/other_helpers.py retrieve_KPIs)
# --------------------------------------------------------------------------- #
B_BOTTLENECK_MARKER = "=== Bottleneck Frequency over runs ==="

B_THROUGHPUT_RE = re.compile(r"Throughput\s*=\s*([0-9.eE+-]+)\s*parts/hour")
B_WIP_RE = re.compile(r"WIP\s*=\s*([0-9.eE+-]+)\s*parts")
B_ENERGY_RE = re.compile(
    r"Mean Energy Consumption per Part\s*=\s*([0-9.eE+-]+)\s*kWh/part")


def parse_b_stdout(stdout: str) -> dict:
    """Extract B's three headline KPIs. Missing -> None (never fabricated)."""
    def num(pat):
        m = pat.search(stdout)
        if not m:
            return None
        try:
            return float(m.group(1))
        except ValueError:
            return None
    return {
        "throughput_per_hour": num(B_THROUGHPUT_RE),
        "wip_parts": num(B_WIP_RE),
        "energy_per_part_kwh": num(B_ENERGY_RE),
    }


def parse_a_probe_json(stdout: str) -> dict:
    """Extract the tagged probe line appended by the A execution wrapper."""
    tag = "__FF_KPI_JSON__:"
    for line in stdout.splitlines():
        if line.startswith(tag):
            try:
                return json.loads(line[len(tag):])
            except json.JSONDecodeError:
                return {"error": "malformed probe line"}
    return {"error": "probe line not found in stdout"}


# --------------------------------------------------------------------------- #
# Method A execution wrapper (streamlit stub + sys.path + probe)
# --------------------------------------------------------------------------- #
def wrap_a_model(raw_code: str, factorysimpy_src: str,
                 exec_wrapper: str | None = None) -> str:
    """Sanitise a FactoryFlow-generated module for headless execution.

    Injects (before any user code): sys.path for factorysimpy, a no-op
    `streamlit` module (generated code copies the examples' st.graphviz_chart
    calls), and MPLBACKEND. Appends the KPI probe at the end, after the module's
    own `if __name__ == "__main__":` block, so the tagged JSON line is printed
    last. Runs must be deterministic per seed: nothing here re-seeds the model.
    """
    code = strip_code_fence(raw_code)
    prelude = (
        "import sys as _sys, os as _os\n"
        "_sys.path.insert(0, %s)\n" % repr(str(factorysimpy_src))
    ) + (
        "_os.environ.setdefault('MPLBACKEND', 'Agg')\n"
        "class _StStreamlit:\n"
        "    graphviz_chart = staticmethod(lambda *a, **k: None)\n"
        "    @staticmethod\n"
        "    def set_page_config(*a, **k):\n"
        "        return None\n"
        "_sys.modules.setdefault('streamlit', _StStreamlit())\n"
        # FactorySimPy emits verbose state traces via print; forward only the
        # probe line so model stdout never floods the harness capture.
        "class _F:\n"
        "    def __init__(self):\n"
        "        self._buf = ''\n"
        "    def write(self, s):\n"
        "        self._buf += s\n"
        "        while '\\n' in self._buf:\n"
        "            line, self._buf = self._buf.split('\\n', 1)\n"
        "            if '__FF_KPI_JSON__' in line:\n"
        "                _sys.__stdout__.write(line + '\\n')\n"
        "                _sys.__stdout__.flush()\n"
        "    def flush(self):\n"
        "        pass\n"
        "_sys.stdout = _F()\n"
    )
    probe = (
        "\n# ===== harness probe (appended) =====\n"
        "import json as _json\n"
        "from factorysimpy.nodes.node import Node as _Node\n"
        "from factorysimpy.nodes.machine import Machine as _Machine\n"
        "_PROBE = {}\n"
        "def _harness_machines():\n"
        "    found = []\n"
        "    for _v in list(globals().values()):\n"
        "        if isinstance(_v, _Node):\n"
        "            for _t in _v.all_tops:\n"
        "                nodes, _edges = _t.get_all_nodes_edges()\n"
        "                for _n in nodes.values():\n"
        "                    if isinstance(_n, _Machine):\n"
        "                        found.append(_n)\n"
        "    return found\n"
        "_ms = _harness_machines()\n"
        "if _ms:\n"
        "    _per = {}\n"
        "    for _m in _ms:\n"
        "        _s = _m.stats\n"
        "        _tts = _s.get('total_time_spent_in_states', {})\n"
        # Machine.stats accrue overlapping state keys (ALL_ACTIVE_* and
        # ATLEAST_ONE_* run in parallel), so neither horizon nor processing
        # time may be derived by summing. horizon = full sim time (machines
        # live for the whole env run); processing = max over the overlapping
        # processing-state accumulators.
        "        _horizon = float(getattr(_m.env, 'now', 0.0))\n"
        "        _proc = max([_tts.get(_k, 0.0) for _k in (\n"
        "            'PROCESSING_STATE', 'ATLEAST_ONE_PROCESSING_STATE',\n"
        "            'ALL_ACTIVE_PROCESSING_STATE')] or [0.0])\n"
        "        _n = _s.get('num_item_processed', 0)\n"
        "        if isinstance(_n, (list, tuple, dict)):\n"
        "            _n = len(_n)\n"
        "        _per[_m.id] = {\n"
        "            'processed': _n,\n"
        "            'horizon': _horizon,\n"
        "            'utilization': (_proc / _horizon) if _horizon else None,\n"
        "            'throughput_per_unit': (_n / _horizon) if _horizon else None,\n"
        "        }\n"
        "    _PROBE['machines'] = _per\n"
        "    _PROBE['time_unit_s'] = 1.0\n"
        "print('__FF_KPI_JSON__:' + _json.dumps(_PROBE, default=str))\n"
    )
    return prelude + code + "\n" + probe


# --------------------------------------------------------------------------- #
# result helpers
# --------------------------------------------------------------------------- #
def empty_result(method: str, case: str, rep: int) -> dict:
    return {
        "method": method,
        "case": case,
        "rep": rep,
        "status": "ok",
        "error": None,
        "elapsed_generation_s": None,
        "elapsed_simulation_s": None,
        "llm_calls": 0,
        "llm_tokens_estimate": None,
        "generated_model_file": None,
        "kpis": {
            "throughput_per_hour": None,
            "utilization": None,
            "wip_parts": None,
            "energy_per_part_kwh": None,
            "native": {},
        },
        "assumptions": None,
        "notes": [],
    }


# ---- Method C's rep status: derived from its stages (protocol.md §5) ------- #
# C's pipeline is several agents in sequence, so "the pipeline returned" is not
# "the method worked": an agent can answer off-contract, or return a model that
# will not run. C's status is therefore read off the deepest stage that failed,
# so that a crashed DES model is a `simulation_error` for C exactly as it is for
# A and B. The rule lives here (stdlib-only, no adapter imports) because the
# report re-derives it against a stored rep, and a second copy would drift.
_TRANSPORT_NAMES = ("URLError", "ConnectionError", "ConnectionResetError",
                    "ConnectionRefusedError", "ConnectionAbortedError",
                    "TimeoutError", "socket.timeout", "OSError")

# des_stage values that name the failure by themselves, needing no DT error
# string to interpret them.
_DECISIVE_DES_STAGES = {"simulation_error", "timeout", "error", "ran_no_contract"}


def transport_named(err) -> bool:
    """Is this recorded error string a transport failure of an endpoint?

    Matched on the exception's type *name*, because per-slot stage errors are
    recorded as strings (`"URLError: <urlopen error timed out>"`).
    """
    return bool(err) and str(err).split(":", 1)[0].strip() in _TRANSPORT_NAMES


def derive_rep_status(measured: bool, des_stage, db_note, des_err) -> tuple:
    """`(status, basis)` for C: the deepest stage that failed, or `ok`.

    `des_err` is the DES slot's own error string: at generation time from the
    live stage dict, on a stored rep from `native.dt_slot_errors.des`.
    """
    if measured:
        return "ok", "KPIs produced from the DES model's stdout"
    if des_stage == "simulation_error":
        return "simulation_error", ("the generated DES model was executed and "
                                    "exited non-zero")
    if des_stage == "timeout":
        return "timeout", "the generated DES model exceeded its execution timeout"
    if des_stage == "error":
        # the model was written but the interpreter could not run it: the same
        # class of outcome A and B call a simulation error
        return "simulation_error", "the generated DES model could not be executed"
    if des_stage == "ran_no_contract":
        return "parse_error", "the DES model ran but printed no KPI contract"
    # no DES model exists: report why the slot that should have produced one
    # failed. An unreachable endpoint is availability, not a generation failure.
    if transport_named(des_err):
        return "service_unavailable", ("the DT agent's endpoint did not answer "
                                       "for the DES slot")
    if "timeout" in f"{des_err or ''} {db_note or ''}".lower():
        return "timeout", "a stage's task poll timed out"
    return "generation_error", "the DT agent produced no DES model"


def _des_err_from_note(note) -> tuple:
    """`(found, des_slot_error)` from a pre-2026-09-20 `native.dt_note`.

    Those blocks kept only the formatted note, whose slots are rendered
    `"<key>: <error>"` joined by `"; "`. Reading the `des` segment back out is
    best-effort on the adapter's own format, and is reported as such: when the
    note has no `des:` segment the verdict stays unknown rather than guessed.

    The adapter puts prose before the *first* segment
    (`"DT agent (agent 2) partial: config: ..."`), so when `des` is the first
    slot to fail the note reads `"... partial: des: <error>"` and no segment
    starts with `des:` until that prose is dropped — `"; "` alone is not a
    sufficient boundary.
    """
    parts = (note or "").split("; ")
    if parts and not parts[0].startswith("des: "):
        # strip the leading prose from the first segment only: `partition`
        # takes the first ": ", which is where the prefix ends and the first
        # `"<key>: <error>"` segment begins.
        _head, sep, rest = parts[0].partition(": ")
        if sep:
            parts[0] = rest
    for part in parts:
        if part.startswith("des: "):
            return True, part[len("des: "):]
    return False, None


def status_from_native(native: dict) -> tuple:
    """`(status, basis)` for a *stored* rep, from its `kpis.native` block alone.

    Returns `("unknown", reason)` when the block does not carry what the verdict
    needs: a pre-2026-09-20 block has `des_stage` but no `dt_slot_errors`, and
    only its formatted `dt_note` can supply the DES slot's error — if that note
    has no `des:` segment, whether the slot failed for an off-contract answer or
    an unreachable endpoint is not recoverable, and asserting either is a guess.
    """
    if not native or native.get("des_stage") in (None, "not_attempted"):
        return "unknown", "no stage evidence (mock or pre-stage native block)"
    des_stage = native.get("des_stage")
    measured = any(v is not None for v in (native.get("des_kpis") or {}).values())
    des_err = (native.get("dt_slot_errors") or {}).get("des")
    if not measured and des_stage not in _DECISIVE_DES_STAGES:
        # the block predates `dt_slot_errors`: fall back to the formatted note
        found, des_err = (_des_err_from_note(native.get("dt_note"))
                          if "dt_slot_errors" not in native else (True, des_err))
        if not found:
            return "unknown", ("block records no per-slot DT errors and its "
                               "`dt_note` names none for `des`, so the failed "
                               "stage cannot be identified")
    return derive_rep_status(measured, des_stage, native.get("db_note"), des_err)
