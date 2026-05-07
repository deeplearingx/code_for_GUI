"""Generate tests/test_action_parser.py - run once then delete this file"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "test_action_parser.py")

# Use hex escapes for chars that confuse the Write tool
THINK_OPEN = "\x3cthink\x3e"
THINK_CLOSE = "\x3c/think\x3e"
THINK_OPEN_ATTR = '\x3cthink type="reasoning"\x3e'
BACKTICK3 = "\x60\x60\x60"

# Build file content as list of lines
L = []
L.append('"""ActionParser unit tests - cover all known formats and edge cases"""')
L.append("")
L.append("import sys")
L.append("import os")
L.append("import importlib.util")
L.append("")
L.append('_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")')
L.append("sys.path.insert(0, _root)")
L.append("_ap_spec = importlib.util.spec_from_file_location(")
L.append('    "action_parser", os.path.join(_root, "utils", "action_parser.py"))')
L.append("_ap = importlib.util.module_from_spec(_ap_spec)")
L.append("_ap_spec.loader.exec_module(_ap)")
L.append("")
L.append("parse = _ap.parse")
L.append("_pre_clean = _ap._pre_clean")
L.append("_extract_json_bracket_balanced = _ap._extract_json_bracket_balanced")
L.append("")
L.append("passed = 0")
L.append("failed = 0")
L.append("")
L.append("")
L.append("def check(label, got, expected):")
L.append("    global passed, failed")
L.append("    if got == expected:")
L.append("        passed += 1")
L.append("    else:")
L.append("        failed += 1")
L.append('        print(f"FAIL: {label}")')
L.append('        print(f"  expected: {expected}")')
L.append('        print(f"  got:      {got}")')
L.append("")
L.append("")

# --- Test data ---
# (label, input_text, expected_result)
tests = [
    # 1. Standard JSON
    ("standard CLICK",
     '{"action": "CLICK", "parameters": {"point": [500, 300]}}',
     ("CLICK", {"point": [500, 300]})),
    ("standard TYPE",
     '{"action": "TYPE", "parameters": {"text": "hello"}}',
     ("TYPE", {"text": "hello"})),
    ("standard SCROLL",
     '{"action": "SCROLL", "parameters": {"start_point": [100, 800], "end_point": [100, 200]}}',
     ("SCROLL", {"start_point": [100, 800], "end_point": [100, 200]})),
    ("standard OPEN",
     '{"action": "OPEN", "parameters": {"app_name": "微信"}}',
     ("OPEN", {"app_name": "微信"})),
    ("standard COMPLETE",
     '{"action": "COMPLETE", "parameters": {}}',
     ("COMPLETE", {})),
    ("standard COMPLETE no params",
     '{"action": "COMPLETE"}',
     ("COMPLETE", {})),
    ("standard lowercase action",
     '{"action": "click", "parameters": {"point": [100, 200]}}',
     ("CLICK", {"point": [100, 200]})),

    # 2. action-as-key
    ("action-key CLICK dict",
     '{"CLICK": {"point": [851, 128]}}',
     ("CLICK", {"point": [851, 128]})),
    ("action-key TYPE dict",
     '{"TYPE": {"text": "狂飙"}}',
     ("TYPE", {"text": "狂飙"})),
    ("action-key CLICK array",
     '{"CLICK": [293, 74]}',
     ("CLICK", {"point": [293, 74]})),
    ("action-key COMPLETE empty",
     '{"COMPLETE": {}}',
     ("COMPLETE", {})),
    ("action-key COMPLETE empty str",
     '{"COMPLETE": ""}',
     ("COMPLETE", {})),
    ("action-key lowercase",
     '{"click": {"point": [100, 200]}}',
     ("CLICK", {"point": [100, 200]})),
    ("action-key CLICK array 3+",
     '{"CLICK": [100, 200, 300]}',
     ("CLICK", {"point": [100, 200]})),

    # 3. ACTION: {json}
    ("colon-json CLICK",
     'CLICK: {"point": [838, 45]}',
     ("CLICK", {"point": [838, 45]})),
    ("colon-json TYPE",
     'TYPE: {"text": "孟子义"}',
     ("TYPE", {"text": "孟子义"})),
    ("colon-json lowercase",
     'click: {"point": [100, 200]}',
     ("CLICK", {"point": [100, 200]})),

    # 4. Function call
    ("func-call CLICK",
     "CLICK(point=[326, 918])",
     ("CLICK", {"point": [326, 918]})),
    ("func-call TYPE",
     'TYPE(text="跳舞")',
     ("TYPE", {"text": "跳舞"})),
    ("func-call TYPE single quote",
     "TYPE(text='跳舞')",
     ("TYPE", {"text": "跳舞"})),
    ("func-call COMPLETE empty braces",
     "COMPLETE{}",
     ("COMPLETE", {})),
    ("func-call TYPE no-paren braces",
     'TYPE{"text": "跳舞"}',
     ("TYPE", {"text": "跳舞"})),
    ("func-call CLICK no-paren braces",
     'CLICK{"point": [326, 918]}',
     ("CLICK", {"point": [326, 918]})),

    # 5. Action line
    ("action-line CLICK",
     "Action: click(point=[500, 300])",
     ("CLICK", {"point": [500, 300]})),
    ("action-line SCROLL",
     "Action: scroll(start_point=[100, 800], end_point=[100, 200])",
     ("SCROLL", {"start_point": [100, 800], "end_point": [100, 200]})),
    ("action-line TYPE",
     'Action: type(text="hello")',
     ("TYPE", {"text": "hello"})),

    # 6. Raw format
    ("raw CLICK",
     "CLICK:[[500, 300]]",
     ("CLICK", {"point": [500, 300]})),
    ("raw SCROLL",
     "SCROLL:[[100, 800], [100, 200]]",
     ("SCROLL", {"start_point": [100, 800], "end_point": [100, 200]})),
    ("raw TYPE single quote",
     "TYPE:['搜索词']",
     ("TYPE", {"text": "搜索词"})),
    ("raw TYPE double quote",
     'TYPE:["搜索词"]',
     ("TYPE", {"text": "搜索词"})),
    ("raw OPEN single quote",
     "OPEN:['微信']",
     ("OPEN", {"app_name": "微信"})),
    ("raw OPEN double quote",
     'OPEN:["微信"]',
     ("OPEN", {"app_name": "微信"})),

    # 7. Point tag
    ("point tag",
     "<point>500 300</point>",
     ("CLICK", {"point": [500, 300]})),

    # 8. Think tags
    ("think tag removal",
     THINK_OPEN + "我需要点击搜索按钮" + THINK_CLOSE
     + '{"action": "CLICK", "parameters": {"point": [100, 200]}}',
     ("CLICK", {"point": [100, 200]})),
    ("think close tag only",
     THINK_CLOSE + '{"action": "CLICK", "parameters": {"point": [100, 200]}}',
     ("CLICK", {"point": [100, 200]})),
    ("think with attrs",
     THINK_OPEN_ATTR + "分析截图" + THINK_CLOSE
     + '{"CLICK": {"point": [50, 60]}}',
     ("CLICK", {"point": [50, 60]})),

    # 9. Markdown code block
    ("markdown json block",
     BACKTICK3 + 'json\n{"action": "CLICK", "parameters": {"point": [100, 200]}}\n' + BACKTICK3,
     ("CLICK", {"point": [100, 200]})),
    ("markdown plain block",
     BACKTICK3 + '\n{"action": "CLICK", "parameters": {"point": [100, 200]}}\n' + BACKTICK3,
     ("CLICK", {"point": [100, 200]})),

    # 10. Missing comma
    ("missing comma 2",
     '{"action": "CLICK", "parameters": {"point": [371 73]}}',
     ("CLICK", {"point": [371, 73]})),
    ("missing comma 4",
     '{"action": "SCROLL", "parameters": {"start_point": [100 200], "end_point": [300 400]}}',
     ("SCROLL", {"start_point": [100, 200], "end_point": [300, 400]})),

    # 11. Trailing comma
    ("trailing comma obj",
     '{"action": "CLICK", "parameters": {"point": [100, 200]},}',
     ("CLICK", {"point": [100, 200]})),
    ("trailing comma arr",
     '{"action": "CLICK", "parameters": {"point": [100, 200,]}}',
     ("CLICK", {"point": [100, 200]})),

    # 12. Double brace
    ("double brace prefix",
     'CLICK: {{"point": [838, 45]}}',
     ("CLICK", {"point": [838, 45]})),
    ("double brace TYPE",
     'TYPE: {{"text": "测试"}}',
     ("TYPE", {"text": "测试"})),

    # 13. Bracket balanced embedded
    ("bracket-balanced embedded",
     'Let me think. {"action": "CLICK", "parameters": {"point": [500, 300]}} That looks right.',
     ("CLICK", {"point": [500, 300]})),
    ("bracket-balanced action-key embedded",
     '根据分析 {"CLICK": {"point": [100, 200]}} 点击搜索框',
     ("CLICK", {"point": [100, 200]})),

    # 14. String-aware bracket extraction
    ("string-aware braces",
     '分析：这个 {"thought": "内容有{花括号}", "action": "CLICK", "parameters": {"point": [100, 200]}}',
     ("CLICK", {"point": [100, 200]})),

    # 15. Mixed
    ("mixed think+action-key",
     THINK_OPEN + "分析截图" + THINK_CLOSE + '{"CLICK": {"point": [851, 128]}}',
     ("CLICK", {"point": [851, 128]})),
    ("mixed markdown+colon-json",
     BACKTICK3 + 'json\nCLICK: {"point": [838, 45]}\n' + BACKTICK3,
     ("CLICK", {"point": [838, 45]})),

    # 16. Edge cases
    ("empty string", "", None),
    ("whitespace only", "   ", None),
    ("invalid action", '{"action": "JUMP", "parameters": {}}', None),
    ("random text", "这是一段随机文字", None),
    ("just braces", "{}", None),
]

pre_clean_tests = [
    ("pre-clean think",
     THINK_OPEN + "reasoning" + THINK_CLOSE + "rest",
     "rest"),
    ("pre-clean markdown",
     BACKTICK3 + "json\nhello\n" + BACKTICK3,
     "hello\n"),
    ("pre-clean double brace",
     "CLICK: {{}}",
     "CLICK: {}"),
    ("pre-clean missing comma",
     "[371 73]",
     "[371, 73]"),
    ("pre-clean trailing comma obj",
     '{"a": 1,}',
     '{"a": 1}'),
    ("pre-clean trailing comma arr",
     "[1, 2,]",
     "[1, 2]"),
]

bb_tests = [
    ("bb basic",
     'hello {"a": 1} world',
     {"a": 1}),
    ("bb string with brace",
     'pre {"a": "x{y}z"} post',
     {"a": "x{y}z"}),
    ("bb nested",
     'pre {"a": {"b": 2}} post',
     {"a": {"b": 2}}),
    ("bb no json",
     "no json here",
     None),
    ("bb escape in string",
     '{"a": "he said \\"hello\\""}',
     {"a": 'he said "hello"'}),
]

# --- Emit parse() tests ---
L.append("# -- parse() tests --")
for label, input_text, expected in tests:
    L.append(f"check({label!r}, parse({input_text!r}), {expected!r})")
    L.append("")

# --- Emit _pre_clean() tests ---
L.append("# -- _pre_clean() tests --")
for label, input_text, expected in pre_clean_tests:
    L.append(f"check({label!r}, _pre_clean({input_text!r}), {expected!r})")
    L.append("")

# --- Emit bracket balanced tests ---
L.append("# -- _extract_json_bracket_balanced() tests --")
for label, input_text, expected in bb_tests:
    L.append(f"check({label!r}, _extract_json_bracket_balanced({input_text!r}), {expected!r})")
    L.append("")

# --- Result summary ---
L.append("")
L.append('sep = "=" * 40')
L.append('print(f"\\n{sep}")')
L.append('print(f"ActionParser tests: {passed} passed, {failed} failed, {passed + failed} total")')
L.append("if failed:")
L.append('    print("RESULT: FAIL")')
L.append("    sys.exit(1)")
L.append("else:")
L.append('    print("RESULT: ALL PASS")')

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(L) + "\n")

print(f"Generated {OUT}")
print(f"  {len(tests)} parse tests, {len(pre_clean_tests)} pre_clean tests, {len(bb_tests)} bracket tests")
