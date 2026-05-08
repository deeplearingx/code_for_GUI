"""任务解析模块 - 从用户指令中提取App名、TYPE队列、搜索关键词等"""

import re
from dataclasses import dataclass, field
from typing import Optional


APP_ALIASES: dict[str, list[str]] = {
    "爱奇艺": ["爱奇艺"],
    "百度地图": ["百度地图", "地图"],
    "哔哩哔哩": ["哔哩哔哩", "B站", "bilibili", "哔哩"],
    "抖音": ["抖音"],
    "快手": ["快手"],
    "芒果TV": ["芒果TV", "芒果"],
    "美团": ["美团外卖", "美团"],
    "去哪儿旅行": ["去哪儿旅行", "去哪旅行", "去哪儿", "去哪"],
    "腾讯视频": ["腾讯视频"],
    "喜马拉雅": ["喜马拉雅"],
    "淘宝": ["淘宝"],
    "京东": ["京东"],
    "拼多多": ["拼多多"],
    "大众点评": ["大众点评"],
    "铁路12306": ["铁路12306", "12306"],
}

# alias -> standard name, long alias first
_ALIAS_TO_STANDARD: dict[str, str] = {}
for _std, _aliases in APP_ALIASES.items():
    for _a in sorted(_aliases, key=len, reverse=True):
        _ALIAS_TO_STANDARD[_a] = _std

# Search triggers, long first
SEARCH_TRIGGERS = ("搜索一下", "搜一下", "搜索", "搜一搜", "搜")
# Comment triggers
COMMENT_POST_TRIGGERS = ("发布评论", "发表评论", "评论：", "评论:", "留言：", "留言:")
COMMENT_PAGE_TRIGGERS = ("评论区", "评论")

_TERMINAL = set("，。、！？；\n")


@dataclass
class TaskInfo:
    instruction: str
    app_name: str = ""
    task_type: str = "general"
    search_keyword: str = ""
    comment_text: str = ""
    origin: str = ""
    destination: str = ""
    shop_name: str = ""
    item_name: str = ""
    episode: str = ""
    type_queue: list[str] = field(default_factory=list)
    type_index: int = 0

    def peek_pending_text(self) -> Optional[str]:
        if self.type_index < len(self.type_queue):
            return self.type_queue[self.type_index]
        return None

    def commit_text(self) -> None:
        if self.type_index < len(self.type_queue):
            self.type_index += 1

    def has_pending_text(self) -> bool:
        return self.type_index < len(self.type_queue)


def _find_app_name(instruction: str) -> str:
    for alias, standard in _ALIAS_TO_STANDARD.items():
        if alias in instruction:
            return standard
    return ""


def _extract_after_trigger(text: str, triggers: tuple[str, ...]) -> str:
    """Long-trigger-first: find first trigger, extract content until terminator."""
    for kw in triggers:
        idx = text.find(kw)
        if idx == -1:
            continue
        start = idx + len(kw)
        while start < len(text) and text[start] in (" ", "：", ":", "为", "是", "到", "去", "的"):
            start += 1
        if start >= len(text):
            continue
        end = start
        while end < len(text) and text[end] not in _TERMINAL:
            end += 1
        return text[start:end].strip()
    return ""


def _extract_book_title(text: str) -> str:
    """Extract content inside book title marks as search keyword."""
    m = re.search(r"《(.+?)》", text)
    if m:
        return m.group(1)
    return ""


def _parse_comment_task(instruction: str, task: TaskInfo, has_content: bool) -> None:
    """Parse comment task: has_content=True extracts comment text, False just opens comment area."""
    task.task_type = "comment"
    search = _extract_after_trigger(instruction, SEARCH_TRIGGERS)
    if not search:
        search = _extract_book_title(instruction)
    if search:
        task.search_keyword = search
        task.type_queue.append(search)
    if has_content:
        comment = _extract_after_trigger(instruction, COMMENT_POST_TRIGGERS)
        if not comment:
            m = re.search(r"(?:评论说|评价|写评论|发评论|评论内容)[：:]*\s*(.+?)(?:，|。|！|？|$)", instruction)
            if m:
                comment = m.group(1).strip()
        if comment:
            task.comment_text = comment
            task.type_queue.append(comment)


