"""Method C adapter — DigitalTwinBuilder (remote multi-agent service).

CLI (run under any stdlib-only interpreter, e.g. /bin/python3):
    python method_c_adapter.py <mock|real> <bundle_dir> <work_dir> <rep>

Method C is NOT a discrete-event simulator: it is a remote FastAPI service
(`API_URL`, agents addressed by index) whose pipeline is

    agent 0  "UI agent"   interview (Russian system prompt) -> requirements JSON
    agent 1  "DB agent"    requirements -> PostgreSQL schema (CREATE/INSERT),
                           validated as SQL and re-asked for when rejected
    agent 2  "DT agent"    requirements + schema -> (conv 0) digital-twin config
                           JSON via `GenConf`/`make_gen_conf`, (conv 1) a
                           PyChrono multi-physics script via `GenSim`/
                           `make_gen_sim`, and (conv 2) a discrete-event SimPy
                           model via `GenDES`/`make_gen_des`; a local HF
                           transformers model

The method's own benchmark (benchmarks/simbench.py, tests/agents/llm-responder.py)
is J-LLM rubric scoring + JSON/SQL similarity — not KPI recovery. Two of the
three DT slots produce non-KPI artefacts: the twin configuration is a JSON
document and the PyChrono script is a rigid-body multi-physics model captured and
measured textually, never executed (no PyChrono on the harness host, and it
models geometry, not the discrete-event semantics of the truth engine).

The `GenDES` slot (conv 2) is the exception: it is asked for a discrete-event
model that prints a KPI contract, and when one is produced this adapter executes
it exactly as the B adapter executes B's model (subprocess, timeout, stdout
parsed with `parse_b_stdout`). Only then are throughput/WIP/energy-per-part
populated; if the slot fails, times out, or the model prints no contract, they
stay `null` (protocol §5: never fabricate). Alongside them the adapter always
reports structural recovery under `kpis.native`:

  * `machine_stats`  — per truth machine: mentioned in C's requirements? were its
                       process time / availability recovered verbatim?
  * `buffers`, `arrival_found`, `equipment_count`
  * `dt_structure`   — machine ids / PyChrono references in agent 2's output
  * `db_stage`, `db_gave_up_reason`
  * `des_stage`, `des_python`, `kpi_source`, `des_parse_error`
  * raw artefacts    — the requirements JSON, the DB schema, the twin config,
                       the PyChrono script, the DES model, the interview log

The interview "customer" is played by an LLM (the harness responder) seeded with
the case's own description, exactly as `tests/agents/llm-responder.py` plays it —
this is the protocol's *Autonomy* dimension, and the turn count is recorded. The
customer also speaks first: agent 0's prompt is an interview protocol that reacts
to a user turn, and a conversation holding only a system prompt gives it nothing
to analyse (see `_opening_message`).

Failures are typed. `service_unavailable` is the one that is not C's: it means
the remote host could not be reached after retries, so the rep measures the
deployment's availability rather than the method's generation behaviour.

Prompt fidelity: the UI/DB system prompts and `make_db_prompt()` are loaded at
runtime from the method's own `src/digital_twin_builder/prompts/*.py` (exec'd in
an isolated namespace) — the adapter never re-types method prompts.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "adapters"))

import adapters.base as B  # noqa: E402
from lib.envfile import load_env_file  # noqa: E402
from lib.simpleyaml import load_yaml  # noqa: E402

load_env_file()

CFG = load_yaml((ROOT / "config.yaml").read_text(encoding="utf-8"))
DTB_REPO = Path(CFG.get("dtb_repo", "/ssd/projects/DigitalTwinBuilder"))
C_CFG = CFG.get("C", {}) or {}
UI_AGENT = int(C_CFG.get("ui_agent_index", 0))
DB_AGENT = int(C_CFG.get("db_agent_index", 1))
DT_AGENT = int(C_CFG.get("dt_agent_index", 2))
POLL_TIMEOUT = float(C_CFG.get("poll_timeout_s", 300))
MAX_TURNS = int(C_CFG.get("max_interview_turns", 8))
MAX_TASK_RETRIES = int(C_CFG.get("max_task_retries", 3))
# The agent's own default is 1000 tokens (base_agent.process_task); reasoning
# preambles then truncate the reply mid-JSON. The DB call in the method's own
# test passes max_tokens, so passing it for the UI call is in-contract.
UI_MAX_TOKENS = int(C_CFG.get("ui_max_tokens", 4000))
# The method's own DB test calls the database agent with max_tokens 10000; a
# DDL document does not fit in the 1000-token default either.
DB_MAX_TOKENS = int(C_CFG.get("db_max_tokens", 10000))
# streamlit-app.py submits both DT slots with {"max_tokens": 3000} (its
# first-shot GenSim path passes {} — a 1000-token default that cannot hold a
# script; the method's own regenerate path uses 3000, which is what we use).
DT_MAX_TOKENS = int(C_CFG.get("dt_max_tokens", 3000))
DT_POLL_TIMEOUT = float(C_CFG.get("dt_poll_timeout_s", 900))
# The DES slot emits a full program, so it needs at least the PyChrono slot's
# budget; the generator may legitimately need more (helpers, several station
# classes, replication loop).
DES_MAX_TOKENS = int(C_CFG.get("des_max_tokens", 8000))
# Executing C's DES model is the same operation as executing B's, so it uses the
# same wall-clock budget unless C overrides it.
DES_EXEC_TIMEOUT = float(C_CFG.get("des_exec_timeout_s",
                                   (CFG.get("B", {}) or {}).get("exec_timeout_s", 900)))
# The generated model is SimPy code, so it cannot run under interpreters.C —
# that is the stdlib-only HTTP client for the remote service, and `import simpy`
# there is a ModuleNotFoundError, i.e. every compliant model would exit 1 and be
# recorded as a simulation error rather than as a measurement. C's *model* is
# executed exactly as B's is (llmdes_adapter.py:124-149), so it runs under a
# runtime that satisfies the imports the prompt mandates. Defaults to
# sys.executable so an unconfigured host degrades to the previous behaviour.
DES_PYTHON = str(C_CFG.get("des_python") or sys.executable)
# DES execute-and-repair, mirroring C's own DES stage as amended on 2026-09-20
# (dtb_repo .../des_runner.py, driven from streamlit-app.py::dt_generate_des).
# C now runs each returned program and feeds the execution output back to the
# DES conversation for a correction; the adapter reproduces that control flow
# faithfully (protocol.md §7) instead of taking C's first output as final. The
# count is *repairs*, so 3 allows 4 programs; 0 reproduces the pre-amendment
# one-shot behaviour and is what makes the before/after runs comparable.
DES_REPAIR_ATTEMPTS = int(C_CFG.get("des_repair_attempts", 0))
DES_REJECT_ALL_ZERO = bool(C_CFG.get("des_reject_all_zero", True))
# DB schema validate-and-repair, mirroring C's own DB stage as amended on
# 2026-09-21 (dtb_repo .../sql_runner.py, driven from
# streamlit-app.py::db_generate_schema). C now reads each reply as SQL and feeds
# the validation report back to the DB conversation for a correction; the
# adapter reproduces that control flow faithfully (protocol.md §7) instead of
# taking C's first reply as final. The count is *repairs*, so 3 allows 4
# replies; 0 reproduces the pre-amendment one-shot behaviour and is what makes
# the before/after runs comparable.
DB_REPAIR_ATTEMPTS = int(C_CFG.get("db_repair_attempts", 0))
RESPONDER_MODEL = C_CFG.get("responder_model", "openai/gpt-5-mini")
# agent 2's conversation slots: what each one is asked to produce
DT_SLOT_KEYS = ("config", "sim", "des")
HTTP_TIMEOUT = float(C_CFG.get("http_timeout_s", 30))
# The remote service intermittently refuses or times out connections (observed
# in the 2026-09-19 real run: bare `URLError: <urlopen error timed out>` from
# the reachability probe / `new_session`, and `Network is unreachable`). A rep
# lost that way measured the host, not the method, so these calls are retried.
# Only reads and session/conversation creation are retried: they are safe to
# repeat, unlike a task submission, which would bill the model twice.
NET_RETRIES = int(C_CFG.get("net_retries", 4))
NET_RETRY_DELAY = float(C_CFG.get("net_retry_delay_s", 5.0))
# Transport failures: the host never answered. `HTTPError` is a `URLError`
# subclass but is deliberately excluded — a status code means the service did
# answer, so it is not a reachability failure.
TRANSPORT_ERRORS = (urllib.error.URLError, ConnectionError, TimeoutError, OSError)
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class ServiceUnavailable(ConnectionError):
    """A remote dependency never answered: the C endpoint, or the harness's own
    responder LLM at OpenRouter.

    Subclasses `ConnectionError` so it is already inside `TRANSPORT_ERRORS` — the
    raiser and the classifier at the end of `generate` agree by construction
    rather than by both remembering the same tuple. `dependency` names which
    remote service was down, so the recorded note cannot blame the wrong host.
    """

    def __init__(self, dependency: str, cause: BaseException):
        super().__init__(f"{dependency}: {type(cause).__name__}: {cause}")
        self.dependency = dependency


# --------------------------------------------------------------------------- #
# tiny stdlib HTTP client (no requests/openai dependency)
# --------------------------------------------------------------------------- #
def _http(method: str, url: str, body=None, params=None, timeout=None,
          retries: int = 0) -> object:
    """One request. `retries` re-attempts on a transport failure only; the
    caller passes it for calls that are safe to repeat (never task submission).
    """
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    attempt = 0
    while True:
        try:
            with urllib.request.urlopen(req, timeout=timeout or HTTP_TIMEOUT) as resp:
                raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else None
        except urllib.error.HTTPError:
            raise                      # the service answered; not transport
        except TRANSPORT_ERRORS:
            attempt += 1
            if attempt > retries:
                raise
            time.sleep(NET_RETRY_DELAY)


def api_url() -> str:
    """Live endpoint from the method's own `.env` (repo copy wins; env override)."""
    env_p = DTB_REPO / ".env"
    url = None
    if env_p.exists():
        for line in env_p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("API_URL=") :
                url = line.split("=", 1)[1].strip().strip('"').strip("'")
    return (os.environ.get("DIGITAL_TWIN_API_URL") or url
            or "http://localhost:8000").rstrip("/")


# --------------------------------------------------------------------------- #
# method prompts, loaded from the method's repo
# --------------------------------------------------------------------------- #
def _exec_prompt_module(rel: str, extra_ns: dict | None = None) -> dict:
    path = DTB_REPO / "src" / "digital_twin_builder" / "prompts" / rel
    ns: dict = {"__name__": "dtb_prompts"}
    if extra_ns:
        ns.update(extra_ns)
    exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), ns)
    return ns


