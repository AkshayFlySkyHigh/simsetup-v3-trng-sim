# Results tables

Source: synced simsetup_v3 results (synced 2026-10-12); coarse sweep from the first v3 sweep (2026-07-06); reversed polarity from the polarity runs (2026-08-12); threshold |m_z| 0.8; Psw all-runs = switched/all.

Uncertainty = plain binomial standard error sqrt(p(1-p)/N).

## 1. Coarse sweep (300 K, -0.1 mA)

| Pulse (ns) | N | switched | not | invalid | Psw all-runs (%) | Psw valid-only (%) |
|---|---|---|---|---|---|---|
| 0.190 | 100 | 23 | 70 | 7 | 23.00 ± 4.21 | 24.73 ± 4.47 |
| 0.195 | 500 | 137 | 339 | 24 | 27.40 ± 1.99 | 28.78 ± 2.08 |
| 0.200 | 500 | 159 | 310 | 31 | 31.80 ± 2.08 | 33.90 ± 2.19 |
| 0.205 | 500 | 212 | 256 | 32 | 42.40 ± 2.21 | 45.30 ± 2.30 |
| 0.210 | 500 | 247 | 227 | 26 | 49.40 ± 2.24 | 52.11 ± 2.29 |

## 2. Fine sweep (300 K, -0.1 mA)

| Pulse (ns) | N | switched | not | invalid | Psw all-runs (%) | Psw valid-only (%) |
|---|---|---|---|---|---|---|
| 0.2087 | 2000 | 987 | 1012 | 1 | 49.35 ± 1.12 | 49.37 ± 1.12 |
| 0.2088 | 30000 | 15118 | 14834 | 48 | 50.39 ± 0.29 | 50.47 ± 0.29 |
| 0.2090 | 2000 | 989 | 1011 | 0 | 49.45 ± 1.12 | 49.45 ± 1.12 |
| 0.2091 | 2000 | 990 | 1008 | 2 | 49.50 ± 1.12 | 49.55 ± 1.12 |
| 0.2092 | 2000 | 1017 | 970 | 13 | 50.85 ± 1.12 | 51.18 ± 1.12 |

## 3. Temperature (0.2088 ns, -0.1 mA)

| T (K) | N | switched | not | invalid | Psw all-runs (%) | Psw valid-only (%) |
|---|---|---|---|---|---|---|
| 298 | 2500 | 1226 | 1274 | 0 | 49.04 ± 1.00 | 49.04 ± 1.00 |
| 299 | 2500 | 1265 | 1234 | 1 | 50.60 ± 1.00 | 50.62 ± 1.00 |
| 300 | 30000 | 15118 | 14834 | 48 | 50.39 ± 0.29 | 50.47 ± 0.29 |
| 301 | 2500 | 1214 | 1225 | 61 | 48.56 ± 1.00 | 49.77 ± 1.01 |
| 302 | 2500 | 1261 | 1165 | 74 | 50.44 ± 1.00 | 51.98 ± 1.01 |

## 4. Polarity (0.2088 ns, 300 K), equal N, 10 ns max time, invalid runs excluded

Reversed runs used a 10 ns max time, so forward runs are classified by m_z at t = 10 ns (last sample if the run stopped earlier), threshold 0.8. Equal sample: reversed has 1422 valid runs, so the forward row uses the first 1422 valid forward runs in seed order (seeds 1 to 1527). No runs were chosen by outcome. Psw = switched / (switched + not switched). No error bars in the figure.

| Direction | N valid | switched | not | Psw valid-only (%) |
|---|---|---|---|---|
| Forward (-0.1 mA), first 1422 valid, classified at 10 ns | 1422 | 716 | 706 | 50.35 |
| Reversed (+0.1 mA), all valid | 1422 | 702 | 720 | 49.37 |

Reversed set: 1500 runs, 78 invalid. Under the earlier forward rule (final value at the end of the longer forward run) the forward row was 710 / 712 = 49.93%. The full 30000-run forward set (valid-only 50.47%, longer max time) is in section 5.

Polarity trace figure (paper_polarity_traces.png): first 200 runs in seed order from each polarity (seeds 1 to 200, any outcome), traces cut at 10 ns. Forward: 119 switched, 68 not, 13 invalid. Reversed: 91 switched, 101 not, 8 invalid.

## 5. 0.2088 ns / 300 K / -0.1 mA full set

| Quantity | Value |
|---|---|
| Runs | 30000 |
| Valid bits | 29952 |
| Invalid | 48 |
| Square side | 173 |
| Bits used | 29929 |
| Ones | 15105 |
| Zeros | 14824 |
| Ones (%) | 50.469 |
| max abs(S_n) | 287 |
| Final S_n | 281 |
| Last seed used | 29977 |
| Overlay Psw (%) | 50.39 ± 0.29 |
