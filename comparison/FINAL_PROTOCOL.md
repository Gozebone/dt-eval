# Final comparison protocol

**Three-way comparison of LLM-based digital-twin / DES model generators**

| | |
|---|---|
| **Methods** | **A** = FactoryFlow (`FactoryFlow/FactoryFlow_v2`) · **B** = LLM-DES-Modeling · **C** = DigitalTwinBuilder (service) |
| **Harness** | `/ssd/projects/dt-eval/comparison` (`run_comparison.py`, `adapters/`, `report.py`, `truth/`) |
| **Design** | 5 synthetic serial lines × 3 methods × 3 repetitions, all in `mode: real` |
| **Status** | final protocol, 2026-09-25 |
| **Companion** | `protocol.md` — the working protocol with the append-only amendment log (§8). This document is the self-contained summary for hand-over; where they differ, `protocol.md`'s amendment log is the audit trail. |

This document contains, in order: **§1** the method used for the comparison,
**§2–§3** brief descriptions of methods A and B, **§4** the DES stage inside
method C's DT agent, **§5** the table of the final run for each of A, B and C
(and the caveats a reader must apply to it), **§6** threats to validity,
**§7** reproducibility.

---

## 1. The comparison method

### 1.1 Comparison question

> Given the *same underlying system* (a synthetic plant with known parameters),
> which method produces a simulation model whose **behaviour** (throughput, WIP,
> energy) best matches the real plant's, how **robustly** across repeated
> generations, how **cheaply**, and with what **structural fidelity**?

### 1.2 Objects of comparison

| Method | Tool | Native input it consumes | Output it produces |
|---|---|---|---|
| **A** | FactoryFlow / FactoryFlow_v2 | Natural-language prose description of the line | Python source defining a FactorySimPy component network |
| **B** | LLM-DES-Modeling | CSV event log of the plant (pm4py process mining) | Python source of a self-contained SimPy model |
| **C** | DigitalTwinBuilder (remote FastAPI service) | An **interview** (the method asks questions; the harness answers from the same information set) | Requirements JSON → PostgreSQL schema (agent 1) and, via agent 2, a twin configuration, a PyChrono script and a **discrete-event SimPy model** |

Each method is used **as published** — the harness changes only orchestration
(process invocation, I/O conversion, result parsing). Where a defect was found
in a method's own output contract, it was fixed **in that method's repository**,
not worked around in the harness (see §4.6 for how C's fixes reach the
measurement without being re-typed).

### 1.3 Fairness rules

1. **Native inputs.** Each method receives the input its authors designed for.
   Every case bundle carries per-method inputs that describe the *same* plant.
2. **Single-shot generation.** One generation pass per method per case
   (A: `run_amg_wrapper`; B: `ModelBuilder.build`). No closed-loop machinery
   (`run_manual_overrides`, `Modeloptimizer`) is used.
3. **No re-rolling.** A failed generation is recorded as a failure, never
   retried for a better sample. **Success rate is itself a metric.**
4. **Seeding.** Truth simulation, each model run and every controllable
   stochastic element are seeded from one case-level base seed. LLM sampling is
   **not** temperature-pinned, so repetition measures genuine generator variance.
5. **Autonomy.** Questions a method would put to a human are answered
   deterministically by the harness from the case's information set, and the
   number of turns is scored as an autonomy cost.
6. **Isolation.** Each method runs in its own venv and working directory; side
   effects stay inside the per-run workdir.
7. **Recorded, never reconciled.** Contradictory or degraded outcomes are
   reported as observed (per-rep, never pooled) and are not smoothed into an
   average that no single run made.

### 1.4 Case set and ground truth