def load_prompts() -> dict:
    sys_ns = _exec_prompt_module("system.py")
    usr_ns = _exec_prompt_module("user.py", {"json": json})
    return {"UI": sys_ns["UI"], "DB": sys_ns["DB"],
            "GenConf": sys_ns["GenConf"], "GenSim": sys_ns["GenSim"],
            "GenDES": sys_ns["GenDES"],
            "make_db_prompt": usr_ns["make_db_prompt"],
            "make_gen_conf": usr_ns["make_gen_conf"],
            "make_gen_sim": usr_ns["make_gen_sim"],
            "make_gen_des": usr_ns["make_gen_des"],
            "make_gen_des_repair": usr_ns["make_gen_des_repair"],
            "make_db_repair": usr_ns["make_db_repair"]}


# --------------------------------------------------------------------------- #
# agent conversation primitives (mirror src/digital_twin_builder/api_utils.py)
# --------------------------------------------------------------------------- #
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def _strip_think(text: str) -> str:
    """The deployed UI agent emits `<think>…</think>` reasoning; it may contain
    braces and would otherwise break naive first-brace/last-brace extraction."""
    text = _THINK_RE.sub(" ", text)
    text = re.sub(r"</?think>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"^```(?:json)?|```$", " ", text, flags=re.MULTILINE)
    return text


def _brace_objects(text: str):
    """Yield brace-balanced substrings, outermost first."""
    depth = 0
    start = None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth:
            depth -= 1
            if depth == 0 and start is not None:
                yield text[start:i + 1]
                start = None


def _get_json(message: str):
    """Best-effort JSON object from an agent message (protocol mirrors the
    method's own tests/agents/llm-responder.py::get_json, hardened for think
    blocks and prose)."""
    if not message:
        return None
    cleaned = _strip_think(message)
    try:
        obj = json.loads(cleaned.strip())
        if isinstance(obj, dict):
            return obj
    except ValueError:
        pass
    fallback = None
    for cand in _brace_objects(cleaned):
        try:
            obj = json.loads(cand)
        except ValueError:
            continue
        if not isinstance(obj, dict):
            continue
        if "completed" in obj or "requirements" in obj:
            return obj
        if fallback is None:
            fallback = obj
    return fallback


def new_session(base: str) -> str:
    r = _http("POST", f"{base}/sessions",
              params={"user_id": "dt-eval", "title": "dt-eval comparison"},
              retries=NET_RETRIES)
    return r["session_id"]


def new_conversation(base: str, session_id: str, agent_id: int, system_prompt: str,
                     conv_idx: int = 0) -> str:
    r = _http("POST", f"{base}/conversations",
              params={"session_id": session_id, "agent_id": agent_id,
                      "conv_idx": conv_idx},
              retries=NET_RETRIES)
    cid = r["conversation_id"]
    _http("POST", f"{base}/conversations/{cid}/messages",
          body={"role": "system", "content": system_prompt},
          retries=NET_RETRIES)
    return cid


def add_message(base: str, cid: str, role: str, content: str) -> None:
    _http("POST", f"{base}/conversations/{cid}/messages",
          body={"role": role, "content": content})


def run_agent(base: str, agent_id: int, cid: str, params: dict,
              poll_timeout: float, conv_idx: int = 0) -> dict:
    """submit_task + poll_task_result, with an explicit status/error result."""
    task = _http("POST", f"{base}/tasks",
                 body={"agent_id": agent_id, "conv_idx": conv_idx,
                       "conversation_id": cid, "params": params, "priority": 5})
    if not task or not task.get("task_id"):
        return {"error": "task submission failed", "elapsed_s": 0.0}
    tid = task["task_id"]
    t0 = time.perf_counter()
    deadline = t0 + poll_timeout
    while time.perf_counter() < deadline:
        try:
            st = _http("GET", f"{base}/tasks/{tid}", retries=NET_RETRIES)
        except urllib.error.HTTPError as e:      # 404 while pending
            if e.code not in (404, 425):
                return {"error": f"poll HTTP {e.code}", "task_id": tid,
                        "elapsed_s": round(time.perf_counter() - t0, 3)}
            st = None
        if st and st.get("status") == "completed":
            return {"result": st.get("result", ""), "task_id": tid,
                    "elapsed_s": round(time.perf_counter() - t0, 3)}
        if st and st.get("status") == "failed":
            return {"error": f"agent task failed: {st.get('error')}",
                    "task_id": tid, "elapsed_s": round(time.perf_counter() - t0, 3)}
        time.sleep(1.0)
    return {"error": f"poll timeout after {poll_timeout}s", "task_id": tid,
            "elapsed_s": round(time.perf_counter() - t0, 3)}


def agent_status(base: str, agent_id: int) -> str:
    """Role/status of one agent on the deployment.

    A transport failure propagates instead of being flattened to the string
    "unreachable": a host that never answered is an availability fact about the
    deployment, and `generate` records it as `service_unavailable`. Swallowing it
    here instead charges a dead host to C as a generation error, because the
    caller's offline check raises a plain `RuntimeError`. That check is about a
    *responding* deployment whose agent indices are misconfigured — a different
    thing, and the only case it should now fire.
    """
    return str(_http("GET", f"{base}/agents/{agent_id}/status",
                     retries=NET_RETRIES).get("status"))


# --------------------------------------------------------------------------- #
# the harness "customer" that answers C's interview
# --------------------------------------------------------------------------- #
# The customer is a real person doing a requirements interview, so it must answer
# the questions that a plant engineer can always answer about its own intent —
# otherwise C stalls asking for goals the case bundle has no ground truth for.
# These answers are fixed harness text, identical for every case/rep, and they
# carry no information that is scored against truth (see protocol §3).
_RESPONDER_POLICY = (
    "Если спросят о целях цифрового двойника — ответь: цель состоит в том, чтобы "
    "оценивать пропускную способность линии, незавершённое производство (WIP) и "
    "удельное энергопотребление на деталь, а также отслеживать доступность "
    "машин M1-M5.\n"
    "Если спросят о частоте обновления данных — ответь: события регистрируются "
    "по каждой обработанной детали, интервалы состояний и энергопотребление "
    "записываются непрерывно.\n"
    "Если спросят о порогах тревог, предупреждениях, интеграциях или иных "
    "данных, которых нет в описании — ответь, что они не определены, и попроси "
    "построить модель по уже предоставленным параметрам.\n"
    "На все остальные вопросы отвечай по существу, используя только описание и "
    "параметры ниже."
)


def _case_facts(bundle: Path, manifest: dict) -> tuple[str, str]:
    """The plant description and its exact parameters in the two forms the
    interview needs: the prose method A is also given, and the manifest's
    normalised values. Kept in one place so the responder's prompt and the
    engineer's opening statement cannot drift apart."""
    facts = (bundle / "prompt_A.txt").read_text(encoding="utf-8")
    truth = json.dumps(
        {"arrival": manifest.get("arrival"), "machines": manifest.get("machines"),
         "buffers": manifest.get("buffers")}, ensure_ascii=False, indent=2)
    return facts, truth


def _opening_message(bundle: Path, manifest: dict) -> str:
    """The engineer's opening statement: the interview's first user turn.

    `system.py::UI` is an interview protocol — it analyses "ответ пользователя",
    completes only when the information suffices, and otherwise returns
    `completed: false` with questions. `_interview` used to poll agent 0 over a
    conversation holding nothing but the system prompt, so there was no user
    turn to analyse. The agent then either fabricated `completed: true` over the
    unfilled template (observed 2026-09-19: every numeric field null, only the
    prompt's example station) or truthfully asked for the missing data and was
    recorded as a generation error. Both paths handed the DES slot a null
    skeleton. The engineer therefore speaks first, with the same description
    method A receives.
    """
    facts, truth = _case_facts(bundle, manifest)
    return ("Здравствуйте! Мне нужно построить цифровой двойник производственной "
            "линии. Ниже — описание системы и точные параметры оборудования, "
            "которые мне известны.\n\n" + facts +
            "\n\nТочные параметры:\n```json\n" + truth + "\n```")


def _responder_system_prompt(bundle: Path, manifest: dict) -> str:
    facts, truth = _case_facts(bundle, manifest)
    return (
        "Ты — инженер производственного участка. Отвечай на заданные вопросы, "
        "беря информацию только из приведённых ниже описания системы и "
        "параметров.\nНельзя придумывать новую информацию, если её нет в "
        "описании.\nНЕ используй markdown форматирование в ответе. Отвечай "
        "кратко и по существу, только ответы на вопросы, без повторения "
        "вопросов.\n\n" + _RESPONDER_POLICY +
        "\n\nОписание системы:\n" + facts +
        "\n\nТочные параметры (используй эти значения):\n```json\n" + truth + "\n```"
    )


def _respond(model: str, messages: list) -> str:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not set (responder LLM unavailable)")
    req = urllib.request.Request(
        OPENROUTER_URL,
        data=json.dumps({"model": model, "messages": messages,
                         "stream": False}).encode("utf-8"),
        method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("HTTP-Referer", os.environ.get("HTTP_REFERER", "http://localhost"))
    req.add_header("X-Title", "dt-eval")
    with urllib.request.urlopen(req, timeout=180) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return payload["choices"][0]["message"]["content"]


# --------------------------------------------------------------------------- #
# generation
# --------------------------------------------------------------------------- #
def _interview(base: str, session_id: str, prompts: dict, bundle: Path,
               manifest: dict, log: list) -> dict:
    """Drive agent 0 to a completed requirements JSON. Returns dict with
    requirements/turns/agent_calls/responder_calls or an error.

    `agent_calls` counts service tasks that returned a result (retries included,
    so it is the true cost of the UI stage); `responder_calls` counts answers
    the harness LLM actually produced. Keeping them separate matters because a
    retry inflates the former without adding an interview turn.
    """
    cid = new_conversation(base, session_id, UI_AGENT, prompts["UI"])
    log.append(("system", "UI agent conversation created", cid))
    responder_prompt = _responder_system_prompt(bundle, manifest)
    log.append(("system", "harness responder system prompt", responder_prompt))
    # The engineer speaks first. Without a user turn the UI agent has nothing to
    # analyse, so it cannot run the interview protocol its own prompt encodes.
    opening = _opening_message(bundle, manifest)
    add_message(base, cid, "user", opening)
    log.append(("user", opening, "opening statement"))
    messages = [{"role": "system", "content": responder_prompt}]
    calls = 0
    responds = 0
    for turn in range(MAX_TURNS + 1):
        # the agent is stochastic (and reasoning-wrapped): retry unparseable replies
        parsed, result, err = None, "", None
        for attempt in range(MAX_TASK_RETRIES):
            task = run_agent(base, UI_AGENT, cid,
                             {"max_tokens": UI_MAX_TOKENS}, POLL_TIMEOUT)
            if "error" in task:
                err = task["error"]
                break
            calls += 1
            result = task.get("result") or ""
            log.append(("agent", result,
                        f"turn {turn} attempt {attempt + 1}"))
            parsed = _get_json(result)
            if parsed is not None:
                break
        if err is not None:
            return {"error": err, "turns": turn, "agent_calls": calls,
                    "responder_calls": responds, "cid": cid}
        if parsed is None:
            return {"error": f"agent returned non-JSON after "
                             f"{MAX_TASK_RETRIES} attempts: {result[:300]}",
                    "turns": turn, "agent_calls": calls,
                    "responder_calls": responds, "cid": cid}
        if parsed.get("completed"):
            return {"requirements": parsed.get("requirements"),
                    "turns": turn + 1, "agent_calls": calls,
                    "responder_calls": responds, "cid": cid,
                    "final_message": parsed.get("message", "")}
        if turn >= MAX_TURNS:
            break
        question = str(parsed.get("message", ""))
        messages.append({"role": "user", "content": question})
        try:
            answer = _respond(RESPONDER_MODEL, messages)
        except Exception as e:  # noqa: BLE001
            if isinstance(e, TRANSPORT_ERRORS):
                # The harness's own dependency (OpenRouter) was unreachable, not
                # C's endpoint. Still an availability failure and so still not
                # charged to C — but it must be raised, not returned as an error
                # string, or `generate` wraps it in a RuntimeError and records it
                # as a generation error (observed in the 2026-09-19 real run as
                # `responder LLM failed: URLError: Network is unreachable`).
                raise ServiceUnavailable(
                    "harness responder LLM (OpenRouter)", e) from e
            return {"error": f"responder LLM failed: {type(e).__name__}: {e}",
                    "turns": turn, "agent_calls": calls,
                    "responder_calls": responds, "cid": cid}
        responds += 1
        messages.append({"role": "assistant", "content": answer})
        log.append(("responder", answer, f"turn {turn}"))
        add_message(base, cid, "user", answer)
    return {"error": f"interview did not complete within {MAX_TURNS} turns",
            "turns": MAX_TURNS + 1, "agent_calls": calls,
            "responder_calls": responds, "cid": cid}


def _schema(base: str, session_id: str, prompts: dict, requirements: dict,
            log: list) -> dict:
    """Run agent 1 (DB) on the collected requirements, then validate and repair.

    The stage's contract is SQL. C's own DB prompt asks for PostgreSQL (`DB` in
    dtb_repo/src/digital_twin_builder/prompts/system.py: "generate complete SQL
    code ... Return only the SQL code without markdown formatting"), and since
    2026-09-21 C also *reads* the reply as SQL: every reply is validated and a
    rejected one is sent back to the same conversation with the validation
    report until it holds together or the attempts run out
    (streamlit-app.py::db_generate_schema -> sql_runner.generate_with_repair).
    This reproduces that control flow instead of taking the first reply as
    final; with `db_repair_attempts: 0` it reproduces the pre-amendment
    one-shot behaviour instead (protocol.md §7.6).

    The artefact of this stage is the agent's own reply, so `schema_raw` is what
    the caller records and what the DT stage is fed — not `_get_json`'s
    extraction from it, which can be a fragment of the reply or nothing at all.
    That settles the question protocol.md §7.6 left open on 2026-09-18.

    Distinguishes the outcomes the caller has to tell apart: task failure
    (reported by the service, e.g. a CUDA/device error inside the agent), an
    empty result, and a reply that does or does not read as a usable schema.
    """
    cid = new_conversation(base, session_id, DB_AGENT, prompts["DB"])
    add_message(base, cid, "user", prompts["make_db_prompt"](requirements))
    task = run_agent(base, DB_AGENT, cid, {"max_tokens": DB_MAX_TOKENS}, POLL_TIMEOUT)
    # `calls` counts submissions that returned a result; `attempts` counts every
    # submission. They differ when the task failed or timed out (the host leaves
    # such tasks `processing` forever), and the caller must be able to tell a
    # stage that produced nothing from a stage that was never reached.
    if "error" in task:
        log.append(("error", task["error"], "db agent"))
        return {"error": task["error"], "attempts": 1, "calls": 0, "cid": cid,
                "schema_raw": "", "sql_attempts": [], "sql_ok": False,
                "sql_report": "", "sql_summary": {}}
    raw = task.get("result") or ""
    log.append(("agent", raw or "(empty result)", "db agent"))
    out = {"error": None if raw.strip() else "agent returned an empty result",
           "attempts": 1, "calls": 1, "cid": cid, "schema_raw": raw,
           "sql_attempts": [], "sql_ok": False, "sql_report": "", "sql_summary": {}}
    if raw.strip():
        _repair_schema(base, cid, prompts, requirements, log, out, raw)
    else:
        # nothing came back to validate: there is no reply to correct, and a
        # repair turn would be asked blind
        out["sql_report"] = ("The agent returned no schema for this turn (its "
                             "task failed or returned an empty result), so "
                             "there was nothing to validate.")
    return out


def _schema_text(db: dict, schema) -> str:
    """The schema string the DT stage is fed: exactly what streamlit passes as
    `st.session_state.db_schema` (the DB agent's own text, not a re-rendering)."""
    raw = db.get("schema_raw")
    if raw and raw.strip():
        return raw
    if isinstance(schema, dict) and "raw" in schema:
        return str(schema.get("raw") or "")
    return json.dumps(schema, ensure_ascii=False, indent=2) if schema else ""


def _horizon(manifest: dict) -> dict:
    """The simulation horizon C is told to use, taken from the case's `reference`.

    The reference plant simulates `warmup_s + window_s` and reports KPIs over
    `[warmup_s, warmup_s + window_s]` (truth/plant.py:144, :401), so a DES model
    given a different horizon is not making the same measurement — measured over
    the whole run, WIP in particular is a different number. The B adapter already
    passes B exactly these values (llmdes_adapter.py:42-67) for that reason; C
    gets the same input so the two are comparable. This is the *measurement
    definition*, not case ground truth: no KPI value is disclosed.

    `replications` is a modelling choice for C's own averaging, not a truth
    parameter, so it uses config's default rather than `reference.replications`.
    """
    ref = manifest.get("reference") or {}
    warmup_s = ref.get("warmup_s")
    window_s = ref.get("window_s")
    # Fallback to config's B block, the same values the B adapter falls back to
    # (llmdes_adapter.py:35-36), so a bundle without a `reference` still gets
    # both methods the same horizon rather than C getting a different one.
    b_cfg = CFG.get("B", {}) or {}
    default_warmup = int(b_cfg.get("warmup_s", 24 * 3600))
    default_sim = int(b_cfg.get("sim_time_s", 8 * 24 * 3600))
    # `is None` rather than truthiness: a reference that genuinely says
    # `warmup_s: 0` must be honoured, not swapped for a default.
    warmup = default_warmup if warmup_s is None else int(warmup_s)
    # B reads this as a *total*: sim_time = SIM_TIME when window_s is absent,
    # else warmup + window_s (llmdes_adapter.py:66). The window is therefore
    # SIM_TIME - warmup in the absent case, using the warm-up actually chosen —
    # not SIM_TIME - default_warmup, which would hand C a different window
    # whenever the reference sets warmup_s without window_s.
    window = (default_sim - warmup) if window_s is None else int(window_s)
    return {"warmup_s": warmup, "window_s": window,
            "replications": int(C_CFG.get("des_replications", 10))}


def _des_kpis_from_exec(exec_res: dict | None) -> dict:
    """The KPIs of an execution result, or {} when it did not run cleanly."""
    if not exec_res or exec_res.get("status") != "ok":
        return {}
    return B.parse_b_stdout(exec_res.get("stdout") or "")


# How much of a traceback is fed back to the agent. Mirrors the limit C's own
# runner uses (dtb_repo .../des_runner.py: REPORT_CHARS), so the same message
# goes to the model whether the loop runs in C's app or in this adapter.
DES_REPORT_CHARS = 4000


def _des_gate() -> dict:
    """C's own DES acceptance gate, loaded from the method's repo.

    The gate is one implementation, not two: the adapter calls the same functions
    the deployed app calls (`des_runner._all_zero_implausible` and
    `des_runner._implausible_kpis`) instead of keeping a copy that can drift.
    Same arrangement as `load_prompts` — the file is read from `DTB_REPO` at run
    time, so a change to the gate takes effect in the comparison without an edit
    here, and a rep cannot pass a check here that it would fail in C's own app.
    """
    global _DES_GATE
    if _DES_GATE is None:
        path = DTB_REPO / "src" / "digital_twin_builder" / "des_runner.py"
        ns: dict = {"__name__": "dtb_des_runner", "__file__": str(path)}
        exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), ns)
        _DES_GATE = ns
    return _DES_GATE


