"""ActionParser unit tests - cover all known formats and edge cases"""

import sys
import os
import importlib.util

_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _root)
_ap_spec = importlib.util.spec_from_file_location(
    "action_parser", os.path.join(_root, "utils", "action_parser.py"))
_ap = importlib.util.module_from_spec(_ap_spec)
_ap_spec.loader.exec_module(_ap)

parse = _ap.parse
_pre_clean = _ap._pre_clean
_extract_json_bracket_balanced = _ap._extract_json_bracket_balanced

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


# -- parse() tests --
check('standard CLICK', parse('{"action": "CLICK", "parameters": {"point": [500, 300]}}'), ('CLICK', {'point': [500, 300]}))

check('standard TYPE', parse('{"action": "TYPE", "parameters": {"text": "hello"}}'), ('TYPE', {'text': 'hello'}))

check('standard SCROLL', parse('{"action": "SCROLL", "parameters": {"start_point": [100, 800], "end_point": [100, 200]}}'), ('SCROLL', {'start_point': [100, 800], 'end_point': [100, 200]}))

check('standard OPEN', parse('{"action": "OPEN", "parameters": {"app_name": "微信"}}'), ('OPEN', {'app_name': '微信'}))

check('standard COMPLETE', parse('{"action": "COMPLETE", "parameters": {}}'), ('COMPLETE', {}))

check('standard COMPLETE no params', parse('{"action": "COMPLETE"}'), ('COMPLETE', {}))

check('standard lowercase action', parse('{"action": "click", "parameters": {"point": [100, 200]}}'), ('CLICK', {'point': [100, 200]}))

check('action-key CLICK dict', parse('{"CLICK": {"point": [851, 128]}}'), ('CLICK', {'point': [851, 128]}))

check('action-key TYPE dict', parse('{"TYPE": {"text": "狂飙"}}'), ('TYPE', {'text': '狂飙'}))

check('action-key CLICK array', parse('{"CLICK": [293, 74]}'), ('CLICK', {'point': [293, 74]}))

check('action-key COMPLETE empty', parse('{"COMPLETE": {}}'), ('COMPLETE', {}))

check('action-key COMPLETE empty str', parse('{"COMPLETE": ""}'), ('COMPLETE', {}))

check('action-key lowercase', parse('{"click": {"point": [100, 200]}}'), ('CLICK', {'point': [100, 200]}))

check('action-key CLICK array 3+', parse('{"CLICK": [100, 200, 300]}'), ('CLICK', {'point': [100, 200]}))

check('colon-json CLICK', parse('CLICK: {"point": [838, 45]}'), ('CLICK', {'point': [838, 45]}))

check('colon-json TYPE', parse('TYPE: {"text": "孟子义"}'), ('TYPE', {'text': '孟子义'}))

check('colon-json lowercase', parse('click: {"point": [100, 200]}'), ('CLICK', {'point': [100, 200]}))

check('func-call CLICK', parse('CLICK(point=[326, 918])'), ('CLICK', {'point': [326, 918]}))

check('func-call TYPE', parse('TYPE(text="跳舞")'), ('TYPE', {'text': '跳舞'}))

check('func-call TYPE single quote', parse("TYPE(text='跳舞')"), ('TYPE', {'text': '跳舞'}))

check('func-call TYPE double braces preserved', parse("TYPE(text='{{name}}')"), ('TYPE', {'text': '{{name}}'}))

check('func-call COMPLETE empty braces', parse('COMPLETE{}'), ('COMPLETE', {}))

check('func-call TYPE no-paren braces', parse('TYPE{"text": "跳舞"}'), ('TYPE', {'text': '跳舞'}))

check('func-call CLICK no-paren braces', parse('CLICK{"point": [326, 918]}'), ('CLICK', {'point': [326, 918]}))

check('action-line CLICK', parse('Action: click(point=[500, 300])'), ('CLICK', {'point': [500, 300]}))

check('action-line SCROLL', parse('Action: scroll(start_point=[100, 800], end_point=[100, 200])'), ('SCROLL', {'start_point': [100, 800], 'end_point': [100, 200]}))

check('action-line TYPE', parse('Action: type(text="hello")'), ('TYPE', {'text': 'hello'}))

check('raw CLICK', parse('CLICK:[[500, 300]]'), ('CLICK', {'point': [500, 300]}))

check('raw SCROLL', parse('SCROLL:[[100, 800], [100, 200]]'), ('SCROLL', {'start_point': [100, 800], 'end_point': [100, 200]}))

check('raw TYPE single quote', parse("TYPE:['搜索词']"), ('TYPE', {'text': '搜索词'}))

check('raw TYPE double quote', parse('TYPE:["搜索词"]'), ('TYPE', {'text': '搜索词'}))

check('raw OPEN single quote', parse("OPEN:['微信']"), ('OPEN', {'app_name': '微信'}))

check('raw OPEN double quote', parse('OPEN:["微信"]'), ('OPEN', {'app_name': '微信'}))

check('point tag', parse('<point>500 300</point>'), ('CLICK', {'point': [500, 300]}))

check('think tag removal', parse('<think>我需要点击搜索按钮</think>{"action": "CLICK", "parameters": {"point": [100, 200]}}'), ('CLICK', {'point': [100, 200]}))

