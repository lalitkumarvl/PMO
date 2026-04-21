from __future__ import annotations

import copy
import hashlib
import html
import io
import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
import zipfile

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from vertexone_kanban_component import render_vertexone_kanban


STATUS_ORDER = ["To Do", "In Progress", "Review", "Done"]
ENGINE_KEYS = ["scan", "roadmap", "technology", "reports", "ai"]
ENGINE_LABELS = {
    "scan": "Delivery Intelligence",
    "roadmap": "RoadMap Studio",
    "technology": "Technology Lifecycle",
    "reports": "Reports Hub",
    "ai": "AI Copilot",
}
CROSS_ENGINE_SOURCES = {
    "scan": "Delivery Intelligence",
    "roadmap": "RoadMap Studio",
    "technology": "Technology Lifecycle",
}
APP_TITLE = "VertexOne DeliveryOS"
APP_SUBTITLE = "PMO command center for delivery intelligence, roadmap design, governance packs, and AI-guided follow-up."
SNAPSHOT_STORE = Path(__file__).with_name("vertexone_snapshots.json")
LEGACY_SNAPSHOT_STORES = [Path.cwd() / "vertexone_snapshots.json"]

TEAM_LIBRARY = [
    ("UI/UX Design", "2", "Mid", "Anika, Veda", 100, True),
    ("Frontend Development", "3", "Mid", "Rohan, Kiran, Joel", 100, True),
    ("Backend Development", "3", "Senior", "Priya, David, Arun", 100, True),
    ("DevOps", "1", "Senior", "Maya", 75, True),
    ("QA/Testing", "2", "Mid", "John, Meera", 100, True),
    ("Project Manager", "1", "Senior", "Lalit", 100, True),
    ("Product Manager", "1", "Senior", "Nisha", 100, True),
    ("Business Analyst", "1", "Mid", "Kavya", 80, False),
    ("Security / Compliance", "1", "Senior", "Aman", 40, False),
    ("Data Engineering", "1", "Mid", "Sana", 40, False),
]

HOLIDAY_SEED = [
    ("2026-01-01", "New Year"),
    ("2026-01-14", "Pongal"),
    ("2026-01-15", "Thiruvalluvar Day"),
    ("2026-01-16", "Uzhavar Thirunal"),
    ("2026-01-26", "Republic Day"),
    ("2026-04-03", "Good Friday"),
    ("2026-04-14", "Tamil New Year"),
    ("2026-05-01", "Labour Day"),
    ("2026-08-15", "Independence Day"),
    ("2026-08-28", "Vinayakar Chaturthi"),
    ("2026-10-02", "Gandhi Jayanthi"),
    ("2026-10-20", "Deepavali"),
    ("2026-12-25", "Christmas"),
]

TECH_STACK_SEED = [
    ("Salesforce", "Spring '25", "2027-06-30", "CRM Platform", "Program Office", "Project1, Project2"),
    ("Power BI", "2.128", "2026-12-31", "Analytics", "BI Team", "Project1"),
    ("PostgreSQL", "13", "2026-11-13", "Database", "Platform Team", "Project1, Data Hub"),
    ("Camunda", "7.19", "2027-04-01", "Workflow", "Automation Team", "Project2"),
]

ACTION_TRACKER_SEED = [
    ("Review API dependency", "David", "Backend Development", "2026-04-08", "Open", "Dependency", "Project1"),
    ("Confirm UAT environment", "Maya", "DevOps", "2026-04-10", "Open", "Environment", "Project1"),
]

RAID_SEED = [
    ("Risk", "Vendor dependency", "High", "Lalit", "Mitigation in progress", "Project1"),
    ("Issue", "Late environment access", "Medium", "Maya", "Waiting on infra", "Project1"),
    ("Dependency", "API contract sign-off", "High", "Priya", "Business confirmation pending", "Project1"),
]

AD_HOC_SEED = [
    ("Project1", "Ad hoc stakeholder dashboard", "Reporting", "Arun", "Backend Development", "2026-04-12", "To Do", "Medium"),
    ("Project1", "Urgent login defect review", "Production Support", "John", "QA/Testing", "2026-04-06", "In Progress", "High"),
]

MARKET_LIBRARY = [
    {
        "name": "Monday.com",
        "organization": "monday.com",
        "keywords": ["workflow", "planning", "team", "dashboard", "project", "delivery"],
        "differentiator": "Strong work management boards and simple team coordination for cross-functional delivery teams.",
    },
    {
        "name": "Jira",
        "organization": "Atlassian",
        "keywords": ["agile", "scrum", "backlog", "story", "release", "sprint"],
        "differentiator": "Deep agile planning, release tracking, and engineering-aligned workflow configuration.",
    },
    {
        "name": "ServiceNow",
        "organization": "ServiceNow",
        "keywords": ["service", "governance", "workflow", "request", "enterprise", "platform"],
        "differentiator": "Enterprise workflow orchestration with strong governance, approvals, and platform operations.",
    },
    {
        "name": "Zoho Projects",
        "organization": "Zoho",
        "keywords": ["small", "medium", "project", "tracking", "collaboration"],
        "differentiator": "Balanced project tracking with lightweight collaboration and cost-conscious deployment.",
    },
    {
        "name": "Aha!",
        "organization": "Aha! Labs",
        "keywords": ["product", "roadmap", "strategy", "initiative", "feature"],
        "differentiator": "Strong product planning and roadmap communication for product and program teams.",
    },
    {
        "name": "Asana",
        "organization": "Asana",
        "keywords": ["task", "collaboration", "marketing", "coordination", "initiative"],
        "differentiator": "Clear collaboration views and progress communication for business-led teams.",
    },
]

MODULE_SIGNAL_LIBRARY = {
    "Workflow Automation": ["workflow", "approval", "governance", "process", "decision"],
    "Portal / Experience": ["portal", "dashboard", "ui", "ux", "mobile", "web", "screen"],
    "Integration Services": ["api", "integration", "interface", "service", "middleware"],
    "Data & Reporting": ["data", "report", "analytics", "warehouse", "migration", "dashboard"],
    "Security & Compliance": ["security", "compliance", "audit", "access", "policy"],
    "Notification & Communication": ["notification", "alert", "email", "teams", "whatsapp", "message"],
}

SCAN_ALIASES = {
    "Task ID": ["task id", "id", "ticket", "work item id"],
    "Task Name": ["task name", "task", "title", "summary", "feature", "item name"],
    "Status": ["status", "state", "stage"],
    "Owner": ["owner", "resource", "assignee", "assigned to"],
    "Team": ["team", "function", "pod", "department"],
    "Planned Start": ["planned start", "start", "start date", "planned start date", "forecast start"],
    "Planned End": ["planned end", "end", "due date", "planned end date", "finish", "forecast end", "target date"],
    "Actual Start": ["actual start", "actual start date"],
    "Actual End": ["actual end", "actual end date", "completed on"],
    "Dependencies": ["dependencies", "depends on", "dependency", "predecessor"],
    "Percent Complete": ["percent complete", "% complete", "completion", "progress", "done %"],
}


