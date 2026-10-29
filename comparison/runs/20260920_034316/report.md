# Comparison report — `20260920_034316`
- mode: real | methods: ['C'] | repetitions: 1

## Validity

| Method | ok | simulation_error | timeout | total |
|---|---|---|---|---|
| C | 1 | 3 | 1 | 5 |

## Case case_0001_serial_line

Truth: throughput=19.868056 parts/h, WIP=40.386633 parts, energy=0.989219 kWh/part (std: 0.195889/0.253178/0.001198)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| C | 0 | simulation_error | — | — | — |

### C structure per rep

| rep | status | turns | DB (agent 1) | DT config | DT script | DES run | ids named | values recovered |
|---|---|---|---|---|---|---|---|---|
| 0 | simulation_error | 1 | answered 2618c / DDL (not JSON → stage unavailable) | 6362c / 0 ids | 11412c / 10 ids | simulation_error | 5/5 | time 5/5, avail 5/5, bufs 5/5, arrival found |

- **C** rep0: 

- **C** rep0 notes: status `simulation_error`: the generated DES model was executed and exited non-zero — the pipeline itself completed, so this is the stage outcome, not an adapter failure | structural recovery only: 5/5 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) output was not JSON; raw text kept in artifacts/dtb_schema.json | DT stage (agent 2) ran: 6362 chars of twin config, 11412 chars of PyChrono script; 5/5 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it

_no comparable KPIs_

## Case case_0002_saturated_short_line

Truth: throughput=32.62 parts/h, WIP=27.91672 parts, energy=0.352459 kWh/part (std: 0.118712/0.058013/8.6e-05)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| C | 0 | simulation_error | — | — | — |

### C structure per rep

| rep | status | turns | DB (agent 1) | DT config | DT script | DES run | ids named | values recovered |
|---|---|---|---|---|---|---|---|---|
| 0 | simulation_error | 1 | answered 2822c / DDL (not JSON → stage unavailable) | 5340c / 0 ids | 12673c / 6 ids | simulation_error | 3/3 | time 3/3, avail 3/3, bufs 3/3, arrival found |

- **C** rep0: 

- **C** rep0 notes: status `simulation_error`: the generated DES model was executed and exited non-zero — the pipeline itself completed, so this is the stage outcome, not an adapter failure | structural recovery only: 3/3 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) output was not JSON; raw text kept in artifacts/dtb_schema.json | DT stage (agent 2) ran: 5340 chars of twin config, 12673 chars of PyChrono script; 3/3 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it

_no comparable KPIs_

## Case case_0003_starved_six_line

Truth: throughput=11.990833 parts/h, WIP=5.25071 parts, energy=2.353658 kWh/part (std: 0.037975/0.303141/0.003344)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| C | 0 | ok | 0 (100.0% err) | 0 (100.0% err) | 0 (100.0% err) |

### C structure per rep

| rep | status | turns | DB (agent 1) | DT config | DT script | DES run | ids named | values recovered |
|---|---|---|---|---|---|---|---|---|
| 0 | ok | 1 | answered 2014c / DDL (not JSON → stage unavailable) | 4266c / 0 ids | 11634c / 12 ids | ok, 3/3 KPIs | 6/6 | time 6/6, avail 6/6, bufs 6/6, arrival found |


- **C** rep0 notes: structural recovery only: 6/6 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) output was not JSON; raw text kept in artifacts/dtb_schema.json | DT stage (agent 2) ran: 4266 chars of twin config, 11634 chars of PyChrono script; 6/6 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it

## Case case_0004_failure_heavy_line

Truth: throughput=22.400833 parts/h, WIP=7.28912 parts, energy=0.873547 kWh/part (std: 0.819642/0.855812/0.003851)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| C | 0 | timeout | — | — | — |

### C structure per rep

| rep | status | turns | DB (agent 1) | DT config | DT script | DES run | ids named | values recovered |
|---|---|---|---|---|---|---|---|---|
| 0 | timeout | 1 | answered 3667c / DDL (not JSON → stage unavailable) | 6569c / 0 ids | 10653c / 10 ids | no model | 5/5 | time 5/5, avail 0/5, bufs 5/5, arrival found, claimed: M1 a=92.58, M2 a=97.36, M3 a=94.69, M4 a=100, M5 a=98.23 |

- **C** rep0: 

- **C** rep0 notes: status `timeout`: a stage's task poll timed out — the pipeline itself completed, so this is the stage outcome, not an adapter failure | structural recovery only: 5/5 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) output was not JSON; raw text kept in artifacts/dtb_schema.json | DT stage (agent 2) ran: 6569 chars of twin config, 10653 chars of PyChrono script; 5/5 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it | DT stage (agent 2): DT agent (agent 2) partial: des: poll timeout after 900.0s

_no comparable KPIs_

## Case case_0005_high_rate_line

Truth: throughput=44.990833 parts/h, WIP=38.88238 parts, energy=0.335373 kWh/part (std: 0.035015/0.094204/9.9e-05)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| C | 0 | simulation_error | — | — | — |

### C structure per rep

| rep | status | turns | DB (agent 1) | DT config | DT script | DES run | ids named | values recovered |
|---|---|---|---|---|---|---|---|---|
| 0 | simulation_error | 1 | answered 3090c / DDL (not JSON → stage unavailable) | 5545c / 0 ids | 8645c / 8 ids | simulation_error | 4/4 | time 4/4, avail 0/4, bufs 4/4, arrival found, claimed: M1 a=99.99, M2 a=100, M3 a=99.88, M4 a=100 |

- **C** rep0: 

- **C** rep0 notes: status `simulation_error`: the generated DES model was executed and exited non-zero — the pipeline itself completed, so this is the stage outcome, not an adapter failure | structural recovery only: 4/4 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) output was not JSON; raw text kept in artifacts/dtb_schema.json | DT stage (agent 2) ran: 5545 chars of twin config, 8645 chars of PyChrono script; 4/4 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it

_no comparable KPIs_

## Aggregated headline error (median MAPE over cases)

| Method | median MAPE (throughput/WIP/energy) |
|---|---|
| C | 100.0% (n=1 cases) |

_Paired non-parametric tests (Friedman/Wilcoxon) apply once >=5 cases exist; skipped here._