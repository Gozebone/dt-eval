# Comparison report — `20260918_165627`
- mode: real | methods: ['C'] | repetitions: 3

## Validity

| Method | ok | generation_error | simulation_error | timeout | parse_error | total |
|---|---|---|---|---|---|---|
| C | 13 | 2 | 0 | 0 | 0 | 15 |

## Case case_0001_serial_line

Truth: throughput=19.868056 parts/h, WIP=40.386633 parts, energy=0.989219 kWh/part (std: 0.195889/0.253178/0.001198)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| C | 0 | ok | — | — | — |
| C | 1 | ok | — | — | — |
| C | 2 | generation_error | — | — | — |

### C structure per rep

| rep | status | turns | DB (agent 1) | DT config | DT script | ids named | values recovered |
|---|---|---|---|---|---|---|---|
| 0 | ok (5 sub / 4 ans) | 2 | timeout 600s | 6284c / 5 ids | 6235c / 10 ids | 5/5 | time 0/5, avail 0/5, bufs 5/5, arrival found |
| 1 | ok (5 sub / 3 ans) | 2 | timeout 600s | 6053c / 3 ids | no output | 5/5 | time 0/5, avail 0/5, bufs 5/5, arrival found |
| 2 | generation_error | — | — | — | — | —/— | — |

- **C** rep2: RuntimeError: interview failed: poll timeout after 600.0s

- **C** rep0 notes: structural recovery only: 5/5 machines mentioned in C's requirements | requirements document names the measured quantities but carries no parameter values (C's requirements stage records sensor kinds only) | DB stage (agent 1) not recovered — DB agent (agent 1) failed: poll timeout after 600.0s — requirements recovered, schema stage unavailable | DT stage (agent 2) ran: 6284 chars of twin config, 6235 chars of PyChrono script; 5/5 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it | DT stage ran with an unavailable DB schema: the DB stage is one of agent 2's two inputs, so its output here is conditioned on a degraded input (recorded, not substituted with a fabricated schema)
- **C** rep1 notes: structural recovery only: 5/5 machines mentioned in C's requirements | requirements document names the measured quantities but carries no parameter values (C's requirements stage records sensor kinds only) | DB stage (agent 1) not recovered — DB agent (agent 1) failed: poll timeout after 600.0s — requirements recovered, schema stage unavailable | DT stage (agent 2) ran: 6053 chars of twin config, 0 chars of PyChrono script; 2/5 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it | DT stage (agent 2): DT agent (agent 2) partial: sim: agent task failed: Processing error: OpenRouter request failed after 4 attempts: empty content (finish_reason=stop, provider=Novita, completion_tokens=1899) | DT stage ran with an unavailable DB schema: the DB stage is one of agent 2's two inputs, so its output here is conditioned on a degraded input (recorded, not substituted with a fabricated schema)
- **C** rep2 notes: Method C could not be driven; no structure recovered

_no comparable KPIs_

## Case case_0002_saturated_short_line

Truth: throughput=32.62 parts/h, WIP=27.91672 parts, energy=0.352459 kWh/part (std: 0.118712/0.058013/8.6e-05)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| C | 0 | ok | — | — | — |
| C | 1 | generation_error | — | — | — |
| C | 2 | ok | — | — | — |

### C structure per rep

| rep | status | turns | DB (agent 1) | DT config | DT script | ids named | values recovered |
|---|---|---|---|---|---|---|---|
| 0 | ok (5 sub / 4 ans) | 2 | timeout 600s | 8398c / 3 ids | 11730c / 3 ids | 3/3 | time 0/3, avail 0/3, bufs 0/3, arrival missing |
| 1 | generation_error | — | — | — | — | —/— | — |
| 2 | ok (5 sub / 4 ans) | 2 | timeout 600s | 9044c / 0 ids | 12336c / 6 ids | 3/3 | time 0/3, avail 0/3, bufs 3/3, arrival found |

- **C** rep1: RuntimeError: interview failed: poll timeout after 600.0s

