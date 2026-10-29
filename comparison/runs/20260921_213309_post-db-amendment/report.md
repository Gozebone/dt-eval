# Comparison report — `20260921_213309_post-db-amendment`
- mode: real | methods: ['C'] | repetitions: 3

## Validity

| Method | ok | generation_error | timeout | total |
|---|---|---|---|---|
| C | 12 | 2 | 1 | 15 |

## Case case_0001_serial_line

Truth: throughput=19.868056 parts/h, WIP=40.386633 parts, energy=0.989219 kWh/part (std: 0.195889/0.253178/0.001198)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| C | 0 | ok | 19.7 (0.9% err) | 40.08 (0.8% err) | 0.9892 (0.0% err) |
| C | 1 | generation_error | — | — | — |
| C | 2 | ok | 19.17 (3.5% err) | 40.07 (0.8% err) | 0.9887 (0.0% err) |

### C structure per rep

| rep | status | turns | DB (agent 1) | DT config | DT script | DES run | ids named | values recovered |
|---|---|---|---|---|---|---|---|---|
| 0 | ok | 1 | answered 3098c / DDL (8 tables) | 6088c / 0 ids | 9747c / 10 ids | ok, 3/3 KPIs | 5/5 | time 5/5, avail 0/5, bufs 5/5, arrival found, claimed: M1 a=99.45, M2 a=96.86, M3 a=99.03, M4 a=97.39, M5 a=99.56 |
| 1 | generation_error | — | — | — | — | — | —/— | — |
| 2 | ok | 1 | answered 2454c / DDL (8 tables, 3 views) | 6685c / 0 ids | 10348c / 10 ids | ok, 3/3 KPIs | 5/5 | time 5/5, avail 5/5, bufs 5/5, arrival found |

- **C** rep1: RuntimeError: interview failed: agent returned non-JSON after 3 attempts: <think>
Okay, let's see. The user wants to create a digital twin for their manufacturing line. They provided detailed info about the production line structure, machines, buffers, and even a JSON with all the parameters. 

Firs

- **C** rep0 notes: structural recovery only: 5/5 machines mentioned in C's requirements | DT stage (agent 2) ran: 6088 chars of twin config, 9747 chars of PyChrono script; 5/5 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it
- **C** rep1 notes: Method C could not be driven; no structure recovered
- **C** rep2 notes: structural recovery only: 5/5 machines mentioned in C's requirements | DT stage (agent 2) ran: 6685 chars of twin config, 10348 chars of PyChrono script; 5/5 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it

## Case case_0002_saturated_short_line

Truth: throughput=32.62 parts/h, WIP=27.91672 parts, energy=0.352459 kWh/part (std: 0.118712/0.058013/8.6e-05)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| C | 0 | ok | 32.27 (1.1% err) | 27.11 (2.9% err) | 0.3523 (0.0% err) |
| C | 1 | generation_error | — | — | — |
| C | 2 | ok | 32.27 (1.1% err) | 27.11 (2.9% err) | 0.3523 (0.0% err) |

### C structure per rep

| rep | status | turns | DB (agent 1) | DT config | DT script | DES run | ids named | values recovered |
|---|---|---|---|---|---|---|---|---|
| 0 | ok | 1 | answered 2413c / DDL (8 tables) | 6083c / 0 ids | 9202c / 6 ids | ok, 3/3 KPIs | 3/3 | time 3/3, avail 3/3, bufs 3/3, arrival found |
| 1 | generation_error | 1 | answered 2306c / DDL (8 tables) | 6239c / 0 ids | 12804c / 6 ids | no model | 3/3 | time 3/3, avail 0/3, bufs 3/3, arrival found, claimed: M1 a=100, M2 a=99, M3 a=100 |
| 2 | ok | 1 | answered 2844c / DDL (7 tables, 2 views) | 5756c / 1 ids | 11176c / 6 ids | ok, 3/3 KPIs | 3/3 | time 3/3, avail 3/3, bufs 3/3, arrival found |

- **C** rep1: 

