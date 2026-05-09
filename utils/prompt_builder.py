"""Prompt构建模块 - 系统prompt、JSON输出协议、消息构造"""

from typing import Dict, Any, List

from .grounder import get_anchor, get_app_profile, get_app_tip
from .task_parser import TaskInfo

APP_TIPS: dict[str, str] = {
    "美团": "美团任务流程：进外卖→搜店铺→进店铺→选商品→加购物车→去结算→默认地址",
    "百度地图": "百度地图打车：进打车→输起点→选第一个→输终点→选第一个→确认叫车",
    "哔哩哔哩": "B站：点搜索→输关键词→点搜索→综合列表第一个→收藏在详情页操作栏",
    "腾讯视频": "腾讯视频：搜入口右上→输剧名→点搜索→进剧集→选对应集数",
    "爱奇艺": "爱奇艺：搜索框→输关键词→搜索→第一个结果→选集数或收藏",
    "芒果TV": "芒果TV：搜索→输关键词→搜索→第一个结果→执行目标操作",
    "喜马拉雅": "喜马拉雅：搜索→输关键词→搜索→第一个结果→执行目标操作",
    "去哪儿旅行": "去哪儿旅行：点出发地→点顶部搜索栏→输入并选第一个结果→点目的地→点顶部搜索栏→输入并选第一个结果",
    "抖音": "抖音：点搜索→输关键词→搜索→点第一个结果",
    "快手": "快手：点搜索→输关键词→搜索→点第一个结果",
    "淘宝": "淘宝：点搜索→输关键词→搜索→点第一个商品",
    "京东": "京东：点搜索→输关键词→搜索→点第一个商品",
    "拼多多": "拼多多：点搜索→输关键词→搜索→点第一个商品",
    "大众点评": "大众点评：搜索→输店名→搜索→点第一个结果",
    "铁路12306": "12306：选出发地→选目的地→选日期→查询→选车次",
}

SEARCH_BAR_COORDS: dict[str, list[int]] = {
    "美团": [500, 120],
    "百度地图": [500, 100],
    # B站公开流的搜索框在顶部中间区域，不是右上角图标。
    "哔哩哔哩": [500, 80],
    "腾讯视频": [850, 80],
    "抖音": [200, 80],
    "快手": [500, 100],
    # 爱奇艺搜索输入框更靠近顶部，y=100 会落到结果/内容区域。
    "爱奇艺": [500, 70],
    "芒果TV": [500, 80],
    "喜马拉雅": [500, 80],
    "去哪儿旅行": [500, 100],
    "淘宝": [500, 120],
    "京东": [500, 120],
    "拼多多": [500, 120],
    "大众点评": [500, 100],
    "铁路12306": [500, 100],
    "default": [500, 100],
}

FLOW_CONTINUE_COORDS: dict[str, list[int]] = {
    "美团": [500, 260],
    # 百度地图公开流第一步应点顶部路线/打车入口，旧的 [500,220] 容易落到首页内容区。
    "百度地图": [850, 40],
    "去哪儿旅行": [500, 220],
    "default": [500, 220],
}

FLOW_INPUT_COORDS: dict[str, list[int]] = {
    "去哪儿旅行": [252, 291],
    "default": [500, 220],
}



TRAVEL_FIELD_COORDS: dict[int, list[int]] = {
    0: [252, 291],
    1: [741, 290],
}

TRAVEL_SEARCH_BAR_COORD = [500, 165]
TRAVEL_RESULT_COORD = [500, 180]
TRAVEL_DATE_ENTRY_COORD = [277, 361]
TRAVEL_DATE_OPTION_COORDS: dict[str, list[int]] = {
    "今天": [433, 224],
    "明天": [574, 224],
    "后天": [902, 303],
    "大后天": [293, 284],
}
TRAVEL_DATE_CONFIRM_COORD = [503, 842]
TRAVEL_SEARCH_BUTTON_COORD = [494, 611]

