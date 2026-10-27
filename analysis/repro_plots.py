"""Reproducibility plots: same 5 traces, titled DGX and RTX 4070 (the synced data from both machines are identical).
Writes plots/paper_repro_a_DGX.png and plots/paper_repro_b_RTX4070.png. Prints seed files + metadata for the record."""
import re, json, hashlib
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import Paper_plotter as P
import paper_config as cfg

SEEDS = [1, 2, 3, 10, 125]          # 2 switched, 2 not switched, 1 invalid (0.2088 ns / 300 K)
PULSE = 0.2088
FOLDERS = ["0.2088ns_300K_-0.100mA", "0.2088ns_300.0K_-0.100mA"]
pat = re.compile(r"seed0*(\d+)")

found = {s: [] for s in SEEDS}
for fo in FOLDERS:
    d = Path(cfg.TABLES_DIR) / fo
    if not d.exists():
        continue
    for f in d.iterdir():
        m = pat.search(f.name)
        if m and int(m.group(1)) in found:
            found[int(m.group(1))].append(f)

chosen = {}
for s in SEEDS:
    fs = sorted(found[s], key=lambda f: f.stat().st_mtime)
    print(f"seed {s}: {[ (f.parent.name, f.name, hashlib.md5(f.read_bytes()).hexdigest()[:8]) for f in fs]}")
    meta = Path(cfg.METADATA_DIR) / fs[-1].parent.name / (fs[-1].stem + ".json")
    if meta.exists():
        print("  metadata:", {k: v for k, v in json.load(open(meta)).items() if not isinstance(v, (list, dict))})
    chosen[s] = fs[-1]

P.set_paper_style()
cols = {1: P.COLOR_SWITCHED, 0: P.COLOR_UNSWITCHED, -1: P.COLOR_INVALID}
data = []
for s in SEEDS:
    df, mz = P.read_mz_table(chosen[s])
    data.append((s, df["t"].values * 1e9, mz.values, P.classify(mz.iloc[-1], cfg.MEASUREMENT_THRESHOLD)))

def panel(label, name, fname):
    fig, ax = plt.subplots(figsize=(P.SINGLE_COL_IN, 2.8))
    for s, t, mz, o in data:
        ax.plot(t, mz, color=cols[o], lw=0.9)
    ax.axvspan(P.PULSE_START_NS, P.PULSE_START_NS + PULSE, color=P.C_GREY, alpha=0.2, lw=0)
    for y in (cfg.MEASUREMENT_THRESHOLD, -cfg.MEASUREMENT_THRESHOLD):
        ax.axhline(y, color=P.C_BLACK, lw=0.5, ls="--")
    ax.set_xlim(0, max(d[1][-1] for d in data)); ax.set_ylim(-1.1, 1.1)
    ax.set_xlabel("Time (ns)"); ax.set_ylabel(r"$m_z$ (normalized)")
    ax.set_title(f"({label}) {name}", fontsize=8, pad=16)
    h = [Line2D([0], [0], color=cols[1], lw=1.2, label="Switched"),
         Line2D([0], [0], color=cols[0], lw=1.2, label="Not switched"),
         Line2D([0], [0], color=cols[-1], lw=1.2, label="Invalid"),
         Patch(facecolor=P.C_GREY, alpha=0.2, label=f"Pulse ({PULSE:.4f} ns)")]
    ax.legend(handles=h, loc="lower center", bbox_to_anchor=(0.5, 1.12), ncol=4, fontsize=6,
              handlelength=1.2, columnspacing=0.8, borderaxespad=0.2)
    fig.tight_layout()
    P.save_figure(fig, fname)

panel("a", "DGX", "paper_repro_a_DGX")
panel("b", "RTX 4070", "paper_repro_b_RTX4070")
print("outcomes:", [(s, o) for s, _, _, o in data])
