import json
from io import BytesIO

import pandas as pd
import plotly.express as px
import streamlit as st

from word_export import build_word_report


PRODUCT_NAME = "VertexOne DeliveryOS"
ASSET_COLUMNS = [
    "Employee Name",
    "Employee ID",
    "Employee Status",
    "Engaged for Project",
    "Asset Category",
    "Provisioning Type",
    "Asset Serial Number",
    "Asset Status",
]


def _inject_styles():
    st.markdown(
        """
        <style>
        div.stButton > button,
        div.stDownloadButton > button {
            height: 3.2rem;
            border-radius: 1rem;
            font-weight: 700;
            border: 1px solid rgba(37, 99, 235, 0.16);
            box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
        }
        div.stButton > button[kind="primary"],
        div.stDownloadButton > button[kind="primary"] {
            background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 55%, #38bdf8 100%);
            color: #ffffff;
            border: none;
        }
        div.stButton > button[kind="secondary"],
        div.stDownloadButton > button[kind="secondary"] {
            background: linear-gradient(135deg, #ffffff 0%, #eff6ff 100%);
            color: #1e3a8a;
        }
        div[data-testid="stDataFrameResizable"] {
            max-width: 100%;
            overflow-x: auto !important;
            border-radius: 1.25rem;
            border: 1px solid rgba(148, 163, 184, 0.22);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _default_asset_df():
    return pd.DataFrame(
        [
            {"Employee Name": "Asha", "Employee ID": "EMP001", "Employee Status": "Active", "Engaged for Project": "VertexOne Program", "Asset Category": "Laptop", "Provisioning Type": "Company Owned", "Asset Serial Number": "LT-10021", "Asset Status": "Active"},
            {"Employee Name": "Rahul", "Employee ID": "EMP002", "Employee Status": "Active", "Engaged for Project": "Client Delivery", "Asset Category": "Monitor", "Provisioning Type": "Vendor Provisioned", "Asset Serial Number": "MN-20311", "Asset Status": "Active"},
        ]
    )


def _clean_asset_df(asset_df):
    clean_df = pd.DataFrame(asset_df).copy()
    for column in ASSET_COLUMNS:
        if column not in clean_df.columns:
            clean_df[column] = ""
    clean_df = clean_df[ASSET_COLUMNS].fillna("")
    clean_df["Employee Status"] = clean_df["Employee Status"].where(clean_df["Employee Status"].isin(["Active", "Inactive", "Separated"]), "Active")
    clean_df["Asset Status"] = clean_df["Asset Status"].where(clean_df["Asset Status"].isin(["Active", "Inactive"]), "Active")
    clean_df["Provisioning Type"] = clean_df["Provisioning Type"].where(clean_df["Provisioning Type"].isin(["Company Owned", "Vendor Provisioned"]), "Company Owned")
    return clean_df.reset_index(drop=True)


def _snapshot(asset_df):
    return _clean_asset_df(asset_df).to_dict(orient="records")


def _track_history(asset_df):
    st.session_state.setdefault("asset_v2_undo", [])
    st.session_state.setdefault("asset_v2_redo", [])
    fp = json.dumps(_snapshot(asset_df), sort_keys=True, default=str)
    if st.session_state.pop("asset_v2_skip_history", False):
        st.session_state["asset_v2_last_snapshot"] = _snapshot(asset_df)
        st.session_state["asset_v2_last_fp"] = fp
        return
    last_fp = st.session_state.get("asset_v2_last_fp")
    last_snapshot = st.session_state.get("asset_v2_last_snapshot")
    if last_fp is None:
        st.session_state["asset_v2_last_snapshot"] = _snapshot(asset_df)
        st.session_state["asset_v2_last_fp"] = fp
        return
    if fp != last_fp and last_snapshot is not None:
        st.session_state["asset_v2_undo"].append(last_snapshot)
        st.session_state["asset_v2_redo"].clear()
        st.session_state["asset_v2_last_snapshot"] = _snapshot(asset_df)
        st.session_state["asset_v2_last_fp"] = fp


def _restore(snapshot):
    st.session_state["asset_management_v2_df"] = pd.DataFrame(snapshot)
    st.session_state["asset_v2_skip_history"] = True


def _build_excel(asset_df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        asset_df.to_excel(writer, index=False, sheet_name="Asset Register")
    output.seek(0)
    return output.getvalue()


def render_asset_management_workspace_v2():
    _inject_styles()
    st.markdown(
        f"""
        <div class="app-hero">
            <div class="hero-main">
                <div class="hero-kicker">Asset Management</div>
                <div class="hero-title">{PRODUCT_NAME}</div>
                <p class="hero-text">Manage employee-assigned physical assets, provisioning ownership, engagement context, and operational activity from a single enterprise register.</p>
            </div>
            <div class="hero-panel">
                <span class="hero-panel-label">Control Scope</span>
                <span class="hero-panel-title">Enterprise Asset Register</span>
                <p class="hero-panel-copy">Track asset ownership, employee activity, and project engagement from one operational surface.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    upload = st.file_uploader("Upload Asset Register", type=["xlsx", "csv"], label_visibility="collapsed", key="asset_v2_upload")
    if upload is not None:
        st.session_state["asset_management_v2_df"] = pd.read_csv(upload) if upload.name.lower().endswith(".csv") else pd.read_excel(upload)

    if "asset_management_v2_df" not in st.session_state:
        st.session_state["asset_management_v2_df"] = _default_asset_df()

    asset_df = _clean_asset_df(st.session_state["asset_management_v2_df"])
    metrics = st.columns(4, gap="small")
    metrics[0].metric("Total Assets", len(asset_df))
    metrics[1].metric("Active Employees", int((asset_df["Employee Status"] == "Active").sum()))
    metrics[2].metric("Active Assets", int((asset_df["Asset Status"] == "Active").sum()))
    metrics[3].metric("Projects Engaged", asset_df["Engaged for Project"].replace("", pd.NA).dropna().nunique())

    toolbar = st.columns([1, 1, 1, 1, 4], gap="small")
    st.session_state.setdefault("asset_v2_undo", [])
    st.session_state.setdefault("asset_v2_redo", [])
    if toolbar[0].button("↶ Undo", key="asset_v2_undo_btn", use_container_width=True, disabled=not st.session_state["asset_v2_undo"]):
        snapshot = st.session_state["asset_v2_undo"].pop()
        st.session_state["asset_v2_redo"].append(_snapshot(asset_df))
        _restore(snapshot)
        st.rerun()
    if toolbar[1].button("↷ Redo", key="asset_v2_redo_btn", use_container_width=True, disabled=not st.session_state["asset_v2_redo"]):
        snapshot = st.session_state["asset_v2_redo"].pop()
        st.session_state["asset_v2_undo"].append(_snapshot(asset_df))
        _restore(snapshot)
        st.rerun()
    if toolbar[2].button("✦ Save", key="asset_v2_save_btn", use_container_width=True, type="primary"):
        st.session_state["asset_v2_saved"] = _snapshot(asset_df)
        st.success("Asset register saved.")
    if toolbar[3].button("⟲ Reset", key="asset_v2_reset_btn", use_container_width=True, type="secondary"):
        _restore(st.session_state.get("asset_v2_saved", _snapshot(_default_asset_df())))
        st.rerun()

    chart_cols = st.columns(2, gap="large")
    with chart_cols[0]:
        category_df = asset_df.groupby("Asset Category", dropna=False).size().reset_index(name="Assets")
        fig_category = px.pie(category_df, names="Asset Category", values="Assets", hole=0.6, title="Assets by Category")
        fig_category.update_layout(margin=dict(t=50, l=10, r=10, b=10), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_category, use_container_width=True)
    with chart_cols[1]:
        project_df = asset_df.groupby(["Engaged for Project", "Asset Status"], dropna=False).size().reset_index(name="Assets")
        fig_project = px.sunburst(project_df, path=["Engaged for Project", "Asset Status"], values="Assets", title="Project Engagement to Asset Status")
        fig_project.update_layout(margin=dict(t=50, l=10, r=10, b=10), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_project, use_container_width=True)

    st.markdown("### Asset Register")
    asset_editor = st.data_editor(
        asset_df,
        key="asset_v2_editor",
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        height=360,
        column_config={
            "Employee Name": st.column_config.TextColumn("Employee Name", required=True, width="medium"),
            "Employee ID": st.column_config.TextColumn("Employee ID", required=True, width="small"),
            "Employee Status": st.column_config.SelectboxColumn("Employee Status", options=["Active", "Inactive", "Separated"], required=True, width="small"),
            "Engaged for Project": st.column_config.TextColumn("Engaged for Project", width="medium"),
            "Asset Category": st.column_config.SelectboxColumn("Asset Category", options=["Laptop", "Monitor", "Mobile", "Accessory", "Other"], required=True, width="small"),
            "Provisioning Type": st.column_config.SelectboxColumn("Provisioning Type", options=["Company Owned", "Vendor Provisioned"], required=True, width="small"),
            "Asset Serial Number": st.column_config.TextColumn("Asset Serial Number", required=True, width="medium"),
            "Asset Status": st.column_config.SelectboxColumn("Asset Status", options=["Active", "Inactive"], required=True, width="small"),
        },
    )
    asset_df = _clean_asset_df(asset_editor)
    st.session_state["asset_management_v2_df"] = asset_df
    _track_history(asset_df)

    word_bytes = build_word_report(
        f"{PRODUCT_NAME} Asset Review",
        [
            {"heading": "Asset Summary", "bullets": [f"Total assets: {len(asset_df)}", f"Active employees: {int((asset_df['Employee Status'] == 'Active').sum())}", f"Active assets: {int((asset_df['Asset Status'] == 'Active').sum())}", f"Projects engaged: {asset_df['Engaged for Project'].replace('', pd.NA).dropna().nunique()}"]},
            {"heading": "Enhancement Backlog", "bullets": ["Add warranty and replacement tracking.", "Add assignment history across employee transfers.", "Add asset health scoring and lifecycle alerts."]},
        ],
        subtitle="Review-ready summary generated from the asset workspace",
    )
    excel_bytes = _build_excel(asset_df)
    export_cols = st.columns([1, 1, 4], gap="small")
    export_cols[0].download_button("📊 Export Excel", data=excel_bytes, file_name="asset_register.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary", use_container_width=True)
    export_cols[1].download_button("📝 Review Word Doc", data=word_bytes, file_name="asset_register_review.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", type="secondary", use_container_width=True)
