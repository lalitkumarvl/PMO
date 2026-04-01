import json
from io import BytesIO

import pandas as pd
import plotly.express as px
import streamlit as st

from word_export import build_word_report


ASSET_COLUMNS = [
    "Employee Name",
    "Employee ID",
    "Employee Status",
    "Asset Category",
    "Provisioning Type",
    "Asset Serial Number",
    "Asset Status",
]


def _inject_enterprise_ui_styles():
    st.markdown(
        """
        <style>
        div.stButton > button,
        div.stDownloadButton > button {
            height: 3.2rem;
            border-radius: 1rem;
            font-weight: 700;
            letter-spacing: 0.01em;
            border: 1px solid rgba(37, 99, 235, 0.16);
            box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
            transition: transform 0.18s ease, box-shadow 0.18s ease;
        }
        div.stButton > button:hover,
        div.stDownloadButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 16px 32px rgba(37, 99, 235, 0.18);
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
            {
                "Employee Name": "Asha",
                "Employee ID": "EMP001",
                "Employee Status": "Active",
                "Asset Category": "Laptop",
                "Provisioning Type": "Company Owned",
                "Asset Serial Number": "LT-10021",
                "Asset Status": "Active",
            },
            {
                "Employee Name": "Rahul",
                "Employee ID": "EMP002",
                "Employee Status": "Active",
                "Asset Category": "Monitor",
                "Provisioning Type": "Vendor Provisioned",
                "Asset Serial Number": "MN-20311",
                "Asset Status": "Active",
            },
        ]
    )


def _clean_asset_df(asset_df):
    clean_df = asset_df.copy()
    for column in ASSET_COLUMNS:
        if column not in clean_df.columns:
            clean_df[column] = ""
    clean_df = clean_df[ASSET_COLUMNS]
    clean_df = clean_df.fillna("")
    clean_df["Employee Status"] = clean_df["Employee Status"].where(
        clean_df["Employee Status"].isin(["Active", "Inactive", "Separated"]),
        "Active",
    )
    clean_df["Asset Status"] = clean_df["Asset Status"].where(clean_df["Asset Status"].isin(["Active", "Inactive"]), "Active")
    clean_df["Provisioning Type"] = clean_df["Provisioning Type"].where(
        clean_df["Provisioning Type"].isin(["Company Owned", "Vendor Provisioned"]),
        "Company Owned",
    )
    return clean_df.reset_index(drop=True)


def _asset_snapshot(asset_df):
    return pd.DataFrame(asset_df)[ASSET_COLUMNS].fillna("").to_dict(orient="records")


def _asset_fingerprint(asset_df):
    return json.dumps(_asset_snapshot(asset_df), sort_keys=True, default=str)


def _track_asset_history(asset_df):
    st.session_state.setdefault("asset_management_undo", [])
    st.session_state.setdefault("asset_management_redo", [])
    snapshot = _asset_snapshot(asset_df)
    fingerprint = _asset_fingerprint(asset_df)
    if st.session_state.pop("asset_management_skip_history_once", False):
        st.session_state["asset_management_last_snapshot"] = snapshot
        st.session_state["asset_management_last_fp"] = fingerprint
        return

    last_fp = st.session_state.get("asset_management_last_fp")
    last_snapshot = st.session_state.get("asset_management_last_snapshot")
    if last_fp is None:
        st.session_state["asset_management_last_snapshot"] = snapshot
        st.session_state["asset_management_last_fp"] = fingerprint
        return
    if fingerprint != last_fp and last_snapshot is not None:
        st.session_state["asset_management_undo"].append(last_snapshot)
        st.session_state["asset_management_undo"] = st.session_state["asset_management_undo"][-25:]
        st.session_state["asset_management_redo"].clear()
        st.session_state["asset_management_last_snapshot"] = snapshot
        st.session_state["asset_management_last_fp"] = fingerprint


def _restore_asset_snapshot(snapshot):
    st.session_state["asset_management_df"] = pd.DataFrame(snapshot)
    st.session_state["asset_management_skip_history_once"] = True


def _build_asset_excel(asset_df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        asset_df.to_excel(writer, index=False, sheet_name="Asset Register")
    output.seek(0)
    return output.getvalue()


def render_asset_management_workspace():
    _inject_enterprise_ui_styles()

    st.markdown(
        """
        <div class="app-hero">
            <div class="hero-main">
                <div class="hero-kicker">Asset Management</div>
                <div class="hero-title">Physical Asset Control</div>
                <p class="hero-text">Track employee-assigned physical assets across company-owned and vendor-provisioned inventories, monitor active versus inactive states, and keep the register export-ready for operations review.</p>
            </div>
            <div class="hero-panel">
                <span class="hero-panel-label">Control Scope</span>
                <span class="hero-panel-title">Employee Asset Register</span>
                <p class="hero-panel-copy">Use this workspace to review ownership, provisioning source, and asset activeness from a single operational view.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    upload = st.file_uploader("Upload Asset Register", type=["xlsx", "csv"], label_visibility="collapsed", key="asset_workspace_upload")
    if upload is not None:
        if upload.name.lower().endswith(".csv"):
            st.session_state["asset_management_df"] = pd.read_csv(upload)
        else:
            st.session_state["asset_management_df"] = pd.read_excel(upload)

    if "asset_management_df" not in st.session_state:
        st.session_state["asset_management_df"] = _default_asset_df()

    asset_df = _clean_asset_df(pd.DataFrame(st.session_state["asset_management_df"]))
    current_snapshot = _asset_snapshot(asset_df)
    metrics = st.columns(4, gap="small")
    metrics[0].metric("Total Assets", len(asset_df))
    metrics[1].metric("Active Assets", int((asset_df["Asset Status"] == "Active").sum()))
    metrics[2].metric("Inactive Assets", int((asset_df["Asset Status"] == "Inactive").sum()))
    metrics[3].metric("Employees Covered", asset_df["Employee ID"].replace("", pd.NA).dropna().nunique())

    toolbar = st.columns([1, 1, 1, 1, 4], gap="small")
    st.session_state.setdefault("asset_management_undo", [])
    st.session_state.setdefault("asset_management_redo", [])
    if toolbar[0].button("↶ Undo", key="asset_toolbar_undo", use_container_width=True, disabled=not st.session_state["asset_management_undo"]):
        snapshot = st.session_state["asset_management_undo"].pop()
        st.session_state["asset_management_redo"].append(current_snapshot)
        _restore_asset_snapshot(snapshot)
        st.rerun()
    if toolbar[1].button("↷ Redo", key="asset_toolbar_redo", use_container_width=True, disabled=not st.session_state["asset_management_redo"]):
        snapshot = st.session_state["asset_management_redo"].pop()
        st.session_state["asset_management_undo"].append(current_snapshot)
        _restore_asset_snapshot(snapshot)
        st.rerun()
    if toolbar[2].button("✦ Save", key="asset_toolbar_save", use_container_width=True, type="primary"):
        st.session_state["asset_management_saved"] = current_snapshot
        st.success("Asset register saved.")
    if toolbar[3].button("⟲ Reset", key="asset_toolbar_clear", use_container_width=True, type="secondary"):
        snapshot = st.session_state.get("asset_management_saved", _asset_snapshot(_default_asset_df()))
        _restore_asset_snapshot(snapshot)
        st.rerun()

    chart_cols = st.columns(2, gap="large")
    with chart_cols[0]:
        category_df = asset_df.groupby("Asset Category", dropna=False).size().reset_index(name="Assets")
        fig_category = px.pie(category_df, names="Asset Category", values="Assets", hole=0.6, title="Assets by Category")
        fig_category.update_layout(margin=dict(t=50, l=10, r=10, b=10), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_category, use_container_width=True)
    with chart_cols[1]:
        provision_df = asset_df.groupby(["Provisioning Type", "Asset Status"], dropna=False).size().reset_index(name="Assets")
        fig_provision = px.sunburst(
            provision_df,
            path=["Provisioning Type", "Asset Status"],
            values="Assets",
            title="Provisioning to Status Breakdown",
        )
        fig_provision.update_layout(margin=dict(t=50, l=10, r=10, b=10), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_provision, use_container_width=True)

    st.markdown("### Asset Register")
    asset_editor = st.data_editor(
        asset_df,
        key="asset_management_editor",
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        height=360,
        column_config={
            "Employee Name": st.column_config.TextColumn("Employee Name", required=True),
            "Employee ID": st.column_config.TextColumn("Employee ID", required=True),
            "Employee Status": st.column_config.SelectboxColumn("Employee Status", options=["Active", "Inactive", "Separated"], required=True),
            "Asset Category": st.column_config.SelectboxColumn("Asset Category", options=["Laptop", "Monitor", "Mobile", "Accessory", "Other"], required=True),
            "Provisioning Type": st.column_config.SelectboxColumn("Provisioning Type", options=["Company Owned", "Vendor Provisioned"], required=True),
            "Asset Serial Number": st.column_config.TextColumn("Asset Serial Number", required=True),
            "Asset Status": st.column_config.SelectboxColumn("Asset Status", options=["Active", "Inactive"], required=True),
        },
    )
    asset_df = _clean_asset_df(asset_editor)
    st.session_state["asset_management_df"] = asset_df
    _track_asset_history(asset_df)

    word_bytes = build_word_report(
        "Asset Management Review",
        [
            {
                "heading": "Dashboard Review Summary",
                "bullets": [
                    f"Total assets: {len(asset_df)}",
                    f"Active assets: {int((asset_df['Asset Status'] == 'Active').sum())}",
                    f"Inactive assets: {int((asset_df['Asset Status'] == 'Inactive').sum())}",
                    f"Employees covered: {asset_df['Employee ID'].replace('', pd.NA).dropna().nunique()}",
                ],
            },
            {
                "heading": "Incremental Feature Backlog",
                "bullets": [
                    "Add asset issue logging and warranty tracking.",
                    "Add assignment history for employee transfers and returns.",
                    "Add vendor SLA tracking for provisioned assets.",
                    "Add automatic alerts for inactive but assigned assets.",
                ],
            },
        ],
        subtitle="Review-ready summary generated from the asset dashboard",
    )
    excel_bytes = _build_asset_excel(asset_df)
    export_cols = st.columns([1, 1, 4], gap="small")
    export_cols[0].download_button(
        "📊 Export Excel",
        data=excel_bytes,
        file_name="asset_register.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        use_container_width=True,
    )
    export_cols[1].download_button(
        "📝 Review Word Doc",
        data=word_bytes,
        file_name="asset_register_review.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        type="secondary",
        use_container_width=True,
    )
