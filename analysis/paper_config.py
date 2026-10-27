# paper_config.py
#
# Settings for Paper_plotter.py. Edit paths here, not in the plotter.

import os
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Synced simsetup_v3 results (contains tables/, metadata/, run_summary.csv).
# Set SIMSETUP_RESULTS to override; default is the results folder of a local
# simsetup_v3 run next to this repository's analysis folder.
DATA_ROOT = Path(os.environ.get("SIMSETUP_RESULTS", HERE.parent / "simsetup_v3" / "results"))

TABLES_DIR = DATA_ROOT / "tables"
METADATA_DIR = DATA_ROOT / "metadata"

# Figures go here (relative to this folder)
OUTPUT_DIR = HERE / "plots"

# Same as simsetup_v3 modules/config.py (MEASUREMENT_THRESHOLD)
MEASUREMENT_THRESHOLD = 0.8

# Pulse start time in the v3 template (same as manualplot.py)
PULSE_START_NS = 1.0

# Use metadata/<seedNNNN_hash>.json mz_final when present (fast).
# Falls back to the table's last row when missing.
USE_METADATA = True

# Same seed with several tables (different hash = re-run): keep newest only.
# False = keep all, like manualplot.py.
DEDUP_SEEDS = True

# Open each saved figure in the default image viewer (False = just save).
AUTO_OPEN_IMAGES = False
