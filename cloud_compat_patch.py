from io import StringIO
import os


def apply_cloud_compat_patch():
    try:
        import pandas as pd
    except Exception:
        return

    if getattr(pd, "_vertexone_cloud_patch_applied", False):
        return

    original_read_json = pd.read_json

    def patched_read_json(path_or_buf, *args, **kwargs):
        if isinstance(path_or_buf, str):
            candidate = path_or_buf.strip()
            looks_like_json = (
                (candidate.startswith("{") and candidate.endswith("}"))
                or (candidate.startswith("[") and candidate.endswith("]"))
                or ('"columns"' in candidate and '"data"' in candidate)
                or ("'columns'" in candidate and "'data'" in candidate)
            )
            if looks_like_json and not os.path.exists(candidate):
                return original_read_json(StringIO(path_or_buf), *args, **kwargs)
        return original_read_json(path_or_buf, *args, **kwargs)

    pd.read_json = patched_read_json
    pd._vertexone_cloud_patch_applied = True