def _parse_meituan(instruction: str, task: TaskInfo) -> None:
    task.task_type = "meituan"
    # Strip app name to avoid it being matched as shop name
    clean = instruction
    for alias in _ALIAS_TO_STANDARD:
        clean = clean.replace(alias, "")
    clean = re.sub(r"^(?:(?:在|去|用|打开|进入)\s*)+", "", clean)
    # Priority: buy from shop
    m = re.search(r"购买(.+?)(?:店铺|商家)(?:里|中|的)(.+?)(?:，|。|$)", clean)
    if not m:
        m = re.search(r"(.+?)(?:店铺|商家)(?:里|中)(.+?)(?:，|。|$)", clean)
    if not m:
        # Fallback: at/go-to shop
        m = re.search(r"(?:在|去)([^，。去在的]+?)(?:店铺|商家)(?:里|中|的)(.+?)(?:，|。|$)", clean)
    if m:
        shop, item = m.group(1).strip(), m.group(2).strip()
        # Strip leading 的/了/order prefixes from item
        item = re.sub(r"^[的了]", "", item)
        item = re.sub(r"^(?:点一份|点个|点一杯|买一份|买一个|点)", "", item)
        task.shop_name = shop
        task.type_queue.append(shop)
        task.item_name = item
        task.type_queue.append(item)
        return

    m = re.search(r"(.+)店里(.+?)(?:，|。|$)", clean)
    if m:
        shop, item = m.group(1).strip(), m.group(2).strip()
        if not shop.endswith(("店", "）")):
            shop = f"{shop}店"
        item = re.sub(r"^[的了]", "", item)
        item = re.sub(r"^(?:点一份|点个|点一杯|买一份|买一个|点)", "", item)
        task.shop_name = shop
        task.type_queue.append(shop)
        task.item_name = item
        task.type_queue.append(item)
        return

    # No regex match -> trigger-word extraction
    shop = _extract_after_trigger(instruction, ("店铺", "商家", "外卖店", "店名", "搜索"))
    if shop:
        task.shop_name = shop
        task.type_queue.append(shop)
    item = _extract_after_trigger(instruction, ("商品", "菜品", "食物", "东西"))
    if not item:
        for prefix in ("点一份", "点个", "点一杯", "买一份", "买一个"):
            idx = instruction.find(prefix)
            if idx != -1:
                start = idx + len(prefix)
                end = start
                while end < len(instruction) and instruction[end] not in _TERMINAL:
                    end += 1
                item = instruction[start:end].strip()
                break
    if item:
        task.item_name = item
        task.type_queue.append(item)


def _parse_baidu_map(instruction: str, task: TaskInfo) -> None:
    task.task_type = "baidu_map"
    # Taxi from A to B / from A to B
    m = re.search(r"(?:打车|叫车)?从(.+?)(?:去|到|前往)(.+?)(?:，|。|地址|$)", instruction)
    if not m:
        m = re.search(r"(?:在)?(?:百度地图)?\s*(.+?)(?:去|到|前往)(.+?)(?:，|。|地址|$)", instruction)
    if m:
        origin, dest = m.group(1).strip(), m.group(2).strip()
        origin = re.sub(r"^(?:在)?百度地图", "", origin).strip()
        origin = re.sub(r"^(?:导航|规划|搜索|查路线|路线规划)", "", origin).strip()
        if origin:
            task.origin = origin
            task.type_queue.append(origin)
        if dest:
            task.destination = dest
            task.type_queue.append(dest)
        return

    origin = _extract_after_trigger(instruction, ("起点", "出发地", "当前"))
    dest = _extract_after_trigger(instruction, ("目的地", "终点"))
    if origin:
        task.origin = origin
        task.type_queue.append(origin)
    if dest:
        task.destination = dest
        task.type_queue.append(dest)


def _strip_action_suffix(keyword: str) -> str:
    """Strip trailing action suffixes like 并播放/并收藏/并查看/筛选... from search keyword."""
    keyword = re.sub(r"并(?:播放|看|收藏|查看|打开|进入|下载|分享|关注|点赞|评论|购买|添加).*", "", keyword)
    keyword = re.sub(r"筛选.*", "", keyword)
    keyword = re.sub(r"然后.*", "", keyword)
    keyword = re.sub(r"的(?:视频|作品|内容)$", "", keyword)
    return keyword.strip()


