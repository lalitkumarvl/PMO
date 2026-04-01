import streamlit as st

from asset_management_workspace_v2 import render_asset_management_workspace_v2
from reports_workspace import render_reports_workspace
from roadmap_workspace_v3 import render_roadmap_workspace_v3
from scan_workspace_v3 import render_scan_workspace_v3


def apply_runtime_patch():
    if getattr(st, "_pmo_runtime_patch_v2_applied", False):
        return

    original_radio = st.radio

    def patched_radio(label, options, *args, **kwargs):
        if label == "Select Engine" and options == ["🚀 Scan Project", "📅 Create RoadMap"]:
            display_options = ["🚀 Scan Project", "📅 Create RoadMap", "🧾 Asset Management", "📈 Reports"]
            selected = original_radio(label, display_options, *args, **kwargs)
            st.session_state["_pmo_actual_engine"] = selected
            if selected in {"🧾 Asset Management", "📈 Reports"}:
                return "🚀 Scan Project"
            return selected
        return original_radio(label, options, *args, **kwargs)

    st.radio = patched_radio

    import project_scan_workspace
    import roadmap_workspace

    def patched_scan_workspace():
        actual_engine = st.session_state.get("_pmo_actual_engine")
        if actual_engine == "🧾 Asset Management":
            render_asset_management_workspace_v2()
        elif actual_engine == "📈 Reports":
            render_reports_workspace()
        else:
            render_scan_workspace_v3()

    project_scan_workspace.render_project_scan_workspace = patched_scan_workspace
    roadmap_workspace.render_roadmap_workspace = render_roadmap_workspace_v3
    st._pmo_runtime_patch_v2_applied = True
