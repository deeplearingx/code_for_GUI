"""ActionPolicy unit tests"""

import sys
import os

_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _root)

from agent import Agent
from utils.action_policy import PolicyDecision, correct
from utils.action_validator import ValidationResult
from utils.prompt_builder import get_search_bar_coord, get_travel_field_coord, get_travel_search_bar_coord
from utils.task_parser import TaskInfo

passed = 0
failed = 0


class RejectingPolicyAgent(Agent):
    def _decide_action_policy(self, result: ValidationResult) -> PolicyDecision:
        return PolicyDecision(
            action="CLICK",
            params={},
            changed=True,
            reason="force_invalid_click",
            confidence="high",
        )


def check(label, got, expected):
    global passed, failed
    if got == expected:
        passed += 1
    else:
        failed += 1
        print(f"FAIL: {label}")
        print(f"  expected: {expected}")
        print(f"  got:      {got}")


search_task = TaskInfo(
    instruction='在抖音搜索狂飙',
    app_name='抖音',
    task_type='video_search',
    type_queue=['狂飙'],
)
flow_task = TaskInfo(
    instruction='在去哪儿旅行查北京到上海的航班',
    app_name='去哪儿旅行',
    task_type='travel',
    type_queue=['北京', '上海'],
)
travel_live_task = TaskInfo(
    instruction='帮我在去哪儿旅行看一下邯郸到上海的航班',
    app_name='去哪儿旅行',
    task_type='travel',
    type_queue=['邯郸', '上海'],
)
comment_stage_two_task = TaskInfo(
    instruction='在爱奇艺搜索采莲曲，发布评论：好看',
    app_name='爱奇艺',
    task_type='comment',
    search_keyword='采莲曲',
    comment_text='好看',
    type_queue=['采莲曲', '好看'],
    type_index=1,
)

search_bar_click = correct(
    action='TYPE',
    params={'text': '狂飙'},
    task=search_task,
    last_action='SCROLL',
    recent_actions=['SCROLL'],
)
check('policy decision type', isinstance(search_bar_click, PolicyDecision), True)
check('policy keeps type action', search_bar_click.action, 'TYPE')
check('policy keeps type params', search_bar_click.params, {'text': '狂飙'})
check('policy keeps type unchanged', search_bar_click.changed, False)
check('policy keeps type reason', search_bar_click.reason, 'validated_action')
check('policy keeps type confidence', search_bar_click.confidence, 'none')

off_target_click = correct(
    action='CLICK',
    params={'point': [720, 640]},
    task=search_task,
    last_action='SCROLL',
    recent_actions=['SCROLL'],
)
check('policy redirects off-target click to search bar', off_target_click.action, 'CLICK')
check('policy redirects off-target click point', off_target_click.params, {'point': get_search_bar_coord('抖音')})
check('policy off-target click marked changed', off_target_click.changed, True)
check('policy off-target click reason', off_target_click.reason, 'activate_search_bar_before_type')
check('policy off-target click confidence', off_target_click.confidence, 'high')

scroll_then_type = correct(
    action='TYPE',
    params={'text': '狂飙'},
    task=search_task,
    last_action='SCROLL',
    recent_actions=['SCROLL'],
)
check('policy keeps scroll then type action', scroll_then_type.action, 'TYPE')
check('policy keeps scroll then type params', scroll_then_type.params, {'text': '狂飙'})
check('policy keeps scroll then type unchanged', scroll_then_type.changed, False)

comment_stage_two_click = correct(
    action='CLICK',
    params={'point': [720, 640]},
    task=comment_stage_two_task,
    last_action='CLICK',
    recent_actions=['TYPE', 'CLICK'],
)
check('policy keeps comment stage two click action', comment_stage_two_click.action, 'CLICK')
check('policy keeps comment stage two click params', comment_stage_two_click.params, {'point': [720, 640]})
check('policy keeps comment stage two click unchanged', comment_stage_two_click.changed, False)

flow_click = correct(
    action='CLICK',
    params={'point': [720, 640]},
    task=flow_task,
    last_action='CLICK',
    recent_actions=['TYPE', 'CLICK'],
)
check('flow click keeps action', flow_click.action, 'CLICK')
check('flow click keeps params', flow_click.params, {'point': [720, 640]})
check('flow click stays unchanged', flow_click.changed, False)
check('flow click reason', flow_click.reason, 'flow_task_preserve_validated_action')
check('flow click confidence', flow_click.confidence, 'none')

