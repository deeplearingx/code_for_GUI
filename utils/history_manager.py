"""动作历史管理模块 - 轻量摘要、重复检测"""

from typing import Optional, Dict, Any

MAX_HISTORY_STEPS = 10
REPEAT_CLICK_THRESHOLD = 50


class HistoryManager:
    def __init__(self) -> None:
        self._steps: list[str] = []
        self._last_action: Optional[str] = None
        self._last_click_point: Optional[list[int]] = None
        self._repeat_click_count: int = 0

    def reset(self) -> None:
        self._steps = []
        self._last_action = None
        self._last_click_point = None
        self._repeat_click_count = 0

    def add(self, action: str, parameters: Dict[str, Any]) -> None:
        summary = self._format_step(action, parameters)
        self._steps.append(summary)
        if len(self._steps) > MAX_HISTORY_STEPS:
            self._steps = self._steps[-MAX_HISTORY_STEPS:]

        self._last_action = action

        if action == "CLICK" and "point" in parameters:
            new_point = parameters["point"]
            if self._last_click_point is not None:
                dist = (
                    (new_point[0] - self._last_click_point[0]) ** 2
                    + (new_point[1] - self._last_click_point[1]) ** 2
                ) ** 0.5
                if dist < REPEAT_CLICK_THRESHOLD:
                    self._repeat_click_count += 1
                else:
                    self._repeat_click_count = 0
            self._last_click_point = new_point
        else:
            self._repeat_click_count = 0

    def is_stuck(self) -> bool:
        return self._repeat_click_count >= 2

    def get_last_action(self) -> Optional[str]:
        return self._last_action

    def get_recent_actions(self, count: int) -> list[str]:
        if count <= 0:
            return []
        return [step.split("(", 1)[0] for step in self._steps[-count:]]

    def get_summary(self) -> str:
        if not self._steps:
            return ""
        return "\n".join(
            f"步骤{i + 1}: {s}" for i, s in enumerate(self._steps)
        )

    @staticmethod
    def _format_step(action: str, parameters: Dict[str, Any]) -> str:
        if action == "CLICK":
            point = parameters.get("point", [])
            target = parameters.get("target", "")
            if target:
                return f'{action}(point={point}, target="{target}")'
            return f"{action}(point={point})"
        elif action == "TYPE":
            text = parameters.get("text", "")
            return f'{action}(text="{text}")'
        elif action == "SCROLL":
            sp = parameters.get("start_point", [])
            ep = parameters.get("end_point", [])
            return f"{action}(start_point={sp}, end_point={ep})"
        elif action == "OPEN":
            app = parameters.get("app_name", "")
            return f'{action}(app_name="{app}")'
        elif action == "COMPLETE":
            return f"{action}()"
        return f"{action}({parameters})"
