"""Action policy layer - cautious post-validation corrections."""

from dataclasses import dataclass
from typing import Any, Optional

from .prompt_builder import get_search_bar_coord, get_travel_search_bar_coord

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
        params={"point": get_search_bar_coord(app_name)},
        changed=True,
        reason="activate_search_bar_before_type",
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


def _is_far_from_search_bar(task: Any, params: dict) -> bool:
    point = params.get("point")
    if not isinstance(point, list) or len(point) < 2:
        return False
    search_x, search_y = get_search_bar_coord(getattr(task, "app_name", "") or "")
    return abs(point[0] - search_x) > 180 or abs(point[1] - search_y) > 180


def _has_pending_text(task: Any) -> bool:
    return bool(task is not None and hasattr(task, "has_pending_text") and task.has_pending_text())


def _pending_text(task: Any) -> str:
    if task is None or not hasattr(task, "peek_pending_text"):
        return ""
    return task.peek_pending_text() or ""


def _is_flow_task(task: Any) -> bool:
    return bool(task is not None and getattr(task, "task_type", "") in FLOW_TASK_TYPES)


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


def correct(
    action: str,
    params: dict,
    task: Any,
    last_action: Optional[str],
    recent_actions: Optional[list[str]] = None,
    last_click_point: Optional[list[int]] = None,
) -> PolicyDecision:
    _ = recent_actions

    if _is_flow_task(task) and action == "CLICK":
        return _keep(action, params, reason="flow_task_preserve_validated_action")

    if _should_redirect_flow_type(task, action, last_action, last_click_point):
        return _redirect_to_travel_search_bar()

    if _should_redirect_search_bar_click(task, action, params):
        return _redirect_to_search_bar(task)

    return _keep(action, params)
