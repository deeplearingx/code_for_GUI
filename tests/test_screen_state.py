"""ScreenState unit tests."""

import os
import sys

_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _root)

from utils.history_manager import HistoryManager  # noqa: E402
from utils.screen_state import ScreenState, recognize_screen_state  # noqa: E402
from utils.task_parser import TaskInfo  # noqa: E402


def test_video_search_states() -> None:
    video_task = TaskInfo(
        instruction="在腾讯视频搜索庆余年",
        app_name="腾讯视频",
        task_type="video_search",
        type_queue=["庆余年"],
    )
    video_history = HistoryManager()
    video_history.add("OPEN", {"app_name": "腾讯视频"})
    assert recognize_screen_state(video_task, video_history).state == ScreenState.SEARCH_ENTRY_VISIBLE

    video_history.add("CLICK", {"point": [902, 78]})
    assert recognize_screen_state(video_task, video_history).state == ScreenState.SEARCH_INPUT_ACTIVE

    video_history.add("TYPE", {"text": "庆余年"})
    assert recognize_screen_state(video_task, video_history).state == ScreenState.RESULT_LIST

    video_task.commit_text()
    video_history.add("CLICK", {"point": [500, 260]})
    assert recognize_screen_state(video_task, video_history).state == ScreenState.DETAIL_PAGE


def test_comment_states() -> None:
    comment_task = TaskInfo(
        instruction="在爱奇艺搜索采莲曲，发布评论：好看",
        app_name="爱奇艺",
        task_type="comment",
        type_queue=["采莲曲", "好看"],
        type_index=1,
    )
    comment_history = HistoryManager()
    comment_history.add("CLICK", {"point": [500, 260]})
    assert recognize_screen_state(comment_task, comment_history).state == ScreenState.DETAIL_PAGE

    comment_history.add("CLICK", {"point": [500, 930]})
    assert recognize_screen_state(comment_task, comment_history).state == ScreenState.COMMENT_BOX

    comment_history.add("TYPE", {"text": "好看"})
    assert recognize_screen_state(comment_task, comment_history).state == ScreenState.COMMENT_TYPED

    comment_task.commit_text()
    comment_history.add("CLICK", {"point": [930, 930]})
    assert recognize_screen_state(comment_task, comment_history).state == ScreenState.DONE


def test_travel_states_with_date_hint() -> None:
    travel_task = TaskInfo(
        instruction="在去哪儿旅行查后天北京到上海的航班",
        app_name="去哪儿旅行",
        task_type="travel",
        type_queue=["北京", "上海"],
        travel_date_hint="后天",
    )
    travel_history = HistoryManager()
    travel_history.add("OPEN", {"app_name": "去哪儿旅行"})
    assert recognize_screen_state(travel_task, travel_history).state == ScreenState.TRAVEL_DEPART_FIELD

    travel_history.add("CLICK", {"point": [252, 291]})
    assert recognize_screen_state(travel_task, travel_history).state == ScreenState.TRAVEL_DEPART_SEARCH

    travel_history.add("CLICK", {"point": [500, 165]})
    assert recognize_screen_state(travel_task, travel_history).state == ScreenState.SEARCH_INPUT_ACTIVE

    travel_history.add("TYPE", {"text": "北京"})
    assert recognize_screen_state(travel_task, travel_history).state == ScreenState.TRAVEL_DEPART_RESULT

    travel_task.commit_text()
    travel_history.add("CLICK", {"point": [500, 180]})
    assert recognize_screen_state(travel_task, travel_history).state == ScreenState.TRAVEL_DESTINATION_FIELD

    travel_history.add("CLICK", {"point": [741, 290]})
    assert recognize_screen_state(travel_task, travel_history).state == ScreenState.TRAVEL_DESTINATION_SEARCH

    travel_history.add("CLICK", {"point": [500, 165]})
    assert recognize_screen_state(travel_task, travel_history).state == ScreenState.SEARCH_INPUT_ACTIVE

    travel_history.add("TYPE", {"text": "上海"})
    assert recognize_screen_state(travel_task, travel_history).state == ScreenState.TRAVEL_DESTINATION_RESULT

    travel_task.commit_text()
    travel_history.add("CLICK", {"point": [500, 180]})
    assert recognize_screen_state(travel_task, travel_history).state == ScreenState.TRAVEL_DATE_ENTRY

    travel_history.add("CLICK", {"point": [277, 361]})
    assert recognize_screen_state(travel_task, travel_history).state == ScreenState.TRAVEL_DATE_OPTION

    travel_history.add("CLICK", {"point": [902, 303]})
    assert recognize_screen_state(travel_task, travel_history).state == ScreenState.TRAVEL_SEARCH_BUTTON

    travel_history.add("CLICK", {"point": [494, 611]})
    assert recognize_screen_state(travel_task, travel_history).state == ScreenState.DONE


def test_travel_no_date_states() -> None:
    travel_no_date_task = TaskInfo(
        instruction="在去哪儿旅行查北京到上海的航班",
        app_name="去哪儿旅行",
        task_type="travel",
        type_queue=["北京", "上海"],
    )
    travel_no_date_history = HistoryManager()
    travel_no_date_history.add("TYPE", {"text": "上海"})
    travel_no_date_task.commit_text()
    travel_no_date_task.commit_text()
    travel_no_date_history.add("CLICK", {"point": [500, 180]})
    assert recognize_screen_state(travel_no_date_task, travel_no_date_history).state == ScreenState.TRAVEL_NO_DATE_READY

    travel_no_date_history.add("SCROLL", {"start_point": [500, 800], "end_point": [500, 300]})
    assert recognize_screen_state(travel_no_date_task, travel_no_date_history).state == ScreenState.DONE

    travel_no_date_history.add("COMPLETE", {})
    assert recognize_screen_state(travel_no_date_task, travel_no_date_history).state == ScreenState.DONE


def test_travel_no_date_uncertain_state_returns_unknown() -> None:
    travel_uncertain_task = TaskInfo(
        instruction="在去哪儿旅行查北京到上海的航班",
        app_name="去哪儿旅行",
        task_type="travel",
        type_queue=["北京", "上海"],
        type_index=2,
    )
    travel_uncertain_history = HistoryManager()
    travel_uncertain_history.add("CLICK", {"point": [741, 290]})

    assert recognize_screen_state(travel_uncertain_task, travel_uncertain_history).state == ScreenState.UNKNOWN
