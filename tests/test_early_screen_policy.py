"""EarlyScreenPolicy unit tests"""

import sys
import os

_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _root)

from utils.early_screen_policy import decide_post_open_action
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


video_task = TaskInfo(instruction='在抖音搜索狂飙', app_name='抖音', task_type='video_search')
travel_task = TaskInfo(instruction='在去哪儿旅行查北京到上海的航班', app_name='去哪儿旅行', task_type='travel')
baidu_map_task = TaskInfo(instruction='在百度地图从北京大学到天安门', app_name='百度地图', task_type='baidu_map')
meituan_task = TaskInfo(instruction='在美团购买窑村干锅猪蹄店铺里的干锅排骨', app_name='美团', task_type='meituan')

check(
    'video task uses search entry after open',
    decide_post_open_action(video_task, 2, 'OPEN'),
    ('CLICK', {'point': [898, 922]}, 'post_open_video_search_entry', 'high'),
)
check(
    'tencent video uses top-right search entry after open',
    decide_post_open_action(TaskInfo(instruction='在腾讯视频搜索庆余年', app_name='腾讯视频', task_type='video_search'), 2, 'OPEN'),
    ('CLICK', {'point': [902, 78]}, 'post_open_video_search_entry', 'high'),
)
check(
    'travel task uses depart field after open',
    decide_post_open_action(travel_task, 2, 'OPEN'),
    ('CLICK', {'point': [252, 291]}, 'post_open_travel_depart_field', 'high'),
)
check(
    'baidu map uses flow entry after open',
    decide_post_open_action(baidu_map_task, 2, 'OPEN'),
    ('CLICK', {'point': [500, 220]}, 'post_open_baidu_map_flow_entry', 'medium'),
)
check(
    'meituan uses flow entry after open',
    decide_post_open_action(meituan_task, 2, 'OPEN'),
    ('CLICK', {'point': [500, 260]}, 'post_open_meituan_flow_entry', 'medium'),
)
check(
    'high confidence popup closes top right',
    decide_post_open_action(video_task, 2, 'OPEN', popup_confidence=0.9),
    ('CLICK', {'point': [900, 60]}, 'close_popup_high_confidence', 'high'),
)
check(
    'non-open previous action returns none',
    decide_post_open_action(video_task, 2, 'CLICK'),
    None,
)
check(
    'late step returns none',
    decide_post_open_action(video_task, 4, 'OPEN'),
    None,
)

sep = '=' * 40
print(f"\n{sep}")
print(f"EarlyScreenPolicy tests: {passed} passed, {failed} failed, {passed + failed} total")
if failed:
    print('RESULT: FAIL')
    sys.exit(1)
else:
    print('RESULT: ALL PASS')
