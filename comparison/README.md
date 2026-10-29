# Comparison harness — FactoryFlow vs LLM-DES-Modeling vs (C)

Compares three LLM-based methods that generate DES / digital-twin models of the
same known-truth manufacturing systems.

| Method | Tool | Native input | Native output |
|---|---|---|---|
| A | `FactoryFlow/FactoryFlow_v2` | NL description (`prompt_A.txt`) | FactorySimPy Python model |
| B | `LLM-DES-Modeling` | event log (`eventlog.csv`) | SimPy Python model |
| C | user method | TBD (adapter stub) | TBD |

Full design, fairness rules, metric definitions and statistical plan:
**[protocol.md](protocol.md)** — read it first.

## Layout

```
comparison/
  protocol.md            the comparison protocol (design document)
  config.yaml            venv paths, mode (mock|real), repetitions
  cases/<case_id>/       one bundle per plant (manifest.yaml + generated
                         eventlog.csv / truth_kpis.json / prompt_A.txt / aux_B.txt)
  truth/plant.py         ground-truth SimPy plant engine (log + KPI synthesis)
  casegen.py             deterministic bundle generator (run under LLM-DES venv)
  adapters/              per-method adapters (A, B, C-stub) — the C integration point
  run_comparison.py      orchestrator (cases x methods x repetitions)
  report.py              renders report.md from a run directory
```

## Quick start

```bash
cd /ssd/projects/dt-eval/comparison

# 1) plumbing check — no LLM calls, uses canned mock models
python run_comparison.py --mode mock

# 2) real runs — set the key once in `.env` (or export OPENROUTER_API_KEY)
python run_comparison.py --mode real --cases case_0001_serial_line --methods A B
python run_comparison.py --mode real --repetitions 3
```

Results go to `runs/<timestamp>/`; open `runs/<timestamp>/report.md`.

### Adding a case
1. `mkdir cases/<id>` and author `manifest.yaml` (see the shipped case and
   protocol.md §3).
2. `python run_comparison.py --mode real --cases <id>` — the orchestrator runs
   `casegen.py` automatically when bundle artefacts are missing.

### Wiring in method C
Implement `adapters/method_c_adapter.py` (real branch) and add its interpreter
to `config.yaml`. See protocol.md §8 for the checklist. No other files change.

## Environment prerequisites

- LLM-DES venv at `LLM-DES-Modeling/.venv` (simpy, pm4py)
- FactoryFlow venv at `FactoryFlow/.venv` (simpy, langgraph, factorysimpy on
  `app/src`)
- `OPENROUTER_API_KEY` for `--mode real` — kept in `.env` at this directory's
  root (edit the file to change it); an exported shell variable overrides it.
  See `RUN_WITH_OPENROUTER.md`.
