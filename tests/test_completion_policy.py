"""CompletionPolicy unit tests"""

import sys
import os

from PIL import Image

_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _root)

from agent import Agent
from agent_base import AgentInput
from utils.completion_policy import should_complete_from_state, should_force_complete
from utils.prompt_builder import get_flow_continue_coord, get_search_bar_coord, get_travel_date_entry_coord, get_travel_date_option_coord, get_travel_field_coord, get_travel_result_coord, get_travel_search_bar_coord, get_travel_search_button_coord
from utils.screen_state import ScreenState, ScreenStateSnapshot
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
baidu_map_task = TaskInfo(instruction='在百度地图从北京大学到天安门', task_type='baidu_map')
meituan_task = TaskInfo(instruction='在美团购买窑村干锅猪蹄店铺里的干锅排骨', task_type='meituan')
travel_task = TaskInfo(instruction='在去哪儿旅行查航班', task_type='travel')
pending_task = TaskInfo(instruction='在抖音搜索狂飙', task_type='video_search', type_queue=['狂飙'])

check('step too low', should_force_complete(video_task, 7, 'CLICK', 'CLICK', ['TYPE', 'CLICK', 'CLICK']), False)
check('pending text remains', should_force_complete(pending_task, 8, 'CLICK', 'CLICK', ['TYPE', 'CLICK', 'CLICK']), False)
check('last action open', should_force_complete(video_task, 8, 'OPEN', 'CLICK', ['TYPE', 'OPEN', 'CLICK']), False)
check('video state complete from detail page', should_complete_from_state(video_task, ScreenStateSnapshot(ScreenState.DETAIL_PAGE, None, 'CLICK', 'first_result', 'result_opened')), True)
check('comment state complete from done state', should_complete_from_state(comment_task, ScreenStateSnapshot(ScreenState.DONE, None, 'CLICK', 'comment_submit', 'comment_submitted')), True)
check('state completion blocks when pending text remains', should_complete_from_state(pending_task, ScreenStateSnapshot(ScreenState.DETAIL_PAGE, '狂飙', 'CLICK', 'first_result', 'result_opened')), False)
check('video force complete still supports legacy click tail', should_force_complete(video_task, 8, 'CLICK', 'CLICK', ['TYPE', 'CLICK']), True)
check('comment force complete still supports legacy click tail', should_force_complete(comment_task, 8, 'CLICK', 'CLICK', ['TYPE', 'CLICK']), True)
check('video force complete accepts explicit detail state', should_force_complete(video_task, 5, 'CLICK', 'COMPLETE', ['TYPE', 'CLICK'], snapshot=ScreenStateSnapshot(ScreenState.DETAIL_PAGE, None, 'CLICK', 'first_result', 'result_opened')), True)
check('comment force complete accepts explicit done state', should_force_complete(comment_task, 6, 'CLICK', 'COMPLETE', ['TYPE', 'CLICK'], snapshot=ScreenStateSnapshot(ScreenState.DONE, None, 'CLICK', 'comment_submit', 'comment_submitted')), True)
check('video click does not force complete without recent type', should_force_complete(video_task, 9, 'CLICK', 'CLICK', ['OPEN', 'CLICK']), False)
check('video click does not force complete when only earlier actions match', should_force_complete(video_task, 9, 'CLICK', 'CLICK', ['TYPE', 'CLICK', 'OPEN', 'CLICK']), False)
check('baidu_map click does not complete on generic boundary tail', should_force_complete(baidu_map_task, 8, 'CLICK', 'CLICK', ['TYPE', 'CLICK']), False)
check('meituan click does not complete on generic boundary tail', should_force_complete(meituan_task, 8, 'CLICK', 'CLICK', ['TYPE', 'CLICK']), False)
check('travel click does not complete on generic boundary tail', should_force_complete(travel_task, 8, 'CLICK', 'CLICK', ['TYPE', 'CLICK']), False)
check('flow task does not auto complete on clicks alone', should_force_complete(travel_task, 12, 'CLICK', 'CLICK', ['OPEN', 'CLICK']), False)
check('flow task does not force complete when only earlier actions match', should_force_complete(travel_task, 12, 'CLICK', 'CLICK', ['TYPE', 'CLICK', 'OPEN', 'CLICK']), False)
check('current non-click does not force complete without terminal state', should_force_complete(video_task, 8, 'CLICK', 'TYPE', ['TYPE', 'CLICK', 'CLICK']), False)
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
popup_close = popup_agent._fallback(AgentInput(instruction='在抖音搜索狂飙', current_image=image, step_count=2, extra={'popup_confidence': 0.9}))
check('fallback popup close uses top right close point', popup_close, ('CLICK', {'point': [900, 60]}))
popup_agent._history.add(popup_close[0], popup_close[1])
after_popup = popup_agent._fallback(AgentInput(instruction='在抖音搜索狂飙', current_image=image, step_count=3))
check('fallback clicks search bar after early popup close', after_popup, ('CLICK', {'point': get_search_bar_coord('抖音')}))
popup_agent._history.add(after_popup[0], after_popup[1])
after_popup_type = popup_agent._fallback(AgentInput(instruction='在抖音搜索狂飙', current_image=image, step_count=4))
check('fallback types after search click following popup close', after_popup_type, ('TYPE', {'text': '狂飙'}))

