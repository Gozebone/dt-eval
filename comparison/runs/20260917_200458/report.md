# Comparison report — `20260917_200458`
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

- **C** recovered machine count: 0/5
- **C** notes: structural recovery only: 0/5 machines mentioned in C's requirements | DT stage (agent 2) ran: 0 chars of twin config, 8828 chars of PyChrono script; 0/5 machine ids appear in that output. The script is not executed (PyChrono is not installed on the harness host and models rigid bodies, not the case's discrete-event semantics), so no KPI is derived from it | DT stage (agent 2): DT agent (agent 2) partial: config: poll timeout after 900.0s

_no comparable KPIs_