- **C** rep0 notes: structural recovery only: 3/3 machines mentioned in C's requirements | DT stage (agent 2) ran: 6083 chars of twin config, 9202 chars of PyChrono script; 3/3 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it
- **C** rep1 notes: status `generation_error`: the DT agent produced no DES model — the pipeline itself completed, so this is the stage outcome, not an adapter failure | structural recovery only: 3/3 machines mentioned in C's requirements | DT stage (agent 2) ran: 6239 chars of twin config, 12804 chars of PyChrono script; 3/3 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it | DT stage (agent 2): DT agent (agent 2) partial: des: agent task failed: Processing error: OpenRouter request failed: HTTP 403: { "success": false, "error": "Access denied by security policy." }
- **C** rep2 notes: structural recovery only: 3/3 machines mentioned in C's requirements | DT stage (agent 2) ran: 5756 chars of twin config, 11176 chars of PyChrono script; 3/3 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it

## Case case_0003_starved_six_line

Truth: throughput=11.990833 parts/h, WIP=5.25071 parts, energy=2.353658 kWh/part (std: 0.037975/0.303141/0.003344)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| C | 0 | ok | 12 (0.1% err) | 6.71 (27.8% err) | 2.338 (0.6% err) |
| C | 1 | ok | 12.01 (0.2% err) | 5.23 (0.4% err) | 2.347 (0.3% err) |
| C | 2 | ok | 12 (0.1% err) | 6.71 (27.8% err) | 2.338 (0.6% err) |

### C structure per rep

| rep | status | turns | DB (agent 1) | DT config | DT script | DES run | ids named | values recovered |
|---|---|---|---|---|---|---|---|---|
| 0 | ok | 1 | answered 3927c / DDL (7 tables) | 4837c / 0 ids | 10073c / 12 ids | ok, 3/3 KPIs | 6/6 | time 6/6, avail 6/6, bufs 6/6, arrival found |
| 1 | ok | 1 | answered 2734c / DDL (8 tables, 2 views) | 5702c / 0 ids | 12737c / 12 ids | ok, 3/3 KPIs | 6/6 | time 6/6, avail 0/6, bufs 6/6, arrival found, claimed: M1 a=98.77, M2 a=98.63, M3 a=99.78, M4 a=98.85, M5 a=99.51, M6 a=98.98 |
| 2 | ok | 1 | answered 3250c / DDL (7 tables) | 5924c / 0 ids | 13087c / 12 ids | ok, 3/3 KPIs | 6/6 | time 6/6, avail 6/6, bufs 6/6, arrival found |


- **C** rep0 notes: structural recovery only: 6/6 machines mentioned in C's requirements | DT stage (agent 2) ran: 4837 chars of twin config, 10073 chars of PyChrono script; 6/6 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it
- **C** rep1 notes: structural recovery only: 6/6 machines mentioned in C's requirements | DT stage (agent 2) ran: 5702 chars of twin config, 12737 chars of PyChrono script; 6/6 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it
- **C** rep2 notes: structural recovery only: 6/6 machines mentioned in C's requirements | DT stage (agent 2) ran: 5924 chars of twin config, 13087 chars of PyChrono script; 6/6 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it

## Case case_0004_failure_heavy_line

Truth: throughput=22.400833 parts/h, WIP=7.28912 parts, energy=0.873547 kWh/part (std: 0.819642/0.855812/0.003851)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| C | 0 | ok | 21.82 (2.6% err) | 8.507 (16.7% err) | 0.8755 (0.2% err) |
| C | 1 | timeout | — | — | — |
| C | 2 | ok | 17.92 (20.0% err) | 12.31 (68.8% err) | 0.8911 (2.0% err) |

### C structure per rep

| rep | status | turns | DB (agent 1) | DT config | DT script | DES run | ids named | values recovered |
|---|---|---|---|---|---|---|---|---|
| 0 | ok | 1 | answered 2218c / DDL (8 tables) | 5655c / 0 ids | 10960c / 10 ids | ok, 3/3 KPIs | 5/5 | time 1/5, avail 0/5, bufs 5/5, arrival found, claimed: M2 t=130.16, M3 t=90.14, M4 t=140.19, M5 t=109.82, M1 a=92.58, M2 a=97.36, M3 a=94.69, M4 a=100, M5 a=98.23 |
| 1 | timeout | 1 | timeout 600s | no output | no output | no model | 5/5 | time 5/5, avail 5/5, bufs 5/5, arrival found |
| 2 | ok (5 sub / 3 ans) | 1 | answered 2765c / DDL (7 tables, 2 views) | no output | no output | ok, 3/3 KPIs | 5/5 | time 5/5, avail 5/5, bufs 5/5, arrival found |

- **C** rep1: 