_DES_GATE: dict | None = None


def _sql_gate() -> dict:
    """C's own DB schema verdict, loaded from the method's repo.

    The verdict is one implementation, not two: the adapter runs the checks the
    deployed app runs (`sql_runner.check` / `verify`) instead of keeping a copy
    that can drift — the same arrangement as `_des_gate`, so a reply cannot pass
    here that C's own front end would reject. Parse-only and stdlib-only, in the
    adapter exactly as in the app: no server is contacted and no SQL is run.
    """
    global _SQL_GATE
    if _SQL_GATE is None:
        path = DTB_REPO / "src" / "digital_twin_builder" / "sql_runner.py"
        ns: dict = {"__name__": "dtb_sql_runner", "__file__": str(path)}
        exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), ns)
        _SQL_GATE = ns
    return _SQL_GATE


_SQL_GATE: dict | None = None


def _repair_schema(base: str, cid: str, prompts: dict, requirements: dict,
                   log: list, out: dict, first_raw: str) -> None:
    """Validate the DB agent's reply and ask for a corrected one while it fails.

    This reproduces C's amended DB stage (dtb_repo .../sql_runner.py driven from
    streamlit-app.py::db_generate_schema): each reply is validated as soon as it
    arrives and the validation report is appended to the *same* conversation so
    the agent corrects the defect it can see. Only the final reply is left in
    `out["schema_raw"]`, because that is the artefact C now hands on.

    The conversation, the message construction and the attempt count all come
    from C's own repo; this is a faithful reproduction of its control flow, not
    an alternative one chosen here. The verdict is C's own (`sql_runner.verify`),
    so a schema cannot pass here that the method's app would reject.
    """
    gate = _sql_gate()
    attempts: list[dict] = []
    raw = first_raw
    for i in range(max(DB_REPAIR_ATTEMPTS, 0) + 1):
        verdict = gate["verify"](raw)
        report = None if verdict["ok"] else verdict["report"]
        attempts.append({"attempt": i, "chars": len(raw), "ok": verdict["ok"],
                         "repair_reason": report,
                         "summary": verdict.get("summary") or {}})
        log.append(("check", (f"schema attempt {i}: "
                              + ("reads as SQL" if verdict["ok"] else
                                 f"rejected — {report[:400]}")),
                    "db agent schema"))
        if verdict["ok"] or i >= DB_REPAIR_ATTEMPTS:
            break
        try:
            add_message(base, cid, "user",
                        prompts["make_db_repair"](requirements, raw, report,
                                                  i + 1, DB_REPAIR_ATTEMPTS))
            out["attempts"] += 1
            task = run_agent(base, DB_AGENT, cid, {"max_tokens": DB_MAX_TOKENS},
                             POLL_TIMEOUT)
        except Exception as e:  # noqa: BLE001
            log.append(("error", f"{type(e).__name__}: {e}", "db agent repair"))
            attempts[-1]["repair_error"] = f"{type(e).__name__}: {e}"
            break
        if "error" in task:
            log.append(("error", task["error"], "db agent repair"))
            attempts[-1]["repair_error"] = task["error"]
            break
        out["calls"] += 1
        raw = task.get("result") or ""
        log.append(("agent", raw or "(empty result)", "db agent repair"))
        if not raw.strip():
            attempts[-1]["repair_error"] = "repair turn returned an empty result"
            break
    out["schema_raw"] = raw
    out["sql_attempts"] = attempts
    out["sql_ok"] = bool(attempts and attempts[-1]["ok"])
    out["sql_report"] = "" if out["sql_ok"] else (attempts[-1]["repair_reason"] or "")
    out["sql_summary"] = attempts[-1].get("summary") or {}
    out["error"] = None if raw.strip() else "agent returned an empty result"


