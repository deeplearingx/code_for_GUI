"""Explicit workflow state inference for deterministic app flows."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .grounder import has_distinct_control, identify_control
from .history_manager import HistoryManager
from .task_parser import TaskInfo


class ScreenState(Enum):
    UNKNOWN = "unknown"
    POST_OPEN = "post_open"
    SEARCH_ENTRY_VISIBLE = "search_entry_visible"
    SEARCH_INPUT_ACTIVE = "search_input_active"
    RESULT_LIST = "result_list"
    DETAIL_PAGE = "detail_page"
    COMMENT_BOX = "comment_box"
    COMMENT_TYPED = "comment_typed"
    TRAVEL_DEPART_FIELD = "travel_depart_field"
    TRAVEL_DEPART_SEARCH = "travel_depart_search"
    TRAVEL_DEPART_RESULT = "travel_depart_result"
    TRAVEL_DESTINATION_FIELD = "travel_destination_field"
    TRAVEL_DESTINATION_SEARCH = "travel_destination_search"
    TRAVEL_DESTINATION_RESULT = "travel_destination_result"
    TRAVEL_DATE_ENTRY = "travel_date_entry"
    TRAVEL_DATE_OPTION = "travel_date_option"
    TRAVEL_SEARCH_BUTTON = "travel_search_button"
    TRAVEL_NO_DATE_READY = "travel_no_date_ready"
    DONE = "done"


@dataclass(frozen=True)
class ScreenStateSnapshot:
    state: ScreenState
    pending_text: Optional[str]
    last_action: Optional[str]
    last_control: Optional[str]
    reason: str


DETERMINISTIC_VIDEO_APPS = {"爱奇艺", "腾讯视频", "芒果TV", "喜马拉雅", "哔哩哔哩", "抖音", "快手"}
DETERMINISTIC_TRAVEL_APPS = {"去哪儿旅行"}
DETERMINISTIC_TASK_TYPES = {"video_search", "comment"}


def supports_deterministic_flow(task: Optional[TaskInfo]) -> bool:
    if task is None:
        return False
    if task.task_type in DETERMINISTIC_TASK_TYPES:
        return task.app_name in DETERMINISTIC_VIDEO_APPS
    if task.task_type == "travel":
        return task.app_name in DETERMINISTIC_TRAVEL_APPS
    return False


def _infer_last_control(task: TaskInfo, history: HistoryManager) -> Optional[str]:
    point = history.get_last_click_point()
    if point is None:
        return None
    candidate_names = [
        "search_entry",
        "search_input",
        "search_bar",
        "first_result",
        "comment_entry",
        "comment_submit",
        "depart_field",
        "destination_field",
        "date_entry",
        "date_option",
        "search_button",
    ]
    return identify_control(task.app_name, point, candidate_names)


def recognize_screen_state(task: Optional[TaskInfo], history: HistoryManager) -> ScreenStateSnapshot:
    if not supports_deterministic_flow(task):
        return ScreenStateSnapshot(
            state=ScreenState.UNKNOWN,
            pending_text=None,
            last_action=history.get_last_action(),
            last_control=None,
            reason="unsupported_task",
        )

    assert task is not None
    last_action = history.get_last_action()
    pending_text = task.peek_pending_text()
    last_control = _infer_last_control(task, history)

    if task.task_type == "travel":
        if last_action == "COMPLETE":
            return ScreenStateSnapshot(
                state=ScreenState.DONE,
                pending_text=None,
                last_action=last_action,
                last_control=last_control,
                reason="travel_complete",
            )
        if last_action == "OPEN":
            return ScreenStateSnapshot(
                state=ScreenState.TRAVEL_DEPART_FIELD,
                pending_text=pending_text,
                last_action=last_action,
                last_control=last_control,
                reason="travel_post_open",
            )
        if task.type_index == 0 and pending_text is not None:
            if last_action == "CLICK" and last_control == "depart_field":
                return ScreenStateSnapshot(ScreenState.TRAVEL_DEPART_SEARCH, pending_text, last_action, last_control, "travel_need_depart_search")
            if last_action == "CLICK" and last_control == "search_bar":
                return ScreenStateSnapshot(ScreenState.SEARCH_INPUT_ACTIVE, pending_text, last_action, last_control, "travel_depart_search_activated")
            if last_action == "TYPE":
                return ScreenStateSnapshot(ScreenState.TRAVEL_DEPART_RESULT, pending_text, last_action, last_control, "travel_depart_typed")
            return ScreenStateSnapshot(ScreenState.TRAVEL_DEPART_FIELD, pending_text, last_action, last_control, "travel_need_depart_field")
        if task.type_index == 1 and pending_text is not None:
            if last_action == "CLICK" and last_control == "first_result":
                return ScreenStateSnapshot(ScreenState.TRAVEL_DESTINATION_FIELD, pending_text, last_action, last_control, "travel_need_destination_field")
            if last_action == "CLICK" and last_control == "destination_field":
                return ScreenStateSnapshot(ScreenState.TRAVEL_DESTINATION_SEARCH, pending_text, last_action, last_control, "travel_need_destination_search")
            if last_action == "CLICK" and last_control == "search_bar":
                return ScreenStateSnapshot(ScreenState.SEARCH_INPUT_ACTIVE, pending_text, last_action, last_control, "travel_destination_search_activated")
            if last_action == "TYPE":
                return ScreenStateSnapshot(ScreenState.TRAVEL_DESTINATION_RESULT, pending_text, last_action, last_control, "travel_destination_typed")
            return ScreenStateSnapshot(ScreenState.TRAVEL_DESTINATION_FIELD, pending_text, last_action, last_control, "travel_need_destination_field")
        if last_action == "TYPE":
            return ScreenStateSnapshot(
                ScreenState.TRAVEL_DESTINATION_RESULT,
                None,
                last_action,
                last_control,
                "travel_destination_typed",
            )
        if task.travel_date_hint:
            if last_action == "CLICK" and last_control == "first_result":
                return ScreenStateSnapshot(ScreenState.TRAVEL_DATE_ENTRY, None, last_action, last_control, "travel_need_date_entry")
            if last_action == "CLICK" and last_control == "date_entry":
                return ScreenStateSnapshot(ScreenState.TRAVEL_DATE_OPTION, None, last_action, last_control, "travel_need_date_option")
            if last_action == "CLICK" and last_control == "date_option":
                return ScreenStateSnapshot(ScreenState.TRAVEL_SEARCH_BUTTON, None, last_action, last_control, "travel_need_search_button")
            if last_action == "CLICK" and last_control == "search_button":
                return ScreenStateSnapshot(ScreenState.DONE, None, last_action, last_control, "travel_search_submitted")
            return ScreenStateSnapshot(ScreenState.TRAVEL_DATE_ENTRY, None, last_action, last_control, "travel_need_date_entry")
        if last_action == "SCROLL":
            return ScreenStateSnapshot(
                ScreenState.DONE,
                None,
                last_action,
                last_control,
                "travel_no_date_scrolled",
            )
        if last_action == "CLICK" and last_control == "first_result":
            return ScreenStateSnapshot(
                ScreenState.TRAVEL_NO_DATE_READY,
                None,
                last_action,
                last_control,
                "travel_no_date_ready",
            )
        return ScreenStateSnapshot(
            state=ScreenState.UNKNOWN,
            pending_text=None,
            last_action=last_action,
            last_control=last_control,
            reason="travel_no_date_uncertain",
        )

    if last_action == "OPEN":
        if has_distinct_control(task.app_name, "search_entry", "search_input"):
            state = ScreenState.SEARCH_ENTRY_VISIBLE
        else:
            state = ScreenState.SEARCH_INPUT_ACTIVE
        return ScreenStateSnapshot(
            state=state,
            pending_text=pending_text,
            last_action=last_action,
            last_control=last_control,
            reason="post_open",
        )

    if task.task_type == "video_search":
        if pending_text is not None:
            if last_action == "CLICK" and last_control in {"search_entry", "search_input"}:
                return ScreenStateSnapshot(
                    state=ScreenState.SEARCH_INPUT_ACTIVE,
                    pending_text=pending_text,
                    last_action=last_action,
                    last_control=last_control,
                    reason="search_activated",
                )
            if last_action == "TYPE":
                return ScreenStateSnapshot(
                    state=ScreenState.RESULT_LIST,
                    pending_text=pending_text,
                    last_action=last_action,
                    last_control=last_control,
                    reason="search_text_typed",
                )
            if last_action is None:
                return ScreenStateSnapshot(
                    state=ScreenState.POST_OPEN,
                    pending_text=pending_text,
                    last_action=last_action,
                    last_control=last_control,
                    reason="no_history",
                )
            return ScreenStateSnapshot(
                state=ScreenState.SEARCH_ENTRY_VISIBLE,
                pending_text=pending_text,
                last_action=last_action,
                last_control=last_control,
                reason="need_search_activation",
            )

        if last_action == "CLICK" and last_control == "first_result":
            return ScreenStateSnapshot(
                state=ScreenState.DETAIL_PAGE,
                pending_text=None,
                last_action=last_action,
                last_control=last_control,
                reason="result_opened",
            )
        return ScreenStateSnapshot(
            state=ScreenState.RESULT_LIST,
            pending_text=None,
            last_action=last_action,
            last_control=last_control,
            reason="awaiting_result",
        )

    if pending_text is not None:
        if task.type_index == 0:
            if last_action == "CLICK" and last_control in {"search_entry", "search_input"}:
                return ScreenStateSnapshot(
                    state=ScreenState.SEARCH_INPUT_ACTIVE,
                    pending_text=pending_text,
                    last_action=last_action,
                    last_control=last_control,
                    reason="comment_search_activated",
                )
            if last_action == "TYPE":
                return ScreenStateSnapshot(
                    state=ScreenState.RESULT_LIST,
                    pending_text=pending_text,
                    last_action=last_action,
                    last_control=last_control,
                    reason="comment_search_typed",
                )
            return ScreenStateSnapshot(
                state=ScreenState.SEARCH_ENTRY_VISIBLE,
                pending_text=pending_text,
                last_action=last_action,
                last_control=last_control,
                reason="comment_need_search_activation",
            )

        if last_action == "CLICK" and last_control == "comment_entry":
            return ScreenStateSnapshot(
                state=ScreenState.COMMENT_BOX,
                pending_text=pending_text,
                last_action=last_action,
                last_control=last_control,
                reason="comment_box_opened",
            )
        if last_action == "TYPE":
            return ScreenStateSnapshot(
                state=ScreenState.COMMENT_TYPED,
                pending_text=pending_text,
                last_action=last_action,
                last_control=last_control,
                reason="comment_text_typed",
            )
        if last_action == "CLICK" and last_control == "first_result":
            return ScreenStateSnapshot(
                state=ScreenState.DETAIL_PAGE,
                pending_text=pending_text,
                last_action=last_action,
                last_control=last_control,
                reason="detail_opened_before_comment",
            )
        return ScreenStateSnapshot(
            state=ScreenState.DETAIL_PAGE,
            pending_text=pending_text,
            last_action=last_action,
            last_control=last_control,
            reason="need_comment_entry",
        )

    if last_action == "CLICK" and last_control == "comment_submit":
        return ScreenStateSnapshot(
            state=ScreenState.DONE,
            pending_text=None,
            last_action=last_action,
            last_control=last_control,
            reason="comment_submitted",
        )
    return ScreenStateSnapshot(
        state=ScreenState.COMMENT_TYPED,
        pending_text=None,
        last_action=last_action,
        last_control=last_control,
        reason="comment_waiting_submit",
    )
