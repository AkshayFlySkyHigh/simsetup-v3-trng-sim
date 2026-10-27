# sweep_plots.py
#
# Psw sweep figures for the paper (simsetup_v3), same style as Paper_plotter.py.
#
#   1. Coarse pulse-width sweep   (0.190-0.210 ns, 300 K, -0.1 mA)
#   2. Fine pulse-width sweep     (0.2085-0.2092 ns, 300 K, -0.1 mA)
#   3. Temperature check          (298-302 K, 0.2088 ns, -0.1 mA)
#   4. Polarity check             (forward -0.1 mA vs reversed +0.1 mA, 0.2088 ns, 300 K)
#   5. Three example traces       (first switched / not switched / invalid run,
#                                  coarse 0.210 ns set, 10 ns max sim time)
#
# Psw = switched / all runs (invalid in denominator), +/- binomial s.e.
# Polarity figure: valid runs only, Psw = switched / (switched + not).
# Also writes plots/sweep_summary.csv with every number plotted.
#
# Run:  python sweep_plots.py

from pathlib import Path
import os
import sys
import json
import csv

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import matplotlib.pyplot as plt

import Paper_plotter as P
import paper_config as cfg


##############################################################################
# INPUTS
##############################################################################

# Fine sweep + temperature: synced v3 results (paper_config.DATA_ROOT)
FINE_ROOT = Path(cfg.DATA_ROOT)

# Coarse sweep (first v3 sweep, 500 runs per point)
COARSE_ROOT = Path(os.environ.get("SIMSETUP_COARSE_RESULTS", FINE_ROOT))

# Reversed polarity (polarsim_v1: initial m_z = -z, current +0.1 mA)
POLARITY_ROOT = Path(os.environ.get("SIMSETUP_POLARITY_RESULTS", FINE_ROOT))
POLARITY_SET = "0.2088ns_300K_0.100mA"

# Analysed set: 0.2088 ns / 300 K uses seeds 1..25849 only (156^2 valid bits)
ANALYSED = (0.2088, 300, -0.1)
ANALYSED_SEED_MAX = 10**9

# Skip sets with fewer runs than this (e.g. 0.2085 ns has 12, 0.45 ns has 4)
MIN_RUNS = 100

THRESHOLD = cfg.MEASUREMENT_THRESHOLD

FINE_WINDOW = (0.2085, 0.2092)

# Fine-sweep points left out of the paper (too few runs)
EXCLUDE_PULSES_NS = (0.2093,)

# Example-trace set: short (10 ns) max simulation time, so invalid runs exist
EXAMPLE_SET = COARSE_ROOT / "tables" / "0.210ns_300K_-0.100mA"
EXAMPLE_PULSE_NS = 0.210

SUMMARY_ROWS = []


##############################################################################
# DATA
##############################################################################

def set_stats(root, fixed, x_key, label):
    """Psw per parameter set under root/tables matching `fixed`."""

    P.METADATA_DIR = root / "metadata"   # read_final_mz looks here
    sets = P.find_parameter_sets(root / "tables")
    rows = []

    for p in sets:

        if any(abs(p[k] - v) > 1e-9 for k, v in fixed.items()):
            continue

        if x_key == "pulse_ns" and any(
                abs(p["pulse_ns"] - e) < 1e-9 for e in EXCLUDE_PULSES_NS):
            print(f"  excluded {p['folder'].name}")
            continue

        seed_files = p["seed_files"]

        if (abs(p["pulse_ns"] - ANALYSED[0]) < 1e-9
                and p["temperature_K"] == ANALYSED[1]
                and abs(p["current_mA"] - ANALYSED[2]) < 1e-9):
            seed_files = [s for s in seed_files if s["seed"] <= ANALYSED_SEED_MAX]

        if len(seed_files) < MIN_RUNS:
            print(f"  skip {p['folder'].name}: {len(seed_files)} runs < {MIN_RUNS}")
            continue

        print(f"  {p['folder'].name}")
        s = P.psw_for_set(seed_files, THRESHOLD)
        s["x"] = p[x_key]
        s["set"] = p["folder"].name
        rows.append(s)
        record(label, p["folder"].name, s)

    P.METADATA_DIR = Path(cfg.METADATA_DIR)
    return sorted(rows, key=lambda r: r["x"])


