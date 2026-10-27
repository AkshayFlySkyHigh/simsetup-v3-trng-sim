# NIST SP 800-22 on bitstream_full.txt (simsetup_v3, 0.2088 ns, 300 K)

Runner: NIST STS 2.1.2 `assess` (compiled unmodified from the NIST source; input is the ready 0/1 stream). Defaults: block-frequency M = 128. alpha = 0.01. 1 sequence, n = 29929 bits (173x173 = 29929; 15105 ones / 14824 zeros with 1 = switched). Nothing adjusted.

## Results (raw p-values from stats.txt)
| Test | p (1 = switched) | p (1 = not switched) | Result at 0.01 |
|---|---|---|---|
| Frequency (monobit) | 0.104317 | 0.104317 | pass |
| Block Frequency (M=128, 233 blocks, 105 bits discarded) | 0.333688 | 0.333688 | pass |
| Cumulative Sums forward | 0.194247 | 0.194247 | pass |
| Cumulative Sums reverse | 0.146295 | 0.146295 | pass |
| Runs | 0.860674 | 0.860674 | pass |
| Longest Run of Ones (M=128, 233 blocks) | 0.042529 | 0.076060 | pass (both) |
| DFT (spectral) | 0.927094 | 0.927094 | pass |

Only Longest Run depends on which symbol is 1 (not complement-symmetric); the paper must state its convention. Main column = file as exported (1 = switched).

All 7 p-values (6 tests) pass. Caveat: single sequence, so STS prints proportion 1/1 and no uniformity p-value; pass/fail is simply p >= 0.01 per test.

## Not applicable at n = 29929 (below minimum length, not run)
Rank (needs >= 38912), Approximate Entropy (minimum 65536 for m=10), Non-overlapping Template, Overlapping Template, Linear Complexity, Serial (>= 1,000,000 recommended), Universal (>= 387,840), Random Excursions and Random Excursions Variant (>= 1,000,000).

## Files (nist/)
- `run_nist.sh` (runner; STS source from NIST, see README), `nist_input_1eq_switched.txt`, `nist_input_1eq_notswitched.txt` (inputs)
- `raw_A_1eq_switched/`, `raw_B_1eq_notswitched/` (STS output: finalAnalysisReport.txt + per-test stats.txt/results.txt)

Old v3 run (1999-bit file) is superseded.
