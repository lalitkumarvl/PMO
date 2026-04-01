import json
import textwrap

import pandas as pd
import plotly.express as px
import streamlit as st

from roadmap_workspace import (
    attach_risk_levels,
    build_default_holiday_df,
    build_default_module_df,
    build_default_team_df,
    build_export_workbook,
    build_gantt_text,
    build_market_comparison_df,
    build_recommendations,
    build_team_utilization,
    clean_holiday_df,
    clean_task_df,
    compute_critical_path,
    generate_default_task_df,
    infer_complexity,
    infer_profile,
    schedule_tasks,
    slugify,
)
from word_export import build_word_report


PRODUCT_NAME = "VertexOne DeliveryOS"


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
            border-color: rgba(37, 99, 235, 0.24);
        }
        div.stButton > button[kind="tertiary"],
        div.stDownloadButton > button[kind="tertiary"] {
            background: linear-gradient(135deg, #0f766e 0%, #14b8a6 100%);
            color: #ffffff;
            border: none;
        }
        div[data-testid="stDataFrameResizable"] {
            max-width: 100%;
            overflow-x: auto !important;
            border-radius: 1.25rem;
            border: 1px solid rgba(148, 163, 184, 0.22);
        }
        .roadmap-note-card {
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 1.2rem;
            background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(239,246,255,0.92));
            box-shadow: 0 18px 36px rgba(15,23,42,0.07);
            padding: 1rem 1.05rem;
            margin-bottom: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _compact_copy(value, limit=58):
    text = str(value or "").strip()
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3]}..."


def _normalize_snapshot_value(value):
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return value


def _df_records(dataframe):
    return [{column: _normalize_snapshot_value(value) for column, value in row.items()} for row in pd.DataFrame(dataframe).to_dict(orient="records")]


def _build_roadmap_snapshot(project_name, project_description, duration_days, start_day, team_df, holiday_df, module_df, task_df, signature):
    return {
        "signature": signature,
        "project_name": project_name,
        "project_description": project_description,
        "duration_days": int(duration_days),
        "start_day": str(pd.to_datetime(start_day).date()),
        "team_df": _df_records(team_df),
        "holiday_df": _df_records(holiday_df),
        "module_df": _df_records(module_df),
        "task_df": _df_records(task_df),
    }


def _snapshot_fingerprint(snapshot):
    return json.dumps(snapshot, sort_keys=True, default=str)


def _restore_roadmap_snapshot(snapshot):
    st.session_state["roadmap_v3_project_name"] = snapshot["project_name"]
    st.session_state["roadmap_v3_project_description"] = snapshot["project_description"]
    st.session_state["roadmap_v3_duration"] = int(snapshot["duration_days"])
    st.session_state["roadmap_v3_start"] = pd.to_datetime(snapshot["start_day"]).date()
    st.session_state["roadmap_v3_team_df"] = pd.DataFrame(snapshot["team_df"])
    st.session_state["roadmap_v3_holiday_df"] = pd.DataFrame(snapshot["holiday_df"])
    st.session_state["roadmap_v3_module_df"] = pd.DataFrame(snapshot["module_df"])
    st.session_state["roadmap_v3_task_df"] = pd.DataFrame(snapshot["task_df"])
    st.session_state["roadmap_v3_signature"] = snapshot["signature"]
    st.session_state["roadmap_v3_task_signature"] = snapshot["signature"]


def _track_roadmap_history(current_snapshot):
    st.session_state.setdefault("roadmap_v3_undo", [])
    st.session_state.setdefault("roadmap_v3_redo", [])
    fingerprint = _snapshot_fingerprint(current_snapshot)
    if st.session_state.pop("roadmap_v3_skip_history_once", False):
        st.session_state["roadmap_v3_last_snapshot"] = current_snapshot
        st.session_state["roadmap_v3_last_snapshot_fp"] = fingerprint
        return

    last_fp = st.session_state.get("roadmap_v3_last_snapshot_fp")
    last_snapshot = st.session_state.get("roadmap_v3_last_snapshot")
    if last_fp is None:
        st.session_state["roadmap_v3_last_snapshot"] = current_snapshot
        st.session_state["roadmap_v3_last_snapshot_fp"] = fingerprint
        return
    if fingerprint != last_fp and last_snapshot is not None:
        st.session_state["roadmap_v3_undo"].append(last_snapshot)
        st.session_state["roadmap_v3_undo"] = st.session_state["roadmap_v3_undo"][-25:]
        st.session_state["roadmap_v3_redo"].clear()
        st.session_state["roadmap_v3_last_snapshot"] = current_snapshot
        st.session_state["roadmap_v3_last_snapshot_fp"] = fingerprint


