from __future__ import annotations

import io
import os
import runpy
import sys
from pathlib import Path

import streamlit as st


ENTERPRISE_THEME = """
<style>
  :root {
    --vx-bg: #eef4fb;
    --vx-surface: rgba(255, 255, 255, 0.88);
    --vx-surface-strong: #ffffff;
    --vx-border: rgba(21, 51, 89, 0.10);
    --vx-shadow: 0 16px 40px rgba(20, 46, 82, 0.10);
    --vx-text: #14263f;
    --vx-text-soft: #5d6b82;
    --vx-primary: #2457d6;
    --vx-primary-2: #19a4a1;
    --vx-danger: #d84b62;
    --vx-warning: #d08a1f;
    --vx-success: #1f8f67;
    --vx-radius: 18px;
  }

  html, body, [data-testid="stAppViewContainer"] {
    background:
      radial-gradient(circle at top right, rgba(36, 87, 214, 0.10), transparent 32%),
      linear-gradient(180deg, #f4f8fd 0%, #edf3fb 100%);
    color: var(--vx-text);
  }

  [data-testid="stHeader"] {
    background: rgba(244, 248, 253, 0.70);
    backdrop-filter: blur(10px);
  }

  .block-container {
    max-width: 100%;
    padding-top: 1.25rem;
    padding-bottom: 2rem;
    padding-left: 1.25rem;
    padding-right: 1.25rem;
  }

  [data-testid="stSidebar"] {
    background: linear-gradient(180deg, #10203f 0%, #16335f 100%);
    border-right: 1px solid rgba(255, 255, 255, 0.07);
  }

  [data-testid="stSidebar"] * {
    color: #f3f7ff;
  }

  [data-testid="stSidebar"] .stButton > button,
  [data-testid="stSidebar"] div[data-testid="stDownloadButton"] > button {
    width: 100%;
  }

  .stButton > button,
  div[data-testid="stDownloadButton"] > button,
  button[kind="primary"],
  button[kind="secondary"] {
    min-height: 2.9rem;
    border-radius: 14px;
    border: 1px solid rgba(36, 87, 214, 0.10);
    background: linear-gradient(135deg, #ffffff 0%, #f7fbff 100%);
    color: var(--vx-text);
    font-weight: 600;
    box-shadow: 0 10px 24px rgba(20, 46, 82, 0.08);
    transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
  }

  .stButton > button:hover,
  div[data-testid="stDownloadButton"] > button:hover,
  button[kind="primary"]:hover,
  button[kind="secondary"]:hover {
    transform: translateY(-1px);
    box-shadow: 0 14px 28px rgba(20, 46, 82, 0.12);
    border-color: rgba(36, 87, 214, 0.24);
  }

  .stButton > button:focus,
  div[data-testid="stDownloadButton"] > button:focus,
  button[kind="primary"]:focus,
  button[kind="secondary"]:focus {
    outline: 3px solid rgba(36, 87, 214, 0.18);
    outline-offset: 2px;
  }

  button[kind="primary"] {
    background: linear-gradient(135deg, #2457d6 0%, #19a4a1 100%);
    color: #ffffff;
    border-color: transparent;
  }

  [data-baseweb="tab-list"] {
    gap: 0.5rem;
    flex-wrap: wrap;
    padding-bottom: 0.65rem;
    border-bottom: 1px solid var(--vx-border);
  }

  button[data-baseweb="tab"] {
    min-height: 2.8rem;
    padding: 0.7rem 1rem;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.66);
    border: 1px solid rgba(36, 87, 214, 0.08);
    box-shadow: 0 8px 20px rgba(20, 46, 82, 0.05);
  }

  button[data-baseweb="tab"][aria-selected="true"] {
    background: linear-gradient(135deg, #2457d6 0%, #477be8 100%);
    color: #ffffff;
    border-color: transparent;
  }

  [data-testid="stMetric"] {
    background: var(--vx-surface);
    border: 1px solid var(--vx-border);
    border-radius: var(--vx-radius);
    box-shadow: var(--vx-shadow);
    padding: 1rem 1.1rem;
  }

  [data-testid="stMetricLabel"],
  [data-testid="stMetricValue"],
  [data-testid="stMetricDelta"] {
    color: var(--vx-text);
  }

  [data-testid="stDataFrame"],
  [data-testid="stDataEditor"] {
    width: 100% !important;
    max-width: 100% !important;
    overflow-x: auto !important;
    border-radius: 16px;
    border: 1px solid var(--vx-border);
    background: rgba(255, 255, 255, 0.84);
  }

  [data-testid="stDataFrame"] > div,
  [data-testid="stDataEditor"] > div {
    max-width: 100% !important;
  }

  iframe[title="streamlit_custom_component"],
  iframe[title="components.html"] {
    width: 100% !important;
    max-width: 100% !important;
  }

  [data-testid="stHorizontalBlock"] {
    gap: 1rem;
  }

  [data-testid="column"] {
    min-width: 0;
  }

  .element-container,
  .stMarkdown,
  .stTable,
  .stDataFrame,
  .stDataEditor {
    max-width: 100%;
  }

  @media (max-width: 1100px) {
    .block-container {
      padding-left: 0.9rem;
      padding-right: 0.9rem;
    }

    [data-testid="stHorizontalBlock"] {
      flex-direction: column !important;
      align-items: stretch !important;
    }

    [data-testid="column"] {
      width: 100% !important;
      flex: 1 1 100% !important;
      min-width: 100% !important;
    }
  }

  @media (max-width: 768px) {
    .block-container {
      padding-top: 0.85rem;
      padding-left: 0.7rem;
      padding-right: 0.7rem;
      padding-bottom: 1.25rem;
    }

    .stButton > button,
    div[data-testid="stDownloadButton"] > button,
    button[kind="primary"],
    button[kind="secondary"] {
      width: 100%;
      min-height: 3rem;
      font-size: 0.98rem;
    }

    [data-baseweb="tab-list"] {
      gap: 0.4rem;
    }

    button[data-baseweb="tab"] {
      width: 100%;
      justify-content: center;
    }
  }
</style>
"""


