"""
工具函数模块

此模块提供一些常用的工具函数，供选手在实现 Agent 时使用。
"""

from .image_utils import encode_image_to_base64, decode_base64_to_image
from .task_parser import parse_task, TaskInfo
from .action_parser import parse as parse_action
from .action_validator import validate as validate_action, ValidationResult
from .prompt_builder import build_messages, build_retry_prompt, get_flow_continue_coord, get_flow_input_coord, get_search_bar_coord, get_travel_field_coord, get_travel_result_coord, get_travel_search_bar_coord
from .history_manager import HistoryManager

__all__ = [
    "encode_image_to_base64",
    "decode_base64_to_image",
    "parse_task",
    "TaskInfo",
    "parse_action",
    "validate_action",
    "ValidationResult",
    "build_messages",
    "build_retry_prompt",
    "get_flow_continue_coord",
    "get_flow_input_coord",
    "get_search_bar_coord",
    "get_travel_field_coord",
    "get_travel_result_coord",
    "get_travel_search_bar_coord",
    "HistoryManager",
]