def _clean_team_input_df(team_df):
    clean_df = pd.DataFrame(team_df).copy()
    if "Use Team" not in clean_df.columns:
        clean_df["Use Team"] = True
    if "Resource Names" not in clean_df.columns:
        clean_df["Resource Names"] = ""
    clean_df["Use Team"] = clean_df["Use Team"].fillna(True).astype(bool)
    clean_df["Resources"] = pd.to_numeric(clean_df["Resources"], errors="coerce").fillna(1).clip(lower=1).astype(int)
    clean_df["Allocation %"] = pd.to_numeric(clean_df["Allocation %"], errors="coerce").fillna(100).clip(lower=20, upper=100).astype(int)
    clean_df["Suggested Resources"] = pd.to_numeric(clean_df["Suggested Resources"], errors="coerce").fillna(clean_df["Resources"]).clip(lower=1).astype(int)
    clean_df["Skill Level"] = clean_df["Skill Level"].where(clean_df["Skill Level"].isin(["Junior", "Mid", "Senior"]), "Mid")
    clean_df["Allocation Guidance"] = clean_df["Allocation Guidance"].fillna("").astype(str).apply(_compact_copy)
    normalized_names = []
    for row in clean_df.to_dict(orient="records"):
        existing = [item.strip() for item in str(row.get("Resource Names", "")).split(",") if item.strip()]
        base_name = str(row["Team"]).replace("/", " ").replace("&", " ").strip()
        while len(existing) < int(row["Resources"]):
            existing.append(f"{base_name} {len(existing) + 1}")
        normalized_names.append(", ".join(existing[: int(row["Resources"])]))
    clean_df["Resource Names"] = normalized_names
    return clean_df.reset_index(drop=True)


def _clean_module_input_df(module_df):
    clean_df = pd.DataFrame(module_df).copy()
    if "Use Module" not in clean_df.columns:
        clean_df["Use Module"] = True
    clean_df["Use Module"] = clean_df["Use Module"].fillna(True).astype(bool)
    clean_df["Build Strategy"] = clean_df["Build Strategy"].where(clean_df["Build Strategy"].isin(["Build from Scratch", "Reuse Existing Module"]), "Build from Scratch")
    clean_df["Reuse Reduction %"] = pd.to_numeric(clean_df["Reuse Reduction %"], errors="coerce").fillna(0).clip(lower=0, upper=80).astype(int)
    clean_df["AI Component"] = clean_df["AI Component"].where(clean_df["AI Component"].isin(["No", "Assistive", "Core"]), "No")
    clean_df["Total APIs"] = pd.to_numeric(clean_df["Total APIs"], errors="coerce").fillna(0).clip(lower=0).astype(int)
    clean_df["Validated APIs"] = pd.to_numeric(clean_df["Validated APIs"], errors="coerce").fillna(0).clip(lower=0).astype(int)
    clean_df["Enough Data"] = clean_df["Enough Data"].where(clean_df["Enough Data"].isin(["Yes", "No", "Partial"]), "Yes")
    clean_df["Dependencies"] = clean_df["Dependencies"].fillna("").astype(str).apply(_compact_copy)
    return clean_df.reset_index(drop=True)


def _merge_input_defaults(default_df, existing_df, key_column):
    if existing_df is None or len(existing_df) == 0:
        return default_df.copy()
    existing_map = pd.DataFrame(existing_df).set_index(key_column).to_dict(orient="index")
    merged_rows = []
    for row in default_df.to_dict(orient="records"):
        current = existing_map.get(row[key_column], {})
        merged_rows.append({**row, **current})
    existing_keys = set(default_df[key_column].tolist())
    for row in pd.DataFrame(existing_df).to_dict(orient="records"):
        if row[key_column] not in existing_keys:
            merged_rows.append(row)
    return pd.DataFrame(merged_rows)


def _apply_module_modifiers(task_df, module_df):
    adjusted_df = task_df.copy()
    module_lookup = {row["Module"]: row for row in module_df.to_dict(orient="records")}
    for index, row in adjusted_df.iterrows():
        module_settings = module_lookup.get(row["Task Name"])
        if not module_settings:
            continue
        effort = float(row["Effort Days"])
        if module_settings["Build Strategy"] == "Reuse Existing Module":
            effort *= max(0.25, (100 - int(module_settings["Reuse Reduction %"])) / 100)
        if module_settings["AI Component"] == "Assistive":
            effort *= 0.92
        elif module_settings["AI Component"] == "Core":
            effort *= 0.86 if module_settings["Enough Data"] == "Yes" else 1.04
        fresh_apis = max(int(module_settings["Total APIs"]) - int(module_settings["Validated APIs"]), 0)
        if fresh_apis:
            effort *= 1 + min(fresh_apis * 0.05, 0.25)
        if module_settings["Enough Data"] == "No":
            effort *= 1.08
        elif module_settings["Enough Data"] == "Partial":
            effort *= 1.03
        adjusted_df.at[index, "Effort Days"] = max(1, int(round(effort)))
    return adjusted_df


