"""Grounder unit tests"""

import os
import sys

_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _root)

from utils.grounder import (
    clear_profile_cache,
    get_anchor,
    get_app_tip,
    get_available_controls,
    get_control_spec,
    get_workflow_family,
    ground_action,
    has_distinct_control,
    identify_control,
)
from utils.prompt_builder import get_flow_continue_coord, get_flow_input_coord, get_search_bar_coord

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


clear_profile_cache()

check('app tip comes from profile override', get_app_tip('腾讯视频'), '腾讯视频：搜入口右上→输剧名→点搜索→进剧集→选对应集数')
check('workflow family comes from family default', get_workflow_family('抖音'), 'video')
check('legacy workflow family still works', get_workflow_family('百度地图'), 'flow')
check('app override anchor wins', get_anchor('腾讯视频', 'search_entry'), [902, 78])
check('family default anchor applies to video apps', get_anchor('快手', 'first_result'), [500, 260])
check('legacy profile anchor still applies', get_anchor('去哪儿旅行', 'search_button'), [494, 611])
check('explicit default wins for unknown control', get_anchor('未知App', 'nonexistent_control', [321, 654]), [321, 654])
check('global default anchor fallback still works', get_anchor('未知App', 'search_entry'), [500, 120])
check('prompt builder search helper keeps search input compatibility', get_search_bar_coord('腾讯视频'), [850, 80])
check('prompt builder flow helper keeps flow compatibility', get_flow_continue_coord('百度地图'), [500, 220])
check('prompt builder flow input falls back to flow entry when depart field is absent', get_flow_input_coord('美团'), [500, 260])

search_entry_spec = get_control_spec('腾讯视频', 'search_entry')
check('control spec keeps override point', list(search_entry_spec.fallback_point), [902, 78])
check('control spec keeps default aliases', list(search_entry_spec.aliases), ['搜索', '放大镜', '搜索入口'])
check('control spec keeps default tolerance when omitted', search_entry_spec.tolerance, 60)

available_controls = get_available_controls('爱奇艺')
check('available controls includes comment submit', 'comment_submit' in available_controls, True)
check('available controls includes first result', 'first_result' in available_controls, True)

travel_controls = get_available_controls('去哪儿旅行')
check('travel available controls includes search bar', 'search_bar' in travel_controls, True)
check('travel available controls includes date entry', 'date_entry' in travel_controls, True)
check('travel available controls includes date option', 'date_option' in travel_controls, True)
check('travel search bar anchor comes from profile override', get_anchor('去哪儿旅行', 'search_bar'), [500, 165])
check('travel first result anchor comes from profile override', get_anchor('去哪儿旅行', 'first_result'), [500, 180])
check('travel date entry anchor comes from profile override', get_anchor('去哪儿旅行', 'date_entry'), [277, 361])
check('travel date option anchor comes from profile override', get_anchor('去哪儿旅行', 'date_option'), [902, 303])

check('identify control matches near override point', identify_control('腾讯视频', [910, 80]), 'search_entry')
check('identify control returns none for distant point', identify_control('腾讯视频', [50, 50]), None)
check('travel app has distinct fields', has_distinct_control('去哪儿旅行', 'depart_field', 'destination_field'), True)
check('generic default controls can overlap', has_distinct_control('未知App', 'search_entry', 'flow_entry'), True)

grounded_click = ground_action('CLICK', {'control': 'search_entry'}, '腾讯视频')
check('ground action resolves click control', (grounded_click.action, grounded_click.parameters), ('CLICK', {'point': [902, 78]}))

grounded_missing = ground_action('CLICK', {'control': 'missing_control'}, '腾讯视频')
check('ground action does not guess point for missing control', (grounded_missing.action, grounded_missing.parameters), ('CLICK', {}))

grounded_type = ground_action('TYPE', {'text': '__PENDING__'}, '腾讯视频', pending_text='庆余年')
check('ground action resolves pending text', (grounded_type.action, grounded_type.parameters), ('TYPE', {'text': '庆余年'}))

grounded_plain = ground_action('SCROLL', {'start_point': [1, 2], 'end_point': [3, 4]}, '腾讯视频')
check('ground action keeps plain parameters', (grounded_plain.action, grounded_plain.parameters), ('SCROLL', {'start_point': [1, 2], 'end_point': [3, 4]}))

sep = '=' * 40
print(f"\n{sep}")
print(f"Grounder tests: {passed} passed, {failed} failed, {passed + failed} total")
if failed:
    print('RESULT: FAIL')
    sys.exit(1)
else:
    print('RESULT: ALL PASS')
