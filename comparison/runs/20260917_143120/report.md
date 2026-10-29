# Comparison report — `20260917_143120`
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
- **C** parameter recovery: process time 0/5, availability 0/5, buffers 0/5, arrival rate missing, 2 interview turn(s) / 4 agent tasks
- **C** notes: structural recovery only: 5/5 machines mentioned in C's requirements | requirements document names the measured quantities but carries no parameter values (C's requirements stage records sensor kinds only) | DB stage (agent 1) not recovered — DB agent (agent 1) failed: agent task failed: Processing error: CUDA error: no kernel image is available for execution on the device | DT agent (agent 2, PyChrono codegen) status=offline; not exercised

_no comparable KPIs_
