from __future__ import annotations

import io
import os
import runpy
import sys
from pathlib import Path


def _patch_pandas_read_json() -> None:
    try:
        import pandas as pd
    except Exception as exc:  # pragma: no cover - launcher safety
        print(f"[PMO] Pandas compatibility patch skipped: {exc}")
        return

    if getattr(pd, "_pmo_read_json_patched", False):
        return

    original_read_json = pd.read_json

    def safe_read_json(path_or_buf, *args, **kwargs):
        if isinstance(path_or_buf, str):
            candidate = path_or_buf.strip()
            looks_like_json = candidate.startswith("{") or candidate.startswith("[")

            if looks_like_json and not os.path.exists(candidate):
                return original_read_json(io.StringIO(candidate), *args, **kwargs)

            try:
                return original_read_json(path_or_buf, *args, **kwargs)
            except FileNotFoundError:
                if looks_like_json:
                    return original_read_json(io.StringIO(candidate), *args, **kwargs)
                raise

        return original_read_json(path_or_buf, *args, **kwargs)

    pd.read_json = safe_read_json
    pd._pmo_read_json_patched = True
    print("[PMO] Pandas JSON compatibility patch loaded.")


def _resolve_app_dir() -> Path:
    here = Path(__file__).resolve().parent
    if (here / "pmo_integrated_system.py").exists():
        return here
    if (here / "PMO" / "pmo_integrated_system.py").exists():
        return here / "PMO"
    raise FileNotFoundError("Could not locate pmo_integrated_system.py")


APP_DIR = _resolve_app_dir()
APP_FILE = APP_DIR / "pmo_integrated_system.py"

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

_patch_pandas_read_json()

for patch_module_name in ("pmo_runtime_patch_v2", "pmo_runtime_patch"):
    try:
        patch_module = __import__(patch_module_name)
        if hasattr(patch_module, "apply_runtime_patch"):
            patch_module.apply_runtime_patch()
            print(f"[PMO] Runtime patch loaded from {patch_module_name}.")
            break
    except Exception as exc:  # pragma: no cover - launcher safety
        print(f"[PMO] Runtime patch {patch_module_name} skipped: {exc}")

runpy.run_path(str(APP_FILE), run_name="__main__")
