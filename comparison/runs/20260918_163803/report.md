# Comparison report — `20260918_163803`
- mode: real | methods: ['B'] | repetitions: 3

## Validity

| Method | ok | generation_error | simulation_error | timeout | parse_error | total |
|---|---|---|---|---|---|---|
| B | 14 | 0 | 1 | 0 | 0 | 15 |

## Case case_0001_serial_line

Truth: throughput=19.868056 parts/h, WIP=40.386633 parts, energy=0.989219 kWh/part (std: 0.195889/0.253178/0.001198)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| B | 0 | ok | 15.77 (20.6% err) | 31.62 (21.7% err) | 0.6326 (36.1% err) |
| B | 1 | ok | 15.88 (20.1% err) | 7.6 (81.2% err) | 0.6307 (36.2% err) |
| B | 2 | ok | 15.96 (19.7% err) | 24.51 (39.3% err) | 0.6349 (35.8% err) |


## Case case_0002_saturated_short_line

Truth: throughput=32.62 parts/h, WIP=27.91672 parts, energy=0.352459 kWh/part (std: 0.118712/0.058013/8.6e-05)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| B | 0 | ok | 32.43 (0.6% err) | 28.98 (3.8% err) | 0.3672 (4.2% err) |
| B | 1 | ok | 40.28 (23.5% err) | 17 (39.1% err) | 0.2237 (36.5% err) |
| B | 2 | simulation_error | — | — | — |


## Case case_0003_starved_six_line

Truth: throughput=11.990833 parts/h, WIP=5.25071 parts, energy=2.353658 kWh/part (std: 0.037975/0.303141/0.003344)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| B | 0 | ok | 0 (100.0% err) | 31 (490.4% err) | 0 (100.0% err) |
| B | 1 | ok | 0 (100.0% err) | 66 (1157.0% err) | 0 (100.0% err) |
| B | 2 | ok | 10.23 (14.7% err) | 36.33 (591.9% err) | 2.031 (13.7% err) |


## Case case_0004_failure_heavy_line

Truth: throughput=22.400833 parts/h, WIP=7.28912 parts, energy=0.873547 kWh/part (std: 0.819642/0.855812/0.003851)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| B | 0 | ok | 16.8 (25.0% err) | 12.78 (75.3% err) | 0.7468 (14.5% err) |
| B | 1 | ok | 20.1 (10.3% err) | 7.66 (5.1% err) | 0.5316 (39.1% err) |
| B | 2 | ok | 16.87 (24.7% err) | 12.87 (76.6% err) | 0.7476 (14.4% err) |


## Case case_0005_high_rate_line

Truth: throughput=44.990833 parts/h, WIP=38.88238 parts, energy=0.335373 kWh/part (std: 0.035015/0.094204/9.9e-05)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| B | 0 | ok | 31.59 (29.8% err) | 34.46 (11.4% err) | 0.3665 (9.3% err) |
| B | 1 | ok | 0 (100.0% err) | 24 (38.3% err) | 0 (100.0% err) |
| B | 2 | ok | 44.44 (1.2% err) | 12.93 (66.7% err) | 0.2597 (22.6% err) |


## Aggregated headline error (median MAPE over cases)

| Method | median MAPE (throughput/WIP/energy) |
|---|---|
| B | 31.6% (n=5 cases) |

_Paired non-parametric tests (Friedman/Wilcoxon) apply once >=5 cases exist; skipped here._