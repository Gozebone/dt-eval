# Comparison report — `20260920_064710_des-repair`
- mode: real | methods: ['C'] | repetitions: 3

## Validity

| Method | ok | generation_error | simulation_error | timeout | total |
|---|---|---|---|---|---|
| C | 7 | 3 | 3 | 2 | 15 |

## Case case_0001_serial_line

Truth: throughput=19.868056 parts/h, WIP=40.386633 parts, energy=0.989219 kWh/part (std: 0.195889/0.253178/0.001198)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| C | 0 | generation_error | — | — | — |
| C | 1 | simulation_error | — | — | — |
| C | 2 | generation_error | — | — | — |

### C structure per rep

| rep | status | turns | DB (agent 1) | DT config | DT script | DES run | ids named | values recovered |
|---|---|---|---|---|---|---|---|---|
| 0 | generation_error | — | — | — | — | — | —/— | — |
| 1 | simulation_error | 1 | answered 1934c / DDL (not JSON → stage unavailable) | 5813c / 0 ids | 12343c / 10 ids | simulation_error | 5/5 | time 5/5, avail 5/5, bufs 5/5, arrival found |
| 2 | generation_error | — | — | — | — | — | —/— | — |

- **C** rep0: RuntimeError: interview failed: poll timeout after 600.0s
- **C** rep1: 
- **C** rep2: RuntimeError: interview failed: agent task failed: Processing error: ("Connection broken: ConnectionResetError(104, 'Connection reset by peer')", ConnectionResetError(104, 'Connection reset by peer'))

- **C** rep0 notes: Method C could not be driven; no structure recovered
- **C** rep1 notes: status `simulation_error`: the generated DES model was executed and exited non-zero — the pipeline itself completed, so this is the stage outcome, not an adapter failure | structural recovery only: 5/5 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) output was not JSON; raw text kept in artifacts/dtb_schema.json | DT stage (agent 2) ran: 5813 chars of twin config, 12343 chars of PyChrono script; 5/5 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it
- **C** rep2 notes: Method C could not be driven; no structure recovered

_no comparable KPIs_

## Case case_0002_saturated_short_line

Truth: throughput=32.62 parts/h, WIP=27.91672 parts, energy=0.352459 kWh/part (std: 0.118712/0.058013/8.6e-05)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| C | 0 | ok | 34.57 (6.0% err) | 27.18 (2.6% err) | 0.3438 (2.4% err) |
| C | 1 | ok | 29.36 (10.0% err) | 23.3 (16.5% err) | 47.2 (13292.6% err) |
| C | 2 | simulation_error | — | — | — |

### C structure per rep

| rep | status | turns | DB (agent 1) | DT config | DT script | DES run | ids named | values recovered |
|---|---|---|---|---|---|---|---|---|
| 0 | ok | 1 | answered 1966c / DDL (not JSON → stage unavailable) | 7281c / 0 ids | 10203c / 6 ids | ok, 3/3 KPIs | 3/3 | time 3/3, avail 3/3, bufs 3/3, arrival found |
| 1 | ok (8 sub / 6 ans) | 1 | timeout 600s | no output | 8111c / 6 ids | ok, 3/3 KPIs | 3/3 | time 3/3, avail 3/3, bufs 3/3, arrival found |
| 2 | simulation_error | 1 | answered 2940c / DDL (not JSON → stage unavailable) | 5996c / 0 ids | 11566c / 6 ids | simulation_error | 3/3 | time 3/3, avail 3/3, bufs 3/3, arrival found |

- **C** rep2: 