travel_premature_type = correct(
    action='TYPE',
    params={'text': '邯郸'},
    task=travel_live_task,
    last_action='SCROLL',
    recent_actions=['SCROLL'],
)
check('travel premature type redirects to travel search action', travel_premature_type.action, 'CLICK')
check('travel premature type redirects to travel search params', travel_premature_type.params, {'point': get_travel_search_bar_coord()})
check('travel premature type marked changed', travel_premature_type.changed, True)
check('travel premature type reason', travel_premature_type.reason, 'activate_travel_search_bar_before_type')
check('travel premature type confidence', travel_premature_type.confidence, 'high')

generic_click_then_type = correct(
    action='TYPE',
    params={'text': '邯郸'},
    task=travel_live_task,
    last_action='CLICK',
    recent_actions=['CLICK'],
    last_click_point=[900, 60],
)
check('travel type after generic click redirects action', generic_click_then_type.action, 'CLICK')
check('travel type after generic click redirects params', generic_click_then_type.params, {'point': get_travel_search_bar_coord()})

travel_field_click_then_type = correct(
    action='TYPE',
    params={'text': '邯郸'},
    task=travel_live_task,
    last_action='CLICK',
    recent_actions=['CLICK'],
    last_click_point=get_travel_field_coord(0),
)
check('travel type after field click redirects action', travel_field_click_then_type.action, 'CLICK')
check('travel type after field click redirects params', travel_field_click_then_type.params, {'point': get_travel_search_bar_coord()})

travel_search_click_then_type = correct(
    action='TYPE',
    params={'text': '邯郸'},
    task=travel_live_task,
    last_action='CLICK',
    recent_actions=['CLICK'],
    last_click_point=get_travel_search_bar_coord(),
)
check('travel type after search bar click stays type action', travel_search_click_then_type.action, 'TYPE')
check('travel type after search bar click stays params', travel_search_click_then_type.params, {'text': '邯郸'})
check('travel type after search bar click stays unchanged', travel_search_click_then_type.changed, False)

travel_second_leg_generic_click = correct(
    action='TYPE',
    params={'text': '上海'},
    task=TaskInfo(
        instruction='帮我在去哪儿旅行看一下邯郸到上海的航班',
        app_name='去哪儿旅行',
        task_type='travel',
        type_queue=['邯郸', '上海'],
        type_index=1,
    ),
    last_action='CLICK',
    recent_actions=['TYPE', 'CLICK'],
    last_click_point=[900, 60],
)
check('travel second leg type redirects after generic click', travel_second_leg_generic_click.action, 'CLICK')
check('travel second leg type redirects params after generic click', travel_second_leg_generic_click.params, {'point': get_travel_search_bar_coord()})

travel_second_leg_search_click = correct(
    action='TYPE',
    params={'text': '上海'},
    task=TaskInfo(
        instruction='帮我在去哪儿旅行看一下邯郸到上海的航班',
        app_name='去哪儿旅行',
        task_type='travel',
        type_queue=['邯郸', '上海'],
        type_index=1,
    ),
    last_action='CLICK',
    recent_actions=['TYPE', 'CLICK'],
    last_click_point=get_travel_search_bar_coord(),
)
check('travel second leg type stays type action', travel_second_leg_search_click.action, 'TYPE')
check('travel second leg type stays type params', travel_second_leg_search_click.params, {'text': '上海'})
check('travel second leg type stays unchanged', travel_second_leg_search_click.changed, False)

agent = Agent()
agent._task = TaskInfo(
    instruction='在抖音搜索狂飙',
    app_name='抖音',
    task_type='video_search',
    type_queue=['狂飙'],
)
agent._history.add('SCROLL', {'start_point': [500, 800], 'end_point': [500, 300]})
applied = agent._apply_action_policy(
    ValidationResult(action='CLICK', parameters={'point': [720, 640]}, ok=True),
    step_count=4,
)
check('agent helper applies corrected action', applied.action, 'CLICK')
check('agent helper applies corrected params', applied.parameters, {'point': get_search_bar_coord('抖音')})
check('agent helper does not commit pending text', agent._task.type_index, 0)

rejecting_agent = RejectingPolicyAgent()
rejecting_agent._task = TaskInfo(
    instruction='在抖音搜索狂飙',
    app_name='抖音',
    task_type='video_search',
    type_queue=['狂飙'],
)
rejecting_agent._history.add('SCROLL', {'start_point': [500, 800], 'end_point': [500, 300]})
reverted = rejecting_agent._apply_action_policy(
    ValidationResult(action='TYPE', parameters={'text': '狂飙'}, ok=True),
    step_count=4,
)
check('agent helper reverts invalid corrected action', reverted.action, 'TYPE')
check('agent helper reverts invalid corrected params', reverted.parameters, {'text': '狂飙'})

sep = '=' * 40
print(f"\n{sep}")
print(f"ActionPolicy tests: {passed} passed, {failed} failed, {passed + failed} total")
if failed:
    print('RESULT: FAIL')
    sys.exit(1)
else:
    print('RESULT: ALL PASS')
