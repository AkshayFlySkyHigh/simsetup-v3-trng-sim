"""Polarity check with equal valid N, no error bars, plus side-by-side trace plot.

Forward (-0.1 mA, +z -> -z) vs reversed (+0.1 mA, -z -> +z), 0.2088 ns / 300 K.
- Max time: reversed runs were simulated for 10 ns, so forward runs are cut at
  T_MAX_NS = 10 ns and classified by m_z at t = 10 ns (or the last sample if the
  run stopped earlier, e.g. early-stable), same 0.8 threshold.
- Bars: the first M valid forward runs (seed order) vs all M valid reversed runs,
  M = number of valid reversed runs. Runs are never chosen by outcome.
- Traces: m_z(t) overlays, the first K runs (seed order, any outcome) that have a
  table, same K for both polarities.
Writes plots/paper_polarity_bars.png and plots/paper_polarity_traces.png,
and prints every number used.

Run:  python polarity_plots.py
"""

from pathlib import Path
import sys
import json

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

import Paper_plotter as P
import paper_config as cfg
import sweep_plots as S

THR = cfg.MEASUREMENT_THRESHOLD
FWD_SET = "0.2088ns_300K_-0.100mA"
MAX_TRACES = 200      # cap on traces per panel
T_MAX_NS = 10.0       # reversed runs used a 10 ns max time


def newest_by_seed(files):
    by = {}
    for f in files:
        m = P.SEED_RE.search(f.name)
        if m is None:
            continue
        s = int(m.group(1))
        if s not in by or f.stat().st_mtime > by[s].stat().st_mtime:
            by[s] = f
    return dict(sorted(by.items()))


def outcome(final_mz, reversed_):
    """1 switched, 0 not switched, -1 invalid (reversed starts at -z)."""
    return P.classify(-final_mz if reversed_ else final_mz, THR)


def mz_at_tmax(table_file):
    """m_z at t = T_MAX_NS (last sample at or before it)."""
    df, mz = P.read_mz_table(table_file)
    if df is None:
        return None
    keep = df["t"].values * 1e9 <= T_MAX_NS + 1e-6
    if not keep.any():
        return None
    return float(mz.values[keep][-1])


def forward_runs(n_valid):
    """Forward runs in seed order, classified at 10 ns, until n_valid valid runs.

    Returns (all runs read so far as {seed: (file, outcome)}, total runs).
    """
    d = Path(cfg.TABLES_DIR) / FWD_SET
    files = newest_by_seed(d.iterdir())
    out = {}
    valid = 0
    for s, f in files.items():
        z = mz_at_tmax(f)
        if z is None:
            continue
        o = outcome(z, False)
        out[s] = (f, o)
        valid += o != -1
        if valid >= n_valid:
            break
    return out, len(files)


def reversed_runs():
    meta = S.POLARITY_ROOT / "metadata" / S.POLARITY_SET
    tabs = S.POLARITY_ROOT / "tables" / S.POLARITY_SET
    tfiles = newest_by_seed(tabs.glob("seed*.txt")) if tabs.exists() else {}
    out = {}
    for s, f in newest_by_seed(meta.glob("seed*.json")).items():
        try:
            with open(f) as fh:
                z = float(json.load(fh)["mz_final"])
        except (OSError, ValueError, KeyError, TypeError):
            continue
        t = None
        if s in tfiles:
            t = tfiles[s]
        out[s] = (t, outcome(z, True))
    return out


def counts(items):
    sw = sum(1 for o in items if o == 1)
    un = sum(1 for o in items if o == 0)
    return sw, un, sw / (sw + un), sw + un


def plot_bars(fs, rs, m, inv_f, inv_r):
    rows = [("Forward\n$-0.1$ mA, $+z \\rightarrow -z$", fs, P.C_BLUE),
            ("Reversed\n$+0.1$ mA, $-z \\rightarrow +z$", rs, P.C_ORANGE)]
    fig, ax = plt.subplots(figsize=(P.SINGLE_COL_IN, 2.4))
    for i, (lab, (sw, un, p, n), c) in enumerate(rows):
        y = 100 * p
        ax.bar(i, y, width=0.55, color=c, alpha=0.85, edgecolor="none")
        ax.text(i, y + 0.4, f"{y:.2f}%\nN = {n} valid", ha="center",
                va="bottom", fontsize=7)
    ax.axhline(50, color=P.C_VERMILION, lw=0.6, ls="--", label="50%")
    ax.set_xticks([0, 1])
    ax.set_xticklabels([r[0] for r in rows])
    ax.tick_params(axis="x", which="both", bottom=False, top=False)
    ax.set_ylabel(r"$P_{sw}$ (%)")
    ax.set_ylim(40, 60)
    ax.grid(True, axis="y")
    ax.legend(loc="upper right")
    ax.text(0.02, 0.04,
            "Pulse = 0.2088 ns, T = 300 K, 10 ns max time;\nequal N, invalid runs excluded",
            transform=ax.transAxes, fontsize=6, va="bottom")
    fig.tight_layout()
    P.save_figure(fig, "paper_polarity_bars")