def _serialize_snapshot_value(value: Any) -> Any:
    if isinstance(value, pd.DataFrame):
        return {"__type__": "dataframe", "value": value.to_json(orient="split", date_format="iso")}
    if isinstance(value, pd.Timestamp):
        return {"__type__": "timestamp", "value": value.isoformat()}
    if isinstance(value, datetime):
        return {"__type__": "datetime", "value": value.isoformat()}
    if isinstance(value, date):
        return {"__type__": "date", "value": value.isoformat()}
    if isinstance(value, dict):
        return {str(key): _serialize_snapshot_value(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_serialize_snapshot_value(item) for item in value]
    if hasattr(value, "item") and callable(getattr(value, "item")):
        try:
            return value.item()
        except Exception:
            pass
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _deserialize_snapshot_value(value: Any) -> Any:
    if isinstance(value, dict) and "__type__" in value:
        kind = value["__type__"]
        if kind == "dataframe":
            payload = json.loads(value["value"])
            frame = pd.DataFrame(payload.get("data", []), columns=payload.get("columns", []))
            if "index" in payload:
                frame.index = payload["index"]
            return frame
        if kind in {"timestamp", "datetime"}:
            return pd.to_datetime(value["value"])
        if kind == "date":
            return date.fromisoformat(value["value"])
    if isinstance(value, dict):
        return {key: _deserialize_snapshot_value(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_deserialize_snapshot_value(item) for item in value]
    return value


def load_persisted_snapshots() -> dict[str, list[dict[str, Any]]]:
    defaults = {engine: [] for engine in ENGINE_KEYS}
    store = None
    for candidate in [SNAPSHOT_STORE, *LEGACY_SNAPSHOT_STORES]:
        if candidate.exists():
            store = candidate
            break
    if store is None:
        return defaults
    try:
        raw = json.loads(store.read_text())
        for engine in ENGINE_KEYS:
            items = raw.get(engine, [])
            defaults[engine] = [
                {
                    "label": item.get("label", f"{ENGINE_LABELS[engine]} Snapshot"),
                    "saved_at": item.get("saved_at", ""),
                    "payload": _deserialize_snapshot_value(item.get("payload", {})),
                }
                for item in items
            ]
    except Exception:
        return defaults
    return defaults


def persist_snapshots() -> None:
    payload = {}
    for engine in ENGINE_KEYS:
        payload[engine] = [
            {
                "label": snap.get("label", f"{ENGINE_LABELS[engine]} Snapshot"),
                "saved_at": snap.get("saved_at", ""),
                "payload": _serialize_snapshot_value(snap.get("payload", {})),
            }
            for snap in st.session_state["engine_snapshots"].get(engine, [])
        ]
    serialized = json.dumps(payload, indent=2)
    SNAPSHOT_STORE.write_text(serialized)
    for candidate in LEGACY_SNAPSHOT_STORES:
        if candidate != SNAPSHOT_STORE:
            try:
                candidate.write_text(serialized)
            except Exception:
                continue


def _should_skip_snapshot_entry(key: str, value: Any) -> bool:
    transient_prefixes = (
        "scan_toolbar_",
        "scan_task_editor_",
        "scan_kanban_",
    )
    transient_suffixes = (
        "_save_snapshot",
        "_restore_snapshot",
        "_restore_btn",
        "_delete_snapshot",
        "_save_snapshot_compact",
        "_restore_snapshot_compact",
        "_restore_btn_compact",
        "_delete_snapshot_compact",
        "_snapshot_label_compact",
        "_btn",
        "_compare_snapshot",
        "_snapshot_label",
        "_flash_message",
    )
    if key == "engine_selector" or key.startswith(transient_prefixes) or key.endswith(transient_suffixes):
        return True
    if key in {"scan_selected_task_id", "scan_last_drag_event"}:
        return True
    if "uploader" in key:
        return True
    value_type = type(value).__name__
    value_module = type(value).__module__
    if value_type == "UploadedFile" or "uploaded_file_manager" in value_module:
        return True
    return False


def main() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inject_theme()
    _init_state()
    _apply_pending_restore()
    _render_sidebar()
    _render_top_header()
    engine = st.session_state.get("active_engine", "scan")

    if engine == "scan":
        render_scan_engine()
    elif engine == "roadmap":
        render_roadmap_engine()
    elif engine == "technology":
        render_technology_engine()
    elif engine == "reports":
        render_reports_engine()
    elif engine == "ai":
        render_ai_engine()


def _inject_theme() -> None:
    st.markdown(
        """
        <style>
          :root {
            --vx-bg: #eef4fb;
            --vx-surface: rgba(255,255,255,0.94);
            --vx-border: rgba(17, 44, 74, 0.10);
            --vx-text: #172a46;
            --vx-muted: #6a7690;
            --vx-primary: #2558d6;
            --vx-secondary: #19a4a1;
            --vx-success: #1c8a63;
            --vx-warning: #d39020;
            --vx-danger: #d95368;
            --vx-radius: 18px;
            --vx-shadow: 0 16px 32px rgba(20, 46, 82, 0.08);
          }

          html, body, [data-testid="stAppViewContainer"] {
            background:
              radial-gradient(circle at top right, rgba(37, 88, 214, 0.10), transparent 28%),
              linear-gradient(180deg, #f4f8fd 0%, #edf3fb 100%);
            color: var(--vx-text);
          }

          .block-container {
            padding-top: 0.3rem;
            padding-bottom: 2rem;
            padding-left: 1rem;
            padding-right: 1rem;
          }

          header[data-testid="stHeader"] {
            background: transparent;
          }

          [data-testid="stDecoration"] {
            display: none;
          }

          [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f1f3d 0%, #193764 100%);
            border-right: 1px solid rgba(255,255,255,0.08);
          }

          [data-testid="stSidebar"] * { color: #f5f8ff; }
          [data-testid="stSidebar"] .stRadio label p { white-space: nowrap; }
          [data-testid="stSidebar"] [data-testid="stPopover"] button {
            background: rgba(255,255,255,0.10) !important;
            border: 1px solid rgba(255,255,255,0.16) !important;
            border-radius: 14px !important;
            box-shadow: none !important;
            color: #f5f8ff !important;
            font-weight: 700 !important;
          }
          [data-testid="stSidebar"] [data-testid="stPopover"] button * {
            color: #f5f8ff !important;
          }
          [data-testid="stSidebar"] [data-testid="stPopover"] button:hover,
          [data-testid="stSidebar"] [data-testid="stPopover"] button:focus,
          [data-testid="stSidebar"] [data-testid="stPopover"] button:focus-visible {
            background: rgba(255,255,255,0.18) !important;
            border-color: rgba(255,255,255,0.28) !important;
            color: #ffffff !important;
          }
          [data-testid="stSidebar"] [data-testid="stPopover"] button:hover *,
          [data-testid="stSidebar"] [data-testid="stPopover"] button:focus *,
          [data-testid="stSidebar"] [data-testid="stPopover"] button:focus-visible * {
            color: #ffffff !important;
          }

          .vx-hero {
            background: linear-gradient(135deg, #10203f 0%, #2457d6 100%);
            color: white;
            border-radius: 24px;
            padding: 1.35rem 1.4rem;
            box-shadow: 0 20px 44px rgba(17, 39, 72, 0.18);
            margin-bottom: 1rem;
          }
          .vx-hero h1 {
            margin: 0;
            font-size: clamp(1.6rem, 2.8vw, 2.65rem);
            line-height: 1.05;
          }
          .vx-hero p {
            margin: 0.55rem 0 0;
            max-width: 76ch;
            color: rgba(255,255,255,0.88);
            font-size: 1rem;
          }
          .vx-about {
            background: linear-gradient(135deg, rgba(16, 32, 63, 0.96) 0%, rgba(36, 87, 214, 0.96) 100%);
            border-radius: 24px;
            color: white;
            margin-top: 1.4rem;
            padding: 1.2rem 1.25rem 1.3rem;
            box-shadow: 0 18px 38px rgba(17, 39, 72, 0.16);
          }
          .vx-about h3 {
            margin: 0 0 0.35rem;
            font-size: 1.45rem;
          }
          .vx-about p {
            color: rgba(255,255,255,0.84);
            margin: 0 0 0.95rem;
          }
          .vx-about-grid {
            display: grid;
            gap: 0.85rem;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            margin-top: 0.9rem;
          }
          .vx-about-card {
            background: rgba(255,255,255,0.12);
            border: 1px solid rgba(255,255,255,0.14);
            border-radius: 18px;
            padding: 0.95rem 0.95rem 0.9rem;
          }
          .vx-about-card h4 {
            font-size: 0.9rem;
            letter-spacing: 0.06em;
            margin: 0 0 0.55rem;
            text-transform: uppercase;
          }
          .vx-about-card ul {
            margin: 0;
            padding-left: 1rem;
          }
          .vx-about-card li {
            color: rgba(255,255,255,0.88);
            line-height: 1.45;
            margin: 0.18rem 0;
          }
          .vx-eyebrow {
            text-transform: uppercase;
            letter-spacing: 0.18em;
            font-size: 0.74rem;
            font-weight: 700;
            opacity: 0.78;
            margin-bottom: 0.5rem;
          }
          .vx-card, div[data-testid="stMetric"] {
            background: var(--vx-surface);
            border: 1px solid var(--vx-border);
            border-radius: var(--vx-radius);
            box-shadow: var(--vx-shadow);
          }
          .stButton > button, div[data-testid="stDownloadButton"] > button {
            min-height: 2.8rem;
            border-radius: 14px;
            border: 1px solid rgba(37, 88, 214, 0.12);
            background: linear-gradient(135deg, #ffffff 0%, #f7fbff 100%);
            color: var(--vx-text);
            font-weight: 600;
          }
          .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #2558d6 0%, #19a4a1 100%);
            color: white;
            border-color: transparent;
          }
          [data-baseweb="tab-list"] {
            gap: 0.45rem;
            flex-wrap: wrap;
            border-bottom: 1px solid var(--vx-border);
            padding-bottom: 0.6rem;
          }
          button[data-baseweb="tab"] {
            border-radius: 999px;
            padding: 0.68rem 1rem;
            background: rgba(255,255,255,0.72);
            border: 1px solid rgba(37, 88, 214, 0.10);
          }
          button[data-baseweb="tab"][aria-selected="true"] {
            background: linear-gradient(135deg, #2558d6 0%, #477be8 100%);
            color: white;
            border-color: transparent;
          }
          .vx-source-banner {
            background: linear-gradient(135deg, rgba(37, 88, 214, 0.08) 0%, rgba(25, 164, 161, 0.08) 100%);
            border: 1px solid rgba(37, 88, 214, 0.12);
            border-radius: 16px;
            color: #46607f;
            margin: 0.2rem 0 1rem;
            padding: 0.8rem 0.95rem;
          }
          .vx-about-panel {
            background: linear-gradient(180deg, #ffffff 0%, #f6f9fe 100%);
            border: 1px solid rgba(17, 44, 74, 0.10);
            border-radius: 16px;
            color: #172a46;
            min-width: 18rem;
            padding: 0.95rem 1rem 1rem;
          }
          .vx-about-panel h4 {
            color: #172a46;
            font-size: 1rem;
            font-weight: 800;
            margin: 0 0 0.65rem;
          }
          .vx-about-label {
            color: #5f6f88;
            font-size: 0.73rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            margin-bottom: 0.25rem;
            text-transform: uppercase;
          }
          .vx-about-panel ul {
            color: #304865;
            margin: 0 0 0.75rem 1rem;
            padding: 0;
          }
          .vx-about-panel li {
            line-height: 1.45;
            margin: 0.14rem 0;
          }
          .vx-lane-shell {
            background: rgba(255,255,255,0.72);
            border: 1px solid rgba(17, 44, 74, 0.08);
            border-radius: 20px;
            box-shadow: var(--vx-shadow);
            min-height: 100%;
            padding: 0.8rem;
          }
          .vx-lane-head {
            border-radius: 18px;
            margin-bottom: 0.85rem;
            padding: 0.95rem 1rem 0.85rem;
          }
          .vx-lane-head h4 {
            font-size: 0.94rem;
            font-weight: 800;
            letter-spacing: 0.06em;
            margin: 0 0 0.45rem;
            text-transform: uppercase;
          }
          .vx-lane-head .vx-lane-value {
            font-size: 2.25rem;
            font-weight: 900;
            line-height: 1;
            margin-bottom: 0.2rem;
          }
          .vx-lane-head .vx-lane-count {
            color: #667791;
            font-size: 0.98rem;
            font-weight: 700;
          }
          .vx-lane-head.todo { box-shadow: inset 0 -5px 0 #6b7a90; }
          .vx-lane-head.inprogress { box-shadow: inset 0 -5px 0 #2558d6; }
          .vx-lane-head.review { box-shadow: inset 0 -5px 0 #d39020; }
          .vx-lane-head.done { box-shadow: inset 0 -5px 0 #1c8a63; }
          .vx-task-card {
            background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
            border: 1px solid rgba(17, 44, 74, 0.08);
            border-left: 5px solid #2558d6;
            border-radius: 18px;
            box-shadow: 0 12px 24px rgba(20, 46, 82, 0.08);
            margin-bottom: 0.75rem;
            padding: 0.9rem 0.95rem;
          }
          .vx-task-card.todo { border-left-color: #6b7a90; }
          .vx-task-card.inprogress { border-left-color: #2558d6; }
          .vx-task-card.review { border-left-color: #d39020; }
          .vx-task-card.done { border-left-color: #1c8a63; }
          .vx-task-id {
            color: #73839c;
            font-size: 0.78rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            margin-bottom: 0.2rem;
            text-transform: uppercase;
          }
          .vx-task-title {
            color: #172a46;
            font-size: 1.16rem;
            font-weight: 800;
            line-height: 1.2;
            margin-bottom: 0.65rem;
          }
          .vx-task-grid {
            display: grid;
            gap: 0.45rem 0.8rem;
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }
          .vx-task-meta {
            display: flex;
            flex-direction: column;
            gap: 0.12rem;
          }
          .vx-task-meta span {
            color: #7f8ca2;
            font-size: 0.76rem;
            font-weight: 700;
            letter-spacing: 0.05em;
            text-transform: uppercase;
          }
          .vx-task-meta strong {
            color: #23324f;
            font-size: 0.95rem;
            font-weight: 700;
          }
          .vx-task-chips {
            display: flex;
            flex-wrap: wrap;
            gap: 0.4rem;
            margin-top: 0.7rem;
          }
          .vx-chip {
            background: rgba(37, 88, 214, 0.08);
            border: 1px solid rgba(37, 88, 214, 0.12);
            border-radius: 999px;
            color: #32527a;
            font-size: 0.78rem;
            font-weight: 700;
            padding: 0.26rem 0.55rem;
          }
          .vx-empty-lane {
            border: 1px dashed rgba(114, 128, 153, 0.26);
            border-radius: 18px;
            color: #8290a6;
            font-size: 0.96rem;
            font-weight: 700;
            padding: 1.5rem 0.9rem;
            text-align: center;
          }
          @media (max-width: 920px) {
            .block-container {
              padding-left: 0.7rem;
              padding-right: 0.7rem;
            }
            button[data-baseweb="tab"] {
              width: 100%;
              justify-content: center;
            }
            .vx-about-grid {
              grid-template-columns: repeat(2, minmax(0, 1fr));
            }
            .vx-task-grid {
              grid-template-columns: 1fr;
            }
          }
          @media (max-width: 640px) {
            .vx-about-grid {
              grid-template-columns: 1fr;
            }
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _apply_pending_restore() -> None:
    pending = st.session_state.pop("_pending_restore", None)
    if not pending:
        return
    engine_key = pending.get("engine")
    payload = pending.get("payload", {})
    for key, value in payload.items():
        st.session_state[key] = clone_value(value)
    if engine_key == "scan":
        if "scan_projects" in st.session_state:
            st.session_state["scan_projects"] = {
                name: sanitize_scan_runtime_df(df, name)
                for name, df in st.session_state["scan_projects"].items()
            }
            available = list(st.session_state["scan_projects"].keys())
            if available and st.session_state.get("scan_selected_project") not in available:
                st.session_state["scan_selected_project"] = available[0]
            st.session_state["scan_history"] = st.session_state.get("scan_history", {})
            st.session_state["scan_future"] = st.session_state.get("scan_future", {})
        st.session_state["scan_ui_version"] = st.session_state.get("scan_ui_version", 0) + 1


def _init_state() -> None:
    persisted_snapshots = load_persisted_snapshots()
    defaults: dict[str, Any] = {
        "active_engine": "scan",
        "engine_snapshots": persisted_snapshots,
        "engine_meta": {
            engine: {"owner": "", "status": "Draft", "decision": ""}
            for engine in ENGINE_KEYS
        },
        "scan_projects": {"Project1": _default_scan_df("Project1"), "Project2": _default_scan_df("Project2", alt=True)},
        "scan_raw_projects": {},
        "scan_source_headers": {},
        "scan_source_header_map": {},
        "scan_display_label_overrides": {},
        "scan_relevant_projects": [],
        "scan_supporting_projects": [],
        "scan_sheet_intelligence": {},
        "scan_selected_project": "Project1",
        "scan_selected_task_id": "",
        "scan_history": {},
        "scan_future": {},
        "scan_ui_version": 0,
        "roadmap_scope_text": "",
        "roadmap_project_name": "VertexOne DeliveryOS Enhancement",
        "roadmap_project_description": "Build an enterprise PMO dashboard for project tracking, roadmap planning, governance reporting, and AI-guided follow-up.",
        "roadmap_duration_days": 90,
        "roadmap_start_date": date(2026, 4, 6),
        "roadmap_doc_register": pd.DataFrame(columns=["Document", "Type", "Signal", "Extraction Status"]),
        "roadmap_doc_signature": "",
        "roadmap_doc_analysis": {},
        "roadmap_doc_excerpt": "",
        "roadmap_doc_notice": "",
        "roadmap_doc_updated_sections": pd.DataFrame(columns=["Area", "Section", "Auto-populated"]),
        "roadmap_team_allocation": _default_team_df(),
        "roadmap_holiday_calendar": _default_holiday_df(),
        "roadmap_dev_approach": _default_development_df(),
        "roadmap_tasks": _default_roadmap_tasks(),
        "tech_lifecycle_df": _default_technology_df(),
        "reports_action_tracker": _default_action_tracker_df(),
        "reports_raid": _default_raid_df(),
        "reports_source_engine": "scan",
        "reports_context_project": "Project1",
        "shared_ad_hoc_requests": _default_ad_hoc_df(),
        "ai_source_engine": "scan",
        "ai_context_project": "Project1",
        "ai_notes": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _render_sidebar() -> None:
    with st.sidebar:
        st.markdown(
            f"""
            <div style="padding:0.3rem 0 1rem;">
              <div style="font-size:2rem;font-weight:800;">{APP_TITLE}</div>
              <div style="color:rgba(245,248,255,0.82);line-height:1.55;margin-top:0.4rem;">
                {APP_SUBTITLE}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("### Base")
        st.caption("Core enterprise modules")
        selected = st.radio(
            "Base Modules",
            options=list(ENGINE_LABELS.keys()),
            format_func=lambda key: ENGINE_LABELS[key],
            index=list(ENGINE_LABELS.keys()).index(st.session_state.get("active_engine", "scan")),
            key="engine_selector",
        )
        st.session_state["active_engine"] = selected
        st.markdown("---")
        st.caption("Snapshots, approvals, and decision notes are managed inside each engine.")
        with st.popover("About VertexOne", use_container_width=True):
            st.markdown(
                """
                <div class="vx-about-panel">
                  <div class="vx-about-label">About The Product</div>
                  <h4>VertexOne DeliveryOS</h4>
                  <p style="color:#3b4e6b; margin:0 0 0.85rem; line-height:1.55;">
                    Enterprise delivery workspace for PMO, Project, Product, and Program teams to scan project plans,
                    build roadmaps, monitor lifecycle risk, generate reports, and use AI-guided operational support.
                  </p>
                  <div class="vx-about-label">Platform Stack</div>
                  <ul>
                    <li>Streamlit application shell</li>
                    <li>Pandas data normalization</li>
                    <li>Plotly executive charts</li>
                    <li>Custom Kanban component</li>
                  </ul>
                  <div class="vx-about-label">Core Product Views</div>
                  <ul>
                    <li>Delivery Intelligence for AI-led intake, Kanban, and delivery intelligence</li>
                    <li>RoadMap Studio for scope, planning inputs, and timeline design</li>
                    <li>Technology Lifecycle for version, support, and upgrade exposure</li>
                    <li>Reports Hub and AI Copilot for governance, summaries, and meeting support</li>
                  </ul>
                  <div class="vx-about-label">Management Terms</div>
                  <ul>
                    <li>Flow health, delivery velocity, and milestone readiness</li>
                    <li>RAID, approvals, action ownership, and stakeholder reporting</li>
                    <li>Lifecycle risk, upgrade exposure, and planning impact</li>
                    <li>Snapshots, exports, and audit-friendly operational views</li>
                  </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _render_top_header() -> None:
    st.markdown(
        f"""
        <section class="vx-hero">
          <div class="vx-eyebrow">Enterprise Delivery Workspace</div>
          <h1>{APP_TITLE}</h1>
          <p>{APP_SUBTITLE}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_about_footer() -> None:
    st.markdown(
        f"""
        <section class="vx-about">
          <div class="vx-eyebrow">About This POC</div>
          <h3>About {APP_TITLE}</h3>
          <p>
            Management-ready delivery workspace for project intake, roadmap design, lifecycle governance,
            reporting, and AI-assisted follow-up. This footer is intended as a quick POC reference for
            reviewers during demos and pilot discussions.
          </p>
          <div class="vx-about-grid">
            <div class="vx-about-card">
              <h4>Platform Stack</h4>
              <ul>
                <li>Streamlit application shell</li>
                <li>Pandas-driven data normalization</li>
                <li>Plotly executive charts</li>
                <li>Custom Kanban component</li>
              </ul>
            </div>
            <div class="vx-about-card">
              <h4>Operating Engines</h4>
              <ul>
                <li>Scan Project</li>
                <li>Create RoadMap</li>
                <li>Technology Lifecycle</li>
                <li>Reports and AI Consultant</li>
              </ul>
            </div>
            <div class="vx-about-card">
              <h4>Management Terms</h4>
              <ul>
                <li>Flow health and delivery velocity</li>
                <li>Critical path and milestone readiness</li>
                <li>RAID, action ownership, approvals</li>
                <li>Lifecycle risk and upgrade exposure</li>
              </ul>
            </div>
            <div class="vx-about-card">
              <h4>POC Review Focus</h4>
              <ul>
                <li>File intake and project switching</li>
                <li>Kanban movement and reporting flow</li>
                <li>Roadmap feasibility and timeline output</li>
                <li>Export, snapshots, and governance views</li>
              </ul>
            </div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_scan_engine() -> None:
    st.markdown(
        """
        <div style="display:flex; align-items:flex-end; justify-content:space-between; gap:1rem; margin:0 0 0.55rem;">
          <div>
            <div class="vx-eyebrow" style="color:#5f6f88; margin-bottom:0.2rem;">Base • AI-layered execution workspace</div>
            <h2 style="margin:0;">Delivery Intelligence</h2>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _render_scan_upload_panel()
    _render_project_sheet_selector()
    _render_advanced_column_mapping()
    _render_scan_snapshot_tools("scan", "scan")
    _render_scan_ai_brief()
    selected_view = st.radio(
        "Delivery Workspace",
        options=["Live Kanban", "Management View", "Delivery Insights"],
        horizontal=True,
        key="scan_workspace_view",
        label_visibility="collapsed",
    )
    if selected_view == "Live Kanban":
        _render_kanban_workspace()
    elif selected_view == "Management View":
        _render_management_view()
    else:
        _render_delivery_insights()


def render_roadmap_engine() -> None:
    _engine_header("roadmap", "Create RoadMap", "Move from business requirement or uploaded documents to a defensible roadmap, timeline, and feasibility view.")
    _render_engine_meta_tools("roadmap")
    _render_snapshot_tools("roadmap")
    tabs = st.tabs(["Quick Scope Assessment", "Project Details", "Document Intake", "Planning Inputs", "Task & Timeline"])
    with tabs[0]:
        _render_quick_scope_assessment()
    with tabs[1]:
        _render_project_details()
    with tabs[2]:
        _render_document_intake()
    with tabs[3]:
        _render_planning_inputs()
    with tabs[4]:
        _render_task_and_timeline()


def render_technology_engine() -> None:
    _engine_header("technology", "Technology Lifecycle", "Track software versions, support windows, and delivery risk from aging platforms without turning this into a heavy ITSM tool.")
    _render_engine_meta_tools("technology")
    _render_snapshot_tools("technology")
    tabs = st.tabs(["Lifecycle Register", "Risk View", "Impact View"])
    with tabs[0]:
        df = st.session_state["tech_lifecycle_df"]
        st.session_state["tech_lifecycle_df"] = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="tech_register_editor")
    with tabs[1]:
        _render_technology_risk_view()
    with tabs[2]:
        _render_technology_impact_view()


def render_reports_engine() -> None:
    _engine_header("reports", "Reports", "Build PMO-ready output packs, action trackers, RAID views, and ad hoc work visibility from live project context.")
    _render_engine_meta_tools("reports")
    _render_snapshot_tools("reports")
    source_engine, context_project = _render_cross_engine_context_controls("reports")
    tabs = st.tabs(["Project Summary", "Stakeholder Update", "Governance Pack", "Action Tracker", "RAID Summary", "Ad Hoc Tracker"])
    with tabs[0]:
        _render_project_summary_report(source_engine, context_project)
    with tabs[1]:
        _render_stakeholder_update(source_engine, context_project)
    with tabs[2]:
        _render_governance_pack(source_engine, context_project)
    with tabs[3]:
        _render_action_tracker(source_engine, context_project)
    with tabs[4]:
        _render_raid_summary(source_engine, context_project)
    with tabs[5]:
        _render_ad_hoc_tracker(source_engine, context_project)


def render_ai_engine() -> None:
    _engine_header("ai", "AI Consultant", "Give PMO teams fast summaries, meeting preparation, and agile guidance without forcing them to write prompts from scratch.")
    _render_engine_meta_tools("ai")
    _render_snapshot_tools("ai")
    source_engine, context_project = _render_cross_engine_context_controls("ai")
    tabs = st.tabs(["Summary Studio", "Meeting Copilot", "Agile Coach"])
    with tabs[0]:
        _render_summary_studio(source_engine, context_project)
    with tabs[1]:
        _render_meeting_copilot(source_engine, context_project)
    with tabs[2]:
        _render_agile_coach(source_engine, context_project)


def _engine_header(engine_key: str, title: str, description: str) -> None:
    st.markdown(
        f"""
        <div class="vx-card" style="padding:1rem 1.15rem 1.05rem; margin-bottom:0.9rem;">
          <div class="vx-eyebrow" style="color:#5f6f88;">{ENGINE_LABELS[engine_key]}</div>
          <h2 style="margin:0;">{title}</h2>
          <p style="margin:0.55rem 0 0; color:#5f6f88;">{description}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_engine_meta_tools(engine_key: str) -> None:
    meta = st.session_state["engine_meta"][engine_key]
    cols = st.columns([1, 1, 2])
    with cols[0]:
        meta["owner"] = st.text_input("Review Owner", value=meta.get("owner", ""), key=f"{engine_key}_owner")
    with cols[1]:
        meta["status"] = st.selectbox("Approval Status", ["Draft", "In Review", "Approved"], index=["Draft", "In Review", "Approved"].index(meta.get("status", "Draft")), key=f"{engine_key}_status")
    with cols[2]:
        meta["decision"] = st.text_input("Decision Log", value=meta.get("decision", ""), key=f"{engine_key}_decision")
    st.session_state["engine_meta"][engine_key] = meta


def _render_snapshot_tools(engine_key: str) -> None:
    snapshot_label = st.text_input("Snapshot Label", value="", key=f"{engine_key}_snapshot_label", placeholder="Optional snapshot name")
    snapshots = st.session_state["engine_snapshots"][engine_key]
    snapshot_options = ["Current state"] + [snap["label"] for snap in snapshots]
    cols = st.columns([1, 1, 1, 1])
    with cols[0]:
        if st.button("💾 Save Snapshot", key=f"{engine_key}_save_snapshot"):
            save_snapshot(engine_key, snapshot_label or f"{ENGINE_LABELS[engine_key]} {datetime.now().strftime('%d %b %H:%M')}")
            st.session_state[f"{engine_key}_flash_message"] = "Snapshot saved."
            st.rerun()
    with cols[1]:
        selected_restore = st.selectbox("Saved Snapshots", snapshot_options, key=f"{engine_key}_restore_snapshot")
    with cols[2]:
        if st.button("⟲ Restore", key=f"{engine_key}_restore_btn") and selected_restore != "Current state":
            restore_snapshot(engine_key, selected_restore)
            st.session_state[f"{engine_key}_flash_message"] = f"Restored {selected_restore}."
            st.rerun()
    with cols[3]:
        if st.button("🗑 Delete Snapshot", key=f"{engine_key}_delete_snapshot") and selected_restore != "Current state":
            delete_snapshot(engine_key, selected_restore)
            st.session_state[f"{engine_key}_flash_message"] = f"Deleted {selected_restore}."
            st.rerun()

    flash_key = f"{engine_key}_flash_message"
    if st.session_state.get(flash_key):
        st.success(st.session_state.pop(flash_key))

    if snapshots:
        with st.expander("Compare Current vs Previous"):
            selected_compare = st.selectbox(
                "Compare with",
                [snap["label"] for snap in snapshots],
                key=f"{engine_key}_compare_snapshot",
            )
            compare_df = compare_snapshot(engine_key, selected_compare)
            st.dataframe(compare_df, use_container_width=True, hide_index=True)


def _render_scan_snapshot_tools(engine_key: str, base_prefix: str) -> None:
    snapshots = st.session_state["engine_snapshots"][engine_key]
    snapshot_options = ["Current state"] + [snap["label"] for snap in snapshots]
    controls = st.columns([1.15, 1.55, 0.8, 0.8, 0.9])
    with controls[0]:
        snapshot_label = st.text_input(
            "Save",
            value="",
            key=f"{engine_key}_snapshot_label_compact",
            placeholder="Save view name",
            label_visibility="collapsed",
        )
    with controls[1]:
        selected_restore = st.selectbox(
            "Saved Views",
            snapshot_options,
            key=f"{engine_key}_restore_snapshot_compact",
            label_visibility="collapsed",
        )
    with controls[2]:
        if st.button("Save", key=f"{engine_key}_save_snapshot_compact", type="primary"):
            save_snapshot(engine_key, snapshot_label or f"{ENGINE_LABELS[engine_key]} {datetime.now().strftime('%d %b %H:%M')}")
            st.session_state[f"{engine_key}_flash_message"] = "Saved current workspace view."
            st.rerun()
    with controls[3]:
        if st.button("Restore", key=f"{engine_key}_restore_btn_compact", disabled=selected_restore == "Current state"):
            restore_snapshot(engine_key, selected_restore)
            st.session_state[f"{engine_key}_flash_message"] = f"Restored {selected_restore}."
            st.rerun()
    with controls[4]:
        if st.button("Delete", key=f"{engine_key}_delete_snapshot_compact", disabled=selected_restore == "Current state"):
            delete_snapshot(engine_key, selected_restore)
            st.session_state[f"{engine_key}_flash_message"] = f"Deleted {selected_restore}."
            st.rerun()

    flash_key = f"{engine_key}_flash_message"
    if st.session_state.get(flash_key):
        st.success(st.session_state.pop(flash_key))
    with st.popover("Notes", use_container_width=True):
        _render_engine_meta_tools(engine_key)


def save_snapshot(engine_key: str, label: str) -> None:
    prefixes = engine_prefixes(engine_key)
    payload = {}
    for key in list(st.session_state.keys()):
        if any(key.startswith(prefix) for prefix in prefixes):
            value = st.session_state[key]
            if _should_skip_snapshot_entry(key, value):
                continue
            payload[key] = clone_value(value)
    st.session_state["engine_snapshots"][engine_key].insert(
        0,
        {
            "label": label,
            "saved_at": datetime.now().isoformat(),
            "payload": payload,
        },
    )
    st.session_state["engine_snapshots"][engine_key] = st.session_state["engine_snapshots"][engine_key][:7]
    persist_snapshots()


def restore_snapshot(engine_key: str, label: str) -> None:
    for snap in st.session_state["engine_snapshots"][engine_key]:
        if snap["label"] == label:
            filtered_payload = {
                key: clone_value(value)
                for key, value in snap["payload"].items()
                if not _should_skip_snapshot_entry(key, value)
            }
            st.session_state["_pending_restore"] = {
                "engine": engine_key,
                "payload": filtered_payload,
            }
            break


def delete_snapshot(engine_key: str, label: str) -> None:
    st.session_state["engine_snapshots"][engine_key] = [
        snap for snap in st.session_state["engine_snapshots"][engine_key]
        if snap["label"] != label
    ]
    persist_snapshots()


def compare_snapshot(engine_key: str, label: str) -> pd.DataFrame:
    current = {}
    prefixes = engine_prefixes(engine_key)
    for key in list(st.session_state.keys()):
        if any(key.startswith(prefix) for prefix in prefixes):
            current[key] = summarize_value(st.session_state[key])
    previous = {}
    for snap in st.session_state["engine_snapshots"][engine_key]:
        if snap["label"] == label:
            previous = {key: summarize_value(value) for key, value in snap["payload"].items()}
            break
    keys = sorted(set(current) | set(previous))
    rows = []
    for key in keys:
        rows.append({"Item": key, "Current": current.get(key, "-"), "Snapshot": previous.get(key, "-")})
    return pd.DataFrame(rows)


def engine_prefixes(engine_key: str) -> list[str]:
    mapping = {
        "scan": ["scan_"],
        "roadmap": ["roadmap_"],
        "technology": ["tech_"],
        "reports": ["reports_", "shared_ad_hoc_requests"],
        "ai": ["ai_"],
    }
    return mapping[engine_key]


def clone_value(value: Any) -> Any:
    if isinstance(value, pd.DataFrame):
        return value.copy()
    if isinstance(value, dict):
        return {k: clone_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clone_value(v) for v in value]
    return copy.deepcopy(value)


def summarize_value(value: Any) -> str:
    if isinstance(value, pd.DataFrame):
        return f"{len(value)} row(s) x {len(value.columns)} col(s)"
    if isinstance(value, dict):
        return f"{len(value)} item(s)"
    if isinstance(value, list):
        return f"{len(value)} item(s)"
    if isinstance(value, (date, datetime)):
        return str(value)
    return str(value)


def _render_scan_upload_panel() -> None:
    intake_cols = st.columns([1.4, 1])
    with intake_cols[0]:
        uploaded = st.file_uploader(
            "Upload workbook",
            type=["xlsx", "xls", "csv"],
            key="scan_uploader",
            label_visibility="collapsed",
        )
    with intake_cols[1]:
        relevant_count = len(st.session_state.get("scan_relevant_projects", []))
        current_count = len(st.session_state.get("scan_projects", {}))
        if current_count:
            st.markdown(
                f"""
                <div class="vx-card" style="padding:0.7rem 0.9rem; min-height:2.95rem; display:flex; align-items:center;">
                  <strong style="color:#23324f;">AI-ready sheets:</strong>&nbsp;
                  <span style="color:#5f6f88;">{relevant_count or current_count} primary • {max(current_count - (relevant_count or current_count), 0)} supporting</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
    if uploaded is not None:
        projects, raw_projects, source_headers, source_header_map = parse_uploaded_project_file(uploaded)
        if projects:
            sheet_intelligence, relevant_projects, supporting_projects = infer_scan_sheet_intelligence(
                raw_projects,
                source_header_map,
            )
            st.session_state["scan_projects"] = projects
            st.session_state["scan_raw_projects"] = raw_projects
            st.session_state["scan_source_headers"] = source_headers
            st.session_state["scan_source_header_map"] = source_header_map
            st.session_state["scan_sheet_intelligence"] = sheet_intelligence
            st.session_state["scan_relevant_projects"] = relevant_projects
            st.session_state["scan_supporting_projects"] = supporting_projects
            st.session_state["scan_selected_project"] = (relevant_projects or list(projects.keys()))[0]
            st.session_state["scan_history"] = {name: [] for name in projects}
            st.session_state["scan_future"] = {name: [] for name in projects}
            st.session_state["scan_ui_version"] = st.session_state.get("scan_ui_version", 0) + 1
            st.success(f"{uploaded.name} loaded. AI selected {len(relevant_projects) or len(projects)} primary sheet(s).")


def _render_project_sheet_selector() -> None:
    project_names = list(st.session_state["scan_projects"].keys())
    if not project_names:
        st.info("Upload a file to begin.")
        return
    relevant_projects = st.session_state.get("scan_relevant_projects") or project_names
    supporting_projects = st.session_state.get("scan_supporting_projects") or []
    selector_row = st.columns([1.4, 0.8, 0.8])
    with selector_row[1]:
        show_all = st.toggle(
            "All Sheets",
            value=False,
            key="scan_show_all_sheets",
            help="AI keeps project-ready sheets in focus by default. Turn this on only when you need supporting workbook sheets.",
        )
    selector_options = project_names if show_all else [name for name in relevant_projects if name in project_names]
    if not selector_options:
        selector_options = project_names
    resolved = _resolve_scan_project_name(st.session_state.get("scan_selected_project"))
    if resolved not in selector_options:
        resolved = selector_options[0]
    with selector_row[0]:
        st.session_state["scan_selected_project"] = st.selectbox(
            "Project View",
            selector_options,
            index=selector_options.index(resolved),
            key="scan_project_selector",
            label_visibility="collapsed",
        )
    intelligence = st.session_state.get("scan_sheet_intelligence", {})
    current_sheet_info = intelligence.get(st.session_state["scan_selected_project"], {})
    if current_sheet_info:
        with selector_row[2]:
            st.markdown(
                f"""
                <div class="vx-card" style="padding:0.7rem 0.85rem; min-height:2.95rem; display:flex; align-items:center; justify-content:center;">
                  <span style="color:#5f6f88;">{current_sheet_info.get('confidence', 'Review')} confidence</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
    if supporting_projects and not show_all:
        st.caption(f"Showing project-ready sheets first. {len(supporting_projects)} supporting sheet(s) are hidden unless `All Sheets` is enabled.")
    headers = st.session_state.get("scan_source_headers", {}).get(st.session_state["scan_selected_project"], [])
    header_map = st.session_state.get("scan_source_header_map", {}).get(st.session_state["scan_selected_project"], {})
    if headers:
        with st.popover("Sheet Details", use_container_width=True):
            sheet_rows = []
            for sheet_name in project_names:
                info = intelligence.get(sheet_name, {})
                sheet_rows.append(
                    {
                        "Workbook Sheet": sheet_name,
                        "AI Selection": "Primary" if sheet_name in relevant_projects else "Supporting",
                        "Confidence": info.get("confidence", "Review"),
                        "Reason": info.get("reason", "Header and task pattern review"),
                        "Rows": info.get("rows", len(st.session_state["scan_projects"].get(sheet_name, pd.DataFrame()))),
                    }
                )
            st.dataframe(pd.DataFrame(sheet_rows), width="stretch", hide_index=True)
            st.write(" • ".join(headers))
            if header_map:
                mapping_df = pd.DataFrame(
                    [{"PMO Field": canonical, "Uploaded Header": source} for canonical, source in header_map.items()]
                )
                st.dataframe(mapping_df, width="stretch", hide_index=True)


def _render_advanced_column_mapping() -> None:
    project_name = _current_scan_project_name()
    raw_df = st.session_state.get("scan_raw_projects", {}).get(project_name)
    available_headers = st.session_state.get("scan_source_headers", {}).get(project_name, [])
    if raw_df is None or not available_headers:
        return
    show_mapping = st.toggle(
        "Show advanced column mapping",
        value=False,
        key=f"scan_show_advanced_mapping_{project_name}",
        help="Map uploaded sheet headers to PMO fields when the inferred structure needs correction.",
    )
    if not show_mapping:
        return
    current_map = st.session_state.get("scan_source_header_map", {}).get(project_name, {})
    fields = [
        ("Task ID", "Task ID"),
        ("Task Name", "Task Name"),
        ("Planned Start", "Planned Start"),
        ("Planned End", "Planned End"),
        ("Actual Start", "Actual Start"),
        ("Actual End", "Actual End"),
        ("Owner", "Owner / Resource"),
        ("Team", "Team"),
        ("Status", "Status"),
        ("Dependencies", "Dependencies"),
        ("Percent Complete", "% Complete"),
    ]
    options = [""] + list(available_headers)
    with st.expander("Advanced Column Mapping (Optional)", expanded=True):
        cols = st.columns(3)
        selected_map: dict[str, str] = {}
        for idx, (canonical, label) in enumerate(fields):
            current_value = current_map.get(canonical, "")
            safe_value = current_value if current_value in options else ""
            selected_map[canonical] = cols[idx % 3].selectbox(
                label,
                options,
                index=options.index(safe_value),
                key=f"scan_mapping_{project_name}_{canonical}",
            )
        chosen = [value for value in selected_map.values() if value]
        duplicates = sorted({value for value in chosen if chosen.count(value) > 1})
        if duplicates:
            st.warning(f"Each uploaded header can only be mapped once. Resolve duplicates: {', '.join(duplicates)}")
        if st.button("Apply Mapping", key=f"scan_apply_mapping_{project_name}", type="primary", disabled=bool(duplicates)):
            cleaned_map = {canonical: value for canonical, value in selected_map.items() if value}
            st.session_state["scan_source_header_map"][project_name] = cleaned_map
            normalized = normalize_scan_df(raw_df.copy(), project_name, cleaned_map)
            st.session_state["scan_projects"][project_name] = sanitize_scan_runtime_df(normalized, project_name)
            st.session_state["scan_history"][project_name] = []
            st.session_state["scan_future"][project_name] = []
            st.session_state["scan_ui_version"] = st.session_state.get("scan_ui_version", 0) + 1
            st.success("Column mapping applied. Task Table, Kanban, Management View, and Delivery Insights now use the selected headers.")
            st.rerun()


def _render_scan_table_layout_controls(df: pd.DataFrame) -> None:
    project_name = _current_scan_project_name()
    internal_to_display, _ = build_scan_display_metadata(df, project_name)
    saved_visible_key = f"scan_task_table_visible_columns_saved_{project_name}"
    widget_visible_key = f"scan_task_table_visible_columns_widget_{project_name}"
    with st.expander("Column Setup", expanded=True):
        st.caption(
            "Use this saved setup area to choose visible columns, rename headers, and keep the same layout after Apply Table Changes. "
            "The table header menu only sorts or hides columns temporarily."
        )
        visible_internal_columns = [column for column in df.columns if column != "Lane Order"]
        stored_visible = st.session_state.get(saved_visible_key, visible_internal_columns)
        safe_visible = [value for value in stored_visible if value in visible_internal_columns]
        if not safe_visible:
            safe_visible = visible_internal_columns
        visible_columns = st.multiselect(
            "Visible columns",
            options=visible_internal_columns,
            default=safe_visible,
            format_func=lambda column: internal_to_display.get(column, column),
            key=widget_visible_key,
        )
        st.caption("Editable column labels")
        label_rows = []
        label_overrides = st.session_state.get("scan_display_label_overrides", {}).get(project_name, {})
        for internal in visible_internal_columns:
            label_rows.append(
                {
                    "Internal Column": internal,
                    "Source Header": internal_to_display[internal],
                    "Display Label": label_overrides.get(internal, internal_to_display[internal]),
                }
            )
        label_df = pd.DataFrame(label_rows)
        edited_labels = st.data_editor(
            label_df,
            width="stretch",
            hide_index=True,
            num_rows="fixed",
            key=f"scan_label_editor_{project_name}",
            disabled=["Internal Column", "Source Header"],
        )
        action_cols = st.columns(4)
        with action_cols[0]:
            if st.button("Apply Table Layout", key=f"scan_apply_layout_{project_name}", type="primary"):
                overrides: dict[str, str] = {}
                for internal, row in zip(visible_internal_columns, edited_labels.to_dict(orient="records")):
                    label = str(row.get("Display Label", "")).strip()
                    source = internal_to_display[internal]
                    if label and label != source:
                        overrides[internal] = label
                st.session_state.setdefault("scan_display_label_overrides", {})[project_name] = overrides
                st.session_state[saved_visible_key] = visible_columns or visible_internal_columns
                st.session_state["scan_ui_version"] = st.session_state.get("scan_ui_version", 0) + 1
                st.success("Table layout saved.")
                st.rerun()
        with action_cols[1]:
            if st.button("✦ Save View", key=f"scan_layout_save_view_{project_name}"):
                save_snapshot("scan", f"{project_name} view {datetime.now().strftime('%d %b %H:%M')}")
                st.success("Scan view saved.")
                st.rerun()
        with action_cols[2]:
            if st.button("↶ Undo", key=f"scan_layout_undo_{project_name}", disabled=not bool(st.session_state["scan_history"].get(project_name))):
                if _undo_scan_history(project_name):
                    st.rerun()
        with action_cols[3]:
            if st.button("↷ Redo", key=f"scan_layout_redo_{project_name}", disabled=not bool(st.session_state["scan_future"].get(project_name))):
                if _redo_scan_history(project_name):
                    st.rerun()


def _resolve_scan_project_name(project_name: str | None = None) -> str:
    projects = list(st.session_state["scan_projects"].keys())
    if not projects:
        st.session_state["scan_projects"] = {"Project1": _default_scan_df("Project1")}
        projects = ["Project1"]
    selected = project_name or st.session_state.get("scan_selected_project") or projects[0]
    if selected not in projects:
        selected = projects[0]
    st.session_state["scan_selected_project"] = selected
    for context_key in ("reports_context_project", "ai_context_project"):
        current = st.session_state.get(context_key)
        if current not in projects:
            st.session_state[context_key] = selected
    return selected


def current_scan_df(project_name: str | None = None) -> pd.DataFrame:
    selected = _resolve_scan_project_name(project_name)
    sanitized = sanitize_scan_runtime_df(st.session_state["scan_projects"][selected], selected)
    st.session_state["scan_projects"][selected] = sanitized
    return sanitized


def current_filtered_scan_df(project_name: str | None = None) -> pd.DataFrame:
    selected = _resolve_scan_project_name(project_name)
    return apply_scan_filters(current_scan_df(selected).copy(), "scan_global", render_controls=False)


def update_current_scan_df(df: pd.DataFrame) -> None:
    project_name = _resolve_scan_project_name(st.session_state.get("scan_selected_project"))
    st.session_state["scan_projects"][project_name] = sanitize_scan_runtime_df(df, project_name)
    st.session_state["scan_ui_version"] = st.session_state.get("scan_ui_version", 0) + 1


def _current_scan_project_name() -> str:
    return _resolve_scan_project_name(st.session_state.get("scan_selected_project"))


def _push_scan_history(project_name: str, df: pd.DataFrame) -> None:
    history = st.session_state["scan_history"].setdefault(project_name, [])
    history.insert(0, clone_value(df))
    st.session_state["scan_history"][project_name] = history[:12]
    st.session_state["scan_future"][project_name] = []


def _undo_scan_history(project_name: str) -> bool:
    history = st.session_state["scan_history"].setdefault(project_name, [])
    if not history:
        return False
    current_df = clone_value(st.session_state["scan_projects"][project_name])
    future = st.session_state["scan_future"].setdefault(project_name, [])
    future.insert(0, current_df)
    st.session_state["scan_projects"][project_name] = history.pop(0)
    st.session_state["scan_ui_version"] = st.session_state.get("scan_ui_version", 0) + 1
    return True


def _redo_scan_history(project_name: str) -> bool:
    future = st.session_state["scan_future"].setdefault(project_name, [])
    if not future:
        return False
    current_df = clone_value(st.session_state["scan_projects"][project_name])
    history = st.session_state["scan_history"].setdefault(project_name, [])
    history.insert(0, current_df)
    st.session_state["scan_projects"][project_name] = future.pop(0)
    st.session_state["scan_ui_version"] = st.session_state.get("scan_ui_version", 0) + 1
    return True


def _build_scan_export_bytes() -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for project_name, frame in st.session_state["scan_projects"].items():
            export_df = frame.copy()
            if "Lane Order" in export_df.columns:
                export_df = export_df.drop(columns=["Lane Order"])
            export_df.to_excel(writer, sheet_name=str(project_name)[:31], index=False)
    output.seek(0)
    return output.getvalue()


def _cell_scalar(value: Any) -> Any:
    if isinstance(value, pd.Series):
        compact = value.dropna()
        if not compact.empty:
            return compact.iloc[0]
        return value.iloc[0] if len(value) else ""
    return value


def source_header_label(project_name: str, canonical: str) -> str:
    header_map = st.session_state.get("scan_source_header_map", {}).get(project_name, {})
    return header_map.get(canonical, canonical)


def build_scan_display_metadata(df: pd.DataFrame, project_name: str) -> tuple[dict[str, str], dict[str, str]]:
    header_map = st.session_state.get("scan_source_header_map", {}).get(project_name, {})
    label_overrides = st.session_state.get("scan_display_label_overrides", {}).get(project_name, {})
    desired_labels: list[str] = []
    internal_columns = list(df.columns)
    for column in internal_columns:
        override_label = label_overrides.get(column)
        if override_label and str(override_label).strip():
            desired_labels.append(str(override_label).strip())
        else:
            source_label = header_map.get(column)
            if source_label and str(source_label).strip():
                desired_labels.append(str(source_label).strip())
            else:
                desired_labels.append(str(column))
    unique_labels = make_unique_column_names(desired_labels)
    internal_to_display = dict(zip(internal_columns, unique_labels))
    display_to_internal = {display: internal for internal, display in internal_to_display.items()}
    return internal_to_display, display_to_internal


def order_scan_display_df(df: pd.DataFrame, project_name: str) -> pd.DataFrame:
    internal_to_display, _ = build_scan_display_metadata(df, project_name)
    display_df = df.rename(columns=internal_to_display)
    source_headers = st.session_state.get("scan_source_headers", {}).get(project_name, [])
    ordered_columns: list[str] = []
    for header in source_headers:
        mapped_candidates = [display for internal, display in internal_to_display.items() if display == header]
        for display in mapped_candidates:
            if display in display_df.columns and display not in ordered_columns:
                ordered_columns.append(display)
    for display in display_df.columns:
        if display not in ordered_columns:
            ordered_columns.append(display)
    return display_df[ordered_columns]


def build_task_table_display(df: pd.DataFrame, project_name: str, selected_internal: list[str]) -> tuple[pd.DataFrame, dict[str, str]]:
    header_map = st.session_state.get("scan_source_header_map", {}).get(project_name, {})
    label_overrides = st.session_state.get("scan_display_label_overrides", {}).get(project_name, {})
    ordered_internal: list[str] = []
    source_headers = st.session_state.get("scan_source_headers", {}).get(project_name, [])
    for header in source_headers:
        for internal in selected_internal:
            preferred = label_overrides.get(internal) or header_map.get(internal) or internal
            if preferred == header and internal not in ordered_internal:
                ordered_internal.append(internal)
    for internal in selected_internal:
        if internal not in ordered_internal:
            ordered_internal.append(internal)
    labels: list[str] = []
    for internal in ordered_internal:
        preferred = label_overrides.get(internal) or header_map.get(internal) or internal
        labels.append(str(preferred).strip() if str(preferred).strip() else internal)
    visible_labels = make_unique_column_names(labels)
    display_to_internal = dict(zip(visible_labels, ordered_internal))
    display_df = df[ordered_internal].copy()
    display_df.columns = visible_labels
    return display_df, display_to_internal


def get_active_scan_filter_values(project_name: str | None = None) -> dict[str, list[str]]:
    selected = _resolve_scan_project_name(project_name)
    df = current_scan_df(selected).copy()
    candidate_columns: list[str] = []
    for column in df.columns:
        if column == "Lane Order":
            continue
        unique_count = df[column].dropna().astype(str).nunique()
        if 1 < unique_count <= 40:
            candidate_columns.append(column)
    active_cols = st.session_state.get(f"scan_global_filter_columns_{selected}", [])
    active_cols = [column for column in active_cols if column in candidate_columns]
    filters: dict[str, list[str]] = {}
    for column in active_cols:
        values = st.session_state.get(f"scan_global_{column}_filter_{selected}", [])
        if values:
            filters[column] = values
    return filters


def apply_scan_filters(
    df: pd.DataFrame,
    prefix: str,
    render_controls: bool = True,
    candidate_override: list[str] | None = None,
) -> pd.DataFrame:
    project_name = _current_scan_project_name()
    internal_to_display, _ = build_scan_display_metadata(df, project_name)
    candidate_columns: list[str] = []
    candidate_source = candidate_override or list(df.columns)
    for column in candidate_source:
        if column == "Lane Order":
            continue
        if column not in df.columns:
            continue
        series = df[column]
        unique_count = series.dropna().astype(str).nunique()
        if 1 < unique_count <= 40:
            candidate_columns.append(column)
    if not candidate_columns:
        return df
    default_columns = [
        column for column in ["Status", "Team", "Owner"] if column in candidate_columns
    ] or candidate_columns[: min(3, len(candidate_columns))]
    stored_columns = st.session_state.get(f"{prefix}_filter_columns_{project_name}", default_columns)
    safe_active_cols = [column for column in stored_columns if column in candidate_columns]
    if not safe_active_cols:
        safe_active_cols = default_columns

    if render_controls:
        with st.expander("Excel-Style Value Filters", expanded=True):
            st.caption(
                "Select a visible workbook header such as Dependency, Status, Owner, or Team, then choose the actual values "
                "present in that column. The same filtered context feeds Management View, Delivery Insights, Reports, and AI Consultant."
            )
            active_cols = st.multiselect(
                "Filter columns",
                options=candidate_columns,
                default=safe_active_cols,
                format_func=lambda column: internal_to_display.get(column, column),
                key=f"{prefix}_filter_columns_{project_name}",
            )
            if not active_cols:
                st.info("Select one or more columns to drive the downstream views.")
                return df
            cols = st.columns(min(len(active_cols), 3))
            for idx, canonical in enumerate(active_cols):
                options = sorted(df[canonical].dropna().astype(str).unique().tolist())
                label = internal_to_display.get(canonical, canonical)
                stored_values = st.session_state.get(f"{prefix}_{canonical}_filter_{project_name}", [])
                safe_values = [value for value in stored_values if value in options]
                cols[idx % len(cols)].multiselect(
                    label,
                    options,
                    default=safe_values,
                    key=f"{prefix}_{canonical}_filter_{project_name}",
                )

    active_cols = st.session_state.get(f"{prefix}_filter_columns_{project_name}", safe_active_cols)
    active_cols = [column for column in active_cols if column in candidate_columns]
    filtered = df.copy()
    for canonical in active_cols:
        values = st.session_state.get(f"{prefix}_{canonical}_filter_{project_name}", [])
        if values:
            filtered = filtered[filtered[canonical].astype(str).isin(values)]
    if render_controls:
        active_summary = []
        for canonical in active_cols:
            values = st.session_state.get(f"{prefix}_{canonical}_filter_{project_name}", [])
            if values:
                active_summary.append(f"{internal_to_display.get(canonical, canonical)}: {', '.join(values[:3])}{' ...' if len(values) > 3 else ''}")
        if active_summary:
            st.info(f"Active filters -> {' | '.join(active_summary)}")
        if len(filtered) != len(df):
            st.info(f"Filtered view: {len(filtered)} of {len(df)} task(s) shown.")
    return filtered


def _render_cross_engine_context_controls(prefix: str) -> tuple[str, str | None]:
    cols = st.columns([1.8, 1.2])
    with cols[0]:
        source_engine = st.radio(
            "Operate From",
            options=list(CROSS_ENGINE_SOURCES.keys()),
            format_func=lambda key: CROSS_ENGINE_SOURCES[key],
            horizontal=True,
            key=f"{prefix}_source_engine",
        )
    context_project = None
    with cols[1]:
        if source_engine == "scan":
            projects = list(st.session_state["scan_projects"].keys())
            if not projects:
                st.caption("No scanned projects loaded")
                return source_engine, None
            default_project = _resolve_scan_project_name(st.session_state.get(f"{prefix}_context_project"))
            context_project = st.selectbox(
                "Project Context",
                projects,
                index=projects.index(default_project),
                key=f"{prefix}_context_project",
            )
        elif source_engine == "roadmap":
            st.caption(st.session_state["roadmap_project_name"])
        else:
            st.caption(f"{len(st.session_state['tech_lifecycle_df'])} lifecycle item(s)")
    if source_engine == "scan" and context_project:
        st.markdown(
            f"<div class='vx-source-banner'><strong>Operating From:</strong> {CROSS_ENGINE_SOURCES[source_engine]} • <strong>Project:</strong> {context_project}</div>",
            unsafe_allow_html=True,
        )
    elif source_engine == "roadmap":
        st.markdown(
            f"<div class='vx-source-banner'><strong>Operating From:</strong> {CROSS_ENGINE_SOURCES[source_engine]} • <strong>Planned Window:</strong> {st.session_state['roadmap_duration_days']} working day(s)</div>",
            unsafe_allow_html=True,
        )
    else:
        high_risk = int((evaluate_tech_lifecycle(st.session_state["tech_lifecycle_df"])["Risk Status"] == "High").sum())
        st.markdown(
            f"<div class='vx-source-banner'><strong>Operating From:</strong> {CROSS_ENGINE_SOURCES[source_engine]} • <strong>High Risk Items:</strong> {high_risk}</div>",
            unsafe_allow_html=True,
        )
    return source_engine, context_project


def _render_scan_action_toolbar(df: pd.DataFrame) -> None:
    project_name = _current_scan_project_name()
    history_available = bool(st.session_state["scan_history"].get(project_name))
    redo_available = bool(st.session_state["scan_future"].get(project_name))
    export_bytes = _build_scan_export_bytes()
    cols = st.columns([1, 1, 1, 1.1, 1.1])
    with cols[0]:
        if st.button("↶ Undo", key="scan_toolbar_undo", disabled=not history_available, type="secondary"):
            if _undo_scan_history(project_name):
                st.rerun()
    with cols[1]:
        if st.button("↷ Redo", key="scan_toolbar_redo", disabled=not redo_available, type="secondary"):
            if _redo_scan_history(project_name):
                st.rerun()
    with cols[2]:
        if st.button("✦ Save View", key="scan_toolbar_save", type="primary"):
            save_snapshot("scan", f"{project_name} view {datetime.now().strftime('%d %b %H:%M')}")
            st.success("Current scan view saved.")
    with cols[3]:
        with st.popover("Board Settings", use_container_width=True):
            st.caption("Keep display preferences here so the Kanban stays focused on work and AI signals.")
            st.slider(
                "Lane Height",
                min_value=360,
                max_value=1200,
                value=int(st.session_state.get("scan_kanban_lane_height", 620)),
                step=40,
                key="scan_kanban_lane_height",
            )
            st.info("Custom Kanban stages are feasible and can be enabled next as a project-level workflow designer.")
    with cols[4]:
        st.download_button(
            "📊 Extract Excel",
            data=export_bytes,
            file_name=f"{project_name.lower().replace(' ', '_')}_scan_export.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="scan_toolbar_export",
            width="stretch",
        )


def _render_review_action_queue(df: pd.DataFrame) -> None:
    review_df = df[(df["Status"] == "Review") | (df["Due Risk"] == "Overdue")].copy()
    st.markdown("### AI Attention Queue")
    if review_df.empty:
        st.info("No immediate AI attention signals were detected in the current delivery flow.")
    else:
        preview = review_df[["Task ID", "Task Name", "Owner", "Planned Start", "Planned End", "Status", "Due Risk"]].copy()
        preview["Planned Start"] = preview["Planned Start"].map(format_date)
        preview["Planned End"] = preview["Planned End"].map(format_date)
        preview["AI Action"] = preview.apply(
            lambda row: "Escalate today" if row["Due Risk"] == "Overdue" else "Close review feedback",
            axis=1,
        )
        st.dataframe(preview, width="stretch", hide_index=True)

    adhoc_df = st.session_state["shared_ad_hoc_requests"].copy()
    open_adhoc = adhoc_df[adhoc_df["Status"] != "Done"].copy()
    if not open_adhoc.empty:
        st.markdown("#### AI Follow-up on Ad Hoc Requests")
        followup = open_adhoc[["Project", "Request", "Owner", "Team", "Due Date", "Status", "Priority"]].copy()
        followup["Due Date"] = followup["Due Date"].map(format_date)
        st.dataframe(followup, width="stretch", hide_index=True)


def _render_kanban_workspace() -> None:
    df = current_scan_df().copy()
    metrics = build_status_metrics(df)
    _render_scan_action_toolbar(df)
    task_payload = []
    working_df = df.copy()
    working_df["Task ID"] = working_df["Task ID"].astype(str)
    if "Lane Order" not in working_df.columns:
        working_df["Lane Order"] = range(len(working_df))
    working_df = working_df.sort_values(["Status", "Lane Order", "Planned End", "Task ID"]).reset_index(drop=True)
    for _, row in working_df.iterrows():
        task_id = _cell_scalar(row["Task ID"])
        task_name = _cell_scalar(row["Task Name"])
        status = _cell_scalar(row["Status"])
        owner = _cell_scalar(row["Owner"])
        team = _cell_scalar(row["Team"])
        planned_start = _cell_scalar(row["Planned Start"])
        planned_end = _cell_scalar(row["Planned End"])
        due_risk = _cell_scalar(row["Due Risk"])
        percent_complete = _cell_scalar(row["Percent Complete"])
        task_payload.append(
            {
                "task_id": str(task_id),
                "task_name": str(task_name),
                "status": str(status),
                "owner": str(owner),
                "team": str(team),
                "planned_start": format_date(planned_start),
                "planned_end": format_date(planned_end),
                "due_risk": format_due_signal(due_risk),
                "percent_complete": int(percent_complete) if pd.notna(percent_complete) else 0,
            }
        )
    board_col, detail_col = st.columns([2.35, 1], gap="large")
    with board_col:
        kanban_state = render_vertexone_kanban(
            task_payload,
            metrics,
            lane_body_height=int(st.session_state.get("scan_kanban_lane_height", 620)),
            key=f"scan_kanban_{st.session_state['scan_selected_project']}",
        )
    with detail_col:
        _render_task_intelligence_panel(current_scan_df().copy())
    if isinstance(kanban_state, str):
        try:
            kanban_state = json.loads(kanban_state)
        except Exception:
            kanban_state = None
    if kanban_state and isinstance(kanban_state, dict):
        last_event = st.session_state.get("scan_last_drag_event")
        event_id = kanban_state.get("event_id")
        event_type = kanban_state.get("event_type", "move")
        updates = kanban_state.get("tasks", [])
        selected_task_id = kanban_state.get("selected_task_id")
        if event_id and event_id != last_event and event_type == "select" and selected_task_id:
            st.session_state["scan_selected_task_id"] = str(selected_task_id)
            st.session_state["scan_last_drag_event"] = event_id
            st.rerun()
        if event_id and event_id != last_event and updates:
            status_map = {item["task_id"]: item["status"] for item in updates}
            order_map = {item["task_id"]: item.get("lane_order", idx) for idx, item in enumerate(updates)}
            _push_scan_history(_current_scan_project_name(), df)
            df["Task ID"] = df["Task ID"].astype(str)
            df["Status"] = df["Task ID"].map(status_map).fillna(df["Status"])
            df["Lane Order"] = df["Task ID"].map(order_map).fillna(df.get("Lane Order", pd.Series([9999] * len(df), index=df.index)))
            df["Percent Complete"] = df.apply(
                lambda row: 100 if row["Status"] == "Done" else min(int(row["Percent Complete"]), 90) if pd.notna(row["Percent Complete"]) else 0,
                axis=1,
            )
            df["Due Risk"] = df.apply(compute_due_risk, axis=1)
            update_current_scan_df(df)
            st.session_state["scan_last_drag_event"] = event_id
            st.rerun()

    with st.expander("Task Table"):
        df = ensure_unique_dataframe_columns(df)
        project_name = _current_scan_project_name()
        _render_scan_table_layout_controls(df)
        visible_internal_columns = [column for column in df.columns if column != "Lane Order"]
        stored_visible_internal = st.session_state.get(f"scan_task_table_visible_columns_saved_{project_name}", visible_internal_columns)
        selected_internal = [column for column in stored_visible_internal if column in visible_internal_columns]
        if not selected_internal:
            selected_internal = visible_internal_columns
        filtered_df = apply_scan_filters(df.copy(), "scan_global", render_controls=True, candidate_override=selected_internal)
        display_df, display_to_internal = build_task_table_display(filtered_df, project_name, selected_internal)
        st.caption(
            "Uploaded source headers are shown where mapped. Use Column Setup to save visible columns and editable labels. "
            "Use Excel-Style Value Filters to narrow the task view by the actual values present in visible workbook columns, and the same filtered context will drive Management View, Delivery Insights, Reports, and AI Consultant."
        )
        editor_key = f"scan_task_editor_{_current_scan_project_name()}_{st.session_state.get('scan_ui_version', 0)}"
        edited_display = st.data_editor(
            display_df,
            width="stretch",
            num_rows="fixed",
            key=editor_key,
        )
        table_action_cols = st.columns([1, 1, 1, 4])
        with table_action_cols[0]:
            add_table_row = st.button("Add Task Row", key=f"{editor_key}_add")
        with table_action_cols[1]:
            apply_table_changes = st.button("Apply Table Changes", key=f"{editor_key}_apply", type="primary")
        with table_action_cols[2]:
            reset_table_changes = st.button("Reset Table View", key=f"{editor_key}_reset")
        if add_table_row:
            new_row = {column: pd.NA for column in df.columns}
            new_row["Project"] = project_name
            new_row["Task ID"] = f"T{len(df) + 1:03d}"
            new_row["Task Name"] = "New Task"
            new_row["Status"] = "To Do"
            new_row["Owner"] = "Unassigned"
            new_row["Team"] = "General Delivery"
            new_row["Percent Complete"] = 0
            new_row["Planned Start"] = pd.Timestamp(date.today())
            new_row["Planned End"] = pd.Timestamp(date.today()) + pd.Timedelta(days=2)
            new_row["Due Risk"] = "On Track"
            extended = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            _push_scan_history(_current_scan_project_name(), current_scan_df().copy())
            update_current_scan_df(extended)
            st.success("New task row added.")
            st.rerun()
        if reset_table_changes:
            st.session_state["scan_ui_version"] = st.session_state.get("scan_ui_version", 0) + 1
            st.rerun()
        if apply_table_changes:
            edited = df.copy()
            restored_display = edited_display.rename(columns=display_to_internal)
            for column in restored_display.columns:
                edited.loc[restored_display.index, column] = restored_display[column]
            if "Lane Order" in edited.columns:
                edited = edited.drop(columns=["Lane Order"])
            _push_scan_history(_current_scan_project_name(), current_scan_df().copy())
            update_current_scan_df(edited)
            st.success("Task Table updates applied to the live scan view.")
            st.rerun()

    with st.expander("AI Attention Queue", expanded=False):
        _render_review_action_queue(current_scan_df().copy())


def _render_management_view() -> None:
    df = apply_scan_filters(current_scan_df().copy(), "scan_global", render_controls=False)
    util_df = build_resource_utilization(df)
    headline = st.columns(4)
    headline[0].metric("Tasks In Flow", int(df["Status"].isin(["In Progress", "Review"]).sum()))
    headline[1].metric("Overdue Tasks", int((df["Due Risk"] == "Overdue").sum()))
    headline[2].metric("Overloaded Owners", int((util_df["Utilization Status"] == "Overloaded").sum()))
    headline[3].metric("Balanced Owners", int((util_df["Utilization Status"] == "Balanced").sum()))

    chart_cols = st.columns(2)
    with chart_cols[0]:
        status_counts = df["Status"].value_counts().reindex(STATUS_ORDER, fill_value=0).reset_index()
        status_counts.columns = ["Status", "Count"]
        fig = px.pie(
            status_counts,
            names="Status",
            values="Count",
            hole=0.52,
            title="Project Portfolio Status",
            color="Status",
            color_discrete_map=status_palette(),
        )
        configure_chart(fig)
        fig.update_traces(
            hovertemplate="<b>%{label}</b><br>Tasks: %{value}<br>Share: %{percent}<extra></extra>"
        )
        st.plotly_chart(fig, use_container_width=True)
    with chart_cols[1]:
        owner_df = df.groupby(["Status", "Owner"]).size().reset_index(name="Count")
        if owner_df.empty:
            owner_df = pd.DataFrame({"Status": ["To Do"], "Owner": ["Unassigned"], "Count": [0]})
        fig = px.sunburst(
            owner_df,
            path=["Status", "Owner"],
            values="Count",
            color="Status",
            title="Status by Owner",
            color_discrete_map=status_palette(),
        )
        configure_chart(fig)
        fig.update_traces(
            hovertemplate="<b>%{label}</b><br>Tasks: %{value}<extra></extra>"
        )
        st.plotly_chart(fig, use_container_width=True)

    lower_cols = st.columns(2)
    with lower_cols[0]:
        fig = px.bar(
            util_df,
            y="Owner",
            x="Active Tasks",
            color="Utilization Status",
            title="Resource Utilization",
            orientation="h",
            color_discrete_map={
                "Balanced": "#19a4a1",
                "Watch": "#d39020",
                "Overloaded": "#d95368",
            },
        )
        configure_chart(fig)
        fig.update_layout(xaxis_title="Open work items", yaxis_title="")
        fig.update_traces(
            hovertemplate="<b>%{y}</b><br>Open Work: %{x}<br>Utilization: %{customdata[0]}<extra></extra>",
            customdata=util_df[["Utilization Status"]],
        )
        st.plotly_chart(fig, use_container_width=True)
    with lower_cols[1]:
        mitigation_df = util_df.sort_values(["Overdue Tasks", "Active Tasks"], ascending=[False, False]).copy()
        mitigation_df["Mitigation Action"] = mitigation_df.apply(
            lambda row: "Escalate overdue closure" if row["Overdue Tasks"] > 0 else "Rebalance active load" if row["Utilization Status"] == "Overloaded" else "Monitor",
            axis=1,
        )
        fig = px.bar(
            mitigation_df,
            y="Owner",
            x="Overdue Tasks",
            color="Mitigation Action",
            title="Mitigation Attention",
            orientation="h",
            color_discrete_map={
                "Escalate overdue closure": "#d95368",
                "Rebalance active load": "#d39020",
                "Monitor": "#19a4a1",
            },
        )
        configure_chart(fig)
        fig.update_layout(xaxis_title="Items needing closure", yaxis_title="")
        fig.update_traces(
            hovertemplate="<b>%{y}</b><br>Overdue: %{x}<br>Action: %{customdata[0]}<extra></extra>",
            customdata=mitigation_df[["Mitigation Action"]],
        )
        st.plotly_chart(fig, use_container_width=True)

    util_view = util_df.copy()
    util_view["Management Action"] = util_view.apply(
        lambda row: "Escalate overdue tasks" if row["Overdue Tasks"] > 0 else "Review allocation" if row["Utilization Status"] == "Overloaded" else "Monitor flow",
        axis=1,
    )
    st.markdown("#### Management Readout")
    st.info("Read the utilization status to understand owner load. Use the management action column to decide whether to monitor, rebalance, or escalate overdue delivery.")
    st.dataframe(util_view, use_container_width=True, hide_index=True)


def _render_delivery_insights() -> None:
    df = apply_scan_filters(current_scan_df().copy(), "scan_global", render_controls=False)
    tabs = st.tabs(["Daily Scrum Focus", "Impediment Analysis", "Velocity / Flow Insight", "Dependency Impact", "Milestone Readiness"])
    with tabs[0]:
        st.markdown(generate_daily_scrum(df))
    with tabs[1]:
        st.markdown(generate_impediment_analysis(df))
    with tabs[2]:
        st.markdown(generate_velocity_insight(df))
    with tabs[3]:
        st.markdown(generate_dependency_impact(df))
    with tabs[4]:
        st.markdown(generate_milestone_readiness(df))


def _render_quick_scope_assessment() -> None:
    st.session_state["roadmap_scope_text"] = st.text_area(
        "Enter requirement or scope statement",
        value=st.session_state["roadmap_scope_text"],
        height=170,
        placeholder="Example: Build an integrated PMO dashboard that tracks projects, delivery status, roadmap readiness, risks, and stakeholder updates.",
    )
    if st.button("Analyze Scope", type="primary"):
        st.session_state["roadmap_scope_analysis"] = analyze_requirement_text(st.session_state["roadmap_scope_text"])
        generated_tasks = generate_tasks_from_scope(st.session_state["roadmap_scope_analysis"])
        if not generated_tasks.empty:
            st.session_state["roadmap_tasks"] = generated_tasks
    analysis = st.session_state.get("roadmap_scope_analysis")
    if analysis:
        cols = st.columns(4)
        cols[0].metric("Complexity", analysis["complexity"])
        cols[1].metric("Timeline Range", analysis["timeline"])
        cols[2].metric("Teams Needed", len(analysis["teams"]))
        cols[3].metric("Existing Flow Impact", analysis["impact"])
        st.markdown("**Recommended Teams**")
        st.write(", ".join(analysis["teams"]))
        st.markdown("**Pain Points**")
        st.write(" • ".join(analysis["pain_points"]))
        st.markdown("**Expected Outputs**")
        st.write(" • ".join(analysis["outputs"]))


def _render_project_details() -> None:
    if st.session_state.get("roadmap_doc_signature"):
        st.info("AI-suggested values from Document Intake are active here. Review the project description, duration, and market comparison before finalizing.")
    cols = st.columns(4)
    with cols[0]:
        st.session_state["roadmap_project_name"] = st.text_input("Project Name", value=st.session_state["roadmap_project_name"])
    with cols[1]:
        st.session_state["roadmap_duration_days"] = st.number_input("Project Duration (working days)", min_value=5, max_value=365, value=int(st.session_state["roadmap_duration_days"]))
    with cols[2]:
        st.session_state["roadmap_start_date"] = st.date_input("Project Start Date", value=st.session_state["roadmap_start_date"])
    with cols[3]:
        projected_end = add_working_days(
            st.session_state["roadmap_start_date"],
            int(st.session_state["roadmap_duration_days"]),
            holiday_dates(st.session_state["roadmap_holiday_calendar"]),
        )
        st.metric("Projected End Date", projected_end.strftime("%d %b %Y"))

    st.session_state["roadmap_project_description"] = st.text_area(
        "Project Description",
        value=st.session_state["roadmap_project_description"],
        height=130,
    )

    summary_df = pd.DataFrame(
        [
            ("Selected Start Date", st.session_state["roadmap_start_date"].strftime("%d %b %Y")),
            ("Projected End Date", projected_end.strftime("%d %b %Y")),
            ("Planned Working Days", st.session_state["roadmap_duration_days"]),
            ("Configured Holidays", len(st.session_state["roadmap_holiday_calendar"])),
        ],
        columns=["Metric", "Value"],
    )
    st.markdown("**Project Summary**")
    st.dataframe(summary_df, use_container_width=True, hide_index=True)

    comparison_df = market_comparison(st.session_state["roadmap_project_description"])
    st.markdown("**Market Comparison**")
    st.dataframe(comparison_df, use_container_width=True, hide_index=True)


def _render_document_intake() -> None:
    uploads = st.file_uploader(
        "Upload BRD / FRD / TRD / SRS / Design documents",
        accept_multiple_files=True,
        key="roadmap_doc_uploader",
    )
    if uploads:
        signature = upload_signature(uploads)
        if signature != st.session_state.get("roadmap_doc_signature"):
            register_rows: list[tuple[str, str, str, str]] = []
            documents: list[dict[str, Any]] = []
            for upload in uploads:
                doc_type = detect_document_type(upload.name)
                signal = infer_document_signal(upload.name)
                extracted_text, extraction_status, extraction_reason = extract_uploaded_document_text(upload)
                register_rows.append((upload.name, doc_type, signal, extraction_status))
                documents.append(
                    {
                        "document": upload.name,
                        "type": doc_type,
                        "signal": signal,
                        "status": extraction_status,
                        "reason": extraction_reason,
                        "text": extracted_text,
                    }
                )
            st.session_state["roadmap_doc_register"] = pd.DataFrame(
                register_rows,
                columns=["Document", "Type", "Signal", "Extraction Status"],
            )
            analysis = derive_document_analysis(documents)
            st.session_state["roadmap_doc_analysis"] = analysis
            st.session_state["roadmap_doc_excerpt"] = analysis.get("excerpt", "")
            st.session_state["roadmap_doc_signature"] = signature
            apply_document_analysis_to_roadmap(analysis)
            parsed = analysis.get("parsed_documents", 0)
            low_confidence = analysis.get("low_confidence_documents", 0)
            st.session_state["roadmap_doc_notice"] = (
                f"Upload successful. {analysis.get('documents_loaded', len(documents))} document(s) processed, "
                f"{parsed} parsed with usable text, {low_confidence} low-confidence. "
                "Project Details, Planning Inputs, and Task & Timeline were auto-populated."
            )
    else:
        st.session_state["roadmap_doc_signature"] = ""
    st.dataframe(st.session_state["roadmap_doc_register"], use_container_width=True, hide_index=True)
    if not st.session_state["roadmap_doc_register"].empty:
        analysis = st.session_state.get("roadmap_doc_analysis", {})
        notice = st.session_state.get("roadmap_doc_notice", "")
        if notice:
            st.success(notice)
        extracted = st.session_state["roadmap_doc_register"].groupby("Type").size().reset_index(name="Count")
        metrics = st.columns(4)
        metrics[0].metric("Documents Loaded", int(analysis.get("documents_loaded", len(st.session_state["roadmap_doc_register"]))))
        metrics[1].metric("Teams Suggested", len(analysis.get("teams", [])))
        metrics[2].metric("Draft Tasks Generated", len(st.session_state.get("roadmap_tasks", pd.DataFrame())))
        metrics[3].metric("Timeline Range", analysis.get("timeline", "Pending"))
        fig = px.bar(extracted, x="Type", y="Count", title="Document Intake Coverage", color="Type")
        configure_chart(fig)
        st.plotly_chart(fig, use_container_width=True)
        if analysis:
            updated_sections = st.session_state.get("roadmap_doc_updated_sections", pd.DataFrame())
            if not updated_sections.empty:
                st.markdown("**Auto-populated Sections**")
                st.dataframe(updated_sections, use_container_width=True, hide_index=True)
            st.markdown("**Detected Modules**")
            st.write(" • ".join(analysis.get("modules", [])))
            st.markdown("**Suggested Teams**")
            st.write(", ".join(analysis.get("teams", [])))
            st.markdown("**Extracted Summary**")
            excerpt = st.session_state.get("roadmap_doc_excerpt", "")
            if analysis.get("parsed_documents", 0) > 0 and excerpt:
                st.info(excerpt)
            else:
                st.warning("Low-confidence document extraction. Suggestions were derived mainly from document names, detected types, and signals. Review Planning Inputs and Task & Timeline before using them.")
            if st.button("Re-apply Document Suggestions", key="roadmap_reapply_doc", type="secondary"):
                apply_document_analysis_to_roadmap(analysis)
                st.success("Document suggestions were reapplied to Planning Inputs and Task & Timeline.")
                st.rerun()


def _render_planning_inputs() -> None:
    if st.session_state.get("roadmap_doc_signature"):
        st.success("Auto-populated from Document Intake. Review the highlighted team and development assumptions, then edit as needed.")
    sub_tabs = st.tabs(["Team Allocation", "Holiday Calendar", "Development Approach"])
    with sub_tabs[0]:
        st.session_state["roadmap_team_allocation"] = st.data_editor(
            st.session_state["roadmap_team_allocation"],
            use_container_width=True,
            num_rows="dynamic",
            key="roadmap_team_editor",
        )
    with sub_tabs[1]:
        st.session_state["roadmap_holiday_calendar"] = st.data_editor(
            st.session_state["roadmap_holiday_calendar"],
            use_container_width=True,
            num_rows="dynamic",
            key="roadmap_holiday_editor",
        )
    with sub_tabs[2]:
        st.session_state["roadmap_dev_approach"] = st.data_editor(
            st.session_state["roadmap_dev_approach"],
            use_container_width=True,
            num_rows="dynamic",
            key="roadmap_dev_editor",
        )


def _render_task_and_timeline() -> None:
    if st.session_state.get("roadmap_doc_signature"):
        st.success("Draft tasks and baseline duration were auto-generated from Document Intake. Refine the task list before confirming the roadmap.")
    subtabs = st.tabs(["Task Input", "Roadmap Table", "Team Timeline", "Feasibility Check"])
    with subtabs[0]:
        st.session_state["roadmap_tasks"] = st.data_editor(
            st.session_state["roadmap_tasks"],
            use_container_width=True,
            num_rows="dynamic",
            key="roadmap_task_editor",
        )
        if st.button("Merge Open Ad Hoc Requests into Roadmap Tasks"):
            merge_ad_hoc_into_roadmap()
            st.success("Open ad hoc requests were added as roadmap tasks.")
            st.rerun()
    with subtabs[1]:
        roadmap_df = build_roadmap_table()
        st.dataframe(roadmap_df, use_container_width=True, hide_index=True)
    with subtabs[2]:
        roadmap_df = build_roadmap_table()
        fig = build_team_timeline_chart(roadmap_df)
        st.plotly_chart(fig, use_container_width=True)
    with subtabs[3]:
        roadmap_df = build_roadmap_table()
        assessment = roadmap_feasibility(roadmap_df)
        cols = st.columns(4)
        cols[0].metric("Feasibility", assessment["status"])
        cols[1].metric("Working Days Needed", assessment["required_days"])
        cols[2].metric("Available Days", assessment["available_days"])
        cols[3].metric("Compression Potential", assessment["compression"])
        st.markdown("**Key Risks**")
        st.write(" • ".join(assessment["risks"]))
        st.markdown("**Recommendation**")
        st.write(assessment["recommendation"])


def _render_technology_risk_view() -> None:
    df = evaluate_tech_lifecycle(st.session_state["tech_lifecycle_df"])
    fig = px.pie(
        df,
        names="Recommendation",
        title="Lifecycle Recommendation Mix",
        hole=0.52,
        color="Recommendation",
        color_discrete_map={
            "Continue": "#19a4a1",
            "Upgrade": "#d39020",
            "Replace": "#d95368",
            "Retire": "#6a7690",
        },
    )
    configure_chart(fig)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df[["Application", "Current Version", "Support End", "Risk Status", "Recommendation"]], use_container_width=True, hide_index=True)


def _render_technology_impact_view() -> None:
    df = evaluate_tech_lifecycle(st.session_state["tech_lifecycle_df"])
    exploded = df.assign(Project=df["Impacted Projects"].str.split(", ")).explode("Project")
    fig = px.bar(
        exploded,
        x="Project",
        y="Impact Score",
        color="Risk Status",
        title="Impact by Project",
        color_discrete_map={
            "Low": "#19a4a1",
            "Medium": "#d39020",
            "High": "#d95368",
        },
    )
    configure_chart(fig)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df[["Application", "Impacted Projects", "Suggested Action Window", "Owner"]], use_container_width=True, hide_index=True)


def _render_project_summary_report(source_engine: str, context_project: str | None) -> None:
    if source_engine == "scan":
        df = current_filtered_scan_df(context_project).copy()
        metrics = build_status_metrics(df)
        cols = st.columns(4)
        cols[0].metric("Project Context", context_project or st.session_state["scan_selected_project"])
        cols[1].metric("Tasks", len(df))
        cols[2].metric("In Flow", metrics["In Progress"]["count"] + metrics["Review"]["count"])
        cols[3].metric("Attention", int((df["Due Risk"] == "Overdue").sum()))
        st.caption(f"Portfolio coverage: {len(st.session_state['scan_projects'])} loaded project sheet(s)")
        trend_df = (
            df.groupby("Status").size().reindex(STATUS_ORDER, fill_value=0).reset_index(name="Tasks")
        )
        trend_df.columns = ["Status", "Tasks"]
        fig = px.bar(
            trend_df,
            x="Status",
            y="Tasks",
            color="Status",
            title=f"{context_project or st.session_state['scan_selected_project']} Delivery Snapshot",
            color_discrete_map=status_palette(),
        )
        configure_chart(fig)
        fig.update_traces(hovertemplate="<b>%{x}</b><br>Tasks: %{y}<extra></extra>")
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(generate_project_summary_text(df, context_project))
        return

    if source_engine == "roadmap":
        roadmap_df = build_roadmap_table()
        feasibility = roadmap_feasibility(roadmap_df)
        cols = st.columns(4)
        cols[0].metric("Roadmap Tasks", len(roadmap_df))
        cols[1].metric("Teams Planned", roadmap_df["Team"].nunique())
        cols[2].metric("Target Status", feasibility["status"])
        cols[3].metric("Working Days", feasibility["required_days"])
        st.plotly_chart(build_team_timeline_chart(roadmap_df), use_container_width=True)
        st.markdown(build_roadmap_summary_text(roadmap_df, feasibility))
        return

    tech_df = evaluate_tech_lifecycle(st.session_state["tech_lifecycle_df"])
    cols = st.columns(4)
    cols[0].metric("Applications", len(tech_df))
    cols[1].metric("High Risk", int((tech_df["Risk Status"] == "High").sum()))
    cols[2].metric("Upgrade / Replace", int(tech_df["Recommendation"].isin(["Upgrade", "Replace"]).sum()))
    cols[3].metric("Impacted Projects", tech_df["Impacted Projects"].str.split(", ").explode().nunique())
    fig = px.bar(
        tech_df.sort_values("Impact Score", ascending=False),
        x="Application",
        y="Impact Score",
        color="Risk Status",
        title="Lifecycle Risk by Application",
        color_discrete_map={"Low": "#19a4a1", "Medium": "#d39020", "High": "#d95368"},
    )
    configure_chart(fig)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(build_technology_summary_text(tech_df))


def _render_stakeholder_update(source_engine: str, context_project: str | None) -> None:
    if source_engine == "scan":
        update_text = build_stakeholder_update(current_filtered_scan_df(context_project).copy(), context_project)
    elif source_engine == "roadmap":
        update_text = build_roadmap_stakeholder_update(build_roadmap_table())
    else:
        update_text = build_technology_stakeholder_update(evaluate_tech_lifecycle(st.session_state["tech_lifecycle_df"]))
    st.markdown("#### Stakeholder Update Draft")
    st.markdown(update_text)


def _render_governance_pack(source_engine: str, context_project: str | None) -> None:
    if source_engine == "scan":
        df = current_filtered_scan_df(context_project).copy()
        overview = st.columns(4)
        overview[0].metric("Project Context", context_project or st.session_state["scan_selected_project"])
        overview[1].metric("Active Flow", int(df["Status"].isin(["In Progress", "Review"]).sum()))
        overview[2].metric("Overdue Items", int((df["Due Risk"] == "Overdue").sum()))
        overview[3].metric("Projects Loaded", len(st.session_state["scan_projects"]))
        cols = st.columns(2)
        with cols[0]:
            workload_df = df.groupby(["Team", "Status"]).size().reset_index(name="Tasks")
            fig = px.bar(
                workload_df,
                x="Team",
                y="Tasks",
                color="Status",
                title="Workload by Team",
                barmode="stack",
                color_discrete_map=status_palette(),
            )
            configure_chart(fig)
            fig.update_traces(hovertemplate="<b>%{x}</b><br>Status: %{fullData.name}<br>Tasks: %{y}<extra></extra>")
            st.plotly_chart(fig, use_container_width=True)
        with cols[1]:
            overdue_owner_df = (
                df.groupby("Owner")["Due Risk"].apply(lambda s: int((s == "Overdue").sum())).reset_index(name="Overdue Tasks")
                .sort_values("Overdue Tasks", ascending=False)
            )
            fig = px.bar(
                overdue_owner_df,
                y="Owner",
                x="Overdue Tasks",
                title="Overdue Tasks by Owner",
                orientation="h",
                color="Overdue Tasks",
                color_continuous_scale=["#ffd9dd", "#ff7c8f", "#d95368"],
            )
            configure_chart(fig)
            fig.update_layout(yaxis_title="", xaxis_title="Overdue tasks")
            fig.update_traces(hovertemplate="<b>%{y}</b><br>Overdue Tasks: %{x}<extra></extra>")
            st.plotly_chart(fig, use_container_width=True)
        exception_df = df[df["Due Risk"] == "Overdue"][["Task Name", "Owner", "Planned End", "Status"]].copy()
        if not exception_df.empty:
            exception_df["Planned End"] = exception_df["Planned End"].map(format_date)
            st.markdown("#### Top Delays / Exceptions")
            st.dataframe(exception_df, use_container_width=True, hide_index=True)
        st.info("Read the stacked team view for where work is sitting, then use the overdue-by-owner chart and exception table to decide who needs follow-up or escalation.")
        st.markdown(generate_governance_pack(df))
        return

    if source_engine == "roadmap":
        roadmap_df = build_roadmap_table()
        cols = st.columns(2)
        with cols[0]:
            fig = px.bar(
                roadmap_df.groupby("Team")["Duration"].sum().reset_index(),
                x="Team",
                y="Duration",
                title="Planned Effort by Team",
                color="Duration",
                color_continuous_scale="Blues",
            )
            configure_chart(fig)
            st.plotly_chart(fig, use_container_width=True)
        with cols[1]:
            fig = px.pie(
                roadmap_df.groupby("Build Strategy").size().reset_index(name="Count"),
                names="Build Strategy",
                values="Count",
                hole=0.52,
                title="Build Strategy Mix",
            )
            configure_chart(fig)
            st.plotly_chart(fig, use_container_width=True)
        st.markdown(build_roadmap_governance_pack(roadmap_df))
        return

    tech_df = evaluate_tech_lifecycle(st.session_state["tech_lifecycle_df"])
    cols = st.columns(2)
    with cols[0]:
        fig = px.pie(
            tech_df,
            names="Recommendation",
            title="Lifecycle Recommendation Mix",
            hole=0.5,
            color="Recommendation",
            color_discrete_map={"Continue": "#19a4a1", "Upgrade": "#d39020", "Replace": "#d95368", "Retire": "#6a7690"},
        )
        configure_chart(fig)
        st.plotly_chart(fig, use_container_width=True)
    with cols[1]:
        exploded = tech_df.assign(Project=tech_df["Impacted Projects"].str.split(", ")).explode("Project")
        fig = px.bar(
            exploded.groupby("Project")["Impact Score"].sum().reset_index(),
            x="Project",
            y="Impact Score",
            title="Lifecycle Exposure by Project",
            color="Impact Score",
            color_continuous_scale="Teal",
        )
        configure_chart(fig)
        st.plotly_chart(fig, use_container_width=True)
    st.markdown(build_technology_governance_pack(tech_df))


def _render_action_tracker(source_engine: str, context_project: str | None) -> None:
    with st.expander("Edit Action Register"):
        st.session_state["reports_action_tracker"] = st.data_editor(
            st.session_state["reports_action_tracker"],
            use_container_width=True,
            num_rows="dynamic",
            key="reports_action_editor",
        )
    tracker = st.session_state["reports_action_tracker"]
    if source_engine == "scan" and context_project:
        tracker = tracker[tracker["Project"] == context_project].copy()
        active_filters = get_active_scan_filter_values(context_project)
        for column in ["Owner", "Team", "Status"]:
            if column in tracker.columns and active_filters.get(column):
                tracker = tracker[tracker[column].astype(str).isin(active_filters[column])].copy()
    elif source_engine == "roadmap":
        tracker = tracker[tracker["Project"].eq(st.session_state["roadmap_project_name"]) | tracker["Project"].eq("Project1")].copy()
    tracker["Due Date"] = pd.to_datetime(tracker["Due Date"], errors="coerce", dayfirst=True)
    today = pd.Timestamp(date.today())
    tracker["Attention"] = tracker.apply(
        lambda row: "Closed" if str(row["Status"]).lower() == "closed" else "Overdue" if pd.notna(row["Due Date"]) and row["Due Date"] < today else "Due Soon" if pd.notna(row["Due Date"]) and row["Due Date"] <= today + pd.Timedelta(days=3) else "On Track",
        axis=1,
    )
    headline = st.columns(4)
    headline[0].metric("Open Actions", int((tracker["Status"].astype(str).str.lower() != "closed").sum()))
    headline[1].metric("Overdue", int((tracker["Attention"] == "Overdue").sum()))
    headline[2].metric("Due Soon", int((tracker["Attention"] == "Due Soon").sum()))
    headline[3].metric("Owners Impacted", tracker["Owner"].nunique())
    fig = px.bar(
        tracker.groupby(["Owner", "Attention"]).size().reset_index(name="Actions"),
        x="Owner",
        y="Actions",
        color="Attention",
        title="Action Tracker Status",
        barmode="stack",
        color_discrete_map={"On Track": "#19a4a1", "Due Soon": "#d39020", "Overdue": "#d95368", "Closed": "#6b7a90"},
    )
    configure_chart(fig)
    fig.update_traces(hovertemplate="<b>%{x}</b><br>Attention: %{fullData.name}<br>Actions: %{y}<extra></extra>")
    st.plotly_chart(fig, use_container_width=True)
    st.info("Read the attention split first: overdue means immediate follow-up, due soon means plan closure this week, and on-track items are for monitoring.")
    view = tracker[["Action", "Owner", "Team", "Due Date", "Status", "Attention", "Category"]].copy()
    view["Due Date"] = view["Due Date"].map(format_date)
    st.dataframe(view.sort_values(["Attention", "Due Date"], ascending=[True, True]), use_container_width=True, hide_index=True)

def _render_raid_summary(source_engine: str, context_project: str | None) -> None:
    with st.expander("Edit RAID Register"):
        st.session_state["reports_raid"] = st.data_editor(
            st.session_state["reports_raid"],
            use_container_width=True,
            num_rows="dynamic",
            key="reports_raid_editor",
        )
    raid_df = st.session_state["reports_raid"]
    if source_engine == "scan" and context_project:
        raid_df = raid_df[raid_df["Project"] == context_project].copy()
        active_filters = get_active_scan_filter_values(context_project)
        if "Owner" in raid_df.columns and active_filters.get("Owner"):
            raid_df = raid_df[raid_df["Owner"].astype(str).isin(active_filters["Owner"])].copy()
        if "Status" in raid_df.columns and active_filters.get("Status"):
            raid_df = raid_df[raid_df["Status"].astype(str).isin(active_filters["Status"])].copy()
    headline = st.columns(4)
    headline[0].metric("RAID Items", len(raid_df))
    headline[1].metric("High Severity", int((raid_df["Severity"] == "High").sum()))
    headline[2].metric("Open Issues", int(((raid_df["Type"] == "Issue") & (raid_df["Status"].astype(str).str.lower() != "closed")).sum()))
    headline[3].metric("Owners Impacted", raid_df["Owner"].nunique())
    fig = px.bar(
        raid_df.groupby(["Type", "Severity"]).size().reset_index(name="Count"),
        x="Type",
        y="Count",
        color="Severity",
        title="RAID Distribution",
        color_discrete_map={"Low": "#19a4a1", "Medium": "#d39020", "High": "#d95368"},
    )
    configure_chart(fig)
    fig.update_traces(hovertemplate="<b>%{x}</b><br>Severity: %{fullData.name}<br>Items: %{y}<extra></extra>")
    st.plotly_chart(fig, use_container_width=True)
    st.info("Use high-severity items and open issues as the first management filter. Risks and dependencies are for proactive control, issues need current action.")
    raid_view = raid_df.copy()
    raid_view["Management Action"] = raid_view.apply(
        lambda row: "Escalate now" if row["Severity"] == "High" and str(row["Status"]).lower() != "closed" else "Track closely" if row["Severity"] == "Medium" else "Monitor",
        axis=1,
    )
    st.dataframe(raid_view[["Type", "Item", "Severity", "Owner", "Status", "Management Action"]], use_container_width=True, hide_index=True)

def _render_ad_hoc_tracker(source_engine: str, context_project: str | None) -> None:
    with st.form("adhoc_create_form", clear_on_submit=True):
        create_cols = st.columns(4)
        adhoc_project = create_cols[0].selectbox("Project", list(st.session_state["scan_projects"].keys()), key="adhoc_create_project")
        adhoc_request = create_cols[1].text_input("Request", key="adhoc_create_request")
        adhoc_owner = create_cols[2].text_input("Owner", key="adhoc_create_owner")
        adhoc_team = create_cols[3].text_input("Team", key="adhoc_create_team")
        detail_cols = st.columns(3)
        adhoc_type = detail_cols[0].selectbox("Type", ["Delivery", "Reporting", "Governance", "Enhancement", "Support"], key="adhoc_create_type")
        adhoc_due = detail_cols[1].date_input("Due Date", value=date.today() + timedelta(days=3), key="adhoc_create_due")
        adhoc_priority = detail_cols[2].selectbox("Priority", ["High", "Medium", "Low"], key="adhoc_create_priority")
        if st.form_submit_button("Add Ad Hoc Request", type="primary"):
            if adhoc_request.strip():
                new_row = pd.DataFrame(
                    [[adhoc_project, adhoc_request.strip(), adhoc_type, adhoc_owner.strip() or "Unassigned", adhoc_team.strip() or "General Delivery", adhoc_due, "To Do", adhoc_priority]],
                    columns=["Project", "Request", "Type", "Owner", "Team", "Due Date", "Status", "Priority"],
                )
                st.session_state["shared_ad_hoc_requests"] = pd.concat([st.session_state["shared_ad_hoc_requests"], new_row], ignore_index=True)
                st.success("Ad hoc request added.")
                st.rerun()
            else:
                st.warning("Enter a request title before adding the item.")

    with st.expander("Edit Ad Hoc Register"):
        st.session_state["shared_ad_hoc_requests"] = st.data_editor(
            st.session_state["shared_ad_hoc_requests"],
            use_container_width=True,
            num_rows="dynamic",
            key="adhoc_editor",
        )
    adhoc_df = st.session_state["shared_ad_hoc_requests"]
    if source_engine == "scan" and context_project:
        adhoc_df = adhoc_df[adhoc_df["Project"] == context_project].copy()
        active_filters = get_active_scan_filter_values(context_project)
        for column in ["Owner", "Team", "Status"]:
            if column in adhoc_df.columns and active_filters.get(column):
                adhoc_df = adhoc_df[adhoc_df[column].astype(str).isin(active_filters[column])].copy()
    elif source_engine == "roadmap":
        adhoc_df = adhoc_df[adhoc_df["Project"].isin([st.session_state["roadmap_project_name"], "Project1"])].copy()
    cols = st.columns(2)
    with cols[0]:
        fig = px.pie(
            adhoc_df,
            names="Status",
            title="Ad Hoc Request Status",
            hole=0.55,
            color="Status",
            color_discrete_map=status_palette(),
        )
        configure_chart(fig)
        st.plotly_chart(fig, use_container_width=True)
    with cols[1]:
        fig = px.bar(
            adhoc_df.groupby("Team").size().reset_index(name="Requests"),
            x="Team",
            y="Requests",
            title="Ad Hoc Requests by Team",
            color="Requests",
            color_continuous_scale="Teal",
        )
        configure_chart(fig)
        st.plotly_chart(fig, use_container_width=True)
    st.info("Add ad hoc items here to track unplanned asks. Open items automatically appear in the Scan Project review follow-up area and can be merged into roadmap planning.")
    adhoc_view = adhoc_df.copy()
    adhoc_view["Due Date"] = adhoc_view["Due Date"].map(format_date)
    st.dataframe(adhoc_view, use_container_width=True, hide_index=True)

def _render_summary_studio(source_engine: str, context_project: str | None) -> None:
    summary_type = st.selectbox(
        "Summary Type",
        ["Project Summary", "Executive Summary", "Risk Summary", "Stakeholder Summary"],
        key=f"ai_summary_type_{source_engine}",
    )
    active_summary = build_source_summary_text(summary_type, source_engine, context_project)
    st.caption(f"Operating from {CROSS_ENGINE_SOURCES[source_engine]}{f' • {context_project}' if context_project else ''}")
    st.markdown("#### Generated Summary")
    st.markdown(active_summary)

def _render_meeting_copilot(source_engine: str, context_project: str | None) -> None:
    meeting_type = st.selectbox(
        "Meeting Type",
        ["Daily Scrum", "Governance Review", "Steering Committee", "Client Update"],
        key=f"ai_meeting_type_{source_engine}",
    )
    meeting_pack = build_source_meeting_pack(meeting_type, source_engine, context_project)
    st.caption(f"Operating from {CROSS_ENGINE_SOURCES[source_engine]}{f' • {context_project}' if context_project else ''}")
    st.markdown("#### Meeting Prep")
    st.markdown(meeting_pack.replace("\n", "  \n"))

def _render_agile_coach(source_engine: str, context_project: str | None) -> None:
    if source_engine == "roadmap":
        options = ["Scope Review", "Plan Readiness", "Dependency Review", "Timeline Compression"]
    elif source_engine == "technology":
        options = ["Lifecycle Risk Review", "Upgrade Prioritization", "Release Readiness"]
    else:
        options = [
            "Daily Scrum Focus",
            "Sprint Planning Clarity",
            "Backlog Refinement",
            "Retrospective Questions",
            "Scrum Anti-Patterns",
        ]
    use_case = st.selectbox("Agile Coach Mode", options, key=f"ai_agile_mode_{source_engine}")
    guidance = build_source_guidance(use_case, source_engine, context_project)
    st.caption(f"Operating from {CROSS_ENGINE_SOURCES[source_engine]}{f' • {context_project}' if context_project else ''}")
    st.markdown("#### Guidance")
    st.markdown(guidance)


def infer_source_header_map(df: pd.DataFrame) -> dict[str, str]:
    lowered = {str(col).strip().lower(): col for col in df.columns}
    source_map: dict[str, str] = {}
    for canonical, options in SCAN_ALIASES.items():
        for lowered_name, original in lowered.items():
            if any(option == lowered_name or option in lowered_name for option in options):
                source_map[canonical] = str(original)
                break
    return source_map


def parse_uploaded_project_file(uploaded_file) -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame], dict[str, list[str]], dict[str, dict[str, str]]]:
    try:
        if uploaded_file.name.lower().endswith(".csv"):
            raw_df = pd.read_csv(uploaded_file, header=None)
            prepared = prepare_input_dataframe(raw_df)
            project_name = clean_project_name(uploaded_file.name)
            return (
                {project_name: normalize_scan_df(prepared, project_name)},
                {project_name: prepared.copy()},
                {project_name: prepared.columns.astype(str).tolist()},
                {project_name: infer_source_header_map(prepared)},
            )
        workbook = pd.ExcelFile(uploaded_file)
        projects = {}
        raw_projects = {}
        source_headers = {}
        source_header_map = {}
        for sheet in workbook.sheet_names:
            raw_df = workbook.parse(sheet, header=None)
            prepared = prepare_input_dataframe(raw_df)
            if prepared.empty:
                continue
            raw_projects[sheet] = prepared.copy()
            projects[sheet] = normalize_scan_df(prepared, sheet)
            source_headers[sheet] = prepared.columns.astype(str).tolist()
            source_header_map[sheet] = infer_source_header_map(prepared)
        return projects, raw_projects, source_headers, source_header_map
    except Exception as exc:
        st.error(f"Could not parse uploaded file: {exc}")
        return {}, {}, {}, {}


def prepare_input_dataframe(raw_df: pd.DataFrame) -> pd.DataFrame:
    cleaned = raw_df.dropna(axis=0, how="all").dropna(axis=1, how="all").reset_index(drop=True)
    if cleaned.empty:
        return cleaned
    header_row = detect_header_row(cleaned)
    header_values = cleaned.iloc[header_row].fillna("").astype(str).str.strip().tolist()
    columns = []
    for idx, value in enumerate(header_values):
        columns.append(value if value else f"Column {idx + 1}")
    prepared = cleaned.iloc[header_row + 1 :].copy().reset_index(drop=True)
    prepared.columns = make_unique_column_names(columns)
    prepared = prepared.dropna(axis=0, how="all").dropna(axis=1, how="all")
    prepared.columns = make_unique_column_names([str(col).strip() for col in prepared.columns])
    return prepared


def detect_header_row(df: pd.DataFrame) -> int:
    best_row = 0
    best_score = -1
    max_scan = min(len(df), 20)
    for idx in range(max_scan):
        values = df.iloc[idx].fillna("").astype(str).str.strip().str.lower().tolist()
        score = 0
        for value in values:
            if not value:
                continue
            for aliases in SCAN_ALIASES.values():
                if any(alias in value for alias in aliases):
                    score += 1
                    break
        if score > best_score:
            best_score = score
            best_row = idx
    return best_row


def make_unique_column_names(columns: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    unique: list[str] = []
    for idx, raw in enumerate(columns, start=1):
        base = (raw or f"Column {idx}").strip() if isinstance(raw, str) else str(raw)
        base = base or f"Column {idx}"
        count = seen.get(base, 0)
        unique.append(base if count == 0 else f"{base}__{count}")
        seen[base] = count + 1
    return unique


def ensure_unique_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work.columns = make_unique_column_names([str(col) for col in work.columns])
    return work


def clean_project_name(name: str) -> str:
    return name.rsplit(".", 1)[0]


def parse_any_datetime(values: Any) -> Any:
    try:
        return pd.to_datetime(values, errors="coerce", dayfirst=True, format="mixed")
    except TypeError:
        return pd.to_datetime(values, errors="coerce", dayfirst=True)
    except ValueError:
        return pd.to_datetime(values, errors="coerce", dayfirst=True)


def normalize_scan_df(df: pd.DataFrame, project_name: str, header_map_override: dict[str, str] | None = None) -> pd.DataFrame:
    aliases = SCAN_ALIASES
    df = ensure_unique_dataframe_columns(df)
    rename_map = {}
    if header_map_override:
        for canonical, source in header_map_override.items():
            if source in df.columns:
                rename_map[source] = canonical
    else:
        lowered = {str(col).strip().lower(): col for col in df.columns}
        for canonical, options in aliases.items():
            matched = None
            for lowered_name, original in lowered.items():
                if any(option == lowered_name or option in lowered_name for option in options):
                    matched = original
                    break
            if matched is not None:
                rename_map[matched] = canonical
    normalized = df.rename(columns=rename_map).copy()
    normalized = normalized.loc[:, ~normalized.columns.duplicated()].copy()
    for column in aliases:
        if column not in normalized.columns:
            normalized[column] = pd.NA
    normalized["Task ID"] = normalized["Task ID"].fillna(pd.Series([f"T{idx+1:03d}" for idx in range(len(normalized))]))
    normalized["Task Name"] = normalized["Task Name"].fillna("Untitled Task")
    normalized["Owner"] = normalized["Owner"].fillna("Unassigned")
    normalized["Team"] = normalized["Team"].fillna("General Delivery")
    normalized["Dependencies"] = normalized["Dependencies"].fillna("")
    normalized["Percent Complete"] = pd.to_numeric(normalized["Percent Complete"], errors="coerce").fillna(0).clip(0, 100)
    for date_col in ["Planned Start", "Planned End", "Actual Start", "Actual End"]:
        normalized[date_col] = parse_any_datetime(normalized[date_col])
    start_seed = pd.Timestamp(date(2026, 4, 1))
    default_starts = pd.Series(start_seed + pd.to_timedelta(range(len(normalized)), unit="D"), index=normalized.index)
    normalized["Planned Start"] = normalized["Planned Start"].where(normalized["Planned Start"].notna(), default_starts)
    default_ends = normalized["Planned Start"] + pd.to_timedelta(2, unit="D")
    normalized["Planned End"] = normalized["Planned End"].where(normalized["Planned End"].notna(), default_ends)
    normalized["Status"] = normalized["Status"].fillna(
        pd.Series(
            ["Done" if pct >= 100 else "In Progress" if pct > 0 else "To Do" for pct in normalized["Percent Complete"]],
            index=normalized.index,
        )
    )
    normalized["Status"] = normalized["Status"].apply(normalize_status)
    if normalized["Task Name"].astype(str).str.strip().eq("").all():
        normalized["Task Name"] = [f"Work Item {idx+1}" for idx in range(len(normalized))]
    normalized["Project"] = project_name
    normalized["Due Risk"] = normalized.apply(compute_due_risk, axis=1)
    core_columns = [
        "Project",
        "Task ID",
        "Task Name",
        "Status",
        "Owner",
        "Team",
        "Planned Start",
        "Planned End",
        "Actual Start",
        "Actual End",
        "Dependencies",
        "Percent Complete",
        "Due Risk",
    ]
    trailing_columns = [column for column in normalized.columns if column not in core_columns]
    final_df = normalized[core_columns + trailing_columns].copy()
    final_df = ensure_unique_dataframe_columns(final_df)
    return final_df


def normalize_status(value: Any) -> str:
    raw = str(value).strip().lower()
    if raw in {"done", "closed", "complete", "completed"}:
        return "Done"
    if raw in {"review", "uat", "validation", "testing"}:
        return "Review"
    if raw in {"in progress", "doing", "active", "ongoing"}:
        return "In Progress"
    return "To Do"


def sanitize_scan_runtime_df(df: pd.DataFrame, project_name: str | None = None) -> pd.DataFrame:
    work = ensure_unique_dataframe_columns(df.copy())
    required_columns = [
        "Project",
        "Task ID",
        "Task Name",
        "Status",
        "Owner",
        "Team",
        "Planned Start",
        "Planned End",
        "Actual Start",
        "Actual End",
        "Dependencies",
        "Percent Complete",
        "Due Risk",
    ]
    for column in required_columns:
        if column not in work.columns:
            work[column] = pd.NA

    default_project = project_name or st.session_state.get("scan_selected_project", "Project")
    work["Project"] = work["Project"].fillna(default_project).astype(str)

    task_ids = work["Task ID"].astype(str).replace({"<NA>": "", "nan": "", "None": ""}).str.strip()
    missing_mask = task_ids.eq("")
    if missing_mask.any():
        generated = [f"T{idx + 1:03d}" for idx in range(len(work))]
        task_ids = task_ids.where(~missing_mask, pd.Series(generated, index=work.index))
    work["Task ID"] = task_ids

    work["Task Name"] = work["Task Name"].fillna("Untitled Task").astype(str)
    work["Owner"] = work["Owner"].fillna("Unassigned").astype(str)
    work["Team"] = work["Team"].fillna("General Delivery").astype(str)
    work["Dependencies"] = work["Dependencies"].fillna("").astype(str)
    work["Status"] = work["Status"].apply(normalize_status)
    work["Percent Complete"] = (
        pd.to_numeric(work["Percent Complete"], errors="coerce")
        .fillna(0)
        .clip(0, 100)
        .astype(int)
    )

    for date_col in ["Planned Start", "Planned End", "Actual Start", "Actual End"]:
        work[date_col] = parse_any_datetime(work[date_col])

    if work["Planned Start"].isna().any():
        fallback_start = pd.Timestamp(date.today())
        work["Planned Start"] = work["Planned Start"].where(
            work["Planned Start"].notna(),
            pd.Series(
                [fallback_start + pd.Timedelta(days=idx) for idx in range(len(work))],
                index=work.index,
            ),
        )
    if work["Planned End"].isna().any():
        work["Planned End"] = work["Planned End"].where(
            work["Planned End"].notna(),
            work["Planned Start"] + pd.to_timedelta(2, unit="D"),
        )

    work["Due Risk"] = work.apply(compute_due_risk, axis=1)
    ordered_columns = [column for column in required_columns if column in work.columns]
    trailing_columns = [column for column in work.columns if column not in ordered_columns]
    return work[ordered_columns + trailing_columns]


def compute_due_risk(row: pd.Series) -> str:
    planned_end = pd.to_datetime(row.get("Planned End"), errors="coerce", dayfirst=True)
    status = normalize_status(row.get("Status", "To Do"))
    today = pd.Timestamp(date.today()).normalize()
    if pd.notna(planned_end):
        planned_end = planned_end.normalize()
    if pd.notna(planned_end) and status != "Done" and planned_end < today:
        return "Overdue"
    if pd.notna(planned_end) and status != "Done" and planned_end <= today + pd.Timedelta(days=3):
        return "Watch"
    return "On Track"


def build_status_metrics(df: pd.DataFrame) -> dict[str, dict[str, int]]:
    total = max(len(df), 1)
    metrics = {}
    for status in STATUS_ORDER:
        count = int((df["Status"] == status).sum())
        metrics[status] = {"count": count, "pct": round((count / total) * 100)}
    return metrics


def format_due_signal(value: Any) -> str:
    raw = str(value or "").strip()
    if raw == "Overdue":
        return "🔴 Overdue"
    if raw == "Watch":
        return "🟠 Watch"
    return "🟢 On Track"


def build_resource_utilization(df: pd.DataFrame) -> pd.DataFrame:
    util = (
        df.groupby("Owner")
        .agg(
            **{
                "Active Tasks": ("Status", lambda s: int((s != "Done").sum())),
                "Overdue Tasks": ("Due Risk", lambda s: int((s == "Overdue").sum())),
            }
        )
        .reset_index()
    )
    util["Utilization Status"] = util["Active Tasks"].apply(lambda x: "Overloaded" if x >= 4 else "Watch" if x >= 2 else "Balanced")
    return util.sort_values(["Utilization Status", "Active Tasks"], ascending=[True, False])


def infer_scan_sheet_intelligence(
    raw_projects: dict[str, pd.DataFrame],
    source_header_map: dict[str, dict[str, str]],
) -> tuple[dict[str, dict[str, Any]], list[str], list[str]]:
    intelligence: dict[str, dict[str, Any]] = {}
    ranked: list[tuple[int, str]] = []
    for sheet_name, frame in raw_projects.items():
        mapped_fields = source_header_map.get(sheet_name, {})
        row_count = len(frame)
        field_score = len(mapped_fields)
        lower_name = sheet_name.lower()
        name_hits = sum(token in lower_name for token in ["project", "plan", "tracker", "delivery", "task", "roadmap", "status"])
        support_hits = sum(token in lower_name for token in ["lookup", "config", "master", "legend", "readme", "holiday", "template"])
        score = (field_score * 3) + (name_hits * 2) - support_hits
        relevant = row_count >= 3 and (field_score >= 3 or (field_score >= 2 and name_hits >= 1))
        if support_hits >= 1 and field_score <= 2:
            relevant = False
        if score >= 12:
            confidence = "High"
        elif score >= 7:
            confidence = "Medium"
        else:
            confidence = "Review"
        reason_parts = []
        if field_score:
            reason_parts.append(f"{field_score} delivery fields recognized")
        if name_hits:
            reason_parts.append("sheet name matches project execution context")
        if support_hits:
            reason_parts.append("supporting workbook pattern detected")
        if not reason_parts:
            reason_parts.append("low signal workbook tab")
        intelligence[sheet_name] = {
            "relevant": relevant,
            "confidence": confidence,
            "reason": "; ".join(reason_parts),
            "rows": row_count,
            "field_score": field_score,
            "score": score,
        }
        ranked.append((score, sheet_name))
    relevant = [name for name, info in intelligence.items() if info["relevant"]]
    if not relevant and ranked:
        relevant = [name for _, name in sorted(ranked, reverse=True)[: min(2, len(ranked))]]
        for name in relevant:
            intelligence[name]["relevant"] = True
            if intelligence[name]["confidence"] == "Review":
                intelligence[name]["confidence"] = "Medium"
                intelligence[name]["reason"] = f"{intelligence[name]['reason']}; promoted as primary sheet by AI review"
    supporting = [name for name in raw_projects.keys() if name not in relevant]
    return intelligence, relevant, supporting


def build_scan_ai_brief(df: pd.DataFrame, project_name: str) -> dict[str, Any]:
    util_df = build_resource_utilization(df) if not df.empty else pd.DataFrame(columns=["Owner", "Active Tasks", "Overdue Tasks", "Utilization Status"])
    overdue_df = df[df["Due Risk"] == "Overdue"].copy()
    review_df = df[df["Status"] == "Review"].copy()
    dep_df = df[df["Dependencies"].astype(str).str.strip() != ""].copy()
    overloaded = util_df[util_df["Utilization Status"] == "Overloaded"]["Owner"].tolist() if not util_df.empty else []
    actions: list[str] = []
    if not overdue_df.empty:
        actions.append(f"Close or reassign {len(overdue_df)} overdue task(s) before the next review cycle.")
    if not review_df.empty:
        actions.append(f"Resolve the {len(review_df)} item(s) waiting in Review to protect delivery flow.")
    if overloaded:
        actions.append(f"Rebalance active work for {', '.join(overloaded[:3])}{' and others' if len(overloaded) > 3 else ''}.")
    if dep_df.empty:
        actions.append("Capture explicit dependency links so the next planning cycle can expose blocked work earlier.")
    summary = (
        f"{project_name} is carrying {len(df)} work item(s) across the execution board. "
        f"{int((df['Status'] == 'Done').sum())} are complete, {int(df['Status'].isin(['In Progress', 'Review']).sum())} are in active flow, "
        f"and {int((df['Due Risk'] == 'Overdue').sum())} require immediate attention."
    )
    next_signals = []
    if not dep_df.empty:
        next_signals.append(f"{len(dep_df)} task(s) have explicit dependencies that should stay visible in daily follow-up.")
    if not util_df.empty:
        top_owner = util_df.sort_values(["Overdue Tasks", "Active Tasks"], ascending=[False, False]).iloc[0]
        next_signals.append(f"{top_owner['Owner']} currently carries the heaviest active load at {int(top_owner['Active Tasks'])} open item(s).")
    next_signals.append("Use the filtered task view to narrow attention by owner, dependency, or status before management review.")
    return {
        "summary": summary,
        "actions": actions[:3] or ["No immediate delivery intervention detected. Continue monitoring flow."],
        "next_signals": next_signals[:3],
        "overdue": int((df["Due Risk"] == "Overdue").sum()),
        "review_queue": int((df["Status"] == "Review").sum()),
        "dependencies": int((df["Dependencies"].astype(str).str.strip() != "").sum()),
        "owners": int(df["Owner"].nunique()),
    }


def _render_scan_ai_brief() -> None:
    project_name = _current_scan_project_name()
    df = current_scan_df(project_name).copy()
    brief = build_scan_ai_brief(df, project_name)
    detail_cols = st.columns([1.5, 1, 1])
    with detail_cols[0]:
        st.markdown(
            f"""
            <div class="vx-card" style="padding:0.95rem 1rem;">
              <div class="vx-eyebrow" style="color:#5f6f88;">AI Delivery Brief</div>
              <p style="margin:0; color:#23324f; line-height:1.65;">{brief['summary']}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with detail_cols[1]:
        st.markdown("#### Recommended Actions")
        for item in brief["actions"]:
            st.markdown(f"- {item}")
    with detail_cols[2]:
        st.markdown("#### Signals")
        for item in brief["next_signals"]:
            st.markdown(f"- {item}")


def build_task_intelligence(df: pd.DataFrame, task_id: str) -> dict[str, Any]:
    if df.empty or task_id not in df["Task ID"].astype(str).tolist():
        return {}
    work = df.copy()
    work["Task ID"] = work["Task ID"].astype(str)
    row = work.loc[work["Task ID"] == task_id].iloc[0]
    dependencies = str(row.get("Dependencies", "") or "").strip()
    follow_on = work[work["Dependencies"].astype(str).str.contains(re.escape(task_id), case=False, na=False)]["Task Name"].astype(str).tolist()
    owner_load = build_resource_utilization(work)
    owner_row = owner_load[owner_load["Owner"] == str(row.get("Owner", ""))]
    owner_active = int(owner_row["Active Tasks"].iloc[0]) if not owner_row.empty else 0
    owner_util = owner_row["Utilization Status"].iloc[0] if not owner_row.empty else "Balanced"
    due_risk = str(row.get("Due Risk", "On Track"))
    status = str(row.get("Status", "To Do"))
    action = "Monitor current plan"
    if due_risk == "Overdue":
        action = "Escalate closure or reassign support before the next checkpoint"
    elif status == "Review":
        action = "Resolve review comments and push for closure"
    elif owner_util == "Overloaded":
        action = "Consider redistributing follow-on work to avoid owner overload"
    return {
        "task_name": str(row.get("Task Name", "")),
        "owner": str(row.get("Owner", "")),
        "team": str(row.get("Team", "")),
        "status": status,
        "due_risk": due_risk,
        "planned_start": format_date(row.get("Planned Start")),
        "planned_end": format_date(row.get("Planned End")),
        "dependencies": dependencies or "No explicit dependency captured",
        "follow_on": follow_on[:5],
        "owner_active": owner_active,
        "owner_util": owner_util,
        "action": action,
        "percent_complete": int(pd.to_numeric(row.get("Percent Complete"), errors="coerce") or 0),
    }


def _render_task_intelligence_panel(df: pd.DataFrame) -> None:
    task_id = str(st.session_state.get("scan_selected_task_id", "") or "")
    if df.empty or not task_id:
        st.markdown(
            """
            <div class="vx-card" style="padding:1rem;">
              <div class="vx-eyebrow" style="color:#5f6f88;">Task Detail</div>
              <p style="margin:0; color:#5f6f88;">Click a Kanban card to view delivery detail, dependency follow-on, and update the task.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return
    intel = build_task_intelligence(df, task_id)
    if not intel:
        st.session_state["scan_selected_task_id"] = ""
        return
    top = st.columns([4, 1])
    with top[0]:
        st.markdown(
            f"""
            <div class="vx-card" style="padding:0.95rem 1rem;">
              <div class="vx-eyebrow" style="color:#5f6f88;">Task Detail</div>
              <h4 style="margin:0 0 0.3rem;">{intel['task_name']}</h4>
              <p style="margin:0 0 0.5rem; color:#5f6f88;">Owner: {intel['owner']} • Team: {intel['team']}</p>
              <p style="margin:0 0 0.45rem; color:#23324f;">Planned window: {intel['planned_start']} to {intel['planned_end']}</p>
              <p style="margin:0; color:#23324f;">Dependency signal: {intel['dependencies']}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with top[1]:
        if st.button("Close", key=f"scan_close_task_detail_{task_id}"):
            st.session_state["scan_selected_task_id"] = ""
            st.rerun()
    headline = st.columns(4)
    headline[0].metric("Task Status", intel["status"])
    headline[1].metric("Due Signal", intel["due_risk"])
    headline[2].metric("Owner Load", intel["owner_active"])
    headline[3].metric("Progress", f"{intel['percent_complete']}%")
    st.markdown("#### AI Next Action")
    st.markdown(f"- {intel['action']}")
    if intel["follow_on"]:
        st.markdown("#### Follower Tasks")
        for item in intel["follow_on"]:
            st.markdown(f"- {item}")
    with st.form(f"scan_task_detail_form_{task_id}"):
            st.caption("Update the selected task from the delivery detail drawer.")
            new_status = st.selectbox("Status", STATUS_ORDER, index=STATUS_ORDER.index(intel["status"]) if intel["status"] in STATUS_ORDER else 0)
            new_owner = st.text_input("Owner", value=intel["owner"])
            new_team = st.text_input("Team", value=intel["team"])
            new_end = st.date_input(
                "Planned End",
                value=pd.to_datetime(intel["planned_end"], errors="coerce").date() if intel["planned_end"] not in {"-", ""} else date.today(),
            )
            save_task = st.form_submit_button("Save Task Update", type="primary")
            if save_task:
                project_name = _current_scan_project_name()
                work = current_scan_df(project_name).copy()
                idx = work.index[work["Task ID"].astype(str) == options[selected_label]]
                if len(idx):
                    idx = idx[0]
                    _push_scan_history(project_name, work.copy())
                    work.at[idx, "Status"] = new_status
                    work.at[idx, "Owner"] = new_owner.strip() or "Unassigned"
                    work.at[idx, "Team"] = new_team.strip() or "General Delivery"
                    work.at[idx, "Planned End"] = pd.Timestamp(new_end)
                    work.at[idx, "Due Risk"] = compute_due_risk(work.loc[idx])
                    update_current_scan_df(work)
                    st.success("Task intelligence update saved.")
                    st.rerun()


def generate_daily_scrum(df: pd.DataFrame) -> str:
    active = df[df["Status"].isin(["In Progress", "Review"])]
    blockers = df[df["Due Risk"] == "Overdue"]
    lines = [
        "### Daily Scrum Focus",
        f"- Active work items: **{len(active)}**",
        f"- Items needing immediate attention: **{len(blockers)}**",
    ]
    if not active.empty:
        top = active.head(5)
        for _, row in top.iterrows():
            lines.append(f"- {row['Owner']} driving **{row['Task Name']}** in {row['Status']} through {format_date(row['Planned End'])}")
    return "\n".join(lines)


def generate_impediment_analysis(df: pd.DataFrame) -> str:
    overdue = df[df["Due Risk"] == "Overdue"]
    if overdue.empty:
        return "### Impediment Analysis\n- No overdue execution blockers detected in the current scan."
    lines = ["### Impediment Analysis", "- Root causes are centered around overdue or dependency-sensitive items:"]
    for _, row in overdue.head(5).iterrows():
        dep = row["Dependencies"] if str(row["Dependencies"]).strip() else "No explicit dependency"
        lines.append(f"- **{row['Task Name']}** owned by {row['Owner']} is overdue. Dependency signal: {dep}.")
    return "\n".join(lines)


def generate_velocity_insight(df: pd.DataFrame) -> str:
    done = int((df["Status"] == "Done").sum())
    in_flow = int(df["Status"].isin(["In Progress", "Review"]).sum())
    todo = int((df["Status"] == "To Do").sum())
    return (
        "### Velocity / Flow Insight\n"
        f"- Done: **{done}**\n"
        f"- In flow: **{in_flow}**\n"
        f"- Remaining backlog: **{todo}**\n"
        "- Recommendation: protect flow by resolving review-stage queues before adding new work."
    )


def generate_dependency_impact(df: pd.DataFrame) -> str:
    dep_df = df[df["Dependencies"].astype(str).str.strip() != ""]
    if dep_df.empty:
        return "### Dependency Impact\n- No explicit dependencies were found in the current project sheet."
    lines = ["### Dependency Impact"]
    for _, row in dep_df.head(5).iterrows():
        lines.append(f"- **{row['Task Name']}** depends on `{row['Dependencies']}` and may affect {row['Status']} flow.")
    return "\n".join(lines)


def generate_milestone_readiness(df: pd.DataFrame) -> str:
    next_week = pd.Timestamp(date.today()) + pd.Timedelta(days=7)
    near = df[(df["Planned End"] <= next_week) & (df["Status"] != "Done")]
    if near.empty:
        return "### Milestone Readiness\n- No near-term incomplete milestones were detected in the next seven days."
    lines = ["### Milestone Readiness", f"- {len(near)} task(s) need closure before the next milestone window:"]
    for _, row in near.head(6).iterrows():
        lines.append(f"- {row['Task Name']} owned by {row['Owner']} due {format_date(row['Planned End'])}")
    return "\n".join(lines)


def analyze_requirement_text(text: str) -> dict[str, Any]:
    lowered = text.lower()
    teams = {"Project Manager", "Product Manager", "Backend Development", "Frontend Development", "QA/Testing"}
    outputs = ["Roadmap phases", "Task breakdown", "Indicative timeline"]
    pain_points = []
    score = 1
    if any(word in lowered for word in ["design", "ui", "ux", "mobile", "portal"]):
        teams.add("UI/UX Design")
    if any(word in lowered for word in ["integration", "api", "interface"]):
        teams.add("DevOps")
        pain_points.append("Integration dependency alignment")
        score += 1
    if any(word in lowered for word in ["security", "audit", "compliance"]):
        teams.add("Security / Compliance")
        pain_points.append("Security review and compliance sign-off")
        score += 1
    if any(word in lowered for word in ["migration", "data", "warehouse", "reporting"]):
        teams.add("Data Engineering")
        pain_points.append("Data quality and migration sequencing")
        score += 1
    if any(word in lowered for word in ["workflow", "approvals", "governance"]):
        teams.add("Business Analyst")
        outputs.append("Decision and approval path")
    if len(text.split()) > 80:
        score += 1
        pain_points.append("Scope needs controlled decomposition")

    complexity = "Low" if score <= 1 else "Medium" if score <= 3 else "High"
    timeline = "4-6 weeks" if complexity == "Low" else "8-12 weeks" if complexity == "Medium" else "12-20 weeks"
    impact = "Contained" if complexity == "Low" else "Moderate" if complexity == "Medium" else "High"
    if not pain_points:
        pain_points = ["Requirement clarity and stakeholder sign-off"]
    return {
        "complexity": complexity,
        "timeline": timeline,
        "impact": impact,
        "teams": sorted(teams),
        "pain_points": pain_points,
        "outputs": outputs,
    }


def market_comparison(description: str) -> pd.DataFrame:
    tokens = set(description.lower().split())
    scored = []
    for item in MARKET_LIBRARY:
        score = len(tokens.intersection(item["keywords"]))
        scored.append((score, item))
    top = [item for score, item in sorted(scored, key=lambda x: x[0], reverse=True)[:4]]
    rows = [
        {
            "Product": item["name"],
            "Organization": item["organization"],
            "Differentiator": item["differentiator"],
        }
        for item in top
    ]
    return pd.DataFrame(rows)


def detect_document_type(filename: str) -> str:
    lower = filename.lower()
    if "brd" in lower:
        return "BRD"
    if "frd" in lower:
        return "FRD"
    if "trd" in lower:
        return "TRD"
    if "srs" in lower:
        return "SRS"
    if "api" in lower:
        return "API Spec"
    if "design" in lower:
        return "Design"
    return "Supporting Document"


def infer_document_signal(filename: str) -> str:
    lower = filename.lower()
    if "api" in lower:
        return "Integration-heavy"
    if "data" in lower:
        return "Data scope"
    if "security" in lower:
        return "Compliance review"
    return "General functional scope"


def upload_signature(uploads: list[Any]) -> str:
    digest = hashlib.sha1()
    for upload in uploads:
        payload = upload.getvalue()
        digest.update(upload.name.encode("utf-8", "ignore"))
        digest.update(str(len(payload)).encode("utf-8"))
        digest.update(payload[:8192])
    return digest.hexdigest()


def normalize_extracted_text(text: str) -> str:
    cleaned = text.replace("\x00", " ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def assess_extracted_text(text: str) -> dict[str, Any]:
    normalized = normalize_extracted_text(text)
    if not normalized:
        return {"usable": False, "status": "Registered", "excerpt": "", "reason": "No extractable text found"}
    words = normalized.split()
    alpha_chars = sum(ch.isalpha() for ch in normalized)
    printable_chars = sum(ch.isprintable() for ch in normalized)
    latin_word_count = len(re.findall(r"[A-Za-z][A-Za-z/&-]{2,}", normalized))
    alpha_ratio = alpha_chars / max(len(normalized), 1)
    latin_ratio = latin_word_count / max(len(words), 1)
    printable_ratio = printable_chars / max(len(normalized), 1)
    usable = len(words) >= 12 and alpha_ratio >= 0.25 and latin_ratio >= 0.25 and printable_ratio >= 0.95
    status = "Parsed" if usable else "Low-confidence parse"
    reason = "Structured text extracted" if usable else "Text extraction was low confidence; using filename and document type signals where needed"
    return {
        "usable": usable,
        "status": status,
        "excerpt": " ".join(words[:120]),
        "reason": reason,
    }


def extract_plain_text(payload: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "latin1"):
        try:
            return normalize_extracted_text(payload.decode(encoding, errors="ignore"))
        except Exception:
            continue
    return ""


def extract_docx_text(payload: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as zf:
            xml = zf.read("word/document.xml").decode("utf-8", errors="ignore")
    except Exception:
        return ""
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<[^>]+>", " ", xml)
    return normalize_extracted_text(html.unescape(xml))


def extract_pdf_text_fallback(payload: bytes) -> str:
    matches = re.findall(rb"\(([^()]*)\)", payload)
    if not matches:
        return ""
    chunks = [m.decode("latin1", errors="ignore") for m in matches[:4000]]
    return normalize_extracted_text(" ".join(chunks))


def extract_pdf_text(payload: bytes) -> str:
    for module_name in ("pypdf", "PyPDF2"):
        try:
            module = __import__(module_name, fromlist=["PdfReader"])
            reader_cls = getattr(module, "PdfReader", None)
            if reader_cls is None:
                continue
            reader = reader_cls(io.BytesIO(payload))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
            text = normalize_extracted_text(text)
            if text:
                return text
        except Exception:
            continue
    return extract_pdf_text_fallback(payload)


def extract_uploaded_document_text(upload: Any) -> tuple[str, str, str]:
    payload = upload.getvalue()
    lower = upload.name.lower()
    if lower.endswith(".pdf"):
        text = extract_pdf_text(payload)
        quality = assess_extracted_text(text)
        return text if quality["usable"] else "", quality["status"], quality["reason"]
    if lower.endswith(".docx"):
        text = extract_docx_text(payload)
        quality = assess_extracted_text(text)
        return text if quality["usable"] else "", quality["status"], quality["reason"]
    text = extract_plain_text(payload)
    quality = assess_extracted_text(text)
    return text if quality["usable"] else "", quality["status"], quality["reason"]


def infer_scope_modules(text: str) -> list[str]:
    lowered = text.lower()
    modules = [
        label
        for label, keywords in MODULE_SIGNAL_LIBRARY.items()
        if any(keyword in lowered for keyword in keywords)
    ]
    return modules or ["Core Delivery Workflow"]


def cleaned_document_project_name(filename: str) -> str:
    stem = clean_project_name(filename)
    stem = re.sub(r"(?i)\b(brd|frd|trd|srs|design|api|spec|document|requirements?)\b", " ", stem)
    stem = re.sub(r"[_\-]+", " ", stem)
    stem = re.sub(r"\s+", " ", stem).strip()
    return stem.title() if stem else APP_TITLE


def derive_document_analysis(documents: list[dict[str, Any]]) -> dict[str, Any]:
    combined_text = normalize_extracted_text(" ".join(doc["text"] for doc in documents if doc.get("status") == "Parsed" and doc.get("text")))
    fallback_text = " ".join(f"{doc['type']} {doc['signal']} {doc['document']}" for doc in documents)
    working_text = combined_text or fallback_text
    analysis = analyze_requirement_text(working_text)
    analysis["document_types"] = sorted({doc["type"] for doc in documents})
    analysis["documents_loaded"] = len(documents)
    analysis["modules"] = infer_scope_modules(working_text)
    analysis["excerpt"] = " ".join(working_text.split()[:120])
    analysis["word_count"] = len(working_text.split())
    analysis["project_name"] = cleaned_document_project_name(documents[0]["document"]) if documents else APP_TITLE
    analysis["parsed_documents"] = int(sum(1 for doc in documents if doc.get("status") == "Parsed"))
    analysis["low_confidence_documents"] = int(sum(1 for doc in documents if doc.get("status") == "Low-confidence parse"))
    analysis["auto_populated_sections"] = [
        ("Project Details", "Project Description", "Description and scope draft"),
        ("Planning Inputs", "Team Allocation", "Suggested teams and capacity mix"),
        ("Planning Inputs", "Development Approach", "Suggested build / reuse / API approach"),
        ("Task & Timeline", "Task Input", "Draft task pack and baseline duration"),
    ]
    return analysis


def build_team_allocation_from_analysis(analysis: dict[str, Any]) -> pd.DataFrame:
    team_df = _default_team_df().copy()
    selected = set(analysis.get("teams", []))
    complexity = analysis.get("complexity", "Medium")
    team_df["Use Team"] = team_df["Team"].isin(selected)
    team_df.loc[~team_df["Use Team"], "Allocation %"] = 25
    if complexity == "High":
        for team in ["Backend Development", "Frontend Development", "QA/Testing"]:
            mask = team_df["Team"] == team
            if mask.any():
                team_df.loc[mask, "Resources"] = pd.to_numeric(team_df.loc[mask, "Resources"], errors="coerce").fillna(1).astype(int) + 1
    return team_df


def build_development_plan_from_analysis(analysis: dict[str, Any]) -> pd.DataFrame:
    modules = analysis.get("modules", [])
    lowered_modules = " ".join(modules).lower()
    complexity = analysis.get("complexity", "Medium")
    rows = [
        (
            "Core Workflow",
            "Build from Scratch" if complexity in {"Medium", "High"} else "Reuse Existing Module",
            "Yes" if complexity == "High" else "No",
            1 if "workflow" in lowered_modules else 0,
            0,
            "High" if complexity == "High" else "Moderate",
        ),
        (
            "Experience Layer",
            "Reuse Existing Module" if "portal" in lowered_modules or "experience" in lowered_modules else "Build from Scratch",
            "Yes",
            1,
            0,
            "Low" if complexity == "Low" else "Moderate",
        ),
        (
            "Integration Services",
            "API-led" if "integration" in lowered_modules else "Build from Scratch",
            "Yes",
            4 if "integration" in lowered_modules else 1,
            2 if "integration" in lowered_modules else 0,
            "Medium" if "integration" in lowered_modules else "Low",
        ),
    ]
    if any("data" in module.lower() for module in modules):
        rows.append(("Data & Reporting", "Build from Scratch", "Yes", 2, 0, "Medium"))
    if any("security" in module.lower() for module in modules):
        rows.append(("Security & Compliance", "Reuse Existing Module", "No", 0, 0, "Medium"))
    return pd.DataFrame(
        rows,
        columns=["Module", "Approach", "AI-assisted", "API Count", "Validated APIs", "Risk"],
    )


def apply_document_analysis_to_roadmap(analysis: dict[str, Any]) -> None:
    if not analysis:
        return
    current_name = st.session_state.get("roadmap_project_name", "")
    if not current_name or current_name == "VertexOne DeliveryOS Enhancement":
        st.session_state["roadmap_project_name"] = analysis.get("project_name", current_name or APP_TITLE)
    excerpt = analysis.get("excerpt", "")
    if excerpt:
        st.session_state["roadmap_project_description"] = excerpt
        st.session_state["roadmap_scope_text"] = excerpt
    st.session_state["roadmap_scope_analysis"] = analysis
    st.session_state["roadmap_team_allocation"] = build_team_allocation_from_analysis(analysis)
    st.session_state["roadmap_dev_approach"] = build_development_plan_from_analysis(analysis)
    generated_tasks = generate_tasks_from_scope(analysis)
    if not generated_tasks.empty:
        st.session_state["roadmap_tasks"] = generated_tasks
    timeline_days = {"Low": 30, "Medium": 60, "High": 90}
    st.session_state["roadmap_duration_days"] = timeline_days.get(analysis.get("complexity", "Medium"), 60)
    st.session_state["roadmap_doc_updated_sections"] = pd.DataFrame(
        analysis.get("auto_populated_sections", []),
        columns=["Area", "Section", "Auto-populated"],
    )


def add_working_days(start: date, working_days: int, holidays: set[date]) -> date:
    current = pd.Timestamp(start).date()
    days_added = 0
    while days_added < max(int(working_days), 1):
        if current.weekday() < 5 and current not in holidays:
            days_added += 1
            if days_added == working_days:
                return current
        current += timedelta(days=1)
    return current


def holiday_dates(holiday_df: pd.DataFrame) -> set[date]:
    dates = set()
    for value in holiday_df["Date"].tolist():
        try:
            dates.add(pd.to_datetime(value).date())
        except Exception:
            continue
    return dates


def generate_tasks_from_scope(analysis: dict[str, Any]) -> pd.DataFrame:
    if not analysis:
        return pd.DataFrame()
    phases = [
        ("Requirement Gathering", "Business Analyst", 5),
        ("Design", "UI/UX Design" if "UI/UX Design" in analysis["teams"] else "Product Manager", 6),
        ("Development", "Backend Development", 18),
        ("Testing", "QA/Testing", 7),
        ("Deployment", "DevOps", 4),
        ("Hypercare", "Project Manager", 5),
    ]
    modules = set(analysis.get("modules", []))
    if "Integration Services" in modules:
        phases.insert(3, ("Integration Design & API Validation", "Backend Development", 7))
    if "Data & Reporting" in modules:
        phases.insert(4, ("Data Mapping & Reporting", "Data Engineering" if "Data Engineering" in analysis["teams"] else "Business Analyst", 6))
    if "Security & Compliance" in modules:
        phases.insert(-1, ("Security & Compliance Review", "Security / Compliance", 4))
    rows = []
    for idx, (task, team, duration) in enumerate(phases, start=1):
        rows.append(
            {
                "Task ID": f"R{idx:03d}",
                "Task Name": task,
                "Team": team,
                "Assigned Resource": "",
                "Duration": duration + (2 if analysis["complexity"] == "High" and task in {"Development", "Testing"} else 0),
                "Dependency": "" if idx == 1 else f"R{idx-1:03d}",
                "Execution": "Sequential" if idx in {1, 2, 5} else "Parallel",
                "Build Strategy": "Build from Scratch",
                "Status": "Planned",
            }
        )
    return pd.DataFrame(rows)


def build_roadmap_table() -> pd.DataFrame:
    tasks = st.session_state["roadmap_tasks"].copy()
    start_date = st.session_state["roadmap_start_date"]
    holidays = holiday_dates(st.session_state["roadmap_holiday_calendar"])
    current_start = start_date
    rows = []
    for _, row in tasks.iterrows():
        duration = int(row.get("Duration", 1) or 1)
        if row.get("Execution") == "Parallel" and rows:
            task_start = rows[-1]["Start Date"]
        else:
            task_start = current_start
        task_end = add_working_days(task_start, duration, holidays)
        rows.append(
            {
                "Task ID": row["Task ID"],
                "Task Name": row["Task Name"],
                "Team": row["Team"],
                "Assigned Resource": row.get("Assigned Resource", ""),
                "Start Date": task_start,
                "End Date": task_end,
                "Duration": duration,
                "Dependency": row.get("Dependency", ""),
                "Execution": row.get("Execution", "Sequential"),
                "Build Strategy": row.get("Build Strategy", "Build from Scratch"),
                "Status": row.get("Status", "Planned"),
            }
        )
        current_start = task_end + timedelta(days=1)
    return pd.DataFrame(rows)


def build_team_timeline_chart(roadmap_df: pd.DataFrame):
    if roadmap_df.empty:
        return go.Figure()
    fig = px.timeline(
        roadmap_df,
        x_start="Start Date",
        x_end="End Date",
        y="Team",
        color="Task Name",
        title="Team Timeline",
    )
    fig.update_yaxes(autorange="reversed")
    configure_chart(fig)
    return fig


def roadmap_feasibility(roadmap_df: pd.DataFrame) -> dict[str, Any]:
    available_days = int(st.session_state["roadmap_duration_days"])
    required_days = int(roadmap_df["Duration"].sum()) if not roadmap_df.empty else 0
    compression = "10-15%" if required_days > available_days else "Optional"
    if required_days <= available_days:
        status = "Achievable"
        recommendation = "Current capacity can support the roadmap if dependencies and approvals stay on time."
        risks = ["Dependency approvals", "Scope changes", "Late ad hoc requests"]
    else:
        status = "At Risk"
        recommendation = "Refine scope, increase shared capacity, or move non-critical work into a later milestone."
        risks = ["Capacity gap against planned window", "High parallel effort", "Potential quality compression"]
    return {
        "status": status,
        "required_days": required_days,
        "available_days": available_days,
        "compression": compression,
        "recommendation": recommendation,
        "risks": risks,
    }


def merge_ad_hoc_into_roadmap() -> None:
    adhoc = st.session_state["shared_ad_hoc_requests"]
    open_items = adhoc[adhoc["Status"] != "Done"]
    if open_items.empty:
        return
    roadmap = st.session_state["roadmap_tasks"].copy()
    for _, row in open_items.iterrows():
        roadmap = pd.concat(
            [
                roadmap,
                pd.DataFrame(
                    [
                        {
                            "Task ID": f"ADH{len(roadmap)+1:03d}",
                            "Task Name": row["Request"],
                            "Team": row["Team"],
                            "Assigned Resource": row["Owner"],
                            "Duration": 3,
                            "Dependency": "",
                            "Execution": "Parallel",
                            "Build Strategy": "Reuse Existing Module" if row["Type"] == "Reporting" else "Build from Scratch",
                            "Status": "Planned",
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )
    st.session_state["roadmap_tasks"] = roadmap


def evaluate_tech_lifecycle(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work["Support End"] = pd.to_datetime(work["Support End"], errors="coerce")
    today = pd.Timestamp(date.today())
    days_left = (work["Support End"] - today).dt.days.fillna(9999)
    work["Risk Status"] = days_left.apply(lambda x: "High" if x < 180 else "Medium" if x < 365 else "Low")
    work["Recommendation"] = work["Risk Status"].map({"Low": "Continue", "Medium": "Upgrade", "High": "Replace"})
    work["Impact Score"] = work["Risk Status"].map({"Low": 1, "Medium": 2, "High": 3})
    work["Suggested Action Window"] = work["Risk Status"].map({"Low": "Next planning cycle", "Medium": "Next 2 quarters", "High": "Immediate review"})
    return work


def generate_project_summary_text(df: pd.DataFrame, project_name: str | None = None) -> str:
    metrics = build_status_metrics(df)
    project_label = project_name or st.session_state["scan_selected_project"]
    return (
        f"### Project Summary\n"
        f"- Project: **{project_label}**\n"
        f"- Total tasks: **{len(df)}**\n"
        f"- In progress: **{metrics['In Progress']['count']}**\n"
        f"- Review queue: **{metrics['Review']['count']}**\n"
        f"- Done: **{metrics['Done']['count']}**\n"
        f"- Overdue: **{int((df['Due Risk'] == 'Overdue').sum())}**"
    )


def build_stakeholder_update(df: pd.DataFrame, project_name: str | None = None) -> str:
    metrics = build_status_metrics(df)
    project_label = project_name or st.session_state["scan_selected_project"]
    return (
        f"{APP_TITLE} update for {project_label}:\n\n"
        f"- Completed work: {metrics['Done']['count']} task(s)\n"
        f"- Active delivery flow: {metrics['In Progress']['count'] + metrics['Review']['count']} task(s)\n"
        f"- Key risk: {int((df['Due Risk'] == 'Overdue').sum())} overdue item(s)\n"
        "- Next step: clear review backlog and protect upcoming milestone commitments."
    )


def generate_governance_pack(df: pd.DataFrame) -> str:
    overdue = df[df["Due Risk"] == "Overdue"]
    active = df[df["Status"].isin(["In Progress", "Review"])]
    return (
        "### Governance Pack\n"
        f"- Active delivery items: **{len(active)}**\n"
        f"- Overdue items needing governance attention: **{len(overdue)}**\n"
        f"- Resource owners with the highest flow pressure: **{', '.join(build_resource_utilization(df).head(3)['Owner'].tolist())}**\n"
        "- Recommended governance action: review blocked dependencies, ad hoc scope, and decision turn-around time."
    )


def build_summary_text(summary_type: str, df: pd.DataFrame, project_name: str | None = None) -> str:
    if summary_type == "Executive Summary":
        return (
            f"Executive view for {project_name or st.session_state['scan_selected_project']}: "
            f"{int((df['Status'] == 'Done').sum())} tasks are complete, "
            f"{int((df['Status'].isin(['In Progress', 'Review'])).sum())} are actively moving, and "
            f"{int((df['Due Risk'] == 'Overdue').sum())} require escalation."
        )
    if summary_type == "Risk Summary":
        overdue = df[df["Due Risk"] == "Overdue"]
        return "Risk Summary:\n" + "\n".join(
            [f"- {row['Task Name']} owned by {row['Owner']} is overdue." for _, row in overdue.head(8).iterrows()]
        ) if not overdue.empty else "Risk Summary:\n- No immediate overdue risk detected."
    if summary_type == "Stakeholder Summary":
        return build_stakeholder_update(df, project_name)
    return generate_project_summary_text(df, project_name)


def build_meeting_pack(meeting_type: str, project: str, df: pd.DataFrame) -> str:
    open_actions = st.session_state["reports_action_tracker"]
    open_actions = open_actions[open_actions["Status"] != "Closed"]
    overdue = df[df["Due Risk"] == "Overdue"]
    lines = [f"{meeting_type} pack for {project}", "", "Agenda:"]
    if meeting_type == "Daily Scrum":
        lines.extend([
            "1. Yesterday / today focus",
            "2. Blockers",
            "3. Decision support needed",
        ])
    elif meeting_type == "Governance Review":
        lines.extend([
            "1. Delivery health",
            "2. Risks and dependencies",
            "3. Actions requiring approval",
        ])
    else:
        lines.extend(["1. Progress", "2. Risks", "3. Decisions / next steps"])
    lines.append("")
    lines.append("Talking points:")
    for _, row in overdue.head(5).iterrows():
        lines.append(f"- Escalate {row['Task Name']} with {row['Owner']} due {format_date(row['Planned End'])}")
    for _, row in open_actions.head(5).iterrows():
        lines.append(f"- Action check: {row['Action']} ({row['Owner']})")
    return "\n".join(lines)


def build_agile_guidance(use_case: str, df: pd.DataFrame) -> str:
    if use_case == "Daily Scrum Focus":
        return generate_daily_scrum(df)
    if use_case == "Sprint Planning Clarity":
        backlog = df[df["Status"] == "To Do"]["Task Name"].head(6).tolist()
        return "Sprint Planning Clarity:\n- Proposed focus:\n" + "\n".join([f"  - {item}" for item in backlog]) if backlog else "No backlog items found."
    if use_case == "Backlog Refinement":
        return "Backlog Refinement:\n- Confirm acceptance criteria\n- Clarify dependencies\n- Split oversized tasks\n- Validate owner and due date"
    if use_case == "Retrospective Questions":
        return "Retrospective Questions:\n- What slowed us down this sprint?\n- Which review handoffs created wait time?\n- What should we stop carrying as ad hoc work?\n- Where did ownership become unclear?"
    return "Scrum Anti-Patterns:\n- Too much work entering mid-cycle\n- Review queue growing without exit criteria\n- Overloaded owners carrying critical path work"


def build_roadmap_summary_text(roadmap_df: pd.DataFrame, feasibility: dict[str, Any]) -> str:
    if roadmap_df.empty:
        return "### Roadmap Summary\n- No roadmap tasks are available yet."
    return (
        f"### Roadmap Summary\n"
        f"- Project: **{st.session_state['roadmap_project_name']}**\n"
        f"- Planned work items: **{len(roadmap_df)}**\n"
        f"- Teams engaged: **{roadmap_df['Team'].nunique()}**\n"
        f"- Feasibility: **{feasibility['status']}**\n"
        f"- Delivery window: **{format_date(roadmap_df['Start Date'].min())} -> {format_date(roadmap_df['End Date'].max())}**"
    )


def build_technology_summary_text(df: pd.DataFrame) -> str:
    if df.empty:
        return "### Technology Lifecycle Summary\n- No lifecycle items are tracked yet."
    return (
        f"### Technology Lifecycle Summary\n"
        f"- Applications tracked: **{len(df)}**\n"
        f"- High risk platforms: **{int((df['Risk Status'] == 'High').sum())}**\n"
        f"- Upgrade / replace actions: **{int(df['Recommendation'].isin(['Upgrade', 'Replace']).sum())}**\n"
        f"- Highest exposure owner: **{df['Owner'].mode().iloc[0]}**"
    )


def build_roadmap_stakeholder_update(roadmap_df: pd.DataFrame) -> str:
    if roadmap_df.empty:
        return f"{APP_TITLE} roadmap update:\n\n- No roadmap tasks are available yet."
    return (
        f"{APP_TITLE} roadmap update for {st.session_state['roadmap_project_name']}:\n\n"
        f"- Planned tasks: {len(roadmap_df)}\n"
        f"- Teams engaged: {roadmap_df['Team'].nunique()}\n"
        f"- Planned start: {format_date(roadmap_df['Start Date'].min())}\n"
        f"- Planned finish: {format_date(roadmap_df['End Date'].max())}\n"
        "- Next step: validate dependencies and protect the critical delivery window."
    )


def build_technology_stakeholder_update(df: pd.DataFrame) -> str:
    return (
        f"{APP_TITLE} lifecycle update:\n\n"
        f"- Applications tracked: {len(df)}\n"
        f"- High-risk items: {int((df['Risk Status'] == 'High').sum())}\n"
        f"- Recommended upgrade / replace actions: {int(df['Recommendation'].isin(['Upgrade', 'Replace']).sum())}\n"
        "- Next step: confirm ownership and align upgrade action windows with active delivery plans."
    )


def build_roadmap_governance_pack(roadmap_df: pd.DataFrame) -> str:
    if roadmap_df.empty:
        return "### Governance Pack\n- No roadmap items available for governance review."
    return (
        "### Governance Pack\n"
        f"- Longest-running workstream: **{roadmap_df.sort_values('Duration', ascending=False).iloc[0]['Task Name']}**\n"
        f"- Parallel tasks planned: **{int((roadmap_df['Execution'] == 'Parallel').sum())}**\n"
        f"- Reuse-led items: **{int((roadmap_df['Build Strategy'] != 'Build from Scratch').sum())}**\n"
        "- Recommended governance action: validate sequencing, reuse assumptions, and resource ownership before baseline sign-off."
    )


def build_technology_governance_pack(df: pd.DataFrame) -> str:
    return (
        "### Governance Pack\n"
        f"- High-risk lifecycle items: **{int((df['Risk Status'] == 'High').sum())}**\n"
        f"- Immediate review candidates: **{int((df['Suggested Action Window'] == 'Immediate review').sum())}**\n"
        f"- Affected projects: **{df['Impacted Projects'].str.split(', ').explode().nunique()}**\n"
        "- Recommended governance action: review unsupported versions before they become delivery blockers."
    )


def build_source_summary_text(summary_type: str, source_engine: str, context_project: str | None = None) -> str:
    if source_engine == "scan":
        return build_summary_text(summary_type, current_filtered_scan_df(context_project).copy(), context_project)
    if source_engine == "roadmap":
        roadmap_df = build_roadmap_table()
        feasibility = roadmap_feasibility(roadmap_df)
        if summary_type == "Risk Summary":
            return "Risk Summary:\n" + "\n".join([f"- {item}" for item in feasibility["risks"]])
        if summary_type == "Stakeholder Summary":
            return build_roadmap_stakeholder_update(roadmap_df)
        if summary_type == "Executive Summary":
            return (
                f"Executive roadmap view for {st.session_state['roadmap_project_name']}: "
                f"{len(roadmap_df)} planned tasks across {roadmap_df['Team'].nunique()} teams with an overall status of {feasibility['status']}."
            )
        return build_roadmap_summary_text(roadmap_df, feasibility)
    tech_df = evaluate_tech_lifecycle(st.session_state["tech_lifecycle_df"])
    if summary_type == "Risk Summary":
        high_risk = tech_df[tech_df["Risk Status"] == "High"]
        if high_risk.empty:
            return "Risk Summary:\n- No high-risk lifecycle items detected."
        return "Risk Summary:\n" + "\n".join([f"- {row['Application']} is nearing support end." for _, row in high_risk.iterrows()])
    if summary_type == "Stakeholder Summary":
        return build_technology_stakeholder_update(tech_df)
    if summary_type == "Executive Summary":
        return (
            f"Executive lifecycle view: {len(tech_df)} applications tracked, "
            f"{int((tech_df['Risk Status'] == 'High').sum())} high-risk items, and "
            f"{int(tech_df['Recommendation'].isin(['Upgrade', 'Replace']).sum())} actions needing planning."
        )
    return build_technology_summary_text(tech_df)


def build_source_meeting_pack(meeting_type: str, source_engine: str, context_project: str | None = None) -> str:
    if source_engine == "scan":
        return build_meeting_pack(meeting_type, context_project or st.session_state["scan_selected_project"], current_filtered_scan_df(context_project).copy())
    if source_engine == "roadmap":
        roadmap_df = build_roadmap_table()
        lines = [f"{meeting_type} pack for {st.session_state['roadmap_project_name']}", "", "Agenda:"]
        lines.extend(["1. Scope and milestone alignment", "2. Dependency review", "3. Resource readiness"])
        lines.append("")
        lines.append("Talking points:")
        for _, row in roadmap_df.sort_values("End Date").head(5).iterrows():
            lines.append(f"- Confirm {row['Task Name']} with {row['Team']} by {format_date(row['End Date'])}")
        return "\n".join(lines)
    tech_df = evaluate_tech_lifecycle(st.session_state["tech_lifecycle_df"])
    lines = [f"{meeting_type} pack for Technology Lifecycle", "", "Agenda:", "1. EOL exposure", "2. Upgrade windows", "3. Delivery impact", "", "Talking points:"]
    for _, row in tech_df.sort_values("Impact Score", ascending=False).head(5).iterrows():
        lines.append(f"- Review {row['Application']} ({row['Current Version']}) with {row['Owner']} - {row['Recommendation']}")
    return "\n".join(lines)


def build_source_guidance(use_case: str, source_engine: str, context_project: str | None = None) -> str:
    if source_engine == "scan":
        return build_agile_guidance(use_case, current_filtered_scan_df(context_project).copy())
    if source_engine == "roadmap":
        roadmap_df = build_roadmap_table()
        if use_case == "Scope Review":
            return "Scope Review:\n- Validate scope boundaries\n- Confirm business outcomes\n- Remove non-critical asks before baseline"
        if use_case == "Plan Readiness":
            return f"Plan Readiness:\n- Planned tasks: {len(roadmap_df)}\n- Teams involved: {roadmap_df['Team'].nunique()}\n- Validate approvals, owners, and start readiness."
        if use_case == "Dependency Review":
            deps = roadmap_df[roadmap_df["Dependency"].astype(str).str.strip() != ""]
            return "Dependency Review:\n" + ("\n".join([f"- {row['Task Name']} depends on {row['Dependency']}" for _, row in deps.iterrows()]) if not deps.empty else "- No explicit roadmap dependencies were entered.")
        return "Timeline Compression:\n- Increase reuse where possible\n- Run design and build overlap carefully\n- Move non-critical work out of the first milestone"
    tech_df = evaluate_tech_lifecycle(st.session_state["tech_lifecycle_df"])
    if use_case == "Lifecycle Risk Review":
        return "Lifecycle Risk Review:\n" + "\n".join([f"- {row['Application']} is {row['Risk Status']} risk." for _, row in tech_df.iterrows()])
    if use_case == "Upgrade Prioritization":
        return "Upgrade Prioritization:\n" + "\n".join([f"- {row['Application']}: {row['Recommendation']}" for _, row in tech_df.sort_values('Impact Score', ascending=False).iterrows()])
    return "Release Readiness:\n- Confirm no release depends on unsupported versions\n- Align lifecycle remediation with release trains\n- Track owner approval for high-risk platforms"


def configure_chart(fig) -> None:
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
        font=dict(family="Inter, Segoe UI, Arial, sans-serif", color="#172a46", size=12),
        title=dict(x=0, xanchor="left", font=dict(size=16), pad=dict(t=10, b=8)),
        legend=dict(orientation="h", y=-0.25, x=0, xanchor="left", font=dict(size=11), title_text=""),
        margin=dict(l=20, r=20, t=72, b=96),
        height=360,
        hoverlabel=dict(bgcolor="#10203f", font_color="white"),
        uniformtext=dict(minsize=10, mode="hide"),
        colorway=["#2558d6", "#19a4a1", "#d39020", "#d95368", "#6b7a90"],
    )
    trace_types = {getattr(trace, "type", "") for trace in fig.data}
    for trace in fig.data:
        trace_type = getattr(trace, "type", "")
        if trace_type == "bar":
            try:
                trace.marker.line = {"width": 0}
            except Exception:
                pass
        if trace_type in {"pie", "sunburst", "treemap"}:
            try:
                trace.marker.line = {"color": "rgba(255,255,255,0.92)", "width": 2}
            except Exception:
                pass
        if trace_type == "pie":
            try:
                trace.textinfo = "percent"
                trace.sort = False
            except Exception:
                pass
        if trace_type == "sunburst":
            try:
                trace.insidetextorientation = "radial"
            except Exception:
                pass
    if "sunburst" in trace_types:
        fig.update_layout(showlegend=False, margin=dict(l=20, r=20, t=72, b=20))
    try:
        fig.update_xaxes(automargin=True)
        fig.update_yaxes(automargin=True)
    except Exception:
        pass


def status_palette() -> dict[str, str]:
    return {
        "To Do": "#6b7a90",
        "In Progress": "#2558d6",
        "Review": "#d39020",
        "Done": "#1c8a63",
    }


def _default_scan_df(project_name: str, alt: bool = False) -> pd.DataFrame:
    rows = [
        ("T001", "Task 1", "To Do", "David", "Backend Development", "2026-04-01", "2026-04-05", "", 0),
        ("T002", "Task 2", "In Progress", "Priya", "Backend Development", "2026-04-02", "2026-04-07", "T001", 35),
        ("T003", "Task 3", "Review", "John", "QA/Testing", "2026-04-03", "2026-04-08", "T002", 75),
        ("T004", "Task 4", "Done", "Arun", "Frontend Development", "2026-03-29", "2026-04-02", "", 100),
        ("T005", "Task 5", "To Do", "Kiran", "Frontend Development", "2026-04-05", "2026-04-11", "", 0),
        ("T006", "Task 6", "In Progress", "Priya", "Backend Development", "2026-04-04", "2026-04-09", "T003", 45),
        ("T007", "Task 7", "Review", "Meera", "QA/Testing", "2026-04-04", "2026-04-10", "T006", 60),
        ("T008", "Task 8", "Done", "David", "Backend Development", "2026-03-28", "2026-04-01", "", 100),
    ]
    if alt:
        rows = [
            ("T101", "Migration Plan", "To Do", "Sana", "Data Engineering", "2026-04-06", "2026-04-12", "", 0),
            ("T102", "API Mapping", "In Progress", "Priya", "Backend Development", "2026-04-05", "2026-04-10", "", 40),
            ("T103", "UX Flow", "Review", "Anika", "UI/UX Design", "2026-04-04", "2026-04-08", "", 70),
            ("T104", "Infra Readiness", "Done", "Maya", "DevOps", "2026-03-29", "2026-04-03", "", 100),
        ]
    df = pd.DataFrame(rows, columns=["Task ID", "Task Name", "Status", "Owner", "Team", "Planned Start", "Planned End", "Dependencies", "Percent Complete"])
    df["Project"] = project_name
    df["Planned Start"] = pd.to_datetime(df["Planned Start"])
    df["Planned End"] = pd.to_datetime(df["Planned End"])
    df["Actual Start"] = pd.NaT
    df["Actual End"] = pd.NaT
    df["Due Risk"] = df.apply(compute_due_risk, axis=1)
    return df[["Project", "Task ID", "Task Name", "Status", "Owner", "Team", "Planned Start", "Planned End", "Actual Start", "Actual End", "Dependencies", "Percent Complete", "Due Risk"]]


def _default_team_df() -> pd.DataFrame:
    return pd.DataFrame(
        TEAM_LIBRARY,
        columns=["Team", "Resources", "Skill Level", "Resource Names", "Allocation %", "Use Team"],
    )


def _default_holiday_df() -> pd.DataFrame:
    return pd.DataFrame(HOLIDAY_SEED, columns=["Date", "Holiday"])


def _default_development_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ("Core Workflow", "Build from Scratch", "No", 0, 0, "Moderate"),
            ("Dashboard Layer", "Reuse Existing Module", "Yes", 4, 2, "Low"),
            ("Notification Service", "API-led", "Yes", 3, 1, "Medium"),
        ],
        columns=["Module", "Approach", "AI-assisted", "API Count", "Validated APIs", "Risk"],
    )


def _default_roadmap_tasks() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ("R001", "Requirement Discovery", "Business Analyst", "Kavya", 5, "", "Sequential", "Build from Scratch", "Planned"),
            ("R002", "Solution Design", "UI/UX Design", "Anika", 6, "R001", "Sequential", "Build from Scratch", "Planned"),
            ("R003", "Core Build", "Backend Development", "Priya", 18, "R002", "Parallel", "Build from Scratch", "Planned"),
            ("R004", "Experience Layer", "Frontend Development", "Kiran", 14, "R002", "Parallel", "Reuse Existing Module", "Planned"),
            ("R005", "QA and Release Readiness", "QA/Testing", "John", 7, "R003,R004", "Sequential", "Build from Scratch", "Planned"),
        ],
        columns=["Task ID", "Task Name", "Team", "Assigned Resource", "Duration", "Dependency", "Execution", "Build Strategy", "Status"],
    )


def _default_technology_df() -> pd.DataFrame:
    return pd.DataFrame(
        TECH_STACK_SEED,
        columns=["Application", "Current Version", "Support End", "Category", "Owner", "Impacted Projects"],
    )


def _default_action_tracker_df() -> pd.DataFrame:
    return pd.DataFrame(
        ACTION_TRACKER_SEED,
        columns=["Action", "Owner", "Team", "Due Date", "Status", "Category", "Project"],
    )


def _default_raid_df() -> pd.DataFrame:
    return pd.DataFrame(
        RAID_SEED,
        columns=["Type", "Item", "Severity", "Owner", "Status", "Project"],
    )


def _default_ad_hoc_df() -> pd.DataFrame:
    return pd.DataFrame(
        AD_HOC_SEED,
        columns=["Project", "Request", "Type", "Owner", "Team", "Due Date", "Status", "Priority"],
    )


def format_date(value: Any) -> str:
    if pd.isna(value):
        return "TBD"
    try:
        return pd.to_datetime(value).strftime("%d %b %Y")
    except Exception:
        return str(value)