def always_fail_api(_messages, **_kwargs):
    raise RuntimeError('forced api failure for fallback test')

travel_open_agent = Agent()
travel_open_agent._call_api = always_fail_api
travel_open_agent.act(AgentInput(instruction='在去哪儿旅行查北京到上海的航班', current_image=image, step_count=1))
travel_open_first_click = travel_open_agent._fallback(AgentInput(instruction='在去哪儿旅行查北京到上海的航班', current_image=image, step_count=2))
check('travel fallback prefers origin field after open', travel_open_first_click, ('CLICK', {'point': get_travel_field_coord(0)}))

baidu_open_agent = Agent()
baidu_open_agent._call_api = always_fail_api
baidu_open_agent.act(AgentInput(instruction='在百度地图从北京大学到天安门', current_image=image, step_count=1))
baidu_open_first_click = baidu_open_agent._fallback(AgentInput(instruction='在百度地图从北京大学到天安门', current_image=image, step_count=2))
check('baidu map fallback prefers flow entry after open', baidu_open_first_click, ('CLICK', {'point': get_flow_continue_coord('百度地图')}))

meituan_open_agent = Agent()
meituan_open_agent._call_api = always_fail_api
meituan_open_agent.act(AgentInput(instruction='在美团购买窑村干锅猪蹄店铺里的干锅排骨', current_image=image, step_count=1))
meituan_open_first_click = meituan_open_agent._fallback(AgentInput(instruction='在美团购买窑村干锅猪蹄店铺里的干锅排骨', current_image=image, step_count=2))
check('meituan fallback prefers flow entry after open', meituan_open_first_click, ('CLICK', {'point': get_flow_continue_coord('美团')}))


def check_flow_fallback_sequence(label_prefix, instruction, app_name, first_text, second_text):
    flow_agent = Agent()
    flow_agent._call_api = always_fail_api
    flow_agent.act(AgentInput(instruction=instruction, current_image=image, step_count=1))

    first_click = flow_agent.act(AgentInput(instruction=instruction, current_image=image, step_count=4))
    check(f'{label_prefix} first click uses expected entry anchor', (first_click.action, first_click.parameters), ('CLICK', {'point': get_search_bar_coord(app_name)}))

    first_type = flow_agent.act(AgentInput(instruction=instruction, current_image=image, step_count=5))
    check(f'{label_prefix} types first pending text after search click', (first_type.action, first_type.parameters), ('TYPE', {'text': first_text}))

    continue_click = flow_agent.act(AgentInput(instruction=instruction, current_image=image, step_count=6))
    check(f'{label_prefix} continuation stays click', continue_click.action, 'CLICK')
    check(f'{label_prefix} continuation click uses flow anchor', continue_click.parameters, {'point': get_flow_continue_coord(app_name)})
    check(f'{label_prefix} continuation click avoids search bar', continue_click.parameters == {'point': get_search_bar_coord(app_name)}, False)

    second_type = flow_agent.act(AgentInput(instruction=instruction, current_image=image, step_count=7))
    check(f'{label_prefix} types second pending text after continuation click', (second_type.action, second_type.parameters), ('TYPE', {'text': second_text}))


