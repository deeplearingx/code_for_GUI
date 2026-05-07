"""动作解析模块 - 多级降级解析模型输出为(action, parameters)"""

import json
import re
from typing import Optional, Tuple, Dict, Any


def _extract_json_bracket_balanced(text: str) -> Optional[Dict[str, Any]]:
    """用栈匹配大括号提取JSON，支持嵌套"""
    start = text.find("{")
    if start == -1:
        return None
    stack = []
    for i in range(start, len(text)):
        if text[i] == "{":
            stack.append(i)
        elif text[i] == "}":
            if not stack:
                continue
            open_pos = stack.pop()
            if not stack:
                candidate = text[open_pos:i + 1]
                try:
                    return json.loads(candidate)
                except (json.JSONDecodeError, ValueError):
                    continue
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


def _parse_action_as_key(text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """解析 {"CLICK": {"point": [x,y]}} / {"TYPE": {"text": "..."}} 等格式"""
    for action_name in ("CLICK", "TYPE", "SCROLL", "OPEN", "COMPLETE"):
        pattern = rf'{{"{action_name}"\s*:\s*(\{{[^}}]*\}})}}'
        m = re.search(pattern, text)
        if m:
            try:
                inner = json.loads(m.group(1))
                return (action_name, inner)
            except (json.JSONDecodeError, ValueError):
                fixed = re.sub(r'\[(\d+)\s+(\d+)\]', r'[\1, \2]', m.group(1))
                try:
                    inner = json.loads(fixed)
                    return (action_name, inner)
                except (json.JSONDecodeError, ValueError):
                    pass
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
    """解析 CLICK(point=[x,y]) / COMPLETE{} 函数调用格式"""
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
    m2 = re.search(r'(COMPLETE)\s*\{\s*\}', text, re.IGNORECASE)
    if m2:
        return ("COMPLETE", {})
    return None


def _parse_point_tag(text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """解析 <point>x y</point> 格式"""
    m = re.search(r"<point>(\d+)\s+(\d+)</point>", text)
    if m:
        return ("CLICK", {"point": [int(m.group(1)), int(m.group(2))]})
    return None


def parse(raw_text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
    """多级降级解析模型输出，失败返回None"""
    raw = raw_text.strip()
    if not raw:
        return None

    # 1. 直接JSON
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict) and "action" in obj:
            action = obj["action"].upper()
            params = obj.get("parameters", {})
            if not isinstance(params, dict):
                params = {}
            return (action, params)
    except (json.JSONDecodeError, ValueError):
        pass

    # 2. 括号平衡提取JSON
    obj = _extract_json_bracket_balanced(raw)
    if obj and isinstance(obj, dict) and "action" in obj:
        action = obj["action"].upper()
        params = obj.get("parameters", {})
        if not isinstance(params, dict):
            params = {}
        return (action, params)

    # 3. {"ACTION": {params}} 格式（doubao常见）
    result = _parse_action_as_key(raw)
    if result:
        return result

    # 4. ACTION: {json} 格式（doubao常见）
    result = _parse_action_colon_json(raw)
    if result:
        return result

    # 5. ACTION(params) 函数调用格式 / COMPLETE{}
    result = _parse_func_call(raw)
    if result:
        return result

    # 6. Action行格式
    result = _parse_action_line(raw)
    if result:
        return result

    # 7-10. 原始格式（CLICK/TYPE/OPEN/SCROLL）
    result = _parse_raw_format(raw)
    if result:
        return result

    # 11. <point>标签
    result = _parse_point_tag(raw)
    if result:
        return result

    # 12. 全部失败
    return None
