"""Submission runtime smoke tests."""

from __future__ import annotations

import importlib
import os
import sys
from typing import Any

import pytest
from PIL import Image

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
PACKAGE_ROOT = os.path.join(ROOT, "submission_fixed_v2")
SUBMISSION_ROOT = os.path.join(PACKAGE_ROOT, "src")
RUNTIME_SYNCED_FILES = [
    "agent.py",
    "agent_base.py",
    "utils/__init__.py",
    "utils/action_parser.py",
    "utils/action_policy.py",
    "utils/action_validator.py",
    "utils/completion_policy.py",
    "utils/control_grounding.py",
    "utils/early_screen_policy.py",
    "utils/grounder.py",
    "utils/history_manager.py",
    "utils/image_utils.py",
    "utils/prompt_builder.py",
    "utils/screen_state.py",
    "utils/task_parser.py",
    "utils/workflow_graph.py",
    "profiles/video_apps.yaml",
    "profiles/iqiyi.yaml",
    "requirements.txt",
]
PACKAGE_REQUIRED_FILES = [
    "src/agent.py",
    "src/agent_base.py",
    "src/requirements.txt",
    "doc/算法设计说明文档",
]
RUNTIME_ROOT = SUBMISSION_ROOT

pytestmark = pytest.mark.skipif(
    not os.path.isdir(SUBMISSION_ROOT)
    or not os.path.isdir(os.path.join(ROOT, "submission_build", "src")),
    reason="submission package layout not present in this repo checkout",
)


class _Message:
    def __init__(self, value: str) -> None:
        self.content = value


class _Choice:
    def __init__(self, value: str) -> None:
        self.message = _Message(value)


class _Response:
    def __init__(self, value: str) -> None:
        self.choices = [_Choice(value)]


@pytest.fixture()
def submission_runtime() -> dict[str, Any]:
    runtime_root = RUNTIME_ROOT
    original_path = list(sys.path)
    _purge_runtime_modules()
    if runtime_root in sys.path:
        sys.path.remove(runtime_root)
    sys.path.insert(0, runtime_root)

    modules = {
        "layout": "package_src",
        "runtime_root": runtime_root,
        "agent": importlib.import_module("agent"),
        "agent_base": importlib.import_module("agent_base"),
        "completion_policy": importlib.import_module("utils.completion_policy"),
        "grounder": importlib.import_module("utils.grounder"),
        "history_manager": importlib.import_module("utils.history_manager"),
        "screen_state": importlib.import_module("utils.screen_state"),
        "task_parser": importlib.import_module("utils.task_parser"),
        "workflow_graph": importlib.import_module("utils.workflow_graph"),
    }

    try:
        yield modules
    finally:
        _purge_runtime_modules()
        sys.path[:] = original_path


def _purge_runtime_modules() -> None:
    for module_name in list(sys.modules):
        if module_name in {"agent", "agent_base", "utils"} or module_name.startswith("utils."):
            sys.modules.pop(module_name, None)


def _image() -> Image.Image:
    return Image.new("RGB", (20, 20), color="white")


def _scroll_response(_messages: list[dict[str, Any]], **_kwargs: Any) -> _Response:
    return _Response(
        '{"action": "SCROLL", "parameters": {"start_point": [500, 800], "end_point": [500, 300]}}'
    )


def test_submission_runtime_files_exist() -> None:
    for relative_path in RUNTIME_SYNCED_FILES:
        submission_path = os.path.join(RUNTIME_ROOT, relative_path)
        assert os.path.isfile(submission_path), submission_path



def test_submission_package_format_files_exist() -> None:
    for relative_path in PACKAGE_REQUIRED_FILES:
        package_path = os.path.join(PACKAGE_ROOT, relative_path)
        assert os.path.isfile(package_path), package_path



def test_submission_package_requirements_match_template() -> None:
    template_path = os.path.join(ROOT, "submission_build", "src", "requirements.txt")
    package_path = os.path.join(PACKAGE_ROOT, "src/requirements.txt")
    with open(template_path, "rb") as template_file:
        template_content = template_file.read()
    with open(package_path, "rb") as package_file:
        package_content = package_file.read()
    assert package_content == template_content, package_path



