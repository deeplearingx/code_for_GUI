"""TaskParser unit tests"""

import sys
import os
import importlib.util

_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, _root)
_tp_spec = importlib.util.spec_from_file_location(
    "task_parser", os.path.join(_root, "utils", "task_parser.py"))
_tp = importlib.util.module_from_spec(_tp_spec)
_tp_spec.loader.exec_module(_tp)

parse_task = _tp.parse_task

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

# -- parse_task() tests --
# comment post - iqiyi
check('comment post - iqiyi' 'task_type', parse_task('在爱奇艺搜索采莲曲，发布评论：好看').task_type, 'comment')
check('comment post - iqiyi' 'app_name', parse_task('在爱奇艺搜索采莲曲，发布评论：好看').app_name, '爱奇艺')
check('comment post - iqiyi' 'search_keyword', parse_task('在爱奇艺搜索采莲曲，发布评论：好看').search_keyword, '采莲曲')
check('comment post - iqiyi' 'comment_text', parse_task('在爱奇艺搜索采莲曲，发布评论：好看').comment_text, '好看')
check('comment post - iqiyi' 'type_queue', parse_task('在爱奇艺搜索采莲曲，发布评论：好看').type_queue, ['采莲曲', '好看'])

# comment page only
check('comment page only' 'task_type', parse_task('在哔哩哔哩搜索视频，打开评论区').task_type, 'comment')
check('comment page only' 'type_queue', parse_task('在哔哩哔哩搜索视频，打开评论区').type_queue, ['视频'])

# meituan shop+item
check('meituan shop+item' 'task_type', parse_task('在美团购买窑村干锅猪蹄店铺里的干锅排骨').task_type, 'meituan')
check('meituan shop+item' 'shop_name', parse_task('在美团购买窑村干锅猪蹄店铺里的干锅排骨').shop_name, '窑村干锅猪蹄')
check('meituan shop+item' 'item_name', parse_task('在美团购买窑村干锅猪蹄店铺里的干锅排骨').item_name, '干锅排骨')
check('meituan shop+item' 'type_queue', parse_task('在美团购买窑村干锅猪蹄店铺里的干锅排骨').type_queue, ['窑村干锅猪蹄', '干锅排骨'])

# meituan at shop
check('meituan at shop' 'task_type', parse_task('去美团外卖在张亮麻辣烫店铺里点一份鱼豆腐').task_type, 'meituan')
check('meituan at shop' 'shop_name', parse_task('去美团外卖在张亮麻辣烫店铺里点一份鱼豆腐').shop_name, '张亮麻辣烫')
check('meituan at shop' 'item_name', parse_task('去美团外卖在张亮麻辣烫店铺里点一份鱼豆腐').item_name, '鱼豆腐')

# meituan natural shop phrase
check('meituan natural shop phrase' 'shop_name', parse_task('窑村干锅猪蹄（科技大学店）店里点一份干锅排骨').shop_name, '窑村干锅猪蹄（科技大学店）')
check('meituan natural shop phrase' 'item_name', parse_task('窑村干锅猪蹄（科技大学店）店里点一份干锅排骨').item_name, '干锅排骨')
check('meituan natural shop phrase' 'type_queue', parse_task('窑村干锅猪蹄（科技大学店）店里点一份干锅排骨').type_queue, ['窑村干锅猪蹄（科技大学店）', '干锅排骨'])
check('meituan branch name ending shop' 'shop_name', parse_task('海底捞万达店里点一份肥牛').shop_name, '海底捞万达店')
check('meituan branch name ending shop' 'item_name', parse_task('海底捞万达店里点一份肥牛').item_name, '肥牛')