- **C** rep0 notes: structural recovery only: 5/5 machines mentioned in C's requirements | DT stage (agent 2) ran: 5655 chars of twin config, 10960 chars of PyChrono script; 5/5 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it
- **C** rep1 notes: status `timeout`: a stage's task poll timed out — the pipeline itself completed, so this is the stage outcome, not an adapter failure | structural recovery only: 5/5 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) failed: poll timeout after 600.0s — requirements recovered, schema stage unavailable | DT stage (agent 2) ran: 0 chars of twin config, 0 chars of PyChrono script; 0/5 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it | DT stage (agent 2): DT agent (agent 2) produced no output for any slot: config: agent task failed: Processing error: OpenRouter request failed: HTTP 403: { "success": false, "error": "Access denied by security policy." }; sim: agent task failed: Processing error: OpenRouter request failed: HTTP 403: { "success": false, "error": "Access denied by security policy." }; des: agent task failed: Processing error: OpenRouter request failed: HTTP 403: { "success": false, "error": "Access denied by security policy." } | DT stage ran with an unavailable DB schema: the DB stage is one of agent 2's two inputs, so its output here is conditioned on a degraded input (recorded, not substituted with a fabricated schema)
- **C** rep2 notes: structural recovery only: 5/5 machines mentioned in C's requirements | DT stage (agent 2) ran: 0 chars of twin config, 0 chars of PyChrono script; 0/5 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it | DT stage (agent 2): DT agent (agent 2) partial: config: agent task failed: Processing error: OpenRouter request failed: HTTP 403: { "success": false, "error": "Access denied by security policy." }; sim: agent task failed: Processing error: OpenRouter request failed: HTTP 403: { "success": false, "error": "Access denied by security policy." }

## Case case_0005_high_rate_line

Truth: throughput=44.990833 parts/h, WIP=38.88238 parts, energy=0.335373 kWh/part (std: 0.035015/0.094204/9.9e-05)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| C | 0 | ok | 44.59 (0.9% err) | 39.26 (1.0% err) | 0.3353 (0.0% err) |
| C | 1 | ok | 44.59 (0.9% err) | 39.01 (0.3% err) | 0.3354 (0.0% err) |
| C | 2 | ok | 44.59 (0.9% err) | 39.05 (0.4% err) | 0.3355 (0.0% err) |

### C structure per rep

| rep | status | turns | DB (agent 1) | DT config | DT script | DES run | ids named | values recovered |
|---|---|---|---|---|---|---|---|---|
| 0 | ok | 1 | answered 3562c / DDL (8 tables) | 8018c / 0 ids | 9432c / 8 ids | ok, 3/3 KPIs | 4/4 | time 4/4, avail 4/4, bufs 4/4, arrival found |
| 1 | ok (6 sub / 5 ans) | 2 | answered 3317c / DDL (7 tables) | timeout 900s | 11895c / 8 ids | ok, 3/3 KPIs | 4/4 | time 4/4, avail 2/4, bufs 4/4, arrival found, claimed: M1 a=99.95, M4 a=99.95 |
| 2 | ok | 1 | answered 2262c / DDL (7 tables, 3 views) | 6047c / 5 ids | 12124c / 8 ids | ok, 3/3 KPIs | 4/4 | time 4/4, avail 2/4, bufs 4/4, arrival found, claimed: M1 a=99.99, M4 a=99.99 |


- **C** rep0 notes: structural recovery only: 4/4 machines mentioned in C's requirements | DT stage (agent 2) ran: 8018 chars of twin config, 9432 chars of PyChrono script; 4/4 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it
- **C** rep1 notes: structural recovery only: 4/4 machines mentioned in C's requirements | DT stage (agent 2) ran: 0 chars of twin config, 11895 chars of PyChrono script; 4/4 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it | DT stage (agent 2): DT agent (agent 2) partial: config: poll timeout after 900.0s
- **C** rep2 notes: structural recovery only: 4/4 machines mentioned in C's requirements | DT stage (agent 2) ran: 6047 chars of twin config, 12124 chars of PyChrono script; 4/4 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it

## Aggregated headline error (median MAPE over cases)

| Method | median MAPE (throughput/WIP/energy) |
|---|---|
| C | 1.3% (n=5 cases) |

_Paired non-parametric tests (Friedman/Wilcoxon) apply once >=5 cases exist; skipped here._