Five immutable case bundles under `cases/`, one per plant. Each contains
`manifest.yaml` / `manifest.json` (the truth spec), `eventlog.csv` (B's input),
`prompt_A.txt` (A's input), `aux_B.txt`, `truth_kpis.json`,
`station_table.md`, `truth_structure.json`. All generated artefacts are
produced deterministically by `casegen.py` and committed, so all methods always
consume byte-identical inputs.

The ground-truth engine is `truth/plant.py` — a pure-SimPy plant independent of
both tools' libraries. `reference.replications = 10` seeded runs are averaged.
A breakdown window is honoured only while a machine is free (never
mid-processing), which keeps `Working` log rows equal to single-part processing
windows.

| Case | Line | Truth throughput (parts/h) | Truth WIP (parts) | Truth energy (kWh/part) |
|---|---|---|---|---|
| `case_0001_serial_line` | 5-machine serial, deterministic arrivals | 19.868 | 40.387 | 0.9892 |
| `case_0002_saturated_short_line` | short, saturated | 32.620 | 27.917 | 0.3525 |
| `case_0003_starved_six_line` | six stations, starved | 11.991 | 5.251 | 2.3537 |
| `case_0004_failure_heavy_line` | failure-heavy | 22.401 | 7.289 | 0.8735 |
| `case_0005_high_rate_line` | high arrival rate | 44.991 | 38.882 | 0.3354 |

Definitions: throughput = completed parts / window hours; WIP = time-average
parts in the system; energy per part = (Σ working·work_power + Σ idle·idle_power)
/ 3600 kWh over the window ÷ completed parts. Units: parts/hour, parts,
kWh/part; all times in seconds.

**C's native input is an interview, not a file.** C's UI agent asks questions
and the harness answers with an LLM "plant engineer" whose system prompt carries
`prompt_A.txt` plus the manifest's exact parameter values — the same information
set A receives in prose and B as a log. Since C's UI prompt is an interview
protocol that analyses the *user's* message, the harness posts the engineer's
opening statement as the first user turn before submitting any task. A fixed,
byte-identical policy string answers the questions no bundle can answer (what
the twin is for, how often data updates, that alarm thresholds are undefined).
It contains no parameter values and is not scored; any other missing fact is
refused. Every turn is logged to `artifacts/interview.log`, and the turn count
is C's Autonomy cost.

### 1.5 Pipeline and unified output contract

Per case × method × rep: **generate → execute → parse → score.**

Every adapter is a standalone CLI run in its method's interpreter and writes the
same `result.json`: `method`, `case`, `rep`, `status`, `error`,
`elapsed_generation_s`, `elapsed_simulation_s`, `llm_calls`,
`llm_tokens_estimate`, `generated_model_file`, `kpis`
(`throughput_per_hour`, `utilization`, `wip_parts`, `energy_per_part_kwh`,
`native`), `assumptions`, `notes`.

A missing or non-numeric indicator is `null`, **never fabricated**. Methods that
cannot express an indicator leave it null; the coverage asymmetry is itself a
finding (model expressiveness), not an error.

**Coverage matrix**

| Indicator | Truth | A | B | C |
|---|---|---|---|---|
| throughput | ✔ | ✔ | ✔ | ✔ (DES slot, executed) |
| utilisation per machine | ✔ | ✔ | — | — |
| WIP | ✔ | approx (buffers) | ✔ | ✔ (DES slot, executed) |
| energy per part | ✔ | — | ✔ | ✔ (DES slot, executed) |
| recovered structure | ✔ | ✔ | ✔ | ✔ (requirements + schema; DT config/script captured, not executed; DES executed) |

In practice A's KPI yield is throughput (plus a separately reported utilisation
APE); it expresses no WIP or energy at all.

### 1.6 Status semantics

`ok | service_unavailable | generation_error | simulation_error | timeout |
parse_error`.

- The **harness's own** failures (its responder LLM at OpenRouter being
  unreachable) are `service_unavailable` and blame the dependency, not the
  method — C's reachability probe, reads, polls and session creation are
  retried (`C.net_retries`) before that verdict. An `HTTPError` is never
  `service_unavailable`: the service answered, so it is charged to the method.
- **C's rep status is derived from its stages**, not from "the pipeline
  returned". A C rep is `ok` only when its DES slot produced a contract-bearing
  KPI payload; otherwise the verdict comes from the deepest failing stage
  (execution exited non-zero / timed out / no contract / no model / a stage's
  poll timeout) and `native.status_basis` records which stage it came from.
  This rule lives in `adapters/base.py::derive_rep_status` and is applied by
  both the adapter and `report.py`, so a rep stored under the old semantics is
  *rendered* under its stage outcome with `(recorded \`ok\`)` shown beside it
  rather than silently restated.

### 1.7 Metric dimensions and formulas

Per case `c`, method `m`, repetition `r ∈ 1..R`:

| Dimension | Metric | Formula |
|---|---|---|
| **Validity** | success rate | fraction of generations yielding a runnable model and parseable KPIs |
| **Behaviour** | indicator MAPE | per rep, the mean of `|pred−truth|/truth` over the indicators *both* sides express; per indicator separately |
| **Behaviour** | distribution test | 2-sample KS between a method's KPI values over its reps and the truth's over its reference replications |
| **Structural** (secondary) | parameter error | for each parameter in `truth_structure.json`, `|pred−true|/true`; extraction is method-specific and best-effort |
| **Robustness** | variance & outliers | std/IQR of throughput across reps; count of `simulation_error` + timeouts |
| **Autonomy** | human interventions | harness-answered prompts + wall time, logged |
| **Cost** | LLM usage | `llm_calls`, token estimate, wall time per generation |

**Aggregation rule (reproducible).** Per case and method the reported figure is
the **median over that method's `ok` reps** of the per-rep mean MAPE; the
aggregate across cases is the **median of those per-case figures**, with `n`
reported (never a pool of individual reps). Utilisation is excluded from the
MAPE aggregate and reported separately as A's APE.

### 1.8 Replication, seeding, statistics

