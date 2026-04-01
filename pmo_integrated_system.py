import streamlit as st
import pandas as pd
import json
import os
import plotly.express as px
from datetime import datetime
from kanban_dnd_component import render_kanban_board
from metric_cards_component import render_metric_cards
from project_scan_workspace import render_project_scan_workspace
from roadmap_workspace import render_roadmap_workspace

# --- 1. THE STICKY "FREEZE PANE" ENGINE ---
st.set_page_config(page_title="PMO AI Command Center", layout="wide")
LOG_FILE = "pmo_history_log.txt"
STATUS_COLORS = {
    "To Do": "#64748b",
    "In Progress": "#2457d6",
    "Review": "#d97706",
    "Done": "#059669",
}

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@500;600;700;800&display=swap');
    :root {
        --bg-0: #f5f9ff;
        --bg-1: #e9f0fb;
        --panel-0: rgba(255, 255, 255, 0.92);
        --panel-1: rgba(241, 246, 255, 0.94);
        --border-soft: rgba(148, 163, 184, 0.22);
        --ink-900: #0f172a;
        --ink-700: #334155;
        --ink-500: #64748b;
        --primary-700: #173ea5;
        --primary-600: #2457d6;
        --primary-500: #3b82f6;
        --secondary-700: #0f766e;
        --secondary-500: #14b8a6;
        --success-700: #047857;
        --success-500: #10b981;
        --warning-600: #d97706;
        --surface-shadow: 0 24px 60px rgba(15, 23, 42, 0.10);
        --card-shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
        --radius-xl: 22px;
        --radius-lg: 18px;
    }

    html, body, [data-testid="stAppViewContainer"], section[data-testid="stSidebar"] {
        font-family: "Manrope", "Aptos", "Segoe UI", sans-serif !important;
    }
    button, input, select, textarea {
        font-family: inherit !important;
    }

    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(circle at top left, rgba(36, 87, 214, 0.14), transparent 32%),
            radial-gradient(circle at top right, rgba(20, 184, 166, 0.16), transparent 28%),
            linear-gradient(180deg, var(--bg-0) 0%, var(--bg-1) 100%);
    }

    .block-container {
        max-width: 1520px;
        padding-top: 1.8rem;
        padding-bottom: 2rem;
    }

    header[data-testid="stHeader"] {
        z-index: 1000 !important;
        background: rgba(245, 249, 255, 0.72);
        backdrop-filter: blur(16px);
        border-bottom: 1px solid rgba(148, 163, 184, 0.18);
    }
    [data-testid="collapsedControl"] {
        position: fixed !important;
        top: 0.9rem !important;
        left: 0.9rem !important;
        z-index: 1002 !important;
        width: 46px !important;
        height: 46px !important;
        margin-left: 0 !important;
        overflow: hidden !important;
        font-size: 0 !important;
        line-height: 0 !important;
        color: transparent !important;
    }
    [data-testid="collapsedControl"] > * {
        font-size: 0 !important;
        line-height: 0 !important;
        color: transparent !important;
    }
    [data-testid="collapsedControl"] button,
    [data-testid="stSidebarCollapseButton"] button,
    section[data-testid="stSidebar"] button[kind="header"] {
        width: 44px !important;
        height: 44px !important;
        min-height: 44px !important;
        border-radius: 14px !important;
        border: 1px solid rgba(36, 87, 214, 0.16) !important;
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.96) 0%, rgba(232, 240, 250, 0.96) 100%) !important;
        color: var(--primary-700) !important;
        box-shadow: 0 14px 26px rgba(15, 23, 42, 0.10) !important;
        transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease !important;
    }
    [data-testid="collapsedControl"] button,
    [data-testid="stSidebarCollapseButton"] button,
    section[data-testid="stSidebar"] button[kind="header"] {
        font-size: 0 !important;
        line-height: 0 !important;
        color: transparent !important;
        position: relative !important;
        overflow: hidden !important;
    }
    [data-testid="collapsedControl"] button *,
    [data-testid="stSidebarCollapseButton"] button *,
    section[data-testid="stSidebar"] button[kind="header"] * {
        color: transparent !important;
        font-size: 0 !important;
        line-height: 0 !important;
    }
    [data-testid="collapsedControl"] button::before,
    [data-testid="stSidebarCollapseButton"] button::before,
    section[data-testid="stSidebar"] button[kind="header"]::before {
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        color: var(--primary-700);
        font-size: 22px;
        line-height: 1;
        font-weight: 800;
        content: "";
    }
    [data-testid="collapsedControl"] button::before,
    [data-testid="stSidebarCollapseButton"] button::before {
        content: "›";
    }
    section[data-testid="stSidebar"] button[kind="header"]::before {
        content: "‹";
    }
    [data-testid="collapsedControl"] button:hover,
    [data-testid="stSidebarCollapseButton"] button:hover,
    section[data-testid="stSidebar"] button[kind="header"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 18px 28px rgba(15, 23, 42, 0.14) !important;
        background: linear-gradient(135deg, rgba(36, 87, 214, 0.12) 0%, rgba(255, 255, 255, 0.98) 100%) !important;
    }

    [data-testid="stSidebar"] > div:first-child {
        background:
            radial-gradient(circle at top, rgba(59, 130, 246, 0.18), transparent 26%),
            linear-gradient(180deg, #091126 0%, #102245 58%, #13315d 100%) !important;
        border-right: 1px solid rgba(148, 163, 184, 0.18);
    }
    [data-testid="stSidebar"] * {
        color: #f8fbff !important;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        letter-spacing: 0.02em;
    }
    .sidebar-brand {
        padding: 0 0 18px;
        margin-bottom: 16px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }
    .sidebar-brand-title {
        margin: 0;
        font-size: 1.95rem;
        font-weight: 800;
        line-height: 1.05;
        letter-spacing: -0.03em;
    }
    .sidebar-brand-copy {
        margin: 10px 0 0 0;
        color: rgba(239, 246, 255, 0.72);
        font-size: 0.93rem;
        line-height: 1.55;
    }
    .sidebar-section-kicker {
        margin: 18px 0 8px;
        font-size: 0.76rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: rgba(239, 246, 255, 0.62);
        font-weight: 800;
    }
    .sidebar-section-title {
        margin: 0;
        font-size: 1.02rem;
        font-weight: 800;
        color: #f8fbff;
    }
    .sidebar-section-copy {
        margin: 6px 0 0 0;
        color: rgba(239, 246, 255, 0.68);
        font-size: 0.84rem;
        line-height: 1.45;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label {
        background: rgba(255, 255, 255, 0.07) !important;
        border: 1px solid rgba(255, 255, 255, 0.10) !important;
        border-radius: 14px !important;
        padding: 10px 12px !important;
        margin-bottom: 8px !important;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
        background: linear-gradient(135deg, rgba(36, 87, 214, 0.34) 0%, rgba(59, 130, 246, 0.24) 100%) !important;
        border-color: rgba(96, 165, 250, 0.52) !important;
        box-shadow: 0 16px 26px rgba(8, 25, 62, 0.24) !important;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
        background: rgba(255, 255, 255, 0.11) !important;
    }
    [data-testid="stSidebar"] [data-baseweb="select"] > div,
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
        background: rgba(255, 255, 255, 0.08) !important;
        border: 1px solid rgba(255, 255, 255, 0.14) !important;
        border-radius: 16px !important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
        padding: 14px !important;
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
    }
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button {
        background: linear-gradient(135deg, var(--primary-700) 0%, var(--primary-500) 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 14px !important;
        box-shadow: 0 16px 28px rgba(36, 87, 214, 0.24) !important;
        font-weight: 800 !important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] small,
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] span,
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] p {
        color: #eff6ff !important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploaderFile"] {
        background: rgba(255, 255, 255, 0.08) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 16px !important;
        padding: 10px !important;
    }

    div[data-testid="stTabs"] {
        background: linear-gradient(180deg, rgba(255, 255, 255, 0.78) 0%, rgba(240, 246, 255, 0.82) 100%);
        border: 1px solid var(--border-soft);
        border-radius: var(--radius-xl);
        box-shadow: var(--surface-shadow);
        padding: 0.4rem 0.55rem 1.1rem;
    }
    div[data-baseweb="tab-list"] {
        flex-wrap: wrap;
        gap: 8px;
    }
    div[data-testid="stTabs"] button[data-baseweb="tab"] {
        border-radius: 16px;
        color: var(--ink-700);
        font-weight: 700;
        padding: 0.85rem 1rem;
        transition: all 0.18s ease;
    }
    div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, var(--primary-600) 0%, #5b7cf7 100%);
        color: white;
        box-shadow: 0 16px 28px rgba(36, 87, 214, 0.24);
    }

    [data-testid="metric-container"] {
        background: linear-gradient(180deg, var(--panel-0) 0%, var(--panel-1) 100%);
        border: 1px solid var(--border-soft);
        border-radius: 18px;
        box-shadow: var(--card-shadow);
        padding: 14px 16px;
    }
    [data-testid="metric-container"] [data-testid="stMetricLabel"] {
        color: var(--ink-500);
        font-weight: 700;
        letter-spacing: 0.01em;
    }
    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: var(--ink-900);
        font-weight: 800;
    }

    [data-testid="stPlotlyChart"],
    div[data-testid="stDataFrame"] {
        background: linear-gradient(180deg, rgba(255, 255, 255, 0.82) 0%, rgba(241, 246, 255, 0.9) 100%);
        border: 1px solid var(--border-soft);
        border-radius: var(--radius-lg);
        box-shadow: var(--card-shadow);
        padding: 10px;
    }

    .app-hero {
        display: grid;
        grid-template-columns: minmax(0, 1.6fr) minmax(280px, 0.9fr);
        gap: 20px;
        align-items: center;
        padding: 24px 26px;
        margin-bottom: 14px;
        background:
            radial-gradient(circle at top right, rgba(20, 184, 166, 0.16), transparent 24%),
            linear-gradient(135deg, rgba(10, 18, 39, 0.98) 0%, rgba(18, 45, 97, 0.96) 60%, rgba(34, 84, 178, 0.92) 100%);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 26px;
        box-shadow: 0 24px 54px rgba(15, 23, 42, 0.18);
        color: #ffffff;
    }
    .hero-main {
        min-width: 0;
    }
    .hero-panel {
        padding: 18px;
        border-radius: 22px;
        background: linear-gradient(180deg, rgba(255, 255, 255, 0.12) 0%, rgba(255, 255, 255, 0.08) 100%);
        border: 1px solid rgba(255, 255, 255, 0.12);
        backdrop-filter: blur(10px);
    }
    .hero-kicker {
        display: block;
        font-size: 0.76rem;
        text-transform: uppercase;
        letter-spacing: 0.16em;
        color: rgba(255, 255, 255, 0.64);
        font-weight: 800;
    }
    .hero-title {
        margin: 10px 0 10px 0;
        font-size: clamp(1.9rem, 3.2vw, 2.8rem);
        line-height: 1.04;
        font-weight: 800;
        letter-spacing: -0.04em;
    }
    .hero-text {
        margin: 0;
        max-width: 780px;
        color: rgba(255, 255, 255, 0.78);
        font-size: 0.96rem;
        line-height: 1.62;
    }
    .hero-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-top: 16px;
    }
    .hero-meta-chip {
        display: inline-flex;
        align-items: center;
        padding: 7px 11px;
        border-radius: 999px;
        font-size: 0.76rem;
        font-weight: 700;
        border: 1px solid rgba(255, 255, 255, 0.14);
        background: rgba(255, 255, 255, 0.08);
        color: rgba(248, 251, 255, 0.92);
    }
    .hero-panel-label {
        display: block;
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: rgba(255, 255, 255, 0.62);
        font-weight: 800;
    }
    .hero-panel-title {
        display: block;
        margin-top: 10px;
        font-size: 1.5rem;
        font-weight: 800;
        line-height: 1.1;
    }
    .hero-panel-copy {
        margin: 8px 0 0 0;
        color: rgba(255, 255, 255, 0.72);
        font-size: 0.87rem;
        line-height: 1.5;
    }
    .hero-panel-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 10px;
        margin-top: 14px;
    }
    .hero-panel-item {
        padding: 12px 12px 10px;
        border-radius: 16px;
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .hero-panel-value {
        display: block;
        font-size: 1.15rem;
        font-weight: 800;
        color: #ffffff;
    }
    .hero-panel-caption {
        display: block;
        margin-top: 4px;
        font-size: 0.76rem;
        color: rgba(255, 255, 255, 0.62);
        letter-spacing: 0.04em;
        text-transform: uppercase;
        font-weight: 700;
    }
    .workspace-detail-card {
        background: linear-gradient(180deg, rgba(255, 255, 255, 0.94) 0%, rgba(243, 247, 255, 0.98) 100%);
        border: 1px solid var(--border-soft);
        border-radius: 22px;
        padding: 22px;
        box-shadow: var(--card-shadow);
    }
    .workspace-detail-card h4 {
        margin: 0 0 8px 0;
        color: var(--ink-900);
        font-size: 1.05rem;
        font-weight: 800;
    }
    .workspace-detail-card p {
        margin: 0;
        color: var(--ink-700);
        font-size: 0.95rem;
        line-height: 1.6;
    }
    .detail-chip-row {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 14px;
    }
    .detail-chip {
        display: inline-flex;
        align-items: center;
        padding: 7px 10px;
        border-radius: 999px;
        background: rgba(36, 87, 214, 0.08);
        color: var(--primary-700);
        border: 1px solid rgba(36, 87, 214, 0.12);
        font-size: 0.77rem;
        font-weight: 700;
    }
    .detail-stat-card {
        height: 100%;
        background: linear-gradient(180deg, rgba(12, 25, 53, 0.96) 0%, rgba(25, 57, 122, 0.92) 100%);
        border: 1px solid rgba(36, 87, 214, 0.14);
        border-radius: 22px;
        padding: 20px;
        box-shadow: 0 20px 38px rgba(15, 23, 42, 0.14);
    }
    .detail-stat-card h4 {
        margin: 0 0 10px 0;
        color: #ffffff;
        font-size: 1rem;
        font-weight: 800;
    }
    .detail-stat-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 16px;
        padding: 10px 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }
    .detail-stat-row:last-child {
        border-bottom: none;
        padding-bottom: 0;
    }
    .detail-stat-label {
        color: rgba(255, 255, 255, 0.68);
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 700;
    }
    .detail-stat-value {
        color: #ffffff;
        font-size: 1rem;
        font-weight: 800;
        text-align: right;
    }

    .summary-card {
        background: linear-gradient(180deg, rgba(255, 255, 255, 0.90) 0%, rgba(241, 246, 255, 0.96) 100%);
        border: 1px solid var(--border-soft);
        border-radius: 20px;
        padding: 20px;
        box-shadow: var(--card-shadow);
    }
    .summary-card h4 {
        margin: 0 0 10px 0;
        color: var(--ink-900);
        font-size: 1.02rem;
        font-weight: 800;
    }
    .summary-card p, .summary-card li {
        color: var(--ink-700);
        font-size: 0.95rem;
        line-height: 1.6;
    }
    .insight-chip {
        display: inline-block;
        padding: 8px 12px;
        margin: 8px 8px 0 0;
        border-radius: 999px;
        background: linear-gradient(135deg, rgba(36, 87, 214, 0.12) 0%, rgba(20, 184, 166, 0.14) 100%);
        color: var(--primary-700);
        border: 1px solid rgba(36, 87, 214, 0.14);
        font-size: 0.8rem;
        font-weight: 800;
    }

    div.stButton > button, div.stDownloadButton > button {
        width: 100% !important;
        min-height: 48px;
        border-radius: 14px !important;
        font-weight: 800 !important;
        letter-spacing: 0.01em;
        border: 1px solid transparent !important;
        transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease !important;
    }
    div.stButton > button:hover, div.stDownloadButton > button:hover {
        transform: translateY(-1px);
    }
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--success-700) 0%, var(--success-500) 100%) !important;
        color: #ffffff !important;
        box-shadow: 0 18px 28px rgba(16, 185, 129, 0.22) !important;
    }
    div.stDownloadButton > button[kind="secondary"] {
        background: linear-gradient(135deg, var(--secondary-700) 0%, var(--secondary-500) 100%) !important;
        color: #ffffff !important;
        box-shadow: 0 18px 28px rgba(20, 184, 166, 0.18) !important;
    }
    div.stButton > button[kind="secondary"] {
        background: linear-gradient(135deg, var(--primary-700) 0%, var(--primary-500) 100%) !important;
        color: #ffffff !important;
        box-shadow: 0 18px 28px rgba(36, 87, 214, 0.18) !important;
    }
    div.stButton > button[kind="tertiary"] {
        background: linear-gradient(180deg, rgba(255, 255, 255, 0.96) 0%, rgba(232, 240, 250, 0.96) 100%) !important;
        color: var(--ink-700) !important;
        border-color: rgba(148, 163, 184, 0.22) !important;
        box-shadow: 0 12px 20px rgba(15, 23, 42, 0.08) !important;
    }

    @media (max-width: 980px) {
        .block-container {
            padding-top: 1.05rem;
            padding-left: 0.9rem;
            padding-right: 0.9rem;
        }
        .app-hero {
            grid-template-columns: 1fr;
            padding: 22px 20px;
            border-radius: 24px;
            gap: 16px;
        }
        div[data-testid="stTabs"] {
            padding: 0.35rem 0.35rem 0.9rem;
            border-radius: 20px;
        }
        div[data-testid="stTabs"] button[data-baseweb="tab"] {
            flex: 1 1 calc(50% - 8px);
            min-width: 0;
            justify-content: center;
            padding: 0.8rem 0.85rem;
        }
        .workspace-detail-card,
        .summary-card {
            padding: 18px;
        }
    }
    @media (max-width: 768px) {
        [data-testid="collapsedControl"] {
            top: 0.72rem !important;
            left: 0.7rem !important;
        }
        [data-testid="stSidebar"] > div:first-child {
            padding-top: 0.6rem;
        }
        .block-container {
            padding-left: 0.75rem;
            padding-right: 0.75rem;
        }
        .hero-text,
        .hero-panel-copy {
            font-size: 0.92rem;
        }
        .hero-meta {
            gap: 8px;
        }
        div.stButton > button,
        div.stDownloadButton > button {
            min-height: 44px;
            font-size: 0.95rem !important;
        }
        [data-testid="metric-container"],
        .workspace-detail-card,
        .summary-card {
            border-radius: 18px;
        }
    }
    @media (max-width: 560px) {
        .block-container {
            padding-top: 0.8rem;
        }
        [data-testid="collapsedControl"] {
            top: 0.62rem !important;
            left: 0.62rem !important;
            width: 42px !important;
            height: 42px !important;
        }
        [data-testid="collapsedControl"] button,
        [data-testid="stSidebarCollapseButton"] button,
        section[data-testid="stSidebar"] button[kind="header"] {
            width: 40px !important;
            height: 40px !important;
            min-height: 40px !important;
            border-radius: 12px !important;
        }
        .app-hero {
            padding: 18px 16px;
            border-radius: 20px;
        }
        div[data-testid="stTabs"] button[data-baseweb="tab"] {
            flex: 1 1 100%;
        }
        .hero-title {
            font-size: clamp(1.85rem, 9vw, 2.3rem);
        }
        .hero-panel {
            padding: 16px;
        }
        .hero-panel-grid {
            grid-template-columns: 1fr 1fr;
        }
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. SIDEBAR ENGINE ---
with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-brand">
            <div class="sidebar-brand-title">PMO Control</div>
            <p class="sidebar-brand-copy">Operational navigation for delivery intake, restore points, and workspace switching.</p>
        </div>
        <div class="sidebar-section-kicker">Workspace</div>
        <p class="sidebar-section-title">Mode Selection</p>
        <p class="sidebar-section-copy">Choose the working mode for project scanning or roadmap preparation.</p>
        """,
        unsafe_allow_html=True,
    )
    engine = st.radio("Select Engine", ["🚀 Scan Project", "📅 Create RoadMap"], label_visibility="collapsed")
    st.divider()
    
    if engine == "🚀 Scan Project":
        st.markdown(
            """
            <div class="sidebar-section-kicker">History</div>
            <p class="sidebar-section-title">Restore Point</p>
            <p class="sidebar-section-copy">Jump back to a saved delivery snapshot when you need to audit or recover state.</p>
            """,
            unsafe_allow_html=True,
        )
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r") as f:
                logs = [json.loads(l) for l in f if l.strip()]
            if logs:
                log_opts = [f"{l.get('date')} @ {l.get('timestamp')} | {l.get('filename')}" for l in logs[::-1]]
                sel = st.selectbox("Restore Point", log_opts, label_visibility="collapsed")
                if st.button("Restore Selected", type="secondary", use_container_width=True):
                    ts = sel.split(" @ ")[1].split(" | ")[0]
                    for l in logs:
                        if l.get('timestamp') == ts:
                            st.session_state.db = {sh: pd.read_json(js) for sh, js in l['payload'].items()}
                            st.rerun()

        st.markdown(
            """
            <div class="sidebar-section-kicker">Upload</div>
            <p class="sidebar-section-title">Project Workbook</p>
            <p class="sidebar-section-copy">Import the current XLSX tracker to refresh the workspace with the latest delivery data.</p>
            """,
            unsafe_allow_html=True,
        )
        up = st.file_uploader("Browse XLSX", type="xlsx", label_visibility="collapsed")
        if up: 
            st.session_state.db = pd.read_excel(up, sheet_name=None)
            st.session_state.fn = up.name
    else:
        st.markdown(
            """
            <div class="sidebar-section-kicker">Roadmap</div>
            <p class="sidebar-section-title">Planning Studio</p>
            <p class="sidebar-section-copy">Create an editable project roadmap with working-day timelines, resource planning, module strategy, and Excel-ready outputs.</p>
            """,
            unsafe_allow_html=True,
        )

# --- 3. MAIN APP ---
if engine == "📅 Create RoadMap":
    render_roadmap_workspace()
elif engine == "🚀 Scan Project":
    render_project_scan_workspace()
    st.stop()
elif 'db' in st.session_state and st.session_state.db:
    sheets = list(st.session_state.db.keys())
    st.sidebar.markdown(
        """
        <div class="sidebar-section-kicker">Workspace</div>
        <p class="sidebar-section-title">Active Sheet</p>
        <p class="sidebar-section-copy">Select the delivery sheet that should drive the board, analytics, and AI summary.</p>
        """,
        unsafe_allow_html=True,
    )
    active_sheet = st.sidebar.selectbox("Active Sheet", sheets, label_visibility="collapsed")
    df = st.session_state.db[active_sheet]

    # Column Detection
    c_stat = next((c for c in df.columns if 'status' in c.lower()), 'Status')
    c_own = next((c for c in df.columns if 'owner' in c.lower() or 'assign' in c.lower()), 'Owner')
    c_id, c_name = df.columns[0], df.columns[1]

    def map_k(x):
        v = str(x).lower().strip()
        if 'done' in v or 'complete' in v: return "Done"
        if 'review' in v or 'uat' in v: return "Review"
        if 'progress' in v or 'active' in v: return "In Progress"
        return "To Do"
    df['K_Status'] = df[c_stat].apply(map_k)
    total = len(df)
    done_n = len(df[df['K_Status'] == "Done"])
    in_progress_n = len(df[df['K_Status'] == "In Progress"])
    review_n = len(df[df['K_Status'] == "Review"])
    todo_n = len(df[df['K_Status'] == "To Do"])
    top_owner = df[c_own].mode().iat[0] if not df[c_own].mode().empty else "Unassigned"
    owner_load = df.groupby(c_own).size().sort_values(ascending=False).reset_index(name="Tasks")
    status_summary = df.groupby('K_Status').size().reset_index(name='Tasks')
    completion_pct = int((done_n/total)*100) if total else 0
    active_flow = in_progress_n + review_n
    undo_store = st.session_state.setdefault("undo_stack", {})
    redo_store = st.session_state.setdefault("redo_stack", {})
    undo_store.setdefault(active_sheet, [])
    redo_store.setdefault(active_sheet, [])

    st.markdown(
        f"""
        <div class="app-hero">
            <div class="hero-main">
                <div class="hero-kicker">Enterprise Delivery Workspace</div>
                <div class="hero-title">PMO Command Center</div>
                <p class="hero-text"><b>{active_sheet}</b> is tracking <b>{total}</b> tickets with <b>{active_flow}</b> items currently moving through execution and validation. The board is tuned for portfolio visibility, faster operational review, and confident handoffs between teams.</p>
                <div class="hero-meta">
                    <span class="hero-meta-chip">Active sheet: {active_sheet}</span>
                    <span class="hero-meta-chip">{total} tracked tickets</span>
                    <span class="hero-meta-chip">{active_flow} in active flow</span>
                    <span class="hero-meta-chip">Lead owner: {top_owner}</span>
                </div>
            </div>
            <div class="hero-panel">
                <span class="hero-panel-label">Workspace Brief</span>
                <span class="hero-panel-title">{active_sheet}</span>
                <p class="hero-panel-copy">Compact executive summary for delivery status, ownership concentration, and completion health.</p>
                <div class="hero-panel-grid">
                    <div class="hero-panel-item">
                        <span class="hero-panel-value">{completion_pct}%</span>
                        <span class="hero-panel-caption">Completion</span>
                    </div>
                    <div class="hero-panel-item">
                        <span class="hero-panel-value">{active_flow}</span>
                        <span class="hero-panel-caption">Active Flow</span>
                    </div>
                    <div class="hero-panel-item">
                        <span class="hero-panel-value">{top_owner}</span>
                        <span class="hero-panel-caption">Lead Owner</span>
                    </div>
                    <div class="hero-panel-item">
                        <span class="hero-panel-value">{done_n}</span>
                        <span class="hero-panel-caption">Completed</span>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    metric_selection_key = f"selected_workspace_metric_{active_sheet}"
    if metric_selection_key not in st.session_state:
        st.session_state[metric_selection_key] = "completion"

    metric_cards = [
        {"id": "completion", "label": "Completion", "value": f"{completion_pct}%", "caption": "Stage distribution across the full portfolio", "note": "Use this view to understand where delivery is accumulating.", "pill": "Overview", "accent": STATUS_COLORS["In Progress"]},
        {"id": "active_flow", "label": "Active Flow", "value": str(active_flow), "caption": "Execution and validation workload in motion", "note": "Focus here when the team needs throughput and blocker visibility.", "pill": "Live", "accent": STATUS_COLORS["Review"]},
        {"id": "lead_owner", "label": "Lead Owner", "value": str(top_owner), "caption": "Ownership concentration across assigned work", "note": "Inspect this when you need balancing decisions or support planning.", "pill": "Owner", "accent": STATUS_COLORS["Done"]},
        {"id": "completed", "label": "Completed", "value": str(done_n), "caption": "Closed delivery items ready for review", "note": "Use this for closure reporting and completed-work validation.", "pill": "Closed", "accent": STATUS_COLORS["Done"]},
    ]
    metric_event = render_metric_cards(
        metric_cards,
        selected_id=st.session_state[metric_selection_key],
        key=f"workspace_metric_cards_{active_sheet}",
        height=154,
    )
    if metric_event and metric_event.get("event_id") != st.session_state.get("last_metric_card_event"):
        selected_card = metric_event.get("card_id")
        if selected_card in {card["id"] for card in metric_cards}:
            st.session_state[metric_selection_key] = selected_card
            st.session_state.last_metric_card_event = metric_event.get("event_id")
            st.rerun()

    selected_metric = st.session_state[metric_selection_key]
    stage_percentages = status_summary.copy()
    stage_percentages["Share"] = stage_percentages["Tasks"].apply(lambda value: f"{(value / total * 100):.1f}%" if total else "0.0%")
    active_items = df[df["K_Status"].isin(["In Progress", "Review"])][[c_id, c_name, c_own, "K_Status"]].copy()
    completed_items = df[df["K_Status"] == "Done"][[c_id, c_name, c_own]].copy()
    lead_owner_items = df[df[c_own] == top_owner][[c_id, c_name, "K_Status"]].copy()

    if selected_metric == "completion":
        detail_title = "Completion Detail"
        detail_text = f"The delivery workspace is currently at {completion_pct}% completion. Use this stage distribution to understand how work is spread across delivery, review, and completed states."
        detail_df = stage_percentages.rename(columns={"K_Status": "Stage"})
        detail_chips = [
            f"{todo_n} items queued",
            f"{in_progress_n} in progress",
            f"{review_n} under review",
            f"{done_n} completed",
        ]
        detail_rows = [("Portfolio completion", f"{completion_pct}%"), ("Next focus", "Clear active review path"), ("Largest stage", f"{max(todo_n, in_progress_n, review_n, done_n)} tasks")]
    elif selected_metric == "active_flow":
        detail_title = "Active Flow Detail"
        detail_text = f"There are {active_flow} items in active execution or validation. This view surfaces the tasks currently moving through the delivery pipeline."
        detail_df = active_items.rename(columns={c_id: "Task ID", c_name: "Task", c_own: "Owner", "K_Status": "Stage"})
        detail_chips = [
            f"{in_progress_n} executing",
            f"{review_n} validating",
            f"Lead owner {top_owner}",
        ]
        detail_rows = [("Items in motion", str(active_flow)), ("Execution lane", str(in_progress_n)), ("Validation lane", str(review_n))]
    elif selected_metric == "lead_owner":
        detail_title = "Lead Owner Detail"
        detail_text = f"{top_owner} currently carries the highest ownership load. Review the tasks below to decide whether redistribution or support is needed."
        detail_df = lead_owner_items.rename(columns={c_id: "Task ID", c_name: "Task", "K_Status": "Stage"})
        detail_chips = [
            f"{len(lead_owner_items)} tasks assigned",
            f"Owner spotlight: {top_owner}",
        ]
        detail_rows = [("Lead owner", str(top_owner)), ("Assigned tasks", str(len(lead_owner_items))), ("Portfolio share", f"{(len(lead_owner_items) / total * 100):.1f}%" if total else "0.0%")]
    else:
        detail_title = "Completed Work Detail"
        detail_text = f"{done_n} tasks have reached completion. This view helps leadership review closed work and spot owners delivering the most finished output."
        detail_df = completed_items.rename(columns={c_id: "Task ID", c_name: "Task", c_own: "Owner"})
        detail_chips = [
            f"{done_n} tasks closed",
            "Ready for executive review",
        ]
        detail_rows = [("Completed items", str(done_n)), ("Completion rate", f"{completion_pct}%"), ("Lead owner", str(top_owner))]

    detail_cols = st.columns([1.7, 0.9], gap="small")
    with detail_cols[0]:
        chip_html = "".join(f'<span class="detail-chip">{chip}</span>' for chip in detail_chips)
        st.markdown(
            f"""
            <div class="workspace-detail-card">
                <h4>{detail_title}</h4>
                <p>{detail_text}</p>
                <div class="detail-chip-row">{chip_html}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with detail_cols[1]:
        stat_rows_html = "".join(
            f'<div class="detail-stat-row"><span class="detail-stat-label">{label}</span><span class="detail-stat-value">{value}</span></div>'
            for label, value in detail_rows
        )
        st.markdown(
            f"""
            <div class="detail-stat-card">
                <h4>Operational Snapshot</h4>
                {stat_rows_html}
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.dataframe(detail_df, use_container_width=True, hide_index=True, height=min(420, max(160, 56 + len(detail_df) * 36)))

    t1, t2, t3 = st.tabs(["🛠️ Technical Kanban", "🏛️ Management View", "🤖 AI Consultant"])

    with t1:
        # ACTION TOOLBAR (FREEZE PANE PART 1)
        tb = st.columns([1.05, 1.05, 1.15, 1.15, 4.6], gap="small", vertical_alignment="center")
        undo_clicked = tb[0].button(
            "Undo",
            type="tertiary",
            use_container_width=True,
            disabled=not undo_store[active_sheet],
        )
        redo_clicked = tb[1].button(
            "Redo",
            type="tertiary",
            use_container_width=True,
            disabled=not redo_store[active_sheet],
        )
        save_clicked = tb[2].button(
            "Save State",
            type="primary",
            use_container_width=True,
        )
        extract_data = st.session_state.db[active_sheet].drop(columns=['K_Status'], errors='ignore').to_csv(index=False).encode("utf-8")
        tb[3].download_button(
            "Extract",
            data=extract_data,
            file_name=f"{active_sheet.lower().replace(' ', '_')}_export.csv",
            mime="text/csv",
            type="secondary",
            use_container_width=True,
        )

        if undo_clicked and undo_store[active_sheet]:
            redo_store[active_sheet].append(st.session_state.db[active_sheet].copy(deep=True))
            st.session_state.db[active_sheet] = undo_store[active_sheet].pop()
            st.rerun()

        if redo_clicked and redo_store[active_sheet]:
            undo_store[active_sheet].append(st.session_state.db[active_sheet].copy(deep=True))
            st.session_state.db[active_sheet] = redo_store[active_sheet].pop()
            st.rerun()

        if save_clicked:
            entry = {"date": datetime.now().strftime("%Y-%m-%d"), "timestamp": datetime.now().strftime("%H:%M:%S"), 
                     "filename": st.session_state.get('fn','Project'), "payload": {sh: d.to_json() for sh, d in st.session_state.db.items()}}
            with open(LOG_FILE, "a") as f: f.write(json.dumps(entry) + "\n")
            st.success("Log Updated")

        # KANBAN BOARD (FREEZE PANE PART 2)
        stages = ["To Do", "In Progress", "Review", "Done"]
        board_items = [
            {
                "row_id": idx,
                "task_id": row[c_id],
                "task_name": row[c_name],
                "owner": row[c_own],
                "stage": row["K_Status"],
            }
            for idx, row in df.iterrows()
        ]
        move_event = render_kanban_board(
            board_items,
            stages,
            key=f"kanban_dnd_{active_sheet}",
            height=900,
        )
        if move_event and move_event.get("event_id") != st.session_state.get("last_kanban_move"):
            row_id = move_event.get("row_id")
            to_stage = move_event.get("to_stage")
            if row_id is not None and to_stage in stages:
                undo_store[active_sheet].append(st.session_state.db[active_sheet].copy(deep=True))
                if len(undo_store[active_sheet]) > 25:
                    undo_store[active_sheet].pop(0)
                redo_store[active_sheet].clear()
                st.session_state.db[active_sheet].at[int(row_id), c_stat] = to_stage
                st.session_state.db[active_sheet]["K_Status"] = st.session_state.db[active_sheet][c_stat].apply(map_k)
                st.session_state.last_kanban_move = move_event.get("event_id")
                st.rerun()

        st.divider()
        st.subheader("📊 Master Table")
        st.data_editor(df.drop(columns=['K_Status']), use_container_width=True)

    with t2:
        st.subheader("🏛️ Portfolio Executive View")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Completion", f"{completion_pct}%")
        m2.metric("Total Tickets", total)
        m3.metric("Done", done_n)
        m4.metric("Active Flow", active_flow)

        c1, c2 = st.columns(2)
        with c1:
            fig_pie = px.pie(
                status_summary,
                names='K_Status',
                values='Tasks',
                hole=0.62,
                title="Task Distribution by Stage",
                color='K_Status',
                color_discrete_map=STATUS_COLORS,
            )
            fig_pie.update_traces(textinfo='percent+label')
            fig_pie.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(family="Manrope, Segoe UI, sans-serif", color="#334155"),
                title=dict(font=dict(size=20, color="#0f172a"), x=0.02),
                legend=dict(orientation="h", y=-0.12, x=0),
                margin=dict(t=60, l=10, r=10, b=10),
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with c2:
            sunburst_df = df.copy()
            sunburst_df['Records'] = 1
            fig_sunburst = px.sunburst(
                sunburst_df,
                path=['K_Status', c_own],
                values='Records',
                color='K_Status',
                color_discrete_map=STATUS_COLORS,
                title="Status to Owner Workload Map",
            )
            fig_sunburst.update_layout(
                margin=dict(t=58, l=0, r=0, b=0),
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(family="Manrope, Segoe UI, sans-serif", color="#334155"),
                title=dict(font=dict(size=20, color="#0f172a"), x=0.02),
            )
            st.plotly_chart(fig_sunburst, use_container_width=True)

    with t3:
        st.subheader("🤖 AI Consultant")
        risk_stage = "Review" if review_n >= in_progress_n else "In Progress"
        focus_owner = owner_load.iloc[0][c_own] if not owner_load.empty else "Unassigned"
        next_action = (
            f"Prioritize {review_n} review items for closure this cycle."
            if review_n
            else f"Pull forward {in_progress_n} active tasks to increase throughput."
        )

        left, right = st.columns([1.4, 1])
        with left:
            st.markdown(
                f"""
                <div class="summary-card">
                    <h4>Project Summary</h4>
                    <p><b>{active_sheet}</b> is currently <b>{completion_pct}% complete</b> with <b>{in_progress_n + review_n}</b> active items in flight. The busiest owner is <b>{focus_owner}</b>, and the next operational attention point is <b>{risk_stage}</b>.</p>
                    <p><b>Recommended next move:</b> {next_action}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                f"""
                <div class="summary-card" style="margin-top:16px;">
                    <h4>Interactive Highlights</h4>
                    <span class="insight-chip">{todo_n} ready to start</span>
                    <span class="insight-chip">{in_progress_n} in execution</span>
                    <span class="insight-chip">{review_n} awaiting validation</span>
                    <span class="insight-chip">{done_n} completed</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with right:
            st.markdown(
                """
                <div class="summary-card">
                    <h4>Leadership Notes</h4>
                    <ul>
                        <li>Use the Kanban board to rebalance ownership directly from overloaded lanes.</li>
                        <li>Management View now shows both distribution and hierarchy, helping spot concentration risks faster.</li>
                        <li>Closing review-stage tasks first will improve visible completion without increasing delivery risk.</li>
                    </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )

            prompt = st.chat_input("Ask for a delivery summary, risk check, or owner workload insight...")
            if prompt:
                st.markdown(
                    f"""
                    <div class="summary-card" style="margin-top:16px;">
                        <h4>AI Response</h4>
                        <p><b>Request:</b> {prompt}</p>
                        <p>Based on the live board, <b>{active_sheet}</b> has <b>{todo_n}</b> tasks waiting, <b>{in_progress_n}</b> active, <b>{review_n}</b> in validation, and <b>{done_n}</b> completed. The best immediate action is to support <b>{focus_owner}</b> only if their active load remains above team average; otherwise, focus on clearing the <b>{risk_stage}</b> lane to improve end-to-end flow.</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

else:
    st.info("👈 Use Sidebar to Scan Project or Restore History.")
