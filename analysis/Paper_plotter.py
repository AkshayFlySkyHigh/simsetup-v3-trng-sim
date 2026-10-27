# Paper_plotter.py
#
# Publication-quality figures for simsetup_v3, standalone.
# Reads the synced results folder set in paper_config.py.
#
# Inputs (same layout as simsetup_v3 / manualplot.py):
#   <DATA_ROOT>/tables/<pulse>ns_<T>K_<I>mA/seedNNNN_<hash>.txt
#   <DATA_ROOT>/metadata/<pulse>ns_<T>K_<I>mA/seedNNNN_<hash>.json
#
# Classification: final m_z < -threshold switched, > threshold not switched,
# otherwise invalid (same as manualplot.py).
#
# Style: vector PDF + 300 dpi PNG, IEEE single column 3.5 in / double 7.16 in,
# serif 8-9 pt, Okabe-Ito palette, Psw error bars = binomial s.e.
#
# Figures:
#   1. m_z(t) overlay for one parameter set
#   2. Psw vs pulse width
#   3. Psw vs temperature
#   4. Bit sequence bitmap + cumulative-sum random walk
#
# Output: <this folder>/plots/<name>.pdf and .png
#
# Run:  python Paper_plotter.py

from pathlib import Path
import os
import sys
import re
import json
import math

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

import paper_config as cfg

TABLES_DIR = Path(cfg.TABLES_DIR)
METADATA_DIR = Path(cfg.METADATA_DIR)
PAPER_DIR = Path(cfg.OUTPUT_DIR)
MEASUREMENT_THRESHOLD = cfg.MEASUREMENT_THRESHOLD
PULSE_START_NS = cfg.PULSE_START_NS


##############################################################################
# DATA DISCOVERY (adapted from manualplot.py)
##############################################################################

SET_RE = re.compile(
    r"([+-]?\d+(?:\.\d+)?)ns_(\d+)K_([+-]?\d+(?:\.\d+)?)mA"
)
SEED_RE = re.compile(r"seed(\d+)")


def get_all_seed_files(tables_folder):

    by_seed = {}
    files = []

    for f in sorted(Path(tables_folder).iterdir()):

        if not f.is_file():
            continue

        m = SEED_RE.search(f.name)
        if m is None:
            continue

        item = {"seed": int(m.group(1)), "file": f}

        if cfg.DEDUP_SEEDS:
            old = by_seed.get(item["seed"])
            if old is None or f.stat().st_mtime > old["file"].stat().st_mtime:
                by_seed[item["seed"]] = item
        else:
            files.append(item)

    if cfg.DEDUP_SEEDS:
        files = list(by_seed.values())

    return sorted(files, key=lambda x: x["seed"])


def find_parameter_sets(tables_dir):

    tables_dir = Path(tables_dir)

    if not tables_dir.exists():
        print(f"ERROR: tables directory not found: {tables_dir}")
        print("Edit DATA_ROOT in paper_config.py")
        return []

    sets = []

    for folder in sorted(tables_dir.iterdir()):

        if not folder.is_dir():
            continue

        m = SET_RE.fullmatch(folder.name)
        if m is None:
            continue

        seed_files = get_all_seed_files(folder)
        if not seed_files:
            continue

        sets.append({
            "folder": folder,
            "pulse_ns": float(m.group(1)),
            "temperature_K": int(m.group(2)),
            "current_mA": float(m.group(3)),
            "seed_files": seed_files,
        })

    return sets


def print_parameter_sets(parameter_sets):

    print()
    print("=" * 70)
    print("AVAILABLE PARAMETER SETS")
    print("=" * 70)
    print(f"{'#':>4} {'Pulse (ns)':>12} {'Temp (K)':>10} "
          f"{'Current (mA)':>15} {'Seeds':>10}")
    print("-" * 70)

    for i, p in enumerate(parameter_sets, start=1):
        print(f"{i:>4} {p['pulse_ns']:>12.4f} {p['temperature_K']:>10} "
              f"{p['current_mA']:>15.3f} {len(p['seed_files']):>10}")

    print("=" * 70)
    print()


def choose_parameter_set(parameter_sets):

    while True:
        try:
            i = int(input(
                f"Choose parameter set [1-{len(parameter_sets)}]: "
            ).strip()) - 1
            if 0 <= i < len(parameter_sets):
                return parameter_sets[i]
        except ValueError:
            pass
        print("Invalid selection.")


