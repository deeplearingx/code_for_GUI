"""Agent deterministic path tests."""

import os
import sys
from unittest.mock import patch

from PIL import Image

_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _root)

from agent import Agent  # noqa: E402
from agent_base import AgentInput  # noqa: E402
from utils.screen_state import ScreenState, ScreenStateSnapshot  # noqa: E402
from utils.task_parser import TaskInfo  # noqa: E402


def _image() -> Image.Image:
    return Image.new("RGB", (20, 20), color="white")


def _fail_if_called(_messages, **_kwargs):
    raise AssertionError("LLM path should not be called for deterministic flow")


class _Message:
    def __init__(self, value: str) -> None:
        self.content = value


class _Choice:
    def __init__(self, value: str) -> None:
        self.message = _Message(value)


class _Response:
    def __init__(self, value: str) -> None:
        self.choices = [_Choice(value)]


def _fake_response(content: str) -> _Response:
    return _Response(content)


def _scroll_response(_messages, **_kwargs) -> _Response:
    return _fake_response(
        '{"action": "SCROLL", "parameters": {"start_point": [500, 800], "end_point": [500, 300]}}'
    )


def test_video_search_uses_deterministic_steps() -> None:
    image = _image()
    agent = Agent()
    agent._call_api = _fail_if_called

    agent.act(AgentInput(instruction="在腾讯视频搜索庆余年", current_image=image, step_count=1))
    step2 = agent.act(AgentInput(instruction="在腾讯视频搜索庆余年", current_image=image, step_count=2))
    assert (step2.action, step2.parameters) == ("CLICK", {"point": [902, 78]})

    step3 = agent.act(AgentInput(instruction="在腾讯视频搜索庆余年", current_image=image, step_count=3))
    assert (step3.action, step3.parameters) == ("CLICK", {"point": [850, 80]})

    step4 = agent.act(AgentInput(instruction="在腾讯视频搜索庆余年", current_image=image, step_count=4))
    assert (step4.action, step4.parameters) == ("TYPE", {"text": "庆余年"})

    step5 = agent.act(AgentInput(instruction="在腾讯视频搜索庆余年", current_image=image, step_count=5))
    assert (step5.action, step5.parameters) == ("CLICK", {"point": [500, 260]})

    step6 = agent.act(AgentInput(instruction="在腾讯视频搜索庆余年", current_image=image, step_count=6))
    assert (step6.action, step6.parameters) == ("COMPLETE", {})


def test_unsupported_task_without_app_uses_model_path() -> None:
    image = _image()
    agent = Agent()
    agent._call_api = _scroll_response

    step1 = agent.act(AgentInput(instruction="帮我滚动一下页面", current_image=image, step_count=1))

    assert step1.action == "SCROLL"
    assert step1.parameters == {"start_point": [500, 800], "end_point": [500, 300]}


def test_travel_uses_deterministic_steps() -> None:
    image = _image()
    agent = Agent()
    agent._call_api = _fail_if_called
    instruction = "在去哪儿旅行查后天北京到上海的航班"

    agent.act(AgentInput(instruction=instruction, current_image=image, step_count=1))
    step2 = agent.act(AgentInput(instruction=instruction, current_image=image, step_count=2))
    assert (step2.action, step2.parameters) == ("CLICK", {"point": [252, 291]})

    step3 = agent.act(AgentInput(instruction=instruction, current_image=image, step_count=3))
    assert (step3.action, step3.parameters) == ("CLICK", {"point": [500, 165]})

    step4 = agent.act(AgentInput(instruction=instruction, current_image=image, step_count=4))
    assert (step4.action, step4.parameters) == ("TYPE", {"text": "北京"})

    step5 = agent.act(AgentInput(instruction=instruction, current_image=image, step_count=5))
    assert (step5.action, step5.parameters) == ("CLICK", {"point": [500, 180]})

    step6 = agent.act(AgentInput(instruction=instruction, current_image=image, step_count=6))
    assert (step6.action, step6.parameters) == ("CLICK", {"point": [741, 290]})


def test_unknown_deterministic_state_falls_back_to_model_path() -> None:
    image = _image()
    agent = Agent()
    agent._call_api = _scroll_response
    instruction = "在去哪儿旅行查后天北京到上海的航班"

    agent.act(AgentInput(instruction=instruction, current_image=image, step_count=1))
    with patch(
        "agent.recognize_screen_state",
        return_value=ScreenStateSnapshot(ScreenState.UNKNOWN, None, "OPEN", None, "forced_unknown"),
    ):
        step2 = agent.act(AgentInput(instruction=instruction, current_image=image, step_count=2))

    assert (step2.action, step2.parameters) == (
        "SCROLL",
        {"start_point": [500, 800], "end_point": [500, 300]},
    )


def test_travel_type_commits_exactly_once() -> None:
    image = _image()
    agent = Agent()
    agent._call_api = _fail_if_called
    instruction = "在去哪儿旅行查后天北京到上海的航班"

    agent.act(AgentInput(instruction=instruction, current_image=image, step_count=1))
    agent.act(AgentInput(instruction=instruction, current_image=image, step_count=2))
    agent.act(AgentInput(instruction=instruction, current_image=image, step_count=3))
    step4 = agent.act(AgentInput(instruction=instruction, current_image=image, step_count=4))

    assert (step4.action, step4.parameters) == ("TYPE", {"text": "北京"})
    assert agent._task is not None
    assert agent._task.type_index == 1


def test_no_date_travel_scrolls_then_completes_and_stays_complete() -> None:
    image = _image()
    agent = Agent()
    agent._call_api = _fail_if_called
    instruction = "在去哪儿旅行查北京到上海的航班"

    for step_count in range(1, 10):
        agent.act(AgentInput(instruction=instruction, current_image=image, step_count=step_count))

    step10 = agent.act(AgentInput(instruction=instruction, current_image=image, step_count=10))
    assert (step10.action, step10.parameters) == (
        "SCROLL",
        {"start_point": [500, 800], "end_point": [500, 300]},
    )

    step11 = agent.act(AgentInput(instruction=instruction, current_image=image, step_count=11))
    assert (step11.action, step11.parameters) == ("COMPLETE", {})

    step12 = agent.act(AgentInput(instruction=instruction, current_image=image, step_count=12))
    assert (step12.action, step12.parameters) == ("COMPLETE", {})


def test_uncertain_no_date_travel_falls_back_to_model_path() -> None:
    image = _image()
    agent = Agent()
    agent._call_api = _scroll_response
    instruction = "在去哪儿旅行查北京到上海的航班"
    agent._task = TaskInfo(
        instruction=instruction,
        app_name="去哪儿旅行",
        task_type="travel",
        type_queue=["北京", "上海"],
        type_index=2,
    )
    agent._history.add("CLICK", {"point": [741, 290]})

    step8 = agent.act(AgentInput(instruction=instruction, current_image=image, step_count=8))

    assert (step8.action, step8.parameters) == (
        "SCROLL",
        {"start_point": [500, 800], "end_point": [500, 300]},
    )
