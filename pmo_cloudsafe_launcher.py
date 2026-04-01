from __future__ import annotations

import io
import os
import re
import runpy
import sys
from pathlib import Path

import streamlit as st


ENTERPRISE_THEME = """
<style>
  :root {
    --vx-bg: #eef4fb;
    --vx-surface: rgba(255, 255, 255, 0.90);
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
    background: rgba(244, 248, 253, 0.72);
    backdrop-filter: blur(10px);
  }

  .block-container {
    max-width: 1480px;
    margin: 0 auto;
    padding-top: 1rem;
    padding-bottom: 2rem;
    padding-left: 1rem;
    padding-right: 1rem;
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

  [data-testid="stSidebar"] [data-testid="stFileUploader"],
  [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
    display: none !important;
  }

  .vx-hero {
    background: linear-gradient(135deg, #10203f 0%, #2457d6 100%);
    color: #ffffff;
    border-radius: 22px;
    padding: 1.2rem 1.3rem;
    box-shadow: 0 18px 42px rgba(18, 41, 74, 0.18);
    margin-bottom: 1rem;
  }

  .vx-hero__eyebrow {
    font-size: 0.72rem;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    opacity: 0.78;
    margin-bottom: 0.45rem;
    font-weight: 700;
  }

  .vx-hero__title {
    font-size: clamp(1.4rem, 2vw, 2rem);
    line-height: 1.1;
    font-weight: 800;
    margin: 0;
  }

  .vx-hero__body {
    margin-top: 0.55rem;
    color: rgba(255, 255, 255, 0.88);
    max-width: 72ch;
    font-size: 0.97rem;
    line-height: 1.55;
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
  [data-testid="stDataEditor"] > div,
  iframe[title="streamlit_custom_component"],
  iframe[title="components.html"] {
    max-width: 100% !important;
    width: 100% !important;
  }

  [data-testid="stHorizontalBlock"] {
    gap: 1rem;
    flex-wrap: wrap !important;
    align-items: stretch !important;
  }

  [data-testid="column"] {
    min-width: min(100%, 360px) !important;
    flex: 1 1 360px !important;
  }

  .element-container,
  .stMarkdown,
  .stTable,
  .stDataFrame,
  .stDataEditor {
    max-width: 100%;
  }

  @media (max-width: 1280px) {
    .block-container {
      padding-left: 0.85rem;
      padding-right: 0.85rem;
    }
  }

  @media (max-width: 960px) {
    .block-container {
      padding-top: 0.85rem;
      padding-left: 0.7rem;
      padding-right: 0.7rem;
      padding-bottom: 1.25rem;
    }

    [data-testid="column"] {
      min-width: 100% !important;
      flex-basis: 100% !important;
    }

    .stButton > button,
    div[data-testid="stDownloadButton"] > button,
    button[kind="primary"],
    button[kind="secondary"] {
      width: 100%;
      min-height: 3rem;
      font-size: 0.98rem;
    }

    button[data-baseweb="tab"] {
      width: 100%;
      justify-content: center;
    }
  }
</style>
"""


HIDDEN_BUTTONS = {
    "Open Holiday Calendar",
    "Open text-based Gantt view",
}

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
    "Browse files": "📂 Browse files",
    "Browse Files": "📂 Browse Files",
    "Restore Selected": "⟲ Restore Selected",
}

SCAN_HERO_HTML = """
<section class="vx-hero" aria-label="Project scan summary">
  <div class="vx-hero__eyebrow">Project Intelligence</div>
  <h1 class="vx-hero__title">Scan delivery data with less friction</h1>
  <div class="vx-hero__body">
    Upload a workbook once, review health, dependencies, resource pressure, and move
    directly into Kanban and management analysis without oversized intro panels.
  </div>
</section>
"""

ROADMAP_HERO_HTML = """
<section class="vx-hero" aria-label="Roadmap studio summary">
  <div class="vx-hero__eyebrow">Roadmap Studio</div>
  <h1 class="vx-hero__title">Plan milestones, teams, and risks in one workspace</h1>
  <div class="vx-hero__body">
    Capture project inputs, refine planning assumptions, and validate delivery feasibility
    through compact tabs instead of a long scrolling page.
  </div>
</section>
"""


def _decorate_label(label):
    if not isinstance(label, str):
        return label
    stripped = label.strip()
    if not stripped:
        return label
    return BUTTON_ICON_MAP.get(stripped, label)


