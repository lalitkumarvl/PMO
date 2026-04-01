from datetime import date, datetime, timedelta
from io import BytesIO

import pandas as pd
import plotly.express as px
import streamlit as st
from fpdf import FPDF

try:
    from kanban_dnd_component import render_kanban_board
except ModuleNotFoundError:
    from PMO.kanban_dnd_component import render_kanban_board


SCAN_STATUS_COLORS = {
    "To Do": "#64748b",
    "In Progress": "#2457d6",
    "Review": "#d97706",
    "Done": "#059669",
    "At Risk": "#dc2626",
}


def normalize_date(value):
    if pd.isna(value):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date()


def guess_column(columns, keywords, exclude=None):
    exclude = set(exclude or [])
    lowered = {column: str(column).lower() for column in columns}
    for keyword in keywords:
        for column, lowered_name in lowered.items():
            if column in exclude:
                continue
            if keyword in lowered_name:
                return column
    return None


def build_default_mapping(df):
    columns = list(df.columns)
    mapping = {}
    mapping["task_id"] = guess_column(columns, ["task id", "id", "ticket", "work item", "issue"])
    mapping["task_name"] = guess_column(columns, ["task", "title", "summary", "name", "story"], exclude=[mapping["task_id"]])
    mapping["planned_start"] = guess_column(columns, ["planned start", "plan start", "start date", "start"])
    mapping["planned_end"] = guess_column(columns, ["planned end", "target end", "due date", "finish", "end date", "end"])
    mapping["actual_start"] = guess_column(columns, ["actual start"])
    mapping["actual_end"] = guess_column(columns, ["actual end", "completed date", "close date", "actual finish", "closed"])
    mapping["owner"] = guess_column(columns, ["owner", "assignee", "resource", "assigned"])
    mapping["team"] = guess_column(columns, ["team", "squad", "stream", "function"])
    mapping["status"] = guess_column(columns, ["status", "state", "stage"])
    mapping["dependencies"] = guess_column(columns, ["dependency", "depends", "predecessor", "blocked by"])
    mapping["skill"] = guess_column(columns, ["skill", "seniority", "level", "grade"])
    return mapping


def load_uploaded_file(uploaded_file):
    if uploaded_file is None:
        return {}
    file_name = uploaded_file.name.lower()
    if file_name.endswith(".csv"):
        return {"Timeline": pd.read_csv(uploaded_file)}
    return pd.read_excel(uploaded_file, sheet_name=None)


def infer_scan_status(row, today_value):
    raw_status = str(row.get("Raw Status", "")).strip().lower()
    if "done" in raw_status or "complete" in raw_status or "closed" in raw_status:
        return "Done"
    if "review" in raw_status or "uat" in raw_status or "validate" in raw_status:
        return "Review"
    if "progress" in raw_status or "active" in raw_status or "doing" in raw_status:
        return "In Progress"
    if row.get("Actual End"):
        return "Done"
    if row.get("Planned End") and row["Planned End"] < today_value:
        return "At Risk"
    if row.get("Planned Start") and row["Planned Start"] <= today_value:
        return "In Progress"
    return "To Do"