def _des_repair_report(exec_res: dict | None, kpis: dict,
                       requirements: dict) -> str | None:
    """Why the DES stage failed, worded as the follow-up message to the agent.

    None when there is nothing to repair. The verdict is C's own
    (`des_runner.verify`): a program that did not exit cleanly, a program that
    printed no KPI contract at all, one that printed three zeros it cannot have
    measured (when `des_reject_all_zero` is on), and — since 2026-09-21 — one
    whose printed numbers contradict the line it was given.

    The last of those is what the amended stage was missing: case_0005's first
    program divided nothing by the measurement window and printed a 126-hour part
    count as `Throughput = 5666.2 parts/hour`, ran cleanly, and was accepted.
    """
    if exec_res is None:
        return ("The program was never executed, so it has not been shown to "
                "run at all.")
    if exec_res.get("status") != "ok":
        detail = (exec_res.get("stdout") or "").strip()
        return (f"The program did not complete: {exec_res.get('error')}.\n\n"
                f"Output (last {DES_REPORT_CHARS} characters):\n"
                f"{detail[-DES_REPORT_CHARS:] or '(no output)'}")
    missing = [name for name, key in (
        ("Throughput", "throughput_per_hour"),
        ("WIP", "wip_parts"),
        ("Mean Energy Consumption per Part", "energy_per_part_kwh"))
        if kpis.get(key) is None]
    if missing:
        tail = (exec_res.get("stdout") or "").strip()[-DES_REPORT_CHARS:] or "(no output)"
        return ("The program exited without printing "
                f"{' and '.join(missing)} as the last line(s) of stdout. "
                "Every one of the three KPI lines must be printed, exactly in "
                "the required form, and nothing may print them twice.\n\n"
                f"Program output (last {DES_REPORT_CHARS} characters):\n{tail}")
    gate = _des_gate()
    reason = None
    if DES_REJECT_ALL_ZERO:
        reason = gate["_all_zero_implausible"](kpis, requirements)
    if reason is None:
        reason = gate["_implausible_kpis"](kpis, requirements)
    if reason:
        return (reason + ".\n\nProgram output:\n"
                f"{(exec_res.get('stdout') or '').strip()[-DES_REPORT_CHARS:]}")
    return None


def _repair_des(base: str, cid: str, prompts: dict, req_in: dict,
                schema_text: str, log: list, out: dict, workdir: Path,
                requirements: dict, first_raw: str) -> None:
    """Run the DES program and ask for a corrected one while it fails.

    This reproduces C's amended DES stage (dtb_repo .../des_runner.py driven
    from streamlit-app.py::dt_generate_des): the program is executed as soon as
    it arrives, and the execution output is appended to the *same* conversation
    so the agent corrects the defect it can see. Only the final program is left
    in `out["des"]`, and only its execution logs remain on disk, because that is
    the artefact C now hands on.

    The conversation, the message construction and the attempt count all come
    from C's own repo; this is a faithful reproduction of its control flow, not
    an alternative one chosen here.
    """
    slot = out["des"]
    attempts: list[dict] = []
    raw = first_raw
    exec_res = None
    kpis: dict = {}
    exec_elapsed = 0.0
    for i in range(max(DES_REPAIR_ATTEMPTS, 0) + 1):
        exec_res = _execute_des(raw, workdir)
        kpis = _des_kpis_from_exec(exec_res)
        exec_elapsed += exec_res["elapsed_s"]
        report = _des_repair_report(exec_res, kpis, requirements)
        attempts.append({"attempt": i, "status": exec_res["status"],
                         "chars": len(raw), "ran_ok": report is None,
                         "elapsed_s": exec_res["elapsed_s"],
                         "repair_reason": report})
        log.append(("exec", (f"des attempt {i}: {exec_res['status']}"
                             + ("" if report is None else f" — {report[:400]}")),
                    "dt agent des"))
        if report is None or i >= DES_REPAIR_ATTEMPTS:
            break
        try:
            add_message(base, cid, "user",
                        prompts["make_gen_des_repair"](
                            req_in, schema_text, raw, report, i + 1,
                            DES_REPAIR_ATTEMPTS))
            out["attempts"] += 1
            task = run_agent(base, DT_AGENT, cid, {"max_tokens": DES_MAX_TOKENS},
                             DT_POLL_TIMEOUT, 2)
        except Exception as e:  # noqa: BLE001
            log.append(("error", f"{type(e).__name__}: {e}", "dt agent des repair"))
            attempts[-1]["repair_error"] = f"{type(e).__name__}: {e}"
            break
        if "error" in task:
            log.append(("error", task["error"], "dt agent des repair"))
            attempts[-1]["repair_error"] = task["error"]
            break
        out["calls"] += 1
        raw = task.get("result") or ""
        log.append(("agent", raw or "(empty result)", "dt agent des repair"))
        if not raw.strip():
            attempts[-1]["repair_error"] = "repair turn returned an empty result"
            break
    slot["raw"] = raw
    slot["exec"] = exec_res
    slot["kpis"] = kpis
    slot["attempts"] = attempts
    slot["exec_elapsed_s"] = round(exec_elapsed, 3)
    slot["elapsed_s"] = (slot.get("elapsed_s") or 0.0) + exec_res["elapsed_s"]
    slot["error"] = None if raw.strip() else "agent returned an empty result"
    # What, if anything, C still could not fix. A run that ends here with a
    # reason recorded gave up on a program that does not run (or does not
    # report); a run with no reason succeeded on its first or a repaired
    # program. Kept so the residual error rate can be read off the data
    # without re-deriving it from the KPIs.
    slot["gave_up_reason"] = None if attempts[-1]["ran_ok"] else attempts[-1]["repair_reason"]


def _dt_stage(base: str, session_id: str, prompts: dict, requirements: dict,
              schema_text: str, log: list, manifest: dict,
              workdir: Path | None = None) -> dict:
    """Run agent 2 (DT) through its conversation slots, as the method does in
    streamlit-app.py: conv 0 = twin configuration JSON (GenConf), conv 1 =
    PyChrono script (GenSim), conv 2 = discrete-event SimPy model (GenDES). All
    are fed (requirements, db_schema).

    Each slot is independent: one may succeed while the others fail, so all
    outcomes are kept rather than collapsed into a single status.

    The DES slot additionally carries C's execute-and-repair loop (`_repair_des`)
    when a workdir is given, because since 2026-09-20 C runs the program it is
    handed and asks for a correction while it fails.
    """
    horizon = _horizon(manifest)
    out: dict = {"attempts": 0, "calls": 0}
    for key, sys_key, builder, cidx in (
            ("config", "GenConf", "make_gen_conf", 0),
            ("sim", "GenSim", "make_gen_sim", 1),
            ("des", "GenDES", "make_gen_des", 2)):
        # The DES slot is the only one whose output is a measurement input, so
        # it is the only one fed the horizon. Passing it to the others would
        # change their prompts mid-study for no measurement gain.
        req_in = (dict(requirements, des_horizon=horizon)
                  if key == "des" else requirements)
        max_tokens = DES_MAX_TOKENS if key == "des" else DT_MAX_TOKENS
        try:
            cid = new_conversation(base, session_id, DT_AGENT, prompts[sys_key], cidx)
            add_message(base, cid, "user",
                        prompts[builder](req_in, schema_text))
            task = run_agent(base, DT_AGENT, cid,
                             {"max_tokens": max_tokens}, DT_POLL_TIMEOUT, cidx)
        except Exception as e:  # noqa: BLE001
            log.append(("error", f"{type(e).__name__}: {e}", f"dt agent {key}"))
            out[key] = {"error": f"{type(e).__name__}: {e}"}
            continue
        out["attempts"] += 1
        if "error" in task:
            log.append(("error", task["error"], f"dt agent {key}"))
            out[key] = {"error": task["error"], "elapsed_s": task.get("elapsed_s")}
            continue
        out["calls"] += 1
        raw = task.get("result") or ""
        log.append(("agent", raw or "(empty result)", f"dt agent {key}"))
        out[key] = {"raw": raw, "elapsed_s": task.get("elapsed_s"),
                    "error": None if raw.strip() else "agent returned an empty result"}
        if key == "des" and raw.strip() and workdir is not None:
            # The DES slot is the only one whose output is executable, so it is
            # the only one C corrects: run it, and hand the execution output
            # back to the same conversation until it runs and reports.
            _repair_des(base, cid, prompts, req_in, schema_text, log, out,
                        workdir, requirements, raw)
    return out


def _execute_des(code: str, workdir: Path) -> dict:
    """Run C's DES model as a subprocess and parse its KPI contract.

    Same treatment as B's model (llmdes_adapter.py:124-149): the generated code
    is run, not inspected, and its stdout is read with the shared contract
    parser. Returns stdout plus a status; never raises for a model error — a
    model that does not run is a measurement, not an adapter crash.
    """
    run_file = workdir / "run_des_model.py"
    run_file.write_text(B.strip_code_fence(code), encoding="utf-8")
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            [DES_PYTHON, str(run_file)],
            cwd=str(workdir), capture_output=True, text=True,
            timeout=DES_EXEC_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return {"stdout": "", "status": "timeout",
                "error": f"DES model exceeded {DES_EXEC_TIMEOUT}s",
                "elapsed_s": round(time.perf_counter() - t0, 3)}
    except OSError as e:
        return {"stdout": "", "status": "error",
                "error": f"{type(e).__name__}: {e}",
                "elapsed_s": round(time.perf_counter() - t0, 3)}
    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    (workdir / "exec_des_stdout.log").write_text(stdout, encoding="utf-8")
    (workdir / "exec_des_stderr.log").write_text(stderr, encoding="utf-8")
    out = {"stdout": stdout, "elapsed_s": round(time.perf_counter() - t0, 3)}
    if proc.returncode != 0:
        out["status"] = "simulation_error"
        out["error"] = f"DES model exited {proc.returncode}: {stderr[-4000:]}"
    else:
        out["status"] = "ok"
        out["error"] = None
    return out