def _calculate_project_end_date(start_day, duration_days, holiday_df):
    holiday_dates = {pd.to_datetime(date).date() for date in pd.to_datetime(holiday_df.get("Date", pd.Series(dtype="datetime64[ns]")), errors="coerce").dropna()}
    current_day = pd.to_datetime(start_day).date()
    consumed = 0
    while consumed < duration_days:
        if current_day.weekday() < 5 and current_day not in holiday_dates:
            consumed += 1
            if consumed == duration_days:
                return pd.to_datetime(current_day)
        current_day += pd.Timedelta(days=1)
    return pd.to_datetime(current_day)


def _resource_options(team_df):
    options = []
    for value in team_df.get("Resource Names", pd.Series(dtype=str)).fillna(""):
        options.extend([item.strip() for item in str(value).split(",") if item.strip()])
    return sorted(dict.fromkeys(options))


def _prepare_task_df(task_df, resource_options):
    prepared = clean_task_df(pd.DataFrame(task_df))
    if "Assigned Resource" not in prepared.columns:
        prepared["Assigned Resource"] = ""
    prepared["Assigned Resource"] = prepared["Assigned Resource"].fillna("").astype(str)
    valid_options = set(resource_options)
    prepared["Assigned Resource"] = prepared["Assigned Resource"].where(prepared["Assigned Resource"].isin(valid_options), "")
    return prepared


def _achievability_summary(duration_days, actual_workdays, module_df):
    blockers = []
    if actual_workdays > duration_days:
        blockers.append(f"Current plan exceeds the target by {actual_workdays - duration_days} working day(s).")
    if not module_df.empty and (module_df["Enough Data"] == "No").any():
        blockers.append("One or more modules do not have enough validation data.")
    if not module_df.empty and ((module_df["Total APIs"] - module_df["Validated APIs"]).clip(lower=0) > 4).any():
        blockers.append("The roadmap includes multiple fresh APIs that increase delivery uncertainty.")
    achievable = not blockers
    remediation = blockers or ["Current plan is achievable if scope and staffing remain stable."]
    return achievable, remediation


def _build_team_timeline_figure(roadmap_df):
    timeline_df = (
        roadmap_df.groupby("Team Responsible", dropna=False)
        .agg(Start_Date=("Start Date", "min"), End_Date=("End Date", "max"), Task_Count=("Task Name", "count"))
        .reset_index()
    )
    fig = px.timeline(
        timeline_df,
        x_start="Start_Date",
        x_end="End_Date",
        y="Team Responsible",
        color="Task_Count",
        color_continuous_scale=["#dbeafe", "#60a5fa", "#1d4ed8"],
        title="Team Delivery Timeline",
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(margin=dict(t=50, l=12, r=12, b=12), paper_bgcolor="rgba(0,0,0,0)", coloraxis_showscale=False)
    return fig


def _roadmap_pdf_safe_text(value, limit=140):
    text = str(value or "").replace("\r", " ").replace("\n", " ").strip()
    text = " ".join(text.split())
    if len(text) > limit:
        text = f"{text[: limit - 3]}..."
    return text or "-"


def _build_safe_roadmap_pdf(project_name, project_description, summary_df, market_df, timeline_df, roadmap_df, recommendations):
    try:
        from fpdf import FPDF

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=12)
        pdf.add_page()
        pdf.set_margins(12, 12, 12)

        def write_lines(lines, font_style="", font_size=11):
            pdf.set_font("Helvetica", font_style, font_size)
            width = max(pdf.w - pdf.l_margin - pdf.r_margin, 120)
            for line in lines:
                wrapped = textwrap.wrap(_roadmap_pdf_safe_text(line), width=88, break_long_words=True, break_on_hyphens=True) or ["-"]
                for chunk in wrapped:
                    pdf.cell(width, 7, chunk, new_x="LMARGIN", new_y="NEXT")

        write_lines([project_name], font_style="B", font_size=16)
        pdf.ln(2)
        write_lines([project_description], font_size=11)
        pdf.ln(2)
        write_lines(["Project Summary"], font_style="B", font_size=13)
        write_lines([f"{row['Attribute']}: {row['Value']}" for row in summary_df.to_dict(orient="records")])
        pdf.ln(1)
        write_lines(["Timeline Summary"], font_style="B", font_size=13)
        write_lines([f"{row['Metric']}: {row['Value']}" for row in timeline_df.to_dict(orient="records")])
        pdf.ln(1)
        write_lines(["Market Comparison"], font_style="B", font_size=13)
        write_lines([f"{row['Product Name']} | {row['Organization']} | {row['Key Differentiation']}" for row in market_df.head(5).to_dict(orient="records")])
        pdf.ln(1)
        write_lines(["Recommendations"], font_style="B", font_size=13)
        write_lines([f"- {item}" for item in recommendations[:8]])
        return bytes(pdf.output(dest="S"))
    except Exception:
        return b"%PDF-1.4\n%VertexOne fallback roadmap PDF export unavailable\n"