def normalize_scan_df(df, mapping):
    working_df = df.copy()
    today_value = date.today()

    normalized = pd.DataFrame()
    if mapping.get("task_id") and mapping["task_id"] in working_df.columns:
        normalized["Task ID"] = working_df[mapping["task_id"]].astype(str)
    else:
        normalized["Task ID"] = [f"T{index + 1:03d}" for index in range(len(working_df))]

    if mapping.get("task_name") and mapping["task_name"] in working_df.columns:
        normalized["Task Name"] = working_df[mapping["task_name"]].astype(str)
    else:
        normalized["Task Name"] = [f"Task {index + 1}" for index in range(len(working_df))]

    planned_start_series = working_df[mapping["planned_start"]] if mapping.get("planned_start") in working_df.columns else pd.Series([None] * len(working_df))
    planned_end_series = working_df[mapping["planned_end"]] if mapping.get("planned_end") in working_df.columns else pd.Series([None] * len(working_df))
    actual_start_series = working_df[mapping["actual_start"]] if mapping.get("actual_start") in working_df.columns else pd.Series([None] * len(working_df))
    actual_end_series = working_df[mapping["actual_end"]] if mapping.get("actual_end") in working_df.columns else pd.Series([None] * len(working_df))

    normalized["Planned Start"] = planned_start_series.apply(normalize_date)
    normalized["Planned End"] = planned_end_series.apply(normalize_date)
    normalized["Actual Start"] = actual_start_series.apply(normalize_date)
    normalized["Actual End"] = actual_end_series.apply(normalize_date)
    normalized["Owner"] = working_df[mapping["owner"]].astype(str) if mapping.get("owner") in working_df.columns else "Unassigned"
    normalized["Team"] = working_df[mapping["team"]].astype(str) if mapping.get("team") in working_df.columns else normalized["Owner"]
    normalized["Dependencies"] = working_df[mapping["dependencies"]].astype(str) if mapping.get("dependencies") in working_df.columns else ""
    normalized["Skill"] = working_df[mapping["skill"]].astype(str) if mapping.get("skill") in working_df.columns else ""
    normalized["Raw Status"] = working_df[mapping["status"]].astype(str) if mapping.get("status") in working_df.columns else ""

    normalized["Planned Start"] = normalized["Planned Start"].fillna(normalized["Actual Start"])
    normalized["Planned End"] = normalized["Planned End"].fillna(normalized["Actual End"])
    normalized["Duration"] = (
        pd.to_datetime(normalized["Planned End"]) - pd.to_datetime(normalized["Planned Start"])
    ).dt.days.fillna(0).astype(int) + 1
    normalized["Duration"] = normalized["Duration"].clip(lower=1)
    normalized["Status"] = normalized.apply(lambda row: infer_scan_status(row, today_value), axis=1)
    normalized["Is Valid Timeline"] = normalized["Planned Start"].notna() & normalized["Planned End"].notna()
    normalized["Task ID"] = normalized["Task ID"].fillna("").astype(str).replace("nan", "")
    normalized["Task Name"] = normalized["Task Name"].fillna("Untitled Task").astype(str)
    normalized["Owner"] = normalized["Owner"].fillna("Unassigned").astype(str)
    normalized["Team"] = normalized["Team"].fillna("Unassigned").astype(str)
    normalized["Dependencies"] = normalized["Dependencies"].fillna("").astype(str)
    return normalized


def parse_dependencies(raw_value):
    cleaned = [item.strip() for item in str(raw_value).replace(";", ",").split(",")]
    return [item for item in cleaned if item and item.lower() != "nan"]


def analyze_dependencies(normalized_df):
    valid_refs = set(normalized_df["Task ID"].tolist()) | set(normalized_df["Task Name"].tolist())
    missing_rows = []
    dependent_map = {task_id: 0 for task_id in normalized_df["Task ID"].tolist()}
    for row in normalized_df.to_dict(orient="records"):
        dependencies = parse_dependencies(row["Dependencies"])
        for dependency in dependencies:
            if dependency in dependent_map:
                dependent_map[dependency] += 1
            if dependency not in valid_refs:
                missing_rows.append(
                    {
                        "Task ID": row["Task ID"],
                        "Task Name": row["Task Name"],
                        "Missing Dependency": dependency,
                    }
                )
    return pd.DataFrame(missing_rows), dependent_map


def overlap_days(start_a, end_a, start_b, end_b):
    if not start_a or not end_a or not start_b or not end_b:
        return 0
    latest_start = max(start_a, start_b)
    earliest_end = min(end_a, end_b)
    if latest_start > earliest_end:
        return 0
    return (earliest_end - latest_start).days + 1


def analyze_resource_conflicts(normalized_df):
    conflict_rows = []
    owner_conflicts = {}
    valid_df = normalized_df[normalized_df["Is Valid Timeline"]].copy()
    for owner_name, owner_df in valid_df.groupby("Owner"):
        rows = owner_df.sort_values(["Planned Start", "Planned End"]).to_dict(orient="records")
        for index, row in enumerate(rows):
            for compare_row in rows[index + 1 :]:
                overlap = overlap_days(row["Planned Start"], row["Planned End"], compare_row["Planned Start"], compare_row["Planned End"])
                if overlap > 0:
                    conflict_rows.append(
                        {
                            "Owner": owner_name,
                            "Task A": row["Task Name"],
                            "Task B": compare_row["Task Name"],
                            "Overlap Days": overlap,
                        }
                    )
                    owner_conflicts[owner_name] = owner_conflicts.get(owner_name, 0) + 1
    return pd.DataFrame(conflict_rows), owner_conflicts


def detect_skill_mismatches(normalized_df):
    mismatch_rows = []
    for row in normalized_df.to_dict(orient="records"):
        skill = str(row["Skill"]).strip().lower()
        task_name = row["Task Name"].lower()
        needs_senior = any(keyword in task_name for keyword in ["architecture", "security", "deploy", "release", "integration", "migration"])
        if needs_senior and skill and skill.startswith("jun"):
            mismatch_rows.append(
                {
                    "Task Name": row["Task Name"],
                    "Owner": row["Owner"],
                    "Skill": row["Skill"],
                    "Issue": "Task appears senior-heavy for assigned skill level.",
                }
            )
    return pd.DataFrame(mismatch_rows)