- `repetitions = 3` (independent LLM generations, fresh seeds); truth precision
  comes from `reference.replications = 10` and is independent of LLM cost.
- Reps are never discarded to improve a method's numbers.
- Statistical plan: Wilcoxon signed-rank over cases for pairwise comparisons
  (paired by case); with A/B/C all present, Friedman per indicator + Nemenyi
  post-hoc; KS per indicator for the behaviour dimension; α = 0.05, two-sided.
  **With n = 5 cases these tests are underpowered and are reported as
  indicative only.**

### 1.9 Deliberately not compared

- No "steered" second pass (truth-informed re-generation) — baseline only.
- C's PyChrono multi-physics script is **measured, never executed**: PyChrono is
  not on the harness host and the script models rigid bodies, not the case's
  discrete-event semantics. Only the size, the machine-id mentions and the
  `pychrono` import are recorded, and nothing is derived from it.
- Token-exact cost (only call counts and wall time; `llm_tokens_estimate` is
  null for all three).

### 1.10 Why SimBench could not be used for A and B

**What SimBench is.** It is method C's *own* benchmark, living in C's repository
(`benchmarks/simbench.py`, `benchmarks/README.md`, inputs
`benchmarks/llm_judge/llm_judge_input/simbench_input_turn[1-3]_v0.json`). It
implements the protocol of Wang J. et al., "SimBench: A Framework for Evaluating
and Diagnosing LLM-Based Digital-Twin Generation for Multi-Physics Simulation"
(IEEE Trans. AI; arXiv:2408.11987v2): three turns (Turn 1 Vague → Turn 2 Sharp →
Turn 3 Complex) on a steel continuous-casting digital-twin task, where the model
must emit a **PyChrono** rigid-body multi-physics script, and scoring is a
J-LLM-as-a-judge rubric (Completeness 40, Correctness 30, Code Quality 10,
Efficiency 10, Error Handling 5, Visualization 5) plus a pairwise
"sllm vs baseline" comparison and Pass@1.

Why it does not apply to A and B:

1. **Wrong artefact class (wrong engine).** SimBench grades a **PyChrono**
   script against PyChrono API criteria (`ChSystemNSC`, `AddBody`/`AddLink`,
   `ChLidarSensor`, `DoStepDynamics`, `chrono_irrlicht`). A emits a
   **FactorySimPy** component network; B emits a self-contained **SimPy** model
   (built via pm4py from the event log). Neither produces PyChrono code, so the
   rubric has no referent — any A or B artefact would fail
   Completeness/Correctness/Visualization for being "the wrong framework". That
   score would measure output format, not the methods.
2. **Wrong scoring object: judge rubric vs KPI recovery.** SimBench's score is
   an LLM judge's opinion and a pairwise preference against a baseline — a
   gradient of *plausibility and code quality* over code text. The comparison's
   question is numeric: how close the model's throughput/WIP/energy is to the
   seeded SimPy ground truth. SimBench has no ground-truth plant and produces no
   KPIs, so it cannot answer behavioural accuracy for anyone — not for A and B,
   and not even for C, whose SimBench run grades the PyChrono slot rather than
   the DES slot this comparison is about.
3. **Wrong task and inputs.** SimBench's inputs are a fixed steel-casting
   scenario with task texts and reference baseline codes across three escalating
   turns. A and B have their own inputs (`prompt_A.txt` — prose plus a table;
   `eventlog.csv`) and are **one-shot** generators: there is no Turn 1/2/3
   dialogue to drive, and no steel-casting task to hand them. Feeding them the
   steel texts would change the task, so what was measured would no longer be
   the comparison's pipeline.
4. **It would replace the object of study.** The comparison holds the case set
   (5 SimPy-truth plants) fixed and scores each method against the same truth;
   SimBench would swap the case set for a single steel scenario and the numeric
   truth for a judge's opinion — a different experiment.

For these reasons SimBench has no row for A and B: it stays C's internal
benchmark (grading, within C, a slot other than the one this comparison scores),
not an alternative protocol for all three methods.

---

## 2. Method A — FactoryFlow (brief)

- **What it is.** A natural-language-to-simulation generator. It receives
  `prompt_A.txt` — prose plus a table describing the same plant A's authors
  designed for — and returns Python source that defines a parameterised
  **FactorySimPy** component network.
- **How the harness drives it.** `from IM.AMG_with_langgraph import
  run_amg_wrapper`, executed with `cwd` at the Streamlit `app/` directory and
  `sys.path` extended with `app/` and `app/src` (FactorySimPy is not
  pip-installed). The generated code runs in a fresh subprocess behind a
  sanitising prelude (a stub `streamlit` module, `MPLBACKEND=Agg`), and a probe
  appended after the model reads `Machine.stats` (`num_item_processed`,
  `total_time_spent_in_states`) plus buffer content and prints one tagged JSON
  line. A `generation_error` from this method is frequently an HTTP 402
  (credit/max-token budget) rather than a modelling failure; a
  `simulation_error` is the generated model exiting non-zero.