def extract_dt_structure(dt: dict | None, manifest: dict) -> dict:
    """What agent 2's own output says about the case. Textual measurement only:
    the PyChrono script is never executed (see the module docstring).

    Deliberately restricted to the config and PyChrono slots. The DES slot is
    excluded even though it is the richest artefact for topology: folding it in
    would silently raise this indicator for every case (more text, more id
    mentions) and make runs before and after that change incomparable. Its shape
    is reported separately, as `stage_shapes.dt_des`.
    """
    if not dt:
        return {}
    blobs = {k: (dt.get(k) or {}).get("raw") or ""
             for k in ("config", "sim") if isinstance(dt.get(k), dict)}
    blob = "\n".join(blobs.values())
    ids = {str(m["id"]): _mentions(blob, str(m["id"]))
           for m in manifest.get("machines", [])}
    return {
        "artifact_chars": {k: len(v) for k, v in blobs.items()},
        "machine_ids_in_dt_output": ids,
        "machines_mentioned_in_dt": sum(1 for v in ids.values() if v),
        "machines_truth": len(manifest.get("machines", [])),
        "pychrono_referenced": bool(
            re.search(r"pychrono|import\s+chrono|chrono\.", blob, re.IGNORECASE)),
    }


# --------------------------------------------------------------------------- #
# structural recovery (the only dimension C can express)
# --------------------------------------------------------------------------- #
def _blob(obj) -> str:
    if isinstance(obj, str):
        return obj
    return json.dumps(obj, ensure_ascii=False)


def _mentions(blob: str, token: str) -> bool:
    """Is `token` named in `blob`, directly or as part of a range?

    C's documents often name a set as a range ("M1-M5", "B0–B4"), which does refer
    to every member; counting only the two endpoints would understate what the
    method recovered. Whether the *parameters* landed is a separate question,
    answered by `_claimed`/`_recovered`.
    """
    if re.search(rf"(?<![A-Za-z0-9]){re.escape(token)}(?![A-Za-z0-9])",
                 blob, re.IGNORECASE) is not None:
        return True
    m = re.fullmatch(r"([A-Za-z_]+)(\d+)", token)
    if not m:
        return False
    prefix, num = m.group(1), int(m.group(2))
    for a, b in re.findall(
            rf"(?<![A-Za-z0-9]){re.escape(prefix)}(\d+)\s*[-\u2010-\u2015]\s*"
            rf"{re.escape(prefix)}(\d+)(?![A-Za-z0-9])", blob, re.IGNORECASE):
        lo, hi = sorted((int(a), int(b)))
        if lo <= num <= hi:
            return True
    return False


# Name fragments a key has to contain to be about a concept. C's agents do not
# agree on key spelling (`processing_time_s`, `process_time_s`, `mttr_s`,
# `inter_arrival_seconds`, `arrival_interval`) and sometimes answer in Russian
# (`время обработки`, `доступность`, `интервалы поступления`), so the match is
# on a fragment rather than an exact name. Fragment matching stays scoped to the
# key that names the concept — which is what the old whole-artefact digit search
# was not.
_CONCEPT_STEMS = {
    "process_time": ("processing_time", "process_time", "cycle_time",
                     "время обработки", "время цикла"),
    "availability": ("availability", "uptime", "доступност", "готовност"),
    "arrival": ("inter_arrival", "interarrival", "arrival_interval",
                "arrival_time", "интервал прихода", "интервал поступления",
                "интервалы поступления"),
}
# C either carries the given number through or invents a different one, so the
# comparison is tight: 101 against a truth of 100 is an invention, not rounding.
_VALUE_TOL = 1e-3


# One number, optionally in scientific notation. Shared by the scalar reader
# and the sentence reader so both accept exactly the same numeric forms.
_SCI = r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?"


def _as_number(v):
    """C's value as a float, or None when it states no number.

    Accepts numbers and unit-annotated strings ("600", "600 s", "92%", "1e3").
    A null, an absent key or a non-numeric string is not a value.

    Rejects strings whose leading digits are not a value C measured: a spec
    range ("0-100%"), a ratio ("24/7") and a comma-decimal list ("1,5"). Each
    of those would otherwise put a wrong number in the record — caught in
    review for the range, and guarded for the other two by the same argument.
    """
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip()
        if re.match(rf"{_SCI}\s*[-\u2010-\u2015]\s*\d", s):
            return None
        if re.match(r"[-+]?\d+\s*/\s*\d", s):
            return None
        if re.match(r"[-+]?\d+,\d", s):
            return None
        m = re.match(rf"({_SCI})(?![0-9.])", s)
        if m:
            return float(m.group(1))
    return None


