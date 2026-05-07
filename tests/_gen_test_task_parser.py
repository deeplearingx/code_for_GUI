"""Generate tests/test_task_parser.py - run once then delete this file"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "test_task_parser.py")

L = []
L.append('"""TaskParser unit tests"""')
L.append("")
L.append("import sys")
L.append("import os")
L.append("import importlib.util")
L.append("")
L.append('_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")')
L.append("sys.path.insert(0, _root)")
L.append('_tp_spec = importlib.util.spec_from_file_location(')
L.append('    "task_parser", os.path.join(_root, "utils", "task_parser.py"))')
L.append("_tp = importlib.util.module_from_spec(_tp_spec)")
L.append("_tp_spec.loader.exec_module(_tp)")
L.append("")
L.append("parse_task = _tp.parse_task")
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

# Test cases: (label, instruction, expected_field, expected_value)
# We'll check specific fields rather than the whole TaskInfo object

tests = [
    # Comment tasks (priority over video search)
    ("comment post - iqiyi",
     "在爱奇艺搜索采莲曲，发布评论：好看",
     ["task_type", "app_name", "search_keyword", "comment_text", "type_queue"],
     ["comment", "爱奇艺", "采莲曲", "好看", ["采莲曲", "好看"]]),

    ("comment page only",
     "在哔哩哔哩搜索视频，打开评论区",
     ["task_type", "type_queue"],
     ["comment", ["视频"]]),

    # Meituan - regex pattern
    ("meituan shop+item",
     "在美团购买窑村干锅猪蹄店铺里的干锅排骨",
     ["task_type", "shop_name", "item_name", "type_queue"],
     ["meituan", "窑村干锅猪蹄", "干锅排骨", ["窑村干锅猪蹄", "干锅排骨"]]),

    ("meituan at shop",
     "去美团外卖在张亮麻辣烫店铺里点一份鱼豆腐",
     ["task_type", "shop_name", "item_name"],
     ["meituan", "张亮麻辣烫", "鱼豆腐"]),

    # Baidu Map - regex pattern
    ("baidu_map from A to B",
     "在百度地图从北京大学到天安门",
     ["task_type", "origin", "destination", "type_queue"],
     ["baidu_map", "北京大学", "天安门", ["北京大学", "天安门"]]),

    ("baidu_map taxi",
     "在百度地图打车从公司去机场",
     ["task_type", "origin", "destination"],
     ["baidu_map", "公司", "机场"]),

    # Video search - book title priority
    ("video book title",
     '在哔哩哔哩搜索《采莲曲》',
     ["task_type", "search_keyword", "type_queue"],
     ["video_search", "采莲曲", ["采莲曲"]]),

    ("video search + episode",
     "在腾讯视频搜索庆余年第5集",
     ["task_type", "search_keyword", "episode"],
     ["video_search", "庆余年", "第5集"]),

    ("video search long trigger",
     "在爱奇艺搜索一下狂飙",
     ["task_type", "search_keyword"],
     ["video_search", "狂飙"]),

    # Travel - flight regex
    ("travel flight",
     "在去哪儿旅行查北京飞上海的航班",
     ["task_type", "origin", "destination", "type_queue"],
     ["travel", "北京", "上海", ["北京", "上海"]]),

    ("travel from A to B",
     "在去哪儿旅行从成都到重庆",
     ["task_type", "origin", "destination"],
     ["travel", "成都", "重庆"]),

    # App alias matching
    ("app alias B站",
     "在B站搜索舞蹈视频",
     ["app_name", "task_type", "search_keyword"],
     ["哔哩哔哩", "video_search", "舞蹈视频"]),

    ("app alias 12306",
     "在铁路12306买票",
     ["app_name"],
     ["铁路12306"]),

    ("app alias 美团外卖",
     "用美团外卖点餐",
     ["app_name", "task_type"],
     ["美团", "meituan"]),

    # Generic search fallback
    ("generic search",
     "搜索天气预报",
     ["task_type", "search_keyword", "type_queue"],
     ["general", "天气预报", ["天气预报"]]),

    # Long trigger priority - should not truncate
    ("long trigger no truncate",
     "搜索一下采莲曲",
     ["search_keyword"],
     ["采莲曲"]),

    # No search content
    ("no search",
     "打开微信",
     ["app_name", "type_queue"],
     ["", []]),
]

L.append("# -- parse_task() tests --")
for label, instruction, fields, values in tests:
    L.append(f"# {label}")
    # Generate field-by-field checks
    task_access = f"parse_task({instruction!r})"
    for field, value in zip(fields, values):
        L.append(f"check({label!r} {field!r}, {task_access}.{field}, {value!r})")
    L.append("")

# Result summary
L.append('sep = "=" * 40')
L.append('print(f"\\n{sep}")')
L.append('print(f"TaskParser tests: {passed} passed, {failed} failed, {passed + failed} total")')
L.append("if failed:")
L.append('    print("RESULT: FAIL")')
L.append("    sys.exit(1)")
L.append("else:")
L.append('    print("RESULT: ALL PASS")')

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(L) + "\n")

print(f"Generated {OUT} with {len(tests)} test groups")
