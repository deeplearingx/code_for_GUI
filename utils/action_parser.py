"""动作解析模块 - 多级降级解析模型输出为(action, parameters)"""

import json
import re
from typing import Optional, Tuple, Dict, Any


VALID_ACTIONS = {"CLICK", "TYPE", "SCROLL", "OPEN", "COMPLETE"}

_THINK_OPEN = re.compile(r"<think[^>]*>.*?</think>", re.DOTALL | re.IGNORECASE)
_THINK_CLOSE = re.compile(r"</think>", re.IGNORECASE)
_MARKDOWN_BLOCK = re.compile(r"```(?:json)?\s*")
_MARKDOWN_CLOSE = re.compile(r"```\s*")
_DOUBLE_BRACE_PREFIX = re.compile(
    r"^(CLICK|TYPE|SCROLL|OPEN|COMPLETE)\s*:\s*\{\{",
    re.IGNORECASE,
)
_DOUBLE_BRACE_SUFFIX = re.compile(r"\}\}\s*$")
_MISSING_COMMA_2 = re.compile(r"\[(\d+)\s+(\d+)\]")
_MISSING_COMMA_4 = re.compile(r"\[(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\]")
_TRAIL_COMMA_OBJ = re.compile(r",\s*}")
_TRAIL_COMMA_ARR = re.compile(r",\s*]")
_DOUBLE_BRACE_OBJECT = re.compile(r"^\s*\{\{([\s\S]*)\}\}\s*$")


def _normalize_nested_double_brace_object(text: str) -> str:
    stripped = text.strip()
    if not _DOUBLE_BRACE_OBJECT.match(stripped):
        return text

    normalized = stripped[1:-1]
    normalized = re.sub(r'("parameters"\s*:\s*)\{\{', r'\1{', normalized, count=1)
    normalized = re.sub(r'\}\}(\s*\})\s*$', r'}\1', normalized, count=1)
    return normalized


def _pre_clean(raw: str) -> str:
    """清洗模型输出：去标签、去markdown、修格式"""
    text = raw

    # 去掉 <think>...</think> 和 </think> 标签
    text = _THINK_OPEN.sub("", text)
    text = _THINK_CLOSE.sub("", text)

    # 去掉 markdown code block
    text = _MARKDOWN_BLOCK.sub("", text)
    text = _MARKDOWN_CLOSE.sub("", text)

    text = _normalize_nested_double_brace_object(text)

    # 去掉动作前缀的双花括号（只在前缀匹配时才处理后缀，避免误伤嵌套JSON的}}）
    if _DOUBLE_BRACE_PREFIX.search(text):
        text = _DOUBLE_BRACE_PREFIX.sub(r"\1: {", text)
        text = _DOUBLE_BRACE_SUFFIX.sub(r"}", text)

    # 整对象双花括号：{{"action": ...}} -> {"action": ...}
    m = _DOUBLE_BRACE_OBJECT.match(text)
    if m:
        text = "{" + m.group(1).strip() + "}"

    # 修复 [371 73] -> [371, 73]（数字间空格缺逗号）
    text = _MISSING_COMMA_4.sub(r"[\1, \2, \3, \4]", text)
    text = _MISSING_COMMA_2.sub(r"[\1, \2]", text)

    # 去掉尾逗号
    text = _TRAIL_COMMA_OBJ.sub("}", text)
    text = _TRAIL_COMMA_ARR.sub("]", text)

    return text


