# Comparison report — `20260908_223442`
- mode: real | methods: ['A', 'B'] | repetitions: 1

## Validity

| Method | ok | generation_error | simulation_error | timeout | parse_error | total |
|---|---|---|---|---|---|---|
| A | 1 | 0 | 0 | 0 | 0 | 1 |
| B | 1 | 0 | 0 | 0 | 0 | 1 |

## Case case_0001_serial_line

Truth: throughput=19.868056 parts/h, WIP=40.386633 parts, energy=0.989219 kWh/part (std: 0.195889/0.253178/0.001198)

### Headline indicators vs truth

| Method | rep | status | Throughput (parts/h) | WIP (parts) | Energy per part (kWh) |
|---|--|--|---|---|---|
| A | 0 | ok | 19.91 (0.2% err) | — | — |
| B | 0 | ok | 18.05 (9.2% err) | 34.58 (14.4% err) | 0.8052 (18.6% err) |

- **A** utilisation APE (mean over ok reps, 5/5 machines matched): `0.8%`
- **A** recovered machine count: 5/5
