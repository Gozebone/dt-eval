# Comparison report — `20260918_024828`
- mode: real | methods: ['C'] | repetitions: 3

## Validity

| Method | ok | generation_error | simulation_error | timeout | parse_error | total |
|---|---|---|---|---|---|---|
| C | 3 | 0 | 0 | 0 | 0 | 3 |

## Case case_0001_serial_line

Truth: throughput=19.868056 parts/h, WIP=40.386633 parts, energy=0.989219 kWh/part (std: 0.195889/0.253178/0.001198)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| C | 0 | ok | — | — | — |
| C | 1 | ok | — | — | — |
| C | 2 | ok | — | — | — |

### C structure per rep

| rep | status | turns | DB (agent 1) | DT config | DT script | ids named | values recovered |
|---|---|---|---|---|---|---|---|
| 0 | ok (5 sub / 4 ans) | 2 | timeout 600s | 5314c / 0 ids | 12459c / 6 ids | 5/5 | time 0/5, avail 0/5, bufs 5/5, arrival missing |
| 1 | ok (4 sub / 3 ans) | 1 | answered 1979c / DDL (not JSON → stage unavailable) | timeout 900s | 9761c / 0 ids | 0/5 | time 0/5, avail 0/5, bufs 0/5, arrival missing |
| 2 | ok (5 sub / 4 ans) | 2 | timeout 600s | 8173c / 10 ids | 14097c / 7 ids | 5/5 | time 5/5, avail 5/5, bufs 5/5, arrival missing |


- **C** rep0 notes: structural recovery only: 5/5 machines mentioned in C's requirements | requirements document names the measured quantities but carries no parameter values (C's requirements stage records sensor kinds only) | DB stage (agent 1) not recovered — DB agent (agent 1) failed: poll timeout after 600.0s — requirements recovered, schema stage unavailable | DT stage (agent 2) ran: 5314 chars of twin config, 12459 chars of PyChrono script; 5/5 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it | DT stage ran with an unavailable DB schema: the DB stage is one of agent 2's two inputs, so its output here is conditioned on a degraded input (recorded, not substituted with a fabricated schema)
- **C** rep1 notes: structural recovery only: 0/5 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) output was not JSON; raw text kept in artifacts/dtb_schema.json | DT stage (agent 2) ran: 0 chars of twin config, 9761 chars of PyChrono script; 0/5 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it | DT stage (agent 2): DT agent (agent 2) partial: config: poll timeout after 900.0s
- **C** rep2 notes: structural recovery only: 5/5 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) failed: poll timeout after 600.0s — requirements recovered, schema stage unavailable | DT stage (agent 2) ran: 8173 chars of twin config, 14097 chars of PyChrono script; 5/5 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it | DT stage ran with an unavailable DB schema: the DB stage is one of agent 2's two inputs, so its output here is conditioned on a degraded input (recorded, not substituted with a fabricated schema)

_no comparable KPIs_