SYSTEM_PROMPT_TEMPLATE = """你是安卓手机 GUI Agent。根据用户任务、当前截图和历史动作，输出下一步操作。
只能输出一个 JSON 对象，不要输出 Markdown，不要多余解释。

必须使用标准 JSON 格式：
{{"action": "CLICK", "parameters": {{"point": [x, y]}}}}
{{"action": "TYPE", "parameters": {{"text": "内容"}}}}
{{"action": "SCROLL", "parameters": {{"start_point": [x1, y1], "end_point": [x2, y2]}}}}
{{"action": "OPEN", "parameters": {{"app_name": "应用名"}}}}
{{"action": "COMPLETE", "parameters": {{}}}}

禁止使用 {{"CLICK": {{...}}}}、CLICK:{{...}}、CLICK(point=[...]) 等非标格式。

坐标规则：
- 0~1000 归一化坐标，左上[0,0]，右下[1000,1000]
- 点击控件中心
- 顶部搜索栏通常 y=50~150
- 底部导航栏通常 y=850~980
- 右上角关闭/跳过通常 x=800~980, y=20~120

决策规则：
1. 弹窗/广告/权限 → 优先关闭/跳过/暂不
2. 需要搜索 → 先点搜索框
3. 输入框已激活 → TYPE
4. 搜索结果出现 → 点最相关或第一个
5. 找不到目标 → SCROLL
6. 确认任务完成 → COMPLETE（不要过早）

COMPLETE规则：
- 当任务目标已经达成时，立即输出COMPLETE，不要继续做额外操作
- 搜索已执行且结果已点开 → COMPLETE
- 评论已发布 → COMPLETE
- 商品已加入购物车/已下单 → COMPLETE
- 路线已规划/已叫车 → COMPLETE
- 已收藏/已关注 → COMPLETE
- 不要因为还有可选操作而继续点击，任务目标达成即可

TYPE规则：
- 只有输入框已激活（光标闪烁）时才输出TYPE
- 不要连续输出TYPE，输入后应点搜索/发送/确定/下一个输入框
- 不要自己编造输入内容，严格按照【待输入队列】中的内容输入
"""


def build_system_prompt(task: TaskInfo) -> str:
    parts = [SYSTEM_PROMPT_TEMPLATE]

    if task.app_name:
        parts.append(f"\n## 目标App\n{task.app_name}")

    if task.task_type != "general":
        parts.append(f"\n## 任务类型\n{task.task_type}")

    if task.app_name:
        app_tip = get_app_tip(task.app_name)
        if app_tip:
            parts.append(f"\n## App流程提示\n{app_tip}")

    return "\n".join(parts)


def build_messages(
    task: TaskInfo,
    history_summary: str,
    step_count: int,
    image_url: str,
) -> List[Dict[str, Any]]:
    """构造messages列表：system + user(text+image)，不传assistant历史原文"""
    system_prompt = build_system_prompt(task)

    user_parts: list[str] = []

    user_parts.append(f"【用户任务】\n{task.instruction}")

    # 待输入队列提示
    if task.type_queue:
        total = len(task.type_queue)
        done = task.type_index
        pending_list = task.type_queue[task.type_index:]
        user_parts.append(
            f"【待输入队列】\n"
            f"全部待输入：{task.type_queue}\n"
            f"当前待输入：{pending_list[0] if pending_list else '无'}\n"
            f"已输入进度：{done}/{total}\n"
            f"注意：只有输入框已经激活时才输出 TYPE；不要自己编造输入内容。"
        )

    # 历史动作摘要
    if history_summary:
        user_parts.append(f"【历史动作】\n{history_summary}")

    user_parts.append(f"【当前步骤】第{step_count}步")

    user_content: list[Dict[str, Any]] = []
    if user_parts:
        user_content.append({"type": "text", "text": "\n".join(user_parts)})
    user_content.append({
        "type": "image_url",
        "image_url": {"url": image_url},
    })

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
    return messages


def build_retry_prompt(reason: str) -> str:
    """构建重试时的额外提示"""
    return (
        f"⚠️ 上次输出被拒绝：{reason}\n"
        "请严格按照标准JSON输出下一步操作，不要提前COMPLETE。"
        "输出格式：{\"action\": \"CLICK|TYPE|SCROLL|OPEN|COMPLETE\", \"parameters\": {...}}"
    )


def get_search_bar_coord(app_name: str) -> list[int]:
    return get_anchor(app_name, "search_input")


def get_flow_continue_coord(app_name: str) -> list[int]:
    return get_anchor(app_name, "flow_entry")


def get_flow_input_coord(app_name: str) -> list[int]:
    profile = get_app_profile(app_name)
    controls = profile.get("controls") if isinstance(profile.get("controls"), dict) else {}
    if "depart_field" in controls:
        return get_anchor(app_name, "depart_field")
    return get_anchor(app_name, "flow_entry")


def get_travel_field_coord(type_index: int) -> list[int]:
    return TRAVEL_FIELD_COORDS.get(type_index, TRAVEL_FIELD_COORDS[1])


def get_travel_search_bar_coord() -> list[int]:
    return list(TRAVEL_SEARCH_BAR_COORD)


def get_travel_result_coord() -> list[int]:
    return list(TRAVEL_RESULT_COORD)



def get_travel_date_entry_coord() -> list[int]:
    return list(TRAVEL_DATE_ENTRY_COORD)



def get_travel_date_option_coord(date_hint: str) -> list[int]:
    return list(TRAVEL_DATE_OPTION_COORDS.get(date_hint, TRAVEL_DATE_OPTION_COORDS["后天"]))



def get_travel_date_confirm_coord() -> list[int]:
    return list(TRAVEL_DATE_CONFIRM_COORD)


def get_travel_search_button_coord() -> list[int]:
    return list(TRAVEL_SEARCH_BUTTON_COORD)