def check_travel_fallback_sequence(instruction, first_text, second_text):
    travel_agent = Agent()
    travel_agent._call_api = always_fail_api
    travel_agent.act(AgentInput(instruction=instruction, current_image=image, step_count=1))

    first_field_click = travel_agent.act(AgentInput(instruction=instruction, current_image=image, step_count=4))
    check('travel fallback first click uses origin field', (first_field_click.action, first_field_click.parameters), ('CLICK', {'point': get_travel_field_coord(0)}))

    first_search_click = travel_agent.act(AgentInput(instruction=instruction, current_image=image, step_count=5))
    check('travel fallback second click uses travel search bar', (first_search_click.action, first_search_click.parameters), ('CLICK', {'point': get_travel_search_bar_coord()}))

    first_type = travel_agent.act(AgentInput(instruction=instruction, current_image=image, step_count=6))
    check('travel fallback types first pending text after search bar click', (first_type.action, first_type.parameters), ('TYPE', {'text': first_text}))

    first_result_click = travel_agent.act(AgentInput(instruction=instruction, current_image=image, step_count=7))
    check('travel fallback clicks first result after first type', (first_result_click.action, first_result_click.parameters), ('CLICK', {'point': get_travel_result_coord()}))

    second_field_click = travel_agent.act(AgentInput(instruction=instruction, current_image=image, step_count=8))
    check('travel fallback clicks destination field after first result', (second_field_click.action, second_field_click.parameters), ('CLICK', {'point': get_travel_field_coord(1)}))

    second_search_click = travel_agent.act(AgentInput(instruction=instruction, current_image=image, step_count=9))
    check('travel fallback clicks travel search bar before second type', (second_search_click.action, second_search_click.parameters), ('CLICK', {'point': get_travel_search_bar_coord()}))

    second_type = travel_agent.act(AgentInput(instruction=instruction, current_image=image, step_count=10))
    check('travel fallback types second pending text after destination search click', (second_type.action, second_type.parameters), ('TYPE', {'text': second_text}))

    second_result_click = travel_agent.act(AgentInput(instruction=instruction, current_image=image, step_count=11))
    check('travel fallback clicks second result after second type', (second_result_click.action, second_result_click.parameters), ('CLICK', {'point': get_travel_result_coord()}))


check_travel_fallback_sequence('在去哪儿旅行查北京到上海的航班', '北京', '上海')


def check_travel_date_fallback_sequence():
    travel_agent = Agent()
    travel_agent._call_api = always_fail_api
    instruction = '在去哪儿旅行查后天北京到上海的航班，最便宜的是多钱'
    travel_agent.act(AgentInput(instruction=instruction, current_image=image, step_count=1))

    travel_agent.act(AgentInput(instruction=instruction, current_image=image, step_count=4))
    travel_agent.act(AgentInput(instruction=instruction, current_image=image, step_count=5))
    travel_agent.act(AgentInput(instruction=instruction, current_image=image, step_count=6))
    travel_agent.act(AgentInput(instruction=instruction, current_image=image, step_count=7))
    travel_agent.act(AgentInput(instruction=instruction, current_image=image, step_count=8))
    travel_agent.act(AgentInput(instruction=instruction, current_image=image, step_count=9))
    travel_agent.act(AgentInput(instruction=instruction, current_image=image, step_count=10))
    travel_agent.act(AgentInput(instruction=instruction, current_image=image, step_count=11))

    date_entry_click = travel_agent.act(AgentInput(instruction=instruction, current_image=image, step_count=12))
    check('travel date fallback clicks date entry after destination result', (date_entry_click.action, date_entry_click.parameters), ('CLICK', {'point': get_travel_date_entry_coord()}))

    date_option_click = travel_agent.act(AgentInput(instruction=instruction, current_image=image, step_count=13))
    check('travel date fallback clicks hinted date option', (date_option_click.action, date_option_click.parameters), ('CLICK', {'point': [902, 303]}))

    search_click = travel_agent.act(AgentInput(instruction=instruction, current_image=image, step_count=14))
    check('travel date fallback clicks search after date selection', (search_click.action, search_click.parameters), ('CLICK', {'point': [494, 611]}))

    final_complete = travel_agent.act(AgentInput(instruction=instruction, current_image=image, step_count=15))
    check('travel date fallback completes after date flow', (final_complete.action, final_complete.parameters), ('COMPLETE', {}))


check_travel_date_fallback_sequence()
check_flow_fallback_sequence('baidu map flow fallback', '在百度地图从北京大学到天安门', '百度地图', '北京大学', '天安门')
check_flow_fallback_sequence('meituan flow fallback', '在美团购买窑村干锅猪蹄店铺里的干锅排骨', '美团', '窑村干锅猪蹄', '干锅排骨')

travel_guard_agent = Agent()
travel_guard_agent._call_api = always_fail_api
travel_guard_agent.act(AgentInput(instruction='在去哪儿旅行查北京到上海的航班', current_image=image, step_count=1))
travel_guard_agent._fallback_ready_to_type = True
travel_guard_agent._history.add('CLICK', {'point': [900, 60]})
travel_guard_blocked = travel_guard_agent._fallback(AgentInput(instruction='在去哪儿旅行查北京到上海的航班', current_image=image, step_count=5))
check('travel fallback blocks type after wrong click', travel_guard_blocked, ('CLICK', {'point': get_travel_field_coord(0)}))