def test_submission_runtime_files_match_root() -> None:
    for relative_path in RUNTIME_SYNCED_FILES:
        root_path = os.path.join(ROOT, relative_path)
        submission_path = os.path.join(RUNTIME_ROOT, relative_path)
        with open(root_path, "rb") as root_file:
            root_content = root_file.read()
        with open(submission_path, "rb") as submission_file:
            submission_content = submission_file.read()
        assert submission_content == root_content, relative_path


def test_submission_agent_uses_deterministic_path(submission_runtime: dict[str, Any]) -> None:
    agent = submission_runtime["agent"].Agent()
    agent_input = submission_runtime["agent_base"].AgentInput
    agent._call_api = lambda _messages, **_kwargs: (_ for _ in ()).throw(
        AssertionError("LLM path should not be called for deterministic flow")
    )
    instruction = "在腾讯视频搜索庆余年"
    image = _image()

    step1 = agent.act(agent_input(instruction=instruction, current_image=image, step_count=1))
    step2 = agent.act(agent_input(instruction=instruction, current_image=image, step_count=2))
    step3 = agent.act(agent_input(instruction=instruction, current_image=image, step_count=3))

    assert (step1.action, step1.parameters) == ("OPEN", {"app_name": "腾讯视频"})
    assert (step2.action, step2.parameters) == ("CLICK", {"point": [902, 78]})
    assert (step3.action, step3.parameters) == ("CLICK", {"point": [850, 80]})


def test_submission_unsupported_task_preserves_model_fallback_contract(submission_runtime: dict[str, Any]) -> None:
    task = submission_runtime["task_parser"].parse_task("帮我滚动一下页面")
    history = submission_runtime["history_manager"].HistoryManager()
    screen_state = submission_runtime["screen_state"]
    snapshot = screen_state.recognize_screen_state(task, history)

    assert screen_state.supports_deterministic_flow(task) is False
    assert snapshot.reason == "unsupported_task"
    assert submission_runtime["workflow_graph"].next_action(task, snapshot) is None

    agent = submission_runtime["agent"].Agent()
    agent_input = submission_runtime["agent_base"].AgentInput
    agent._call_api = _scroll_response
    step1 = agent.act(agent_input(instruction="帮我滚动一下页面", current_image=_image(), step_count=1))

    assert (step1.action, step1.parameters) == (
        "SCROLL",
        {"start_point": [500, 800], "end_point": [500, 300]},
    )



def test_submission_completion_policy_is_snapshot_aware(submission_runtime: dict[str, Any]) -> None:
    completion_policy = submission_runtime["completion_policy"]
    screen_state = submission_runtime["screen_state"]
    task_info = submission_runtime["task_parser"].TaskInfo

    video_task = task_info(
        instruction="在腾讯视频搜索庆余年",
        app_name="腾讯视频",
        task_type="video_search",
    )
    detail_snapshot = screen_state.ScreenStateSnapshot(
        screen_state.ScreenState.DETAIL_PAGE,
        None,
        "CLICK",
        "first_result",
        "result_opened",
    )
    pending_task = task_info(
        instruction="在腾讯视频搜索庆余年",
        app_name="腾讯视频",
        task_type="video_search",
        type_queue=["庆余年"],
    )
    pending_snapshot = screen_state.ScreenStateSnapshot(
        screen_state.ScreenState.DETAIL_PAGE,
        "庆余年",
        "CLICK",
        "first_result",
        "result_opened",
    )

    assert completion_policy.should_complete_from_state(video_task, detail_snapshot) is True
    assert completion_policy.should_force_complete(
        video_task,
        5,
        "CLICK",
        "COMPLETE",
        ["TYPE", "CLICK"],
        snapshot=detail_snapshot,
    ) is True
    assert completion_policy.should_complete_from_state(pending_task, pending_snapshot) is False



def test_submission_profile_backed_anchors_match_profiles(submission_runtime: dict[str, Any]) -> None:
    grounder = submission_runtime["grounder"]
    grounder.clear_profile_cache()

    assert grounder.get_anchor("爱奇艺", "search_entry") == [835, 46]
    assert grounder.get_anchor("抖音", "search_entry") == [898, 922]
    assert grounder.get_anchor("去哪儿旅行", "search_button") == [494, 611]
    assert grounder.has_distinct_control("爱奇艺", "search_entry", "search_input") is True