- **What it can express.** Throughput and per-machine utilisation. **WIP and
  energy are not part of its output contract**, so those columns are `null` for
  A by construction.
- **Why not SimBench.** SimBench grades a PyChrono script, while A emits a
  FactorySimPy network; its rubric would score the framework, not the method
  (§1.10).
- **Known measurement caveats** (recorded, not corrected):
  - *Availability has no library primitive.* FactorySimPy contains no
    mtbf/mttr or failure/repair concept, so availability must be hand-rolled by
    the generated code. Two observed outcomes of the same case show both ways
    this fails invisibly: one model ignored availability entirely and still
    returned a throughput within 0.2 % of truth, another invented the API
    (`Machine(..., mtbf=…)`) and landed as `simulation_error`. **An `ok` from A
    does not mean the case's availability was modelled** — read the generated
    code before attributing a KPI to the system.
  - *Cold start.* A's prompt asks it to simulate `window_s` from t = 0, so its
    measurement window is `[0, 432000]` against the truth's `[21600, 453600]`:
    the durations match but A keeps the 6 h transient and drops the last 6 h.
    Relevant only to residual error near the noise floor (throughput is far less
    transient-sensitive than WIP, which A does not report).

---

## 3. Method B — LLM-DES-Modeling (brief)

- **What it is.** A process-mining-to-simulation generator. It consumes the
  plant's `eventlog.csv` (`MachineName`, `StartTime`, `EndTime`, `ReasonCode`
  ∈ {Working, Idle, Stopped}, `EnergyConsumption` in kJ), computes pm4py
  metrics and a sequence representation, then asks a builder LLM for a
  self-contained **SimPy** model.
- **How the harness drives it.** In the LLM-DES venv, mirroring the repo's
  headless path: `eventlog.load/preprocess`, `metrics.compute`,
  `to_sequence_text`, then
  `ModelBuilder(client).build(blueprint_code, stations_md, sequence_text,
  buffers, defects, manual_note)`, with `aux_B.txt` supplying buffers/defects.
  The adapter passes the blueprint and a `stations_md` table derived from the
  same case bundle. Execution reuses the repo's own runner: the model is
  sub-processed and its stdout contract parsed
  (`Throughput = … parts/hour`, `WIP = … parts`, `Mean Energy Consumption per
  Part = … kWh/part`).
- **Horizon (fixed 2026-09-18).** Earlier B runs passed a fixed 7-day sim after
  a 1-day warm-up regardless of case, while the truth measures 5 days after 6 h;
  **every B result recorded before that fix is not comparable to
  `truth_kpis.json`.** The adapter now derives `sim_time = warmup_s + window_s`
  and `warmup_seconds = warmup_s` from the bundle's `reference` block (config
  values are only a fallback). The fix is in place in the run cited in §5.
- **What it can express.** Throughput, WIP and energy per part — but **no
  utilisation**, so the utilisation comparison is A-only.
- **Why not SimBench.** SimBench grades a PyChrono script, while B emits a
  self-contained SimPy model from a process-mining step; its rubric measures
  code plausibility against a judge, not KPI recovery (§1.10).

---

## 4. Method C — DigitalTwinBuilder, and the DES stage inside its DT agent

### 4.1 The service and its agents

