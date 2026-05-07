"""动作校验与修正模块 - 保证输出格式合法，可修正的直接修，不触发重试"""

from dataclasses import dataclass
from typing import Dict, Any, Optional


ACTION_ALIASES: dict[str, str] = {
    "click": "CLICK", "tap": "CLICK", "press": "CLICK",
    "type": "TYPE", "input": "TYPE", "enter": "TYPE",
    "scroll": "SCROLL", "swipe": "SCROLL",
    "open": "OPEN", "launch": "OPEN",
    "complete": "COMPLETE", "done": "COMPLETE", "finish": "COMPLETE",
}

KEY_ALIASES: dict[str, dict[str, str]] = {
    "CLICK": {
        "point": "point", "coord": "point", "coords": "point",
        "position": "point", "pos": "point", "xy": "point",
        "location": "point", "coordinate": "point",
    },
    "TYPE": {
        "text": "text", "content": "text", "input": "text",
        "value": "text", "message": "text", "query": "text",
    },
    "OPEN": {
        "app_name": "app_name", "app": "app_name", "name": "app_name",
        "application": "app_name", "package": "app_name",
    },
    "SCROLL": {},
    "COMPLETE": {},
}

VALID_ACTIONS = {"CLICK", "TYPE", "SCROLL", "OPEN", "COMPLETE"}


@dataclass
class ValidationResult:
    action: str
    parameters: Dict[str, Any]
    ok: bool
    need_retry: bool = False
    retry_reason: str = ""


def normalize_point(p: Any) -> list[int]:
    """归一化坐标到[0, 1000]，兼容0~1自动放大"""
    if not isinstance(p, (list, tuple)) or len(p) < 2:
        return [500, 500]
    x, y = float(p[0]), float(p[1])
    if 0 <= x <= 1 and 0 <= y <= 1:
        x *= 1000
        y *= 1000
    return [max(0, min(1000, int(round(x)))), max(0, min(1000, int(round(y))))]


def _standardize_action(action: str) -> str:
    return ACTION_ALIASES.get(action.lower(), action.upper())


def _standardize_keys(action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    alias_map = KEY_ALIASES.get(action, {})
    new_params: Dict[str, Any] = {}
    for key, value in params.items():
        std_key = alias_map.get(key, key)
        new_params[std_key] = value
    return new_params


def _validate_click(params: Dict[str, Any]) -> Dict[str, Any]:
    if "point" not in params:
        for key in ("coord", "coords", "position", "pos", "xy", "location", "coordinate"):
            if key in params:
                params["point"] = params.pop(key)
                break
    if "point" in params:
        params["point"] = normalize_point(params["point"])
    else:
        params["point"] = [500, 500]
    params = {"point": params["point"]}
    return params


def _validate_type(params: Dict[str, Any], task: Any) -> Dict[str, Any]:
    if task is not None and hasattr(task, "peek_pending_text"):
        next_text = task.peek_pending_text()
        if next_text:
            return {"text": next_text}
    text = params.get("text", "")
    if isinstance(text, list):
        text = str(text[0]) if text else ""
    return {"text": str(text)}


def _validate_scroll(params: Dict[str, Any]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    if "start_point" in params:
        result["start_point"] = normalize_point(params["start_point"])
    else:
        result["start_point"] = [500, 800]
    if "end_point" in params:
        result["end_point"] = normalize_point(params["end_point"])
    else:
        result["end_point"] = [500, 300]
    return result


def _validate_open(params: Dict[str, Any], task: Any) -> Dict[str, Any]:
    if task is not None and hasattr(task, "app_name") and task.app_name:
        return {"app_name": task.app_name}
    app_name = params.get("app_name", "")
    if isinstance(app_name, list):
        app_name = str(app_name[0]) if app_name else ""
    return {"app_name": str(app_name)}


def _check_complete_protection(
    step_count: int, task: Any, last_action: Optional[str]
) -> Optional[str]:
    """COMPLETE防早退保护，返回拒绝原因，None表示允许"""
    if step_count < 4:
        return f"步骤数过少({step_count}<4)"
    if task is not None and hasattr(task, "has_pending_text") and task.has_pending_text():
        return "还有待输入内容"
    if last_action == "OPEN":
        return "上一步是OPEN"
    if last_action == "TYPE":
        return "上一步是TYPE"
    return None


def _check_type_protection(
    action: str, task: Any, last_action: Optional[str]
) -> Optional[str]:
    """TYPE防错保护：需要先点击输入框才能TYPE，返回拒绝原因，None表示允许"""
    if action != "TYPE":
        return None
    # 上一步是OPEN → 应该先点搜索框/输入框
    if last_action == "OPEN":
        return "上一步是OPEN，请先点击搜索框或输入框，再输入文字"
    # 上一步是TYPE → 需要先点击下一个输入框（如目的地）
    if last_action == "TYPE":
        return "上一步是TYPE，请先点击下一个输入框，再输入文字"
    # 上一步是SCROLL → 可能还没定位到输入框
    if last_action == "SCROLL":
        return "上一步是SCROLL，请先点击搜索框或输入框，再输入文字"
    return None


def validate(
    action: str,
    params: Dict[str, Any],
    task: Any = None,
    step_count: int = 1,
    last_action: Optional[str] = None,
) -> ValidationResult:
    """校验修正动作，可修正的直接修，COMPLETE防早退触发重试"""
    # Action标准化
    action = _standardize_action(action)

    # Key标准化
    params = _standardize_keys(action, params)

    # TYPE防错保护（优先于类型校验，避免TYPE覆盖正确文本后返回）
    type_reject = _check_type_protection(action, task, last_action)
    if type_reject:
        return ValidationResult(
            action=action,
            parameters=params,
            ok=False,
            need_retry=True,
            retry_reason=f"TYPE被拒绝：{type_reject}",
        )

    # 按动作类型校验
    if action == "CLICK":
        params = _validate_click(params)
    elif action == "TYPE":
        params = _validate_type(params, task)
    elif action == "SCROLL":
        params = _validate_scroll(params)
    elif action == "OPEN":
        params = _validate_open(params, task)
    elif action == "COMPLETE":
        reject_reason = _check_complete_protection(step_count, task, last_action)
        if reject_reason:
            return ValidationResult(
                action="COMPLETE",
                parameters={},
                ok=False,
                need_retry=True,
                retry_reason=f"COMPLETE被拒绝：{reject_reason}。请继续执行任务，不要提前完成。",
            )
        params = {}
    else:
        return ValidationResult(
            action=action,
            parameters=params,
            ok=False,
            need_retry=True,
            retry_reason=f"未知动作: {action}",
        )

    return ValidationResult(action=action, parameters=params, ok=True)
