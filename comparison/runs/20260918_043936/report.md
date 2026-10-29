# Comparison report — `20260918_043936`
- mode: real | methods: ['A', 'B'] | repetitions: 3

## Validity

| Method | ok | generation_error | simulation_error | timeout | parse_error | total |
|---|---|---|---|---|---|---|
| A | 4 | 3 | 8 | 0 | 0 | 15 |
| B | 10 | 5 | 0 | 0 | 0 | 15 |

## Case case_0001_serial_line

Truth: throughput=19.868056 parts/h, WIP=40.386633 parts, energy=0.989219 kWh/part (std: 0.195889/0.253178/0.001198)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| A | 0 | simulation_error | — | — | — |
| A | 1 | simulation_error | — | — | — |
| A | 2 | simulation_error | — | — | — |
| B | 0 | ok | 17.92 (9.8% err) | 11.53 (71.5% err) | 0.7943 (19.7% err) |
| B | 1 | ok | 18.18 (8.5% err) | 4.15 (89.7% err) | 0.6204 (37.3% err) |
| B | 2 | ok | 0 (100.0% err) | 57 (41.1% err) | 0 (100.0% err) |


## Case case_0002_saturated_short_line

Truth: throughput=32.62 parts/h, WIP=27.91672 parts, energy=0.352459 kWh/part (std: 0.118712/0.058013/8.6e-05)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| A | 0 | ok | 32.67 (0.2% err) | — | — |
| A | 1 | simulation_error | — | — | — |
| A | 2 | simulation_error | — | — | — |
| B | 0 | ok | 64.87 (98.9% err) | 9 (67.8% err) | 0.269 (23.7% err) |
| B | 1 | ok | 32.43 (0.6% err) | 24.48 (12.3% err) | 0.3672 (4.2% err) |
| B | 2 | ok | 32.43 (0.6% err) | 28.48 (2.0% err) | 0.3672 (4.2% err) |

- **A** utilisation APE (mean over ok reps, 3/3 machines matched): `0.3%`
- **A** recovered machine count: 3/3

## Case case_0003_starved_six_line

Truth: throughput=11.990833 parts/h, WIP=5.25071 parts, energy=2.353658 kWh/part (std: 0.037975/0.303141/0.003344)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| A | 0 | simulation_error | — | — | — |
| A | 1 | simulation_error | — | — | — |
| A | 2 | simulation_error | — | — | — |
| B | 0 | ok | 15.43 (28.7% err) | 53.7 (922.7% err) | 1.895 (19.5% err) |
| B | 1 | ok | 0 (100.0% err) | 56 (966.5% err) | 0 (100.0% err) |
| B | 2 | ok | 0 (100.0% err) | 21 (299.9% err) | 0 (100.0% err) |


## Case case_0004_failure_heavy_line

Truth: throughput=22.400833 parts/h, WIP=7.28912 parts, energy=0.873547 kWh/part (std: 0.819642/0.855812/0.003851)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| A | 0 | ok | 23.98 (7.0% err) | — | — |
| A | 1 | ok | 23.98 (7.0% err) | — | — |
| A | 2 | ok | 23.98 (7.0% err) | — | — |
| B | 0 | ok | 0 (100.0% err) | 14 (92.1% err) | 0 (100.0% err) |
| B | 1 | generation_error | — | — | — |
| B | 2 | generation_error | — | — | — |

- **A** utilisation APE (mean over ok reps, 5/5 machines matched): `7.1%`
- **A** recovered machine count: 5/5

## Case case_0005_high_rate_line

Truth: throughput=44.990833 parts/h, WIP=38.88238 parts, energy=0.335373 kWh/part (std: 0.035015/0.094204/9.9e-05)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| A | 0 | generation_error | — | — | — |
| A | 1 | generation_error | — | — | — |
| A | 2 | generation_error | — | — | — |
| B | 0 | generation_error | — | — | — |
| B | 1 | generation_error | — | — | — |
| B | 2 | generation_error | — | — | — |


_no comparable KPIs_

## Aggregated headline error (median MAPE over cases)

| Method | median MAPE (throughput/WIP/energy) |
|---|---|
| A | 3.6% (n=2 cases) |
| B | 71.3% (n=4 cases) |

_Paired non-parametric tests (Friedman/Wilcoxon) apply once >=5 cases exist; skipped here._