C is not a local tool: it is a FastAPI service reached over HTTP at the URL in
`dtb_repo/.env` (`API_URL`; the final run hit `http://176.119.159.227:8000`).
Agents are addressed by index — **UI = 0, DB = 1, DT = 2**, the mapping the
method's own repo uses. The harness's pipeline is
`POST /sessions` → `POST /conversations` (seeded with C's own system prompt) →
`POST /conversations/{id}/messages` → `POST /tasks` → poll `GET /tasks/{id}`.
Task submission is **never retried** (a repeat would bill the model twice);
reads and polls are retried.

The service is an inference host with no published model card: agent identity
and its own model ids are **not recorded** in `environment.json`. What is
recorded is the harness-side responder (`openai/gpt-5-mini`) and C's per-agent
call split.

### 4.2 From interview to requirements and schema

1. **UI agent (0)** — interview loop until the reply's `completed` flag is true
   or `C.max_interview_turns` is reached. Output: the **requirements JSON**
   (line topology, stations, buffers, arrival, sensors, `des_horizon`, …).
2. **DB agent (1)** — a conversation seeded with `make_db_prompt(requirements)`
   returns **PostgreSQL DDL** (`CREATE TABLE`/`INSERT`/indexes, views optional).
   Since the 2026-09-21 DB amendment the reply is validated as **SQL**, not as
   JSON: `sql_runner.check` is parse-only (no server is contacted) and requires
   at least one `CREATE TABLE`, rejecting a JSON document, unparseable
   statements and relations used but never created. A rejected reply draws a
   repair turn (`make_db_repair`, up to `C.db_repair_attempts`).
3. **DT agent (2)** — three conversation slots (below), fed the requirements
   *and* the schema.

### 4.3 The DT agent's three slots

The DT agent is driven through three slots, exactly as the method's own
`streamlit-app.py` does (same prompts, same `conv_idx`, same token budgets):

| Slot | System prompt | User prompt | Output | `max_tokens` |
|---|---|---|---|---|
| 0 | `GenConf` | `make_gen_conf(requirements, db_schema)` | twin configuration (JSON) | 3000 |
| 1 | `GenSim` | `make_gen_sim(requirements, db_schema)` | **PyChrono** multi-physics script | 3000 |
| 2 | `GenDES` | `make_gen_des(requirements, db_schema)` | **discrete-event SimPy model** | **8000** |

All prompts are `exec`'d at runtime from `dtb_repo/src/digital_twin_builder/prompts/*.py`,
so a prompt edit in C's repo propagates on the next run with no harness change.
Slot 1 is captured and measured but never executed (§1.9).

### 4.4 The DES slot: adapt the reference program, don't write one

Slot 2 is asked for a SimPy program that prints the **same three-line KPI
contract B prints** — through the same parser (`parse_b_stdout`), the same
horizon and the same measurement definition — which is what makes C's and B's
numbers directly comparable.

Two properties of the prompt do the heavy lifting:

- **A reference blueprint (`DES_BLUEPRINT`).** `GenDES` embeds a known-good
  SimPy program: source → stations → buffers → sink, with a parameterised
  `PARAMETERS` block, `STATIONS`, `BUFFERS`, `INTER_ARRIVAL_S`, `WARMUP_S`,
  `WINDOW_S`, `REPLICATIONS`. The prompt phrases the task as **adapt, not
  write** — change the parameter values (and the length of the station/buffer
  lists) and leave the model and the KPI block alone. The KPI block is
  therefore *inherited* rather than authored.
- **The blueprint's KPI arithmetic is exact by construction.** WIP and power
  draw are integrated by a `Ledger` at **event granularity** (every event that
  moves a part or changes a station state calls `sync` *before* the change), so
  nothing is sampled and a state shorter than any sampling interval still
  contributes exactly its own duration. Spans before the warm-up boundary are
  discarded, which makes warm-up free. Throughput divides the parts that left
  the last station **by `window_s / 3600`** — the count-vs-rate error that
  broke earlier programs is structurally excluded. Replications are seeded, and
  the mean of each KPI is printed by the blueprint's own `main()`.
- The prompt also states the KPI definitions and a **self-check**: a serial line
  cannot exceed `3600 / max(processing_time_s)` parts/hour, and energy per part
  cannot exceed the busy-draw of one part divided by the worst availability.

The requirements handed to the slot carry the injected `des_horizon` =
`{warmup_s, window_s, replications}` from the case bundle (e.g. case_0001:
21600 / 432000 / 10).

### 4.5 Execution, acceptance gate and execute-and-repair

The harness does not trust that the printed numbers came from the line it was
given. The DES slot runs C's own `des_runner.py`:

- **`execute`** — writes the program, runs it under `C.des_python`
  (`comparison/.venv-des/bin/python`, a SimPy-capable interpreter), with
  `C.des_exec_timeout_s = 900`.
- **`parse_kpis`** — extracts the three contract lines from stdout.
- **`verify`** — accepts only if the program ran cleanly, **and** printed the
  contract, **and** the numbers are possible for the declared line. The
  semantic gate is `_serial_bounds` + `_implausible_kpis`, which derive bounds
  from the *requirements' own parameters* (never from the case truth):
  - throughput ceiling `3600 / max(processing_time_s) × 1.05`;
  - throughput floor `min(3600/max_processing_time_s, 3600/inter_arrival_time_s)
    × min(availability) × 0.5`;
  - energy ceiling `Σ(power_working_kw × processing_time_s / 3600) /
    min(availability) × 1.10`;
  - WIP and energy cannot be 0 while parts are being produced
    (`_all_zero_implausible`, gated by `C.des_reject_all_zero`).
  A non-serial topology is not bounded; an absent `topology` is read as serial;
  no bound is invented when a parameter is missing; the energy ceiling is
  dropped when a station draws more when idle than working. Slacks (1.05, 0.5,
  1.10) come from the margin the five reference lines' ground truth keeps on
  each bound. Malformed requirement shapes are read as *no bound* rather than
  raising, because the gate runs on every replication.
- **`generate_with_repair`** — a verdict that is not `ok` (crash, timeout, no
  contract, or a bound violation) is fed back **verbatim** with the previous
  program as a follow-up turn (`make_gen_des_repair`), up to
  `C.des_repair_attempts` = 3 (at most 4 programs). `des_stage` and the KPI
  fields describe the **last** program; `des_gave_up_reason` is null when the
  last program was accepted.

C's own app runs the same engine (`streamlit-app.py::dt_generate_des`), so the
harness and the product agree by construction.

### 4.6 Why the measurement is C's, not the harness's

Because the harness reproduces C's control flow rather than calling the
Streamlit app, the DB gate, the DES gate and the repair loops had to be
**mirrored** in `adapters/method_c_adapter.py` for the fixes to reach the
measurement. They are not re-typed: `_des_gate()` execs C's `des_runner.py` and
`_sql_gate()` execs C's `sql_runner.py`, and both the hardened system prompt and
the repair user prompts are loaded from C's `prompts/`. Consequences:

- A rep cannot pass a check here that it would fail in C's own app.
- A prompt or gate edit in C's repo propagates with no harness change.
- The recorded run labels reflect this: a run after a gate change is a
  **different method** from a run before it, and the two must not be pooled.

**Status semantics do not move with these amendments.** A gate verdict is a
*recorded property* (`db_stage`, `des_stage`), never a rep-status input:
`derive_rep_status` reads DB/DES notes only for a timeout or an unreachable
endpoint. The amendment is not allowed to make C look better by reclassifying a
rep, so e.g. a `0/0/0` program still reads `des_stage: ok` and must be
separated from a real measurement by reading `des_gave_up_reason` /
`des_programs` / `des_repairs_used`.

### 4.7 What the DES stage yielded in the final run

In `20260921_073238_post-amendment`:

- **All 14 `ok` reps produced a contract-bearing DES model** — `des_stage = ok`,
  `des_programs = 1`, `des_repairs_used = 0`, `des_gave_up_reason = null`, and
  every generated program carries the blueprint's own classes (`class Ledger`,
  `class Sink` are present in all 14 `artifacts/dtb_des.py`). **No repair round
  was spent anywhere in the run**, which is the intended effect of the
  blueprint: first-attempt programs inherit correct KPI arithmetic rather than
  authoring it. (For contrast, the pre-blueprint run
  `20260920_064710_des-repair` has `class Ledger` in **0 of 10** DES artefacts.)
