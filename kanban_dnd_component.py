import os

import streamlit.components.v1 as components


_FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "components", "kanban_dnd")
_KANBAN_COMPONENT = components.declare_component("kanban_dnd_board", path=_FRONTEND_DIR)


def render_kanban_board(items, stages, key="kanban_board", height=980):
    board_data = []
    for item in items:
        board_data.append(
            {
                "row_id": str(item["row_id"]),
                "task_id": str(item["task_id"]),
                "task_name": str(item["task_name"]),
                "owner": str(item["owner"]),
                "stage": str(item["stage"]),
            }
        )

    return _KANBAN_COMPONENT(
        board_data=board_data,
        stages=stages,
        key=key,
        default=None,
        height=height,
    )
