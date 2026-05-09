"""Profile-backed semantic grounding helpers."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Optional

PROFILE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "profiles")

DEFAULT_CONTROLS: dict[str, dict[str, Any]] = {
    "search_entry": {
        "aliases": ["搜索", "放大镜", "搜索入口"],
        "preferred_region": "top",
        "fallback_point": [500, 120],
        "tolerance": 60,
    },
    "search_input": {
        "aliases": ["搜索框", "输入框"],
        "preferred_region": "top",
        "fallback_point": [500, 100],
        "tolerance": 80,
    },
    "search_bar": {
        "aliases": ["顶部搜索栏", "搜索栏"],
        "preferred_region": "top",
        "fallback_point": [500, 165],
        "tolerance": 80,
    },
    "first_result": {
        "aliases": ["第一个结果", "结果第一项"],
        "preferred_region": "upper_middle",
        "fallback_point": [500, 260],
        "tolerance": 100,
    },
    "comment_entry": {
        "aliases": ["评论区", "评论框"],
        "preferred_region": "bottom",
        "fallback_point": [500, 930],
        "tolerance": 120,
    },
    "comment_submit": {
        "aliases": ["发送", "发布"],
        "preferred_region": "bottom_right",
        "fallback_point": [930, 930],
        "tolerance": 100,
    },
    "flow_entry": {
        "aliases": ["流程入口"],
        "preferred_region": "upper_middle",
        "fallback_point": [500, 220],
        "tolerance": 80,
    },
    "depart_field": {
        "aliases": ["出发地"],
        "preferred_region": "upper_middle",
        "fallback_point": [500, 220],
        "tolerance": 80,
    },
    "destination_field": {
        "aliases": ["目的地"],
        "preferred_region": "upper_middle",
        "fallback_point": [741, 290],
        "tolerance": 80,
    },
    "date_entry": {
        "aliases": ["日期入口", "日期选择"],
        "preferred_region": "upper_middle",
        "fallback_point": [277, 361],
        "tolerance": 80,
    },
    "date_option": {
        "aliases": ["日期选项", "日期"],
        "preferred_region": "upper_middle",
        "fallback_point": [902, 303],
        "tolerance": 100,
    },
    "search_button": {
        "aliases": ["搜索按钮", "查询按钮"],
        "preferred_region": "lower_middle",
        "fallback_point": [494, 611],
        "tolerance": 100,
    },
}

LEGACY_APP_PROFILES: dict[str, dict[str, Any]] = {
    "去哪儿旅行": {
        "workflow_family": "travel",
        "tip": "去哪儿旅行：点出发地→点顶部搜索栏→输入并选第一个结果→点目的地→点顶部搜索栏→输入并选第一个结果",
        "controls": {
            "search_entry": {"fallback_point": [500, 100]},
            "search_input": {"fallback_point": [500, 100]},
            "search_bar": {"fallback_point": [500, 165]},
            "flow_entry": {"fallback_point": [500, 220]},
            "depart_field": {"fallback_point": [252, 291]},
            "destination_field": {"fallback_point": [741, 290]},
            "first_result": {"fallback_point": [500, 180]},
            "date_entry": {"fallback_point": [277, 361]},
            "date_option": {"fallback_point": [902, 303]},
            "search_button": {"fallback_point": [494, 611]},
        },
    },
    "百度地图": {
        "workflow_family": "flow",
        "tip": "百度地图打车：进打车→输起点→选第一个→输终点→选第一个→确认叫车",
        "controls": {
            "search_entry": {"fallback_point": [500, 100]},
            "search_input": {"fallback_point": [500, 100]},
            "flow_entry": {"fallback_point": [500, 220]},
        },
    },
    "美团": {
        "workflow_family": "flow",
        "tip": "美团任务流程：进外卖→搜店铺→进店铺→选商品→加购物车→去结算→默认地址",
        "controls": {
            "search_entry": {"fallback_point": [500, 120]},
            "search_input": {"fallback_point": [500, 120]},
            "flow_entry": {"fallback_point": [500, 260]},
        },
    },
}


@dataclass(frozen=True)
class ControlSpec:
    name: str
    aliases: tuple[str, ...]
    preferred_region: str
    fallback_point: tuple[int, int]
    tolerance: int


@dataclass(frozen=True)
class GroundedAction:
    action: str
    parameters: dict[str, Any]


_PROFILE_CACHE: Optional[dict[str, dict[str, Any]]] = None


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        existing = merged.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            merged[key] = _deep_merge(existing, value)
        else:
            merged[key] = value
    return merged


def _load_profile_document(file_path: str) -> dict[str, Any]:
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read().strip()
    if not content:
        return {}
    return json.loads(content)


def _load_profiles() -> dict[str, dict[str, Any]]:
    profiles = {name: dict(profile) for name, profile in LEGACY_APP_PROFILES.items()}
    if not os.path.isdir(PROFILE_DIR):
        return profiles

    for file_name in sorted(os.listdir(PROFILE_DIR)):
        if not file_name.endswith(".yaml"):
            continue
        file_path = os.path.join(PROFILE_DIR, file_name)
        document = _load_profile_document(file_path)
        defaults = document.get("defaults")
        if isinstance(defaults, dict):
            for app_name, profile in document.get("apps", {}).items():
                profiles[app_name] = _deep_merge(defaults, profile)
            continue

        app_name = document.get("app_name")
        if isinstance(app_name, str) and app_name:
            profiles[app_name] = _deep_merge(profiles.get(app_name, {}), document)

    return profiles


def _get_profiles() -> dict[str, dict[str, Any]]:
    global _PROFILE_CACHE
    if _PROFILE_CACHE is None:
        _PROFILE_CACHE = _load_profiles()
    return _PROFILE_CACHE


def clear_profile_cache() -> None:
    global _PROFILE_CACHE
    _PROFILE_CACHE = None


def get_app_profile(app_name: str) -> dict[str, Any]:
    return dict(_get_profiles().get(app_name, {}))


def get_app_tip(app_name: str) -> str:
    profile = get_app_profile(app_name)
    tip = profile.get("tip")
    if isinstance(tip, str):
        return tip
    return ""


def get_workflow_family(app_name: str) -> str:
    profile = get_app_profile(app_name)
    workflow_family = profile.get("workflow_family")
    if isinstance(workflow_family, str):
        return workflow_family
    return ""


def get_control_spec(app_name: str, control_name: str) -> Optional[ControlSpec]:
    profile = get_app_profile(app_name)
    controls = profile.get("controls") if isinstance(profile.get("controls"), dict) else {}
    raw = controls.get(control_name)
    default_raw = DEFAULT_CONTROLS.get(control_name)
    if not isinstance(raw, dict):
        if default_raw is None:
            return None
        raw = default_raw

    aliases = raw.get("aliases")
    if not isinstance(aliases, list):
        aliases = default_raw.get("aliases", []) if isinstance(default_raw, dict) else []

    preferred_region = raw.get("preferred_region")
    if not isinstance(preferred_region, str):
        preferred_region = default_raw.get("preferred_region", "top") if isinstance(default_raw, dict) else "top"

    fallback_point = raw.get("fallback_point")
    if not isinstance(fallback_point, list) or len(fallback_point) < 2:
        fallback_point = default_raw.get("fallback_point", [500, 120]) if isinstance(default_raw, dict) else [500, 120]

    tolerance = raw.get("tolerance")
    if not isinstance(tolerance, int):
        tolerance = default_raw.get("tolerance", 60) if isinstance(default_raw, dict) else 60

    return ControlSpec(
        name=control_name,
        aliases=tuple(str(alias) for alias in aliases),
        preferred_region=preferred_region,
        fallback_point=(int(fallback_point[0]), int(fallback_point[1])),
        tolerance=tolerance,
    )


def get_available_controls(app_name: str) -> list[str]:
    profile = get_app_profile(app_name)
    controls = profile.get("controls") if isinstance(profile.get("controls"), dict) else {}
    if controls:
        return sorted(set(DEFAULT_CONTROLS) | set(controls))
    return sorted(DEFAULT_CONTROLS)


def get_anchor(app_name: str, control_name: str, default: Optional[list[int]] = None) -> Optional[list[int]]:
    profile = get_app_profile(app_name)
    controls = profile.get("controls") if isinstance(profile.get("controls"), dict) else {}
    raw = controls.get(control_name)
    if isinstance(raw, dict):
        fallback_point = raw.get("fallback_point")
        if isinstance(fallback_point, list) and len(fallback_point) >= 2:
            return [int(fallback_point[0]), int(fallback_point[1])]
    if default is not None:
        return list(default)
    default_spec = DEFAULT_CONTROLS.get(control_name)
    if not isinstance(default_spec, dict):
        return None
    fallback_point = default_spec.get("fallback_point")
    if not isinstance(fallback_point, list) or len(fallback_point) < 2:
        return None
    return [int(fallback_point[0]), int(fallback_point[1])]


def identify_control(app_name: str, point: Optional[list[int]], candidate_names: Optional[list[str]] = None) -> Optional[str]:
    if not isinstance(point, list) or len(point) < 2:
        return None
    control_names = candidate_names or get_available_controls(app_name)
    best_match: Optional[str] = None
    best_distance: Optional[int] = None
    for control_name in control_names:
        spec = get_control_spec(app_name, control_name)
        if spec is None:
            continue
        delta_x = abs(point[0] - spec.fallback_point[0])
        delta_y = abs(point[1] - spec.fallback_point[1])
        if delta_x > spec.tolerance or delta_y > spec.tolerance:
            continue
        distance = delta_x + delta_y
        if best_distance is None or distance < best_distance:
            best_match = control_name
            best_distance = distance
    return best_match


def has_distinct_control(app_name: str, first_control: str, second_control: str) -> bool:
    first_anchor = get_anchor(app_name, first_control)
    second_anchor = get_anchor(app_name, second_control)
    if first_anchor is None or second_anchor is None:
        return False
    return first_anchor != second_anchor


def ground_action(action: str, parameters: dict[str, Any], app_name: str, pending_text: Optional[str] = None) -> GroundedAction:
    resolved_parameters = dict(parameters)
    control_name = resolved_parameters.pop("control", None)
    if action == "CLICK" and isinstance(control_name, str):
        point = get_anchor(app_name, control_name)
        if point is not None:
            resolved_parameters["point"] = point
    if action == "TYPE" and resolved_parameters.get("text") == "__PENDING__":
        resolved_parameters["text"] = pending_text or ""
    return GroundedAction(action=action, parameters=resolved_parameters)