def compute_critical_path(normalized_df):
    tasks = {}
    valid_refs = set(normalized_df["Task ID"].tolist())
    for row in normalized_df.to_dict(orient="records"):
        dependencies = [dependency for dependency in parse_dependencies(row["Dependencies"]) if dependency in valid_refs]
        tasks[row["Task ID"]] = {"duration": max(int(row["Duration"]), 1), "dependencies": dependencies}
    memo = {}

    def walk(task_id):
        if task_id in memo:
            return memo[task_id]
        task = tasks[task_id]
        if not task["dependencies"]:
            memo[task_id] = (task["duration"], [task_id])
            return memo[task_id]
        best_duration = -1
        best_path = []
        for dependency in task["dependencies"]:
            dep_duration, dep_path = walk(dependency)
            if dep_duration > best_duration:
                best_duration = dep_duration
                best_path = dep_path
        memo[task_id] = (best_duration + task["duration"], best_path + [task_id])
        return memo[task_id]

    longest_duration = -1
    longest_path = []
    for task_id in tasks:
        duration_value, path = walk(task_id)
        if duration_value > longest_duration:
            longest_duration = duration_value
            longest_path = path
    return longest_path


def build_task_insights(normalized_df, missing_dep_df, owner_conflicts, dependent_map, critical_path):
    today_value = date.today()
    missing_dep_set = {
        (row["Task ID"], row["Missing Dependency"])
        for row in missing_dep_df.to_dict(orient="records")
    }
    insights = []
    for row in normalized_df.to_dict(orient="records"):
        planned_end = row["Planned End"]
        actual_end = row["Actual End"]
        if planned_end and actual_end:
            delay_days = max((actual_end - planned_end).days, 0)
        elif planned_end and row["Status"] != "Done" and planned_end < today_value:
            delay_days = (today_value - planned_end).days
        else:
            delay_days = 0

        dependency_missing = any(task_id == row["Task ID"] for task_id, _ in missing_dep_set)
        conflict_count = owner_conflicts.get(row["Owner"], 0)
        downstream_count = dependent_map.get(row["Task ID"], 0)
        risk_score = 0
        if delay_days > 0:
            risk_score += 2
        if dependency_missing:
            risk_score += 2
        if conflict_count > 0:
            risk_score += 1
        if row["Task ID"] in critical_path:
            risk_score += 2
        if downstream_count >= 2:
            risk_score += 1

        if risk_score >= 5:
            risk_level = "High"
        elif risk_score >= 2:
            risk_level = "Medium"
        else:
            risk_level = "Low"

        recommendation_parts = []
        if delay_days > 0:
            recommendation_parts.append("Rebaseline or accelerate this task.")
        if dependency_missing:
            recommendation_parts.append("Resolve missing predecessor references.")
        if conflict_count > 0:
            recommendation_parts.append("Reduce owner overlap or reassign in-flight work.")
        if row["Task ID"] in critical_path and not recommendation_parts:
            recommendation_parts.append("Protect this task because it sits on the critical path.")
        if not recommendation_parts:
            recommendation_parts.append("Track normally.")

        insights.append(
            {
                "Task ID": row["Task ID"],
                "Task Name": row["Task Name"],
                "Owner": row["Owner"],
                "Team": row["Team"],
                "Planned Start": row["Planned Start"],
                "Planned End": row["Planned End"],
                "Status": row["Status"],
                "Delay Days": delay_days,
                "Dependency Missing": "Yes" if dependency_missing else "No",
                "Owner Conflict Count": conflict_count,
                "Downstream Dependents": downstream_count,
                "Critical Path": "Yes" if row["Task ID"] in critical_path else "No",
                "Risk": risk_level,
                "Recommendation": " ".join(recommendation_parts),
            }
        )
    return pd.DataFrame(insights)


