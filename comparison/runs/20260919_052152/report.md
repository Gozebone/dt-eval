# Comparison report — `20260919_052152`
- mode: real | methods: ['C'] | repetitions: 3

## Validity

| Method | ok | generation_error | total |
|---|---|---|---|
| C | 3 | 12 | 15 |

## Case case_0001_serial_line

Truth: throughput=19.868056 parts/h, WIP=40.386633 parts, energy=0.989219 kWh/part (std: 0.195889/0.253178/0.001198)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| C | 0 | generation_error | — | — | — |
| C | 1 | generation_error | — | — | — |
| C | 2 | generation_error | — | — | — |

- **C** rep0 notes: Method C could not be driven; no structure recovered
- **C** rep1 notes: Method C could not be driven; no structure recovered
- **C** rep2 notes: Method C could not be driven; no structure recovered

_no comparable KPIs_

## Case case_0002_saturated_short_line

Truth: throughput=32.62 parts/h, WIP=27.91672 parts, energy=0.352459 kWh/part (std: 0.118712/0.058013/8.6e-05)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| C | 0 | generation_error | — | — | — |
| C | 1 | generation_error | — | — | — |
| C | 2 | generation_error | — | — | — |

- **C** rep0 notes: Method C could not be driven; no structure recovered
- **C** rep1 notes: Method C could not be driven; no structure recovered
- **C** rep2 notes: Method C could not be driven; no structure recovered

_no comparable KPIs_

## Case case_0003_starved_six_line

Truth: throughput=11.990833 parts/h, WIP=5.25071 parts, energy=2.353658 kWh/part (std: 0.037975/0.303141/0.003344)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| C | 0 | generation_error | — | — | — |
| C | 1 | generation_error | — | — | — |
| C | 2 | ok | — | — | — |

### C structure per rep

| rep | status | turns | DB (agent 1) | DT config | DT script | DES run | ids named | values recovered |
|---|---|---|---|---|---|---|---|---|
| 0 | generation_error | — | — | — | — | — | —/— | — |
| 1 | generation_error | — | — | — | — | — | —/— | — |
| 2 | ok | 1 | answered 2844c / DDL (not JSON → stage unavailable) | no output | no output | no model | 1/6 | time 1/6, avail 0/6, bufs 1/6, arrival missing, (pre-2026-09-20 recovery metric — counts not comparable) |

- **C** rep0: URLError: <urlopen error timed out>
- **C** rep1: RuntimeError: interview failed: responder LLM failed: URLError: <urlopen error [Errno 101] Network is unreachable>

- **C** rep0 notes: Method C could not be driven; no structure recovered
- **C** rep1 notes: Method C could not be driven; no structure recovered
- **C** rep2 notes: structural recovery only: 1/6 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) output was not JSON; raw text kept in artifacts/dtb_schema.json | DT stage (agent 2) ran: 0 chars of twin config, 0 chars of PyChrono script; 0/6 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it | DT stage (agent 2): DT agent (agent 2) produced no output for any slot: config: URLError: <urlopen error timed out>; sim: URLError: <urlopen error timed out>; des: URLError: <urlopen error timed out>

_no comparable KPIs_

## Case case_0004_failure_heavy_line

Truth: throughput=22.400833 parts/h, WIP=7.28912 parts, energy=0.873547 kWh/part (std: 0.819642/0.855812/0.003851)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| C | 0 | generation_error | — | — | — |
| C | 1 | generation_error | — | — | — |
| C | 2 | ok | — | — | — |

### C structure per rep

| rep | status | turns | DB (agent 1) | DT config | DT script | DES run | ids named | values recovered |
|---|---|---|---|---|---|---|---|---|
| 0 | generation_error | — | — | — | — | — | —/— | — |
| 1 | generation_error | — | — | — | — | — | —/— | — |
| 2 | ok | 1 | answered 2867c / DDL (not JSON → stage unavailable) | 5050c / 0 ids | 8085c / 4 ids | simulation_error | 3/5 | time 2/5, avail 0/5, bufs 1/5, arrival found, (pre-2026-09-20 recovery metric — counts not comparable) |

- **C** rep0: URLError: <urlopen error timed out>
- **C** rep1: URLError: <urlopen error timed out>

- **C** rep0 notes: Method C could not be driven; no structure recovered
- **C** rep1 notes: Method C could not be driven; no structure recovered
- **C** rep2 notes: structural recovery only: 3/5 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) output was not JSON; raw text kept in artifacts/dtb_schema.json | DT stage (agent 2) ran: 5050 chars of twin config, 8085 chars of PyChrono script; 3/5 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it

_no comparable KPIs_

## Case case_0005_high_rate_line

Truth: throughput=44.990833 parts/h, WIP=38.88238 parts, energy=0.335373 kWh/part (std: 0.035015/0.094204/9.9e-05)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| C | 0 | ok | — | — | — |
| C | 1 | generation_error | — | — | — |
| C | 2 | generation_error | — | — | — |

### C structure per rep

| rep | status | turns | DB (agent 1) | DT config | DT script | DES run | ids named | values recovered |
|---|---|---|---|---|---|---|---|---|
| 0 | ok | 1 | answered 2442c / DDL (not JSON → stage unavailable) | 3745c / 0 ids | 12820c / 2 ids | simulation_error | 1/4 | time 0/4, avail 0/4, bufs 1/4, arrival missing, (pre-2026-09-20 recovery metric — counts not comparable) |
| 1 | generation_error | — | — | — | — | — | —/— | — |
| 2 | generation_error | — | — | — | — | — | —/— | — |

- **C** rep1: RuntimeError: interview failed: agent returned non-JSON after 3 attempts: <think>

</think>
completed: false
message: Уточните, какой тип производства вы производите? Также, какие процессы и оборудование используются в вашем производстве? Уточните, какие датчики используются для отслеживания парамет
- **C** rep2: URLError: <urlopen error timed out>

- **C** rep0 notes: structural recovery only: 1/4 machines mentioned in C's requirements | requirements document names the measured quantities but carries no parameter values (C's requirements stage records sensor kinds only) | DB stage (agent 1) not recovered — DB agent (agent 1) output was not JSON; raw text kept in artifacts/dtb_schema.json | DT stage (agent 2) ran: 3745 chars of twin config, 12820 chars of PyChrono script; 1/4 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it
- **C** rep1 notes: Method C could not be driven; no structure recovered
- **C** rep2 notes: Method C could not be driven; no structure recovered

_no comparable KPIs_

## Aggregated headline error (median MAPE over cases)

| Method | median MAPE (throughput/WIP/energy) |
|---|---|

_Paired non-parametric tests (Friedman/Wilcoxon) apply once >=5 cases exist; skipped here._