- **C** rep0 notes: structural recovery only: 3/3 machines mentioned in C's requirements | requirements document names the measured quantities but carries no parameter values (C's requirements stage records sensor kinds only) | DB stage (agent 1) not recovered — DB agent (agent 1) failed: poll timeout after 600.0s — requirements recovered, schema stage unavailable | DT stage (agent 2) ran: 8398 chars of twin config, 11730 chars of PyChrono script; 3/3 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it | DT stage ran with an unavailable DB schema: the DB stage is one of agent 2's two inputs, so its output here is conditioned on a degraded input (recorded, not substituted with a fabricated schema)
- **C** rep1 notes: Method C could not be driven; no structure recovered
- **C** rep2 notes: structural recovery only: 3/3 machines mentioned in C's requirements | requirements document names the measured quantities but carries no parameter values (C's requirements stage records sensor kinds only) | DB stage (agent 1) not recovered — DB agent (agent 1) failed: poll timeout after 600.0s — requirements recovered, schema stage unavailable | DT stage (agent 2) ran: 9044 chars of twin config, 12336 chars of PyChrono script; 3/3 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it | DT stage ran with an unavailable DB schema: the DB stage is one of agent 2's two inputs, so its output here is conditioned on a degraded input (recorded, not substituted with a fabricated schema)

_no comparable KPIs_

## Case case_0003_starved_six_line

Truth: throughput=11.990833 parts/h, WIP=5.25071 parts, energy=2.353658 kWh/part (std: 0.037975/0.303141/0.003344)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| C | 0 | ok | — | — | — |
| C | 1 | ok | — | — | — |
| C | 2 | ok | — | — | — |

### C structure per rep

| rep | status | turns | DB (agent 1) | DT config | DT script | ids named | values recovered |
|---|---|---|---|---|---|---|---|
| 0 | ok (6 sub / 5 ans) | 2 | timeout 600s | 4827c / 6 ids | 8060c / 6 ids | 6/6 | time 6/6, avail 6/6, bufs 0/6, arrival missing |
| 1 | ok (6 sub / 5 ans) | 3 | timeout 600s | 6655c / 5 ids | 11691c / 6 ids | 6/6 | time 0/6, avail 0/6, bufs 0/6, arrival missing |
| 2 | ok (5 sub / 4 ans) | 2 | timeout 600s | 7180c / 0 ids | 9990c / 6 ids | 6/6 | time 6/6, avail 4/6, bufs 6/6, arrival found |


- **C** rep0 notes: structural recovery only: 6/6 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) failed: poll timeout after 600.0s — requirements recovered, schema stage unavailable | DT stage (agent 2) ran: 4827 chars of twin config, 8060 chars of PyChrono script; 6/6 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it | DT stage ran with an unavailable DB schema: the DB stage is one of agent 2's two inputs, so its output here is conditioned on a degraded input (recorded, not substituted with a fabricated schema)
- **C** rep1 notes: structural recovery only: 6/6 machines mentioned in C's requirements | requirements document names the measured quantities but carries no parameter values (C's requirements stage records sensor kinds only) | DB stage (agent 1) not recovered — DB agent (agent 1) failed: poll timeout after 600.0s — requirements recovered, schema stage unavailable | DT stage (agent 2) ran: 6655 chars of twin config, 11691 chars of PyChrono script; 6/6 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it | DT stage ran with an unavailable DB schema: the DB stage is one of agent 2's two inputs, so its output here is conditioned on a degraded input (recorded, not substituted with a fabricated schema)
- **C** rep2 notes: structural recovery only: 6/6 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) failed: poll timeout after 600.0s — requirements recovered, schema stage unavailable | DT stage (agent 2) ran: 7180 chars of twin config, 9990 chars of PyChrono script; 6/6 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it | DT stage ran with an unavailable DB schema: the DB stage is one of agent 2's two inputs, so its output here is conditioned on a degraded input (recorded, not substituted with a fabricated schema)

_no comparable KPIs_

## Case case_0004_failure_heavy_line

Truth: throughput=22.400833 parts/h, WIP=7.28912 parts, energy=0.873547 kWh/part (std: 0.819642/0.855812/0.003851)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| C | 0 | ok | — | — | — |
| C | 1 | ok | — | — | — |
| C | 2 | ok | — | — | — |

### C structure per rep

| rep | status | turns | DB (agent 1) | DT config | DT script | ids named | values recovered |
|---|---|---|---|---|---|---|---|
| 0 | ok (5 sub / 3 ans) | 2 | timeout 600s | 6079c / 0 ids | timeout 900s | 5/5 | time 1/5, avail 0/5, bufs 0/5, arrival found |
| 1 | ok (5 sub / 4 ans) | 2 | timeout 600s | 5749c / 10 ids | 8133c / 7 ids | 5/5 | time 5/5, avail 5/5, bufs 5/5, arrival found |
| 2 | ok (4 sub / 2 ans) | 1 | timeout 600s | timeout 900s | 5930c / 0 ids | 0/5 | time 0/5, avail 0/5, bufs 0/5, arrival missing |


