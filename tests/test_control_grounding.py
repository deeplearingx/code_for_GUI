"""ControlGrounding unit tests"""

import sys
import os

_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _root)

from utils.control_grounding import get_anchor

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


check('douyin search entry anchor', get_anchor('抖音', 'search_entry'), [898, 922])
check('douyin search input anchor', get_anchor('抖音', 'search_input'), [200, 80])
check('tencent video search entry anchor', get_anchor('腾讯视频', 'search_entry'), [902, 78])
check('tencent video search input anchor', get_anchor('腾讯视频', 'search_input'), [850, 80])
check('ximalaya search entry anchor', get_anchor('喜马拉雅', 'search_entry'), [854, 40])
check('ximalaya search input anchor', get_anchor('喜马拉雅', 'search_input'), [500, 100])
check('qunar depart field anchor', get_anchor('去哪儿旅行', 'depart_field'), [252, 291])
check('qunar search button anchor', get_anchor('去哪儿旅行', 'search_button'), [494, 611])
check('baidu flow entry anchor', get_anchor('百度地图', 'flow_entry'), [500, 220])
check('meituan flow entry anchor', get_anchor('美团', 'flow_entry'), [500, 260])
check('default anchor fallback', get_anchor('未知App', 'search_entry'), [500, 120])
check('explicit default fallback', get_anchor('未知App', 'flow_entry', [321, 654]), [321, 654])

sep = '=' * 40
print(f"\n{sep}")
print(f"ControlGrounding tests: {passed} passed, {failed} failed, {passed + failed} total")
if failed:
    print('RESULT: FAIL')
    sys.exit(1)
else:
    print('RESULT: ALL PASS')
