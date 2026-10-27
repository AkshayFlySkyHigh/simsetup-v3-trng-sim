# Export the analysed bitstream (same bits as plot_bits) for
# 0.2088 ns, 300 K, -0.100 mA: first k^2 valid bits in seed order,
# 1 = switched, 0 = not switched, invalid runs excluded.

import math
from pathlib import Path

import Paper_plotter as P

PULSE_NS = 0.2088
TEMPERATURE_K = 300
CURRENT_MA = -0.100

OUT_DIR = Path(__file__).resolve().parent.parent / "data"
TXT_PATH = OUT_DIR / "bitstream_24k.txt"
CSV_PATH = OUT_DIR / "bitstream_24k_seeds.csv"


def main():

    sets = P.find_parameter_sets(P.TABLES_DIR)
    pset = next(
        p for p in sets
        if abs(p["pulse_ns"] - PULSE_NS) < 1e-6
        and p["temperature_K"] == TEMPERATURE_K
        and abs(p["current_mA"] - CURRENT_MA) < 1e-6
    )

    rows = []
    for item in pset["seed_files"]:
        try:
            mz = P.read_final_mz(item["file"])
        except (OSError, ValueError):
            mz = None
        if mz is None:
            continue
        o = P.classify(mz, P.MEASUREMENT_THRESHOLD)
        if o != -1:
            rows.append((item["seed"], o, mz))

    rows.sort(key=lambda r: r[0])
    side = math.isqrt(len(rows))
    rows = rows[:side * side]
    bits = "".join(str(b) for _, b, _ in rows)

    with open(TXT_PATH, "w", newline="\n") as f:
        for r in range(side):
            f.write(bits[r * side:(r + 1) * side] + "\n")

    with open(CSV_PATH, "w", newline="\n") as f:
        f.write("index,seed,bit,mz_final\n")
        for i, (seed, b, mz) in enumerate(rows, start=1):
            f.write(f"{i},{seed},{b},{mz:.6f}\n")

    # Verify from the written file
    lines = TXT_PATH.read_text().splitlines()
    total = sum(len(l) for l in lines)
    ones = sum(l.count("1") for l in lines)
    checks = {
        f"line count {side}": len(lines) == side,
        f"every line length {side}": all(len(l) == side for l in lines),
        f"total {side * side}": total == side * side,
        "ones 12243": ones == 12243,
        "zeros 12093": total - ones == 12093,
    }

    print(f"Wrote {TXT_PATH}")
    print(f"Wrote {CSV_PATH}")
    print(f"Valid bits used: {len(rows)} ({side} x {side}), "
          f"ones={ones}, zeros={total - ones}, last seed={rows[-1][0]}")
    for name, ok in checks.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")


if __name__ == "__main__":
    main()