- The single rep with no model is a DES-slot poll timeout, not a gate
  rejection: the slot never returned within its 900 s budget.
- DES execution itself is cheap: `des_exec_elapsed_total_s ≈ 1.0 s` per rep
  (SimPy at event granularity) against a median generation time of ≈ 426 s,
  i.e. the cost sits in the LLM agents, not in running the model.

---

## 5. Final run for each method

### 5.1 Provenance — three runs, not one

The last **real** run per method is used. No single real run exists with all
three methods on the current code, and the two newest run directories
(`20260922_110432`, `20260922_111306`) are `mode: mock` plumbing runs and are
**not results**. The three columns therefore come from three different runs;
they are comparable because the case bundles, truth engine, output contract and
scoring code are identical, but they are **not a pooled experiment** and must be
reported as per-method blocks.

| Method | Run directory | Label | Date | Mode | Reps | Cases | Method's LLM(s) |
|---|---|---|---|---|---|---|---|
| **A** | `runs/20260918_043936` | — | 2026-09-18 | real | 3 | 5 | FactoryFlow, `google/gemini-3.1-pro-preview` via OpenRouter |
| **B** | `runs/20260918_163803` | — | 2026-09-18 | real | 3 | 5 | LLM-DES-Modeling, `gpt-5.1` builder/inspector via OpenRouter |
| **C** | `runs/20260921_073238_post-amendment` | `post-amendment` | 2026-09-21 | real | 3 | 5 | DigitalTwinBuilder service (`http://176.119.159.227:8000`); harness responder `openai/gpt-5-mini` |

Why these three:

- **A** — it is the only real run in which A produced comparable KPIs
  (`20260918_043936`, shared with B). The later A-only run
  (`20260918_162954`) covers only case_0005 and returned `simulation_error` in
  all 3 reps.
- **B** — its numbers are only valid **after** the horizon fix (§3), and
  `20260918_163803` is the first post-fix B run over all 5 cases. All earlier B
  runs must not be cited.
- **C** — the run carrying the DES amendments of 2026-09-20/21 (the
  execute-and-repair loop and the `DES_BLUEPRINT` / semantic acceptance gate,
  §4.4–§4.5); every one of its 14 generated DES programs contains the
  blueprint's own classes, so the cited numbers are the post-blueprint method's.

The C run's single non-`ok` rep is a DES-slot poll timeout at 900 s
(`case_0005` rep2: the slot never returned, so no model was produced and the
rep is `timeout`). Per §1.3.3 it is recorded, not re-rolled.

### 5.2 Headline table — the final run per method