travel_search_guard_agent = Agent()
travel_search_guard_agent._call_api = always_fail_api
travel_search_guard_agent.act(AgentInput(instruction='在去哪儿旅行查北京到上海的航班', current_image=image, step_count=1))
travel_search_guard_agent._fallback_ready_to_type = True
travel_search_guard_agent._history.add('CLICK', {'point': get_travel_field_coord(0)})
travel_search_guard_blocked = travel_search_guard_agent._fallback(AgentInput(instruction='在去哪儿旅行查北京到上海的航班', current_image=image, step_count=5))
check('travel fallback blocks type until search bar is clicked', travel_search_guard_blocked, ('CLICK', {'point': get_travel_search_bar_coord()}))

travel_search_tolerance_agent = Agent()
travel_search_tolerance_agent._call_api = always_fail_api
travel_search_tolerance_agent.act(AgentInput(instruction='在去哪儿旅行查北京到上海的航班', current_image=image, step_count=1))
travel_search_tolerance_agent._fallback_ready_to_type = True
travel_search_tolerance_agent._history.add('CLICK', {'point': [495, 170]})
travel_search_tolerance = travel_search_tolerance_agent._fallback(AgentInput(instruction='在去哪儿旅行查北京到上海的航班', current_image=image, step_count=5))
check('travel fallback accepts near search bar click for type', travel_search_tolerance, ('TYPE', {'text': '北京'}))

generic_type_guard_agent = Agent()
generic_type_guard_agent._call_api = always_fail_api
generic_type_guard_agent.act(AgentInput(instruction='在抖音搜索狂飙', current_image=image, step_count=1))
generic_type_guard_agent._fallback_ready_to_type = True
generic_type_guard_agent._history.add('CLICK', {'point': [900, 60]})
generic_type_guard_blocked = generic_type_guard_agent._fallback(AgentInput(instruction='在抖音搜索狂飙', current_image=image, step_count=5))
check('generic fallback blocks type after wrong click', generic_type_guard_blocked, ('CLICK', {'point': get_search_bar_coord('抖音')}))

generic_type_tolerance_agent = Agent()
generic_type_tolerance_agent._call_api = always_fail_api
generic_type_tolerance_agent.act(AgentInput(instruction='在抖音搜索狂飙', current_image=image, step_count=1))
generic_type_tolerance_agent._fallback_ready_to_type = True
generic_type_tolerance_agent._history.add('CLICK', {'point': [205, 85]})
generic_type_tolerance = generic_type_tolerance_agent._fallback(AgentInput(instruction='在抖音搜索狂飙', current_image=image, step_count=5))
check('generic fallback accepts near search bar click for type', generic_type_tolerance, ('TYPE', {'text': '狂飙'}))

generic_travel_agent = Agent()
generic_travel_agent._call_api = always_fail_api
generic_instruction = '在去哪儿旅行查北京到上海的航班'
generic_travel_agent.act(AgentInput(instruction=generic_instruction, current_image=image, step_count=1))
generic_travel_agent.act(AgentInput(instruction=generic_instruction, current_image=image, step_count=4))
generic_travel_agent.act(AgentInput(instruction=generic_instruction, current_image=image, step_count=5))
generic_travel_agent.act(AgentInput(instruction=generic_instruction, current_image=image, step_count=6))
generic_travel_agent.act(AgentInput(instruction=generic_instruction, current_image=image, step_count=7))
generic_travel_agent.act(AgentInput(instruction=generic_instruction, current_image=image, step_count=8))
generic_travel_agent.act(AgentInput(instruction=generic_instruction, current_image=image, step_count=9))
generic_travel_agent.act(AgentInput(instruction=generic_instruction, current_image=image, step_count=10))
generic_travel_agent.act(AgentInput(instruction=generic_instruction, current_image=image, step_count=11))
travel_after_second_result = generic_travel_agent._fallback(AgentInput(instruction=generic_instruction, current_image=image, step_count=12))
check('generic travel still scrolls after second result without date hint', travel_after_second_result, ('SCROLL', {'start_point': [500, 800], 'end_point': [500, 300]}))

sep = '=' * 40
print(f"\n{sep}")
print(f"CompletionPolicy tests: {passed} passed, {failed} failed, {passed + failed} total")
if failed:
    print('RESULT: FAIL')
    sys.exit(1)
else:
    print('RESULT: ALL PASS')
