# Comparison report — `20260918_031215`
- mode: real | methods: ['C'] | repetitions: 3

## Validity

| Method | ok | generation_error | simulation_error | timeout | parse_error | total |
|---|---|---|---|---|---|---|
| C | 2 | 1 | 0 | 0 | 0 | 3 |

## Case case_0001_serial_line

Truth: throughput=19.868056 parts/h, WIP=40.386633 parts, energy=0.989219 kWh/part (std: 0.195889/0.253178/0.001198)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| C | 0 | ok | — | — | — |
| C | 1 | generation_error | — | — | — |
| C | 2 | ok | — | — | — |

### C structure per rep

| rep | status | turns | DB (agent 1) | DT config | DT script | ids named | values recovered |
|---|---|---|---|---|---|---|---|
| 0 | ok (10 sub / 8 ans) | 6 | timeout 600s | timeout 900s | 14697c / 7 ids | 5/5 | time 5/5, avail 5/5, bufs 5/5, arrival found |
| 1 | generation_error | — | — | — | — | —/— | — |
| 2 | ok (7 sub / 6 ans) | 3 | timeout 600s | 9497c / 10 ids | 11593c / 10 ids | 5/5 | time 0/5, avail 0/5, bufs 5/5, arrival missing |

- **C** rep1: RuntimeError: interview failed: agent task failed: Processing error: ("Connection broken: ConnectionResetError(104, 'Connection reset by peer')", ConnectionResetError(104, 'Connection reset by peer'))

- **C** rep0 notes: structural recovery only: 5/5 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) failed: poll timeout after 600.0s — requirements recovered, schema stage unavailable | DT stage (agent 2) ran: 0 chars of twin config, 14697 chars of PyChrono script; 5/5 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it | DT stage (agent 2): DT agent (agent 2) partial: config: poll timeout after 900.0s | DT stage ran with an unavailable DB schema: the DB stage is one of agent 2's two inputs, so its output here is conditioned on a degraded input (recorded, not substituted with a fabricated schema)
- **C** rep1 notes: Method C could not be driven; no structure recovered
- **C** rep2 notes: structural recovery only: 5/5 machines mentioned in C's requirements | requirements document names the measured quantities but carries no parameter values (C's requirements stage records sensor kinds only) | DB stage (agent 1) not recovered — DB agent (agent 1) failed: poll timeout after 600.0s — requirements recovered, schema stage unavailable | DT stage (agent 2) ran: 9497 chars of twin config, 11593 chars of PyChrono script; 5/5 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it | DT stage ran with an unavailable DB schema: the DB stage is one of agent 2's two inputs, so its output here is conditioned on a degraded input (recorded, not substituted with a fabricated schema)

_no comparable KPIs_
