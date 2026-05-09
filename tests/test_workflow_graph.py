"""WorkflowGraph unit tests."""

import os
import sys

_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _root)

from utils.screen_state import ScreenState, ScreenStateSnapshot  # noqa: E402
from utils.task_parser import TaskInfo  # noqa: E402
from utils.workflow_graph import next_action  # noqa: E402


def test_video_search_workflow() -> None:
    video_task = TaskInfo(
        instruction="在腾讯视频搜索庆余年",
        app_name="腾讯视频",
        task_type="video_search",
        type_queue=["庆余年"],
    )

    assert next_action(
        video_task,
        ScreenStateSnapshot(ScreenState.SEARCH_ENTRY_VISIBLE, "庆余年", "OPEN", None, "post_open"),
    ).parameters == {"control": "search_entry"}
    assert next_action(
        video_task,
        ScreenStateSnapshot(
            ScreenState.SEARCH_INPUT_ACTIVE,
            "庆余年",
            "CLICK",
            "search_entry",
            "search_activated",
        ),
    ).action == "TYPE"
    assert next_action(
        video_task,
        ScreenStateSnapshot(ScreenState.RESULT_LIST, "庆余年", "TYPE", "search_input", "search_text_typed"),
    ).parameters == {"control": "first_result"}

    video_task.commit_text()
    assert next_action(
        video_task,
        ScreenStateSnapshot(ScreenState.DETAIL_PAGE, None, "CLICK", "first_result", "result_opened"),
    ).action == "COMPLETE"


def test_comment_workflow() -> None:
    comment_task = TaskInfo(
        instruction="在爱奇艺搜索采莲曲，发布评论：好看",
        app_name="爱奇艺",
        task_type="comment",
        type_queue=["采莲曲", "好看"],
        type_index=1,
    )

    assert next_action(
        comment_task,
        ScreenStateSnapshot(
            ScreenState.DETAIL_PAGE,
            "好看",
            "CLICK",
            "first_result",
            "detail_opened_before_comment",
        ),
    ).parameters == {"control": "comment_entry"}
    assert next_action(
        comment_task,
        ScreenStateSnapshot(
            ScreenState.COMMENT_BOX,
            "好看",
            "CLICK",
            "comment_entry",
            "comment_box_opened",
        ),
    ).action == "TYPE"

    comment_task.commit_text()
    assert next_action(
        comment_task,
        ScreenStateSnapshot(
            ScreenState.COMMENT_TYPED,
            None,
            "TYPE",
            "comment_entry",
            "comment_text_typed",
        ),
    ).parameters == {"control": "comment_submit"}


def test_travel_workflow_with_date_hint() -> None:
    travel_task = TaskInfo(
        instruction="在去哪儿旅行查后天北京到上海的航班",
        app_name="去哪儿旅行",
        task_type="travel",
        type_queue=["北京", "上海"],
        travel_date_hint="后天",
    )

    assert next_action(
        travel_task,
        ScreenStateSnapshot(
            ScreenState.TRAVEL_DEPART_FIELD,
            "北京",
            "OPEN",
            None,
            "travel_post_open",
        ),
    ).parameters == {"control": "depart_field"}
    assert next_action(
        travel_task,
        ScreenStateSnapshot(
            ScreenState.TRAVEL_DEPART_SEARCH,
            "北京",
            "CLICK",
            "depart_field",
            "travel_need_depart_search",
        ),
    ).parameters == {"control": "search_bar"}
    assert next_action(
        travel_task,
        ScreenStateSnapshot(
            ScreenState.SEARCH_INPUT_ACTIVE,
            "北京",
            "CLICK",
            "search_bar",
            "travel_depart_search_activated",
        ),
    ).action == "TYPE"
    assert next_action(
        travel_task,
        ScreenStateSnapshot(
            ScreenState.TRAVEL_DEPART_RESULT,
            "北京",
            "TYPE",
            "search_bar",
            "travel_depart_typed",
        ),
    ).parameters == {"control": "first_result"}

    travel_task.commit_text()
    assert next_action(
        travel_task,
        ScreenStateSnapshot(
            ScreenState.TRAVEL_DESTINATION_FIELD,
            "上海",
            "CLICK",
            "first_result",
            "travel_need_destination_field",
        ),
    ).parameters == {"control": "destination_field"}
    assert next_action(
        travel_task,
        ScreenStateSnapshot(
            ScreenState.TRAVEL_DESTINATION_SEARCH,
            "上海",
            "CLICK",
            "destination_field",
            "travel_need_destination_search",
        ),
    ).parameters == {"control": "search_bar"}
    assert next_action(
        travel_task,
        ScreenStateSnapshot(
            ScreenState.TRAVEL_DESTINATION_RESULT,
            "上海",
            "TYPE",
            "search_bar",
            "travel_destination_typed",
        ),
    ).parameters == {"control": "first_result"}

    travel_task.commit_text()
    assert next_action(
        travel_task,
        ScreenStateSnapshot(
            ScreenState.TRAVEL_DATE_ENTRY,
            None,
            "CLICK",
            "first_result",
            "travel_need_date_entry",
        ),
    ).parameters == {"control": "date_entry"}
    assert next_action(
        travel_task,
        ScreenStateSnapshot(
            ScreenState.TRAVEL_DATE_OPTION,
            None,
            "CLICK",
            "date_entry",
            "travel_need_date_option",
        ),
    ).parameters == {"control": "date_option"}
    assert next_action(
        travel_task,
        ScreenStateSnapshot(
            ScreenState.TRAVEL_SEARCH_BUTTON,
            None,
            "CLICK",
            "date_option",
            "travel_need_search_button",
        ),
    ).parameters == {"control": "search_button"}
    assert next_action(
        travel_task,
        ScreenStateSnapshot(
            ScreenState.DONE,
            None,
            "CLICK",
            "search_button",
            "travel_search_submitted",
        ),
    ).action == "COMPLETE"


def test_travel_workflow_without_date_hint() -> None:
    travel_no_date_task = TaskInfo(
        instruction="在去哪儿旅行查北京到上海的航班",
        app_name="去哪儿旅行",
        task_type="travel",
        type_queue=["北京", "上海"],
        type_index=2,
    )

    assert next_action(
        travel_no_date_task,
        ScreenStateSnapshot(
            ScreenState.TRAVEL_NO_DATE_READY,
            None,
            "CLICK",
            "first_result",
            "travel_no_date_ready",
        ),
    ).parameters == {"start_point": [500, 800], "end_point": [500, 300]}
    assert next_action(
        travel_no_date_task,
        ScreenStateSnapshot(
            ScreenState.DONE,
            None,
            "SCROLL",
            None,
            "travel_no_date_scrolled",
        ),
    ).action == "COMPLETE"


def test_unsupported_task_returns_none() -> None:
    result = next_action(
        TaskInfo(instruction="打开淘宝", app_name="淘宝", task_type="general"),
        ScreenStateSnapshot(ScreenState.UNKNOWN, None, None, None, "unsupported"),
    )

    assert result is None
