"""Semantic control grounding helpers."""

from typing import Optional

from .prompt_builder import get_flow_continue_coord, get_travel_field_coord, get_travel_search_button_coord

DEFAULT_ANCHORS: dict[str, list[int]] = {
    "search_entry": [500, 120],
    "search_input": [500, 100],
    "flow_entry": [500, 220],
    "depart_field": [500, 220],
    "search_button": [500, 120],
}

ANCHORS_BY_APP: dict[str, dict[str, list[int]]] = {
    "抖音": {
        "search_entry": [898, 922],
        "search_input": [200, 80],
    },
    "快手": {
        "search_entry": [913, 69],
        "search_input": [500, 100],
    },
    "爱奇艺": {
        "search_entry": [835, 46],
        "search_input": [500, 100],
    },
    "芒果TV": {
        "search_entry": [849, 79],
        "search_input": [500, 100],
    },
    "喜马拉雅": {
        "search_entry": [854, 40],
        "search_input": [500, 100],
    },
    "腾讯视频": {
        "search_entry": [902, 78],
        "search_input": [850, 80],
    },
    "哔哩哔哩": {
        "search_entry": [912, 74],
        "search_input": [800, 80],
    },
    "去哪儿旅行": {
        "search_entry": [500, 100],
        "search_input": [500, 100],
        "depart_field": get_travel_field_coord(0),
        "destination_field": get_travel_field_coord(1),
        "search_button": get_travel_search_button_coord(),
    },
    "百度地图": {
        "search_entry": [500, 100],
        "search_input": [500, 100],
        "flow_entry": get_flow_continue_coord("百度地图"),
    },
    "美团": {
        "search_entry": [500, 120],
        "search_input": [500, 120],
        "flow_entry": get_flow_continue_coord("美团"),
    },
}


def get_anchor(app_name: str, anchor_name: str, default: Optional[list[int]] = None) -> list[int]:
    app_anchors = ANCHORS_BY_APP.get(app_name, {})
    anchor = app_anchors.get(anchor_name)
    if anchor is not None:
        return list(anchor)
    if default is not None:
        return list(default)
    return list(DEFAULT_ANCHORS.get(anchor_name, DEFAULT_ANCHORS["search_entry"]))
