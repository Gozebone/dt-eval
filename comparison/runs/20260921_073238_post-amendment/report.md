# Comparison report — `20260921_073238_post-amendment`
- mode: real | methods: ['C'] | repetitions: 3

## Validity

| Method | ok | timeout | total |
|---|---|---|---|
| C | 14 | 1 | 15 |

## Case case_0001_serial_line

Truth: throughput=19.868056 parts/h, WIP=40.386633 parts, energy=0.989219 kWh/part (std: 0.195889/0.253178/0.001198)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| C | 0 | ok | 19.7 (0.9% err) | 40.08 (0.8% err) | 0.9892 (0.0% err) |
| C | 1 | ok | 19.17 (3.5% err) | 40.07 (0.8% err) | 0.9887 (0.0% err) |
| C | 2 | ok | 19.17 (3.5% err) | 40.07 (0.8% err) | 0.9887 (0.0% err) |

### C structure per rep

| rep | status | turns | DB (agent 1) | DT config | DT script | DES run | ids named | values recovered |
|---|---|---|---|---|---|---|---|---|
| 0 | ok | 1 | answered 3472c / DDL (not JSON → stage unavailable) | 5632c / 0 ids | 10998c / 10 ids | ok, 3/3 KPIs | 5/5 | time 5/5, avail 0/5, bufs 5/5, arrival found, claimed: M1 a=99.45, M2 a=96.86, M3 a=99.03, M4 a=97.39, M5 a=99.56 |
| 1 | ok | 1 | answered 3129c / DDL (not JSON → stage unavailable) | 5979c / 0 ids | 12720c / 10 ids | ok, 3/3 KPIs | 5/5 | time 5/5, avail 5/5, bufs 5/5, arrival found |
| 2 | ok | 1 | answered 4316c / DDL (not JSON → stage unavailable) | 4785c / 10 ids | 11925c / 10 ids | ok, 3/3 KPIs | 5/5 | time 5/5, avail 5/5, bufs 5/5, arrival found |


- **C** rep0 notes: structural recovery only: 5/5 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) output was not JSON; raw text kept in artifacts/dtb_schema.json | DT stage (agent 2) ran: 5632 chars of twin config, 10998 chars of PyChrono script; 5/5 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it | DT agent (agent 2, PyChrono codegen) status=offline at start; the stage outcome above is what the run actually produced
- **C** rep1 notes: structural recovery only: 5/5 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) output was not JSON; raw text kept in artifacts/dtb_schema.json | DT stage (agent 2) ran: 5979 chars of twin config, 12720 chars of PyChrono script; 5/5 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it
- **C** rep2 notes: structural recovery only: 5/5 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) output was not JSON; raw text kept in artifacts/dtb_schema.json | DT stage (agent 2) ran: 4785 chars of twin config, 11925 chars of PyChrono script; 5/5 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it

## Case case_0002_saturated_short_line

Truth: throughput=32.62 parts/h, WIP=27.91672 parts, energy=0.352459 kWh/part (std: 0.118712/0.058013/8.6e-05)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| C | 0 | ok | 32.69 (0.2% err) | 27.41 (1.8% err) | 0.3524 (0.0% err) |
| C | 1 | ok | 32.73 (0.3% err) | 27.42 (1.8% err) | 0.3523 (0.0% err) |
| C | 2 | ok | 32.27 (1.1% err) | 27.11 (2.9% err) | 0.3523 (0.0% err) |

### C structure per rep

| rep | status | turns | DB (agent 1) | DT config | DT script | DES run | ids named | values recovered |
|---|---|---|---|---|---|---|---|---|
| 0 | ok | 1 | answered 2801c / DDL (not JSON → stage unavailable) | 5069c / 0 ids | 13382c / 6 ids | ok, 3/3 KPIs | 3/3 | time 3/3, avail 3/3, bufs 3/3, arrival found |
| 1 | ok | 1 | answered 3138c / DDL (not JSON → stage unavailable) | 6099c / 3 ids | 11068c / 6 ids | ok, 3/3 KPIs | 3/3 | time 3/3, avail 0/3, bufs 3/3, arrival found, claimed: M1 a=99.55, M2 a=100, M3 a=100 |
| 2 | ok | 1 | answered 3925c / DDL (not JSON → stage unavailable) | 6095c / 6 ids | 11420c / 6 ids | ok, 3/3 KPIs | 3/3 | time 3/3, avail 3/3, bufs 3/3, arrival found |