- **C** rep0 notes: structural recovery only: 3/3 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) output was not JSON; raw text kept in artifacts/dtb_schema.json | DT stage (agent 2) ran: 7281 chars of twin config, 10203 chars of PyChrono script; 3/3 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it
- **C** rep1 notes: structural recovery only: 3/3 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) failed: poll timeout after 600.0s — requirements recovered, schema stage unavailable | DT stage (agent 2) ran: 0 chars of twin config, 8111 chars of PyChrono script; 3/3 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it | DT stage (agent 2): DT agent (agent 2) partial: config: agent task failed: Processing error: OpenRouter request failed after 4 attempts: empty content (finish_reason=stop, provider=Novita, completion_tokens=1404) | DT stage ran with an unavailable DB schema: the DB stage is one of agent 2's two inputs, so its output here is conditioned on a degraded input (recorded, not substituted with a fabricated schema)
- **C** rep2 notes: status `simulation_error`: the generated DES model was executed and exited non-zero — the pipeline itself completed, so this is the stage outcome, not an adapter failure | structural recovery only: 3/3 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) output was not JSON; raw text kept in artifacts/dtb_schema.json | DT stage (agent 2) ran: 5996 chars of twin config, 11566 chars of PyChrono script; 3/3 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it

## Case case_0003_starved_six_line

Truth: throughput=11.990833 parts/h, WIP=5.25071 parts, energy=2.353658 kWh/part (std: 0.037975/0.303141/0.003344)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| C | 0 | simulation_error | — | — | — |
| C | 1 | ok | 12.57 (4.8% err) | 0 (100.0% err) | 2.286 (2.9% err) |
| C | 2 | generation_error | — | — | — |

### C structure per rep

| rep | status | turns | DB (agent 1) | DT config | DT script | DES run | ids named | values recovered |
|---|---|---|---|---|---|---|---|---|
| 0 | simulation_error | 1 | answered 2009c / DDL (not JSON → stage unavailable) | timeout 900s | 10921c / 12 ids | simulation_error | 6/6 | time 6/6, avail 6/6, bufs 6/6, arrival found |
| 1 | ok (5 sub / 4 ans) | 1 | answered 2883c / DDL (not JSON → stage unavailable) | 5112c / 0 ids | timeout 900s | ok, 3/3 KPIs | 6/6 | time 6/6, avail 6/6, bufs 6/6, arrival found |
| 2 | generation_error | — | — | — | — | — | —/— | — |

- **C** rep0: 
- **C** rep2: RuntimeError: interview failed: poll timeout after 600.0s

- **C** rep0 notes: status `simulation_error`: the generated DES model was executed and exited non-zero — the pipeline itself completed, so this is the stage outcome, not an adapter failure | structural recovery only: 6/6 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) output was not JSON; raw text kept in artifacts/dtb_schema.json | DT stage (agent 2) ran: 0 chars of twin config, 10921 chars of PyChrono script; 6/6 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it | DT stage (agent 2): DT agent (agent 2) partial: config: poll timeout after 900.0s
- **C** rep1 notes: structural recovery only: 6/6 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) output was not JSON; raw text kept in artifacts/dtb_schema.json | DT stage (agent 2) ran: 5112 chars of twin config, 0 chars of PyChrono script; 0/6 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it | DT stage (agent 2): DT agent (agent 2) partial: sim: poll timeout after 900.0s
- **C** rep2 notes: Method C could not be driven; no structure recovered

## Case case_0004_failure_heavy_line

Truth: throughput=22.400833 parts/h, WIP=7.28912 parts, energy=0.873547 kWh/part (std: 0.819642/0.855812/0.003851)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| C | 0 | ok | 8.06 (64.0% err) | 11.21 (53.8% err) | 0 (100.0% err) |
| C | 1 | timeout | — | — | — |
| C | 2 | ok | 0 (100.0% err) | 68.29 (836.9% err) | 0 (100.0% err) |

### C structure per rep

| rep | status | turns | DB (agent 1) | DT config | DT script | DES run | ids named | values recovered |
|---|---|---|---|---|---|---|---|---|
| 0 | ok | 1 | answered 3930c / DDL (not JSON → stage unavailable) | 5278c / 0 ids | 10085c / 10 ids | ok, 3/3 KPIs | 5/5 | time 5/5, avail 5/5, bufs 5/5, arrival found |
| 1 | timeout | 1 | answered 3058c / DDL (not JSON → stage unavailable) | 4631c / 5 ids | 11046c / 10 ids | no model | 5/5 | time 5/5, avail 5/5, bufs 5/5, arrival found |
| 2 | ok | 1 | answered 1527c / DDL (not JSON → stage unavailable) | 5340c / 0 ids | 11639c / 10 ids | ok, 3/3 KPIs | 5/5 | time 5/5, avail 5/5, bufs 5/5, arrival found |