def build_resource_utilization(normalized_df):
    valid_df = normalized_df[normalized_df["Is Valid Timeline"]].copy()
    if valid_df.empty:
        return pd.DataFrame(columns=["Owner", "Task Count", "Assigned Days", "Schedule Span", "Utilization %", "Status"])

    project_start = valid_df["Planned Start"].min()
    project_end = valid_df["Planned End"].max()
    schedule_span = max((project_end - project_start).days + 1, 1)
    rows = []
    for owner_name, owner_df in valid_df.groupby("Owner"):
        task_count = len(owner_df)
        assigned_days = int(owner_df["Duration"].sum())
        utilization = (assigned_days / schedule_span) * 100
        if utilization >= 95:
            status = "Over-utilized"
        elif utilization < 35:
            status = "Under-utilized"
        else:
            status = "Balanced"
        rows.append(
            {
                "Owner": owner_name,
                "Task Count": task_count,
                "Assigned Days": assigned_days,
                "Schedule Span": schedule_span,
                "Utilization %": round(utilization, 1),
                "Status": status,
            }
        )
    return pd.DataFrame(rows).sort_values("Utilization %", ascending=False).reset_index(drop=True)


def build_timeline_variance(normalized_df, insights_df):
    variance_df = insights_df.groupby("Owner", dropna=False)["Delay Days"].sum().reset_index(name="Delay Days")
    variance_df = variance_df.sort_values("Delay Days", ascending=False).reset_index(drop=True)
    return variance_df


def build_optimization_suggestions(normalized_df, insights_df, utilization_df, missing_dep_df, owner_conflicts):
    suggestions = []
    delayed_count = len(insights_df[insights_df["Delay Days"] > 0])
    if delayed_count:
        suggestions.append(f"Re-sequence {delayed_count} delayed tasks and fast-track the ones on the critical path first.")
    if not missing_dep_df.empty:
        suggestions.append("Clean dependency mapping before the next planning cycle to avoid false start dates and hidden blockers.")
    if owner_conflicts:
        hottest_owner = max(owner_conflicts, key=owner_conflicts.get)
        suggestions.append(f"Reassign overlapping tasks away from {hottest_owner} to reduce multi-tasking conflicts.")
    under_utilized = utilization_df[utilization_df["Status"] == "Under-utilized"]
    over_utilized = utilization_df[utilization_df["Status"] == "Over-utilized"]
    if not under_utilized.empty and not over_utilized.empty:
        suggestions.append(
            f"Move selected tasks from {over_utilized.iloc[0]['Owner']} to {under_utilized.iloc[0]['Owner']} to compress the delivery path."
        )
    tasks_with_no_deps = insights_df[(insights_df["Dependency Missing"] == "No") & (insights_df["Critical Path"] == "No")]
    if len(tasks_with_no_deps) >= 2:
        suggestions.append("Several non-critical tasks can run in parallel if capacity is available, creating a compression opportunity.")
    if not suggestions:
        suggestions.append("Current plan is relatively healthy; keep weekly dependency audits and owner balancing in place.")
    return suggestions


def build_ai_summary(normalized_df, insights_df, missing_dep_df, conflict_df, critical_path):
    total_tasks = len(normalized_df)
    delayed_tasks = len(insights_df[insights_df["Delay Days"] > 0])
    delayed_ratio = delayed_tasks / max(total_tasks, 1)
    score = 28 + delayed_ratio * 42 + min(len(missing_dep_df) * 6, 18) + min(len(conflict_df) * 4, 16)
    delay_probability = min(int(round(score)), 95)

    valid_timeline = normalized_df[normalized_df["Is Valid Timeline"]].copy()
    planned_end = valid_timeline["Planned End"].max() if not valid_timeline.empty else date.today()
    average_delay = int(round(insights_df["Delay Days"].mean())) if not insights_df.empty else 0
    optimized_days = max(0, average_delay - 2)
    optimized_completion = planned_end + timedelta(days=optimized_days)

    risk_level = "Low"
    if delay_probability >= 65 or len(insights_df[insights_df["Risk"] == "High"]) >= 3:
        risk_level = "High"
    elif delay_probability >= 40:
        risk_level = "Medium"

    summary = {
        "delay_probability": delay_probability,
        "optimized_completion": optimized_completion,
        "risk_level": risk_level,
        "critical_path": critical_path,
    }
    return summary


