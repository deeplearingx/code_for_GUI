"""AnalyzeFailures unit tests"""

import sys
import os
import importlib.util

_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _root)
_af_spec = importlib.util.spec_from_file_location(
    "analyze_failures", os.path.join(_root, "scripts", "analyze_failures.py"))
_af = importlib.util.module_from_spec(_af_spec)
_af_spec.loader.exec_module(_af)

passed = 0
failed = 0


SYNTHETIC_LOG = """2026-05-08 10:00:00,000 - INFO - Start testing case: old_case
2026-05-08 10:00:01,000 - ERROR - [Checker] CLICK failed: old click miss
2026-05-08 10:00:02,000 - INFO - [No. 1: old_case] Score: 1/2 = 0.50
2026-05-08 10:00:03,000 - INFO - Step Level Accuracy: 0.10
2026-05-08 10:00:04,000 - INFO - Case Level Accuracy: 0.09
2026-05-08 12:00:00,000 - INFO - Start testing case: step_case_a
2026-05-08 12:00:01,000 - ERROR - [Checker] Action mismatch: expect [CLICK], got [TYPE]
2026-05-08 12:00:02,000 - INFO - [No. 1: step_case_a] Score: 7/10 = 0.70
2026-05-08 12:00:03,000 - INFO - Start testing case: step_case_b
2026-05-08 12:00:04,000 - ERROR - [Checker] Action mismatch: expect [TYPE], got [CLICK]
2026-05-08 12:00:05,000 - ERROR - [Checker] Action mismatch: expect [COMPLETE], got [CLICK]
2026-05-08 12:00:06,000 - ERROR - [Checker] CLICK failed: latest click miss
2026-05-08 12:00:07,000 - WARNING - 解析失败，原始输出: bad json
2026-05-08 12:00:08,000 - INFO - ACTION_POLICY decision changed=True original_action=TYPE original_params={'text': '狂飙'} corrected_action=CLICK corrected_params={'point': [200, 80]} reason=activate_search_bar_before_type confidence=high
2026-05-08 12:00:08,500 - INFO - ACTION_POLICY accepted final_action=CLICK final_params={'point': [200, 80]} reason=activate_search_bar_before_type
2026-05-08 12:00:08,800 - INFO - ACTION_POLICY decision changed=True original_action=CLICK original_params={'point': [1, 2]} corrected_action=CLICK corrected_params={} reason=force_invalid_click confidence=high
2026-05-08 12:00:08,900 - INFO - ACTION_POLICY rejected final_action=CLICK final_params={'point': [1, 2]} reason=force_invalid_click confidence=high retry_reason=CLICK missing point parameter
2026-05-08 12:00:09,000 - INFO - [No. 2: step_case_b] Score: 3/5 = 0.60
2026-05-08 12:00:09,100 - INFO - Step Level Accuracy: 0.80
2026-05-08 12:00:09,200 - INFO - Case Level Accuracy: 0.36
2026-05-08 13:00:00,000 - INFO - Start testing case: trailing_case
2026-05-08 13:00:01,000 - ERROR - [Checker] Action mismatch: expect [CLICK], got [TYPE]
"""



def check(label, got, expected):
    global passed, failed
    if got == expected:
        passed += 1
    else:
        failed += 1
        print(f"FAIL: {label}")
        print(f"  expected: {expected}")
        print(f"  got:      {got}")


report = _af.analyze_text(SYNTHETIC_LOG)
check('latest step accuracy', report['step_accuracy'], 0.80)
check('latest case accuracy', report['case_accuracy'], 0.36)
check('latest case scores', report['case_scores'], {
    'step_case_a': {'earned': 7, 'total': 10, 'ratio': 0.70},
    'step_case_b': {'earned': 3, 'total': 5, 'ratio': 0.60},
})
check('failure count click failed', report['category_counts']['CLICK failed'], 1)
check('failure count expect click got type', report['category_counts']['expect CLICK, got TYPE'], 1)
check('failure count expect type got click', report['category_counts']['expect TYPE, got CLICK'], 1)
check('failure count expect complete got click', report['category_counts']['expect COMPLETE, got CLICK'], 1)
check('failure count parser failed', report['category_counts']['Parser failed'], 1)
check('action policy observability', report['action_policy'], {
    'corrected_steps': 2,
    'accepted_corrections': 1,
    'rejected_corrections': 1,
    'rejected_correction_cases': ['step_case_b'],
    'reasons': {
        'activate_search_bar_before_type': 1,
        'force_invalid_click': 1,
    },
})

sep = '=' * 40
print(f"\n{sep}")
print(f"AnalyzeFailures tests: {passed} passed, {failed} failed, {passed + failed} total")
if failed:
    print('RESULT: FAIL')
    sys.exit(1)
else:
    print('RESULT: ALL PASS')