- **C** rep1: 

- **C** rep0 notes: structural recovery only: 5/5 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) output was not JSON; raw text kept in artifacts/dtb_schema.json | DT stage (agent 2) ran: 5278 chars of twin config, 10085 chars of PyChrono script; 5/5 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it
- **C** rep1 notes: status `timeout`: a stage's task poll timed out — the pipeline itself completed, so this is the stage outcome, not an adapter failure | structural recovery only: 5/5 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) output was not JSON; raw text kept in artifacts/dtb_schema.json | DT stage (agent 2) ran: 4631 chars of twin config, 11046 chars of PyChrono script; 5/5 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it | DT stage (agent 2): DT agent (agent 2) partial: des: poll timeout after 900.0s
- **C** rep2 notes: structural recovery only: 5/5 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) output was not JSON; raw text kept in artifacts/dtb_schema.json | DT stage (agent 2) ran: 5340 chars of twin config, 11639 chars of PyChrono script; 5/5 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it

## Case case_0005_high_rate_line

Truth: throughput=44.990833 parts/h, WIP=38.88238 parts, energy=0.335373 kWh/part (std: 0.035015/0.094204/9.9e-05)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| C | 0 | timeout | — | — | — |
| C | 1 | ok | 5666 (12494.1% err) | 26.63 (31.5% err) | 0.3073 (8.4% err) |
| C | 2 | ok | 246.6 (448.2% err) | 0.05 (99.9% err) | 0.7028 (109.6% err) |

### C structure per rep

| rep | status | turns | DB (agent 1) | DT config | DT script | DES run | ids named | values recovered |
|---|---|---|---|---|---|---|---|---|
| 0 | timeout | 1 | answered 2287c / DDL (not JSON → stage unavailable) | 4829c / 4 ids | 12052c / 8 ids | no model | 4/4 | time 4/4, avail 4/4, bufs 4/4, arrival found |
| 1 | ok | 1 | answered 2820c / DDL (not JSON → stage unavailable) | 6908c / 4 ids | 8171c / 8 ids | ok, 3/3 KPIs | 4/4 | time 4/4, avail 0/4, bufs 4/4, arrival found, claimed: M1 a=99.99, M2 a=100, M3 a=99.88, M4 a=100 |
| 2 | ok (6 sub / 5 ans) | 1 | answered 3456c / DDL (not JSON → stage unavailable) | timeout 900s | 9189c / 8 ids | ok, 3/3 KPIs | 4/4 | time 4/4, avail 4/4, bufs 4/4, arrival found |

- **C** rep0: 

- **C** rep0 notes: status `timeout`: a stage's task poll timed out — the pipeline itself completed, so this is the stage outcome, not an adapter failure | structural recovery only: 4/4 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) output was not JSON; raw text kept in artifacts/dtb_schema.json | DT stage (agent 2) ran: 4829 chars of twin config, 12052 chars of PyChrono script; 4/4 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it | DT stage (agent 2): DT agent (agent 2) partial: des: poll timeout after 900.0s
- **C** rep1 notes: structural recovery only: 4/4 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) output was not JSON; raw text kept in artifacts/dtb_schema.json | DT stage (agent 2) ran: 6908 chars of twin config, 8171 chars of PyChrono script; 4/4 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it
- **C** rep2 notes: structural recovery only: 4/4 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) output was not JSON; raw text kept in artifacts/dtb_schema.json | DT stage (agent 2) ran: 0 chars of twin config, 9189 chars of PyChrono script; 4/4 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it | DT stage (agent 2): DT agent (agent 2) partial: config: poll timeout after 900.0s

## Aggregated headline error (median MAPE over cases)

| Method | median MAPE (throughput/WIP/energy) |
|---|---|
| C | 1203.9% (n=4 cases) |

_Paired non-parametric tests (Friedman/Wilcoxon) apply once >=5 cases exist; skipped here._