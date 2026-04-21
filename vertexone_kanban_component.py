from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit.components.v1 as components


_FRONTEND_DIR = Path("/Users/lalitfintuple.com/Desktop/test_script/PMO/vertexone_kanban_frontend")
if not _FRONTEND_DIR.exists():
    _FRONTEND_DIR = Path(__file__).with_name("vertexone_kanban_frontend")

_KANBAN_COMPONENT = components.declare_component(
    "vertexone_kanban_component",
    path=str(_FRONTEND_DIR),
)


def _safe_scalar(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    try:
        return value.item()  # numpy scalar support
    except Exception:
        return str(value)


def render_vertexone_kanban(
    tasks: list[dict[str, Any]],
    metrics: dict[str, dict[str, Any]],
    lane_body_height: int = 620,
    key: str | None = None,
):
    payload = {
        "tasks": [
            {
                "task_id": str(task.get("task_id", "")),
                "task_name": str(task.get("task_name", "")),
                "status": str(task.get("status", "To Do")),
                "owner": str(task.get("owner", "Unassigned")),
                "team": str(task.get("team", "General Delivery")),
                "planned_start": str(task.get("planned_start", "-")),
                "planned_end": str(task.get("planned_end", "-")),
                "due_risk": str(task.get("due_risk", "On Track")),
                "percent_complete": int(_safe_scalar(task.get("percent_complete", 0)) or 0),
            }
            for task in tasks
        ],
        "metrics": {
            str(status): {
                "count": int(_safe_scalar(values.get("count", 0)) or 0),
                "pct": int(_safe_scalar(values.get("pct", 0)) or 0),
            }
            for status, values in metrics.items()
        },
        "lane_body_height": int(lane_body_height),
    }
    return _KANBAN_COMPONENT(data=payload, default=None, key=key)
