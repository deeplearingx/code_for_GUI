"""Completion policy - conservative force-complete decisions"""

from typing import Any, Optional


VIDEO_COMPLETE_TYPES = {"video_search", "comment"}
RECENT_ACTION_WINDOW = 3
MIN_VIDEO_COMPLETE_STEP = 8



def _has_recent_type_then_two_clicks(recent_actions: list[str]) -> bool:
    tail = recent_actions[-RECENT_ACTION_WINDOW:]
    return tail == ["TYPE", "CLICK", "CLICK"]



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

    history_tail = recent_actions or []
    if task.task_type in VIDEO_COMPLETE_TYPES:
        return _has_recent_type_then_two_clicks(history_tail)
    return False