def render_roadmap_workspace_v3():
    _inject_enterprise_ui_styles()

    project_name = st.text_input("Project Name", value=st.session_state.get("roadmap_v3_project_name", ""), key="roadmap_v3_project_name")
    project_description = st.text_area(
        "Project Description",
        value=st.session_state.get("roadmap_v3_project_description", "Build an enterprise delivery workspace with workflow visibility, planning, and management reporting."),
        key="roadmap_v3_project_description",
        height=120,
    )
    top_inputs = st.columns([1, 1], gap="small")
    with top_inputs[0]:
        duration_days = int(st.number_input("Project Duration (working days)", min_value=10, max_value=365, value=int(st.session_state.get("roadmap_v3_duration", 90)), step=5, key="roadmap_v3_duration"))
    with top_inputs[1]:
        start_day = st.date_input("Project Start Date", value=st.session_state.get("roadmap_v3_start", pd.Timestamp.today().date()), key="roadmap_v3_start")

    profile = infer_profile(project_description)
    complexity = infer_complexity(project_description, duration_days, len(build_default_module_df(profile, "Medium")))
    default_team_df = build_default_team_df(profile, complexity)
    default_team_df["Use Team"] = True
    default_team_df["Resource Names"] = ""
    default_module_df = build_default_module_df(profile, complexity)
    default_module_df["Use Module"] = True
    default_module_df["AI Component"] = "No"
    default_module_df["Total APIs"] = 0
    default_module_df["Validated APIs"] = 0
    default_module_df["Enough Data"] = "Yes"
    default_holiday_df = build_default_holiday_df(start_day, duration_days)

    signature = "|".join([project_name.strip(), project_description.strip(), str(duration_days), str(start_day), complexity, profile["id"]])
    if st.session_state.get("roadmap_v3_signature") != signature:
        st.session_state["roadmap_v3_signature"] = signature
        st.session_state["roadmap_v3_team_df"] = _merge_input_defaults(default_team_df, st.session_state.get("roadmap_v3_team_df"), "Team")
        st.session_state["roadmap_v3_module_df"] = _merge_input_defaults(default_module_df, st.session_state.get("roadmap_v3_module_df"), "Module")
        st.session_state["roadmap_v3_holiday_df"] = clean_holiday_df(pd.concat([default_holiday_df, pd.DataFrame(st.session_state.get("roadmap_v3_holiday_df", []))], ignore_index=True))

    team_df = _clean_team_input_df(st.session_state["roadmap_v3_team_df"])
    module_df = _clean_module_input_df(st.session_state["roadmap_v3_module_df"])
    holiday_df = clean_holiday_df(pd.DataFrame(st.session_state["roadmap_v3_holiday_df"]))
    market_df = build_market_comparison_df(profile)
    project_end_date = _calculate_project_end_date(start_day, duration_days, holiday_df)

    active_team_df = team_df[team_df["Use Team"]].copy()
    active_module_df = module_df[module_df["Use Module"]].copy()
    if active_team_df.empty:
        active_team_df = team_df.copy()
    if active_module_df.empty:
        active_module_df = module_df.copy()

    base_task_df = generate_default_task_df(project_name, duration_days, complexity, active_team_df.drop(columns=["Use Team"]), active_module_df.drop(columns=["Use Module", "AI Component", "Total APIs", "Validated APIs", "Enough Data"], errors="ignore"))
    if "Assigned Resource" not in base_task_df.columns:
        base_task_df["Assigned Resource"] = ""
    if "roadmap_v3_task_df" not in st.session_state or st.session_state.get("roadmap_v3_task_signature") != signature:
        st.session_state["roadmap_v3_task_df"] = base_task_df
        st.session_state["roadmap_v3_task_signature"] = signature

    current_snapshot = _build_roadmap_snapshot(project_name, project_description, duration_days, start_day, st.session_state["roadmap_v3_team_df"], st.session_state["roadmap_v3_holiday_df"], st.session_state["roadmap_v3_module_df"], st.session_state["roadmap_v3_task_df"], signature)
    _track_roadmap_history(current_snapshot)

    st.markdown(
        f"""
        <div class="app-hero">
            <div class="hero-main">
                <div class="hero-kicker">Create RoadMap</div>
                <div class="hero-title">{PRODUCT_NAME}</div>
                <p class="hero-text">Shape the project plan, resource strategy, holiday impacts, and execution approach from one enterprise planning workspace.</p>
            </div>
            <div class="hero-panel">
                <span class="hero-panel-label">Roadmap Studio</span>
                <span class="hero-panel-title">{project_name or 'New Enterprise Plan'}</span>
                <p class="hero-panel-copy">Use the tabs below to move from executive inputs to planning controls and then into the generated roadmap timeline.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    toolbar = st.columns([1, 1, 1, 1.15, 4], gap="small")
    if toolbar[0].button("↶ Undo", key="roadmap_v3_toolbar_undo", use_container_width=True, disabled=not st.session_state["roadmap_v3_undo"]):
        snapshot = st.session_state["roadmap_v3_undo"].pop()
        st.session_state["roadmap_v3_redo"].append(current_snapshot)
        _restore_roadmap_snapshot(snapshot)
        st.session_state["roadmap_v3_skip_history_once"] = True
        st.rerun()
    if toolbar[1].button("↷ Redo", key="roadmap_v3_toolbar_redo", use_container_width=True, disabled=not st.session_state["roadmap_v3_redo"]):
        snapshot = st.session_state["roadmap_v3_redo"].pop()
        st.session_state["roadmap_v3_undo"].append(current_snapshot)
        _restore_roadmap_snapshot(snapshot)
        st.session_state["roadmap_v3_skip_history_once"] = True
        st.rerun()
    if toolbar[2].button("✦ Save", key="roadmap_v3_toolbar_save", use_container_width=True, type="primary"):
        st.session_state["roadmap_v3_saved_snapshot"] = current_snapshot
        st.success("Roadmap inputs saved.")
    if toolbar[3].button("⟲ Reset", key="roadmap_v3_toolbar_reset", use_container_width=True, type="secondary"):
        snapshot = st.session_state.get("roadmap_v3_saved_snapshot", current_snapshot)
        _restore_roadmap_snapshot(snapshot)
        st.session_state["roadmap_v3_skip_history_once"] = True
        st.rerun()

    details_tab, planning_tab, timeline_tab = st.tabs(["Project Details", "Planning Inputs", "Task & Timeline"])

    with details_tab:
        summary_df = pd.DataFrame(
            [
                {"Attribute": "Project Name", "Value": project_name or "Untitled Project"},
                {"Attribute": "Product Profile", "Value": profile["name"]},
                {"Attribute": "Complexity", "Value": complexity},
                {"Attribute": "Project Start Date", "Value": pd.to_datetime(start_day).strftime("%d %b %Y")},
                {"Attribute": "Project End Date", "Value": project_end_date.strftime("%d %b %Y")},
                {"Attribute": "Target Working Days", "Value": duration_days},
            ]
        )
        st.markdown("### Project Summary")
        st.dataframe(summary_df, use_container_width=True, hide_index=True, height=250)
        st.markdown("### Market Comparison")
        st.dataframe(market_df, use_container_width=True, hide_index=True, height=240)
        st.markdown("### Timeline Summary")
        with st.container(border=True):
            row_a = st.columns([1, 1], gap="small")
            row_a[0].markdown("**Selected Start Date**")
            row_a[1].markdown(pd.to_datetime(start_day).strftime("%d %b %Y"))

            row_b = st.columns([1, 1], gap="small")
            row_b[0].markdown("**Projected End Date**")
            row_b[1].markdown(project_end_date.strftime("%d %b %Y"))

            row_c = st.columns([1, 1], gap="small")
            row_c[0].markdown("**Chennai Holiday List**")
            if row_c[1].button(
                f"{len(holiday_df)} configured holiday(s)",
                key="roadmap_v3_holiday_jump",
                type="secondary",
                use_container_width=True,
                help="Open the Planning Inputs tab and review the Holiday Calendar section.",
            ):
                st.session_state["roadmap_v3_holiday_hint"] = True
                st.info("Open the Planning Inputs tab. The Holiday Calendar section is ready for review.")

            row_d = st.columns([1, 1], gap="small")
            row_d[0].markdown("**Planned Working Days**")
            row_d[1].markdown(str(duration_days))

    with planning_tab:
        if st.session_state.pop("roadmap_v3_holiday_hint", False):
            st.info("Holiday Calendar is the next section in this tab.")

        st.markdown("### Team Allocation")
        st.caption("Editable team setup. Suggested resources remain AI-guided and are intentionally read-only.")
        team_editor = st.data_editor(
            team_df,
            key="roadmap_v3_team_editor",
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            height=340,
            column_config={
                "Use Team": st.column_config.CheckboxColumn("Use", default=True, help="Include or exclude this team from roadmap generation."),
                "Team": st.column_config.TextColumn("Team", required=True, width="medium", help="Delivery team or discipline."),
                "Resources": st.column_config.NumberColumn("Resources", min_value=1, max_value=30, step=1, width="small", help="Editable resource count for this team."),
                "Resource Names": st.column_config.TextColumn("Resource Names", width="large", help="Comma-separated resource names generated from the selected count."),
                "Skill Level": st.column_config.SelectboxColumn("Skill Level", options=["Junior", "Mid", "Senior"], required=True, width="small", help="Primary skill band for this team."),
                "Allocation %": st.column_config.NumberColumn("Allocation %", min_value=20, max_value=100, step=5, width="small", help="Planned allocation percentage."),
                "Suggested Resources": st.column_config.NumberColumn("Suggested", disabled=True, width="small", help="AI recommendation based on project profile and complexity."),
                "Allocation Guidance": st.column_config.TextColumn("Guidance", width="medium", help="Compact delivery guidance for the team."),
            },
        )
        team_df = _clean_team_input_df(team_editor)
        st.session_state["roadmap_v3_team_df"] = team_df

        st.markdown("### Holiday Calendar")
        holiday_actions = st.columns([1, 1, 4], gap="small")
        if holiday_actions[0].button("＋ Row Above", key="roadmap_v3_holiday_top", use_container_width=True):
            blank_row = pd.DataFrame([{"Date": pd.to_datetime(start_day).date(), "Holiday": ""}])
            st.session_state["roadmap_v3_holiday_df"] = pd.concat([blank_row, holiday_df], ignore_index=True)
            st.rerun()
        if holiday_actions[1].button("＋ Row Below", key="roadmap_v3_holiday_bottom", use_container_width=True):
            blank_row = pd.DataFrame([{"Date": pd.to_datetime(start_day).date(), "Holiday": ""}])
            st.session_state["roadmap_v3_holiday_df"] = pd.concat([holiday_df, blank_row], ignore_index=True)
            st.rerun()
        holiday_editor = st.data_editor(
            holiday_df,
            key="roadmap_v3_holiday_editor",
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            height=280,
            column_config={
                "Date": st.column_config.DateColumn("Date", format="DD-MM-YYYY", required=True, help="Public holiday date used for project-end calculation."),
                "Holiday": st.column_config.TextColumn("Holiday", required=True, width="medium", help="Holiday name or closure note."),
            },
        )
        holiday_df = clean_holiday_df(holiday_editor)
        st.session_state["roadmap_v3_holiday_df"] = holiday_df

        st.markdown("### Development Approach")
        module_metrics = st.columns(4, gap="small")
        module_metrics[0].metric("Modules", int(module_df["Use Module"].sum()))
        module_metrics[1].metric("Reuse Modules", int((module_df["Build Strategy"] == "Reuse Existing Module").sum()))
        module_metrics[2].metric("AI-Enabled", int((module_df["AI Component"] != "No").sum()))
        module_metrics[3].metric("Fresh APIs", int((module_df["Total APIs"] - module_df["Validated APIs"]).clip(lower=0).sum()))
        module_editor = st.data_editor(
            module_df,
            key="roadmap_v3_module_editor",
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            height=340,
            column_config={
                "Use Module": st.column_config.CheckboxColumn("Use", default=True, help="Include the module in the roadmap."),
                "Module": st.column_config.TextColumn("Module", required=True, width="medium", help="Module or workstream name."),
                "Team Responsible": st.column_config.SelectboxColumn("Team Responsible", options=sorted(team_df["Team"].tolist()), required=True, width="medium", help="Primary team delivering the module."),
                "Build Strategy": st.column_config.SelectboxColumn("Build Strategy", options=["Build from Scratch", "Reuse Existing Module"], required=True, width="medium", help="Delivery strategy for the module."),
                "Reuse Reduction %": st.column_config.NumberColumn("Reuse Reduction %", min_value=0, max_value=80, step=5, width="small", help="Expected effort reduction from reuse."),
                "AI Component": st.column_config.SelectboxColumn("AI Component", options=["No", "Assistive", "Core"], required=True, width="small", help="Level of AI usage in the build path."),
                "Total APIs": st.column_config.NumberColumn("Total APIs", min_value=0, max_value=50, step=1, width="small", help="Total APIs involved in the module."),
                "Validated APIs": st.column_config.NumberColumn("Validated APIs", min_value=0, max_value=50, step=1, width="small", help="Previously validated APIs reused from earlier phases."),
                "Enough Data": st.column_config.SelectboxColumn("Enough Data", options=["Yes", "No", "Partial"], required=True, width="small", help="Whether the team has enough data for validation."),
                "Dependencies": st.column_config.TextColumn("Dependency Reference", width="medium", help="Critical dependency or reuse reference."),
            },
        )
        module_df = _clean_module_input_df(module_editor)
        st.session_state["roadmap_v3_module_df"] = module_df

    active_team_df = team_df[team_df["Use Team"]].copy()
    active_module_df = module_df[module_df["Use Module"]].copy()
    if active_team_df.empty:
        active_team_df = team_df.copy()
    if active_module_df.empty:
        active_module_df = module_df.copy()

    resource_options = _resource_options(active_team_df)

    with timeline_tab:
        st.markdown("### Task Input")
        st.caption("Select the team, assign a resource from the enabled team pool, and shape the work that will generate the timeline.")
        task_df = _prepare_task_df(st.session_state["roadmap_v3_task_df"], resource_options)
        task_editor = st.data_editor(
            task_df,
            key="roadmap_v3_task_editor",
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            height=420,
            column_config={
                "Task Key": st.column_config.TextColumn("Task Key", required=True, help="Unique task identifier."),
                "Phase": st.column_config.SelectboxColumn("Phase", options=["Requirement Gathering", "Design", "Development", "Testing", "Deployment", "Post-Production Support"], required=True, width="medium", help="Delivery phase for the task."),
                "Task Name": st.column_config.TextColumn("Task Name", required=True, width="medium", help="Task description."),
                "Team Responsible": st.column_config.SelectboxColumn("Team Responsible", options=sorted(active_team_df["Team"].tolist()), required=True, width="medium", help="Owning team for the task."),
                "Assigned Resource": st.column_config.SelectboxColumn("Assigned Resource", options=resource_options, width="medium", help="Resource chosen from the active team pool."),
                "Effort Days": st.column_config.NumberColumn("Effort Days", min_value=1, max_value=180, step=1, width="small", help="Estimated effort in working days."),
                "Execution": st.column_config.SelectboxColumn("Execution", options=["Sequential", "Parallel"], required=True, width="small", help="Whether the task can run in parallel."),
                "Build Strategy": st.column_config.SelectboxColumn("Build Strategy", options=["Build from Scratch", "Reuse Existing Module"], required=True, width="medium", help="Build vs reuse decision for the task."),
                "Reuse Reduction %": st.column_config.NumberColumn("Reuse Reduction %", min_value=0, max_value=80, step=5, width="small", help="Expected effort reduction for reused work."),
                "Dependency": st.column_config.TextColumn("Dependency", width="small", help="Immediate predecessor or blocker."),
                "Reuse Dependency": st.column_config.TextColumn("Dependency Notes", width="medium", help="Additional notes or reuse references."),
            },
        )
        task_df = _prepare_task_df(task_editor, resource_options)
        st.session_state["roadmap_v3_task_df"] = task_df
        _track_roadmap_history(_build_roadmap_snapshot(project_name, project_description, duration_days, start_day, team_df, holiday_df, module_df, task_df, signature))

        adjusted_task_df = _apply_module_modifiers(task_df, active_module_df)
        schedule_team_df = active_team_df.drop(columns=["Use Team"])
        roadmap_df, holiday_dates, working_start = schedule_tasks(adjusted_task_df, schedule_team_df, start_day, holiday_df)
        actual_end = roadmap_df["End Date"].max()
        actual_workdays = max((pd.to_datetime(actual_end) - pd.to_datetime(working_start)).days + 1, 1)
        critical_path = compute_critical_path(adjusted_task_df)
        roadmap_df = attach_risk_levels(roadmap_df, adjusted_task_df, schedule_team_df, critical_path)
        utilization_df = build_team_utilization(roadmap_df, schedule_team_df, working_start, actual_end, holiday_dates)
        achievable, remediation = _achievability_summary(duration_days, actual_workdays, active_module_df)
        recommendations = remediation + build_recommendations(roadmap_df, utilization_df, critical_path, complexity, actual_end if achievable else working_start, actual_end, schedule_team_df)

        status_class = "risk-low" if achievable else "risk-high"
        st.markdown(
            f"""
            <div class="workspace-detail-card" style="margin-bottom:16px;">
                <h4>AI Feasibility Check</h4>
                <div class="roadmap-risk-pill {status_class}">{'Achievable' if achievable else 'Not Achievable'}</div>
                <p style="margin-top:12px;">Working start: {working_start.strftime('%d %b %Y')}</p>
                <p>Roadmap end: {actual_end.strftime('%d %b %Y')}</p>
                <p>Estimated working span: {actual_workdays} day(s)</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### Roadmap Table")
        st.dataframe(roadmap_df[["Task Name", "Team Responsible", "Start Date", "End Date", "Duration", "Dependency", "Status", "Risk", "Critical Path"]], use_container_width=True, hide_index=True, height=360)
        st.markdown("### Gantt Timeline")
        st.plotly_chart(_build_team_timeline_figure(roadmap_df), use_container_width=True)

        st.markdown("### Remediation")
        st.markdown(f"<div class='roadmap-note-card'><ul>{''.join(f'<li>{item}</li>' for item in recommendations[:8])}</ul></div>", unsafe_allow_html=True)

        summary_df = pd.DataFrame(
            [
                {"Attribute": "Project Name", "Value": project_name or "Untitled Project"},
                {"Attribute": "Product Profile", "Value": profile["name"]},
                {"Attribute": "Complexity", "Value": complexity},
                {"Attribute": "Selected Start", "Value": pd.to_datetime(start_day).strftime("%d %b %Y")},
                {"Attribute": "Projected End", "Value": project_end_date.strftime("%d %b %Y")},
                {"Attribute": "Working Start", "Value": working_start.strftime("%d %b %Y")},
                {"Attribute": "Target Working Days", "Value": duration_days},
                {"Attribute": "Estimated Working Span", "Value": actual_workdays},
            ]
        )
        timeline_df = pd.DataFrame(
            [
                {"Metric": "Working Start Date", "Value": working_start.strftime("%d %b %Y")},
                {"Metric": "Roadmap End Date", "Value": actual_end.strftime("%d %b %Y")},
                {"Metric": "Projected End Date", "Value": project_end_date.strftime("%d %b %Y")},
                {"Metric": "Target Duration", "Value": duration_days},
                {"Metric": "Estimated Duration", "Value": actual_workdays},
                {"Metric": "Achievability", "Value": "Achievable" if achievable else "Not Achievable"},
            ]
        )
        workbook_bytes = build_export_workbook(
            summary_df,
            market_df,
            timeline_df,
            schedule_team_df,
            active_module_df,
            adjusted_task_df,
            roadmap_df,
            roadmap_df[["Task Name", "Phase", "Team Responsible", "Start Date", "End Date", "Risk", "Dependency"]],
            holiday_df,
            build_gantt_text(roadmap_df, working_start, holiday_dates),
        )
        pdf_bytes = _build_safe_roadmap_pdf(f"{PRODUCT_NAME} | {project_name or 'Enterprise Roadmap'}", project_description, summary_df, market_df, timeline_df, roadmap_df, recommendations)
        word_bytes = build_word_report(
            project_name or f"{PRODUCT_NAME} Roadmap",
            [
                {"heading": "Project Summary", "paragraphs": [project_description, f"Projected end date: {project_end_date.strftime('%d %b %Y')}", f"Achievability: {'Achievable' if achievable else 'Not Achievable'}"]},
                {"heading": "Remediation", "bullets": recommendations[:8]},
            ],
            subtitle="Review-ready summary generated from the roadmap workspace",
        )
        export_cols = st.columns([1, 1, 1, 3], gap="small")
        export_cols[0].download_button("📊 Export Excel", data=workbook_bytes, file_name=f"{slugify(project_name or 'project_roadmap')}_roadmap.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary", use_container_width=True)
        export_cols[1].download_button("📄 Export PDF", data=pdf_bytes, file_name=f"{slugify(project_name or 'project_roadmap')}_roadmap.pdf", mime="application/pdf", type="secondary", use_container_width=True)
        export_cols[2].download_button("📝 Review Word Doc", data=word_bytes, file_name=f"{slugify(project_name or 'project_roadmap')}_review.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", type="tertiary", use_container_width=True)