def _parse_video_search(instruction: str, task: TaskInfo) -> None:
    task.task_type = "video_search"
    # Priority: book title marks
    keyword = _extract_book_title(instruction)
    if not keyword:
        keyword = _extract_after_trigger(instruction, ("搜索一下", "搜一下", "搜索", "搜一搜", "看", "播放", "找", "搜"))
    if not keyword and re.search(r".+的(?:视频|作品|内容)$", instruction):
        keyword = instruction.strip()
    # Strip action suffix before episode (e.g. "扫毒风暴并播放第三集" -> "扫毒风暴第三集")
    if keyword:
        keyword = _strip_action_suffix(keyword)
    # Strip episode suffix from keyword (e.g. "庆余年第5集" -> "庆余年")
    if keyword:
        keyword = re.sub(r"第\d+集$", "", keyword).strip()
    if keyword:
        task.search_keyword = keyword
        task.type_queue.append(keyword)
    # Extract episode number
    m = re.search(r"第(\d+)集", instruction)
    if m:
        episode = f"第{m.group(1)}集"
        task.episode = episode


def _parse_travel(instruction: str, task: TaskInfo) -> None:
    task.task_type = "travel"
    # Strip app name, time words, and common prepositions to avoid matching them as cities
    text = instruction
    for alias in _ALIAS_TO_STANDARD:
        text = text.replace(alias, "")
    text = re.sub(r"(今天|明天|后天|大后天|今晚|明晚)", "", text)
    text = re.sub(r"^(?:在|去|用|打开|进入)[^一-鿿]*", "", text)
    text = re.sub(r"^(?:帮我|我想|想|我要|给我)?(?:查|看|搜|搜索|查找|查询)", "", text)
    # Flight pattern
    m = re.search(r"([一-鿿]{2,10})(?:飞|出发到|到)([一-鿿]{2,10})(?:的航班|航班|机票)", text)
    if not m:
        m = re.search(r"([一-鿿]{2,10})到([一-鿿]{2,10})的?(?:航班|机票)", text)
    if m:
        origin, dest = m.group(1).strip(), m.group(2).strip()
        # Strip trailing 的 from destination
        dest = re.sub(r"的$", "", dest)
        task.origin = origin
        task.type_queue.append(origin)
        task.destination = dest
        task.type_queue.append(dest)
        return

    # General: from A to B
    m = re.search(r"从(.+?)(?:到|去|前往)(.+?)(?:，|。|$)", instruction)
    if m:
        origin, dest = m.group(1).strip(), m.group(2).strip()
        if origin:
            task.origin = origin
            task.type_queue.append(origin)
        if dest:
            task.destination = dest
            task.type_queue.append(dest)
        return

    origin = _extract_after_trigger(instruction, ("出发", "出发地"))
    dest = _extract_after_trigger(instruction, ("目的地",))
    if origin:
        task.origin = origin
        task.type_queue.append(origin)
    if dest:
        task.destination = dest
        task.type_queue.append(dest)


def _looks_like_meituan(instruction: str) -> bool:
    return not _find_app_name(instruction) and bool(
        re.search(r".+店里(?:点一份|点个|点一杯|买一份|买一个|点).+", instruction)
    )



def _looks_like_travel(instruction: str) -> bool:
    return not _find_app_name(instruction) and bool(
        re.search(r"[一-鿿]{2,10}到[一-鿿]{2,10}的?(?:航班|机票)", instruction)
    )



def parse_task(instruction: str) -> TaskInfo:
    task = TaskInfo(instruction=instruction)
    task.app_name = _find_app_name(instruction)

    # Comment task first (avoid being swallowed by video search branch)
    is_post_comment = any(k in instruction for k in COMMENT_POST_TRIGGERS)
    is_comment_page = any(k in instruction for k in COMMENT_PAGE_TRIGGERS)
    if is_post_comment:
        _parse_comment_task(instruction, task, has_content=True)
        return task
    if is_comment_page:
        _parse_comment_task(instruction, task, has_content=False)
        return task

    # App branches
    if task.app_name == "美团" or _looks_like_meituan(instruction):
        _parse_meituan(instruction, task)
    elif task.app_name == "百度地图":
        _parse_baidu_map(instruction, task)
    elif task.app_name in ("哔哩哔哩", "腾讯视频", "爱奇艺", "芒果TV", "喜马拉雅", "抖音", "快手"):
        _parse_video_search(instruction, task)
    elif task.app_name == "去哪儿旅行" or _looks_like_travel(instruction):
        _parse_travel(instruction, task)
    else:
        # Generic search fallback
        keyword = _extract_book_title(instruction)
        if not keyword:
            keyword = _extract_after_trigger(instruction, SEARCH_TRIGGERS + ("输入",))
        if keyword:
            keyword = _strip_action_suffix(keyword)
            task.search_keyword = keyword
            task.type_queue.append(keyword)

    return task
