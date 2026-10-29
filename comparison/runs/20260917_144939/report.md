# Comparison report — `20260917_144939`
- mode: mock | methods: ['A', 'B', 'C'] | repetitions: 1

## Validity

| Method | ok | generation_error | simulation_error | timeout | parse_error | total |
|---|---|---|---|---|---|---|
| A | 1 | 0 | 0 | 0 | 0 | 1 |
| B | 1 | 0 | 0 | 0 | 0 | 1 |
| C | 1 | 0 | 0 | 0 | 0 | 1 |

## Case case_0001_serial_line

Truth: throughput=19.868056 parts/h, WIP=40.386633 parts, energy=0.989219 kWh/part (std: 0.195889/0.253178/0.001198)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| A | 0 | ok | 19.98 (0.5% err) | — | — |
| B | 0 | ok | 19.87 (0.0% err) | 40.39 (0.0% err) | 0.9892 (0.0% err) |
| C | 0 | ok | — | — | — |

- **A** utilisation APE (mean over ok reps, 5/5 machines matched): `0.9%`
- **A** recovered machine count: 5/5
- **C** recovered machine count: 5/5
- **C** parameter recovery: process time 5/5, availability 5/5, buffers 5/5, arrival rate found
- **C** notes: structural recovery only: 5/5 machines mentioned in C's requirements
