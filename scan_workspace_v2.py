from io import BytesIO
import textwrap

import pandas as pd
import plotly.express as px
import streamlit as st

from kanban_dnd_component import render_kanban_board
from project_scan_workspace import (
    SCAN_STATUS_COLORS,
    analyze_dependencies,
    analyze_resource_conflicts,
    build_ai_summary,
    build_default_mapping,
    build_optimization_suggestions,
    build_scan_excel_export,
    build_task_insights,
    build_timeline_variance,
    compute_critical_path,
    detect_skill_mismatches,
    load_uploaded_file,
    normalize_date,
    normalize_scan_df,
)
from word_export import build_word_report


KANBAN_STAGES = ["To Do", "In Progress", "Review", "Done"]


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
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _column_signature(df):
    return "|".join(str(column).strip().lower() for column in df.columns)


def _date_candidate_score(series, column_name):
    name = str(column_name).strip().lower()
    name_hint = any(token in name for token in ["date", "start", "end", "due", "eta", "deadline"])
    start_hint = any(token in name for token in ["start", "begin", "kickoff"])
    end_hint = any(token in name for token in ["end", "due", "finish", "close"])

    if pd.api.types.is_datetime64_any_dtype(series):
        parsed = pd.to_datetime(series, errors="coerce")
    elif pd.api.types.is_numeric_dtype(series):
        if not name_hint:
            return None
        parsed = pd.to_datetime(series, unit="D", origin="1899-12-30", errors="coerce")
    else:
        parsed = pd.to_datetime(series, errors="coerce")

    valid = parsed.dropna()
    if valid.empty:
        return None
    valid = valid[(valid.dt.year >= 2000) & (valid.dt.year <= 2100)]
    if valid.empty:
        return None

    ratio = len(valid) / max(len(series), 1)
    if ratio < 0.45 and not name_hint:
        return None

    score = ratio
    if name_hint:
        score += 0.35
    if start_hint:
        score += 0.2
    if end_hint:
        score += 0.2

    return {
        "column": column_name,
        "score": score,
        "start_hint": start_hint,
        "end_hint": end_hint,
    }


def _find_date_candidates(raw_df):
    candidates = []
    for column in raw_df.columns:
        result = _date_candidate_score(raw_df[column], column)
        if result is not None:
            candidates.append(result)
    return sorted(candidates, key=lambda item: item["score"], reverse=True)


def _best_date_column(candidates, role):
    if role == "start":
        start_candidates = [item for item in candidates if item["start_hint"]]
        if start_candidates:
            return start_candidates[0]["column"]
    if role == "end":
        end_candidates = [item for item in candidates if item["end_hint"]]
        if end_candidates:
            return end_candidates[0]["column"]
    return candidates[0]["column"] if candidates else None


def _enhance_mapping(raw_df, mapping):
    mapping = dict(mapping)
    date_candidates = _find_date_candidates(raw_df)
    valid_date_columns = {item["column"] for item in date_candidates}
    best_start = _best_date_column(date_candidates, "start")
    best_end = _best_date_column(date_candidates, "end")

    if not mapping.get("planned_start") or mapping.get("planned_start") not in valid_date_columns:
        mapping["planned_start"] = best_start
    if not mapping.get("planned_end") or mapping.get("planned_end") not in valid_date_columns:
        mapping["planned_end"] = best_end or best_start
    return mapping


def _normalize_with_fallback(raw_df, mapping):
    enhanced_mapping = _enhance_mapping(raw_df, mapping)
    normalized_df = normalize_scan_df(raw_df, enhanced_mapping)
    if normalized_df["Is Valid Timeline"].any():
        return normalized_df, enhanced_mapping

    duration_column = next((column for column in raw_df.columns if "duration" in str(column).lower() or "effort" in str(column).lower()), None)
    if duration_column and enhanced_mapping.get("planned_start"):
        working_df = raw_df.copy()
        start_series = pd.to_datetime(working_df[enhanced_mapping["planned_start"]], errors="coerce")
        duration_series = pd.to_numeric(working_df[duration_column], errors="coerce").fillna(1).clip(lower=1)
        synthetic_end = start_series + pd.to_timedelta(duration_series - 1, unit="D")
        temp_column = "__synthetic_planned_end__"
        working_df[temp_column] = synthetic_end
        enhanced_mapping["planned_end"] = temp_column
        normalized_df = normalize_scan_df(working_df, enhanced_mapping)
    return normalized_df, enhanced_mapping


