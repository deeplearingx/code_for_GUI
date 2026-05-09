"""Deterministic workflow graph for supported video/comment/travel tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .screen_state import ScreenState, ScreenStateSnapshot, supports_deterministic_flow
from .task_parser import TaskInfo


@dataclass(frozen=True)
class PlannedAction:
    action: str
    parameters: dict
    terminal: bool = False


def next_action(task: Optional[TaskInfo], snapshot: ScreenStateSnapshot) -> Optional[PlannedAction]:
    if task is None or not supports_deterministic_flow(task):
        return None

    pending_text = task.peek_pending_text()

    if task.task_type == "travel":
        if snapshot.state == ScreenState.TRAVEL_DEPART_FIELD:
            return PlannedAction("CLICK", {"control": "depart_field"})
        if snapshot.state == ScreenState.TRAVEL_DEPART_SEARCH:
            return PlannedAction("CLICK", {"control": "search_bar"})
        if snapshot.state == ScreenState.SEARCH_INPUT_ACTIVE and pending_text is not None:
            return PlannedAction("TYPE", {"text": "__PENDING__"})
        if snapshot.state == ScreenState.TRAVEL_DEPART_RESULT:
            return PlannedAction("CLICK", {"control": "first_result"})
        if snapshot.state == ScreenState.TRAVEL_DESTINATION_FIELD:
            return PlannedAction("CLICK", {"control": "destination_field"})
        if snapshot.state == ScreenState.TRAVEL_DESTINATION_SEARCH:
            return PlannedAction("CLICK", {"control": "search_bar"})
        if snapshot.state == ScreenState.TRAVEL_DESTINATION_RESULT:
            return PlannedAction("CLICK", {"control": "first_result"})
        if snapshot.state == ScreenState.TRAVEL_DATE_ENTRY:
            return PlannedAction("CLICK", {"control": "date_entry"})
        if snapshot.state == ScreenState.TRAVEL_DATE_OPTION:
            return PlannedAction("CLICK", {"control": "date_option"})
        if snapshot.state == ScreenState.TRAVEL_SEARCH_BUTTON:
            return PlannedAction("CLICK", {"control": "search_button"})
        if snapshot.state == ScreenState.TRAVEL_NO_DATE_READY:
            return PlannedAction("SCROLL", {"start_point": [500, 800], "end_point": [500, 300]})
        if snapshot.state == ScreenState.DONE:
            return PlannedAction("COMPLETE", {}, terminal=True)
        return None

    if task.task_type == "video_search":
        if snapshot.state == ScreenState.SEARCH_ENTRY_VISIBLE:
            return PlannedAction("CLICK", {"control": "search_entry"})
        if snapshot.state == ScreenState.SEARCH_INPUT_ACTIVE and pending_text is not None:
            return PlannedAction("TYPE", {"text": "__PENDING__"})
        if snapshot.state == ScreenState.RESULT_LIST:
            return PlannedAction("CLICK", {"control": "first_result"})
        if snapshot.state == ScreenState.DETAIL_PAGE:
            return PlannedAction("COMPLETE", {}, terminal=True)
        return None

    if snapshot.state == ScreenState.SEARCH_ENTRY_VISIBLE:
        return PlannedAction("CLICK", {"control": "search_entry"})
    if snapshot.state == ScreenState.SEARCH_INPUT_ACTIVE and pending_text is not None:
        return PlannedAction("TYPE", {"text": "__PENDING__"})
    if snapshot.state == ScreenState.RESULT_LIST:
        return PlannedAction("CLICK", {"control": "first_result"})
    if snapshot.state == ScreenState.DETAIL_PAGE and pending_text is not None:
        return PlannedAction("CLICK", {"control": "comment_entry"})
    if snapshot.state == ScreenState.COMMENT_BOX and pending_text is not None:
        return PlannedAction("TYPE", {"text": "__PENDING__"})
    if snapshot.state == ScreenState.COMMENT_TYPED:
        return PlannedAction("CLICK", {"control": "comment_submit"})
    if snapshot.state == ScreenState.DONE:
        return PlannedAction("COMPLETE", {}, terminal=True)
    return None
