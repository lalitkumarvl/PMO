import os

import streamlit.components.v1 as components


_FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "components", "hero_metric_cards")
_METRIC_CARDS_COMPONENT = components.declare_component("hero_metric_cards", path=_FRONTEND_DIR)


def render_metric_cards(cards, selected_id=None, key="hero_metric_cards", height=154):
    payload = []
    for card in cards:
        payload.append(
            {
                "id": str(card["id"]),
                "label": str(card["label"]),
                "value": str(card["value"]),
                "caption": str(card.get("caption", "")),
                "note": str(card.get("note", "")),
                "pill": str(card.get("pill", "")),
                "accent": str(card.get("accent", "#2457d6")),
            }
        )

    return _METRIC_CARDS_COMPONENT(
        cards=payload,
        selected_id=selected_id,
        key=key,
        default=None,
        height=height,
    )
