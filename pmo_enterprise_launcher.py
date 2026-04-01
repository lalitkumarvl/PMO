from pathlib import Path
import runpy
import sys


APP_DIR = Path(__file__).resolve().parent
APP_FILE = APP_DIR / "pmo_integrated_system.py"

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

try:
    import pmo_runtime_patch_v2

    pmo_runtime_patch_v2.apply_runtime_patch()
    print("[PMO] Enterprise runtime patch loaded.")
except Exception as exc:
    print(f"[PMO] Enterprise runtime patch failed to load: {exc}")

runpy.run_path(str(APP_FILE), run_name="__main__")