# baidu_map from A to B
check('baidu_map from A to B' 'task_type', parse_task('在百度地图从北京大学到天安门').task_type, 'baidu_map')
check('baidu_map from A to B' 'origin', parse_task('在百度地图从北京大学到天安门').origin, '北京大学')
check('baidu_map from A to B' 'destination', parse_task('在百度地图从北京大学到天安门').destination, '天安门')
check('baidu_map from A to B' 'type_queue', parse_task('在百度地图从北京大学到天安门').type_queue, ['北京大学', '天安门'])

# baidu_map taxi
check('baidu_map taxi' 'task_type', parse_task('在百度地图打车从公司去机场').task_type, 'baidu_map')
check('baidu_map taxi' 'origin', parse_task('在百度地图打车从公司去机场').origin, '公司')
check('baidu_map taxi' 'destination', parse_task('在百度地图打车从公司去机场').destination, '机场')

# baidu_map natural route phrase
check('baidu_map natural route phrase' 'origin', parse_task('在百度地图国际医学中心到回民街').origin, '国际医学中心')
check('baidu_map natural route phrase' 'destination', parse_task('在百度地图国际医学中心到回民街').destination, '回民街')
check('baidu_map natural route phrase' 'type_queue', parse_task('在百度地图国际医学中心到回民街').type_queue, ['国际医学中心', '回民街'])
check('baidu_map navigation phrase' 'origin', parse_task('在百度地图导航国际医学中心到回民街').origin, '国际医学中心')
check('baidu_map navigation phrase' 'destination', parse_task('在百度地图导航国际医学中心到回民街').destination, '回民街')

# video book title
check('video book title' 'task_type', parse_task('在哔哩哔哩搜索《采莲曲》').task_type, 'video_search')
check('video book title' 'search_keyword', parse_task('在哔哩哔哩搜索《采莲曲》').search_keyword, '采莲曲')
check('video book title' 'type_queue', parse_task('在哔哩哔哩搜索《采莲曲》').type_queue, ['采莲曲'])

# video search + episode
check('video search + episode' 'task_type', parse_task('在腾讯视频搜索庆余年第5集').task_type, 'video_search')
check('video search + episode' 'search_keyword', parse_task('在腾讯视频搜索庆余年第5集').search_keyword, '庆余年')
check('video search + episode' 'episode', parse_task('在腾讯视频搜索庆余年第5集').episode, '第5集')

# video search long trigger
check('video search long trigger' 'task_type', parse_task('在爱奇艺搜索一下狂飙').task_type, 'video_search')
check('video search long trigger' 'search_keyword', parse_task('在爱奇艺搜索一下狂飙').search_keyword, '狂飙')

# douyin suffix stripping
check('douyin video suffix' 'app_name', parse_task('在抖音搜索甄嬛传的视频').app_name, '抖音')
check('douyin video suffix' 'task_type', parse_task('在抖音搜索甄嬛传的视频').task_type, 'video_search')
check('douyin video suffix' 'search_keyword', parse_task('在抖音搜索甄嬛传的视频').search_keyword, '甄嬛传')
check('douyin video suffix' 'type_queue', parse_task('在抖音搜索甄嬛传的视频').type_queue, ['甄嬛传'])
check('douyin bare video suffix' 'search_keyword', parse_task('在抖音搜索跳舞视频').search_keyword, '跳舞')
check('douyin bare video suffix' 'type_queue', parse_task('在抖音搜索跳舞视频').type_queue, ['跳舞'])
check('kuaishou filter tail cleanup' 'app_name', parse_task('去快手搜索动画片筛选1日内的1-5分钟作品').app_name, '快手')
check('kuaishou filter tail cleanup' 'task_type', parse_task('去快手搜索动画片筛选1日内的1-5分钟作品').task_type, 'video_search')
check('kuaishou filter tail cleanup' 'search_keyword', parse_task('去快手搜索动画片筛选1日内的1-5分钟作品').search_keyword, '动画片')
check('kuaishou filter tail cleanup' 'type_queue', parse_task('去快手搜索动画片筛选1日内的1-5分钟作品').type_queue, ['动画片'])

