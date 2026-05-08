"""Completion policy - conservative force-complete decisions"""

from typing import Any, Optional


VIDEO_COMPLETE_TYPES = {"video_search", "comment"}
FLOW_COMPLETE_TYPES = {"baidu_map", "meituan", "travel"}
RECENT_ACTION_WINDOW = 3
MIN_VIDEO_COMPLETE_STEP = 8



def _has_recent_type_then_completion_clicks(action_sequence: list[str]) -> bool:
    return action_sequence[-3:] == ["TYPE", "CLICK", "CLICK"] or action_sequence[-4:] == ["TYPE", "CLICK", "CLICK", "CLICK"]



def _build_action_sequence(
    recent_actions: Optional[list[str]],
    current_action: Optional[str],
) -> list[str]:
    sequence = list(recent_actions or [])
    if current_action is not None:
        sequence.append(current_action)
    return sequence



def should_force_complete(
    task: Any,
    step_count: int,
    last_action: Optional[str],
    current_action: Optional[str],
    recent_actions: Optional[list[str]] = None,
) -> bool:
    if task is not None and hasattr(task, "has_pending_text") and task.has_pending_text():
        return False
    if step_count < MIN_VIDEO_COMPLETE_STEP:
        return False
    if last_action == "OPEN":
        return False
    if task is None or not hasattr(task, "task_type"):
        return False
    if last_action != "CLICK":
        return False
    if current_action != "CLICK":
        return False

    action_sequence = _build_action_sequence(recent_actions, current_action)
    if task.task_type in VIDEO_COMPLETE_TYPES:
        return _has_recent_type_then_completion_clicks(action_sequence)
    return False
