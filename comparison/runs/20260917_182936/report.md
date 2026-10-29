# Comparison report — `20260917_182936`
- mode: real | methods: ['A', 'B', 'C'] | repetitions: 1

## Validity

| Method | ok | generation_error | simulation_error | timeout | parse_error | total |
|---|---|---|---|---|---|---|
| A | 0 | 0 | 1 | 0 | 0 | 1 |
| B | 1 | 0 | 0 | 0 | 0 | 1 |
| C | 1 | 0 | 0 | 0 | 0 | 1 |

## Case case_0001_serial_line

Truth: throughput=19.868056 parts/h, WIP=40.386633 parts, energy=0.989219 kWh/part (std: 0.195889/0.253178/0.001198)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| A | 0 | simulation_error | — | — | — |
| B | 0 | ok | 23.79 (19.7% err) | 33.63 (16.7% err) | 0.5907 (40.3% err) |
| C | 0 | ok | — | — | — |

- **C** recovered machine count: 5/5
- **C** parameter recovery: process time 5/5, availability 5/5, buffers 5/5, arrival rate found, 2 interview turn(s) / 5 agent tasks
- **C** DB stage (agent 1): unavailable — DB agent (agent 1) failed: poll timeout after 600.0s — requirements recovered, schema stage unavailable
- **C** DT stage (agent 2): ok — 6215 chars twin config, 12918 chars PyChrono script; 5/5 machine ids appear in that output (script captured, not executed); schema input unavailable
- **C** agent tasks: 6 submission(s) to the service, 5 answered
- **C** notes: structural recovery only: 5/5 machines mentioned in C's requirements | DB stage (agent 1) not recovered — DB agent (agent 1) failed: poll timeout after 600.0s — requirements recovered, schema stage unavailable | DT stage (agent 2) ran: 6215 chars of twin config, 12918 chars of PyChrono script; 5/5 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it | DT stage ran with an unavailable DB schema: the DB stage is one of agent 2's two inputs, so its output here is conditioned on a degraded input (recorded, not substituted with a fabricated schema)
