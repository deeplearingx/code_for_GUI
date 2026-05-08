"""GUI Agent 实现 - 基于 BaseAgent，规则化OPEN/TYPE，视觉化CLICK，防早退COMPLETE"""

import io
import base64
import logging
from typing import Dict, Any, Optional

from agent_base import BaseAgent, AgentInput, AgentOutput, ACTION_CLICK, ACTION_TYPE, ACTION_SCROLL, ACTION_OPEN, ACTION_COMPLETE
from utils.task_parser import parse_task, TaskInfo
from utils.action_parser import parse as parse_action
from utils.action_validator import validate as validate_action, ValidationResult
from utils.action_policy import correct as correct_action, PolicyDecision
from utils.prompt_builder import build_messages, build_retry_prompt, get_flow_continue_coord, get_search_bar_coord, get_travel_date_confirm_coord, get_travel_date_entry_coord, get_travel_date_option_coord, get_travel_field_coord, get_travel_result_coord, get_travel_search_bar_coord, get_travel_search_button_coord
from utils.history_manager import HistoryManager
from utils.completion_policy import RECENT_ACTION_WINDOW, should_force_complete

logger = logging.getLogger(__name__)

FLOW_TASK_TYPES = {"baidu_map", "meituan", "travel"}
TRAVEL_CLICK_TOLERANCE = 40


def _points_close(point: Optional[list[int]], target: list[int], tolerance: int = TRAVEL_CLICK_TOLERANCE) -> bool:
    if not isinstance(point, list) or len(point) < 2:
        return False
    return abs(point[0] - target[0]) <= tolerance and abs(point[1] - target[1]) <= tolerance



def _travel_date_flow_step(task: Optional[TaskInfo], last_action: Optional[str], last_click_point: Optional[list[int]]) -> Optional[tuple[str, dict]]:
    if task is None or task.task_type != "travel" or task.has_pending_text():
        return None
    if not task.travel_date_hint:
        return None
    date_entry_coord = get_travel_date_entry_coord()
    date_option_coord = get_travel_date_option_coord(task.travel_date_hint)
    search_button_coord = get_travel_search_button_coord()

    if last_action == ACTION_CLICK and _points_close(last_click_point, date_entry_coord):
        return (ACTION_CLICK, {"point": date_option_coord})
    if last_action == ACTION_CLICK and _points_close(last_click_point, date_option_coord):
        return (ACTION_CLICK, {"point": search_button_coord})
    if last_action == ACTION_CLICK and _points_close(last_click_point, search_button_coord):
        return (ACTION_COMPLETE, {})
    if last_action == ACTION_CLICK and _points_close(last_click_point, get_travel_result_coord()):
        return (ACTION_CLICK, {"point": date_entry_coord})
    return None