def choose_seed_files(seed_files):

    seeds = [s["seed"] for s in seed_files]
    print(f"\nSeeds {min(seeds)} -> {max(seeds)} ({len(seeds)} available)")
    print("1. All available seeds")
    print("2. Custom seed range")

    while True:

        c = input("Choose seed selection [1/2]: ").strip()

        if c == "1":
            return seed_files

        if c == "2":
            try:
                a = int(input("Start seed: ").strip())
                b = int(input("End seed: ").strip())
            except ValueError:
                print("Enter integers.")
                continue
            sel = [s for s in seed_files if a <= s["seed"] <= b]
            if sel:
                print(f"Selected {len(sel)} seeds.")
                return sel
            print("No seeds in that range.")
            continue

        print("Enter 1 or 2.")


def read_mz_table(table_file):

    try:
        df = pd.read_csv(table_file, sep=r"\s+", comment="#", header=None)
    except Exception as e:
        print(f"PARSE ERROR: {table_file}\n{e}")
        return None, None

    if len(df) == 0:
        return None, None

    if df.shape[1] == 7:
        df.columns = ["t", "mx1", "my1", "mz1", "mx2", "my2", "mz2"]
        return df, df["mz2"]

    if df.shape[1] == 4:
        df.columns = ["t", "mx", "my", "mz"]
        return df, df["mz"]

    print(f"BAD TABLE: {table_file} ({df.shape[1]} columns)")
    return None, None


##############################################################################
# STYLE
##############################################################################

SINGLE_COL_IN = 3.5
DOUBLE_COL_IN = 7.16

# Okabe-Ito palette
C_BLUE = "#0072B2"
C_ORANGE = "#E69F00"
C_VERMILION = "#D55E00"
C_GREEN = "#009E73"
C_SKY = "#56B4E9"
C_PURPLE = "#CC79A7"
C_GREY = "#7F7F7F"
C_BLACK = "#000000"

COLOR_SWITCHED = C_BLUE
COLOR_UNSWITCHED = C_ORANGE
COLOR_INVALID = C_GREY


