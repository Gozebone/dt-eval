# Comparison report — `20260920_030210`
- mode: mock | methods: ['A', 'B', 'C'] | repetitions: 1

## Validity

| Method | ok | generation_error | total |
|---|---|---|---|
| A | 1 | 4 | 5 |
| B | 1 | 4 | 5 |
| C | 1 | 4 | 5 |
- case_0001_serial_line/C/rep0: recorded as `ok`; no stage evidence (mock or pre-stage native block)

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
### C structure per rep

| rep | status | turns | DB (agent 1) | DT config | DT script | DES run | ids named | values recovered |
|---|---|---|---|---|---|---|---|---|
| 0 | ok | 0 | not attempted | not attempted | not attempted | not attempted | 5/5 | time 0/5, avail 0/5, bufs 5/5, arrival found |


- **C** rep0 notes: structural recovery only: 5/5 machines mentioned in C's requirements | requirements document names the measured quantities but carries no parameter values (C's requirements stage records sensor kinds only)

## Case case_0002_saturated_short_line

Truth: throughput=32.62 parts/h, WIP=27.91672 parts, energy=0.352459 kWh/part (std: 0.118712/0.058013/8.6e-05)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| A | 0 | generation_error | — | — | — |
| B | 0 | generation_error | — | — | — |
| C | 0 | generation_error | — | — | — |

- **C** rep0 notes: Method C could not be driven; no structure recovered

_no comparable KPIs_

## Case case_0003_starved_six_line

Truth: throughput=11.990833 parts/h, WIP=5.25071 parts, energy=2.353658 kWh/part (std: 0.037975/0.303141/0.003344)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| A | 0 | generation_error | — | — | — |
| B | 0 | generation_error | — | — | — |
| C | 0 | generation_error | — | — | — |

- **C** rep0 notes: Method C could not be driven; no structure recovered

_no comparable KPIs_

## Case case_0004_failure_heavy_line

Truth: throughput=22.400833 parts/h, WIP=7.28912 parts, energy=0.873547 kWh/part (std: 0.819642/0.855812/0.003851)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| A | 0 | generation_error | — | — | — |
| B | 0 | generation_error | — | — | — |
| C | 0 | generation_error | — | — | — |

- **C** rep0 notes: Method C could not be driven; no structure recovered

_no comparable KPIs_

## Case case_0005_high_rate_line

Truth: throughput=44.990833 parts/h, WIP=38.88238 parts, energy=0.335373 kWh/part (std: 0.035015/0.094204/9.9e-05)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| A | 0 | generation_error | — | — | — |
| B | 0 | generation_error | — | — | — |
| C | 0 | generation_error | — | — | — |

- **C** rep0 notes: Method C could not be driven; no structure recovered

_no comparable KPIs_

## Aggregated headline error (median MAPE over cases)

| Method | median MAPE (throughput/WIP/energy) |
|---|---|
| A | 0.5% (n=1 cases) |
| B | 0.0% (n=1 cases) |

_Paired non-parametric tests (Friedman/Wilcoxon) apply once >=5 cases exist; skipped here._