def build_scan_excel_export(summary_df, normalized_df, insights_df, resource_df, variance_df, missing_dep_df, conflict_df, skill_mismatch_df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        summary_df.to_excel(writer, index=False, sheet_name="Summary")
        normalized_df.to_excel(writer, index=False, sheet_name="Normalized Timeline")
        insights_df.to_excel(writer, index=False, sheet_name="Task Insights")
        resource_df.to_excel(writer, index=False, sheet_name="Resource Utilization")
        variance_df.to_excel(writer, index=False, sheet_name="Timeline Variance")
        missing_dep_df.to_excel(writer, index=False, sheet_name="Missing Dependencies")
        conflict_df.to_excel(writer, index=False, sheet_name="Resource Conflicts")
        skill_mismatch_df.to_excel(writer, index=False, sheet_name="Skill Mismatch")
    output.seek(0)
    return output.getvalue()


def build_scan_pdf_report(active_sheet, summary_df, suggestions, ai_summary):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, f"Project Scan Report - {active_sheet}", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Summary", ln=True)
    pdf.set_font("Helvetica", "", 9)
    for row in summary_df.to_dict(orient="records"):
        pdf.multi_cell(0, 5, f"{row['Metric']}: {row['Value']}")

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "AI Insights", ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 5, f"Delay probability: {ai_summary['delay_probability']}%")
    pdf.multi_cell(0, 5, f"Risk level: {ai_summary['risk_level']}")
    pdf.multi_cell(0, 5, f"Optimized completion date: {ai_summary['optimized_completion'].strftime('%d %b %Y')}")

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Optimization Suggestions", ln=True)
    pdf.set_font("Helvetica", "", 9)
    for index, suggestion in enumerate(suggestions[:8], start=1):
        pdf.multi_cell(0, 5, f"{index}. {suggestion}")
    return pdf.output(dest="S").encode("latin-1", errors="replace")