def set_paper_style():

    matplotlib.rcParams.update({
        "font.family": "serif",
        "font.serif": [
            "Times New Roman",
            "Times",
            "Nimbus Roman",
            "STIXGeneral",
            "DejaVu Serif",
        ],
        "mathtext.fontset": "stix",
        "font.size": 9,
        "axes.labelsize": 9,
        "axes.titlesize": 9,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 8,
        "axes.linewidth": 0.6,
        "lines.linewidth": 1.0,
        "lines.markersize": 4,
        "xtick.direction": "in",
        "ytick.direction": "in",
        "xtick.top": True,
        "ytick.right": True,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,
        "xtick.minor.visible": True,
        "ytick.minor.visible": True,
        "legend.frameon": False,
        "grid.linewidth": 0.4,
        "grid.alpha": 0.4,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
        # Embed TrueType fonts (IEEE PDF eXpress / Overleaf friendly)
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


def save_figure(fig, name):

    PAPER_DIR.mkdir(parents=True, exist_ok=True)

    # pdf_path = PAPER_DIR / f"{name}.pdf"
    png_path = PAPER_DIR / f"{name}.png"

    # fig.savefig(pdf_path, dpi=300)
    try:
        fig.savefig(png_path, dpi=300)
    except OSError:
        # Old PNG locked (e.g. open in a viewer): write a temp file, then replace.
        tmp_path = PAPER_DIR / f"{name}.tmp.png"
        fig.savefig(tmp_path, dpi=300)
        try:
            os.replace(tmp_path, png_path)
        except OSError:
            n = 1
            while (PAPER_DIR / f"{name}_{n}.png").exists():
                n += 1
            png_path = PAPER_DIR / f"{name}_{n}.png"
            os.replace(tmp_path, png_path)
            print(f"  original locked, saved as {png_path.name}")
    plt.close(fig)

    # print(f'Saved: "{pdf_path}"')
    print(f'Saved: "{png_path}"')

    if getattr(cfg, "AUTO_OPEN_IMAGES", False):
        try:
            os.startfile(png_path)
        except (AttributeError, OSError):
            pass


##############################################################################
# STATISTICS
##############################################################################

def binom_se(k, n):
    """p and +/- one binomial standard error sqrt(p(1-p)/n), clipped to [0, 1]."""

    if n == 0:
        return 0.0, 0.0, 0.0

    p = k / n
    se = math.sqrt(p * (1 - p) / n)

    return p, max(0.0, p - se), min(1.0, p + se)


OUTCOME_NAMES = {1: "SWITCHED", 0: "NOT_SWITCHED", -1: "INVALID"}


def progress(i, total, label, counts):
    """Single-line progress bar with running switched/not/invalid counts."""
    if i != total and i % 50 != 0:
        return
    width = 30
    frac = i / total if total else 1.0
    bar = "#" * int(width * frac) + "-" * (width - int(width * frac))
    sys.stdout.write(
        f"\r{label} [{bar}] {i}/{total} ({100*frac:5.1f}%)  "
        f"sw={counts[1]} not={counts[0]} inv={counts[-1]}")
    if i == total:
        sys.stdout.write("\n")
    sys.stdout.flush()


def classify(final_mz, threshold):

    if final_mz < -threshold:
        return 1   # switched

    if final_mz > threshold:
        return 0   # not switched

    return -1      # invalid


def read_final_mz(table_file):
    """Final m_z: metadata JSON mz_final if present, else table last row."""

    if cfg.USE_METADATA:
        meta = METADATA_DIR / Path(table_file).parent.name / (
            Path(table_file).stem + ".json")
        if meta.exists():
            try:
                with open(meta, "r") as f:
                    v = json.load(f).get("mz_final")
                if v is not None:
                    return float(v)
            except (OSError, ValueError):
                pass

    last = None

    with open(table_file, "r") as f:
        for line in f:
            s = line.strip()
            if s and not s.startswith("#"):
                last = s

    if last is None:
        return None

    cols = last.split()

    # 7 columns -> mz2 (index 6); 4 columns -> mz (index 3)
    if len(cols) == 7:
        return float(cols[6])

    if len(cols) == 4:
        return float(cols[3])

    return None


def outcomes_for_set(seed_files, threshold):
    """List of (seed, outcome) with outcome 1 / 0 / -1."""

    out = []
    total = len(seed_files)
    counts = {1: 0, 0: 0, -1: 0}

    for i, item in enumerate(seed_files, start=1):
        try:
            final_mz = read_final_mz(item["file"])
        except (OSError, ValueError):
            final_mz = None

        if final_mz is None:
            progress(i, total, "Classifying", counts)
            continue

        o = classify(final_mz, threshold)
        out.append((item["seed"], o))
        counts[o] += 1
        progress(i, total, "Classifying", counts)

    return out


def psw_for_set(seed_files, threshold):

    outcomes = outcomes_for_set(seed_files, threshold)

    n_sw = sum(1 for _, o in outcomes if o == 1)
    n_un = sum(1 for _, o in outcomes if o == 0)
    n_inv = sum(1 for _, o in outcomes if o == -1)

    # Psw over all classified runs (same denominator as manualplot.py)
    n = n_sw + n_un + n_inv
    p, lo, hi = binom_se(n_sw, n)

    return {
        "n": n,
        "switched": n_sw,
        "unswitched": n_un,
        "invalid": n_inv,
        "psw": p,
        "lo": lo,
        "hi": hi,
    }


##############################################################################
# FIGURE 1: m_z(t) OVERLAY
##############################################################################

def plot_overlay(pset, seed_files, threshold, max_traces=None):

    fig, ax = plt.subplots(figsize=(SINGLE_COL_IN, 2.8))

    counts = {1: 0, 0: 0, -1: 0}
    colors = {1: COLOR_SWITCHED, 0: COLOR_UNSWITCHED, -1: COLOR_INVALID}
    t_end = None

    files = seed_files
    if max_traces is not None and len(files) > max_traces:
        files = files[:max_traces]

    for i, item in enumerate(files, start=1):

        df, mz = read_mz_table(item["file"])

        if df is None:
            progress(i, len(files), "Plotting", counts)
            continue

        t_ns = df["t"].values * 1e9
        outcome = classify(mz.iloc[-1], threshold)
        counts[outcome] += 1
        progress(i, len(files), "Plotting", counts)
        t_end = t_ns[-1] if t_end is None else max(t_end, t_ns[-1])

        # Rasterize traces so the PDF stays small; axes/text stay vector.
        ax.plot(
            t_ns,
            mz.values,
            color=colors[outcome],
            linewidth=0.4,
            alpha=0.35,
            rasterized=True,
        )

    pulse_end = PULSE_START_NS + pset["pulse_ns"]

    ax.axvspan(PULSE_START_NS, pulse_end, color=C_GREY, alpha=0.2, lw=0)
    ax.axhline(threshold, color=C_BLACK, lw=0.5, ls="--")
    ax.axhline(-threshold, color=C_BLACK, lw=0.5, ls="--")

    ax.set_xlabel("Time (ns)")
    ax.set_ylabel(r"$m_z$ (normalized)")
    ax.set_ylim(-1.1, 1.1)

    if t_end is not None:
        ax.set_xlim(0, t_end)

    n = counts[1] + counts[0] + counts[-1]
    p, lo, hi = binom_se(counts[1], n)

    handles = [
        Line2D([0], [0], color=COLOR_SWITCHED, lw=1.2,
               label=f"Switched ({counts[1]})"),
        Line2D([0], [0], color=COLOR_UNSWITCHED, lw=1.2,
               label=f"Not switched ({counts[0]})"),
        Patch(facecolor=C_GREY, alpha=0.2,
              label=f"Pulse ({pset['pulse_ns']:.4f} ns)"),
    ]

    if counts[-1]:
        handles.insert(2, Line2D([0], [0], color=COLOR_INVALID, lw=1.2,
                                 label=f"Invalid ({counts[-1]})"))

    stats = (
        f"$P_{{sw}}$ = {100*p:.1f} $\\pm$ {100*(hi-lo)/2:.1f}% (s.e.), "
        f"N = {n}, T = {pset['temperature_K']} K, "
        f"I = {pset['current_mA']:.3f} mA"
    )

    # Legend above the axes so it never covers traces.
    ax.legend(handles=handles, loc="lower center",
              bbox_to_anchor=(0.5, 1.0), ncol=2, handlelength=1.5,
              title=stats, title_fontsize=7, fontsize=7,
              columnspacing=1.0, borderaxespad=0.2)

    fig.tight_layout()

    name = (
        f"paper_mz_overlay_{pset['pulse_ns']:.4f}ns_"
        f"{pset['temperature_K']}K_{pset['current_mA']:.3f}mA_N{n}"
    )

    save_figure(fig, name)


##############################################################################
# FIGURES 2 / 3: Psw SWEEPS
##############################################################################

def _sweep(parameter_sets, threshold, x_key, fixed):

    rows = []

    for p in parameter_sets:

        if any(abs(p[k] - v) > 1e-9 for k, v in fixed.items()):
            continue

        stats = psw_for_set(p["seed_files"], threshold)

        if stats["n"] == 0:
            continue

        stats["x"] = p[x_key]
        rows.append(stats)

        print(
            f"  {x_key}={p[x_key]}  N={stats['n']}  "
            f"Psw={100*stats['psw']:.2f}% "
            f"[{100*stats['lo']:.2f}, {100*stats['hi']:.2f}]"
        )

    return sorted(rows, key=lambda r: r["x"])


def _plot_sweep(rows, xlabel, name, note, x_fmt=None):

    if len(rows) < 2:
        print(f"Skipping {name}: fewer than 2 parameter sets match.")
        return

    x = np.array([r["x"] for r in rows])
    y = np.array([r["psw"] for r in rows]) * 100
    lo = np.array([r["lo"] for r in rows]) * 100
    hi = np.array([r["hi"] for r in rows]) * 100

    fig, ax = plt.subplots(figsize=(SINGLE_COL_IN, 2.4))

    ax.errorbar(
        x, y,
        yerr=[y - lo, hi - y],
        fmt="o-",
        color=C_BLUE,
        ecolor=C_BLUE,
        elinewidth=0.8,
        capsize=2.5,
        capthick=0.8,
        markersize=3.5,
        lw=0.8,
        label=r"$P_{sw}$ ($\pm$ binomial s.e.)",
    )

    ax.axhline(50, color=C_VERMILION, lw=0.6, ls="--", label="50%")

    ax.set_xlabel(xlabel)
    ax.set_ylabel(r"Switching probability $P_{sw}$ (%)")
    ax.set_ylim(-3, 103)
    ax.set_xticks(x)

    if x_fmt is not None:
        ax.set_xticklabels([x_fmt(v) for v in x])
        if len(x) > 4:
            plt.setp(ax.get_xticklabels(), rotation=30, ha="right")

    ax.minorticks_on()
    ax.tick_params(axis="x", which="minor", bottom=False, top=False)
    ax.grid(True, axis="y")
    ax.legend(loc="best")

    ax.text(0.98, 0.04, note, transform=ax.transAxes,
            fontsize=7, ha="right", va="bottom")

    fig.tight_layout()
    save_figure(fig, name)


def plot_psw_vs_pulse(parameter_sets, threshold, temperature_K, current_mA):

    print(f"\nPsw vs pulse width at T={temperature_K} K, I={current_mA} mA")

    rows = _sweep(
        parameter_sets, threshold, "pulse_ns",
        {"temperature_K": temperature_K, "current_mA": current_mA},
    )

    _plot_sweep(
        rows,
        "Pulse width (ns)",
        f"paper_psw_vs_pulse_{temperature_K}K_{current_mA:.3f}mA",
        f"T = {temperature_K} K, I = {current_mA:.3f} mA",
        x_fmt=lambda v: f"{v:.4f}",
    )


def plot_psw_vs_temperature(parameter_sets, threshold, pulse_ns, current_mA):

    print(f"\nPsw vs temperature at pulse={pulse_ns} ns, I={current_mA} mA")

    rows = _sweep(
        parameter_sets, threshold, "temperature_K",
        {"pulse_ns": pulse_ns, "current_mA": current_mA},
    )

    _plot_sweep(
        rows,
        "Temperature (K)",
        f"paper_psw_vs_temperature_{pulse_ns:.4f}ns_{current_mA:.3f}mA",
        f"Pulse = {pulse_ns:.4f} ns, I = {current_mA:.3f} mA",
        x_fmt=lambda v: f"{v:g}",
    )


##############################################################################
# FIGURE 4: BIT SEQUENCE BITMAP + CUMULATIVE SUM WALK
##############################################################################

def plot_bits(pset, seed_files, threshold):

    outcomes = outcomes_for_set(seed_files, threshold)

    # Bits in seed order; invalid runs are excluded from the sequence.
    bits = np.array([o for _, o in sorted(outcomes) if o != -1], dtype=int)
    n_valid = len(bits)

    if n_valid == 0:
        print("No valid bits in this set.")
        return

    # Keep the first k^2 bits (seed order) so the bitmap is a full square.
    side = math.isqrt(n_valid)
    bits = bits[:side * side]
    n = len(bits)
    if n < n_valid:
        print(f"Bitmap: using first {n} of {n_valid} valid bits "
              f"({side} x {side})")

    n_ones = int(bits.sum())
    n_inv = sum(1 for _, o in outcomes if o == -1)

    fig, (ax1, ax2) = plt.subplots(
        1, 2,
        figsize=(DOUBLE_COL_IN, 2.6),
        gridspec_kw={"width_ratios": [1, 1.6]},
    )

    # ---- bitmap (square-ish grid, row-major) ------------------------------
    width = int(math.ceil(math.sqrt(n)))
    height = int(math.ceil(n / width))
    grid = np.full(width * height, np.nan)
    grid[:n] = bits
    grid = grid.reshape(height, width)

    cmap = matplotlib.colors.ListedColormap([COLOR_UNSWITCHED, COLOR_SWITCHED])
    cmap.set_bad("white")

    ax1.imshow(
        np.ma.masked_invalid(grid),
        cmap=cmap,
        vmin=0, vmax=1,
        interpolation="nearest",
        aspect="equal",
    )
    ax1.set_xticks([])
    ax1.set_yticks([])
    ax1.minorticks_off()
    ax1.set_title(f"(a) Bit map, {width} x {height}, row-major")

    ax1.legend(
        handles=[
            Patch(facecolor=COLOR_SWITCHED, label=f"1 = switched ({n_ones})"),
            Patch(facecolor=COLOR_UNSWITCHED,
                  label=f"0 = not switched ({n - n_ones})"),
        ],
        loc="upper center",
        bbox_to_anchor=(0.5, -0.02),
        ncol=1,
        fontsize=7,
    )

    # ---- cumulative-sum walk ---------------------------------------------
    steps = 2 * bits - 1
    walk = np.cumsum(steps)
    idx = np.arange(1, n + 1)
    envelope = 2 * np.sqrt(idx)

    ax2.fill_between(idx, -envelope, envelope, color=C_SKY, alpha=0.25,
                     lw=0, label=r"$\pm 2\sqrt{n}$ (unbiased walk)")
    ax2.plot(idx, walk, color=C_BLUE, lw=0.7, label=r"$S_n=\sum(2b_i-1)$",
             rasterized=n > 5000)
    ax2.axhline(0, color=C_BLACK, lw=0.5)

    ax2.set_xlabel("Bit index $n$")
    ax2.set_ylabel("Cumulative sum $S_n$")
    ax2.set_xlim(0, n)
    ax2.grid(True)
    ax2.legend(loc="upper left", fontsize=7)

    p1 = n_ones / n
    note = (
        f"N = {n} bits, ones = {100*p1:.2f}%, "
        f"max $|S_n|$ = {int(np.max(np.abs(walk)))}"
    )
    if n < n_valid:
        note += f" (first {n} of {n_valid} valid)"
    if n_inv:
        note += f", {n_inv} invalid excluded"

    ax2.set_title("(b) Cumulative-sum random walk\n" + note, fontsize=8)

    fig.tight_layout()

    name = (
        f"paper_bits_{pset['pulse_ns']:.4f}ns_"
        f"{pset['temperature_K']}K_{pset['current_mA']:.3f}mA_N{n}"
    )

    save_figure(fig, name)


##############################################################################
# MENU
##############################################################################

def choose_menu():

    print()
    print("=" * 70)
    print("PAPER FIGURES")
    print("=" * 70)
    print("1. m_z(t) overlay (one set)")
    print("2. Psw vs pulse width")
    print("3. Psw vs temperature")
    print("4. Bit sequence bitmap + cumulative-sum walk (one set)")
    print("5. All of the above")
    print()

    while True:
        choice = input("Choose figure [1-5]: ").strip()
        if choice in {"1", "2", "3", "4", "5"}:
            return int(choice)
        print("Please enter 1-5.")


def ask_value(prompt, options, default):

    options = sorted(set(options))
    txt = ", ".join(f"{o:g}" for o in options)

    while True:
        raw = input(f"{prompt} [{txt}] (Enter = {default:g}): ").strip()
        if raw == "":
            return default
        try:
            v = float(raw)
        except ValueError:
            print("Enter a number.")
            continue
        for o in options:
            if abs(o - v) < 1e-9:
                return o
        print("Not an available value.")


def ask_overlay_limit(n):

    raw = input(
        f"Max traces in overlay (Enter = all {n}): "
    ).strip()

    if raw == "":
        return None

    try:
        return max(1, int(raw))
    except ValueError:
        return None


def main():

    print(f"DATA_ROOT  : {cfg.DATA_ROOT}")
    print(f"OUTPUT_DIR : {PAPER_DIR}")
    print(f"THRESHOLD  : {MEASUREMENT_THRESHOLD}")
    print(f"DEDUP_SEEDS: {cfg.DEDUP_SEEDS}")

    set_paper_style()

    parameter_sets = find_parameter_sets(TABLES_DIR)

    if len(parameter_sets) == 0:
        print(f"No parameter sets found in {TABLES_DIR}")
        return

    print_parameter_sets(parameter_sets)
    choice = choose_menu()

    temps = [p["temperature_K"] for p in parameter_sets]
    pulses = [p["pulse_ns"] for p in parameter_sets]
    currents = [p["current_mA"] for p in parameter_sets]

    # Single-set figures
    if choice in (1, 4, 5):

        print("\nSelect parameter set for overlay / bit figures.")
        pset = choose_parameter_set(parameter_sets)
        seed_files = choose_seed_files(pset["seed_files"])

        if choice in (1, 5):
            limit = ask_overlay_limit(len(seed_files))
            plot_overlay(pset, seed_files, MEASUREMENT_THRESHOLD, limit)

        if choice in (4, 5):
            plot_bits(pset, seed_files, MEASUREMENT_THRESHOLD)

    # Sweeps (use all seeds of each set)
    if choice in (2, 3, 5):

        default_I = max(set(currents), key=currents.count)
        current = ask_value("Current (mA)", currents, default_I)

        if choice in (2, 5):
            default_T = 300 if 300 in temps else max(set(temps), key=temps.count)
            T = ask_value("Temperature for Psw-vs-pulse (K)", temps, default_T)
            plot_psw_vs_pulse(parameter_sets, MEASUREMENT_THRESHOLD,
                              int(T), current)

        if choice in (3, 5):
            default_P = max(set(pulses), key=pulses.count)
            P = ask_value("Pulse for Psw-vs-temperature (ns)", pulses,
                          default_P)
            plot_psw_vs_temperature(parameter_sets, MEASUREMENT_THRESHOLD,
                                    P, current)

    print(f"\nDone. Figures in: {PAPER_DIR}")


if __name__ == "__main__":
    main()