- **C** rep0 notes: structural recovery only: 3/3 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) output was not JSON; raw text kept in artifacts/dtb_schema.json | DT stage (agent 2) ran: 5069 chars of twin config, 13382 chars of PyChrono script; 3/3 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it
- **C** rep1 notes: structural recovery only: 3/3 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) output was not JSON; raw text kept in artifacts/dtb_schema.json | DT stage (agent 2) ran: 6099 chars of twin config, 11068 chars of PyChrono script; 3/3 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it
- **C** rep2 notes: structural recovery only: 3/3 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) output was not JSON; raw text kept in artifacts/dtb_schema.json | DT stage (agent 2) ran: 6095 chars of twin config, 11420 chars of PyChrono script; 3/3 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it

## Case case_0003_starved_six_line

Truth: throughput=11.990833 parts/h, WIP=5.25071 parts, energy=2.353658 kWh/part (std: 0.037975/0.303141/0.003344)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| C | 0 | ok | 12 (0.1% err) | 6.71 (27.8% err) | 2.338 (0.6% err) |
| C | 1 | ok | 12 (0.1% err) | 6.71 (27.8% err) | 2.338 (0.6% err) |
| C | 2 | ok | 12.01 (0.2% err) | 5.23 (0.4% err) | 2.35 (0.2% err) |

### C structure per rep

| rep | status | turns | DB (agent 1) | DT config | DT script | DES run | ids named | values recovered |
|---|---|---|---|---|---|---|---|---|
| 0 | ok | 1 | answered 4394c / DDL (not JSON → stage unavailable) | 6895c / 0 ids | 10119c / 12 ids | ok, 3/3 KPIs | 6/6 | time 6/6, avail 6/6, bufs 6/6, arrival found |
| 1 | ok | 1 | answered 4129c / DDL (not JSON → stage unavailable) | 7660c / 5 ids | 12113c / 6 ids | ok, 3/3 KPIs | 6/6 | time 6/6, avail 6/6, bufs 6/6, arrival found |
| 2 | ok | 1 | answered 3117c / DDL (not JSON → stage unavailable) | 5319c / 4 ids | 8992c / 12 ids | ok, 3/3 KPIs | 6/6 | time 6/6, avail 0/6, bufs 6/6, arrival found, claimed: M1 a=0.9877, M2 a=0.9863, M3 a=0.9978, M4 a=0.9885, M5 a=0.9951, M6 a=0.9898 |


- **C** rep0 notes: structural recovery only: 6/6 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) output was not JSON; raw text kept in artifacts/dtb_schema.json | DT stage (agent 2) ran: 6895 chars of twin config, 10119 chars of PyChrono script; 6/6 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it
- **C** rep1 notes: structural recovery only: 6/6 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) output was not JSON; raw text kept in artifacts/dtb_schema.json | DT stage (agent 2) ran: 7660 chars of twin config, 12113 chars of PyChrono script; 6/6 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it
- **C** rep2 notes: structural recovery only: 6/6 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) output was not JSON; raw text kept in artifacts/dtb_schema.json | DT stage (agent 2) ran: 5319 chars of twin config, 8992 chars of PyChrono script; 6/6 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it

## Case case_0004_failure_heavy_line

Truth: throughput=22.400833 parts/h, WIP=7.28912 parts, energy=0.873547 kWh/part (std: 0.819642/0.855812/0.003851)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| C | 0 | ok | 21.75 (2.9% err) | 7.99 (9.6% err) | 0.8754 (0.2% err) |
| C | 1 | ok | 17.92 (20.0% err) | 12.31 (68.8% err) | 0.8911 (2.0% err) |
| C | 2 | ok | 21.75 (2.9% err) | 7.99 (9.6% err) | 0.8754 (0.2% err) |

### C structure per rep