check('think close tag only', parse('</think>{"action": "CLICK", "parameters": {"point": [100, 200]}}'), ('CLICK', {'point': [100, 200]}))

check('think with attrs', parse('<think type="reasoning">分析截图</think>{"CLICK": {"point": [50, 60]}}'), ('CLICK', {'point': [50, 60]}))

check('markdown json block', parse('```json\n{"action": "CLICK", "parameters": {"point": [100, 200]}}\n```'), ('CLICK', {'point': [100, 200]}))

check('markdown plain block', parse('```\n{"action": "CLICK", "parameters": {"point": [100, 200]}}\n```'), ('CLICK', {'point': [100, 200]}))

check('missing comma 2', parse('{"action": "CLICK", "parameters": {"point": [371 73]}}'), ('CLICK', {'point': [371, 73]}))

check('missing comma 4', parse('{"action": "SCROLL", "parameters": {"start_point": [100 200], "end_point": [300 400]}}'), ('SCROLL', {'start_point': [100, 200], 'end_point': [300, 400]}))

check('trailing comma obj', parse('{"action": "CLICK", "parameters": {"point": [100, 200]},}'), ('CLICK', {'point': [100, 200]}))

check('trailing comma arr', parse('{"action": "CLICK", "parameters": {"point": [100, 200,]}}'), ('CLICK', {'point': [100, 200]}))

check('double brace prefix', parse('CLICK: {{"point": [838, 45]}}'), ('CLICK', {'point': [838, 45]}))

check('double brace TYPE', parse('TYPE: {{"text": "测试"}}'), ('TYPE', {'text': '测试'}))

check('double brace full object', parse('{{"action": "CLICK", "parameters": {"point": [354, 71]}}}'), ('CLICK', {'point': [354, 71]}))

check('double brace nested parameters object', parse('{{"action": "CLICK", "parameters": {{"point": [275, 73]}}}}'), ('CLICK', {'point': [275, 73]}))

check('double brace full object preserves inner text', parse('{{"action": "TYPE", "parameters": {"text": "{{name}}"}}}'), ('TYPE', {'text': '{{name}}'}))

check('nested action-key parameters', parse('{"TYPE": {"parameters": {"text": "邯郸"}}}'), ('TYPE', {'text': '邯郸'}))

check('embedded action field click', parse('{"action": "CLICK(point=[[354, 71]]", "parameters": {}}'), ('CLICK', {'point': [354, 71]}))

check('bracket-balanced embedded', parse('Let me think. {"action": "CLICK", "parameters": {"point": [500, 300]}} That looks right.'), ('CLICK', {'point': [500, 300]}))

check('bracket-balanced action-key embedded', parse('根据分析 {"CLICK": {"point": [100, 200]}} 点击搜索框'), ('CLICK', {'point': [100, 200]}))

check('embedded malformed nested double brace object', parse('分析后给出结果：{{"action":"CLICK","parameters":{{"point":[275,73]}}}}'), ('CLICK', {'point': [275, 73]}))

check('string-aware braces', parse('分析：这个 {"thought": "内容有{花括号}", "action": "CLICK", "parameters": {"point": [100, 200]}}'), ('CLICK', {'point': [100, 200]}))

check('mixed think+action-key', parse('<think>分析截图</think>{"CLICK": {"point": [851, 128]}}'), ('CLICK', {'point': [851, 128]}))

check('mixed markdown+colon-json', parse('```json\nCLICK: {"point": [838, 45]}\n```'), ('CLICK', {'point': [838, 45]}))

check('empty string', parse(''), None)

check('whitespace only', parse('   '), None)

check('invalid action', parse('{"action": "JUMP", "parameters": {}}'), None)

check('random text', parse('这是一段随机文字'), None)

check('just braces', parse('{}'), None)

# -- _pre_clean() tests --
check('pre-clean think', _pre_clean('<think>reasoning</think>rest'), 'rest')

check('pre-clean markdown', _pre_clean('```json\nhello\n```'), 'hello\n')

check('pre-clean double brace', _pre_clean('CLICK: {{}}'), 'CLICK: {}')

check('pre-clean missing comma', _pre_clean('[371 73]'), '[371, 73]')

check('pre-clean trailing comma obj', _pre_clean('{"a": 1,}'), '{"a": 1}')

check('pre-clean trailing comma arr', _pre_clean('[1, 2,]'), '[1, 2]')

# -- _extract_json_bracket_balanced() tests --
check('bb basic', _extract_json_bracket_balanced('hello {"a": 1} world'), {'a': 1})

check('bb string with brace', _extract_json_bracket_balanced('pre {"a": "x{y}z"} post'), {'a': 'x{y}z'})

check('bb nested', _extract_json_bracket_balanced('pre {"a": {"b": 2}} post'), {'a': {'b': 2}})

check('bb no json', _extract_json_bracket_balanced('no json here'), None)

check('bb escape in string', _extract_json_bracket_balanced('{"a": "he said \\"hello\\""}'), {'a': 'he said "hello"'})


sep = "=" * 40
print(f"\n{sep}")
print(f"ActionParser tests: {passed} passed, {failed} failed, {passed + failed} total")
if failed:
    print("RESULT: FAIL")
    sys.exit(1)
else:
    print("RESULT: ALL PASS")