def _prepare_board_state(sheet_key, normalized_df):
    state_key = f"scan_board_state_{sheet_key}"
    signature_key = f"scan_board_signature_{sheet_key}"
    signature = f"{len(normalized_df)}|{normalized_df['Task ID'].astype(str).str.cat(sep='|')}"
    if st.session_state.get(signature_key) != signature:
        st.session_state[signature_key] = signature
        st.session_state[state_key] = normalized_df.copy()
        st.session_state.setdefault(f"scan_undo_{sheet_key}", [])
        st.session_state.setdefault(f"scan_redo_{sheet_key}", [])
        st.session_state[f"scan_undo_{sheet_key}"].clear()
        st.session_state[f"scan_redo_{sheet_key}"].clear()
    return state_key


def _apply_status_overrides(board_df, normalized_df):
    merged_df = normalized_df.copy()
    if "Status" in board_df.columns:
        merged_df["Status"] = board_df["Status"].values
    return merged_df


def _build_resource_utilization_v2(board_df):
    if board_df.empty:
        return pd.DataFrame(columns=["Owner", "Task Count", "Assigned Days", "Schedule Span", "Utilization %", "Status"])

    util_df = board_df.copy()
    util_df["Owner"] = util_df["Owner"].fillna("Unassigned").replace("", "Unassigned")
    start_series = pd.to_datetime(util_df["Planned Start"], errors="coerce")
    end_series = pd.to_datetime(util_df["Planned End"], errors="coerce")
    durations = (end_series - start_series).dt.days.add(1)
    durations = durations.where(durations.between(1, 180), 1).fillna(1)
    util_df["Assigned Days"] = durations.astype(int)

    valid_starts = start_series.dropna()
    valid_ends = end_series.dropna()
    if not valid_starts.empty and not valid_ends.empty:
        schedule_span = int(max((valid_ends.max() - valid_starts.min()).days + 1, 1))
    else:
        schedule_span = int(max(min(util_df["Assigned Days"].sum(), 60), 1))

    status_weight = {"To Do": 0.35, "In Progress": 1.0, "Review": 0.85, "Done": 0.2}
    util_df["Weighted Load"] = util_df["Assigned Days"] * util_df["Status"].map(status_weight).fillna(0.5)

    grouped = (
        util_df.groupby("Owner", dropna=False)
        .agg(
            **{
                "Task Count": ("Task ID", "count"),
                "Assigned Days": ("Assigned Days", "sum"),
                "Weighted Load": ("Weighted Load", "sum"),
            }
        )
        .reset_index()
    )
    grouped["Schedule Span"] = schedule_span
    grouped["Utilization %"] = ((grouped["Weighted Load"] / grouped["Schedule Span"]) * 100).round(1).clip(lower=0, upper=200)
    grouped["Status"] = grouped["Utilization %"].apply(
        lambda value: "Over-utilized" if value > 100 else ("Under-utilized" if value < 40 else "Balanced")
    )
    return grouped[["Owner", "Task Count", "Assigned Days", "Schedule Span", "Utilization %", "Status"]].sort_values(
        ["Utilization %", "Task Count", "Owner"], ascending=[False, False, True]
    )