BUTTON_ICON_MAP = {
    "Export Excel": "⬇ Export Excel",
    "Export PDF": "🧾 Export PDF",
    "Review Word Doc": "📝 Review Word Doc",
    "Save": "💾 Save",
    "Undo": "↶ Undo",
    "Redo": "↷ Redo",
    "Clear": "✕ Clear",
    "Apply": "✓ Apply",
    "Apply Mapping": "✓ Apply Mapping",
    "Open Holiday Calendar": "🗓 Open Holiday Calendar",
    "Browse files": "📂 Browse files",
    "Browse Files": "📂 Browse Files",
}


def _decorate_label(label):
    if not isinstance(label, str):
        return label

    stripped = label.strip()
    if not stripped:
        return label

    if stripped in BUTTON_ICON_MAP:
        return BUTTON_ICON_MAP[stripped]

    return label


def _normalize_width_kwargs(kwargs, default_stretch=False):
    normalized = dict(kwargs)
    if "use_container_width" in normalized:
        use_container_width = normalized.pop("use_container_width")
        if "width" not in normalized:
            normalized["width"] = "stretch" if use_container_width else "content"
    elif default_stretch and "width" not in normalized:
        normalized["width"] = "stretch"
    return normalized


def _patch_streamlit_runtime() -> None:
    from streamlit.delta_generator import DeltaGenerator

    if getattr(st, "_vertexone_enterprise_runtime_patched", False):
        return

    original_button = st.button
    original_download_button = st.download_button
    original_dataframe = st.dataframe
    original_data_editor = st.data_editor
    original_dg_button = DeltaGenerator.button
    original_dg_download_button = DeltaGenerator.download_button
    original_dg_dataframe = DeltaGenerator.dataframe
    original_dg_data_editor = DeltaGenerator.data_editor

    def patched_button(label, *args, **kwargs):
        return original_button(_decorate_label(label), *args, **kwargs)

    def patched_download_button(label, *args, **kwargs):
        return original_download_button(_decorate_label(label), *args, **kwargs)

    def patched_dataframe(data=None, *args, **kwargs):
        return original_dataframe(data, *args, **_normalize_width_kwargs(kwargs, default_stretch=True))

    def patched_data_editor(data=None, *args, **kwargs):
        return original_data_editor(data, *args, **_normalize_width_kwargs(kwargs, default_stretch=True))

    def patched_dg_button(self, label, *args, **kwargs):
        return original_dg_button(self, _decorate_label(label), *args, **kwargs)

    def patched_dg_download_button(self, label, *args, **kwargs):
        return original_dg_download_button(self, _decorate_label(label), *args, **kwargs)

    def patched_dg_dataframe(self, data=None, *args, **kwargs):
        return original_dg_dataframe(self, data, *args, **_normalize_width_kwargs(kwargs, default_stretch=True))

    def patched_dg_data_editor(self, data=None, *args, **kwargs):
        return original_dg_data_editor(self, data, *args, **_normalize_width_kwargs(kwargs, default_stretch=True))

    st.button = patched_button
    st.download_button = patched_download_button
    st.dataframe = patched_dataframe
    st.data_editor = patched_data_editor
    DeltaGenerator.button = patched_dg_button
    DeltaGenerator.download_button = patched_dg_download_button
    DeltaGenerator.dataframe = patched_dg_dataframe
    DeltaGenerator.data_editor = patched_dg_data_editor
    st._vertexone_enterprise_runtime_patched = True
    print("[PMO] Enterprise responsive theme patch loaded.")


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

st.markdown(ENTERPRISE_THEME, unsafe_allow_html=True)
_patch_streamlit_runtime()
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