# video search cleanup for fallback-only runs
check('video search strips collection action tail' 'search_keyword', parse_task('在爱奇艺搜索采莲曲并收藏综合列表里第一个视频').search_keyword, '采莲曲')
check('video search strips collection action tail' 'type_queue', parse_task('在爱奇艺搜索采莲曲并收藏综合列表里第一个视频').type_queue, ['采莲曲'])
check('video search strips download container prefix' 'search_keyword', parse_task('在芒果TV搜索我的下载里的新还珠格格第2集').search_keyword, '新还珠格格')
check('video search strips download container prefix' 'episode', parse_task('在芒果TV搜索我的下载里的新还珠格格第2集').episode, '第2集')
check('video search strips download container prefix' 'type_queue', parse_task('在芒果TV搜索我的下载里的新还珠格格第2集').type_queue, ['新还珠格格'])

# travel flight
check('travel flight' 'task_type', parse_task('在去哪儿旅行查北京飞上海的航班').task_type, 'travel')
check('travel flight' 'origin', parse_task('在去哪儿旅行查北京飞上海的航班').origin, '北京')
check('travel flight' 'destination', parse_task('在去哪儿旅行查北京飞上海的航班').destination, '上海')
check('travel flight' 'type_queue', parse_task('在去哪儿旅行查北京飞上海的航班').type_queue, ['北京', '上海'])

# travel from A to B
check('travel from A to B' 'task_type', parse_task('在去哪儿旅行从成都到重庆').task_type, 'travel')
check('travel from A to B' 'origin', parse_task('在去哪儿旅行从成都到重庆').origin, '成都')
check('travel from A to B' 'destination', parse_task('在去哪儿旅行从成都到重庆').destination, '重庆')

# travel natural flight phrase
check('travel natural flight phrase' 'task_type', parse_task('在去哪儿旅行看邯郸到上海的航班').task_type, 'travel')
check('travel natural flight phrase' 'origin', parse_task('在去哪儿旅行看邯郸到上海的航班').origin, '邯郸')
check('travel natural flight phrase' 'destination', parse_task('在去哪儿旅行看邯郸到上海的航班').destination, '上海')
check('travel natural flight phrase' 'type_queue', parse_task('在去哪儿旅行看邯郸到上海的航班').type_queue, ['邯郸', '上海'])

