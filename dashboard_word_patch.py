import math
from datetime import date

import pandas as pd
import streamlit as st

from word_export import build_word_report


def _roadmap_word_button():
    project_name = st.session_state.get("roadmap_project_name") or "Enterprise Project Roadmap"
    project_description = st.session_state.get("roadmap_project_description") or "Roadmap review export generated from the live dashboard."
    duration = st.session_state.get("roadmap_duration_days", 0)
    start_date = st.session_state.get("roadmap_start_date")
    team_df = pd.DataFrame(st.session_state.get("roadmap_team_df", []))
    module_df = pd.DataFrame(st.session_state.get("roadmap_module_df", []))
    task_df = pd.DataFrame(st.session_state.get("roadmap_task_df", []))

    if hasattr(start_date, "strftime"):
        start_text = start_date.strftime("%d %b %Y")
    else:
        start_text = str(start_date or "Not set")

    sections = [
        {
            "heading": "Dashboard Review Summary",
            "paragraphs": [
                project_description,
                f"Planned working duration: {duration} day(s)",
                f"Project start date: {start_text}",
            ],
        },
        {
            "heading": "Current Planning Snapshot",
            "bullets": [
                f"Teams configured: {len(team_df)}",
                f"Modules configured: {len(module_df)}",
                f"Tasks configured: {len(task_df)}",
            ],
        },
    ]

    if not team_df.empty:
        sections.append(
            {
                "heading": "Team Allocation Review",
                "bullets": [
                    f"{row['Team']}: {row['Resources']} resource(s), {row.get('Allocation %', 100)}% allocation, skill {row['Skill Level']}"
                    for row in team_df.head(10).to_dict(orient="records")
                ],
            }
        )

    if not task_df.empty:
        sections.append(
            {
                "heading": "Key Task Review",
                "bullets": [
                    f"{row['Task Name']} | {row['Phase']} | {row['Team Responsible']} | {row['Effort Days']} day(s)"
                    for row in task_df.head(12).to_dict(orient="records")
                ],
            }
        )

    sections.append(
        {
            "heading": "Incremental Feature Backlog",
            "bullets": [
                "Add baseline-versus-current comparison across roadmap versions.",
                "Introduce approver sign-off for scope, staffing, and date changes.",
                "Add scenario planning for optimistic, likely, and constrained delivery paths.",
                "Add cross-project dependency views for PMO-level portfolio reviews.",
            ],
        }
    )

    word_bytes = build_word_report(
        project_name,
        sections,
        subtitle="Review-ready summary generated from the roadmap dashboard",
    )
    st.download_button(
        "Review Word Doc",
        data=word_bytes,
        file_name=f"{project_name.lower().replace(' ', '_')}_review.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        type="tertiary",
        use_container_width=False,
        key="roadmap_review_word_doc",
    )


