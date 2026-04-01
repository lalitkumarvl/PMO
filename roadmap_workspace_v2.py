import json
import textwrap

import pandas as pd
import streamlit as st

from roadmap_workspace import (
    attach_risk_levels,
    build_default_holiday_df,
    build_default_module_df,
    build_default_team_df,
    build_export_workbook,
    build_gantt_figure,
    build_gantt_text,
    build_market_comparison_df,
    build_recommendations,
    build_roadmap_pdf,
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


def _inject_enterprise_ui_styles():
    st.markdown(
        """
        <style>
        div.stButton > button,
        div.stDownloadButton > button {
            height: 3.25rem;
            border-radius: 1rem;
            font-weight: 700;
            letter-spacing: 0.01em;
            border: 1px solid rgba(37, 99, 235, 0.16);
            box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
            transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
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
        div[data-testid="stDataFrame"],
        div[data-testid="stDataEditor"] {
            max-width: 100%;
        }
        div[data-testid="stDataFrameResizable"] {
            max-width: 100%;
            overflow-x: auto !important;
            border-radius: 1.25rem;
            border: 1px solid rgba(148, 163, 184, 0.22);
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.8);
        }
        div[data-testid="stDataEditor"] [data-testid="stDataFrameResizable"],
        div[data-testid="stDataFrame"] [data-testid="stDataFrameResizable"] {
            overflow-x: auto !important;
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


def _clean_team_input_df(team_df):
    clean_df = team_df.copy()
    clean_df["Use Team"] = clean_df["Use Team"].fillna(True).astype(bool)
    clean_df["Resources"] = pd.to_numeric(clean_df["Resources"], errors="coerce").fillna(1).clip(lower=1).astype(int)
    clean_df["Allocation %"] = pd.to_numeric(clean_df["Allocation %"], errors="coerce").fillna(100).clip(lower=20, upper=100).astype(int)
    clean_df["Suggested Resources"] = pd.to_numeric(clean_df["Suggested Resources"], errors="coerce").fillna(clean_df["Resources"]).clip(lower=1).astype(int)
    clean_df["Skill Level"] = clean_df["Skill Level"].where(clean_df["Skill Level"].isin(["Junior", "Mid", "Senior"]), "Mid")
    clean_df["Allocation Guidance"] = clean_df["Allocation Guidance"].fillna("").astype(str).apply(_compact_copy)
    return clean_df.reset_index(drop=True)


def _clean_module_input_df(module_df):
    clean_df = module_df.copy()
    clean_df["Use Module"] = clean_df["Use Module"].fillna(True).astype(bool)
    clean_df["Build Strategy"] = clean_df["Build Strategy"].where(
        clean_df["Build Strategy"].isin(["Build from Scratch", "Reuse Existing Module"]),
        "Build from Scratch",
    )
    clean_df["Reuse Reduction %"] = pd.to_numeric(clean_df["Reuse Reduction %"], errors="coerce").fillna(0).clip(lower=0, upper=80).astype(int)
    clean_df["AI Component"] = clean_df["AI Component"].where(clean_df["AI Component"].isin(["No", "Assistive", "Core"]), "No")
    clean_df["Total APIs"] = pd.to_numeric(clean_df["Total APIs"], errors="coerce").fillna(0).clip(lower=0).astype(int)
    clean_df["Validated APIs"] = pd.to_numeric(clean_df["Validated APIs"], errors="coerce").fillna(0).clip(lower=0).astype(int)
    clean_df["Enough Data"] = clean_df["Enough Data"].where(clean_df["Enough Data"].isin(["Yes", "No", "Partial"]), "Yes")
    clean_df["Dependencies"] = clean_df["Dependencies"].fillna("").astype(str)
    return clean_df.reset_index(drop=True)


def _merge_input_defaults(default_df, existing_df, key_column):
    if existing_df is None or len(existing_df) == 0:
        return default_df.copy()
    existing_map = pd.DataFrame(existing_df).set_index(key_column).to_dict(orient="index")
    merged_rows = []
    for row in default_df.to_dict(orient="records"):
        current = existing_map.get(row[key_column], {})
        merged_rows.append({**row, **{k: v for k, v in current.items() if k in row or k not in {key_column}}})
    existing_keys = set(default_df[key_column].tolist())
    for row in pd.DataFrame(existing_df).to_dict(orient="records"):
        if row[key_column] not in existing_keys:
            merged_rows.append(row)
    return pd.DataFrame(merged_rows)


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
    return [
        {column: _normalize_snapshot_value(value) for column, value in row.items()}
        for row in pd.DataFrame(dataframe).to_dict(orient="records")
    ]


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


def _build_default_roadmap_state(project_name, project_description, duration_days, start_day, profile, complexity, signature):
    team_df = build_default_team_df(profile, complexity)
    team_df["Use Team"] = True
    module_df = build_default_module_df(profile, complexity)
    module_df["Use Module"] = True
    module_df["AI Component"] = "No"
    module_df["Total APIs"] = 0
    module_df["Validated APIs"] = 0
    module_df["Enough Data"] = "Yes"
    holiday_df = build_default_holiday_df(start_day, duration_days)
    task_df = generate_default_task_df(
        project_name,
        duration_days,
        complexity,
        team_df.drop(columns=["Use Team"]),
        module_df.drop(columns=["Use Module", "AI Component", "Total APIs", "Validated APIs", "Enough Data"], errors="ignore"),
    )
    return _build_roadmap_snapshot(project_name, project_description, duration_days, start_day, team_df, holiday_df, module_df, task_df, signature)


def _snapshot_fingerprint(snapshot):
    return json.dumps(snapshot, sort_keys=True, default=str)


def _restore_roadmap_snapshot(snapshot):
    st.session_state["roadmap_v2_project_name"] = snapshot["project_name"]
    st.session_state["roadmap_v2_project_description"] = snapshot["project_description"]
    st.session_state["roadmap_v2_duration"] = int(snapshot["duration_days"])
    st.session_state["roadmap_v2_start"] = pd.to_datetime(snapshot["start_day"]).date()
    st.session_state["roadmap_v2_team_df"] = pd.DataFrame(snapshot["team_df"])
    st.session_state["roadmap_v2_holiday_df"] = pd.DataFrame(snapshot["holiday_df"])
    st.session_state["roadmap_v2_module_df"] = pd.DataFrame(snapshot["module_df"])
    st.session_state["roadmap_v2_task_df"] = pd.DataFrame(snapshot["task_df"])
    st.session_state["roadmap_v2_signature"] = snapshot["signature"]
    st.session_state["roadmap_v2_task_signature"] = snapshot["signature"]


def _track_roadmap_history(current_snapshot):
    st.session_state.setdefault("roadmap_v2_undo", [])
    st.session_state.setdefault("roadmap_v2_redo", [])
    fingerprint = _snapshot_fingerprint(current_snapshot)
    if st.session_state.pop("roadmap_v2_skip_history_once", False):
        st.session_state["roadmap_v2_last_snapshot"] = current_snapshot
        st.session_state["roadmap_v2_last_snapshot_fp"] = fingerprint
        return

    last_fingerprint = st.session_state.get("roadmap_v2_last_snapshot_fp")
    last_snapshot = st.session_state.get("roadmap_v2_last_snapshot")
    if last_fingerprint is None:
        st.session_state["roadmap_v2_last_snapshot"] = current_snapshot
        st.session_state["roadmap_v2_last_snapshot_fp"] = fingerprint
        return

    if fingerprint != last_fingerprint and last_snapshot is not None:
        st.session_state["roadmap_v2_undo"].append(last_snapshot)
        st.session_state["roadmap_v2_undo"] = st.session_state["roadmap_v2_undo"][-25:]
        st.session_state["roadmap_v2_redo"].clear()
        st.session_state["roadmap_v2_last_snapshot"] = current_snapshot
        st.session_state["roadmap_v2_last_snapshot_fp"] = fingerprint


def _apply_module_modifiers(task_df, module_df):
    adjusted_df = task_df.copy()
    module_lookup = {row["Module"]: row for row in module_df.to_dict(orient="records")}
    for index, row in adjusted_df.iterrows():
        module_settings = module_lookup.get(row["Task Name"])
        if not module_settings:
            continue
        effort = float(row["Effort Days"])
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


def _achievability_summary(duration_days, actual_workdays, module_df):
    blockers = []
    if actual_workdays > duration_days:
        blockers.append(f"Current plan exceeds the target by {actual_workdays - duration_days} working day(s).")
    if not module_df.empty and (module_df["Enough Data"] == "No").any():
        blockers.append("One or more modules do not have enough data for confident validation.")
    if not module_df.empty and ((module_df["Total APIs"] - module_df["Validated APIs"]).clip(lower=0) > 4).any():
        blockers.append("The roadmap includes multiple fresh APIs that may increase integration uncertainty.")

    achievable = not blockers
    remediation = blockers or ["Current plan is achievable if scope and staffing remain stable."]
    return achievable, remediation


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
                safe_line = _roadmap_pdf_safe_text(line)
                wrapped = textwrap.wrap(safe_line, width=88, break_long_words=True, break_on_hyphens=True) or ["-"]
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
        write_lines(
            [
                f"{row['Product Name']} | {row['Organization']} | {row['Key Differentiation']}"
                for row in market_df.head(5).to_dict(orient="records")
            ]
        )
        pdf.ln(1)

        write_lines(["Roadmap Highlights"], font_style="B", font_size=13)
        write_lines(
            [
                f"{row['Task Name']} | {row['Team Responsible']} | {pd.to_datetime(row['Start Date']).strftime('%d %b %Y')} to {pd.to_datetime(row['End Date']).strftime('%d %b %Y')} | {row['Risk']}"
                for row in roadmap_df.head(12).to_dict(orient="records")
            ]
        )
        pdf.ln(1)

        write_lines(["Recommendations"], font_style="B", font_size=13)
        write_lines([f"- {item}" for item in recommendations[:8]])
        return bytes(pdf.output(dest="S"))
    except Exception:
        return b"%PDF-1.4\n%PMO fallback roadmap PDF export unavailable\n"


def render_roadmap_workspace_v2():
    _inject_enterprise_ui_styles()

    project_name = st.text_input("Project Name", value=st.session_state.get("roadmap_v2_project_name", ""), key="roadmap_v2_project_name")
    project_description = st.text_area(
        "Project Description",
        value=st.session_state.get(
            "roadmap_v2_project_description",
            "Build an enterprise project workspace with workflow visibility, planning, and management reporting.",
        ),
        key="roadmap_v2_project_description",
        height=120,
    )
    top_inputs = st.columns([1, 1], gap="small")
    with top_inputs[0]:
        duration_days = int(
            st.number_input(
                "Project Duration (working days)",
                min_value=10,
                max_value=365,
                value=int(st.session_state.get("roadmap_v2_duration", 90)),
                step=5,
                key="roadmap_v2_duration",
            )
        )
    with top_inputs[1]:
        start_day = st.date_input("Project Start Date", value=st.session_state.get("roadmap_v2_start", pd.Timestamp.today().date()), key="roadmap_v2_start")

    profile = infer_profile(project_description)
    base_module_df = build_default_module_df(profile, "Medium")
    complexity = infer_complexity(project_description, duration_days, len(base_module_df))
    default_team_df = build_default_team_df(profile, complexity)
    default_team_df["Use Team"] = True
    default_module_df = build_default_module_df(profile, complexity)
    default_module_df["Use Module"] = True
    default_module_df["AI Component"] = "No"
    default_module_df["Total APIs"] = 0
    default_module_df["Validated APIs"] = 0
    default_module_df["Enough Data"] = "Yes"
    default_holiday_df = build_default_holiday_df(start_day, duration_days)

    signature = "|".join([project_name.strip(), project_description.strip(), str(duration_days), str(start_day), complexity, profile["id"]])
    if st.session_state.get("roadmap_v2_signature") != signature:
        st.session_state["roadmap_v2_signature"] = signature
        st.session_state["roadmap_v2_team_df"] = _merge_input_defaults(default_team_df, st.session_state.get("roadmap_v2_team_df"), "Team")
        st.session_state["roadmap_v2_module_df"] = _merge_input_defaults(default_module_df, st.session_state.get("roadmap_v2_module_df"), "Module")
        st.session_state["roadmap_v2_holiday_df"] = clean_holiday_df(
            pd.concat(
                [default_holiday_df, pd.DataFrame(st.session_state.get("roadmap_v2_holiday_df", []))],
                ignore_index=True,
            )
        )

    team_df = _clean_team_input_df(pd.DataFrame(st.session_state["roadmap_v2_team_df"]))
    module_df = _clean_module_input_df(pd.DataFrame(st.session_state["roadmap_v2_module_df"]))
    holiday_df = clean_holiday_df(pd.DataFrame(st.session_state["roadmap_v2_holiday_df"]))
    market_df = build_market_comparison_df(profile)

    details_tab, planning_tab, timeline_tab = st.tabs(["Project Details", "Planning Inputs", "Task & Timeline"])

    with details_tab:
        st.markdown(
            f"""
            <div class="app-hero">
                <div class="hero-main">
                    <div class="hero-kicker">Create RoadMap</div>
                    <div class="hero-title">{project_name or 'Enterprise Roadmap Studio'}</div>
                    <p class="hero-text">{project_description}</p>
                    <div class="hero-meta">
                        <span class="hero-meta-chip">Profile: {profile['name']}</span>
                        <span class="hero-meta-chip">Complexity: {complexity}</span>
                        <span class="hero-meta-chip">Working duration: {duration_days} day(s)</span>
                    </div>
                </div>
                <div class="hero-panel">
                    <span class="hero-panel-label">Roadmap Context</span>
                    <span class="hero-panel-title">{start_day.strftime('%d %b %Y')}</span>
                    <p class="hero-panel-copy">This tab consolidates the executive inputs and market framing before the timeline is built.</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        summary_df = pd.DataFrame(
            [
                {"Attribute": "Project Name", "Value": project_name or "Untitled Project"},
                {"Attribute": "Product Profile", "Value": profile["name"]},
                {"Attribute": "Complexity", "Value": complexity},
                {"Attribute": "Project Start Date", "Value": start_day.strftime("%d %b %Y")},
                {"Attribute": "Target Working Days", "Value": duration_days},
            ]
        )
        st.markdown("### Project Summary")
        st.dataframe(summary_df, use_container_width=True, hide_index=True)
        st.markdown("### Market Comparison")
        st.dataframe(market_df, use_container_width=True, hide_index=True)
        st.markdown("### Timeline Summary")
        timeline_summary = pd.DataFrame(
            [
                {"Metric": "Selected Start Date", "Value": start_day.strftime("%d %b %Y")},
                {"Metric": "Chennai Holiday Entries", "Value": len(holiday_df)},
                {"Metric": "Planned Working Days", "Value": duration_days},
            ]
        )
        st.dataframe(timeline_summary, use_container_width=True, hide_index=True)

    with planning_tab:
        st.markdown("### Team Allocation")
        st.caption("Use the checkbox to include or exclude teams from the generated roadmap.")
        team_editor = st.data_editor(
            team_df,
            key="roadmap_v2_team_editor",
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            height=320,
            column_config={
                "Use Team": st.column_config.CheckboxColumn("Use", default=True),
                "Team": st.column_config.TextColumn("Team", required=True, width="medium"),
                "Resources": st.column_config.NumberColumn("Resources", min_value=1, max_value=30, step=1, width="small"),
                "Skill Level": st.column_config.SelectboxColumn("Skill Level", options=["Junior", "Mid", "Senior"], required=True, width="small"),
                "Allocation %": st.column_config.NumberColumn("Allocation %", min_value=20, max_value=100, step=5, width="small"),
                "Suggested Resources": st.column_config.NumberColumn("Suggested", disabled=True, width="small"),
                "Allocation Guidance": st.column_config.TextColumn("Guidance", width="medium"),
            },
        )
        team_df = _clean_team_input_df(team_editor)
        st.session_state["roadmap_v2_team_df"] = team_df

        st.markdown("### Holiday Calendar")
        holiday_actions = st.columns([1, 1, 4], gap="small")
        if holiday_actions[0].button("＋ Row Above", key="roadmap_v2_holiday_add_top", use_container_width=True):
            blank_row = pd.DataFrame([{"Date": pd.to_datetime(start_day).date(), "Holiday": ""}])
            st.session_state["roadmap_v2_holiday_df"] = pd.concat([blank_row, holiday_df], ignore_index=True)
            st.rerun()
        if holiday_actions[1].button("＋ Row Below", key="roadmap_v2_holiday_add_bottom", use_container_width=True):
            blank_row = pd.DataFrame([{"Date": pd.to_datetime(start_day).date(), "Holiday": ""}])
            st.session_state["roadmap_v2_holiday_df"] = pd.concat([holiday_df, blank_row], ignore_index=True)
            st.rerun()
        holiday_editor = st.data_editor(
            holiday_df,
            key="roadmap_v2_holiday_editor",
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            height=280,
            column_config={
                "Date": st.column_config.DateColumn("Date", format="DD-MM-YYYY", required=True),
                "Holiday": st.column_config.TextColumn("Holiday", required=True),
            },
        )
        holiday_df = clean_holiday_df(holiday_editor)
        st.session_state["roadmap_v2_holiday_df"] = holiday_df

        st.markdown("### Development Approach")
        module_editor = st.data_editor(
            module_df,
            key="roadmap_v2_module_editor",
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            height=340,
            column_config={
                "Use Module": st.column_config.CheckboxColumn("Use", default=True),
                "Module": st.column_config.TextColumn("Module", required=True, width="medium"),
                "Team Responsible": st.column_config.SelectboxColumn("Team Responsible", options=sorted(team_df["Team"].tolist()), required=True, width="medium"),
                "Build Strategy": st.column_config.SelectboxColumn("Build Strategy", options=["Build from Scratch", "Reuse Existing Module"], required=True, width="medium"),
                "Reuse Reduction %": st.column_config.NumberColumn("Reuse Reduction %", min_value=0, max_value=80, step=5, width="small"),
                "AI Component": st.column_config.SelectboxColumn("AI Component", options=["No", "Assistive", "Core"], required=True, width="small"),
                "Total APIs": st.column_config.NumberColumn("Total APIs", min_value=0, max_value=50, step=1, width="small"),
                "Validated APIs": st.column_config.NumberColumn("Validated APIs", min_value=0, max_value=50, step=1, width="small"),
                "Enough Data": st.column_config.SelectboxColumn("Enough Data", options=["Yes", "No", "Partial"], required=True, width="small"),
                "Dependencies": st.column_config.TextColumn("Dependency Reference", width="medium"),
            },
        )
        module_df = _clean_module_input_df(module_editor)
        st.session_state["roadmap_v2_module_df"] = module_df

    active_team_df = team_df[team_df["Use Team"]].copy()
    active_module_df = module_df[module_df["Use Module"]].copy()
    if active_team_df.empty:
        active_team_df = team_df.copy()
    if active_module_df.empty:
        active_module_df = module_df.copy()

    base_task_df = generate_default_task_df(project_name, duration_days, complexity, active_team_df.drop(columns=["Use Team"]), active_module_df.drop(columns=["Use Module", "AI Component", "Total APIs", "Validated APIs", "Enough Data"], errors="ignore"))
    if "roadmap_v2_task_df" not in st.session_state or st.session_state.get("roadmap_v2_task_signature") != signature:
        st.session_state["roadmap_v2_task_df"] = base_task_df
        st.session_state["roadmap_v2_task_signature"] = signature

    current_snapshot = _build_roadmap_snapshot(
        project_name,
        project_description,
        duration_days,
        start_day,
        st.session_state["roadmap_v2_team_df"],
        st.session_state["roadmap_v2_holiday_df"],
        st.session_state["roadmap_v2_module_df"],
        st.session_state["roadmap_v2_task_df"],
        signature,
    )
    default_snapshot = _build_default_roadmap_state(project_name, project_description, duration_days, start_day, profile, complexity, signature)
    _track_roadmap_history(current_snapshot)

    toolbar = st.columns([1, 1, 1, 1.2, 4], gap="small")
    if toolbar[0].button("↶ Undo", key="roadmap_v2_toolbar_undo", use_container_width=True, disabled=not st.session_state["roadmap_v2_undo"]):
        snapshot = st.session_state["roadmap_v2_undo"].pop()
        st.session_state["roadmap_v2_redo"].append(current_snapshot)
        _restore_roadmap_snapshot(snapshot)
        st.session_state["roadmap_v2_skip_history_once"] = True
        st.rerun()
    if toolbar[1].button("↷ Redo", key="roadmap_v2_toolbar_redo", use_container_width=True, disabled=not st.session_state["roadmap_v2_redo"]):
        snapshot = st.session_state["roadmap_v2_redo"].pop()
        st.session_state["roadmap_v2_undo"].append(current_snapshot)
        _restore_roadmap_snapshot(snapshot)
        st.session_state["roadmap_v2_skip_history_once"] = True
        st.rerun()
    if toolbar[2].button("✦ Save", key="roadmap_v2_toolbar_save", use_container_width=True, type="primary"):
        st.session_state["roadmap_v2_saved_snapshot"] = current_snapshot
        st.success("Roadmap inputs saved.")
    if toolbar[3].button("⟲ Reset", key="roadmap_v2_toolbar_clear", use_container_width=True, type="secondary"):
        snapshot = st.session_state.get("roadmap_v2_saved_snapshot", default_snapshot)
        _restore_roadmap_snapshot(snapshot)
        st.session_state["roadmap_v2_skip_history_once"] = True
        st.rerun()

    st.caption("Tabs available: Project Details | Planning Inputs | Task & Timeline.")

    with timeline_tab:
        st.markdown("### Task Input")
        task_df = clean_task_df(pd.DataFrame(st.session_state["roadmap_v2_task_df"]))
        task_editor = st.data_editor(
            task_df,
            key="roadmap_v2_task_editor",
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            height=420,
            column_config={
                "Task Key": st.column_config.TextColumn("Task Key", required=True),
                "Phase": st.column_config.SelectboxColumn("Phase", options=["Requirement Gathering", "Design", "Development", "Testing", "Deployment", "Post-Production Support"], required=True),
                "Task Name": st.column_config.TextColumn("Task Name", required=True, width="medium"),
                "Team Responsible": st.column_config.SelectboxColumn("Team Responsible", options=sorted(active_team_df["Team"].tolist()), required=True, width="medium"),
                "Effort Days": st.column_config.NumberColumn("Effort Days", min_value=1, max_value=180, step=1, width="small"),
                "Execution": st.column_config.SelectboxColumn("Execution", options=["Sequential", "Parallel"], required=True, width="small"),
                "Build Strategy": st.column_config.SelectboxColumn("Build Strategy", options=["Build from Scratch", "Reuse Existing Module"], required=True, width="medium"),
                "Reuse Reduction %": st.column_config.NumberColumn("Reuse Reduction %", min_value=0, max_value=80, step=5, width="small"),
                "Dependency": st.column_config.TextColumn("Dependency", width="small"),
                "Reuse Dependency": st.column_config.TextColumn("Dependency Notes", width="medium"),
            },
        )
        task_df = clean_task_df(task_editor)
        st.session_state["roadmap_v2_task_df"] = task_df
        _track_roadmap_history(
            _build_roadmap_snapshot(
                project_name,
                project_description,
                duration_days,
                start_day,
                team_df,
                holiday_df,
                module_df,
                task_df,
                signature,
            )
        )

        adjusted_task_df = _apply_module_modifiers(task_df, active_module_df)
        schedule_team_df = active_team_df.drop(columns=["Use Team"])
        roadmap_df, holiday_dates, working_start = schedule_tasks(adjusted_task_df, schedule_team_df, start_day, holiday_df)
        actual_end = roadmap_df["End Date"].max()
        actual_workdays = max((pd.to_datetime(actual_end) - pd.to_datetime(working_start)).days + 1, 1)
        critical_path = compute_critical_path(adjusted_task_df)
        roadmap_df = attach_risk_levels(roadmap_df, adjusted_task_df, schedule_team_df, critical_path)
        utilization_df = build_team_utilization(roadmap_df, schedule_team_df, working_start, actual_end, holiday_dates)
        achievable, remediation = _achievability_summary(duration_days, actual_workdays, active_module_df)
        recommendations = build_recommendations(roadmap_df, utilization_df, critical_path, complexity, actual_end if achievable else working_start, actual_end, schedule_team_df)
        recommendations = remediation + recommendations

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
        st.dataframe(
            roadmap_df[["Task Name", "Team Responsible", "Start Date", "End Date", "Duration", "Dependency", "Status", "Risk", "Critical Path"]],
            use_container_width=True,
            hide_index=True,
            height=360,
        )
        st.markdown("### Gantt Timeline")
        st.plotly_chart(build_gantt_figure(roadmap_df), use_container_width=True)

        st.markdown("### Remediation")
        st.markdown(
            f"""
            <div class="workspace-detail-card">
                <ul>{"".join(f"<li>{item}</li>" for item in recommendations[:8])}</ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

        summary_df = pd.DataFrame(
            [
                {"Attribute": "Project Name", "Value": project_name or "Untitled Project"},
                {"Attribute": "Product Profile", "Value": profile["name"]},
                {"Attribute": "Complexity", "Value": complexity},
                {"Attribute": "Selected Start", "Value": start_day.strftime("%d %b %Y")},
                {"Attribute": "Working Start", "Value": working_start.strftime("%d %b %Y")},
                {"Attribute": "Target Working Days", "Value": duration_days},
                {"Attribute": "Estimated Working Span", "Value": actual_workdays},
            ]
        )
        timeline_df = pd.DataFrame(
            [
                {"Metric": "Working Start Date", "Value": working_start.strftime("%d %b %Y")},
                {"Metric": "Roadmap End Date", "Value": actual_end.strftime("%d %b %Y")},
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
        pdf_bytes = _build_safe_roadmap_pdf(
            project_name or "Enterprise Roadmap",
            project_description,
            summary_df,
            market_df,
            timeline_df,
            roadmap_df,
            recommendations,
        )
        word_bytes = build_word_report(
            project_name or "Enterprise Roadmap",
            [
                {
                    "heading": "Dashboard Review Summary",
                    "paragraphs": [
                        project_description,
                        f"Achievability: {'Achievable' if achievable else 'Not Achievable'}",
                        f"Roadmap end date: {actual_end.strftime('%d %b %Y')}",
                    ],
                },
                {"heading": "Remediation", "bullets": recommendations[:8]},
                {
                    "heading": "Incremental Feature Backlog",
                    "bullets": [
                        "Add scenario planning against scope, staffing, and API complexity.",
                        "Add maturity scoring for AI-assisted build strategies.",
                        "Add reusable template libraries for project archetypes.",
                        "Add approval-driven roadmap baselining for PMO governance.",
                    ],
                },
            ],
            subtitle="Review-ready summary generated from the roadmap dashboard",
        )
        export_cols = st.columns([1, 1, 1, 3], gap="small")
        export_cols[0].download_button(
            "📊 Export Excel",
            data=workbook_bytes,
            file_name=f"{slugify(project_name or 'project_roadmap')}_roadmap.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True,
        )
        export_cols[1].download_button(
            "📄 Export PDF",
            data=pdf_bytes,
            file_name=f"{slugify(project_name or 'project_roadmap')}_roadmap.pdf",
            mime="application/pdf",
            type="secondary",
            use_container_width=True,
        )
        export_cols[2].download_button(
            "📝 Review Word Doc",
            data=word_bytes,
            file_name=f"{slugify(project_name or 'project_roadmap')}_review.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            type="tertiary",
            use_container_width=True,
        )
