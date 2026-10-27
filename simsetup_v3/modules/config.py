# ============================================================
# Machine configuration (example; edit for your machine)
# ============================================================

# ------------------------------------------------------------
# Machine information
# ------------------------------------------------------------

HOSTNAME = "my-gpu-host"
MACHINE = "GPU workstation"
MACHINE_ID = "gpu1"

# ------------------------------------------------------------
# MuMax3 executable
# ------------------------------------------------------------

MUMAX_EXE = "mumax3"  # full path to the MuMax3 3.10 executable if not on PATH

# GPUs available for this project
GPU_IDS = [0]

# Number of simultaneous simulations
MAX_PARALLEL_JOBS = len(GPU_IDS)

# ------------------------------------------------------------
# Simulation protocol
# ------------------------------------------------------------

SIM_PROTOCOL = "v3_kort"

# Classification threshold
MEASUREMENT_THRESHOLD = 0.8

# Retry behaviour
MAX_RETRIES = 1
RETRY_DELAY = 2  # seconds

# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------

TEMPLATE_FILE = "modules/template.mx3"

RESULTS_DIR = "results"

TABLES_DIR = "results/tables"
METADATA_DIR = "results/metadata"
PLOTS_DIR = "results/plots"

RUN_SUMMARY_FILE = "results/run_summary.csv"
RESULTS_SUMMARY_FILE = "results/results_summary.csv"

STATUS_LOG = "results/status.log"
ERROR_LOG = "results/error.log"

# ------------------------------------------------------------
# Caching / hashing
# ------------------------------------------------------------

ENABLE_CACHE = True
ENABLE_HASHING = True

# ------------------------------------------------------------
# Cleanup
# ------------------------------------------------------------
# False = keep the complete MuMax3 .out directory, including OVFs
# True  = delete the .out directory after extracting the results
CLEANUP = True

# ------------------------------------------------------------
# Output formatting
# ------------------------------------------------------------

PERCENT_DECIMALS = 4
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
ETA_AVERAGE_WINDOW = 100

# ------------------------------------------------------------
# Seed control
# ------------------------------------------------------------

SEED_SHIFT = 0


# ---------------- Early termination ---------------- #

ENABLE_EARLY_STOP = True

# Frequency at which the simulation output is checked
CHECK_INTERVAL_S = 0.5

# Minimum simulation time before early-stop logic is allowed
MIN_SIM_TIME_NS = 2.0

# Required duration for which the stability criterion must remain true
STABILITY_WINDOW_NS = 0.5

# Magnetization threshold for considering the state stable
MZ_THRESHOLD = MEASUREMENT_THRESHOLD

# Maximum allowed fluctuation of mz over the stability window
MZ_STD_THRESHOLD = 0.025

# Hard cutoff for the simulation
MAX_SIM_TIME_NS = 20
