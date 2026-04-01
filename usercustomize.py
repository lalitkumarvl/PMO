try:
    import pmo_runtime_patch

    pmo_runtime_patch.apply_runtime_patch()
except Exception:
    pass