| Method | Run | Validity (ok / 15) | Cases with a KPI (n) | **Median MAPE over cases** | Non-`ok` reps and their cause |
|---|---|---|---|---|---|
| **A** | `20260918_043936` | **4 / 15** | **2 / 5** | **3.6 %** (n = 2) | 8 `simulation_error` (generated model exited 1: 3× case_0001, 2× case_0002, 3× case_0003); 3 `generation_error` (case_0005 ×3 — OpenRouter **HTTP 402**, a credit/max-token budget limit, not a modelling failure) |
| **B** | `20260918_163803` | **14 / 15** | **5 / 5** | **31.6 %** (n = 5) | 1 `simulation_error` (case_0002 rep2, generated model exited 1) |
| **C** | `20260921_073238_post-amendment` | **14 / 15** | **5 / 5** | **1.5 %** (n = 5) | 1 `timeout` (case_0005 rep2 — DES slot poll timeout at 900 s; no model produced) |

**Per-indicator median MAPE** (median over cases of the per-case median; `—` =
the method cannot express the indicator):

| Method | Throughput | WIP | Energy per part |
|---|---|---|---|
| **A** | 3.6 % (n = 2) | — | — |
| **B** | 24.7 % (n = 5) | 39.3 % (n = 5) | 22.6 % (n = 5) |
| **C** | **0.5 %** (n = 5) | **1.8 %** (n = 5) | **0.0 %** (n = 5) |

Additional per-method structural/behaviour facts from the same runs:

- **A** — utilisation APE 0.3 % (3/3 machines matched, case_0002) and 7.1 %
  (5/5 machines, case_0004). The per-case median MAPEs behind the 3.6 % are
  0.17 % (case_0002, 1 ok rep) and 7.03 % (case_0004, 3 ok reps).
- **B** — 1 of 42 KPI cells lands inside the truth's own relative std; 3 of 15
  reps deadlock and print `Throughput = 0.00` with non-zero WIP; one rep fails
  outright on `simpy.Store(env, capacity=None)`.
- **C** — structural recovery over all 15 reps, each carrying stage evidence
  (69 machine slots): machines mentioned **69/69**, process time recovered
  **69/69**, availability recovered **41/69**, buffer capacities **69/69**,
  arrival rate found **15/15 reps**.

### 5.3 Per-case table

`ok/3` = ok reps for that case; the percentage is the case's median MAPE over
its ok reps (the figure §1.7 aggregates). `—` = no KPI from that method for
that case.

| Case | Truth T / WIP / E | A ok/3 | A median MAPE | B ok/3 | B median MAPE | C ok/3 | C median MAPE |
|---|---|---|---|---|---|---|---|
| `case_0001_serial_line` | 19.868 / 40.387 / 0.9892 | 0/3 | — | 3/3 | 31.60 % | 3/3 | **1.45 %** |
| `case_0002_saturated_short_line` | 32.620 / 27.917 / 0.3525 | 1/3 | 0.17 % | 2/3 | 17.95 % | 3/3 | **0.72 %** |
| `case_0003_starved_six_line` | 11.991 / 5.251 / 2.3537 | 0/3 | — | 3/3 | 230.13 % | 3/3 | **9.51 %** |
| `case_0004_failure_heavy_line` | 22.401 / 7.289 / 0.8735 | 3/3 | 7.03 % | 3/3 | 38.28 % | 3/3 | **4.24 %** |
| `case_0005_high_rate_line` | 44.991 / 38.882 / 0.3354 | 0/3 | — | 3/3 | 30.18 % | 2/3 | **0.43 %** |
| **aggregate** | | **4/15** | **3.6 %** (n=2) | **14/15** | **31.6 %** (n=5) | **14/15** | **1.5 %** (n=5) |

Case-by-case reading: where C produced a model it is under 1.5 % on three of the
five cases; its largest deviation is `case_0003` (9.5 %, driven by a WIP
overshoot of +27.8 % in two of three reps), and `case_0004` is next (4.2 %),
where the residual is WIP and throughput on the failure-heavy line. The
blueprint's own validation attributes that direction of error to the **truth
engine's failure model** (a breakdown is armed only while a machine is waiting,
so a machine that stays busy never fails) — B's model deviates the same way
(case_0004: 16.8 / 12.78 vs truth 22.4 / 7.29). This is a shared ceiling, to be
read alongside any per-method error rather than as C's defect alone.

### 5.4 Cost and autonomy (same runs)

| Method | `llm_calls` (total / median per rep) | C's per-agent split | Agent submissions | Interview / repair turns | Generation time, median (sum) | Simulation time, median |
|---|---|---|---|---|---|---|
| **A** | 24 / 2 | — | — | — | 55.7 s (663 s) | 0.1 s |
| **B** | 30 / 2 | — | — | — | 56.5 s (820 s) | 16.2 s |
| **C** | 81 / 5 | ui 23 · db 14 · dt 44 | 83 attempted for 81 answers | 1 interview turn per rep in 15/15 reps; **0 DES repair turns** | 425.9 s (7 899 s) | 1.0 s |