def reversed_stats():
    """Reversed polarity from metadata JSON (tables were not all synced).

    Initial state is -z, so a run switched if final m_z > +threshold.
    Duplicate seeds: newest JSON kept.
    """

    folder = POLARITY_ROOT / "metadata" / POLARITY_SET
    by_seed = {}

    for f in sorted(folder.glob("seed*.json")):
        m = P.SEED_RE.search(f.name)
        if m is None:
            continue
        seed = int(m.group(1))
        old = by_seed.get(seed)
        if old is None or f.stat().st_mtime > old.stat().st_mtime:
            by_seed[seed] = f

    sw = un = inv = 0

    for f in by_seed.values():
        try:
            with open(f, "r") as fh:
                mz = float(json.load(fh)["mz_final"])
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if mz > THRESHOLD:
            sw += 1
        elif mz < -THRESHOLD:
            un += 1
        else:
            inv += 1

    n = sw + un + inv
    p, lo, hi = P.binom_se(sw, n)
    s = {"n": n, "switched": sw, "unswitched": un, "invalid": inv,
         "psw": p, "lo": lo, "hi": hi}
    record("polarity", POLARITY_SET + " (reversed)", s)
    return s


def record(label, name, s):

    SUMMARY_ROWS.append({
        "figure": label,
        "set": name,
        "N": s["n"],
        "switched": s["switched"],
        "not_switched": s["unswitched"],
        "invalid": s["invalid"],
        "psw_pct": round(100 * s["psw"], 3),
        "se_pct": round(100 * (s["hi"] - s["lo"]) / 2, 3),
    })

    print(f"    N={s['n']} sw={s['switched']} not={s['unswitched']} "
          f"inv={s['invalid']} Psw={100*s['psw']:.2f}% "
          f"+/- {100*(s['hi']-s['lo'])/2:.2f}")


##############################################################################
# PLOTTING
##############################################################################

def sweep_axes(rows, xlabel, x_fmt, ylim=None):

    x = np.array([r["x"] for r in rows], dtype=float)
    y = np.array([r["psw"] for r in rows]) * 100
    lo = np.array([r["lo"] for r in rows]) * 100
    hi = np.array([r["hi"] for r in rows]) * 100

    fig, ax = plt.subplots(figsize=(P.SINGLE_COL_IN, 2.4))

    ax.errorbar(
        x, y, yerr=[y - lo, hi - y],
        fmt="o-", color=P.C_BLUE, ecolor=P.C_BLUE,
        elinewidth=0.8, capsize=2.5, capthick=0.8,
        markersize=3.5, lw=0.8,
        label=r"$P_{sw}$ ($\pm$ binomial s.e.)",
    )
    ax.axhline(50, color=P.C_VERMILION, lw=0.6, ls="--", label="50%")

    ax.set_xlabel(xlabel)
    ax.set_ylabel(r"$P_{sw}$ (%)")
    ax.set_xticks(x)
    ax.set_xticklabels([x_fmt(v) for v in x])
    if len(x) > 4:
        plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    ax.tick_params(axis="x", which="minor", bottom=False, top=False)
    ax.grid(True, axis="y")

    if ylim is None:
        pad = 2.0
        ylim = (min(lo.min(), 50) - pad, max(hi.max(), 50) + pad)
    ax.set_ylim(*ylim)

    return fig, ax