def _parse_embedded_action_value(action_text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """Parse embedded action text like CLICK(point=[[354, 71]]) inside an action field."""
    text = str(action_text).strip()

    m = re.search(
        r"(CLICK)\s*\(\s*point\s*=\s*\[\[?\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*\]?\]?",
        text,
        re.IGNORECASE,
    )
    if m:
        return ("CLICK", {"point": [int(float(m.group(2))), int(float(m.group(3)))]})

    m = re.search(
        r"(TYPE)\s*\(\s*text\s*=\s*['\"]([^'\"]+)['\"]",
        text,
        re.IGNORECASE,
    )
    if m:
        return ("TYPE", {"text": m.group(2)})

    m = re.search(r'(CLICK)\s*\[\[(\d+)\s*,\s*(\d+)\]\]', text, re.IGNORECASE)
    if m:
        return (m.group(1).upper(), {"point": [int(m.group(2)), int(m.group(3))]})

    return None


def _parse_standard_json_obj(obj: Dict[str, Any]) -> Optional[Tuple[str, Dict[str, Any]]]:
    """解析标准格式 {"action": "CLICK", "parameters": {...}}"""
    if not isinstance(obj, dict):
        return None
    if "action" not in obj:
        return None
    action = str(obj["action"]).upper()
    if action not in VALID_ACTIONS:
        extracted = _parse_embedded_action_value(str(obj["action"]))
        if extracted:
            obj_params = obj.get("parameters", {})
            if isinstance(obj_params, dict):
                for k, v in obj_params.items():
                    if k not in extracted[1]:
                        extracted[1][k] = v
            return extracted
        return None
    params = obj.get("parameters", {})
    if not isinstance(params, dict):
        # Parameters is a list/array — treat as coordinates for CLICK, text for TYPE
        if isinstance(params, list):
            if action == "CLICK" and len(params) >= 2:
                try:
                    return (action, {"point": [int(float(v)) for v in params[:2]]})
                except (TypeError, ValueError):
                    return (action, {"point": params[:2]})
            elif action == "TYPE" and params:
                return (action, {"text": str(params[0])})
            elif action == "OPEN" and params:
                return (action, {"app_name": str(params[0])})
            elif action == "SCROLL" and len(params) >= 4:
                try:
                    return (action, {"start_point": [int(float(v)) for v in params[:2]],
                                     "end_point": [int(float(v)) for v in params[2:4]]})
                except (TypeError, ValueError):
                    pass
        params = {}
    return (action, params)


def _parse_action_key_obj(obj: Dict[str, Any]) -> Optional[Tuple[str, Dict[str, Any]]]:
    """解析 action-as-key 格式 {"CLICK": {"point": [x,y]}} / {"CLICK": [x,y]}"""
    if not isinstance(obj, dict):
        return None
    for key in obj:
        action = key.upper()
        if action not in VALID_ACTIONS:
            continue
        value = obj[key]
        if isinstance(value, dict):
            if "parameters" in value and isinstance(value["parameters"], dict):
                return (action, value["parameters"])
            return (action, value)
        elif isinstance(value, list):
            if action == "CLICK" and len(value) == 2:
                try:
                    return (action, {"point": [int(float(v)) for v in value]})
                except (TypeError, ValueError):
                    return (action, {"point": value})
            elif action == "CLICK" and len(value) >= 2:
                return (action, {"point": value[:2]})
            elif action == "COMPLETE":
                return (action, {})
        elif value == {} or (isinstance(value, str) and not value):
            return (action, {})
    return None


def _load_json_candidate(candidate: str) -> Optional[Dict[str, Any]]:
    try:
        obj = json.loads(candidate)
        if isinstance(obj, dict):
            return obj
    except (json.JSONDecodeError, ValueError):
        pass

    normalized = _normalize_nested_double_brace_object(candidate)
    if normalized == candidate:
        return None

    try:
        obj = json.loads(normalized)
        if isinstance(obj, dict):
            return obj
    except (json.JSONDecodeError, ValueError):
        pass
    return None



def _extract_json_bracket_balanced(text: str) -> Optional[Dict[str, Any]]:
    """用栈匹配大括号提取JSON，支持嵌套，string-aware"""
    start = text.find("{")
    if start == -1:
        return None
    stack = []
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            if in_string:
                escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            stack.append(i)
        elif ch == "}":
            if not stack:
                continue
            open_pos = stack.pop()
            if not stack:
                candidate = text[open_pos:i + 1]
                obj = _load_json_candidate(candidate)
                if obj is not None:
                    return obj
    return None


def _parse_action_colon_json(text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """解析 CLICK: {"point": [x,y]} / TYPE: {"text": "..."} 格式"""
    m = re.search(r'(CLICK|TYPE|SCROLL|OPEN|COMPLETE)\s*:\s*(\{.+\})', text, re.IGNORECASE)
    if m:
        action = m.group(1).upper()
        try:
            params = json.loads(m.group(2))
            return (action, params)
        except (json.JSONDecodeError, ValueError):
            pass
    return None


def _parse_func_call(text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """解析 CLICK(point=[x,y]) / COMPLETE{} / TYPE{"text": "..."} 函数调用格式"""
    # 标准函数调用：ACTION(params)
    m = re.search(r'(CLICK|TYPE|SCROLL|OPEN|COMPLETE)\s*\((.+?)\)', text, re.IGNORECASE)
    if m:
        action = m.group(1).upper()
        params_str = m.group(2)
        params: Dict[str, Any] = {}
        for pair in re.finditer(r'(\w+)=\[([^\]]*)\]', params_str):
            key = pair.group(1)
            vals = pair.group(2).split(",")
            params[key] = [int(float(v.strip())) for v in vals]
        for pair in re.finditer(r'(\w+)="([^"]*)"', params_str):
            params[pair.group(1)] = pair.group(2)
        for pair in re.finditer(r"(\w+)='([^']*)'", params_str):
            params[pair.group(1)] = pair.group(2)
        return (action, params)

    # COMPLETE 空花括号
    m3 = re.search(r'(COMPLETE)\s*\{\s*\}', text, re.IGNORECASE)
    if m3:
        return ("COMPLETE", {})

    # 无括号格式：TYPE{"text": "..."} / CLICK{"point": [x,y]}
    m2 = re.search(
        r'(CLICK|TYPE|SCROLL|OPEN|COMPLETE)\s*\{(\{.*\}|.*?)\}',
        text,
        re.IGNORECASE,
    )
    if m2:
        action = m2.group(1).upper()
        inner = m2.group(2).strip()
        if not inner:
            return (action, {})
        try:
            params = json.loads("{" + inner + "}")
            return (action, params)
        except (json.JSONDecodeError, ValueError):
            pass

    return None


def _parse_action_line(text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """解析 Action: click(point=[x,y]) 格式"""
    m = re.search(r"Action:\s*(\w+)\((.+)\)", text, re.IGNORECASE)
    if not m:
        return None
    action = m.group(1).upper()
    params_str = m.group(2)

    params: Dict[str, Any] = {}
    for pair in re.finditer(r"(\w+)=\[([^\]]*)\]", params_str):
        key = pair.group(1)
        vals = pair.group(2).split(",")
        if len(vals) == 2:
            try:
                params[key] = [int(float(v.strip())) for v in vals]
            except ValueError:
                params[key] = [float(v.strip()) for v in vals]
        elif len(vals) == 4:
            try:
                params[key] = [int(float(v.strip())) for v in vals]
            except ValueError:
                params[key] = [float(v.strip()) for v in vals]

    for pair in re.finditer(r"(\w+)='([^']*)'", params_str):
        params[pair.group(1)] = pair.group(2)

    for pair in re.finditer(r'(\w+)="([^"]*)"', params_str):
        params[pair.group(1)] = pair.group(2)

    return (action, params)


def _parse_raw_format(text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """解析 CLICK:[[x,y]] / TYPE:['text'] / OPEN:['app'] / SCROLL:[[x1,y1],[x2,y2]]"""
    patterns: list[Tuple[str, str]] = [
        (r"CLICK:\s*\[\[(\d+)\s*,\s*(\d+)\]\]", "CLICK"),
        (r"SCROLL:\s*\[\[(\d+)\s*,\s*(\d+)\]\s*,\s*\[(\d+)\s*,\s*(\d+)\]\]", "SCROLL"),
        (r"TYPE:\s*\['([^']*)'\]", "TYPE"),
        (r'TYPE:\s*\["([^"]*)"\]', "TYPE"),
        (r"OPEN:\s*\['([^']*)'\]", "OPEN"),
        (r'OPEN:\s*\["([^"]*)"\]', "OPEN"),
    ]

    for pattern, action_name in patterns:
        m = re.search(pattern, text)
        if not m:
            continue
        groups = m.groups()
        if action_name == "CLICK":
            return ("CLICK", {"point": [int(groups[0]), int(groups[1])]})
        elif action_name == "SCROLL":
            return ("SCROLL", {
                "start_point": [int(groups[0]), int(groups[1])],
                "end_point": [int(groups[2]), int(groups[3])]
            })
        elif action_name == "TYPE":
            return ("TYPE", {"text": groups[0]})
        elif action_name == "OPEN":
            return ("OPEN", {"app_name": groups[0]})

    return None


def _parse_point_tag(text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """解析 <point>x y</point> 格式"""
    m = re.search(r"<point>(\d+)\s+(\d+)</point>", text)
    if m:
        return ("CLICK", {"point": [int(m.group(1)), int(m.group(2))]})
    return None


def _try_parse_json_obj(obj: Any) -> Optional[Tuple[str, Dict[str, Any]]]:
    """对已解析的 JSON 对象尝试对象级判断"""
    if not isinstance(obj, dict):
        return None
    parsed = _parse_standard_json_obj(obj)
    if parsed:
        return parsed
    parsed = _parse_action_key_obj(obj)
    if parsed:
        return parsed
    return None


def parse(raw_text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """多级降级解析模型输出，失败返回None"""
    raw = raw_text.strip()
    if not raw:
        return None

    # 0. 预清洗
    clean = _pre_clean(raw)
    clean = clean.strip()
    if not clean:
        return None

    # 1. 直接JSON → 对象级判断
    try:
        obj = json.loads(clean)
        parsed = _try_parse_json_obj(obj)
        if parsed:
            return parsed
    except (json.JSONDecodeError, ValueError):
        pass

    # 2. 括号平衡提取JSON → 对象级判断
    obj = _extract_json_bracket_balanced(clean)
    if obj is not None:
        parsed = _try_parse_json_obj(obj)
        if parsed:
            return parsed

    # 3. ACTION: {json} 格式
    result = _parse_action_colon_json(clean)
    if result:
        return result

    # 4. ACTION(params) / ACTION{} / ACTION{params} 函数调用格式
    result = _parse_func_call(clean)
    if result:
        return result

    # 5. Action行格式
    result = _parse_action_line(clean)
    if result:
        return result

    # 6. 原始格式（CLICK/TYPE/OPEN/SCROLL）
    result = _parse_raw_format(clean)
    if result:
        return result

    # 7. <point>标签
    result = _parse_point_tag(clean)
    if result:
        return result

    # 8. 全部失败
    return None