def _scan_word_button(project_scan_workspace):
    db = st.session_state.get("db", {})
    if not db:
        return

    active_sheet = st.session_state.get("scan_active_sheet") or next(iter(db.keys()))
    if active_sheet not in db:
        return

    raw_df = db[active_sheet]
    mapping_key = f"scan_mapping_{active_sheet}"
    mapping = st.session_state.get(mapping_key) or project_scan_workspace.build_default_mapping(raw_df)
    normalized_df = project_scan_workspace.normalize_scan_df(raw_df, mapping)
    override_key = f"scan_status_overrides_{active_sheet}"
    overrides = st.session_state.get(override_key, {})
    for row_index, overridden_status in overrides.items():
        try:
            if int(row_index) in normalized_df.index:
                normalized_df.at[int(row_index), "Status"] = overridden_status
        except ValueError:
            continue

    missing_dep_df, dependent_map = project_scan_workspace.analyze_dependencies(normalized_df)
    conflict_df, owner_conflicts = project_scan_workspace.analyze_resource_conflicts(normalized_df)
    critical_path = project_scan_workspace.compute_critical_path(normalized_df)
    insights_df = project_scan_workspace.build_task_insights(normalized_df, missing_dep_df, owner_conflicts, dependent_map, critical_path)
    resource_df = project_scan_workspace.build_resource_utilization(normalized_df)
    suggestions = project_scan_workspace.build_optimization_suggestions(normalized_df, insights_df, resource_df, missing_dep_df, owner_conflicts)
    ai_summary = project_scan_workspace.build_ai_summary(normalized_df, insights_df, missing_dep_df, conflict_df, critical_path)

    total_tasks = len(normalized_df)
    delayed_tasks = len(insights_df[insights_df["Delay Days"] > 0])
    high_risk_tasks = len(insights_df[insights_df["Risk"] == "High"])

    sections = [
        {
            "heading": "Dashboard Review Summary",
            "paragraphs": [
                f"Active sheet: {active_sheet}",
                f"Total tasks: {total_tasks}",
                f"Delayed tasks: {delayed_tasks}",
                f"High-risk tasks: {high_risk_tasks}",
                f"Delay probability: {ai_summary['delay_probability']}%",
                f"Optimized completion date: {ai_summary['optimized_completion'].strftime('%d %b %Y')}",
            ],
        },
        {
            "heading": "Key Findings",
            "bullets": [
                f"Missing dependency references: {len(missing_dep_df)}",
                f"Resource conflicts: {len(conflict_df)}",
                f"Critical path length: {len(critical_path)} task(s)",
                f"Risk level: {ai_summary['risk_level']}",
            ],
        },
    ]

    if not resource_df.empty:
        sections.append(
            {
                "heading": "Resource Review",
                "bullets": [
                    f"{row['Owner']}: {row['Utilization %']}% utilization, status {row['Status']}"
                    for row in resource_df.head(10).to_dict(orient="records")
                ],
            }
        )

    if not insights_df.empty:
        sections.append(
            {
                "heading": "Task Review Highlights",
                "bullets": [
                    f"{row['Task Name']} | Risk {row['Risk']} | Delay {row['Delay Days']} day(s) | {row['Recommendation']}"
                    for row in insights_df.head(12).to_dict(orient="records")
                ],
            }
        )

    sections.append(
        {
            "heading": "Incremental Feature Backlog",
            "bullets": [
                "Add baseline-versus-actual trend history across repeated scans.",
                "Introduce saved mapping templates for recurring client file formats.",
                "Add what-if reallocation simulation before accepting optimization actions.",
                "Add direct sync to Jira, Monday.com, or ServiceNow issue sources.",
            ],
        }
    )

    word_bytes = build_word_report(
        f"{active_sheet} Scan Review",
        sections,
        subtitle="Review-ready summary generated from the project scan dashboard",
    )
    st.download_button(
        "Review Word Doc",
        data=word_bytes,
        file_name=f"{active_sheet.lower().replace(' ', '_')}_review.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        type="tertiary",
        use_container_width=False,
        key=f"scan_review_word_doc_{active_sheet}",
    )


def patch_modules():
    import project_scan_workspace
    import roadmap_workspace

    if not getattr(roadmap_workspace, "_word_patch_applied", False):
        original_roadmap_render = roadmap_workspace.render_roadmap_workspace

        def wrapped_roadmap_render():
            original_roadmap_render()
            _roadmap_word_button()

        roadmap_workspace.render_roadmap_workspace = wrapped_roadmap_render
        roadmap_workspace._word_patch_applied = True

    if not getattr(project_scan_workspace, "_word_patch_applied", False):
        original_scan_render = project_scan_workspace.render_project_scan_workspace

        def wrapped_scan_render():
            original_scan_render()
            _scan_word_button(project_scan_workspace)

        project_scan_workspace.render_project_scan_workspace = wrapped_scan_render
        project_scan_workspace._word_patch_applied = True
