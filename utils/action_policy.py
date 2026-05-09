"""Action policy layer - cautious post-validation corrections."""

from dataclasses import dataclass
from typing import Any, Optional

from .control_grounding import get_anchor
from .prompt_builder import get_travel_field_coord, get_travel_search_bar_coord

FLOW_TASK_TYPES = {"baidu_map", "meituan", "travel"}


@dataclass(frozen=True)
class PolicyDecision:
    action: str
    params: dict
    changed: bool
    reason: str
    confidence: str


def _keep(action: str, params: dict, reason: str = "validated_action") -> PolicyDecision:
    return PolicyDecision(
        action=action,
        params=dict(params),
        changed=False,
        reason=reason,
        confidence="none",
    )


def _redirect_to_search_bar(task: Any) -> PolicyDecision:
    app_name = getattr(task, "app_name", "") or ""
    return PolicyDecision(
        action="CLICK",
        params={"point": get_anchor(app_name, "search_input")},
        changed=True,
        reason="activate_search_bar_before_type",
        confidence="high",
    )


def _redirect_to_search_entry(task: Any) -> PolicyDecision:
    app_name = getattr(task, "app_name", "") or ""
    return PolicyDecision(
        action="CLICK",
        params={"point": get_anchor(app_name, "search_entry")},
        changed=True,
        reason="activate_search_entry_before_type",
        confidence="high",
    )


def _redirect_to_travel_search_bar() -> PolicyDecision:
    return PolicyDecision(
        action="CLICK",
        params={"point": get_travel_search_bar_coord()},
        changed=True,
        reason="activate_travel_search_bar_before_type",
        confidence="high",
    )


def _redirect_to_flow_entry(task: Any) -> PolicyDecision:
    app_name = getattr(task, "app_name", "") or ""
    if getattr(task, "task_type", "") == "travel":
        point = get_travel_field_coord(getattr(task, "type_index", 0))
    else:
        point = get_anchor(app_name, "flow_entry")
    return PolicyDecision(
        action="CLICK",
        params={"point": point},
        changed=True,
        reason="post_open_flow_entry_correction",
        confidence="high",
    )


def _is_far_from_search_bar(task: Any, params: dict) -> bool:
    point = params.get("point")
    if not isinstance(point, list) or len(point) < 2:
        return False
    search_x, search_y = get_anchor(getattr(task, "app_name", "") or "", "search_input")
    return abs(point[0] - search_x) > 180 or abs(point[1] - search_y) > 180


def _has_pending_text(task: Any) -> bool:
    return bool(task is not None and hasattr(task, "has_pending_text") and task.has_pending_text())


def _pending_text(task: Any) -> str:
    if task is None or not hasattr(task, "peek_pending_text"):
        return ""
    return task.peek_pending_text() or ""


def _is_flow_task(task: Any) -> bool:
    return bool(task is not None and getattr(task, "task_type", "") in FLOW_TASK_TYPES)


def _is_search_entry_click(task: Any, params: dict) -> bool:
    point = params.get("point")
    if not isinstance(point, list) or len(point) < 2:
        return False
    entry_x, entry_y = get_anchor(getattr(task, "app_name", "") or "", "search_entry")
    return abs(point[0] - entry_x) <= 40 and abs(point[1] - entry_y) <= 40


def _should_redirect_search_bar_click(task: Any, action: str, params: dict) -> bool:
    if action != "CLICK":
        return False
    if task is None:
        return False
    if getattr(task, "task_type", "") not in {"video_search", "comment"}:
        return False
    if not _has_pending_text(task):
        return False
    search_keyword = getattr(task, "search_keyword", "") or ""
    current_pending = _pending_text(task)
    if search_keyword and current_pending != search_keyword:
        return False
    return _is_far_from_search_bar(task, params)


def _is_travel_search_bar_click(last_action: Optional[str], last_click_point: Optional[list[int]]) -> bool:
    if last_action != "CLICK":
        return False
    if not isinstance(last_click_point, list) or len(last_click_point) < 2:
        return False
    target_x, target_y = get_travel_search_bar_coord()
    return abs(last_click_point[0] - target_x) <= 40 and abs(last_click_point[1] - target_y) <= 40


def _is_top_right_close_click(params: dict) -> bool:
    point = params.get("point")
    if not isinstance(point, list) or len(point) < 2:
        return False
    return point[0] >= 800 and point[1] <= 120


def _should_redirect_flow_type(task: Any, action: str, last_action: Optional[str], last_click_point: Optional[list[int]]) -> bool:
    if action != "TYPE":
        return False
    if task is None:
        return False
    if getattr(task, "task_type", "") != "travel":
        return False
    if not _has_pending_text(task):
        return False
    return not _is_travel_search_bar_click(last_action, last_click_point)


def _should_redirect_post_open_flow_click(task: Any, action: str, last_action: Optional[str], params: dict) -> bool:
    if action != "CLICK":
        return False
    if last_action != "OPEN":
        return False
    if not _is_flow_task(task):
        return False
    if not _has_pending_text(task):
        return False
    if getattr(task, "task_type", "") != "travel":
        return False
    if _is_top_right_close_click(params):
        return False
    point = params.get("point")
    if point == get_travel_field_coord(getattr(task, "type_index", 0)):
        return False
    if point == get_travel_search_bar_coord():
        return False
    return True


def correct(
    action: str,
    params: dict,
    task: Any,
    last_action: Optional[str],
    recent_actions: Optional[list[str]] = None,
    last_click_point: Optional[list[int]] = None,
) -> PolicyDecision:
    _ = recent_actions

    if _is_flow_task(task) and last_action == "OPEN" and _has_pending_text(task) and action == "TYPE":
        return _redirect_to_flow_entry(task)

    if _should_redirect_post_open_flow_click(task, action, last_action, params):
        return _redirect_to_flow_entry(task)

    if _is_flow_task(task) and action == "CLICK":
        return _keep(action, params, reason="flow_task_preserve_validated_action")

    if action == "CLICK" and last_action == "OPEN" and getattr(task, "task_type", "") in {"video_search", "comment"} and _has_pending_text(task):
        if _is_search_entry_click(task, params):
            return _keep(action, params, reason="post_open_search_entry_preserve")
        return _redirect_to_search_entry(task)

    if _should_redirect_flow_type(task, action, last_action, last_click_point):
        return _redirect_to_travel_search_bar()

    if _should_redirect_search_bar_click(task, action, params):
        return _redirect_to_search_bar(task)

    return _keep(action, params)