def _normalize_width_kwargs(kwargs, default_stretch=False):
    normalized = dict(kwargs)
    if "use_container_width" in normalized:
        use_container_width = normalized.pop("use_container_width")
        if "width" not in normalized:
            normalized["width"] = "stretch" if use_container_width else "content"
    elif default_stretch and "width" not in normalized:
        normalized["width"] = "stretch"
    return normalized


def _sanitize_pdf_text(value) -> str:
    text = value if isinstance(value, str) else str(value)
    text = text.replace("\r", " ").replace("\t", " ")
    text = text.encode("latin-1", "replace").decode("latin-1")
    text = re.sub(r"[ ]{2,}", " ", text)
    lines = []
    for line in text.splitlines() or [""]:
        words = []
        for word in line.split(" "):
            if len(word) > 32:
                words.extend(word[i:i + 32] for i in range(0, len(word), 32))
            else:
                words.append(word)
        lines.append(" ".join(words).strip())
    return "\n".join(line for line in lines if line).strip() or "-"


def _pdf_bytes(pdf):
    raw = pdf.output(dest="S")
    if isinstance(raw, str):
        return raw.encode("latin-1", "replace")
    return bytes(raw)


def _write_pdf_section(pdf, heading: str, value) -> None:
    pdf.set_font("Helvetica", "B", 12)
    pdf.multi_cell(0, 8, _sanitize_pdf_text(heading))
    pdf.set_font("Helvetica", size=10)

    if hasattr(value, "to_string"):
        try:
            body = value.to_string(index=False)
        except Exception:
            body = str(value)
    else:
        body = str(value)

    body = _sanitize_pdf_text(body)
    for paragraph in body.split("\n"):
        pdf.multi_cell(0, 5, paragraph or "-")
    pdf.ln(1)


def _safe_build_roadmap_pdf(*args, **kwargs):
    from fpdf import FPDF

    title = kwargs.get("project_name") or (args[0] if args else "Enterprise Project Roadmap")
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(0, 10, _sanitize_pdf_text(title))
    pdf.ln(2)

    for index, value in enumerate(args[1:], start=1):
        _write_pdf_section(pdf, f"Section {index}", value)

    for key, value in kwargs.items():
        if key == "project_name":
            continue
        _write_pdf_section(pdf, key.replace("_", " ").title(), value)

    return _pdf_bytes(pdf)


def _safe_build_scan_pdf_report(*args, **kwargs):
    from fpdf import FPDF

    title = kwargs.get("title") or (args[0] if args else "Project Scan Review")
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(0, 10, _sanitize_pdf_text(title))
    pdf.ln(2)

    for index, value in enumerate(args[1:], start=1):
        _write_pdf_section(pdf, f"Analysis {index}", value)

    for key, value in kwargs.items():
        if key == "title":
            continue
        _write_pdf_section(pdf, key.replace("_", " ").title(), value)

    return _pdf_bytes(pdf)


