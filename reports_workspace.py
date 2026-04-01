from urllib.parse import quote

import pandas as pd
import streamlit as st


PRODUCT_NAME = "VertexOne DeliveryOS"


def _inject_reports_styles():
    st.markdown(
        """
        <style>
        .report-card-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1rem;
            margin: 1rem 0 1.25rem 0;
        }
        .report-task-card {
            border: 1px solid rgba(148, 163, 184, 0.2);
            border-radius: 1.2rem;
            background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(239,246,255,0.92));
            box-shadow: 0 18px 36px rgba(15, 23, 42, 0.08);
            padding: 1rem 1rem 0.95rem 1rem;
        }
        .report-task-id {
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.12em;
            color: #64748b;
            text-transform: uppercase;
            margin-bottom: 0.45rem;
        }
        .report-task-title {
            font-size: 1.02rem;
            font-weight: 800;
            color: #0f172a;
            margin-bottom: 0.55rem;
        }
        .report-task-meta {
            font-size: 0.88rem;
            color: #334155;
            line-height: 1.55;
        }
        .report-link-buttons {
            display: flex;
            gap: 0.75rem;
            margin-top: 0.75rem;
            flex-wrap: wrap;
        }
        .report-link-button {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 180px;
            padding: 0.9rem 1rem;
            border-radius: 1rem;
            text-decoration: none;
            font-weight: 700;
            color: #ffffff !important;
            background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 55%, #38bdf8 100%);
            box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
        }
        .report-link-button.secondary {
            background: linear-gradient(135deg, #0f766e 0%, #14b8a6 100%);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_metric_buttons():
    report_mode = st.radio(
        "Report Source",
        ["Scan Project", "Created RoadMap", "Asset Management"],
        horizontal=True,
        key="reports_workspace_mode",
    )
    return report_mode


def _scan_sheet_names():
    workbook = st.session_state.get("db", {})
    return list(workbook.keys()) if workbook else []


def _scan_board_df(sheet_name):
    if not sheet_name:
        return pd.DataFrame()
    board_key = f"scan_board_state_{sheet_name}"
    if board_key in st.session_state:
        return pd.DataFrame(st.session_state[board_key]).copy()
    workbook = st.session_state.get("db", {})
    if sheet_name in workbook:
        return pd.DataFrame(workbook[sheet_name]).copy()
    return pd.DataFrame()


def _render_scan_reports():
    sheet_names = _scan_sheet_names()
    if not sheet_names:
        st.info("Open Scan Project and upload a workbook first. Reports will then reflect the current project state dynamically.")
        return

    project_name = st.selectbox("Project Report", sheet_names, key="reports_scan_project")
    board_df = _scan_board_df(project_name)
    if board_df.empty:
        st.warning("The selected project does not yet have an active board state.")
        return

    board_df["Status"] = board_df.get("Status", pd.Series(["To Do"] * len(board_df))).fillna("To Do")
    board_df["Owner"] = board_df.get("Owner", pd.Series(["Unassigned"] * len(board_df))).fillna("Unassigned").replace("", "Unassigned")
    board_df["Planned End"] = pd.to_datetime(board_df.get("Planned End"), errors="coerce")
    board_df["Planned Start"] = pd.to_datetime(board_df.get("Planned Start"), errors="coerce")

    review_date = st.date_input("Follow-up Date", value=pd.Timestamp.today().date(), key="reports_scan_date")
    review_ts = pd.to_datetime(review_date)
    incomplete_df = board_df[board_df["Status"] != "Done"].copy()
    overdue_df = incomplete_df[incomplete_df["Planned End"].notna() & (incomplete_df["Planned End"] <= review_ts)].copy()

    top = st.columns(4, gap="small")
    top[0].metric("Not Completed", len(incomplete_df))
    top[1].metric("Due / Overdue", len(overdue_df))
    top[2].metric("Owners Impacted", incomplete_df["Owner"].nunique())
    top[3].metric("In Review", int((incomplete_df["Status"] == "Review").sum()))

    if incomplete_df.empty:
        st.success("No pending tasks for the selected project.")
        return

    st.markdown("### Pending Task Cards")
    card_columns = st.columns(2, gap="large")
    for index, row in enumerate(incomplete_df.sort_values(["Planned End", "Owner", "Task Name"]).head(24).to_dict(orient="records")):
        start_text = pd.to_datetime(row.get("Planned Start"), errors="coerce")
        end_text = pd.to_datetime(row.get("Planned End"), errors="coerce")
        start_label = start_text.strftime("%d %b %Y") if pd.notna(start_text) else "TBD"
        end_label = end_text.strftime("%d %b %Y") if pd.notna(end_text) else "TBD"
        card_columns[index % 2].markdown(
            f"""
            <div class="report-task-card">
                <div class="report-task-id">{row.get('Task ID', 'Task')}</div>
                <div class="report-task-title">{row.get('Task Name', 'Untitled Task')}</div>
                <div class="report-task-meta">
                    <b>Status:</b> {row.get('Status', '-')}<br/>
                    <b>Owner:</b> {row.get('Owner', 'Unassigned')}<br/>
                    <b>Start:</b> {start_label}<br/>
                    <b>End:</b> {end_label}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    followup_df = (
        incomplete_df.groupby("Owner", dropna=False)
        .agg(
            Pending_Tasks=("Task ID", "count"),
            Attention_Items=("Status", lambda col: int(col.isin(["Review", "At Risk"]).sum())),
            Next_End_Date=("Planned End", "min"),
        )
        .reset_index()
        .rename(columns={"Owner": "Resource"})
    )
    followup_df["Next End Date"] = pd.to_datetime(followup_df["Next_End_Date"], errors="coerce").dt.strftime("%d %b %Y").fillna("TBD")
    followup_df = followup_df.drop(columns=["Next_End_Date"])

    st.markdown("### Resource Follow-up View")
    st.dataframe(followup_df, use_container_width=True, hide_index=True, height=280)

    st.markdown("### Follow-up Draft")
    channel = st.selectbox("Channel", ["Microsoft Teams", "WhatsApp", "Email"], key="reports_channel")
    selected_resources = st.multiselect("Resources", sorted(followup_df["Resource"].tolist()), default=sorted(followup_df["Resource"].tolist())[:3], key="reports_resources")
    selected_tasks = incomplete_df[incomplete_df["Owner"].isin(selected_resources)] if selected_resources else incomplete_df.head(5)
    message_lines = [
        f"{PRODUCT_NAME} follow-up for {project_name} as of {review_ts.strftime('%d %b %Y')}:",
        "",
    ]
    for row in selected_tasks.head(8).to_dict(orient="records"):
        end_text = pd.to_datetime(row.get("Planned End"), errors="coerce")
        end_label = end_text.strftime("%d %b %Y") if pd.notna(end_text) else "TBD"
        message_lines.append(
            f"- {row.get('Owner', 'Unassigned')}: {row.get('Task Name', 'Task')} [{row.get('Status', '-')}] due {end_label}"
        )
    draft_message = "\n".join(message_lines)
    st.text_area("Notification Draft", value=draft_message, height=180, key="reports_message")

    encoded_message = quote(draft_message)
    teams_link = f"https://teams.microsoft.com/l/chat/0/0?message={encoded_message}"
    whatsapp_link = f"https://wa.me/?text={encoded_message}"
    st.markdown(
        f"""
        <div class="report-link-buttons">
            <a class="report-link-button" href="{teams_link}" target="_blank" rel="noopener noreferrer">💬 Open in Microsoft Teams</a>
            <a class="report-link-button secondary" href="{whatsapp_link}" target="_blank" rel="noopener noreferrer">📲 Open in WhatsApp</a>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(f"These links use the live pending-task draft. If Teams or WhatsApp is installed and registered on your machine, the browser can hand the draft off to the local app.")


def _render_roadmap_reports():
    task_df = pd.DataFrame(st.session_state.get("roadmap_v3_task_df", []))
    team_df = pd.DataFrame(st.session_state.get("roadmap_v3_team_df", []))
    if task_df.empty:
        st.info("Create or edit a roadmap first. The roadmap report will then mirror the live planning data.")
        return

    st.markdown("### Roadmap Planning Summary")
    top = st.columns(4, gap="small")
    top[0].metric("Planned Tasks", len(task_df))
    top[1].metric("Teams Enabled", int(team_df["Use Team"].sum()) if "Use Team" in team_df.columns else team_df["Team"].nunique())
    top[2].metric("Parallel Tasks", int((task_df.get("Execution", pd.Series(dtype=str)) == "Parallel").sum()))
    top[3].metric("Reuse Modules", int((task_df.get("Build Strategy", pd.Series(dtype=str)) == "Reuse Existing Module").sum()))

    st.dataframe(task_df, use_container_width=True, hide_index=True, height=360)


def _render_asset_reports():
    asset_df = pd.DataFrame(st.session_state.get("asset_management_v2_df", []))
    if asset_df.empty:
        st.info("Open Asset Management first. The asset report will then reflect the current register.")
        return

    top = st.columns(4, gap="small")
    top[0].metric("Assets", len(asset_df))
    top[1].metric("Active Employees", int((asset_df.get("Employee Status", pd.Series(dtype=str)) == "Active").sum()))
    top[2].metric("Active Assets", int((asset_df.get("Asset Status", pd.Series(dtype=str)) == "Active").sum()))
    top[3].metric("Engaged Projects", asset_df.get("Engaged for Project", pd.Series(dtype=str)).replace("", pd.NA).dropna().nunique())
    st.dataframe(asset_df, use_container_width=True, hide_index=True, height=360)


def render_reports_workspace():
    _inject_reports_styles()
    st.markdown(
        f"""
        <div class="app-hero">
            <div class="hero-main">
                <div class="hero-kicker">Reports</div>
                <div class="hero-title">{PRODUCT_NAME} Reports Hub</div>
                <p class="hero-text">Review the live delivery picture across scanned projects, created roadmaps, and asset operations. The report views reflect the current workspace state so follow-ups and management reviews stay current.</p>
            </div>
            <div class="hero-panel">
                <span class="hero-panel-label">Enterprise View</span>
                <span class="hero-panel-title">Actionable Reporting</span>
                <p class="hero-panel-copy">Use this space to review pending work, team exposure, and operational follow-up drafts without rebuilding manual status packs.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    report_mode = _render_metric_buttons()
    if report_mode == "Scan Project":
        _render_scan_reports()
    elif report_mode == "Created RoadMap":
        _render_roadmap_reports()
    else:
        _render_asset_reports()
