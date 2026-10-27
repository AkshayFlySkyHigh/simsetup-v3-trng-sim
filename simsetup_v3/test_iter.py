# test_iter.py

from pprint import pprint
from modules.iter_run import run_iteration
from modules.config import *

mumax_exe=MUMAX_EXE,
template_file=TEMPLATE_FILE,

result = run_iteration(
    pulse_ns=0.450,
    seed=1,
    mumax_exe=MUMAX_EXE,
    template_file=TEMPLATE_FILE,

    temperature_K=300,
    current_A=-1e-4,
    gpu_id=0,
)

print()
print("="*60)
print("RESULT")
print("="*60)

pprint(result)