| rep | status | turns | DB (agent 1) | DT config | DT script | DES run | ids named | values recovered |
|---|---|---|---|---|---|---|---|---|
| 0 | ok | 1 | answered 3483c / DDL (not JSON → stage unavailable) | 6509c / 0 ids | 13253c / 10 ids | ok, 3/3 KPIs | 5/5 | time 5/5, avail 0/5, bufs 5/5, arrival found, claimed: M1 a=92.58, M2 a=97.36, M3 a=94.69, M4 a=100, M5 a=98.23 |
| 1 | ok (6 sub / 5 ans) | 1 | timeout 600s | 7477c / 10 ids | 10454c / 10 ids | ok, 3/3 KPIs | 5/5 | time 5/5, avail 5/5, bufs 5/5, arrival found |
| 2 | ok | 1 | answered 4056c / DDL (not JSON → stage unavailable) | 5239c / 4 ids | 14316c / 10 ids | ok, 3/3 KPIs | 5/5 | time 5/5, avail 0/5, bufs 5/5, arrival found, claimed: M1 a=92.58, M2 a=97.36, M3 a=94.69, M4 a=100, M5 a=98.23 |


- **C** rep0 notes: structural recovery only: 5/5 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) output was not JSON; raw text kept in artifacts/dtb_schema.json | DT stage (agent 2) ran: 6509 chars of twin config, 13253 chars of PyChrono script; 5/5 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it
- **C** rep1 notes: structural recovery only: 5/5 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) failed: poll timeout after 600.0s — requirements recovered, schema stage unavailable | DT stage (agent 2) ran: 7477 chars of twin config, 10454 chars of PyChrono script; 5/5 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it | DT stage ran with an unavailable DB schema: the DB stage is one of agent 2's two inputs, so its output here is conditioned on a degraded input (recorded, not substituted with a fabricated schema)
- **C** rep2 notes: structural recovery only: 5/5 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) output was not JSON; raw text kept in artifacts/dtb_schema.json | DT stage (agent 2) ran: 5239 chars of twin config, 14316 chars of PyChrono script; 5/5 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it

## Case case_0005_high_rate_line

Truth: throughput=44.990833 parts/h, WIP=38.88238 parts, energy=0.335373 kWh/part (std: 0.035015/0.094204/9.9e-05)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| C | 0 | ok | 45 (0.0% err) | 38.62 (0.7% err) | 0.3354 (0.0% err) |
| C | 1 | ok | 44.59 (0.9% err) | 39.26 (1.0% err) | 0.3353 (0.0% err) |
| C | 2 | timeout | — | — | — |

### C structure per rep

| rep | status | turns | DB (agent 1) | DT config | DT script | DES run | ids named | values recovered |
|---|---|---|---|---|---|---|---|---|
| 0 | ok | 1 | answered 2483c / DDL (not JSON → stage unavailable) | 4548c / 3 ids | 11188c / 8 ids | ok, 3/3 KPIs | 4/4 | time 4/4, avail 0/4, bufs 4/4, arrival found, claimed: M1 a=99.99, M2 a=100, M3 a=99.88, M4 a=99.995 |
| 1 | ok | 1 | answered 3488c / DDL (not JSON → stage unavailable) | 6200c / 0 ids | 10482c / 8 ids | ok, 3/3 KPIs | 4/4 | time 4/4, avail 4/4, bufs 4/4, arrival found |
| 2 | timeout | 1 | answered 2338c / DDL (not JSON → stage unavailable) | 6494c / 0 ids | 11530c / 8 ids | no model | 4/4 | time 4/4, avail 4/4, bufs 4/4, arrival found |

- **C** rep2: 

- **C** rep0 notes: structural recovery only: 4/4 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) output was not JSON; raw text kept in artifacts/dtb_schema.json | DT stage (agent 2) ran: 4548 chars of twin config, 11188 chars of PyChrono script; 4/4 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it
- **C** rep1 notes: structural recovery only: 4/4 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) output was not JSON; raw text kept in artifacts/dtb_schema.json | DT stage (agent 2) ran: 6200 chars of twin config, 10482 chars of PyChrono script; 4/4 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it
- **C** rep2 notes: status `timeout`: a stage's task poll timed out — the pipeline itself completed, so this is the stage outcome, not an adapter failure | structural recovery only: 4/4 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) output was not JSON; raw text kept in artifacts/dtb_schema.json | DT stage (agent 2) ran: 6494 chars of twin config, 11530 chars of PyChrono script; 4/4 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it | DT stage (agent 2): DT agent (agent 2) partial: des: poll timeout after 900.0s

## Aggregated headline error (median MAPE over cases)

| Method | median MAPE (throughput/WIP/energy) |
|---|---|
| C | 1.5% (n=5 cases) |

_Paired non-parametric tests (Friedman/Wilcoxon) apply once >=5 cases exist; skipped here._