"""GUI Agent 实现 - 基于 BaseAgent，规则化OPEN/TYPE，视觉化CLICK，防早退COMPLETE"""

import io
import base64
import logging
from typing import Dict, Any, Optional

from agent_base import BaseAgent, AgentInput, AgentOutput, ACTION_CLICK, ACTION_TYPE, ACTION_SCROLL, ACTION_OPEN, ACTION_COMPLETE
from utils.task_parser import parse_task, TaskInfo
from utils.action_parser import parse as parse_action
from utils.action_validator import validate as validate_action, ValidationResult
from utils.prompt_builder import build_messages, build_retry_prompt, get_search_bar_coord
from utils.history_manager import HistoryManager

logger = logging.getLogger(__name__)


class Agent(BaseAgent):
    def _initialize(self) -> None:
        self._task: Optional[TaskInfo] = None
        self._history = HistoryManager()

    def reset(self) -> None:
        self._task = None
        self._history.reset()

    def act(self, input_data: AgentInput) -> AgentOutput:
        step_count = input_data.step_count

        # 首次进入：解析任务
        if self._task is None:
            self._task = parse_task(input_data.instruction)

        # step_count==1 且 app_name存在 → 直接返回OPEN，不调模型
        if step_count == 1 and self._task.app_name:
            action = ACTION_OPEN
            parameters = {"app_name": self._task.app_name}
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
            return self._fallback(input_data)

        # 解析模型输出
        parsed = parse_action(raw_output)
        if parsed is None:
            logger.warning(f"解析失败，原始输出: {raw_output[:200]}")
            return self._retry_or_fallback(input_data, messages, "模型输出无法解析为合法动作")

        action, parameters = parsed

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
                    # TYPE commit
                    if result.action == ACTION_TYPE and self._task is not None:
                        self._task.commit_text()

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

        # 2. step_count<=3 -> CLICK close ad/popup
        if step_count <= 3:
            return (ACTION_CLICK, {"point": [900, 60]})

        # 3. Has pending text -> CLICK search box (not TYPE!)
        if self._task and self._task.has_pending_text():
            app_name = self._task.app_name or ""
            coord = get_search_bar_coord(app_name)
            return (ACTION_CLICK, {"point": coord})

        # 4. SCROLL down
        return (ACTION_SCROLL, {"start_point": [500, 800], "end_point": [500, 300]})

    def _encode_image(self, image, image_format: str = "JPEG") -> str:
        """覆盖为JPEG编码(quality=90)，不缩小图片"""
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=90)
        base64_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{base64_str}"
