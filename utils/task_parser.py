"""任务解析模块 - 从用户指令中提取App名、TYPE队列、搜索关键词等"""

from dataclasses import dataclass, field
from typing import Optional, List


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

# 反向查找表：alias → 标准名
_ALIAS_TO_STANDARD: dict[str, str] = {}
for _std, _aliases in APP_ALIASES.items():
    for _a in _aliases:
        _ALIAS_TO_STANDARD[_a] = _std


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


def _extract_quoted(text: str, keywords: tuple[str, ...]) -> str:
    for kw in keywords:
        idx = text.find(kw)
        if idx == -1:
            continue
        rest = text[idx + len(kw):]
        for ch in rest:
            if ch not in (" ", "：", ":", "为", "是", "到", "去", "的"):
                break
        else:
            continue
        start = idx + len(kw)
        while start < len(text) and text[start] in (" ", "：", ":", "为", "是", "到", "去", "的"):
            start += 1
        end = start
        while end < len(text) and text[end] not in ("，", "。", "、", "！", "？", " ", "\n"):
            end += 1
        return text[start:end].strip()
    return ""


def _parse_meituan(instruction: str, task: TaskInfo) -> None:
    task.task_type = "meituan"
    shop = _extract_quoted(instruction, ("店铺", "商家", "外卖店", "店名", "搜索"))
    if not shop:
        for kw in ("点一份", "在", "从", "去", "叫"):
            idx = instruction.find(kw)
            if idx != -1:
                rest = instruction[idx + len(kw):]
                end = 0
                while end < len(rest) and rest[end] not in ("里", "中", "上", "点", "买", "搜", "加", "，", "。"):
                    end += 1
                if end > 0:
                    shop = rest[:end].strip()
                    break
    if shop:
        task.shop_name = shop
        task.type_queue.append(shop)
    item = _extract_quoted(instruction, ("商品", "菜品", "食物", "东西", "份", "杯", "个"))
    if not item:
        for prefix in ("点一份", "点个", "点一杯", "买一份", "买一个"):
            idx = instruction.find(prefix)
            if idx != -1:
                start = idx + len(prefix)
                end = start
                while end < len(instruction) and instruction[end] not in ("，", "。", "！", "？", " "):
                    end += 1
                item = instruction[start:end].strip()
                break
    if item:
        task.item_name = item
        task.type_queue.append(item)


def _parse_baidu_map(instruction: str, task: TaskInfo) -> None:
    task.task_type = "baidu_map"
    origin = _extract_quoted(instruction, ("从", "起点", "出发地", "当前"))
    if not origin:
        for kw in ("从",):
            idx = instruction.find(kw)
            if idx != -1:
                start = idx + len(kw)
                while start < len(instruction) and instruction[start] in (" ", "：", ":"):
                    start += 1
                end = start
                while end < len(instruction) and instruction[end] not in ("到", "去", "，", "。", " "):
                    end += 1
                if end > start:
                    origin = instruction[start:end].strip()
                    break
    dest = _extract_quoted(instruction, ("到", "去", "目的地", "终点"))
    if origin:
        task.origin = origin
        task.type_queue.append(origin)
    if dest:
        task.destination = dest
        task.type_queue.append(dest)


def _parse_video_search(instruction: str, task: TaskInfo) -> None:
    task.task_type = "video_search"
    keyword = _extract_quoted(instruction, ("搜", "看", "播放", "找", "搜索"))
    if not keyword:
        for kw in ("搜", "看", "播放", "找"):
            idx = instruction.find(kw)
            if idx != -1:
                start = idx + len(kw)
                while start < len(instruction) and instruction[start] in (" ", "：", ":"):
                    start += 1
                end = start
                while end < len(instruction) and instruction[end] not in ("，", "。", "！", "？", " "):
                    end += 1
                if end > start:
                    keyword = instruction[start:end].strip()
                    break
    if keyword:
        task.search_keyword = keyword
        task.type_queue.append(keyword)
    episode = _extract_quoted(instruction, ("第", "集"))
    if "第" in instruction and "集" in instruction:
        idx1 = instruction.find("第")
        idx2 = instruction.find("集", idx1)
        if idx2 > idx1:
            episode = instruction[idx1:idx2 + 1]
            task.episode = episode


def _parse_comment_task(instruction: str, task: TaskInfo) -> None:
    task.task_type = "comment"
    search = _extract_quoted(instruction, ("搜", "找", "搜索"))
    if search:
        task.search_keyword = search
        task.type_queue.append(search)
    comment = _extract_quoted(instruction, ("评论", "评价", "留言"))
    if not comment:
        for kw in ("评论说", "评价", "写评论", "发评论"):
            idx = instruction.find(kw)
            if idx != -1:
                start = idx + len(kw)
                while start < len(instruction) and instruction[start] in (" ", "：", ":"):
                    start += 1
                end = start
                while end < len(instruction) and instruction[end] not in ("，", "。", "！", "？", " "):
                    end += 1
                if end > start:
                    comment = instruction[start:end].strip()
                    break
    if comment:
        task.comment_text = comment
        task.type_queue.append(comment)


def _parse_travel(instruction: str, task: TaskInfo) -> None:
    task.task_type = "travel"
    origin = _extract_quoted(instruction, ("从", "出发", "出发地"))
    dest = _extract_quoted(instruction, ("到", "去", "目的地"))
    if origin:
        task.origin = origin
        task.type_queue.append(origin)
    if dest:
        task.destination = dest
        task.type_queue.append(dest)


def parse_task(instruction: str) -> TaskInfo:
    task = TaskInfo(instruction=instruction)
    task.app_name = _find_app_name(instruction)

    if task.app_name == "美团":
        _parse_meituan(instruction, task)
    elif task.app_name == "百度地图":
        _parse_baidu_map(instruction, task)
    elif task.app_name in ("哔哩哔哩", "腾讯视频", "爱奇艺", "芒果TV", "喜马拉雅"):
        _parse_video_search(instruction, task)
    elif task.app_name == "去哪儿旅行":
        _parse_travel(instruction, task)
    elif "评论" in instruction or "评价" in instruction:
        _parse_comment_task(instruction, task)
    else:
        general_kw = _extract_quoted(instruction, ("搜", "找", "搜索", "输入"))
        if general_kw:
            task.search_keyword = general_kw
            task.type_queue.append(general_kw)

    return task