def _records(obj):
    """Every dict inside a JSON document, depth-first."""
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _records(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _records(v)


_INSERT_RE = re.compile(r"insert\s+into\s+[\w.\"]+\s*\(([^)]*)\)"
                        r"\s*values\s*(.*?)(?:;|(?=\s*insert\s+into\b)|$)",
                        re.IGNORECASE | re.DOTALL)


def _split_cells(s: str) -> list:
    """Comma-split a SQL cell list, honouring single-quoted strings.

    C writes names into cells (`'M1'`, `'M1, line 2'`), so a quoted comma is
    part of one value, not a column boundary.
    """
    cells, cur, q = [], [], False
    for ch in s:
        if ch == "'":
            q = not q
            cur.append(ch)
        elif ch == "," and not q:
            cells.append(cur)
            cur = []
        else:
            cur.append(ch)
    cells.append(cur)
    return ["".join(c).strip().strip("'\"") for c in cells]


def _rows_in(values: str) -> list:
    """The parenthesised row groups of a VALUES list, quotes honoured."""
    out, depth, start, q = [], 0, None, False
    for i, ch in enumerate(values):
        if ch == "'":
            q = not q
        elif q:
            continue
        elif ch == "(":
            if depth == 0:
                start = i + 1
            depth += 1
        elif ch == ")" and depth:
            depth -= 1
            if depth == 0:
                out.append(values[start:i])
    return out


def _sql_rows(text: str) -> list:
    """`(columns, cells)` for every row of every INSERT ... VALUES in `text`.

    C's DB agent states parameters as DDL rather than JSON — `INSERT INTO
    stations (id, machine_id, processing_time_s, ...) VALUES ('M1','M1',600,...)`
    — so a structured read has to cover both shapes. A statement need not end in
    `;`, a multi-row VALUES list contributes every row, and a quoted cell may
    contain a comma or a bracket.
    """
    rows = []
    for cols, values in _INSERT_RE.findall(text):
        columns = [c.strip().strip('"').lower() for c in _split_cells(cols)]
        for row in _rows_in(values):
            rows.append((columns, _split_cells(row)))
    return rows


def _key_matches(key: str, stems) -> bool:
    k = str(key).strip().lower()
    return any(s in k for s in stems)


# A record is *about* a machine only when a field whose key denotes identity
# names it — `{"machine": "M1", "process_time_s": 150}`. Testing the id against
# every value in the record instead let a line-level field that merely lists
# machine names scope a generic number to that machine; caught in review
# (`{"equipment_list": "M1", "cycle_time_s": 150}` credited 150 to M1).
_IDENTITY_KEYS = {"id", "machine", "station", "equipment", "unit", "name",
                  "tag", "code", "processor", "stand", "станок", "станция",
                  "агрегат", "оборудование", "машина"}
_IDENTITY_SUFFIXES = ("_id", "_name", "_tag", "_code")


def _identity_key(key) -> bool:
    k = str(key).strip().lower()
    return k in _IDENTITY_KEYS or k.endswith(_IDENTITY_SUFFIXES)


def _id_pos_in(text: str, token: str):
    """Whole-token match, so id "M1" is not found inside "M10"."""
    return re.search(rf"(?:^|[^A-Za-z0-9]){re.escape(token)}(?![A-Za-z0-9])", text)


def _range_ids(text: str, ids) -> set:
    """Ids covered by a range like "M1-M5" — C's way of saying "each of them".

    Only a range whose endpoints share a letter prefix counts, so a numeric
    range in prose ("0-100") expands to nothing rather than to machines.
    """
    out = set()
    for a, b in re.findall(r"([A-Za-zА-Яа-я]+\d+)\s*[-\u2010-\u2015]\s*"
                           r"([A-Za-zА-Яа-я]+\d+)", text):
        ma, mb = (re.match(r"([A-Za-zА-Яа-я]+)(\d+)", a),
                  re.match(r"([A-Za-zА-Яа-я]+)(\d+)", b))
        if not ma or ma.group(1) != mb.group(1):
            continue
        lo, hi = sorted((int(ma.group(2)), int(mb.group(2))))
        for i in ids:
            m = re.match(rf"{re.escape(ma.group(1))}(\d+)$", i)
            if m and lo <= int(m.group(1)) <= hi:
                out.add(i)
    return out


def _number_near(text: str, token: str, ids):
    """The number stated for `token` inside one sentence.

    C often answers a whole line in one string — `время обработки на станцию:
    "200 с для M1, 220 с для M2"` — so the value has to be tied to the machine
    the sentence names. The sentence is cut at clause boundaries and a clause
    credits `token` only when it names no *other* machine besides `token` (or
    names the rest only as a range, e.g. `"0.97 для M1-M5"`) and states exactly
    one number. Both orders C uses work — `"100 с для M1"` and `"M1 — 100 с"` —
    while an id-first list does not: in `"M1 — 500 с, M2 — 100 с"` the number
    before M2 belongs to M1, and the earlier "nearest number before the id"
    rule silently credited 500 to M2 (caught in review).
    """
    # A clause that names the machine outright outranks one that merely ranges
    # over it: in "M1-M5 — 500 с, M3 — 100 с" M3's own clause states 100.
    for literal_only in (True, False):
        for clause in re.split(r"[,;，、]", text):
            ranged = _range_ids(clause, ids)
            literal = bool(_id_pos_in(clause, token))
            if literal_only and not literal:
                continue
            if not literal_only and (literal or token not in ranged):
                continue
            named = {i for i in ids if _id_pos_in(clause, i)}
            bare = clause
            for i in named | ranged:
                bare = re.sub(rf"(?:^|[^A-Za-z0-9]){re.escape(i)}(?![A-Za-z0-9])",
                              " ", bare)
            # the range token itself ("M1-M5") still carries digits
            bare = re.sub(r"[A-Za-zА-Яа-я]+\d+\s*[-\u2010-\u2015]\s*"
                          r"[A-Za-zА-Яа-я]+\d+", " ", bare)
            nums = re.findall(rf"({_SCI})", bare)
            if len(nums) == 1 and len(named - ranged) <= 1:
                return float(nums[0])
    return None


def _claimed(docs, machine_id, stems, sql_rows, ids):
    """The value C states for `stems` about `machine_id`, or None if it states none.

    `machine_id=None` searches the whole document and skips the SQL rows: the
    arrival interval is a line property, so a row with no machine column cannot
    be attributed to it.
    """
    for doc in docs:
        for rec in _records(doc):
            scoped = machine_id is None or any(
                _identity_key(k) and isinstance(v, str)
                and v.strip() == machine_id for k, v in rec.items())
            for k, v in rec.items():
                if not _key_matches(k, stems):
                    continue
                # A string that itself names machines is a per-machine answer
                # ("100 с для M1, 130 с для M2"): its leading digits are not
                # this record's value, so read it by machine, below.
                if scoped and not (isinstance(v, str)
                                   and any(_id_pos_in(v, i) for i in ids)):
                    n = _as_number(v)
                    if n is not None:
                        return n
                if machine_id is not None and isinstance(v, str):
                    n = _number_near(v, machine_id, ids)
                    if n is not None:
                        return n
    if machine_id is None:
        return None
    for columns, cells in sql_rows:
        if machine_id not in cells[:2]:
            continue
        for i, col in enumerate(columns):
            if i < len(cells) and _key_matches(col, stems):
                n = _as_number(cells[i])
                if n is not None:
                    return n
    return None


def _recovered(concept: str, claimed, truth) -> bool:
    """Is C's stated value the truth?

    Availability is accepted as a fraction (0.92) or a percentage (92) — the
    same claim in two units — but C's 95 is not truth's 0.92.
    """
    if claimed is None or truth is None:
        return False
    tol = abs(truth) * _VALUE_TOL
    if abs(claimed - truth) <= tol:
        return True
    if concept == "availability":
        if claimed > 1.5 >= truth and abs(claimed / 100.0 - truth) <= tol:
            return True
        if truth > 1.5 >= claimed and abs(claimed * 100.0 - truth) <= tol:
            return True
    return False


def extract_structure(requirements: dict, schema: dict, manifest: dict) -> dict:
    """Per-machine parameter recovery: does C state *this machine's* value for
    *this concept*, and does it equal the truth?

    The previous check searched the artefact for the bare digit. That is not a
    recovery test: in runs/20260919_052152/case_0004 rep2 the truth M1 process
    time (100) was "found" as M1's `power_working_kw` in C's own INSERT, truth
    M3's 90 was found as *M2's* `availability_pct`, and the arrival interval 150
    as M3's `mttr_s` — while C's own `line.stations` was null for every field.
    The digits were all present; none of them was the parameter. Under it, reps
    whose requirements document carries no station at all still read as
    "5/5 process times, 5/5 availabilities".
    """
    docs = [requirements, schema]
    blob = _blob(requirements) + "\n" + _blob(schema)
    sql_rows = _sql_rows(blob)
    ids = [str(m["id"]) for m in manifest.get("machines", [])]
    stats = {}
    for m in manifest.get("machines", []):
        mid = str(m["id"])
        if not _mentions(blob, mid):
            continue
        rec = {"mentioned": True}
        for name, truth in (("process_time", m.get("process_time_s")),
                            ("availability", m.get("availability"))):
            claimed = _claimed(docs, mid, _CONCEPT_STEMS[name], sql_rows, ids)
            rec[f"{name}_found"] = _recovered(name, claimed, truth)
            # Keep what C actually stated. A bare found/not-found boolean is
            # exactly what let invented numbers read as recoveries unnoticed.
            if claimed is not None:
                rec[f"{name}_claimed"] = claimed
        stats[mid] = rec
    buffers = {b["id"]: _mentions(blob, b["id"]) for b in manifest.get("buffers", [])}
    arrival_claimed = _claimed(docs, None, _CONCEPT_STEMS["arrival"], sql_rows, ids)
    return {
        "machine_stats": stats,
        "machines_mentioned": len(stats),
        "machines_truth": len(manifest.get("machines", [])),
        "buffers": buffers,
        "arrival_found": _recovered(
            "arrival", arrival_claimed,
            manifest.get("arrival", {}).get("inter_arrival_s")),
        "arrival_claimed": arrival_claimed,
        "equipment_count": len((requirements or {}).get("equipment", []) or []),
    }


# --------------------------------------------------------------------------- #
# content shape — "an answer arrived" vs "here is what the answer is"
# --------------------------------------------------------------------------- #
# Two texts are measured for the DB stage, and since 2026-09-21 they are the
# same reply (§7.6 settled the question of which one is the schema artefact:
# the agent's reply):
#   * `db_answer`   — the agent's own reply (`schema_raw`) as it arrived, which
#                     is what the method consumes and what the DT stage is fed;
#   * `db_recorded` — the text written to artifacts/dtb_schema.sql: that reply
#                     fence-stripped, the form C's own app stores in
#                     `st.session_state.db_schema`. Identical to `db_answer`
#                     unless the reply carried a code fence or trailing newline.
# Both are kept because they are measured in one pass and a stored run recorded
# before this change can still have them diverge (there `db_recorded` was
# `_get_json`'s *extraction* from the reply, which could be a different document
# entirely). These checks measure text only; they never alter the method's
# behaviour.
#
# The DDL test is two-tiered on purpose. Bare type words ("text", "timestamp",
# "integer") appear in ordinary prose and in non-DDL dicts, so they are not
# evidence on their own; unambiguous SQL phrases are.
_DDL_PHRASE_RE = re.compile(
    r"\b(create\s+table|create\s+schema|alter\s+table|drop\s+table|"
    r"insert\s+into|primary\s+key|foreign\s+key|not\s+null|create\s+index)\b",
    re.IGNORECASE)
_SQL_TYPE_RE = re.compile(
    r"\b(varchar|numeric|bigserial|serial|uuid|jsonb|timestamptz|"
    r"double\s+precision|boolean)\b", re.IGNORECASE)


def _shape(text: str, manifest: dict, *, ddl: bool = False) -> dict:
    text = text or ""
    ids = ([str(m["id"]) for m in manifest.get("machines", [])]
           + [str(b["id"]) for b in manifest.get("buffers", [])])
    shape = {"chars": len(text),
             "ids_present": sum(1 for t in ids if _mentions(text, t)),
             "ids_truth": len(ids)}
    if ddl:
        phrases = sorted({m.group(0).lower() for m in _DDL_PHRASE_RE.finditer(text)})
        types = sorted({m.group(0).lower() for m in _SQL_TYPE_RE.finditer(text)})
        shape["ddl_phrases"] = phrases
        shape["sql_types"] = types
        shape["looks_like_ddl"] = bool(phrases) or len(types) >= 2
    return shape


def stage_shapes(schema_raw: str, schema_recorded: str, dt: dict | None,
                 manifest: dict) -> dict:
    """Per-stage content shape, reported next to each stage's status.

    Answers what a status cannot: does the stage's output carry the case's own
    entities, and is the DB stage's text actually DDL? The DB stage is measured
    twice — the agent's answer and the recorded schema artefact — which are the
    same text for a run of this version and can differ in a stored run recorded
    before 2026-09-21 (see the note above).
    """
    out = {"db_answer": _shape(schema_raw, manifest, ddl=True),
           "db_recorded": _shape(schema_recorded, manifest, ddl=True)}
    for key in DT_SLOT_KEYS:
        raw = ((dt or {}).get(key) or {}).get("raw") or ""
        s = _shape(raw, manifest)
        if key == "config":
            s["looks_like_json"] = bool(raw.strip()) and _get_json(raw) is not None
        out[f"dt_{key}"] = s
    return out


def _rep_status(measured: bool, des_stage: str, db_note,
                des_err) -> tuple:
    """`(status, basis)`: C's rep status from the deepest stage that failed.

    A and B report `simulation_error` when the model they generated was executed
    and failed; C reported `ok` for that same outcome, because `ok` meant only
    "the pipeline completed" — so C's validity table was not comparable with
    theirs (e.g. runs/20260919_052152 case_0004 rep2 ran a DES model that exited
    non-zero and read `ok`). The status is therefore derived from what the
    stages produced, and the `basis` is recorded next to it so a reader can see
    which stage the verdict came from.

    `des_err` is the DES slot's own error string. The rule itself lives in
    `base.derive_rep_status` (protocol.md §5) so `report.py` can re-derive a
    stored rep — from `native.dt_slot_errors.des` — without a second, drifting
    copy; the formatted `dt_note` cannot be split back into per-slot outcomes.
    """
    return B.derive_rep_status(measured, des_stage, db_note, des_err)


def generate(manifest: dict, bundle: Path, mode: str, workdir: Path, rep: str):
    res = B.empty_result("C", manifest["case_id"], int(rep))
    t0 = time.perf_counter()
    log: list = []
    try:
        if mode == "mock":
            mock = ROOT / "adapters" / "_mock_models" / "mock_C_requirements_serial.json"
            if manifest["case_id"] != "case_0001_serial_line" or not mock.exists():
                raise RuntimeError(f"no mock requirements shipped for '{manifest['case_id']}'")
            payload = json.loads(mock.read_text(encoding="utf-8"))
            requirements, schema = payload["requirements"], payload.get("schema", {})
            meta = {"interview_turns": 0, "agent_tasks": 0, "responder_calls": 0,
                    "api_url": None, "dt": None, "dt_schema_text": None,
                    "agent_status": {f"agent{i}": "mock"
                                     for i in sorted({UI_AGENT, DB_AGENT, DT_AGENT})}}
            log.append(("mock", "canned requirements for shipped case", ""))
        else:
            base = api_url()
            prompts = load_prompts()
            status = {f"agent{i}": agent_status(base, i)
                      for i in sorted({UI_AGENT, DB_AGENT, DT_AGENT})}
            if status.get(f"agent{UI_AGENT}") != "active":
                raise RuntimeError(
                    f"Method C UI agent (agent {UI_AGENT}) offline at {base} "
                    f"(roles: ui={UI_AGENT} db={DB_AGENT} dt={DT_AGENT}; status={status})"
                    " — check C.ui_agent_index in config.yaml against the "
                    "deployment's UI_AGENT_INDEX")
            session_id = new_session(base)
            iv = _interview(base, session_id, prompts, bundle, manifest, log)
            if "error" in iv:
                raise RuntimeError(f"interview failed: {iv['error']}")
            requirements = iv["requirements"]
            if not isinstance(requirements, dict):
                raise RuntimeError("UI agent returned no requirements object")
            db = _schema(base, session_id, prompts, requirements, log)
            # The agent's reply is the stage's artefact as it stands: it is what
            # C's own front end holds as `db_schema` and what `_schema_text`
            # feeds to the DT stage, so it is recorded verbatim. `_get_json` is
            # not applied to it — a SQL reply does not parse as JSON, and the
            # extractor's fallback (the first brace-balanced object in the text)
            # records a fragment of the reply as if it were the schema. That
            # mis-labelling is what protocol.md §7.6 settled on 2026-09-21.
            schema = {"raw": db.get("schema_raw") or ""}
            db_note = None
            if db.get("error"):
                db_note = (f"DB agent (agent {DB_AGENT}) failed: "
                           f"{db['error'][:200]}"
                           " — requirements recovered, schema stage unavailable")
            meta = {"interview_turns": iv["turns"], "db_note": db_note,
                    "db_error": db.get("error"),
                    "db_sql_ok": db.get("sql_ok"),
                    "db_sql_report": db.get("sql_report"),
                    "db_sql_summary": db.get("sql_summary") or {},
                    "db_sql_attempts": db.get("sql_attempts") or [],
                    "responder_calls": iv["responder_calls"],
                    "ui_agent_calls": iv["agent_calls"],
                    "db_agent_calls": db.get("calls", 0),
                    "db_agent_attempts": db.get("attempts", 0),
                    "api_url": base, "agent_status": status}
            # agent 2 (DT) is exercised even when the DB stage failed: the
            # schema is one of its two inputs, so a degraded input must be
            # recorded rather than silently skipped (or papered over).
            schema_text = _schema_text(db, schema)
            meta["dt_schema_text"] = schema_text
            meta["dt"] = _dt_stage(base, session_id, prompts, requirements,
                                   schema_text, log, manifest, workdir)
            meta["agent_tasks"] = (meta["ui_agent_calls"] + meta["db_agent_calls"]
                                   + meta["dt"]["calls"])
            # submissions, not answers: on this host a task can sit in
            # `processing` forever, so what it cost and what it returned differ
            meta["agent_tasks_attempted"] = (meta["ui_agent_calls"]
                                             + meta["db_agent_attempts"]
                                             + meta["dt"]["attempts"])
        res["elapsed_generation_s"] = round(time.perf_counter() - t0, 3)
        res["llm_calls"] = meta["agent_tasks"] + meta["responder_calls"]
        res["llm_tokens_estimate"] = None
    except Exception as e:  # noqa: BLE001
        # A transport failure means the host never answered: that measures the
        # deployment's availability, not C's generation behaviour, so it is not
        # charged to C as a generation error. `HTTPError` is excluded because
        # the service did answer, with an error. `ServiceUnavailable` carries a
        # `dependency` so a responder-LLM outage is attributed to OpenRouter
        # rather than to the C endpoint, which is a different host.
        res["error"] = f"{type(e).__name__}: {e}"
        if isinstance(e, TRANSPORT_ERRORS) and not isinstance(e, urllib.error.HTTPError):
            res["status"] = "service_unavailable"
            what = (f"{e.dependency} was" if isinstance(e, ServiceUnavailable)
                    else "the configured C endpoint was")
            res["notes"].append(
                f"{what} unreachable after {NET_RETRIES} retries; recorded as an "
                "availability failure of that dependency, not as a generation "
                "failure of method C")
        else:
            res["status"] = "generation_error"
            res["notes"].append(
                "Method C could not be driven; no structure recovered")
        try:  # keep the transcript even when generation fails
            art = workdir / "artifacts"
            art.mkdir(exist_ok=True)
            (art / "interview.log").write_text(
                "\n\n".join(f"[{r}|{w}] {c}" for r, c, w in log), encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
        B.write_json(workdir / "result.json", res)
        return res, None

    # artefacts: C's "model" is a requirements document + database schema
    # (+ agent 2's twin configuration, PyChrono script and DES model when they ran)
    art = workdir / "artifacts"
    art.mkdir(exist_ok=True)
    B.write_json(art / "dtb_requirements.json", requirements)
    # The schema artefact is the DB agent's reply, not a parse of it (§7.6, the
    # question left open on 2026-09-18 is settled here): `dtb_schema.sql` holds
    # that reply, fence-stripped exactly as C's own app stores it
    # (sql_runner.generate_with_repair -> `st.session_state.db_schema`), and
    # `dtb_schema.json` keeps its former role as the JSON wrapper the DT stage's
    # input is carried in — in real mode `{"raw": <the reply>}`, in mock mode the
    # canned schema object. `schema_artefact_text` is the text every "what was
    # recorded" measurement reads, and it is the file's content by construction.
    if mode == "mock":
        schema_artefact_text = json.dumps(schema, ensure_ascii=False, indent=2)
    else:
        schema_artefact_text = B.strip_code_fence(meta.get("dt_schema_text") or "")
    B.write_json(art / "dtb_schema.json", schema)
    if mode != "mock" and schema_artefact_text.strip():
        (art / "dtb_schema.sql").write_text(schema_artefact_text, encoding="utf-8")
    dt = meta.get("dt") or {}
    dt_note = None
    dt_slots_ok = None          # None = stage not attempted (mock)
    des_raw = ""
    if dt:
        cfg_raw = (dt.get("config") or {}).get("raw")
        if cfg_raw:
            cfg = _get_json(cfg_raw)
            B.write_json(art / "dtb_dt_config.json",
                         cfg if cfg is not None else {"raw": cfg_raw})
        sim_raw = (dt.get("sim") or {}).get("raw")
        if sim_raw:
            (art / "dtb_pychrono.py").write_text(sim_raw, encoding="utf-8")
        des_raw = (dt.get("des") or {}).get("raw") or ""
        # Unlike the PyChrono slot, the DES model is executed, so a fence that
        # the agent added despite the prompt is stripped before it is written to
        # the artefact too — otherwise the artefact is not what was run.
        if des_raw:
            (art / "dtb_des.py").write_text(
                B.strip_code_fence(des_raw), encoding="utf-8")
        errs = {k: (dt.get(k) or {}).get("error") for k in DT_SLOT_KEYS}
        ok_slots = [k for k, v in errs.items() if not v]
        dt_slots_ok = len(ok_slots)
        if not ok_slots:
            dt_note = (f"DT agent (agent {DT_AGENT}) produced no output for any "
                       "slot: " + "; ".join(f"{k}: {v}" for k, v in errs.items()))
        elif len(ok_slots) < len(DT_SLOT_KEYS):
            dt_note = f"DT agent (agent {DT_AGENT}) partial: " + "; ".join(
                f"{k}: {v}" for k, v in errs.items() if v)
    (art / "interview.log").write_text(
        "\n\n".join(f"[{r}|{w}] {c}" for r, c, w in log), encoding="utf-8")
    B.write_json(workdir / "model.json",
                 {"requirements": requirements, "schema": schema,
                  "dt_config": _get_json((dt.get("config") or {}).get("raw") or "")
                  if dt else None,
                  "dt_simulation": (dt.get("sim") or {}).get("raw") if dt else None,
                  "dt_des": des_raw or None})

    # C's DES model is the only agent-2 artefact that is a measurement rather
    # than a document, so it is executed and its KPI contract parsed. If it does
    # not run, or prints no contract, the KPIs stay null: a stage that failed is
    # recorded as failed, never as a zero (protocol §5).
    #
    # Since the amendment of 2026-09-20 the execution happens inside the DES
    # slot (`_repair_des`), because C runs each program as it arrives and
    # corrects it — so the execution recorded there is the one to report, and
    # re-running here would execute a program that is no longer the artefact.
    des_slot = (dt.get("des") or {}) if dt else {}
    # one entry per program the slot produced, in order; empty when the slot
    # never ran (not reached, or its task timed out), which the native counts
    # below must report as None rather than 0.
    des_attempts = des_slot.get("attempts") or []
    # one entry per DB reply that was validated, in order (the loop above);
    # empty when no reply ever arrived, which the counts below report as None
    db_attempts = meta.get("db_sql_attempts") or []
    des_exec: dict | None = des_slot.get("exec")
    des_kpis: dict = des_slot.get("kpis") or {}
    if des_exec is not None:
        res["elapsed_simulation_s"] = des_exec["elapsed_s"]
    elif des_raw.strip():
        # No execution recorded: a DT stage driven without a workdir, or a
        # stored path from before the amendment. Execute here so the artefact
        # is still measured rather than assumed to work.
        des_exec = _execute_des(des_raw, workdir)
        res["elapsed_simulation_s"] = des_exec["elapsed_s"]
        des_kpis = _des_kpis_from_exec(des_exec)

    struct = extract_structure(requirements or {}, schema or {}, manifest)
    dt_struct = extract_dt_structure(meta.get("dt"), manifest)
    # what each stage's answer actually is, not just whether one arrived. The
    # DB agent's reply and the schema artefact are measured separately: the
    # reply is the method's output, the artefact is the harness's extraction of
    # it, and they are not always the same document (see the note below).
    shapes = stage_shapes(
        meta.get("dt_schema_text") if meta.get("dt_schema_text") is not None
        else (_blob(schema) if schema else ""),
        schema_artefact_text, meta.get("dt"), manifest)
    # Headline KPIs, populated only from a DES model that actually ran and
    # printed the contract. `parse_b_stdout` returns None per missing indicator,
    # so a partial contract yields partial KPIs rather than fabricated zeros.
    if des_kpis:
        res["kpis"].update(des_kpis)
    if mode == "mock":
        des_stage = "not_attempted"
    elif not des_raw.strip():
        des_stage = "unavailable"
    elif des_exec is None:
        des_stage = "unavailable"
    elif des_exec["status"] != "ok":
        des_stage = des_exec["status"]          # timeout | simulation_error | error
    elif any(v is not None for v in des_kpis.values()):
        des_stage = "ok"
    else:
        des_stage = "ran_no_contract"

    # C's rep status now follows its stages. A pipeline that ran to the end but
    # produced no measurement is not `ok`: `ok` would put C's table out of step
    # with A's and B's, which already report the model's failure. (Decided
    # 2026-09-20; see protocol.md §5.)
    status_basis = None
    if mode != "mock" and res["status"] == "ok":
        res["status"], status_basis = _rep_status(
            any(v is not None for v in des_kpis.values()), des_stage,
            meta.get("db_note"),
            ((meta.get("dt") or {}).get("des") or {}).get("error"))
        if res["status"] != "ok":
            res["notes"].append(
                f"status `{res['status']}`: {status_basis} — the pipeline itself "
                "completed, so this is the stage outcome, not an adapter failure")

    res["kpis"]["native"] = {
        **struct,
        **dt_struct,
        "stage_shapes": shapes,
        "interview_turns": meta["interview_turns"],
        "agent_tasks": meta["agent_tasks"],
        "agent_tasks_attempted": meta.get("agent_tasks_attempted",
                                          meta["agent_tasks"]),
        "responder_calls": meta["responder_calls"],
        "llm_calls_split": {
            "ui_agent": meta.get("ui_agent_calls"),
            "db_agent": meta.get("db_agent_calls"),
            "dt_agent": (meta.get("dt") or {}).get("calls"),
            "harness_responder": meta["responder_calls"],
        },
        "responder_model": None if mode == "mock" else RESPONDER_MODEL,
        "api_url": meta["api_url"],
        "agent_status": meta["agent_status"],
        # What agent 1's reply *is*, not just whether one arrived (the meaning
        # `db_stage` had before 2026-09-21, which conflated an answer with a
        # schema). `ok` means the reply reads as a usable PostgreSQL schema by
        # C's own verdict (`sql_runner.check`: parsed, at least one CREATE TABLE,
        # no relation created twice or used without being created);
        # `invalid_sql` means a reply arrived but did not; `unavailable` means no
        # reply arrived at all and `db_note` says why.
        "db_stage": ("not_attempted" if mode == "mock" else
                     "unavailable" if meta.get("db_note") else
                     "ok" if meta.get("db_sql_ok") else "invalid_sql"),
        "db_note": meta.get("db_note"),
        # Counts for the same reason as the DES pair below: they say whether the
        # loop stopped on a reply that reads as SQL or ran out of attempts. None
        # (not 0) when no reply was ever validated.
        "db_programs": (None if mode == "mock" or not db_attempts
                        else len(db_attempts)),
        "db_repairs_used": (None if mode == "mock" or not db_attempts
                            else max(len(db_attempts) - 1, 0)),
        "db_repair_attempts_allowed": (None if mode == "mock"
                                       else DB_REPAIR_ATTEMPTS),
        # Non-null only when the last reply still does not read as SQL. Why each
        # rejected reply was rejected is written to artifacts/interview.log as
        # one `schema attempt N: ...` line per reply, next to the repair turn it
        # triggered; this is the verdict of record for the reply that was kept.
        "db_gave_up_reason": (None if mode == "mock" or not db_attempts
                              else db_attempts[-1].get("repair_reason")),
        # the counts C's own verdict made, kept so the report can render what the
        # reply defines without re-parsing the text (the relations themselves,
        # and any relation used but never created, are in `db_gave_up_reason`)
        "db_sql_summary": (None if mode == "mock" else {
            k: (meta.get("db_sql_summary") or {}).get(k)
            for k in ("statements", "tables", "views", "indexes", "inserts")}),
        "dt_stage": ("not_attempted" if mode == "mock" else
                     "ok" if dt_slots_ok == len(DT_SLOT_KEYS) else
                     "partial" if dt_slots_ok else "unavailable"),
        "dt_note": dt_note,
        "dt_slots_ok": dt_slots_ok,
        # the per-slot error strings, kept structured so the derived status
        # (`status_basis`) can be re-checked from the artefact rather than only
        # from the in-memory stage dict. `dt_note` is a formatted summary that
        # cannot be split back into per-slot outcomes: a run whose `config` slot
        # failed with URLError but whose `des` slot answered off-contract is a
        # `generation_error`, not the `service_unavailable` a whole-note scan
        # would read (protocol.md §5).
        "dt_slot_errors": ({
            key: (meta["dt"].get(key) or {}).get("error")
            for key in DT_SLOT_KEYS} if mode != "mock" and meta.get("dt")
            else None),
        "dt_slots_total": None if dt_slots_ok is None else len(DT_SLOT_KEYS),
        # the DES slot alone, separately from the dt_stage roll-up: a paper
        # reporting "C cannot be measured" needs to distinguish "the slot was
        # never reached" from "the generated model did not run" from "it ran and
        # printed nothing".
        "des_stage": des_stage,
        "des_exec_status": None if des_exec is None else des_exec["status"],
        "des_exec_error": None if des_exec is None else des_exec.get("error"),
        "des_parse_error": (
            None if des_stage in ("not_attempted", "unavailable") else
            "stdout carried no KPI contract lines" if des_stage == "ran_no_contract"
            else None),
        "des_kpis": des_kpis or None,
        # DES execute-and-repair, added 2026-09-20. `des_programs` is how many
        # programs C produced for this case (1 = it worked first time) and
        # `des_repairs_used` how many of those were corrections. Why each
        # rejected program was rejected (traceback tail, missing contract line,
        # all-zero verdict, or — since 2026-09-21 — numbers the declared line
        # cannot produce) is NOT a key here: that per-attempt trace is written
        # to artifacts/interview.log as one `des attempt N: ...` line per
        # program, next to the repair turn it triggered.
        # `des_gave_up_reason` is non-null only when the last program still
        # failed C's gate — it did not run, did not report, or reported numbers
        # the declared line cannot produce. That last case is why the field is
        # the reading of record rather than `des_stage`: such a program prints
        # the contract, so `des_stage` is `ok` and the status stays `ok`
        # (protocol.md §5), and only this field says the KPIs above are a
        # printed number rather than an accepted measurement.
        "des_repair_attempts_allowed": (None if mode == "mock"
                                        else DES_REPAIR_ATTEMPTS),
        "des_reject_all_zero": None if mode == "mock" else DES_REJECT_ALL_ZERO,
        # Both are None — not 0 — when the DES stage never ran (the slot timed
        # out or the run stopped earlier): "no program was produced" is not the
        # same reading as "a program ran and needed no repair", and only the
        # second is a repair-loop success.
        "des_programs": (None if mode == "mock"
                         else (len(des_attempts) or None)),
        "des_repairs_used": (None if mode == "mock" or not des_attempts
                             else max(len(des_attempts) - 1, 0)),
        "des_exec_elapsed_total_s": (None if mode == "mock" else
                                     (dt.get("des") or {}).get("exec_elapsed_s")),
        "des_gave_up_reason": (None if mode == "mock" else
                               (dt.get("des") or {}).get("gave_up_reason")),
        # which stage the rep's status came from (protocol.md §5): `ok` only
        # when a measurement was produced, otherwise the deepest stage that
        # failed. None for a mock run, where the status is not derived.
        "status_basis": status_basis,
        # where the headline KPIs above came from. Lives in the native block
        # because it describes a property of C's measurement, not an indicator;
        # a flat key under `kpis` would sit among the headline values.
        "kpi_source": (
            None if mode == "mock" else
            "des_model_stdout" if any(v is not None for v in des_kpis.values())
            else None),
        # the interpreter that ran the model: part of the evidence that a
        # `simulation_error` is the model's fault and not a missing library
        "des_python": None if mode == "mock" else DES_PYTHON,
        "dt_schema_input": ("not_attempted" if mode == "mock" else
                            "ok" if (meta.get("dt_schema_text") or "").strip()
                            else "unavailable"),
        "capability": ("Method C emits a requirements document + PostgreSQL schema "
                       "and (agent 2) a twin configuration, a PyChrono "
                       "multi-physics script and a discrete-event SimPy model; the "
                       "DES model is executed and its KPI contract parsed, so "
                       "throughput/WIP/energy are populated when that slot "
                       "succeeds and null when it does not"),
    }
    res["generated_model_file"] = str(workdir / "model.json")
    res["notes"].append(
        f"structural recovery only: {struct['machines_mentioned']}/"
        f"{struct['machines_truth']} machines mentioned in C's requirements")
    if struct["machine_stats"] and not any(
            v["process_time_found"] for v in struct["machine_stats"].values()):
        # The UI agent records *which* measurements exist ("average process time
        # (s)", "availability (%)") but not their values, so no parameter value
        # survives into the requirements document; that is a property of C's
        # first stage, measured here, not a harness extraction miss.
        res["notes"].append(
            "requirements document names the measured quantities but carries no "
            "parameter values (C's requirements stage records sensor kinds only)")
    if meta.get("db_note"):
        first_line = meta["db_note"].splitlines()[0]
        res["notes"].append(f"DB stage (agent 1) not recovered — {first_line}")
    ans = shapes["db_answer"]
    if mode != "mock" and not meta.get("db_note") and ans["chars"]:
        if not meta.get("db_sql_ok"):
            # A reply arrived but does not read as a schema. This is the reading
            # `db_stage` now carries (`invalid_sql`); the reply and the recorded
            # artefact are the same text by construction, so nothing has to be
            # said here about `_get_json`'s extraction standing in for it.
            res["notes"].append(
                f"DB stage: agent {DB_AGENT} answered {ans['chars']} chars "
                f"(machine/buffer ids present: {ans['ids_present']}/"
                f"{ans['ids_truth']}) but the reply is not a usable PostgreSQL "
                "schema — C's own `sql_runner` verdict: "
                f"{(meta.get('db_sql_report') or '').splitlines()[0][:200]}")
            if len(db_attempts) > 1:
                res["notes"].append(
                    f"DB stage: {len(db_attempts)} replies were validated "
                    f"({len(db_attempts) - 1} repair turn(s)) and the last one "
                    "still does not read as a schema, so the DT stage below was "
                    "built on an input this stage never delivered")
    if mode != "mock":
        if dt_struct:
            res["notes"].append(
                "DT stage (agent 2) ran: "
                f"{dt_struct['artifact_chars']['config']} chars of twin config, "
                f"{dt_struct['artifact_chars']['sim']} chars of PyChrono script; "
                f"{dt_struct['machines_mentioned_in_dt']}/"
                f"{dt_struct['machines_truth']} machine ids appear in that output. "
                "The script is not executed (PyChrono is not installed on the "
                "harness host and models rigid bodies, not the case's "
                "discrete-event semantics), so no KPI is derived from it")
        if dt_note:
            res["notes"].append(f"DT stage (agent 2): {dt_note}")
        if not (meta.get("dt_schema_text") or "").strip():
            res["notes"].append(
                "DT stage ran with an unavailable DB schema: the DB stage is one "
                "of agent 2's two inputs, so its output here is conditioned on a "
                "degraded input (recorded, not substituted with a fabricated schema)")
    if meta["agent_status"].get(f"agent{DT_AGENT}") != "active" and mode != "mock":
        res["notes"].append(
            f"DT agent (agent {DT_AGENT}, PyChrono codegen) status="
            f"{meta['agent_status'].get(f'agent{DT_AGENT}')} at start; the stage "
            "outcome above is what the run actually produced")
    B.write_json(workdir / "result.json", res)
    return res, struct


def main(mode: str, bundle: str, workdir: str, rep: str) -> int:
    bundle = Path(bundle)
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    manifest = B.load_manifest(bundle)
    res, struct = generate(manifest, bundle, mode, workdir, rep)
    if struct is not None:
        nat = res["kpis"]["native"]
        print(f"[C] {res['status']} machines_mentioned="
              f"{struct['machines_mentioned']}/{struct['machines_truth']} "
              f"turns={nat['interview_turns']} db={nat['db_stage']} "
              f"dt={nat['dt_stage']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("usage: python method_c_adapter.py <mock|real> <bundle> <workdir> <rep>")
        sys.exit(2)
    mode, bundle, workdir, rep = sys.argv[1:]
    sys.exit(main(mode, bundle, workdir, rep))
