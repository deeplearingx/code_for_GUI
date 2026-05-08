"""Early post-open screen policy."""

from typing import Optional

from agent_base import ACTION_CLICK, ACTION_OPEN
from .control_grounding import get_anchor
from .task_parser import TaskInfo

EARLY_STEP_LIMIT = 3
HIGH_CONFIDENCE_POPUP_THRESHOLD = 0.8
POPUP_CLOSE_POINT = [900, 60]


def decide_post_open_action(
    task: Optional[TaskInfo],
    step_count: int,
    last_action: Optional[str],
    popup_confidence: float = 0.0,
) -> Optional[tuple[str, dict, str, str]]:
    if task is None:
        return None
    if last_action != ACTION_OPEN:
        return None
    if step_count > EARLY_STEP_LIMIT:
        return None
    if popup_confidence >= HIGH_CONFIDENCE_POPUP_THRESHOLD:
        return (
            ACTION_CLICK,
            {"point": list(POPUP_CLOSE_POINT)},
            "close_popup_high_confidence",
            "high",
        )

    if task.task_type == "travel":
        return (
            ACTION_CLICK,
            {"point": get_anchor(task.app_name, "depart_field")},
            "post_open_travel_depart_field",
            "high",
        )
    if task.task_type == "baidu_map":
        return (
            ACTION_CLICK,
            {"point": get_anchor(task.app_name, "flow_entry")},
            "post_open_baidu_map_flow_entry",
            "medium",
        )
    if task.task_type == "meituan":
        return (
            ACTION_CLICK,
            {"point": get_anchor(task.app_name, "flow_entry")},
            "post_open_meituan_flow_entry",
            "medium",
        )
    if task.app_name:
        return (
            ACTION_CLICK,
            {"point": get_anchor(task.app_name, "search_entry")},
            f"post_open_{task.task_type}_entry",
            "high",
        )
    return None