def plot_coarse(rows):

    if len(rows) < 2:
        print("Coarse sweep: fewer than 2 sets, skipped.")
        return

    fig, ax = sweep_axes(rows, "Pulse width (ns)", lambda v: f"{v:.3f}")
    ax.axvspan(*FINE_WINDOW, color=P.C_GREEN, alpha=0.2, lw=0,
               label="Fine-sweep window")
    ns = sorted({r["n"] for r in rows})
    ax.text(0.98, 0.04,
            f"T = 300 K, I = -0.100 mA, N = {'/'.join(map(str, ns))} per point",
            transform=ax.transAxes, fontsize=7, ha="right", va="bottom")
    ax.legend(loc="upper left")
    fig.tight_layout()
    P.save_figure(fig, "paper_coarse_sweep_300K_-0.100mA")


def plot_fine(rows):

    if len(rows) < 2:
        print("Fine sweep: fewer than 2 sets, skipped.")
        return

    fig, ax = sweep_axes(rows, "Pulse width (ns)", lambda v: f"{v:.4f}")
    for r in rows:
        ax.annotate(f"{r['n']}", (r["x"], 100 * r["hi"]),
                    textcoords="offset points", xytext=(0, 2),
                    ha="center", fontsize=6, color=P.C_GREY)
    ax.text(0.98, 0.04, "T = 300 K, I = -0.100 mA; numbers = runs N",
            transform=ax.transAxes, fontsize=7, ha="right", va="bottom")
    ax.legend(loc="upper left")
    fig.tight_layout()
    P.save_figure(fig, "paper_fine_sweep_300K_-0.100mA")


def plot_temperature(rows):

    if len(rows) < 2:
        print("Temperature: fewer than 2 sets, skipped.")
        return

    fig, ax = sweep_axes(rows, "Temperature (K)", lambda v: f"{v:g}")
    for r in rows:
        ax.annotate(f"{r['n']}", (r["x"], 100 * r["hi"]),
                    textcoords="offset points", xytext=(0, 2),
                    ha="center", fontsize=6, color=P.C_GREY)
    ax.text(0.98, 0.04, "Pulse = 0.2088 ns, I = -0.100 mA; numbers = runs N",
            transform=ax.transAxes, fontsize=7, ha="right", va="bottom")
    ax.legend(loc="upper left")
    fig.tight_layout()
    P.save_figure(fig, "paper_temperature_0.2088ns_-0.100mA")


def plot_polarity(fwd, rev):

    rows = [
        ("Forward\n$-0.1$ mA, $+z \\rightarrow -z$", fwd, P.C_BLUE),
        ("Reversed\n$+0.1$ mA, $-z \\rightarrow +z$", rev, P.C_ORANGE),
    ]

    # Valid runs only: Psw = switched / (switched + not switched)
    valid = []
    for lab, s, c in rows:
        k, n = s["switched"], s["switched"] + s["unswitched"]
        p, lo, hi = P.binom_se(k, n)
        v = {"n": n, "switched": k, "unswitched": s["unswitched"],
             "invalid": s["invalid"], "psw": p, "lo": lo, "hi": hi}
        record("polarity_valid_only", s["set"] if "set" in s else POLARITY_SET, v)
        valid.append((lab, v, c))
    inv_f, inv_r = fwd["invalid"], rev["invalid"]
    rows = valid
    fwd, rev = valid[0][1], valid[1][1]

    fig, ax = plt.subplots(figsize=(P.SINGLE_COL_IN, 2.4))

    for i, (lab, s, c) in enumerate(rows):
        y = 100 * s["psw"]
        ax.bar(i, y, width=0.55, color=c, alpha=0.85, edgecolor="none")
        ax.errorbar(i, y, yerr=[[y - 100 * s["lo"]], [100 * s["hi"] - y]],
                    color=P.C_BLACK, capsize=3, elinewidth=0.8, capthick=0.8)
        ax.text(i, 100 * s["hi"] + 0.4,
                f"{y:.2f}%\nN = {s['n']}", ha="center", va="bottom", fontsize=7)

    ax.axhline(50, color=P.C_VERMILION, lw=0.6, ls="--", label="50%")
    ax.set_xticks([0, 1])
    ax.set_xticklabels([r[0] for r in rows])
    ax.tick_params(axis="x", which="both", bottom=False, top=False)
    ax.set_ylabel(r"$P_{sw}$ (%)")
    top = max(100 * fwd["hi"], 100 * rev["hi"])
    ax.set_ylim(40, max(60, top + 4))
    ax.grid(True, axis="y")
    ax.legend(loc="upper right")
    ax.text(0.02, 0.04,
            "Pulse = 0.2088 ns, T = 300 K, invalid runs excluded, "
            "error bars = binomial s.e.\n"
            f"invalid: fwd {inv_f}, rev {inv_r}",
            transform=ax.transAxes, fontsize=6, va="bottom")
    fig.tight_layout()
    P.save_figure(fig, "paper_polarity_0.2088ns_300K")