Reading: C buys its accuracy with roughly three times the LLM calls and seven
times the wall time of A/B, and its spend sits inside its own pipeline (the DT
agent alone is 44 of 81 calls). Its autonomy cost in this run is minimal — one
interview turn per rep, in all 15 reps — and, post-amendment, zero repair rounds.

### 5.5 Structural recovery (C only)

| Dimension | Final run |
|---|---|
| machine ids mentioned (vs truth) | 69 / 69 |
| process times recovered | 69 / 69 (100 %) |
| availability recovered | 41 / 69 (59.4 %) |
| buffer capacities recovered | 69 / 69 |
| arrival rate found | 15 / 15 reps |
| DT slots answered (`dt_slots_ok / total`) | 3 / 3 on 14 of 15 reps (2 / 3 on the timed-out rep) |
| machine ids present in the PyChrono script | 5/5, 3/3, 6/6, 5/5, 4/4 per case |

A parameter counts as recovered only when C states a number **under a key that
names the concept** and it equals the truth; the number C actually claimed is
recorded beside the verdict (`*_claimed`), so an invented value is visible
rather than collapsed into a boolean. Availability claimed as a percentage is
accepted against a truth fraction; a value like 95 against 0.92 is neither.

---

## 6. How to read the table — threats to validity

1. **Not one pooled run.** The three columns come from three runs on three
   dates (§5.1). Within each column the comparison is clean (same bundles, same
   truth, same scoring); *across* columns it is a comparison of method results,
   not of one simultaneous three-arm experiment. A publication-grade run would
   be a single `python run_comparison.py --mode real --repetitions 3` with all
   three methods on the current code.
2. **Unequal denominators.** A's 3.6 % is a median over **2 cases** (A yielded a
   KPI in only 4 of 15 reps), while B's and C's are over 5. A's headline number
   is therefore not on the same footing as the others, and its low success rate
   is the more important fact about it. Any A/B/C ranking must carry `n`.
3. **All three of A's case_0005 failures are infrastructure** (OpenRouter HTTP
   402 — a credit/max-token budget limit) rather than modelling behaviour. They
   remain in the table as `generation_error` because §1.3.3 forbids re-rolling;
   they are not evidence about the method.
4. **C's behaviour numbers are conditional on the DES slot.** Throughput, WIP
   and energy exist only when that slot yields a runnable, contract-bearing
   model; Validity, Autonomy, Cost and structural recovery are the dimensions
   comparable over *every* C rep. C's behaviour figures here are 14 of 15 reps,
   and in a smaller/degraded host run the yield can collapse (in
   `runs/20260919_052152` it was 0/3).
5. **C's DES numbers come through the same parser and horizon as B's** but are
   not the same generator: comparability of the *measurement* is exact,
   comparability of the *task* is the point of the study.
6. **C's PyChrono script is never executed**, so no multi-physics claim is
   supported for C — only that the slot ran and what it emitted.
7. **The truth engine has a bounded failure model** (breakdowns only while a
   machine is free), which is the dominant shared error on `case_0004`; all
   methods are scored against the same bounded truth, so this is a shared
   ceiling, not a per-method bias.
8. **n = 5 cases, R = 3.** Wilcoxon/Friedman are underpowered; results are
   indicative. LLM sampling is deliberately not temperature-pinned, so
   repetition-to-repetition spread is a measured property.
9. **The service is a black box** — C's agent identity and models are not
   published or recorded, so the run cannot be reproduced *bit-for-bit* against
   a pinned model; the run's `api_url` and per-agent call counts are recorded in
   every `result.json`.

---

## 7. Reproducibility

```bash
cd /ssd/projects/dt-eval/comparison

python run_comparison.py --mode mock                  # plumbing, no cost
python run_comparison.py --mode real --repetitions 3  # full 3-method design
python report.py runs/<timestamp>                     # render report.md
```

Interpreters/cwds, per-method knobs and the case/method/rep selection come from
`config.yaml`; the OpenRouter key lives in `.env` (an exported shell variable
overrides it). The orchestrator auto-runs `casegen.py` when a bundle's generated
artefacts are missing.

Per generation, `runs/<timestamp>/<case>/<method>/rep<r>/` holds `result.json`,
the generated model, the execution stdout/stderr, and (C) an `artifacts/`
directory with the requirements JSON, the schema reply (`dtb_schema.sql`) and
its JSON wrapper, the twin config, the PyChrono script, the DES program, and
`interview.log` with every turn and every gate verdict. Archive for publication:
case bundles, `runs/`, venv requirements, prompt inputs and the model list in
`RUN_WITH_OPENROUTER.md`.

**Citation of the three runs**

- A: `comparison/runs/20260918_043936` (A column; the same directory also holds
  B's pre-horizon-fix results, which are superseded — use `20260918_163803` for
  B).
- B: `comparison/runs/20260918_163803`.
- C: `comparison/runs/20260921_073238_post-amendment`.
