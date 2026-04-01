try:
    import pmo_runtime_patch

    pmo_runtime_patch.apply_runtime_patch()
except Exception:
    pass

try:
    import dashboard_word_patch

    dashboard_word_patch.patch_modules()
except Exception:
    pass