def pulse_from_metadata(table_file):
    """Pulse width (ns) stored in the run's metadata JSON.

    The coarse set's metadata folder is named with the opposite current sign
    (0.210ns_300K_0.100mA) to its tables folder, so both names are tried.
    """

    table_file = Path(table_file)
    name = table_file.stem + ".json"
    folder = table_file.parent.name
    candidates = [folder, folder.replace("_-0.100mA", "_0.100mA"),
                  folder.replace("_-0.100mA", "_+0.100mA")]
    meta = None
    for c in candidates:
        f = COARSE_ROOT / "metadata" / c / name
        if f.exists():
            meta = f
            break
    if meta is None:
        raise FileNotFoundError(
            f"no metadata for {name} in {COARSE_ROOT / 'metadata'}")

    with open(meta, "r") as f:
        d = json.load(f)

    print(f"  metadata file: {meta}")
    print("  metadata (scalars): " + ", ".join(
        f"{k}={v}" for k, v in d.items()
        if isinstance(v, (int, float, str)) and k != "hash"))

    for k, v in d.items():
        if "pulse" in k.lower() and isinstance(v, (int, float)):
            return v * 1e9 if v < 1e-3 else float(v)

    raise KeyError(f"no numeric pulse key in {meta}: {list(d)}")


def plot_three_traces():
    """First switched, not switched and invalid run (seed order)."""

    if not EXAMPLE_SET.exists():
        print(f"  not found: {EXAMPLE_SET}")
        return

    picks = {}
    for item in P.get_all_seed_files(EXAMPLE_SET):
        df, mz = P.read_mz_table(item["file"])
        if df is None:
            continue
        o = P.classify(mz.iloc[-1], THRESHOLD)
        if o not in picks:
            picks[o] = (item["seed"], df["t"].values * 1e9, mz.values,
                        item["file"])
            print(f"  {P.OUTCOME_NAMES[o]:<13} seed {item['seed']}  "
                  f"final m_z = {mz.iloc[-1]:+.3f}")
        if len(picks) == 3:
            break

    style = {
        1: ("Switched", P.COLOR_SWITCHED, "-"),
        0: ("Not switched", P.COLOR_UNSWITCHED, "-"),
        -1: ("Invalid", P.C_BLACK, "-"),
    }

    fig, ax = plt.subplots(figsize=(P.SINGLE_COL_IN, 2.4))

    t_end = 0.0
    for o in (1, 0, -1):
        if o not in picks:
            continue
        seed, t, mz, _ = picks[o]
        lab, c, ls = style[o]
        ax.plot(t, mz, color=c, ls=ls, lw=1.2, alpha=1.0, zorder=3,
                label=f"{lab} (seed {seed})")
        t_end = max(t_end, t[-1])

    pulse_ns = pulse_from_metadata(next(iter(picks.values()))[3])
    print(f"  pulse width from metadata: {pulse_ns:.4f} ns")

    ax.axvspan(P.PULSE_START_NS, P.PULSE_START_NS + pulse_ns,
               color=P.C_GREY, alpha=0.25, lw=0)
    ax.axhline(THRESHOLD, color=P.C_BLACK, lw=0.5, ls="--")
    ax.axhline(-THRESHOLD, color=P.C_BLACK, lw=0.5, ls="--")

    # Label the pulse region (current on).
    ax.annotate(f"current pulse\n{pulse_ns:.3f} ns",
                xy=(P.PULSE_START_NS + pulse_ns / 2, 1.05),
                xytext=(P.PULSE_START_NS + 1.6, 1.22),
                fontsize=7, ha="left", va="center",
                arrowprops=dict(arrowstyle="-", lw=0.6, color=P.C_BLACK))

    ax.set_xlabel("Time (ns)")
    ax.set_ylabel(r"$m_z$ (normalized)")
    ax.set_xlim(0, t_end)
    ax.set_ylim(-1.1, 1.4)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3,
              fontsize=7, handlelength=1.2, columnspacing=0.8,
              borderaxespad=0.2,
              title=(f"Pulse {pulse_ns:.3f} ns (shaded), 300 K, "
                     f"-0.100 mA, max time {t_end:.0f} ns; "
                     rf"invalid: $|m_z| < {THRESHOLD}$ at end"),
              title_fontsize=7)

    fig.tight_layout()
    P.save_figure(fig, f"paper_three_traces_{EXAMPLE_PULSE_NS:.3f}ns_300K")