def _board_header_cards(status_df):
    total = max(len(status_df), 1)
    status_counts = status_df.groupby("Status").size().to_dict()
    card_cols = st.columns(4, gap="small")
    for column, stage in zip(card_cols, KANBAN_STAGES):
        count = int(status_counts.get(stage, 0))
        pct = int(round((count / total) * 100))
        column.markdown(
            f"""
            <div class="roadmap-metric-card">
                <div class="roadmap-metric-label">{stage}</div>
                <div class="roadmap-metric-value">{pct}%</div>
                <div class="roadmap-metric-note">{count} task(s)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _build_review_word(active_sheet, insights_df, resource_df, ai_summary, suggestions):
    sections = [
        {
            "heading": "Dashboard Review Summary",
            "bullets": [
                f"Project: {active_sheet}",
                f"Tasks analysed: {len(insights_df)}",
                f"High-risk tasks: {len(insights_df[insights_df['Risk'] == 'High'])}",
                f"Delay probability: {ai_summary['delay_probability']}%",
                f"Optimized completion date: {ai_summary['optimized_completion'].strftime('%d %b %Y')}",
            ],
        },
        {
            "heading": "Resource Review",
            "bullets": [
                f"{row['Owner']}: {row['Utilization %']}% utilization ({row['Status']})"
                for row in resource_df.head(8).to_dict(orient="records")
            ],
        },
        {
            "heading": "Incremental Feature Backlog",
            "bullets": [
                "Add auto-saved mappings for recurring vendor timeline formats.",
                "Add cross-project dependency mapping across all uploaded sheets.",
                "Add one-click scenario simulation for reallocation and compression.",
                "Add direct issue synchronization to Jira, Monday.com, and ServiceNow.",
            ]
            + suggestions[:3],
        },
    ]
    return build_word_report(
        f"{active_sheet} Dashboard Review",
        sections,
        subtitle="Review-ready summary generated from the scan dashboard",
    )


def _pdf_safe_text(value, limit=120):
    text = str(value or "").replace("\r", " ").replace("\n", " ").strip()
    text = " ".join(text.split())
    if len(text) > limit:
        text = f"{text[: limit - 3]}..."
    return text or "-"


def _build_safe_scan_pdf_report(active_sheet, total_tasks, ai_summary, suggestions):
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
                safe_line = _pdf_safe_text(line, limit=140)
                wrapped = textwrap.wrap(safe_line, width=90, break_long_words=True, break_on_hyphens=True) or ["-"]
                for chunk in wrapped:
                    pdf.cell(width, 7, chunk, new_x="LMARGIN", new_y="NEXT")

        write_lines([f"{active_sheet} Dashboard Review"], font_style="B", font_size=16)
        pdf.ln(2)
        write_lines(
            [
                f"Total Tasks: {total_tasks}",
                f"Risk Level: {ai_summary['risk_level']}",
                f"Delay Probability: {ai_summary['delay_probability']}%",
                f"Optimized Completion: {ai_summary['optimized_completion'].strftime('%d %b %Y')}",
            ]
        )
        pdf.ln(2)
        write_lines(["Recommendations"], font_style="B", font_size=13)
        write_lines([f"- {item}" for item in suggestions[:8]])
        return bytes(pdf.output(dest="S"))
    except Exception:
        return b"%PDF-1.4\n%PMO fallback PDF export unavailable\n"


def render_scan_workspace_v2():
    _inject_enterprise_ui_styles()

    st.markdown(
        """
        <style>
        .scan-toolbar-note {
            color: #475569;
            font-size: 0.9rem;
            margin-bottom: 0.65rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if "db" not in st.session_state:
        st.session_state.db = {}

    upload = st.file_uploader("Upload Timeline File", type=["xlsx", "csv"], label_visibility="collapsed", key="scan_v2_uploader")
    if upload is not None:
        st.session_state.db = load_uploaded_file(upload)
        st.session_state.fn = upload.name

    if not st.session_state.db:
        st.markdown(
            """
            <div class="app-hero">
                <div class="hero-main">
                    <div class="hero-kicker">Scan Project</div>
                    <div class="hero-title">Unified Project Scanner</div>
                    <p class="hero-text">Upload multi-sheet Excel or CSV files from different project sources and the scanner will infer structure, normalize the data, and generate delivery insights without forcing you to remap every time.</p>
                </div>
                <div class="hero-panel">
                    <span class="hero-panel-label">Input</span>
                    <span class="hero-panel-title">Timeline File</span>
                    <p class="hero-panel-copy">Supports multiple sheets and dynamic project switching once the workbook is loaded.</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.info("Upload an Excel or CSV file to start the scan analysis.")
        return

    sheets = list(st.session_state.db.keys())
    portfolio_summary = []
    for sheet_name, frame in st.session_state.db.items():
        portfolio_summary.append({"Project": sheet_name, "Rows": len(frame), "Columns": len(frame.columns)})
    st.sidebar.markdown(
        """
        <div class="sidebar-section-kicker">Portfolio</div>
        <p class="sidebar-section-title">Project Selector</p>
        <p class="sidebar-section-copy">Move across uploaded project sheets and keep the dashboard context dynamic.</p>
        """,
        unsafe_allow_html=True,
    )
    active_sheet = st.sidebar.selectbox("Project", sheets, label_visibility="collapsed", key="scan_v2_project")
    raw_df = st.session_state.db[active_sheet].copy()

    signature = _column_signature(raw_df)
    mapping_cache = st.session_state.setdefault("scan_mapping_cache", {})
    mapping = mapping_cache.get(signature, build_default_mapping(raw_df))
    normalized_df, applied_mapping = _normalize_with_fallback(raw_df, mapping)
    mapping_cache[signature] = applied_mapping
    st.session_state["scan_mapping_cache"] = mapping_cache

    if not normalized_df["Is Valid Timeline"].any():
        st.warning("The scanner did not find fully reliable date columns, so it created a best-effort view. Open advanced mapping only if the inferred result needs tuning.")

    show_mapping = not normalized_df["Is Valid Timeline"].any() or st.toggle(
        "Show advanced column mapping",
        value=False,
        key=f"scan_v2_show_mapping_{active_sheet}",
        help="Optional. The scanner auto-detects most formats, so this is only for correction when a source file is unusual.",
    )
    if show_mapping:
        with st.expander("Advanced Column Mapping (Optional)", expanded=not normalized_df["Is Valid Timeline"].any()):
            st.caption("The scanner remembers format signatures automatically. Most uploads should not need this.")
            available_columns = [""] + list(raw_df.columns)
            mapping_cols = st.columns(3, gap="small")
            field_labels = {
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
            adjusted_mapping = {}
            for idx, (field, label) in enumerate(field_labels.items()):
                current_value = applied_mapping.get(field) or ""
                if current_value not in available_columns:
                    current_value = ""
                selected = mapping_cols[idx % 3].selectbox(
                    label,
                    available_columns,
                    index=available_columns.index(current_value) if current_value in available_columns else 0,
                    key=f"scan_v2_mapping_{active_sheet}_{field}",
                )
                adjusted_mapping[field] = selected or None
            if st.button("Apply Mapping", key=f"scan_v2_apply_{active_sheet}", type="secondary"):
                mapping_cache[signature] = adjusted_mapping
                st.session_state["scan_mapping_cache"] = mapping_cache
                st.rerun()

    normalized_df = normalized_df.reset_index(drop=True)
    normalized_df["Row ID"] = normalized_df.index.astype(int)
    state_key = _prepare_board_state(active_sheet, normalized_df)
    board_df = pd.DataFrame(st.session_state[state_key]).copy()
    board_df = _apply_status_overrides(board_df, normalized_df)
    board_df["Row ID"] = board_df["Row ID"].astype(int)
    st.session_state[state_key] = board_df

    total_tasks = len(board_df)
    delayed_proxy = int((board_df["Status"].isin(["Review", "At Risk"])).sum())
    in_flow = int((board_df["Status"].isin(["In Progress", "Review", "At Risk"])).sum())

    st.markdown(
        f"""
        <div class="app-hero">
            <div class="hero-main">
                <div class="hero-kicker">Scan Project</div>
                <div class="hero-title">Project Intelligence Hub</div>
                <p class="hero-text"><b>{active_sheet}</b> was loaded from <b>{st.session_state.get('fn', 'uploaded file')}</b> with <b>{total_tasks}</b> normalized tasks. The scanner caches the column pattern for this format and keeps the Kanban, management, and AI views aligned as you update task status.</p>
                <div class="hero-meta">
                    <span class="hero-meta-chip">{len(sheets)} project sheet(s)</span>
                    <span class="hero-meta-chip">{total_tasks} normalized tasks</span>
                    <span class="hero-meta-chip">{in_flow} active flow items</span>
                    <span class="hero-meta-chip">{delayed_proxy} items need attention</span>
                </div>
            </div>
            <div class="hero-panel">
                <span class="hero-panel-label">Portfolio View</span>
                <span class="hero-panel-title">{active_sheet}</span>
                <p class="hero-panel-copy">Switch projects from the sidebar to inspect individual sheets while preserving the full uploaded workbook as a portfolio source.</p>
                <div class="hero-panel-grid">
                    <div class="hero-panel-item"><span class="hero-panel-value">{len(sheets)}</span><span class="hero-panel-caption">Projects</span></div>
                    <div class="hero-panel-item"><span class="hero-panel-value">{total_tasks}</span><span class="hero-panel-caption">Tasks</span></div>
                    <div class="hero-panel-item"><span class="hero-panel-value">{in_flow}</span><span class="hero-panel-caption">In Flow</span></div>
                    <div class="hero-panel-item"><span class="hero-panel-value">{delayed_proxy}</span><span class="hero-panel-caption">Attention</span></div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    missing_dep_df, dependent_map = analyze_dependencies(board_df)
    conflict_df, owner_conflicts = analyze_resource_conflicts(board_df)
    skill_mismatch_df = detect_skill_mismatches(board_df)
    critical_path = compute_critical_path(board_df)
    insights_df = build_task_insights(board_df, missing_dep_df, owner_conflicts, dependent_map, critical_path)
    resource_df = _build_resource_utilization_v2(board_df)
    variance_df = build_timeline_variance(board_df, insights_df)
    suggestions = build_optimization_suggestions(board_df, insights_df, resource_df, missing_dep_df, owner_conflicts)
    ai_summary = build_ai_summary(board_df, insights_df, missing_dep_df, conflict_df, critical_path)

    summary_cards = st.columns(4, gap="small")
    summary_cards[0].metric("Total Tasks", total_tasks)
    summary_cards[1].metric("Delayed Tasks", len(insights_df[insights_df["Delay Days"] > 0]))
    summary_cards[2].metric("Risk Level", ai_summary["risk_level"])
    summary_cards[3].metric("Delay Probability", f"{ai_summary['delay_probability']}%")

    tab_tech, tab_mgmt, tab_ai = st.tabs(["Technical Kanban", "Management View", "AI Consultant"])

    with tab_tech:
        _board_header_cards(board_df)
        undo_key = f"scan_v2_undo_{active_sheet}"
        redo_key = f"scan_v2_redo_{active_sheet}"
        saved_key = f"scan_v2_saved_{active_sheet}"
        st.session_state.setdefault(undo_key, [])
        st.session_state.setdefault(redo_key, [])
        st.session_state.setdefault(saved_key, [])

        toolbar = st.columns([1, 1, 1.2, 1.2, 4], gap="small")
        if toolbar[0].button("↶ Undo", use_container_width=True, disabled=not st.session_state[undo_key], key=f"scan_v2_undo_btn_{active_sheet}"):
            st.session_state[redo_key].append(board_df.copy())
            board_df = st.session_state[undo_key].pop()
            st.session_state[state_key] = board_df
            st.rerun()
        if toolbar[1].button("↷ Redo", use_container_width=True, disabled=not st.session_state[redo_key], key=f"scan_v2_redo_btn_{active_sheet}"):
            st.session_state[undo_key].append(board_df.copy())
            board_df = st.session_state[redo_key].pop()
            st.session_state[state_key] = board_df
            st.rerun()
        if toolbar[2].button("✦ Save View", use_container_width=True, key=f"scan_v2_save_btn_{active_sheet}", type="primary"):
            st.session_state[saved_key].append(board_df.copy())
            st.success("Current dashboard view saved.")

        export_excel = build_scan_excel_export(
            pd.DataFrame(
                [
                    {"Metric": "Project", "Value": active_sheet},
                    {"Metric": "Total Tasks", "Value": total_tasks},
                    {"Metric": "Risk Level", "Value": ai_summary["risk_level"]},
                ]
            ),
            board_df,
            insights_df,
            resource_df,
            variance_df,
            missing_dep_df,
            conflict_df,
            skill_mismatch_df,
        )
        toolbar[3].download_button(
            "📊 Extract Excel",
            data=export_excel,
            file_name=f"{active_sheet.lower().replace(' ', '_')}_dashboard.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="secondary",
            key=f"scan_v2_extract_{active_sheet}",
        )

        board_items = [
            {
                "row_id": int(row["Row ID"]),
                "task_id": row["Task ID"],
                "task_name": row["Task Name"],
                "owner": row["Owner"],
                "stage": row["Status"] if row["Status"] in KANBAN_STAGES else "Review",
            }
            for row in board_df.to_dict(orient="records")
        ]
        move_event = render_kanban_board(board_items, KANBAN_STAGES, key=f"scan_v2_kanban_{active_sheet}", height=860)
        if move_event and move_event.get("event_id") != st.session_state.get(f"scan_v2_move_event_{active_sheet}"):
            row_id = move_event.get("row_id")
            to_stage = move_event.get("to_stage")
            if row_id is not None and to_stage in KANBAN_STAGES:
                st.session_state[undo_key].append(board_df.copy())
                st.session_state[redo_key].clear()
                board_df.loc[board_df["Row ID"] == int(row_id), "Status"] = to_stage
                st.session_state[state_key] = board_df
                st.session_state[f"scan_v2_move_event_{active_sheet}"] = move_event.get("event_id")
                st.rerun()

        st.markdown("### Dynamic Task Table")
        st.dataframe(
            board_df[["Task ID", "Task Name", "Owner", "Team", "Planned Start", "Planned End", "Status", "Dependencies"]],
            use_container_width=True,
            hide_index=True,
            height=360,
        )

    with tab_mgmt:
        status_summary = board_df.groupby("Status").size().reset_index(name="Tasks")
        mgmt_cols = st.columns(4, gap="small")
        mgmt_cols[0].metric("Portfolio Completion", f"{int((len(board_df[board_df['Status'] == 'Done']) / max(len(board_df), 1)) * 100)}%")
        mgmt_cols[1].metric("Active Flow", int((board_df["Status"].isin(["In Progress", "Review", "At Risk"])).sum()))
        mgmt_cols[2].metric("High Risk Tasks", len(insights_df[insights_df["Risk"] == "High"]))
        mgmt_cols[3].metric("Projects Loaded", len(sheets))

        chart_cols = st.columns(2, gap="large")
        with chart_cols[0]:
            fig_pie = px.pie(
                status_summary,
                names="Status",
                values="Tasks",
                hole=0.62,
                color="Status",
                color_discrete_map=SCAN_STATUS_COLORS,
                title="Project Portfolio Status",
            )
            fig_pie.update_layout(margin=dict(t=52, l=10, r=10, b=10), paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_pie, use_container_width=True)
        with chart_cols[1]:
            sunburst_df = board_df.copy()
            sunburst_df["Records"] = 1
            fig_sunburst = px.sunburst(
                sunburst_df,
                path=["Status", "Team", "Owner"],
                values="Records",
                color="Status",
                color_discrete_map=SCAN_STATUS_COLORS,
                title="Status to Owner Deep Dive",
            )
            fig_sunburst.update_traces(
                marker=dict(line=dict(color="#ffffff", width=2)),
                hovertemplate="<b>%{label}</b><br>Parent: %{parent}<br>Tasks: %{value}<extra></extra>",
            )
            fig_sunburst.update_layout(margin=dict(t=52, l=10, r=10, b=10), paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_sunburst, use_container_width=True)

        util_cols = st.columns([1.1, 1], gap="large")
        with util_cols[0]:
            fig_util = px.bar(
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
                title="Resource Utilisation",
            )
            fig_util.update_traces(texttemplate="%{text:.0f}%", textposition="outside")
            fig_util.update_layout(margin=dict(t=52, l=10, r=10, b=10), paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_util, use_container_width=True)
        with util_cols[1]:
            mitigation_html = "".join(f"<li>{item}</li>" for item in suggestions[:5])
            st.markdown(
                f"""
                <div class="workspace-detail-card">
                    <h4>Mitigation</h4>
                    <ul>{mitigation_html}</ul>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("### Resource Utilisation Table")
        st.dataframe(resource_df, use_container_width=True, hide_index=True, height=320)
        st.markdown("### Portfolio Status Table")
        st.dataframe(
            board_df[
                ["Task ID", "Task Name", "Owner", "Team", "Planned Start", "Planned End", "Status", "Dependencies"]
            ].sort_values(["Status", "Team", "Owner", "Task Name"]),
            use_container_width=True,
            hide_index=True,
            height=360,
        )

    with tab_ai:
        chat_key = f"scan_v2_chat_{active_sheet}"
        st.session_state.setdefault(chat_key, [])
        top_ai_cols = st.columns([4, 1], gap="small")
        top_ai_cols[1].button("🧹 Clear Chat", key=f"scan_v2_clear_chat_{active_sheet}", on_click=lambda: st.session_state.update({chat_key: []}))
        st.markdown(
            f"""
            <div class="summary-card">
                <h4>Project Summary</h4>
                <p><b>{active_sheet}</b> has <b>{total_tasks}</b> tasks, <b>{len(insights_df[insights_df['Delay Days'] > 0])}</b> delayed items, and an estimated <b>{ai_summary['delay_probability']}%</b> delay probability. The overall risk level is <b>{ai_summary['risk_level']}</b>.</p>
                <p><b>Suggested optimized completion:</b> {ai_summary['optimized_completion'].strftime("%d %b %Y")}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        for message in st.session_state[chat_key]:
            role = message["role"]
            with st.chat_message(role):
                st.markdown(message["content"])
        prompt = st.chat_input("Ask about delays, bottlenecks, portfolio health, or mitigation...", key=f"scan_v2_prompt_{active_sheet}")
        if prompt:
            st.session_state[chat_key].append({"role": "user", "content": prompt})
            response = (
                f"The current project view shows {len(insights_df[insights_df['Delay Days'] > 0])} delayed task(s), "
                f"{len(conflict_df)} resource conflict(s), and a {ai_summary['risk_level']} risk profile. "
                f"The next best action is {suggestions[0].lower()}"
            )
            st.session_state[chat_key].append({"role": "assistant", "content": response})
            st.rerun()

    review_word = _build_review_word(active_sheet, insights_df, resource_df, ai_summary, suggestions)
    review_pdf = _build_safe_scan_pdf_report(active_sheet, total_tasks, ai_summary, suggestions)
    export_cols = st.columns([1, 1, 1, 3], gap="small")
    export_cols[0].download_button(
        "📊 Export Excel",
        data=export_excel,
        file_name=f"{active_sheet.lower().replace(' ', '_')}_dashboard.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        use_container_width=True,
        key=f"scan_v2_export_excel_{active_sheet}",
    )
    export_cols[1].download_button(
        "📄 Export PDF",
        data=review_pdf,
        file_name=f"{active_sheet.lower().replace(' ', '_')}_dashboard.pdf",
        mime="application/pdf",
        type="secondary",
        use_container_width=True,
        key=f"scan_v2_export_pdf_{active_sheet}",
    )
    export_cols[2].download_button(
        "📝 Review Word Doc",
        data=review_word,
        file_name=f"{active_sheet.lower().replace(' ', '_')}_review.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        type="tertiary",
        use_container_width=True,
        key=f"scan_v2_export_word_{active_sheet}",
    )
