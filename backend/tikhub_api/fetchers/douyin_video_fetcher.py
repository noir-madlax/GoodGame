from typing import Dict, Any, Optional, List
from .base_fetcher import BaseFetcher


from ..capabilities import VideoPostProvider, VideoDurationProvider, DanmakuProvider, CommentsProvider

# ===== 抖音搜索（V3）默认配置常量（可由你后续修改） =====
# 接口路径占位：请根据实际文档更新
DOUYIN_SEARCH_API = "/douyin/search/fetch_general_search_v3"

#


##

# 默认请求体（仅占位示例）：首次请求 cursor=0, search_id=""
DOUYIN_SEARCH_DEFAULT_PAYLOAD: Dict[str, Any] = {
    "keyword": "火锅", #搜索关键词，如 "猫咪"
    "cursor": 0,  #翻页游标（首次请求传 0）
    "sort_type": "2", #排序方式：0: 综合排序，1: 最多点赞，2: 最新发布
    "publish_time": "7",#0: 不限，1: 最近一天，7: 最近一周，180: 最近半年
    "filter_duration": "0", #0: 不限，0-1: 1分钟以内，1-5: 1-5分钟，5-10000: 5分钟以上
    "content_type": "0",  # 0: 不限，1: 视频，2: 图片，3: 文章
    "search_id": "", #搜索ID（分页时使用）
}

# 本次任务最多获取的结果条数（达到该数将停止翻页）
DOUYIN_SEARCH_MAX_ITEMS: int = 10


class DouyinVideoFetcher(BaseFetcher, VideoPostProvider, VideoDurationProvider, DanmakuProvider, CommentsProvider):
    """抖音视频获取器，用于调用 TikHub API 获取抖音视频信息"""

    @property
    def platform_name(self) -> str:
        """平台名称"""
        return "抖音"


    def get_adapter(self):
        from ..adapters import DouyinVideoAdapter
        return DouyinVideoAdapter()

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
                print(f"API 返回信息: {result}")
                return None

        except Exception as e:
            print(f"获取视频信息失败: {str(e)}")
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
            print(f"获取下载链接失败: {str(e)}")
            return None

    # ===== 抖音搜索能力 =====
    def fetch_search_posts(self) -> List[Dict[str, Any]]:
        """
        内置分页：基于 DOUYIN_SEARCH_DEFAULT_PAYLOAD 和 DOUYIN_SEARCH_MAX_ITEMS，
        自动按 cursor/search_id 翻页，返回“原始详情”字典列表，供基类适配为 PlatformPost。
        每个元素形如 {"aweme_detail": {...}}。
        """
        gathered: List[Dict[str, Any]] = []
        cursor = 0
        search_id = ""
        has_more = 1
        total_needed = int(DOUYIN_SEARCH_MAX_ITEMS)

        while has_more == 1 and len(gathered) < total_needed:
            payload = dict(DOUYIN_SEARCH_DEFAULT_PAYLOAD)
            payload["cursor"] = cursor
            payload["search_id"] = search_id

            url = f"{self.base_url}{DOUYIN_SEARCH_API}"
            result = self._make_request(url, payload, method="POST")
            if not self._check_api_response(result):
                print(f"搜索接口返回异常: {result}")
                break

            data = result.get("data") or {}
            # 兼容多种返回结构，解析出 items 列表
            items = None
            try:
                if isinstance(data.get("data"), dict) and isinstance(data["data"].get("data"), list):
                    items = data["data"]["data"]
                elif isinstance(data.get("status_code"), (int, float)) and isinstance(data.get("data"), list):
                    items = data["data"]
                elif isinstance(data.get("data"), list):
                    items = data["data"]
                elif isinstance(data.get("aweme_list"), list):
                    items = data["aweme_list"]
                elif isinstance(data.get("items"), list):
                    items = data["items"]
            except Exception:
                items = None

            items = items or []
            added_this_page = 0
            for it in items:
                if len(gathered) >= total_needed:
                    break
                try:
                    if not isinstance(it, dict):
                        continue
                    if int(it.get("type") or 0) != 1:
                        continue
                    aweme = it.get("aweme_info") or {}
                    if not isinstance(aweme, dict):
                        continue
                    details_like = {"aweme_detail": aweme}
                    gathered.append(details_like)
                    added_this_page += 1
                except Exception:
                    continue

            # 翻页字段
            inner = data if isinstance(data, dict) else {}
            cursor = int(inner.get("cursor") or cursor)
            search_id = str(inner.get("search_id") or search_id)
            has_more = int(inner.get("has_more") or (1 if added_this_page > 0 else 0))
            if cursor == payload["cursor"] and has_more == 1:
                has_more = 0  # 防止死循环

        return gathered

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
                print(f"获取弹幕失败: {result.get('message', '未知错误')}")
                return None

        except Exception as e:
            print(f"获取弹幕信息失败: {str(e)}")
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
                print(f"获取评论失败，response: {result}")
                return None
        except Exception as e:
            print(f"获取评论信息失败: {str(e)}")
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
                print(f"获取评论回复失败: {result.get('message', '未知错误')}")
                return None
        except Exception as e:
            print(f"获取评论回复信息失败: {str(e)}")
            return None


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
        print("API 返回结果:")
        print(video_info)

        # 使用便捷方法
        video_details = fetcher.get_video_details(test_aweme_id)
        if video_details:
            print("\n视频详细信息:")
            print(video_details)
        else:
            print("获取视频详细信息失败")

    except Exception as e:
        print(f"错误: {str(e)}")