# travel natural flight phrase without app
check('travel natural flight no app' 'task_type', parse_task('邯郸到上海的航班').task_type, 'travel')
check('travel natural flight no app' 'origin', parse_task('邯郸到上海的航班').origin, '邯郸')
check('travel natural flight no app' 'destination', parse_task('邯郸到上海的航班').destination, '上海')
check('travel natural flight no app' 'type_queue', parse_task('邯郸到上海的航班').type_queue, ['邯郸', '上海'])
check('travel natural flight with prefix' 'origin', parse_task('帮我看邯郸到上海的航班').origin, '邯郸')
check('travel natural flight with prefix' 'destination', parse_task('帮我看邯郸到上海的航班').destination, '上海')
check('travel app prefix cleanup one' 'origin', parse_task('帮我在去哪儿旅行看一下邯郸到上海的航班').origin, '邯郸')
check('travel app prefix cleanup one' 'destination', parse_task('帮我在去哪儿旅行看一下邯郸到上海的航班').destination, '上海')
check('travel app prefix cleanup one' 'type_queue', parse_task('帮我在去哪儿旅行看一下邯郸到上海的航班').type_queue, ['邯郸', '上海'])
check('travel app prefix cleanup two' 'origin', parse_task('去哪儿旅行查一下邯郸到上海机票').origin, '邯郸')
check('travel app prefix cleanup two' 'destination', parse_task('去哪儿旅行查一下邯郸到上海机票').destination, '上海')
check('travel app prefix cleanup two' 'type_queue', parse_task('去哪儿旅行查一下邯郸到上海机票').type_queue, ['邯郸', '上海'])
check('travel app prefix cleanup three' 'origin', parse_task('我想在去哪儿看一下北京到成都的航班').origin, '北京')
check('travel app prefix cleanup three' 'destination', parse_task('我想在去哪儿看一下北京到成都的航班').destination, '成都')
check('travel app prefix cleanup three' 'type_queue', parse_task('我想在去哪儿看一下北京到成都的航班').type_queue, ['北京', '成都'])
check('travel date hint task_type', parse_task('在去哪儿旅行查后天北京到上海的航班，最便宜的是多钱').task_type, 'travel')
check('travel date hint origin', parse_task('在去哪儿旅行查后天北京到上海的航班，最便宜的是多钱').origin, '北京')
check('travel date hint destination', parse_task('在去哪儿旅行查后天北京到上海的航班，最便宜的是多钱').destination, '上海')
check('travel date hint type_queue', parse_task('在去哪儿旅行查后天北京到上海的航班，最便宜的是多钱').type_queue, ['北京', '上海'])
check('travel date hint value', parse_task('在去哪儿旅行查后天北京到上海的航班，最便宜的是多钱').travel_date_hint, '后天')
check('travel tonight origin cleanup', parse_task('在去哪儿旅行查今晚北京到上海的航班').origin, '北京')
check('travel tonight destination cleanup', parse_task('在去哪儿旅行查今晚北京到上海的航班').destination, '上海')
check('travel tonight date hint normalize', parse_task('在去哪儿旅行查今晚北京到上海的航班').travel_date_hint, '今天')
check('travel tomorrow night origin cleanup', parse_task('在去哪儿旅行查明晚北京到上海的航班').origin, '北京')
check('travel tomorrow night destination cleanup', parse_task('在去哪儿旅行查明晚北京到上海的航班').destination, '上海')
check('travel tomorrow night date hint normalize', parse_task('在去哪儿旅行查明晚北京到上海的航班').travel_date_hint, '明天')

# app alias B站
check('app alias B站' 'app_name', parse_task('在B站搜索舞蹈视频').app_name, '哔哩哔哩')
check('app alias B站' 'task_type', parse_task('在B站搜索舞蹈视频').task_type, 'video_search')
check('app alias B站' 'search_keyword', parse_task('在B站搜索舞蹈视频').search_keyword, '舞蹈视频')

# app alias 12306
check('app alias 12306' 'app_name', parse_task('在铁路12306买票').app_name, '铁路12306')

# app alias 美团外卖
check('app alias 美团外卖' 'app_name', parse_task('用美团外卖点餐').app_name, '美团')
check('app alias 美团外卖' 'task_type', parse_task('用美团外卖点餐').task_type, 'meituan')

# other app should not be hijacked by meituan heuristic
check('other app not hijacked' 'app_name', parse_task('在大众点评海底捞店里点一份肥牛').app_name, '大众点评')
check('other app not hijacked' 'task_type', parse_task('在大众点评海底捞店里点一份肥牛').task_type, 'general')

# generic search
check('generic search' 'task_type', parse_task('搜索天气预报').task_type, 'general')
check('generic search' 'search_keyword', parse_task('搜索天气预报').search_keyword, '天气预报')
check('generic search' 'type_queue', parse_task('搜索天气预报').type_queue, ['天气预报'])

# long trigger no truncate
check('long trigger no truncate' 'search_keyword', parse_task('搜索一下采莲曲').search_keyword, '采莲曲')

# no search
check('no search' 'app_name', parse_task('打开微信').app_name, '')
check('no search' 'type_queue', parse_task('打开微信').type_queue, [])

sep = "=" * 40
print(f"\n{sep}")
print(f"TaskParser tests: {passed} passed, {failed} failed, {passed + failed} total")
if failed:
    print("RESULT: FAIL")
    sys.exit(1)
else:
    print("RESULT: ALL PASS")
