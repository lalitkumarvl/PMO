from __future__ import annotations

import importlib
import io
import json
import os
import runpy
import sys
import types
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


ENTERPRISE_THEME = """
<style>
  :root {
    --vx-bg: #eef4fb;
    --vx-surface: rgba(255, 255, 255, 0.92);
    --vx-border: rgba(21, 51, 89, 0.10);
    --vx-shadow: 0 16px 36px rgba(20, 46, 82, 0.10);
    --vx-text: #14263f;
    --vx-text-soft: #5d6b82;
    --vx-primary: #2457d6;
    --vx-secondary: #19a4a1;
    --vx-radius: 18px;
  }

  html, body, [data-testid="stAppViewContainer"] {
    background:
      radial-gradient(circle at top right, rgba(36, 87, 214, 0.10), transparent 32%),
      linear-gradient(180deg, #f4f8fd 0%, #edf3fb 100%);
    color: var(--vx-text);
    overflow-x: hidden;
    -webkit-text-size-adjust: 100%;
    text-size-adjust: 100%;
  }

  *, *::before, *::after {
    box-sizing: border-box;
  }

  [data-testid="stHeader"] {
    background: rgba(244, 248, 253, 0.70);
    backdrop-filter: blur(10px);
  }

  .block-container {
    max-width: 100%;
    padding-top: 0.95rem;
    padding-bottom: 1.75rem;
    padding-left: 0.8rem;
    padding-right: 0.8rem;
  }

  h1, h2, h3, h4 {
    color: var(--vx-text);
    line-height: 1.12;
    word-break: keep-all !important;
    overflow-wrap: break-word;
    hyphens: none;
  }

  h1 { font-size: clamp(1.7rem, 3vw, 2.6rem) !important; }
  h2 { font-size: clamp(1.35rem, 2.2vw, 2rem) !important; }
  h3 { font-size: clamp(1.15rem, 1.8vw, 1.55rem) !important; }

  p, li, label, span, div {
    overflow-wrap: break-word;
    word-break: normal;
  }

  [data-testid="stSidebar"] {
    background: linear-gradient(180deg, #10203f 0%, #16335f 100%);
    border-right: 1px solid rgba(255, 255, 255, 0.08);
    overflow-x: hidden;
    min-width: 240px !important;
    max-width: 240px !important;
  }

  [data-testid="stSidebar"] * {
    color: #f4f7ff;
  }

  [data-testid="stSidebar"] [data-testid="stFileUploader"],
  [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
    display: none !important;
  }

  .stButton > button,
  div[data-testid="stDownloadButton"] > button,
  button[kind="primary"],
  button[kind="secondary"] {
    min-height: 2.85rem;
    border-radius: 14px;
    border: 1px solid rgba(36, 87, 214, 0.12);
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
    outline: 3px solid rgba(36, 87, 214, 0.20);
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
    padding-bottom: 0.6rem;
    border-bottom: 1px solid var(--vx-border);
  }

  button[data-baseweb="tab"] {
    min-height: 2.75rem;
    padding: 0.68rem 1rem;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.72);
    border: 1px solid rgba(36, 87, 214, 0.08);
    box-shadow: 0 8px 18px rgba(20, 46, 82, 0.05);
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
    padding: 1rem 1.05rem;
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
    width: 100% !important;
    max-width: 100% !important;
  }

  img, svg, canvas {
    max-width: 100%;
    height: auto;
  }

  [data-testid="stTabs"] {
    max-width: 100%;
    overflow: hidden;
  }

  [data-testid="stHorizontalBlock"] {
    align-items: stretch;
  }

  .stButton,
  div[data-testid="stDownloadButton"] {
    max-width: 100%;
  }

  .vx-mobile-shell {
    display: none;
  }

  @media (max-width: 1100px) {
    .block-container {
      padding-left: 0.8rem;
      padding-right: 0.8rem;
    }

    [data-testid="stSidebar"] {
      min-width: 220px !important;
      max-width: 220px !important;
    }
  }

  @media (max-width: 820px) {
    .block-container {
      padding-top: 0.75rem;
      padding-left: 0.7rem;
      padding-right: 0.7rem;
      padding-bottom: 1rem;
    }

    [data-testid="stSidebar"] {
      min-width: min(84vw, 320px) !important;
      max-width: min(84vw, 320px) !important;
    }

    h1 { font-size: clamp(1.45rem, 7vw, 1.9rem) !important; }
    h2 { font-size: clamp(1.2rem, 5.4vw, 1.55rem) !important; }
    h3 { font-size: clamp(1.05rem, 4.4vw, 1.25rem) !important; }

    .stButton > button,
    div[data-testid="stDownloadButton"] > button,
    button[kind="primary"],
    button[kind="secondary"] {
      width: 100%;
      min-height: 3rem;
    }

    button[data-baseweb="tab"] {
      width: 100%;
      justify-content: center;
    }

    [data-testid="stSidebar"] {
      display: none !important;
    }

    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapseButton"] {
      display: none !important;
    }

    .vx-mobile-shell {
      display: block;
      margin-bottom: 0.9rem;
    }

    [data-testid="stHorizontalBlock"] {
      flex-direction: column !important;
      gap: 0.75rem !important;
    }

    [data-testid="column"] {
      width: 100% !important;
      flex: 1 1 100% !important;
      min-width: 100% !important;
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
    "Restore Selected": "⟲ Restore Selected",
    "Browse files": "📂 Browse files",
    "Browse Files": "📂 Browse Files",
}


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
    words = []
    for chunk in text.split():
        if len(chunk) > 28:
            words.extend(chunk[i:i + 28] for i in range(0, len(chunk), 28))
        else:
            words.append(chunk)
    return " ".join(words) or "-"


def _pdf_bytes(pdf):
    raw = pdf.output(dest="S")
    if isinstance(raw, str):
        return raw.encode("latin-1", "replace")
    return bytes(raw)


def _safe_build_pdf(title: str, *sections, **named_sections):
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(0, 10, _sanitize_pdf_text(title))
    pdf.ln(2)

    pdf.set_font("Helvetica", size=10)
    for index, section in enumerate(sections, start=1):
        pdf.set_font("Helvetica", "B", 12)
        pdf.multi_cell(0, 7, f"Section {index}")
        pdf.set_font("Helvetica", size=10)
        body = section.to_string(index=False) if hasattr(section, "to_string") else str(section)
        for line in str(body).splitlines() or ["-"]:
            pdf.multi_cell(0, 5, _sanitize_pdf_text(line))
        pdf.ln(1)

    for key, value in named_sections.items():
        pdf.set_font("Helvetica", "B", 12)
        pdf.multi_cell(0, 7, _sanitize_pdf_text(key.replace("_", " ").title()))
        pdf.set_font("Helvetica", size=10)
        body = value.to_string(index=False) if hasattr(value, "to_string") else str(value)
        for line in str(body).splitlines() or ["-"]:
            pdf.multi_cell(0, 5, _sanitize_pdf_text(line))
        pdf.ln(1)

    return _pdf_bytes(pdf)


def _safe_build_scan_pdf_report(*args, **kwargs):
    title = kwargs.pop("title", None) or (args[0] if args else "Project Scan Review")
    remaining_args = args[1:] if args else ()
    return _safe_build_pdf(title, *remaining_args, **kwargs)


def _safe_build_roadmap_pdf(*args, **kwargs):
    title = kwargs.pop("project_name", None) or (args[0] if args else "Enterprise Project Roadmap")
    remaining_args = args[1:] if args else ()
    return _safe_build_pdf(title, *remaining_args, **kwargs)


def _patch_fpdf() -> None:
    try:
        from fpdf import FPDF
        from fpdf.errors import FPDFException
    except Exception as exc:
        print(f"[PMO] FPDF patch skipped: {exc}")
        return

    if getattr(FPDF, "_pmo_multi_cell_patched", False):
        return

    original_multi_cell = FPDF.multi_cell

    def safe_multi_cell(self, w, h=None, text="", *args, **kwargs):
        safe_text = _sanitize_pdf_text(text)
        try:
            return original_multi_cell(self, w, h, safe_text, *args, **kwargs)
        except FPDFException as exc:
            if "Not enough horizontal space" not in str(exc):
                raise
            try:
                self.set_x(self.l_margin)
            except Exception:
                pass
            retry_w = w if isinstance(w, (int, float)) and w > 5 else max(getattr(self, "epw", 170), 50)
            retry_h = h if h is not None else 5
            return original_multi_cell(self, retry_w, retry_h, safe_text, *args, **kwargs)

    FPDF.multi_cell = safe_multi_cell
    FPDF._pmo_multi_cell_patched = True
    print("[PMO] FPDF compatibility patch loaded.")


def _patch_pandas_read_json() -> None:
    try:
        import pandas as pd
    except Exception as exc:
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
                try:
                    return original_read_json(io.StringIO(candidate), *args, **kwargs)
                except Exception:
                    try:
                        loaded = json.loads(candidate)
                        if isinstance(loaded, dict) and "data" in loaded:
                            return pd.DataFrame(loaded["data"])
                        if isinstance(loaded, list):
                            return pd.DataFrame(loaded)
                    except Exception:
                        pass

            try:
                return original_read_json(path_or_buf, *args, **kwargs)
            except (FileNotFoundError, OSError, ValueError):
                if looks_like_json:
                    try:
                        return original_read_json(io.StringIO(candidate), *args, **kwargs)
                    except Exception:
                        loaded = json.loads(candidate)
                        if isinstance(loaded, dict) and "data" in loaded:
                            return pd.DataFrame(loaded["data"])
                        if isinstance(loaded, list):
                            return pd.DataFrame(loaded)
                raise

        return original_read_json(path_or_buf, *args, **kwargs)

    pd.read_json = safe_read_json
    pd._pmo_read_json_patched = True
    print("[PMO] Pandas JSON compatibility patch loaded.")


def _patch_streamlit_runtime() -> None:
    from streamlit.delta_generator import DeltaGenerator

    if getattr(st, "_vertexone_enterprise_runtime_patched", False):
        return

    original_set_page_config = st.set_page_config
    original_button = st.button
    original_download_button = st.download_button
    original_dataframe = st.dataframe
    original_data_editor = st.data_editor
    original_radio = st.radio
    original_dg_button = DeltaGenerator.button
    original_dg_download_button = DeltaGenerator.download_button
    original_dg_dataframe = DeltaGenerator.dataframe
    original_dg_data_editor = DeltaGenerator.data_editor

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

    def patched_radio(label, options, *args, **kwargs):
        normalized_options = list(options) if isinstance(options, (list, tuple)) else options
        if isinstance(label, str) and "Select Engine" in label and isinstance(normalized_options, list):
            if "🚀 Scan Project" in normalized_options and "📅 Create RoadMap" in normalized_options:
                display_options = ["🚀 Scan Project", "📅 Create RoadMap", "🧾 Asset Management", "📈 Reports"]
                selected = original_radio(label, display_options, *args, **kwargs)
                st.session_state["_pmo_actual_engine"] = selected
                if selected in {"🧾 Asset Management", "📈 Reports"}:
                    return "🚀 Scan Project"
                return selected
        return original_radio(label, options, *args, **kwargs)

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

    st.set_page_config = patched_set_page_config
    st.button = patched_button
    st.download_button = patched_download_button
    st.dataframe = patched_dataframe
    st.data_editor = patched_data_editor
    st.radio = patched_radio
    DeltaGenerator.button = patched_dg_button
    DeltaGenerator.download_button = patched_dg_download_button
    DeltaGenerator.dataframe = patched_dg_dataframe
    DeltaGenerator.data_editor = patched_dg_data_editor
    st._vertexone_enterprise_runtime_patched = True
    print("[PMO] Enterprise responsive theme patch loaded.")


def _wire_workspace_overrides() -> None:
    try:
        scan_v3 = importlib.import_module("scan_workspace_v3")
        roadmap_v3 = importlib.import_module("roadmap_workspace_v3")
        asset_v2 = importlib.import_module("asset_management_workspace_v2")
        reports_v1 = importlib.import_module("reports_workspace")
        original_scan = importlib.import_module("project_scan_workspace")
        original_roadmap = importlib.import_module("roadmap_workspace")
    except Exception as exc:
        print(f"[PMO] Workspace override patch skipped: {exc}")
        return

    def routed_scan_workspace():
        actual_engine = st.session_state.get("_pmo_actual_engine", "🚀 Scan Project")
        if actual_engine == "🧾 Asset Management":
            return asset_v2.render_asset_management_workspace_v2()
        if actual_engine == "📈 Reports":
            return reports_v1.render_reports_workspace()
        return scan_v3.render_scan_workspace_v3()

    original_scan.render_project_scan_workspace = routed_scan_workspace
    original_scan.build_scan_pdf_report = _safe_build_scan_pdf_report
    original_roadmap.render_roadmap_workspace = roadmap_v3.render_roadmap_workspace_v3
    original_roadmap.build_roadmap_pdf = _safe_build_roadmap_pdf

    scan_proxy = types.ModuleType("project_scan_workspace")
    scan_proxy.__dict__.update(original_scan.__dict__)
    scan_proxy.render_project_scan_workspace = routed_scan_workspace
    scan_proxy.build_scan_pdf_report = _safe_build_scan_pdf_report

    roadmap_proxy = types.ModuleType("roadmap_workspace")
    roadmap_proxy.__dict__.update(original_roadmap.__dict__)
    roadmap_proxy.render_roadmap_workspace = roadmap_v3.render_roadmap_workspace_v3
    roadmap_proxy.build_roadmap_pdf = _safe_build_roadmap_pdf

    sys.modules["project_scan_workspace"] = scan_proxy
    sys.modules["roadmap_workspace"] = roadmap_proxy
    print("[PMO] Workspace routing patch loaded.")


def _render_mobile_workspace_switcher() -> None:
    st.caption("Workspace")
    options = ["🚀 Scan Project", "📅 Create RoadMap", "🧾 Asset Management", "📈 Reports"]
    selected = None

    segmented_control = getattr(st, "segmented_control", None)
    if callable(segmented_control):
        try:
            selected = segmented_control(
                "Workspace",
                options,
                key="vx_workspace_switcher",
                selection_mode="single",
                default=st.session_state.get("_pmo_actual_engine", options[0]),
                label_visibility="collapsed",
            )
        except TypeError:
            selected = segmented_control(
                "Workspace",
                options,
                key="vx_workspace_switcher",
                label_visibility="collapsed",
            )
    else:
        selected = st.radio(
            "Workspace",
            options,
            key="vx_workspace_switcher",
            horizontal=True,
            index=options.index(st.session_state.get("_pmo_actual_engine", options[0])),
            label_visibility="collapsed",
        )

    if selected:
        st.session_state["_pmo_actual_engine"] = selected


def _inject_kanban_breakpoint_bridge() -> None:
    bridge = """
    <script>
    (function () {
      function ensureStyles(doc) {
        if (!doc || !doc.head || doc.getElementById('vertexone-kanban-responsive')) return;
        const style = doc.createElement('style');
        style.id = 'vertexone-kanban-responsive';
        style.textContent = `
          html, body {
            overflow-x: hidden !important;
            max-width: 100% !important;
          }
          [class*="kanban"][class*="board"],
          [class*="board"][class*="grid"],
          [class*="board"][class*="container"],
          [class*="lane"][class*="grid"],
          [class*="lane"][class*="container"],
          [class*="column"][class*="grid"],
          [class*="columns"],
          [class*="lanes"] {
            width: 100% !important;
            max-width: 100% !important;
            min-width: 0 !important;
          }
          [class*="kanban"][class*="board"],
          [class*="board"][class*="grid"],
          [class*="lane"][class*="grid"],
          [class*="columns"],
          [class*="lanes"] {
            display: grid !important;
            grid-template-columns: repeat(4, minmax(0, 1fr)) !important;
            align-items: start !important;
            gap: 10px !important;
          }
          [class*="lane"],
          [class*="column"] {
            min-width: 0 !important;
            width: auto !important;
            max-width: 100% !important;
          }
          [class*="header"],
          [class*="title"] {
            word-break: keep-all !important;
            overflow-wrap: break-word !important;
            hyphens: none !important;
          }
          [class*="card"] {
            min-width: 0 !important;
            max-width: 100% !important;
          }
          @media (max-width: 980px) {
            [class*="kanban"][class*="board"],
            [class*="board"][class*="grid"],
            [class*="lane"][class*="grid"],
            [class*="columns"],
            [class*="lanes"] {
              grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
            }
          }
          @media (max-width: 720px) {
            [class*="kanban"][class*="board"],
            [class*="board"][class*="grid"],
            [class*="lane"][class*="grid"],
            [class*="columns"],
            [class*="lanes"] {
              grid-template-columns: minmax(0, 1fr) !important;
            }
          }
        `;
        doc.head.appendChild(style);
      }

      function patchIframes() {
        const frames = window.parent.document.querySelectorAll('iframe');
        frames.forEach((frame) => {
          try {
            const doc = frame.contentDocument || (frame.contentWindow && frame.contentWindow.document);
            ensureStyles(doc);
          } catch (err) {
          }
        });
      }

      patchIframes();
      setInterval(patchIframes, 1200);
    })();
    </script>
    """
    components.html(bridge, height=0, width=0)


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
_patch_fpdf()
_wire_workspace_overrides()
st.markdown(ENTERPRISE_THEME, unsafe_allow_html=True)
_render_mobile_workspace_switcher()
_inject_kanban_breakpoint_bridge()

runpy.run_path(str(APP_FILE), run_name="__main__")