class Agent(BaseAgent):
    def _initialize(self) -> None:
        self._task: Optional[TaskInfo] = None
        self._history = HistoryManager()
        self._fallback_ready_to_type = False

    def reset(self) -> None:
        self._task = None
        self._history.reset()
        self._fallback_ready_to_type = False

    def _decide_action_policy(self, result: ValidationResult) -> PolicyDecision:
        recent_actions = self._history.get_recent_actions(RECENT_ACTION_WINDOW)
        return correct_action(
            action=result.action,
            params=result.parameters,
            task=self._task,
            last_action=self._history.get_last_action(),
            recent_actions=recent_actions,
            last_click_point=self._history.get_last_click_point(),
        )

    def _apply_action_policy(self, result: ValidationResult, step_count: int) -> ValidationResult:
        decision = self._decide_action_policy(result)
        if not decision.changed:
            return result
        logger.info(
            f"ACTION_POLICY decision changed=True original_action={result.action} "
            f"original_params={result.parameters} corrected_action={decision.action} "
            f"corrected_params={decision.params} reason={decision.reason} confidence={decision.confidence}"
        )
        corrected = validate_action(
            action=decision.action,
            params=decision.params,
            task=self._task,
            step_count=step_count,
            last_action=self._history.get_last_action(),
        )
        if corrected.ok:
            logger.info(
                f"ACTION_POLICY accepted final_action={corrected.action} "
                f"final_params={corrected.parameters} reason={decision.reason}"
            )
            return corrected
        logger.info(
            f"ACTION_POLICY rejected final_action={result.action} final_params={result.parameters} "
            f"reason={decision.reason} confidence={decision.confidence} retry_reason={corrected.retry_reason}"
        )
        return result

    def act(self, input_data: AgentInput) -> AgentOutput:
        step_count = input_data.step_count

        # 首次进入：解析任务
        if self._task is None:
            self._task = parse_task(input_data.instruction)

        # step_count==1 且 app_name存在 → 直接返回OPEN，不调模型
        if step_count == 1 and self._task.app_name:
            action = ACTION_OPEN
            parameters = {"app_name": self._task.app_name}
            self._fallback_ready_to_type = False
            self._history.add(action, parameters)
            return AgentOutput(action=action, parameters=parameters)

        # 构造messages
        image_url = self._encode_image(input_data.current_image)
        history_summary = self._history.get_summary()
        messages = build_messages(
            task=self._task,
            history_summary=history_summary,
            step_count=step_count,
            image_url=image_url,
        )

        # 调用模型
        try:
            response = self._call_api(messages)
        except Exception as e:
            logger.warning(f"API调用失败: {e}")
            action, parameters = self._fallback(input_data)
            if action == ACTION_TYPE and self._task is not None:
                self._task.commit_text()
            self._history.add(action, parameters)
            return AgentOutput(action=action, parameters=parameters)

        # 提取模型输出
        raw_output = ""
        try:
            raw_output = response.choices[0].message.content or ""
        except (AttributeError, IndexError) as e:
            logger.warning(f"提取模型输出失败: {e}")
            action, parameters = self._fallback(input_data)
            if action == ACTION_TYPE and self._task is not None:
                self._task.commit_text()
            self._history.add(action, parameters)
            return AgentOutput(action=action, parameters=parameters)

        # 解析模型输出
        parsed = parse_action(raw_output)
        if parsed is None:
            logger.warning(f"解析失败，原始输出: {raw_output[:200]}")
            return self._retry_or_fallback(input_data, messages, "模型输出无法解析为合法动作")

        action, parameters = parsed
        logger.debug(f"解析结果: action={action}, params={parameters}, 原始输出: {raw_output[:200]}")

        # 校验修正
        last_action = self._history.get_last_action()
        result = validate_action(
            action=action,
            params=parameters,
            task=self._task,
            step_count=step_count,
            last_action=last_action,
        )

        if result.need_retry:
            logger.info(f"校验需重试: {result.retry_reason}")
            return self._retry_or_fallback(input_data, messages, result.retry_reason)

        result = self._apply_action_policy(result, step_count)

        recent_actions = self._history.get_recent_actions(RECENT_ACTION_WINDOW)
        if should_force_complete(self._task, step_count, last_action, result.action, recent_actions):
            self._fallback_ready_to_type = False
            self._history.add(ACTION_COMPLETE, {})
            return AgentOutput(action=ACTION_COMPLETE, parameters={})

        # 重复点击检测
        if result.action == ACTION_CLICK and self._history.is_stuck():
            logger.info("检测到重复点击，追加提示重试")
            return self._retry_or_fallback(
                input_data, messages,
                "你重复点击了几乎相同位置，页面没有变化。重新观察截图，不要重复点击。优先关闭弹窗、点搜索框或滚动。",
            )

        # TYPE commit：只有最终返回TYPE动作时才commit
        if result.action == ACTION_TYPE and self._task is not None:
            self._task.commit_text()

        self._fallback_ready_to_type = False

        # 更新历史
        self._history.add(result.action, result.parameters)

        # 提取usage
        usage = None
        try:
            usage = self.extract_usage_info(response)
        except Exception:
            pass

        return AgentOutput(
            action=result.action,
            parameters=result.parameters,
            raw_output=raw_output,
            usage=usage,
        )

    def _retry_or_fallback(
        self,
        input_data: AgentInput,
        original_messages: list,
        reason: str,
    ) -> AgentOutput:
        """追加严格格式提示，重试一次；仍失败则fallback"""
        retry_prompt = build_retry_prompt(reason)

        # 构造重试messages
        retry_messages = list(original_messages)
        retry_messages.append({
            "role": "user",
            "content": [{"type": "text", "text": retry_prompt}],
        })

        try:
            response = self._call_api(retry_messages)
            raw_output = response.choices[0].message.content or ""

            parsed = parse_action(raw_output)
            if parsed is not None:
                action, parameters = parsed
                last_action = self._history.get_last_action()
                result = validate_action(
                    action=action,
                    params=parameters,
                    task=self._task,
                    step_count=input_data.step_count,
                    last_action=last_action,
                )

                if result.ok:
                    result = self._apply_action_policy(result, input_data.step_count)
                    last_action = self._history.get_last_action()

                    recent_actions = self._history.get_recent_actions(RECENT_ACTION_WINDOW)
                    if should_force_complete(
                        self._task,
                        input_data.step_count,
                        last_action,
                        result.action,
                        recent_actions,
                    ):
                        self._fallback_ready_to_type = False
                        self._history.add(ACTION_COMPLETE, {})
                        return AgentOutput(
                            action=ACTION_COMPLETE,
                            parameters={},
                            raw_output=raw_output,
                        )

                    if result.action == ACTION_CLICK and self._history.is_stuck():
                        logger.info("重试后仍检测到重复点击，继续走fallback")
                    else:
                        # TYPE commit
                        if result.action == ACTION_TYPE and self._task is not None:
                            self._task.commit_text()

                        self._fallback_ready_to_type = False
                        self._history.add(result.action, result.parameters)
                        usage = None
                        try:
                            usage = self.extract_usage_info(response)
                        except Exception:
                            pass

                        return AgentOutput(
                            action=result.action,
                            parameters=result.parameters,
                            raw_output=raw_output,
                            usage=usage,
                        )
        except Exception as e:
            logger.warning(f"重试API调用失败: {e}")

        # 重试也失败 → fallback
        action, parameters = self._fallback(input_data)
        # TYPE commit for fallback
        if action == ACTION_TYPE and self._task is not None:
            self._task.commit_text()
        self._history.add(action, parameters)
        return AgentOutput(action=action, parameters=parameters)

    def _fallback(self, input_data: AgentInput) -> tuple[str, dict]:
        """Conservative fallback: returns (action, parameters), no history.add()"""
        step_count = input_data.step_count

        # 1. step_count==1 and app_name -> OPEN
        if step_count == 1 and self._task and self._task.app_name:
            return (ACTION_OPEN, {"app_name": self._task.app_name})

        # 2. Immediate post-open fallback -> CLICK close ad/popup
        if step_count <= 3 and self._history.get_last_action() == ACTION_OPEN:
            self._fallback_ready_to_type = False
            return (ACTION_CLICK, {"point": [900, 60]})

        # 3. Travel post-type -> click selected result
        if self._task and self._task.task_type == "travel" and self._history.get_last_action() == ACTION_TYPE:
            self._fallback_ready_to_type = False
            return (ACTION_CLICK, {"point": get_travel_result_coord()})

        # 4. Has pending text -> TYPE only after fallback click
        if self._task and self._task.has_pending_text():
            pending_text = self._task.peek_pending_text()
            app_name = self._task.app_name or ""
            last_action = self._history.get_last_action()
            last_click_point = self._history.get_last_click_point()
            if self._task.task_type == "travel":
                field_coord = get_travel_field_coord(self._task.type_index)
                search_coord = get_travel_search_bar_coord()
                result_coord = get_travel_result_coord()
                if last_action == ACTION_TYPE:
                    self._fallback_ready_to_type = False
                    return (ACTION_CLICK, {"point": result_coord})
                if self._fallback_ready_to_type and last_action == ACTION_CLICK and _points_close(last_click_point, search_coord):
                    self._fallback_ready_to_type = False
                    return (ACTION_TYPE, {"text": pending_text})
                next_coord = field_coord
                if _points_close(last_click_point, field_coord):
                    next_coord = search_coord
                self._fallback_ready_to_type = next_coord == search_coord
                return (ACTION_CLICK, {"point": next_coord})
            ready_for_type = (
                self._fallback_ready_to_type
                and last_action == ACTION_CLICK
                and pending_text is not None
            )
            if ready_for_type:
                self._fallback_ready_to_type = False
                return (ACTION_TYPE, {"text": pending_text})
            should_use_flow_continue = (
                self._task.task_type in FLOW_TASK_TYPES
                and len(self._task.type_queue) == 2
                and self._task.type_index == 1
                and last_action == ACTION_TYPE
            )
            coord = get_flow_continue_coord(app_name) if should_use_flow_continue else get_search_bar_coord(app_name)
            self._fallback_ready_to_type = True
            return (ACTION_CLICK, {"point": coord})

        travel_date_action = _travel_date_flow_step(
            self._task,
            self._history.get_last_action(),
            self._history.get_last_click_point(),
        )
        if travel_date_action is not None:
            self._fallback_ready_to_type = False
            return travel_date_action

        # 4. SCROLL down
        self._fallback_ready_to_type = False
        return (ACTION_SCROLL, {"start_point": [500, 800], "end_point": [500, 300]})

    def _encode_image(self, image, image_format: str = "JPEG") -> str:
        """JPEG编码，兼容 RGBA/P/LA 等模式"""
        if image.mode != "RGB":
            image = image.convert("RGB")

        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=90)
        base64_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{base64_str}"