def plot_traces(fwd, rev, k):
    colors = {1: P.COLOR_SWITCHED, 0: P.COLOR_UNSWITCHED, -1: P.COLOR_INVALID}
    fig, axes = plt.subplots(1, 2, figsize=(P.DOUBLE_COL_IN, 2.8),
                             sharex=True, sharey=True)
    t_end = 0.0
    shown = []
    for ax, (title, runs, rv) in zip(axes, [("(a) Forward, $-0.1$ mA", fwd, False),
                                             ("(b) Reversed, $+0.1$ mA", rev, True)]):
        cnt = {1: 0, 0: 0, -1: 0}
        for s, (f, o) in runs:
            df, mz = P.read_mz_table(f)
            if df is None:
                continue
            t = df["t"].values * 1e9
            keep = t <= T_MAX_NS + 1e-6
            t, y = t[keep], mz.values[keep]
            o = outcome(y[-1], rv)
            cnt[o] += 1
            t_end = max(t_end, t[-1])
            ax.plot(t, y, color=colors[o], lw=0.5, alpha=0.45,
                    rasterized=True)
        ax.axvspan(P.PULSE_START_NS, P.PULSE_START_NS + 0.2088,
                   color=P.C_GREY, alpha=0.2, lw=0)
        ax.axhline(THR, color=P.C_BLACK, lw=0.5, ls="--")
        ax.axhline(-THR, color=P.C_BLACK, lw=0.5, ls="--")
        ax.set_xlabel("Time (ns)")
        ax.set_title(f"{title} (n = {sum(cnt.values())})", fontsize=8)
        shown.append(cnt)
    axes[0].set_ylabel(r"$m_z$ (normalized)")
    axes[0].set_xlim(0, T_MAX_NS)
    axes[0].set_ylim(-1.1, 1.1)
    h = [Line2D([0], [0], color=colors[1], lw=1.2, label="Switched"),
         Line2D([0], [0], color=colors[0], lw=1.2, label="Not switched"),
         Line2D([0], [0], color=colors[-1], lw=1.2, label="Invalid")]
    fig.legend(handles=h, loc="lower center", ncol=3, fontsize=7,
               bbox_to_anchor=(0.5, 0.0), handlelength=1.4)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    P.save_figure(fig, "paper_polarity_traces")
    print("  trace outcome counts (fwd, rev):", shown)


def main():
    P.set_paper_style()
    rv = reversed_runs()
    r_valid = [(s, o) for s, (f, o) in rv.items() if o != -1]
    fw, n_fwd_files = forward_runs(len(r_valid))
    f_valid = [(s, o) for s, (f, o) in fw.items() if o != -1]
    m = min(len(f_valid), len(r_valid))
    print(f"forward: read {len(fw)} of {n_fwd_files} runs at t = {T_MAX_NS:g} ns "
          f"(valid {len(f_valid)}), "
          f"reversed runs {len(rv)} (valid {len(r_valid)}), equal N = {m}")

    fs = counts([o for _, o in f_valid[:m]])
    rs = counts([o for _, o in r_valid[:m]])
    last_f = f_valid[m - 1][0]
    print(f"forward first {m} valid: last seed {last_f}; "
          f"switched {fs[0]} not {fs[1]} Psw {100 * fs[2]:.2f}%")
    print(f"reversed first {m} valid: switched {rs[0]} not {rs[1]} "
          f"Psw {100 * rs[2]:.2f}%")
    inv_r = sum(1 for _, (f, o) in rv.items() if o == -1)
    plot_bars(fs, rs, m, None, inv_r)

    f_tab = [(s, v) for s, v in fw.items()]
    r_tab = [(s, v) for s, v in rv.items() if v[0] is not None]
    k = min(MAX_TRACES, len(f_tab), len(r_tab))
    print(f"reversed tables available: {len(r_tab)}; traces per panel K = {k}")
    plot_traces(f_tab[:k], r_tab[:k], k)
    print(f"  forward seeds {f_tab[0][0]}..{f_tab[k - 1][0]}, "
          f"reversed seeds {r_tab[0][0]}..{r_tab[k - 1][0]}")


if __name__ == "__main__":
    main()
