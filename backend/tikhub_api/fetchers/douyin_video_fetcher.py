from typing import Dict, Any, Optional, List
from .base_fetcher import BaseFetcher


from ..capabilities import VideoPostProvider, VideoDurationProvider, DanmakuProvider, CommentsProvider
from jobs.logger import get_logger
import json


log = get_logger(__name__)

# ===== 抖音搜索（V3）默认配置常量（可由你后续修改） =====
# 接口路径占位：请根据实际文档更新
DOUYIN_SEARCH_API = "/douyin/search/fetch_general_search_v3"

# 默认请求体（仅占位示例）：首次请求 cursor=0, search_id=""
DOUYIN_SEARCH_DEFAULT_PAYLOAD: Dict[str, Any] = {
    "keyword": "火锅", #搜索关键词，如 "猫咪"
    "cursor": 0,  #翻页游标（首次请求传 0）
    "sort_type": "0", #排序方式：0: 综合排序，1: 最多点赞，2: 最新发布
    "publish_time": "7",#0: 不限，1: 最近一天，7: 最近一周，180: 最近半年
    "filter_duration": "0", #0: 不限，0-1: 1分钟以内，1-5: 1-5分钟，5-10000: 5分钟以上
    "content_type": "1",  # 0: 不限，1: 视频，2: 图片，3: 文章
    "search_id": "", #搜索ID（分页时使用）
}

