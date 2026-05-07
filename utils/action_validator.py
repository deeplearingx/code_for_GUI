"""Action validation and correction module - retry on missing params, no silent defaults"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple


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
        "location": "point", "coordinate": "point", "coordinates": "point",
        "target": "point", "click_position": "point", "center": "point",
        "spot": "point", "place": "point",
    },
    "TYPE": {
        "text": "text", "content": "text", "input": "text",
        "value": "text", "message": "text", "query": "text",
    },
    "OPEN": {
        "app_name": "app_name", "app": "app_name", "name": "app_name",
        "application": "app_name", "package": "app_name",
    },
    "SCROLL": {
        "start_point": "start_point", "start": "start_point",
        "end_point": "end_point", "end": "end_point",
        "from_point": "start_point", "to_point": "end_point",
    },
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


def normalize_point(p: Any) -> Optional[list[int]]:
    """Normalize coordinates to [0, 1000], auto-scale 0~1. Returns None on invalid input."""
    if not isinstance(p, (list, tuple)) or len(p) < 2:
        return None
    try:
        x, y = float(p[0]), float(p[1])
    except (TypeError, ValueError):
        return None
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


# -- Helper functions return (params_or_None, error_or_None) --

def _validate_click(params: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if "point" not in params:
        # Try x/y separate fields: {"x": 500, "y": 300}
        if "x" in params and "y" in params:
            try:
                params["point"] = [float(params["x"]), float(params["y"])]
                params.pop("x", None)
                params.pop("y", None)
            except (TypeError, ValueError):
                return None, "CLICK invalid x/y coordinates"
    if "point" not in params:
        for key in ("coord", "coords", "position", "pos", "xy", "location", "coordinate",
                     "coordinates", "target", "click_position", "center", "spot", "place"):
            if key in params:
                params["point"] = params.pop(key)
                break
    if "point" not in params:
        return None, "CLICK missing point parameter"
    point = normalize_point(params["point"])
    if point is None:
        return None, "CLICK invalid coordinates"
    return {"point": point}, None


def _validate_type(params: Dict[str, Any], task: Any) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if task is not None and hasattr(task, "peek_pending_text"):
        next_text = task.peek_pending_text()
        if next_text:
            return {"text": next_text}, None
    text = params.get("text", "")
    if isinstance(text, list):
        text = str(text[0]) if text else ""
    if not text:
        return None, "TYPE missing text content"
    return {"text": str(text)}, None


def _validate_scroll(params: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if "start_point" not in params or "end_point" not in params:
        return None, "SCROLL missing coordinate parameters"
    sp = normalize_point(params["start_point"])
    ep = normalize_point(params["end_point"])
    if sp is None or ep is None:
        return None, "SCROLL invalid coordinates"
    return {"start_point": sp, "end_point": ep}, None


def _validate_open(params: Dict[str, Any], task: Any) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if task is not None and hasattr(task, "app_name") and task.app_name:
        return {"app_name": task.app_name}, None
    app_name = params.get("app_name", "")
    if isinstance(app_name, list):
        app_name = str(app_name[0]) if app_name else ""
    if not app_name:
        return None, "OPEN missing app_name"
    return {"app_name": str(app_name)}, None


def _check_complete_protection(
    step_count: int, task: Any, last_action: Optional[str]
) -> Optional[str]:
    """COMPLETE early-exit protection. Returns rejection reason, None means allow."""
    if step_count < 4:
        return f"step count too low ({step_count}<4)"
    if task is not None and hasattr(task, "has_pending_text") and task.has_pending_text():
        return "pending text content remains"
    if last_action == "OPEN":
        return "last action was OPEN"
    # Removed: TYPE rejection — after typing search term or comment, task may be done
    return None


def _check_type_protection(
    action: str, task: Any, last_action: Optional[str]
) -> Optional[str]:
    """TYPE error protection: reject TYPE after OPEN or TYPE, allow after SCROLL."""
    if action != "TYPE":
        return None
    if last_action == "OPEN":
        return "last action was OPEN, click search/input box first"
    if last_action == "TYPE":
        return "last action was TYPE, click next input box or send button first"
    # Removed: SCROLL rejection - let model decide if input box is visible
    return None


def validate(
    action: str,
    params: Dict[str, Any],
    task: Any = None,
    step_count: int = 1,
    last_action: Optional[str] = None,
) -> ValidationResult:
    """Validate and correct action. Retry on missing/invalid params."""
    # Action standardization
    action = _standardize_action(action)

    # Key standardization
    params = _standardize_keys(action, params)

    # TYPE protection (before type validation to avoid overwriting correct text)
    type_reject = _check_type_protection(action, task, last_action)
    if type_reject:
        return ValidationResult(
            action=action,
            parameters=params,
            ok=False,
            need_retry=True,
            retry_reason=f"TYPE rejected: {type_reject}",
        )

    # Per-action validation
    if action == "CLICK":
        params, err = _validate_click(params)
        if err:
            return ValidationResult(action="CLICK", parameters={}, ok=False,
                                    need_retry=True, retry_reason=err)
    elif action == "TYPE":
        params, err = _validate_type(params, task)
        if err:
            return ValidationResult(action="TYPE", parameters={}, ok=False,
                                    need_retry=True, retry_reason=err)
    elif action == "SCROLL":
        params, err = _validate_scroll(params)
        if err:
            return ValidationResult(action="SCROLL", parameters={}, ok=False,
                                    need_retry=True, retry_reason=err)
    elif action == "OPEN":
        params, err = _validate_open(params, task)
        if err:
            return ValidationResult(action="OPEN", parameters={}, ok=False,
                                    need_retry=True, retry_reason=err)
    elif action == "COMPLETE":
        reject_reason = _check_complete_protection(step_count, task, last_action)
        if reject_reason:
            return ValidationResult(
                action="COMPLETE",
                parameters={},
                ok=False,
                need_retry=True,
                retry_reason=f"COMPLETE rejected: {reject_reason}",
            )
        params = {}
    else:
        return ValidationResult(
            action=action,
            parameters=params,
            ok=False,
            need_retry=True,
            retry_reason=f"unknown action: {action}",
        )

    return ValidationResult(action=action, parameters=params, ok=True)