- **C** rep0 notes: structural recovery only: 5/5 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) failed: poll timeout after 600.0s — requirements recovered, schema stage unavailable | DT stage (agent 2) ran: 6079 chars of twin config, 0 chars of PyChrono script; 0/5 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it | DT stage (agent 2): DT agent (agent 2) partial: sim: poll timeout after 900.0s | DT stage ran with an unavailable DB schema: the DB stage is one of agent 2's two inputs, so its output here is conditioned on a degraded input (recorded, not substituted with a fabricated schema)
- **C** rep1 notes: structural recovery only: 5/5 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) failed: poll timeout after 600.0s — requirements recovered, schema stage unavailable | DT stage (agent 2) ran: 5749 chars of twin config, 8133 chars of PyChrono script; 5/5 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it | DT stage ran with an unavailable DB schema: the DB stage is one of agent 2's two inputs, so its output here is conditioned on a degraded input (recorded, not substituted with a fabricated schema)
- **C** rep2 notes: structural recovery only: 0/5 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) failed: poll timeout after 600.0s — requirements recovered, schema stage unavailable | DT stage (agent 2) ran: 0 chars of twin config, 5930 chars of PyChrono script; 0/5 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it | DT stage (agent 2): DT agent (agent 2) partial: config: poll timeout after 900.0s | DT stage ran with an unavailable DB schema: the DB stage is one of agent 2's two inputs, so its output here is conditioned on a degraded input (recorded, not substituted with a fabricated schema)

_no comparable KPIs_

## Case case_0005_high_rate_line

Truth: throughput=44.990833 parts/h, WIP=38.88238 parts, energy=0.335373 kWh/part (std: 0.035015/0.094204/9.9e-05)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| C | 0 | ok | — | — | — |
| C | 1 | ok | — | — | — |
| C | 2 | ok | — | — | — |

### C structure per rep

| rep | status | turns | DB (agent 1) | DT config | DT script | ids named | values recovered |
|---|---|---|---|---|---|---|---|
| 0 | ok (5 sub / 4 ans) | 2 | timeout 600s | 7346c / 8 ids | 9404c / 8 ids | 4/4 | time 0/4, avail 0/4, bufs 4/4, arrival missing |
| 1 | ok (5 sub / 4 ans) | 2 | timeout 600s | 6002c / 0 ids | 6470c / 8 ids | 4/4 | time 0/4, avail 0/4, bufs 4/4, arrival found |
| 2 | ok (5 sub / 4 ans) | 2 | answered 3218c / DDL (not JSON → stage unavailable) | 6430c / 0 ids | timeout 900s | 4/4 | time 1/4, avail 0/4, bufs 4/4, arrival found |


- **C** rep0 notes: structural recovery only: 4/4 machines mentioned in C's requirements | requirements document names the measured quantities but carries no parameter values (C's requirements stage records sensor kinds only) | DB stage (agent 1) not recovered — DB agent (agent 1) failed: poll timeout after 600.0s — requirements recovered, schema stage unavailable | DT stage (agent 2) ran: 7346 chars of twin config, 9404 chars of PyChrono script; 4/4 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it | DT stage ran with an unavailable DB schema: the DB stage is one of agent 2's two inputs, so its output here is conditioned on a degraded input (recorded, not substituted with a fabricated schema)
- **C** rep1 notes: structural recovery only: 4/4 machines mentioned in C's requirements | requirements document names the measured quantities but carries no parameter values (C's requirements stage records sensor kinds only) | DB stage (agent 1) not recovered — DB agent (agent 1) failed: poll timeout after 600.0s — requirements recovered, schema stage unavailable | DT stage (agent 2) ran: 6002 chars of twin config, 6470 chars of PyChrono script; 4/4 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it | DT stage ran with an unavailable DB schema: the DB stage is one of agent 2's two inputs, so its output here is conditioned on a degraded input (recorded, not substituted with a fabricated schema)
- **C** rep2 notes: structural recovery only: 4/4 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) output was not JSON; raw text kept in artifacts/dtb_schema.json | DT stage (agent 2) ran: 6430 chars of twin config, 0 chars of PyChrono script; 0/4 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it | DT stage (agent 2): DT agent (agent 2) partial: sim: poll timeout after 900.0s

_no comparable KPIs_

## Aggregated headline error (median MAPE over cases)

| Method | median MAPE (throughput/WIP/energy) |
|---|---|

_Paired non-parametric tests (Friedman/Wilcoxon) apply once >=5 cases exist; skipped here._