class DouyinVideoFetcher(BaseFetcher, VideoPostProvider, VideoDurationProvider, DanmakuProvider, CommentsProvider):
    """抖音视频获取器，用于调用 TikHub API 获取抖音视频信息"""

    @property
    def platform_name(self) -> str:
        """平台名称"""
        return "抖音"


    def get_adapter(self):
        from ..adapters import DouyinVideoAdapter
        return DouyinVideoAdapter()

    def get_comment_adapter(self):
        """获取评论适配器"""
        from ..adapters import DouyinCommentAdapter
        return DouyinCommentAdapter

    @property
    def api_endpoint(self) -> str:
        """API 端点路径"""
        return "/douyin/web/fetch_one_video"

    def fetch_video_info(self, aweme_id: str) -> Dict[str, Any]:
        """
        根据视频 ID 获取抖音视频信息

        Args:
            aweme_id (str): 抖音视频 ID

        Returns:
            Dict[str, Any]: API 返回的视频信息

        Raises:
            requests.RequestException: 请求异常
            ValueError: 参数错误
        """
        self._validate_video_id(aweme_id)

        url = f"{self.base_url}{self.api_endpoint}"
        params = {'aweme_id': aweme_id}

        return self._make_request(url, params)

    def get_video_details(self, aweme_id: str) -> Optional[Dict[str, Any]]:
        """
        获取视频详细信息的便捷方法

        Args:
            aweme_id (str): 抖音视频 ID

        Returns:
            Optional[Dict[str, Any]]: 视频详细信息，如果获取失败返回 None
        """
        try:
            result = self.fetch_video_info(aweme_id)

            # 检查 API 返回状态
            if self._check_api_response(result):
                return result.get('data')
            else:
                log.info(f"API 返回信息: {result}")
                return None

        except Exception as e:
            log.info(f"获取视频信息失败: {str(e)}")
            return None

    def get_download_urls(self, aweme_id: str) -> Optional[List[str]]:
        """
        获取视频下载链接列表

        Args:
            aweme_id (str): 抖音视频 ID

        Returns:
            Optional[List[str]]: 下载链接列表，如果获取失败返回 None
        """
        try:
            video_details = self.get_video_details(aweme_id)
            if video_details and 'aweme_detail' in video_details:
                download_addr = video_details['aweme_detail']['video']['download_addr']
                return download_addr.get('url_list', [])
            return None
        except Exception as e:
            log.info(f"获取下载链接失败: {str(e)}")
            return None

    # ===== 抖音搜索能力 =====
    def fetch_search_posts(self, keyword: str) -> List[Dict[str, Any]]:
        """
        内置分页：基于 DOUYIN_SEARCH_DEFAULT_PAYLOAD，
        自动按 cursor/search_id 翻页，返回“原始详情”字典列表（全量抓取直到 has_more=0）。
        每个元素形如 {"aweme_detail": {...}}。
        keyword 由上游传入，覆盖默认 payload 中的 keyword。
        """
        gathered: List[Dict[str, Any]] = []
        cursor = 0
        search_id = ""
        has_more = 1

        while has_more == 1:
            payload = dict(DOUYIN_SEARCH_DEFAULT_PAYLOAD)
            payload["keyword"] = keyword
            payload["cursor"] = cursor
            payload["search_id"] = search_id

            log.info("[Douyin] 开始请求 (keyword=%s) JSON body=\n%s", keyword, json.dumps(payload, ensure_ascii=False, indent=2))

            url = f"{self.base_url}{DOUYIN_SEARCH_API}"
            result = self._make_request(url, payload, method="POST")
            if not self._check_api_response(result):
                log.info(f"搜索接口返回异常: {result}")
                break

            data = result.get("data") or {}

            # 打印本次请求 data.data 中的条目数（结构固定：data.status_code + data.data<List>）
            inner_list = data.get("data")
            count_this_page = len(inner_list) if isinstance(inner_list, list) else 0
            log.info("[Douyin] 本次请求 data.data 数量: %d (keyword=%s, cursor=%s, search_id=%s)", count_this_page, keyword, str(cursor), search_id)

            # 解析 items：结构固定为 data.status_code + data.data(list)
            inner_list = data.get("data")
            items = inner_list if isinstance(inner_list, list) else []
            for it in items:
                try:
                    if not isinstance(it, dict):
                        continue
                    if int(it.get("type") or 0) != 1:
                        continue
                    aweme = it.get("aweme_info") or {}
                    if not isinstance(aweme, dict):
                        continue
                    # 检查 aweme_info 是否包含必要的 aweme_id 字段
                    aweme_id = aweme.get("aweme_id")
                    if not aweme_id:
                        log.warning("[Douyin] 跳过无 aweme_id 的条目: %s", it.get("type"))
                        continue
                    details_like = {"aweme_detail": aweme}
                    gathered.append(details_like)
                except Exception as e:
                    log.error("[Douyin] 处理搜索条目异常: %s", e)
                    continue

            # 翻页字段（抖音返回路径修正）
            inner = data if isinstance(data, dict) else {}
            # $.data.cursor
            next_cursor = int(inner.get("cursor") or cursor)
            # $.data.extra.logid  -> 作为下一次请求的 search_id
            extra = inner.get("extra") or {}
            search_id_val = extra.get("logid")
            if search_id_val:
                search_id = str(search_id_val)
            # $.data.has_more
            has_more = 1 if int(inner.get("has_more") or 0) == 1 else 0
            if next_cursor == payload["cursor"] and has_more == 1:
                # 防止服务端错误导致死循环
                has_more = 0
            cursor = next_cursor

        return gathered

    def iter_fetch_search_pages(self, keyword: str):
        """
        按页迭代抖音搜索结果：每次 yield 一页解析后的“原始详情”列表（形如 {"aweme_detail": {...}}）。
        """
        cursor = 0
        search_id = ""
        has_more = 1
        while has_more == 1:
            payload = dict(DOUYIN_SEARCH_DEFAULT_PAYLOAD)
            payload["keyword"] = keyword
            payload["cursor"] = cursor
            payload["search_id"] = search_id

            log.info("[Douyin] 开始请求 (keyword=%s) JSON body=\n%s", keyword, json.dumps(payload, ensure_ascii=False, indent=2))

            url = f"{self.base_url}{DOUYIN_SEARCH_API}"
            result = self._make_request(url, payload, method="POST")
            if not self._check_api_response(result):
                log.info(f"搜索接口返回异常: {result}")
                break

            data = result.get("data") or {}
            inner_list = data.get("data")
            items = inner_list if isinstance(inner_list, list) else []

            # 组装本页 batch
            page_batch: List[Dict[str, Any]] = []
            for it in items:
                try:
                    if not isinstance(it, dict):
                        continue
                    # 过滤非视频类型
                    if int(it.get("type") or 0) != 1:
                        continue
                    aweme = it.get("aweme_info") or {}
                    if not isinstance(aweme, dict):
                        continue
                    # 检查 aweme_info 是否包含必要的 aweme_id 字段
                    aweme_id = aweme.get("aweme_id")
                    if not aweme_id:
                        log.warning("[Douyin] 跳过无 aweme_id 的条目: %s", it.get("type"))
                        continue
                    page_batch.append({"aweme_detail": aweme})
                except Exception as e:
                    log.error("[Douyin] 处理搜索条目异常: %s", e)
                    continue

            log.info("[Douyin] 本页条目: %d (keyword=%s, cursor=%s, search_id=%s)", len(page_batch), keyword, str(cursor), search_id)
            if page_batch:
                yield page_batch

            # 翻页字段（抖音返回路径修正）
            inner = data if isinstance(data, dict) else {}
            # $.data.cursor
            next_cursor = int(inner.get("cursor") or cursor)
            # $.data.extra.logid  -> 作为下一次请求的 search_id
            extra = inner.get("extra") or {}
            search_id_val = extra.get("logid")
            if search_id_val:
                search_id = str(search_id_val)
            # $.data.has_more
            has_more = 1 if int(inner.get("has_more") or 0) == 1 else 0
            if next_cursor == payload["cursor"] and has_more == 1:
                # 防止服务端错误导致死循环
                has_more = 0
            cursor = next_cursor
            log.info("[Douyin] 下一页 (has_more=%s, keyword=%s, cursor=%s, search_id=%s)", inner.get("has_more"), keyword, str(cursor), search_id)

    # 兼容命名
    def fetch_search_page(self) -> List[Dict[str, Any]]:
        return self.fetch_search_posts()


    def fetch_video_danmaku(self, item_id: str, duration: int, start_time: int = 0, end_time: Optional[int] = None) -> Dict[str, Any]:
        """
        获取抖音视频弹幕信息

        Args:
            item_id (str): 抖音视频 ID
            duration (int): 视频时长（毫秒）
            start_time (int): 开始时间（毫秒），默认为 0
            end_time (Optional[int]): 结束时间（毫秒），如果为 None 则使用 duration-1

        Returns:
            Dict[str, Any]: API 返回的弹幕信息

        Raises:
            requests.RequestException: 请求异常
            ValueError: 参数错误
        """
        self._validate_video_id(item_id)

        if duration <= 0:
            raise ValueError("视频时长必须大于 0")

        if start_time < 0:
            raise ValueError("开始时间不能小于 0")

        if end_time is None:
            end_time = duration - 1

        if end_time > duration:
            raise ValueError("结束时间不能大于视频时长")

        if start_time >= end_time:
            raise ValueError("开始时间必须小于结束时间")

        url = f"{self.base_url}/douyin/web/fetch_one_video_danmaku"
        params = {
            'item_id': item_id,
            'duration': duration,
            'start_time': start_time,
            'end_time': end_time
        }

        return self._make_request(url, params)

    def get_video_danmaku(self, item_id: str, duration: int, start_time: int = 0, end_time: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        获取视频弹幕信息的便捷方法

        Args:
            item_id (str): 抖音视频 ID
            duration (int): 视频时长（毫秒）
            start_time (int): 开始时间（毫秒），默认为 0
            end_time (Optional[int]): 结束时间（毫秒），如果为 None 则使用 duration-1

        Returns:
            Optional[Dict[str, Any]]: 弹幕信息，如果获取失败返回 None
        """
        try:
            result = self.fetch_video_danmaku(item_id, duration, start_time, end_time)

            # 检查 API 返回状态
            if self._check_api_response(result):
                return result.get('data')
            else:
                log.info(f"获取弹幕失败: {result.get('message', '未知错误')}")
                return None

        except Exception as e:
            log.info(f"获取弹幕信息失败: {str(e)}")
            return None

    # ===== 评论能力 =====
    def fetch_video_comments_page(self, aweme_id: str, cursor: int = 0, count: int = 20) -> Dict[str, Any]:
        self._validate_video_id(aweme_id)
        if cursor < 0:
            raise ValueError("cursor 不能小于 0")
        if count <= 0 or count > 50:
            raise ValueError("count 必须在 1~50 之间")
        url = f"{self.base_url}/douyin/web/fetch_video_comments"
        params = {
            'aweme_id': aweme_id,
            'cursor': cursor,
            'count': count,
        }
        return self._make_request(url, params)

    def get_video_comments(self, aweme_id: str, cursor: int = 0, count: int = 20) -> Optional[Dict[str, Any]]:
        try:
            result = self.fetch_video_comments_page(aweme_id, cursor, count)
            if self._check_api_response(result):
                return result.get('data')
            else:
                log.info(f"获取评论失败，response: {result}")
                return None
        except Exception as e:
            log.info(f"获取评论信息失败: {str(e)}")
            return None

    # ===== 评论回复能力 =====
    def fetch_video_comment_replies_page(self, item_id: str, comment_id: str, cursor: int = 0, count: int = 20) -> Dict[str, Any]:
        self._validate_video_id(item_id)
        if not comment_id:
            raise ValueError("comment_id 不能为空")
        if cursor < 0:
            raise ValueError("cursor 不能小于 0")
        if count <= 0 or count > 50:
            raise ValueError("count 必须在 1~50 之间")
        url = f"{self.base_url}/douyin/web/fetch_video_comment_replies"
        params = {
            'item_id': item_id,
            'comment_id': comment_id,
            'cursor': cursor,
            'count': count,
        }
        return self._make_request(url, params)

    def get_video_comment_replies(self, item_id: str, comment_id: str, cursor: int = 0, count: int = 20) -> Optional[Dict[str, Any]]:
        try:
            result = self.fetch_video_comment_replies_page(item_id, comment_id, cursor, count)
            if self._check_api_response(result):
                return result.get('data')
            else:
                log.info(f"获取评论回复失败: {result.get('message', '未知错误')}")
                return None
        except Exception as e:
            log.info(f"获取评论回复信息失败: {str(e)}")
            return None

    # ===== 作者信息获取能力 =====
    def fetch_author_info(self, sec_user_id: str) -> Dict[str, Any]:
        """
        根据 sec_user_id 获取抖音作者信息（返回原始 API 响应）

        Args:
            sec_user_id (str): 抖音作者的 sec_user_id

        Returns:
            Dict[str, Any]: API 返回的原始作者信息

        Raises:
            requests.RequestException: 请求异常
            ValueError: 参数错误
        """
        if not sec_user_id or not isinstance(sec_user_id, str):
            raise ValueError("sec_user_id 不能为空")

        url = f"{self.base_url}/douyin/app/v3/handler_user_profile"
        params = {'sec_user_id': sec_user_id}

        return self._make_request(url, params)

    def get_author_adapter(self):
        """获取抖音作者适配器"""
        from ..adapters import DouyinAuthorAdapter
        return DouyinAuthorAdapter()


# 便捷函数
def fetch_douyin_video(aweme_id: str) -> Optional[Dict[str, Any]]:
    """
    便捷函数：获取抖音视频信息

    Args:
        aweme_id (str): 抖音视频 ID

    Returns:
        Optional[Dict[str, Any]]: 视频信息，失败返回 None
    """
    fetcher = DouyinVideoFetcher()
    return fetcher.get_video_details(aweme_id)


if __name__ == "__main__":
    # 测试代码
    test_aweme_id = "7499608775142608186"

    try:
        fetcher = DouyinVideoFetcher()
        video_info = fetcher.fetch_video_info(test_aweme_id)
        log.info("API 返回结果:")
        log.info(f"{video_info}")

        # 使用便捷方法
        video_details = fetcher.get_video_details(test_aweme_id)
        if video_details:
            log.info("视频详细信息:")
            log.info(f"{video_details}")
        else:
            log.info("获取视频详细信息失败")

    except Exception as e:
        log.info(f"错误: {str(e)}")
