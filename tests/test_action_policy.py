"""ActionPolicy unit tests"""

import sys
import os

_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _root)

from agent import Agent
from utils.action_policy import PolicyDecision, correct
from utils.action_validator import ValidationResult
from utils.control_grounding import get_anchor
from utils.prompt_builder import get_flow_continue_coord, get_travel_field_coord, get_travel_search_bar_coord
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
check('policy redirects off-target click point', off_target_click.params, {'point': get_anchor('抖音', 'search_input')})
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

baidu_post_open_close_click = correct(
    action='CLICK',
    params={'point': [900, 60]},
    task=TaskInfo(
        instruction='在百度地图从北京大学到天安门',
        app_name='百度地图',
        task_type='baidu_map',
        type_queue=['北京大学', '天安门'],
    ),
    last_action='OPEN',
    recent_actions=['OPEN'],
)
check('baidu post-open close click redirects action', baidu_post_open_close_click.action, 'CLICK')
check('baidu post-open close click redirects params', baidu_post_open_close_click.params, {'point': get_flow_continue_coord('百度地图')})
check('baidu post-open close click marked changed', baidu_post_open_close_click.changed, True)
check('baidu post-open close click reason', baidu_post_open_close_click.reason, 'post_open_flow_entry_correction')
check('baidu post-open close click confidence', baidu_post_open_close_click.confidence, 'high')

meituan_post_open_generic_click = correct(
    action='CLICK',
    params={'point': [800, 500]},
    task=TaskInfo(
        instruction='在美团购买窑村干锅猪蹄店铺里的干锅排骨',
        app_name='美团',
        task_type='meituan',
        type_queue=['窑村干锅猪蹄', '干锅排骨'],
    ),
    last_action='OPEN',
    recent_actions=['OPEN'],
)
check('meituan post-open generic click redirects action', meituan_post_open_generic_click.action, 'CLICK')
check('meituan post-open generic click redirects params', meituan_post_open_generic_click.params, {'point': get_flow_continue_coord('美团')})
check('meituan post-open generic click marked changed', meituan_post_open_generic_click.changed, True)

travel_post_open_close_click = correct(
    action='CLICK',
    params={'point': [900, 60]},
    task=TaskInfo(
        instruction='在去哪儿旅行查北京到上海的航班',
        app_name='去哪儿旅行',
        task_type='travel',
        type_queue=['北京', '上海'],
    ),
    last_action='OPEN',
    recent_actions=['OPEN'],
)
check('travel post-open close click redirects action', travel_post_open_close_click.action, 'CLICK')
check('travel post-open close click redirects params', travel_post_open_close_click.params, {'point': get_travel_field_coord(0)})
check('travel post-open close click marked changed', travel_post_open_close_click.changed, True)

travel_post_open_type = correct(
    action='TYPE',
    params={'text': '北京'},
    task=TaskInfo(
        instruction='在去哪儿旅行查北京到上海的航班',
        app_name='去哪儿旅行',
        task_type='travel',
        type_queue=['北京', '上海'],
    ),
    last_action='OPEN',
    recent_actions=['OPEN'],
)
check('travel post-open type redirects action', travel_post_open_type.action, 'CLICK')
check('travel post-open type redirects params', travel_post_open_type.params, {'point': get_travel_field_coord(0)})
check('travel post-open type marked changed', travel_post_open_type.changed, True)
check('travel post-open type reason', travel_post_open_type.reason, 'post_open_flow_entry_correction')

flow_click_without_pending_text = correct(
    action='CLICK',
    params={'point': [900, 60]},
    task=TaskInfo(
        instruction='在百度地图从北京大学到天安门',
        app_name='百度地图',
        task_type='baidu_map',
        type_queue=['北京大学', '天安门'],
        type_index=2,
    ),
    last_action='OPEN',
    recent_actions=['OPEN'],
)
check('flow click without pending text keeps action', flow_click_without_pending_text.action, 'CLICK')
check('flow click without pending text keeps params', flow_click_without_pending_text.params, {'point': [900, 60]})
check('flow click without pending text stays unchanged', flow_click_without_pending_text.changed, False)

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
check('agent helper applies corrected params', applied.parameters, {'point': get_anchor('抖音', 'search_input')})
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

ximalaya_task = TaskInfo(
    instruction='在喜马拉雅搜索三体',
    app_name='喜马拉雅',
    task_type='video_search',
    type_queue=['三体'],
)
ximalaya_search_entry_click = correct(
    action='CLICK',
    params={'point': [853, 40]},
    task=ximalaya_task,
    last_action='OPEN',
    recent_actions=['OPEN'],
)
check('policy keeps ximalaya search entry click action', ximalaya_search_entry_click.action, 'CLICK')
check('policy keeps ximalaya search entry click params', ximalaya_search_entry_click.params, {'point': [853, 40]})
check('policy keeps ximalaya search entry click unchanged', ximalaya_search_entry_click.changed, False)
check('policy keeps ximalaya search entry click reason', ximalaya_search_entry_click.reason, 'post_open_search_entry_preserve')

tencent_task = TaskInfo(
    instruction='在腾讯视频搜索庆余年',
    app_name='腾讯视频',
    task_type='video_search',
    type_queue=['庆余年'],
)
tencent_search_input_redirect = correct(
    action='CLICK',
    params={'point': [341, 78]},
    task=tencent_task,
    last_action='CLICK',
    recent_actions=['OPEN', 'CLICK'],
)
check('policy redirects tencent off-target click to search input action', tencent_search_input_redirect.action, 'CLICK')
check('policy redirects tencent off-target click to search input params', tencent_search_input_redirect.params, {'point': get_anchor('腾讯视频', 'search_input')})
check('policy redirects tencent off-target click to search input changed', tencent_search_input_redirect.changed, True)

tencent_post_open_off_target_click = correct(
    action='CLICK',
    params={'point': [341, 78]},
    task=tencent_task,
    last_action='OPEN',
    recent_actions=['OPEN'],
)
check('policy redirects tencent post-open off-target click action', tencent_post_open_off_target_click.action, 'CLICK')
check('policy redirects tencent post-open off-target click params', tencent_post_open_off_target_click.params, {'point': get_anchor('腾讯视频', 'search_entry')})
check('policy redirects tencent post-open off-target click changed', tencent_post_open_off_target_click.changed, True)
check('policy redirects tencent post-open off-target click reason', tencent_post_open_off_target_click.reason, 'activate_search_entry_before_type')

tencent_post_open_input_click = correct(
    action='CLICK',
    params={'point': get_anchor('腾讯视频', 'search_input')},
    task=tencent_task,
    last_action='OPEN',
    recent_actions=['OPEN'],
)
check('policy redirects tencent post-open input click action', tencent_post_open_input_click.action, 'CLICK')
check('policy redirects tencent post-open input click params', tencent_post_open_input_click.params, {'point': get_anchor('腾讯视频', 'search_entry')})
check('policy redirects tencent post-open input click changed', tencent_post_open_input_click.changed, True)
check('policy redirects tencent post-open input click reason', tencent_post_open_input_click.reason, 'activate_search_entry_before_type')

sep = '=' * 40
print(f"\n{sep}")
print(f"ActionPolicy tests: {passed} passed, {failed} failed, {passed + failed} total")
if failed:
    print('RESULT: FAIL')
    sys.exit(1)
else:
    print('RESULT: ALL PASS')