def render_project_scan_workspace():
    st.markdown(
        """
        <style>
        .scan-hero {
            display: grid;
            grid-template-columns: minmax(0, 1.55fr) minmax(280px, 0.95fr);
            gap: 20px;
            align-items: center;
            padding: 24px 26px;
            margin-bottom: 16px;
            background:
                radial-gradient(circle at top right, rgba(245, 158, 11, 0.12), transparent 24%),
                linear-gradient(135deg, rgba(9, 17, 38, 0.98) 0%, rgba(18, 45, 97, 0.96) 58%, rgba(31, 91, 196, 0.92) 100%);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 26px;
            box-shadow: 0 24px 54px rgba(15, 23, 42, 0.18);
            color: #ffffff;
        }
        .scan-note-card {
            background: linear-gradient(180deg, rgba(255,255,255,0.96) 0%, rgba(241,246,255,0.98) 100%);
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 20px;
            padding: 18px 20px;
            box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
        }
        .scan-note-card h4 {
            margin: 0 0 8px 0;
            color: #0f172a;
            font-size: 1.02rem;
            font-weight: 800;
        }
        .scan-note-card p {
            margin: 0;
            color: #475569;
            font-size: 0.92rem;
            line-height: 1.55;
        }
        .scan-pill {
            display: inline-flex;
            align-items: center;
            padding: 6px 10px;
            border-radius: 999px;
            margin-right: 8px;
            margin-bottom: 8px;
            background: rgba(36, 87, 214, 0.10);
            border: 1px solid rgba(36, 87, 214, 0.16);
            color: #173ea5;
            font-size: 0.78rem;
            font-weight: 700;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if "db" not in st.session_state:
        st.session_state.db = {}

    top_cols = st.columns([1.45, 0.95], gap="large")
    with top_cols[0]:
        st.markdown(
            """
            <div class="scan-hero">
                <div>
                    <div class="hero-kicker">Project Scan & Analysis</div>
                    <div class="hero-title">Portfolio Timeline Scanner</div>
                    <p class="hero-text">Upload Excel or CSV timelines, map the incoming columns, validate dependencies and resource conflicts, and generate action-oriented delivery insights in a single workspace.</p>
                    <div class="hero-meta">
                        <span class="hero-meta-chip">Excel multi-sheet support</span>
                        <span class="hero-meta-chip">Dependency validation</span>
                        <span class="hero-meta-chip">Capacity and risk analysis</span>
                    </div>
                </div>
                <div class="hero-panel">
                    <span class="hero-panel-label">How To Use</span>
                    <span class="hero-panel-title">Scan in minutes</span>
                    <p class="hero-panel-copy">Upload the source plan, confirm the column map, and review the health, workload, and optimization output. The module tolerates varied client spreadsheet formats.</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with top_cols[1]:
        st.markdown(
            """
            <div class="scan-note-card">
                <h4>File Intake</h4>
                <p>You can upload a workbook here or use the sidebar intake. Multiple sheets are supported, and each sheet can be analyzed independently.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        upload = st.file_uploader("Upload Timeline File", type=["xlsx", "csv"], label_visibility="collapsed", key="scan_workspace_uploader")
        if upload is not None:
            st.session_state.db = load_uploaded_file(upload)
            st.session_state.fn = upload.name

    if not st.session_state.db:
        st.info("Upload an Excel or CSV timeline to begin scanning and analysis.")
        return

    sheets = list(st.session_state.db.keys())
    st.sidebar.markdown(
        """
        <div class="sidebar-section-kicker">Workspace</div>
        <p class="sidebar-section-title">Active Sheet</p>
        <p class="sidebar-section-copy">Choose the uploaded sheet to analyze. Each sheet uses its own mapping and insight state.</p>
        """,
        unsafe_allow_html=True,
    )
    active_sheet = st.sidebar.selectbox("Active Sheet", sheets, label_visibility="collapsed", key="scan_active_sheet")
    raw_df = st.session_state.db[active_sheet].copy()

    if raw_df.empty:
        st.warning("The selected sheet is empty. Choose another sheet or upload a populated plan.")
        return

    mapping_state_key = f"scan_mapping_{active_sheet}"
    if mapping_state_key not in st.session_state:
        st.session_state[mapping_state_key] = build_default_mapping(raw_df)

    mapping_defaults = st.session_state[mapping_state_key]
    available_columns = [""] + list(raw_df.columns)
    mapping_labels = {
        "task_id": "Task ID",
        "task_name": "Task Name",
        "planned_start": "Planned Start",
        "planned_end": "Planned End",
        "actual_start": "Actual Start",
        "actual_end": "Actual End",
        "owner": "Owner / Resource",
        "team": "Team",
        "status": "Status",
        "dependencies": "Dependencies",
        "skill": "Skill Level",
    }

    with st.expander("Column Mapping", expanded=True):
        st.caption("Adjust the mapping if the upload uses non-standard column names.")
        mapping_cols = st.columns(3, gap="small")
        updated_mapping = {}
        ordered_keys = list(mapping_labels.keys())
        for index, key in enumerate(ordered_keys):
            default_value = mapping_defaults.get(key, "")
            if default_value not in available_columns:
                default_value = ""
            selected = mapping_cols[index % 3].selectbox(
                mapping_labels[key],
                available_columns,
                index=available_columns.index(default_value) if default_value in available_columns else 0,
                key=f"{mapping_state_key}_{key}",
            )
            updated_mapping[key] = selected or None
        st.session_state[mapping_state_key] = updated_mapping

    normalized_df = normalize_scan_df(raw_df, st.session_state[mapping_state_key])
    status_override_key = f"scan_status_overrides_{active_sheet}"
    status_overrides = st.session_state.setdefault(status_override_key, {})
    for row_index, overridden_status in status_overrides.items():
        if int(row_index) in normalized_df.index and overridden_status in SCAN_STATUS_COLORS:
            normalized_df.at[int(row_index), "Status"] = overridden_status
    if not normalized_df["Is Valid Timeline"].any():
        st.error("A usable planned start and planned end column is required for scan analysis. Update the column map and try again.")
        return

    missing_dep_df, dependent_map = analyze_dependencies(normalized_df)
    conflict_df, owner_conflicts = analyze_resource_conflicts(normalized_df)
    skill_mismatch_df = detect_skill_mismatches(normalized_df)
    critical_path = compute_critical_path(normalized_df)
    insights_df = build_task_insights(normalized_df, missing_dep_df, owner_conflicts, dependent_map, critical_path)
    resource_df = build_resource_utilization(normalized_df)
    variance_df = build_timeline_variance(normalized_df, insights_df)
    suggestions = build_optimization_suggestions(normalized_df, insights_df, resource_df, missing_dep_df, owner_conflicts)
    ai_summary = build_ai_summary(normalized_df, insights_df, missing_dep_df, conflict_df, critical_path)

    total_tasks = len(normalized_df)
    delayed_tasks = len(insights_df[insights_df["Delay Days"] > 0])
    high_risk_tasks = len(insights_df[insights_df["Risk"] == "High"])
    active_tasks = len(normalized_df[normalized_df["Status"].isin(["In Progress", "Review", "At Risk"])])

    summary_df = pd.DataFrame(
        [
            {"Metric": "File", "Value": st.session_state.get("fn", "Uploaded plan")},
            {"Metric": "Sheet", "Value": active_sheet},
            {"Metric": "Total Tasks", "Value": total_tasks},
            {"Metric": "Delayed Tasks", "Value": delayed_tasks},
            {"Metric": "High Risk Tasks", "Value": high_risk_tasks},
            {"Metric": "Delay Probability", "Value": f"{ai_summary['delay_probability']}%"},
            {"Metric": "Optimized Completion", "Value": ai_summary["optimized_completion"].strftime("%d %b %Y")},
            {"Metric": "Risk Level", "Value": ai_summary["risk_level"]},
        ]
    )

    metrics = st.columns(4, gap="small")
    metrics[0].metric("Total Tasks", total_tasks)
    metrics[1].metric("Delayed Tasks", delayed_tasks)
    metrics[2].metric("Risk Level", ai_summary["risk_level"])
    metrics[3].metric("Active Flow", active_tasks)

    overview_tab, board_tab, ai_tab = st.tabs(["Overview", "Technical Board", "AI Insights"])

    with overview_tab:
        chart_cols = st.columns(2, gap="large")
        with chart_cols[0]:
            status_summary = normalized_df.groupby("Status").size().reset_index(name="Tasks")
            status_figure = px.pie(
                status_summary,
                names="Status",
                values="Tasks",
                hole=0.58,
                color="Status",
                color_discrete_map=SCAN_STATUS_COLORS,
                title="Timeline Health by Status",
            )
            status_figure.update_layout(
                margin=dict(t=54, l=10, r=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Manrope, Segoe UI, sans-serif", color="#334155"),
                legend=dict(orientation="h", y=-0.12, x=0),
            )
            st.plotly_chart(status_figure, use_container_width=True)

        with chart_cols[1]:
            resource_figure = px.bar(
                resource_df,
                x="Owner",
                y="Utilization %",
                color="Status",
                text="Utilization %",
                color_discrete_map={
                    "Over-utilized": "#d97706",
                    "Balanced": "#2457d6",
                    "Under-utilized": "#10b981",
                },
                title="Resource Utilization",
            )
            resource_figure.update_layout(
                margin=dict(t=54, l=10, r=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Manrope, Segoe UI, sans-serif", color="#334155"),
                legend=dict(orientation="h", y=1.02, x=0),
            )
            resource_figure.update_traces(texttemplate="%{text:.0f}%", textposition="outside")
            st.plotly_chart(resource_figure, use_container_width=True)

        variance_cols = st.columns(2, gap="large")
        with variance_cols[0]:
            variance_figure = px.bar(
                variance_df,
                x="Owner",
                y="Delay Days",
                color="Delay Days",
                color_continuous_scale=["#93c5fd", "#2457d6", "#d97706"],
                title="Timeline Variance by Owner",
            )
            variance_figure.update_layout(
                margin=dict(t=54, l=10, r=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Manrope, Segoe UI, sans-serif", color="#334155"),
                coloraxis_showscale=False,
            )
            st.plotly_chart(variance_figure, use_container_width=True)

        with variance_cols[1]:
            timeline_df = normalized_df[normalized_df["Is Valid Timeline"]].copy()
            timeline_df["Bar Label"] = timeline_df["Task Name"]
            timeline_fig = px.timeline(
                timeline_df,
                x_start="Planned Start",
                x_end="Planned End",
                y="Bar Label",
                color="Status",
                color_discrete_map=SCAN_STATUS_COLORS,
                title="Planned Timeline View",
                hover_data={"Owner": True, "Team": True, "Dependencies": True},
            )
            timeline_fig.update_yaxes(autorange="reversed")
            timeline_fig.update_layout(
                margin=dict(t=54, l=10, r=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Manrope, Segoe UI, sans-serif", color="#334155"),
                legend=dict(orientation="h", y=1.02, x=0),
            )
            st.plotly_chart(timeline_fig, use_container_width=True)

        info_cols = st.columns([1.1, 1.1, 1.2], gap="small")
        info_cols[0].markdown(
            f"""
            <div class="scan-note-card">
                <h4>Validation</h4>
                <p>{len(missing_dep_df)} missing dependency references, {len(conflict_df)} owner overlap conflicts, and {len(skill_mismatch_df)} skill mismatch signals were detected.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        info_cols[1].markdown(
            f"""
            <div class="scan-note-card">
                <h4>Critical Path</h4>
                <p>{" → ".join(critical_path) if critical_path else "No dependency chain detected from the uploaded data."}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        info_cols[2].markdown(
            f"""
            <div class="scan-note-card">
                <h4>Optimization Focus</h4>
                <p>{suggestions[0]}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### Task-Level Insights")
        st.dataframe(
            insights_df,
            use_container_width=True,
            hide_index=True,
            height=min(560, 90 + len(insights_df) * 35),
        )

        detail_tabs = st.tabs(["Missing Dependencies", "Resource Conflicts", "Skill Mismatch"])
        detail_tabs[0].dataframe(missing_dep_df if not missing_dep_df.empty else pd.DataFrame({"Info": ["No missing dependencies found."]}), use_container_width=True, hide_index=True)
        detail_tabs[1].dataframe(conflict_df if not conflict_df.empty else pd.DataFrame({"Info": ["No overlapping resource conflicts found."]}), use_container_width=True, hide_index=True)
        detail_tabs[2].dataframe(skill_mismatch_df if not skill_mismatch_df.empty else pd.DataFrame({"Info": ["No skill mismatch signals found or skill data was not provided."]}), use_container_width=True, hide_index=True)

    with board_tab:
        board_items = []
        status_source = normalized_df.copy()
        for index, row in status_source.iterrows():
            board_items.append(
                {
                    "row_id": index,
                    "task_id": row["Task ID"],
                    "task_name": row["Task Name"],
                    "owner": row["Owner"],
                    "stage": row["Status"] if row["Status"] in ["To Do", "In Progress", "Review", "Done"] else "Review",
                }
            )
        st.markdown(
            "<div class='roadmap-section-copy'>Use the drag-and-drop board to review operational flow after the scan. This board is an interactive triage layer derived from the uploaded timeline.</div>",
            unsafe_allow_html=True,
        )
        stages = ["To Do", "In Progress", "Review", "Done"]
        move_event = render_kanban_board(board_items, stages, key=f"scan_kanban_{active_sheet}", height=820)
        if move_event and move_event.get("event_id") != st.session_state.get("scan_last_move"):
            row_id = move_event.get("row_id")
            to_stage = move_event.get("to_stage")
            if row_id is not None and to_stage in stages:
                status_overrides[str(int(row_id))] = to_stage
                st.session_state[status_override_key] = status_overrides
                st.session_state["scan_last_move"] = move_event.get("event_id")
                st.rerun()

        st.subheader("Normalized Timeline Data")
        st.dataframe(normalized_df.drop(columns=["Raw Status"]), use_container_width=True, hide_index=True)

    with ai_tab:
        st.markdown(
            f"""
            <div class="workspace-detail-card">
                <h4>AI Delivery Insight</h4>
                <p><b>{active_sheet}</b> contains <b>{total_tasks}</b> tasks with <b>{delayed_tasks}</b> delayed items and an estimated <b>{ai_summary['delay_probability']}%</b> chance of schedule slippage if the current plan remains unchanged.</p>
                <p><b>Optimized completion date:</b> {ai_summary['optimized_completion'].strftime("%d %b %Y")}</p>
                <div class="detail-chip-row">
                    <span class="scan-pill">{high_risk_tasks} high-risk tasks</span>
                    <span class="scan-pill">{len(missing_dep_df)} dependency gaps</span>
                    <span class="scan-pill">{len(conflict_df)} owner overlaps</span>
                    <span class="scan-pill">Risk level: {ai_summary['risk_level']}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div class="workspace-detail-card" style="margin-top:16px;">
                <h4>Optimization Suggestions</h4>
                <ul>{"".join(f"<li>{item}</li>" for item in suggestions)}</ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

        prompt = st.chat_input("Ask for delay probability, bottlenecks, or reallocation suggestions...")
        if prompt:
            st.markdown(
                f"""
                <div class="workspace-detail-card" style="margin-top:16px;">
                    <h4>AI Response</h4>
                    <p><b>Request:</b> {prompt}</p>
                    <p>The current scan indicates <b>{delayed_tasks}</b> delayed tasks, <b>{len(conflict_df)}</b> owner conflicts, and a <b>{ai_summary['risk_level']}</b> overall risk profile. The strongest immediate action is to protect the critical path <b>{" → ".join(critical_path) if critical_path else 'tasks with active delays'}</b> and rebalance work away from over-utilized owners before new items are pulled into execution.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    excel_bytes = build_scan_excel_export(summary_df, normalized_df, insights_df, resource_df, variance_df, missing_dep_df, conflict_df, skill_mismatch_df)
    pdf_bytes = build_scan_pdf_report(active_sheet, summary_df, suggestions, ai_summary)
    export_cols = st.columns([1, 1, 4], gap="small")
    export_cols[0].download_button(
        "Export Excel",
        data=excel_bytes,
        file_name=f"{active_sheet.lower().replace(' ', '_')}_scan_analysis.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        use_container_width=True,
    )
    export_cols[1].download_button(
        "Export PDF",
        data=pdf_bytes,
        file_name=f"{active_sheet.lower().replace(' ', '_')}_scan_summary.pdf",
        mime="application/pdf",
        type="secondary",
        use_container_width=True,
    )
