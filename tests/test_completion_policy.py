"""CompletionPolicy unit tests"""

import sys
import os

from PIL import Image

_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _root)

from agent import Agent
from agent_base import AgentInput
from utils.completion_policy import should_force_complete
from utils.task_parser import TaskInfo

passed = 0
failed = 0


def check(label, got, expected):
    global passed, failed
    if got == expected:
        passed += 1
    else:
        failed += 1
        print(f"FAIL: {label}")
        print(f"  expected: {expected}")
        print(f"  got:      {got}")


video_task = TaskInfo(instruction='在抖音搜索狂飙', task_type='video_search')
comment_task = TaskInfo(instruction='在爱奇艺评论', task_type='comment')
travel_task = TaskInfo(instruction='在去哪儿旅行查航班', task_type='travel')
pending_task = TaskInfo(instruction='在抖音搜索狂飙', task_type='video_search', type_queue=['狂飙'])

check('step too low', should_force_complete(video_task, 7, 'CLICK', 'CLICK', ['TYPE', 'CLICK', 'CLICK']), False)
check('pending text remains', should_force_complete(pending_task, 8, 'CLICK', 'CLICK', ['TYPE', 'CLICK', 'CLICK']), False)
check('last action open', should_force_complete(video_task, 8, 'OPEN', 'CLICK', ['TYPE', 'OPEN', 'CLICK']), False)
check('video click complete after two prior clicks', should_force_complete(video_task, 8, 'CLICK', 'CLICK', ['TYPE', 'CLICK', 'CLICK']), True)
check('comment click complete after two prior clicks', should_force_complete(comment_task, 8, 'CLICK', 'CLICK', ['TYPE', 'CLICK', 'CLICK']), True)
check('video click does not force complete after one prior click', should_force_complete(video_task, 8, 'CLICK', 'CLICK', ['OPEN', 'TYPE', 'CLICK']), False)
check('video click does not force complete without recent type', should_force_complete(video_task, 9, 'CLICK', 'CLICK', ['OPEN', 'CLICK', 'CLICK']), False)
check('flow task does not auto complete on clicks alone', should_force_complete(travel_task, 12, 'CLICK', 'CLICK', ['TYPE', 'CLICK', 'CLICK']), False)
check('current non-click does not force complete', should_force_complete(video_task, 8, 'CLICK', 'TYPE', ['TYPE', 'CLICK', 'CLICK']), False)
check('previous non-click does not force complete', should_force_complete(video_task, 8, 'TYPE', 'CLICK', ['TYPE', 'CLICK', 'TYPE']), False)

image = Image.new('RGB', (20, 20), color='white')
agent = Agent()
agent.act(AgentInput(instruction='在抖音搜索狂飙', current_image=image, step_count=1))
first_fallback = agent._fallback(AgentInput(instruction='在抖音搜索狂飙', current_image=image, step_count=4))
check('fallback clicks search box before typing', first_fallback[0], 'CLICK')
agent._history.add(first_fallback[0], first_fallback[1])
second_fallback = agent._fallback(AgentInput(instruction='在抖音搜索狂飙', current_image=image, step_count=5))
check('fallback types pending text after click', second_fallback, ('TYPE', {'text': '狂飙'}))

popup_agent = Agent()
popup_agent.act(AgentInput(instruction='在抖音搜索狂飙', current_image=image, step_count=1))
popup_close = popup_agent._fallback(AgentInput(instruction='在抖音搜索狂飙', current_image=image, step_count=3))
check('fallback popup close is click', popup_close[0], 'CLICK')
popup_agent._history.add(popup_close[0], popup_close[1])
after_popup = popup_agent._fallback(AgentInput(instruction='在抖音搜索狂飙', current_image=image, step_count=4))
check('fallback does not type after popup close click', after_popup[0], 'CLICK')

sep = '=' * 40
print(f"\n{sep}")
print(f"CompletionPolicy tests: {passed} passed, {failed} failed, {passed + failed} total")
if failed:
    print('RESULT: FAIL')
    sys.exit(1)
else:
    print('RESULT: ALL PASS')