def _patch_streamlit_runtime() -> None:
    from streamlit.delta_generator import DeltaGenerator

    if getattr(st, "_vertexone_enterprise_runtime_patched", False):
        return

    original_set_page_config = st.set_page_config
    original_button = st.button
    original_download_button = st.download_button
    original_dataframe = st.dataframe
    original_data_editor = st.data_editor
    original_markdown = st.markdown
    original_dg_button = DeltaGenerator.button
    original_dg_download_button = DeltaGenerator.download_button
    original_dg_dataframe = DeltaGenerator.dataframe
    original_dg_data_editor = DeltaGenerator.data_editor
    original_dg_markdown = DeltaGenerator.markdown

    def patched_set_page_config(*args, **kwargs):
        patched_kwargs = dict(kwargs)
        patched_kwargs.setdefault("layout", "wide")
        patched_kwargs.setdefault("initial_sidebar_state", "collapsed")
        return original_set_page_config(*args, **patched_kwargs)

    def patched_button(label, *args, **kwargs):
        if isinstance(label, str) and label.strip() in HIDDEN_BUTTONS:
            return False
        return original_button(_decorate_label(label), *args, **kwargs)

    def patched_download_button(label, *args, **kwargs):
        return original_download_button(_decorate_label(label), *args, **kwargs)

    def patched_dataframe(data=None, *args, **kwargs):
        return original_dataframe(data, *args, **_normalize_width_kwargs(kwargs, default_stretch=True))

    def patched_data_editor(data=None, *args, **kwargs):
        return original_data_editor(data, *args, **_normalize_width_kwargs(kwargs, default_stretch=True))

    def _replacement_markdown(body):
        if not isinstance(body, str):
            return body, False
        if "Portfolio Timeline Scanner" in body or "Project Scan & Analysis" in body:
            return SCAN_HERO_HTML, True
        if "Project Roadmap Studio" in body:
            return ROADMAP_HERO_HTML, True
        return body, False

    def patched_markdown(body, *args, **kwargs):
        replacement, is_html = _replacement_markdown(body)
        patched_kwargs = dict(kwargs)
        if is_html:
            patched_kwargs["unsafe_allow_html"] = True
        return original_markdown(replacement, *args, **patched_kwargs)

    def patched_dg_button(self, label, *args, **kwargs):
        if isinstance(label, str) and label.strip() in HIDDEN_BUTTONS:
            return False
        return original_dg_button(self, _decorate_label(label), *args, **kwargs)

    def patched_dg_download_button(self, label, *args, **kwargs):
        return original_dg_download_button(self, _decorate_label(label), *args, **kwargs)

    def patched_dg_dataframe(self, data=None, *args, **kwargs):
        return original_dg_dataframe(self, data, *args, **_normalize_width_kwargs(kwargs, default_stretch=True))

    def patched_dg_data_editor(self, data=None, *args, **kwargs):
        return original_dg_data_editor(self, data, *args, **_normalize_width_kwargs(kwargs, default_stretch=True))

    def patched_dg_markdown(self, body, *args, **kwargs):
        replacement, is_html = _replacement_markdown(body)
        patched_kwargs = dict(kwargs)
        if is_html:
            patched_kwargs["unsafe_allow_html"] = True
        return original_dg_markdown(self, replacement, *args, **patched_kwargs)

    st.set_page_config = patched_set_page_config
    st.button = patched_button
    st.download_button = patched_download_button
    st.dataframe = patched_dataframe
    st.data_editor = patched_data_editor
    st.markdown = patched_markdown
    DeltaGenerator.button = patched_dg_button
    DeltaGenerator.download_button = patched_dg_download_button
    DeltaGenerator.dataframe = patched_dg_dataframe
    DeltaGenerator.data_editor = patched_dg_data_editor
    DeltaGenerator.markdown = patched_dg_markdown
    st._vertexone_enterprise_runtime_patched = True
    print("[PMO] Enterprise responsive theme patch loaded.")


def _patch_pandas_read_json() -> None:
    try:
        import pandas as pd
    except Exception as exc:  # pragma: no cover
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
            except (FileNotFoundError, OSError, ValueError):
                if looks_like_json:
                    return original_read_json(io.StringIO(candidate), *args, **kwargs)
                raise

        return original_read_json(path_or_buf, *args, **kwargs)

    pd.read_json = safe_read_json
    pd._pmo_read_json_patched = True
    print("[PMO] Pandas JSON compatibility patch loaded.")


def _apply_workspace_patches() -> None:
    try:
        import project_scan_workspace
        import roadmap_workspace
    except Exception as exc:
        print(f"[PMO] Base workspace patch skipped: {exc}")
        return

    try:
        from scan_workspace_v3 import render_scan_workspace_v3

        project_scan_workspace.render_project_scan_workspace = render_scan_workspace_v3
    except Exception as exc:
        print(f"[PMO] Scan workspace v3 patch skipped: {exc}")

    try:
        from roadmap_workspace_v3 import render_roadmap_workspace_v3

        roadmap_workspace.render_roadmap_workspace = render_roadmap_workspace_v3
    except Exception as exc:
        print(f"[PMO] Roadmap workspace v3 patch skipped: {exc}")

    try:
        project_scan_workspace.build_scan_pdf_report = _safe_build_scan_pdf_report
    except Exception:
        pass

    try:
        roadmap_workspace.build_roadmap_pdf = _safe_build_roadmap_pdf
    except Exception:
        pass

    print("[PMO] Direct workspace compatibility patches loaded.")


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

_patch_streamlit_runtime()
_patch_pandas_read_json()
_apply_workspace_patches()
st.markdown(ENTERPRISE_THEME, unsafe_allow_html=True)

for patch_module_name in ("pmo_runtime_patch_v2", "pmo_runtime_patch"):
    try:
        patch_module = __import__(patch_module_name)
        if hasattr(patch_module, "apply_runtime_patch"):
            patch_module.apply_runtime_patch()
            print(f"[PMO] Runtime patch loaded from {patch_module_name}.")
            break
    except Exception as exc:  # pragma: no cover
        print(f"[PMO] Runtime patch {patch_module_name} skipped: {exc}")

runpy.run_path(str(APP_FILE), run_name="__main__")
