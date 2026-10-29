# Comparison report — `20260917_154052`
- mode: real | methods: ['C'] | repetitions: 1

## Validity

| Method | ok | generation_error | simulation_error | timeout | parse_error | total |
|---|---|---|---|---|---|---|
| C | 1 | 0 | 0 | 0 | 0 | 1 |

## Case case_0001_serial_line

Truth: throughput=19.868056 parts/h, WIP=40.386633 parts, energy=0.989219 kWh/part (std: 0.195889/0.253178/0.001198)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| C | 0 | ok | — | — | — |

- **C** recovered machine count: 5/5
- **C** parameter recovery: process time 0/5, availability 0/5, buffers 5/5, arrival rate found, 4 interview turn(s) / 6 agent tasks
- **C** DB stage (agent 1): unavailable — DB agent (agent 1) failed: poll timeout after 600.0s — requirements recovered, schema stage unavailable
- **C** DT stage (agent 2): ok — 7296 chars twin config, 11089 chars PyChrono script; 5/5 machine ids appear in that output (script captured, not executed); schema input unavailable
- **C** agent tasks: 7 submission(s) to the service, 6 answered
- **C** notes: structural recovery only: 5/5 machines mentioned in C's requirements | requirements document names the measured quantities but carries no parameter values (C's requirements stage records sensor kinds only) | DB stage (agent 1) not recovered — DB agent (agent 1) failed: poll timeout after 600.0s — requirements recovered, schema stage unavailable | DT stage (agent 2) ran: 7296 chars of twin config, 11089 chars of PyChrono script; 5/5 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it | DT stage ran with an unavailable DB schema: the DB stage is one of agent 2's two inputs, so its output here is conditioned on a degraded input (recorded, not substituted with a fabricated schema)

_no comparable KPIs_