def write_summary():

    out = Path(P.PAPER_DIR) / "sweep_summary.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(SUMMARY_ROWS[0].keys()))
        w.writeheader()
        w.writerows(SUMMARY_ROWS)
    print(f'Saved: "{out}"')


##############################################################################
# MAIN
##############################################################################

def main():

    P.set_paper_style()

    # Optional figure names on the command line, e.g.  python sweep_plots.py fine three
    # (coarse, fine, temperature, polarity, three). No names = all figures.
    want = set(a.lower() for a in sys.argv[1:] if a.isalpha()) or {
        "coarse", "fine", "temperature", "polarity", "three"}
    full_run = len(want) == 5

    if "coarse" in want:
        print("\n=== Coarse pulse sweep ===")
        coarse = []
        if (COARSE_ROOT / "tables").exists():
            coarse = set_stats(COARSE_ROOT,
                               {"temperature_K": 300, "current_mA": -0.1},
                               "pulse_ns", "coarse")
        else:
            print(f"  not found: {COARSE_ROOT}")
        plot_coarse(coarse)

    fine = []
    if want & {"fine", "polarity"}:
        print("\n=== Fine pulse sweep ===")
        fine = set_stats(FINE_ROOT, {"temperature_K": 300, "current_mA": -0.1},
                         "pulse_ns", "fine")
        if "fine" in want:
            plot_fine(fine)
            for r in fine:
                print(f"  FINE {r['set']}: N={r['n']} sw={r['switched']} "
                      f"Psw={100 * r['psw']:.2f} +/- {100 * (r['hi'] - r['lo']) / 2:.2f}")

    if "temperature" in want:
        print("\n=== Temperature ===")
        temp = set_stats(FINE_ROOT, {"pulse_ns": 0.2088, "current_mA": -0.1},
                         "temperature_K", "temperature")
        plot_temperature(temp)

    if "polarity" in want:
        print("\n=== Polarity ===")
        fwd = next((r for r in fine if abs(r["x"] - ANALYSED[0]) < 1e-9), None)
        if fwd is not None and (POLARITY_ROOT / "metadata" / POLARITY_SET).exists():
            rec = dict(fwd)
            record("polarity", fwd["set"] + " (forward)", rec)
            rev = reversed_stats()
            plot_polarity(fwd, rev)
        else:
            print("  polarity data or forward set missing, skipped.")

    if "three" in want:
        print("\n=== Three example traces ===")
        plot_three_traces()

    # Only a full run rewrites the summary CSV (a partial run has partial rows).
    if SUMMARY_ROWS and full_run:
        write_summary()

    print(f"\nDone. Figures in: {P.PAPER_DIR}")


if __name__ == "__main__":
    main()
