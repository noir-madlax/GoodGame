"""
小红书视频获取器
用于调用 TikHub API 获取小红书视频信息
"""

import json
from typing import Dict, Any, Optional, List
from .base_fetcher import BaseFetcher
from ..capabilities import CommentsProvider
from ..orm.models import PlatformPost
from jobs.logger import get_logger

log = get_logger(__name__)

class XiaohongshuFetcher(BaseFetcher, CommentsProvider):
    """小红书视频获取器，用于调用 TikHub API 获取小红书视频信息"""

    # 搜索接口与默认配置（改为使用 app/search_notes）
    # 参考示例：/api/v1/xiaohongshu/app/search_notes?keyword=海底捞&page=1&sort_type=general&filter_note_type=不限&filter_note_time=不限
    XHS_SEARCH_API = "/xiaohongshu/app/search_notes"
    XHS_SEARCH_DEFAULT_PARAMS: Dict[str, Any] = {
        "keyword": "海底捞",
        "page": 1,
        "searchId": "",
        "session_id": "",
        "sort_type": "general",
        "filter_note_type": "不限",
        "filter_note_time": "一天内",
    }

    @property
    def platform_name(self) -> str:
        """平台名称"""
        return "小红书"

    def get_adapter(self):
        from ..adapters import XiaohongshuVideoAdapter
        return XiaohongshuVideoAdapter()

    def get_comment_adapter(self):
        """获取评论适配器"""
        from ..adapters import XiaohongshuCommentAdapter
        return XiaohongshuCommentAdapter


    @property
    def api_endpoint(self) -> str:
        """API 端点路径"""
        # 切换为 TikHub 小红书 Web v2 feed 接口，数据更完整
        return "/xiaohongshu/app/get_note_info_v2"

    def fetch_video_info(self, note_id: str) -> Dict[str, Any]:
        """
        根据笔记 ID 获取小红书视频信息（调用 TikHub web_v2/fetch_feed_notes_v2）

        Args:
            note_id (str): 小红书笔记 ID

        Returns:
            Dict[str, Any]: API 返回的原始响应

        Raises:
            requests.RequestException: 请求异常
            ValueError: 参数错误
        """
        self._validate_video_id(note_id)

        url = f"{self.base_url}{self.api_endpoint}"
        params = {"note_id": note_id}
        return self._make_request(url, params)

    def get_video_details(self, note_id: str) -> Optional[Dict[str, Any]]:
        """
        获取笔记详细信息：
        - 优先适配 /xiaohongshu/app/get_note_info_v2 返回的 data.data
        - 兼容旧结构 data.note_list[0]
        """
        try:
            result = self.fetch_video_info(note_id)

            if self._check_api_response(result):
                payload = result.get("data") or {}
                # 新结构：data.data 即为笔记详情
                details = payload.get("data") or {}
                if isinstance(details, dict) and details:
                    return details
                # 兼容旧结构：data.note_list[0]
                note_list = payload.get("note_list") or []
                if isinstance(note_list, list) and note_list:
                    return note_list[0]
                return None
            else:
                log.info(f"API 返回信息异常: {result}")
                return None

        except Exception as e:
            log.error(f"获取视频信息失败: {str(e)}")
            return None

    def get_download_urls(self, note_id: str) -> Optional[List[str]]:
        """
        获取视频下载链接列表

        Args:
            note_id (str): 小红书笔记 ID

        Returns:
            Optional[List[str]]: 下载链接列表，如果获取失败返回 None
        """
        try:
            details = self.get_video_details(note_id)
            if not details:
                return None
            video = (details.get("video") or {})
            # 优先多清晰度列表
            url_info_list = video.get("url_info_list") or []
            urls = [x.get("url") for x in url_info_list if isinstance(x, dict) and x.get("url")]
            if urls:
                return urls
            # 回落到单一 url 字段
            if isinstance(video.get("url"), str) and video.get("url"):
                return [video.get("url")]
            return None
        except Exception as e:
            print(f"获取下载链接失败: {str(e)}")
            return None


    def get_image_urls_by_platform_id(self, note_id: str) -> Optional[List[str]]:
        """
        根据 platform_item_id 返回图文帖的图片 URL 列表。
        """
        try:
            details = self.get_video_details(note_id) or {}
            if not isinstance(details, dict) or not details:
                return []
            images = details.get("imagesList") or details.get("images_list") or []
            urls: List[str] = []
            if isinstance(images, list):
                for it in images:
                    if isinstance(it, dict):
                        u = it.get("url")
                        if isinstance(u, str) and u.strip():
                            urls.append(u)
            return urls
        except Exception:
            return []

    # ===== 小红书搜索能力 =====
    def fetch_search_posts(self, keyword: str) -> List[Dict[str, Any]]:
        """
        内置分页：基于 XHS_SEARCH_DEFAULT_PARAMS 和 XHS_SEARCH_MAX_ITEMS，
        按 page 翻页，解析 data.data.items 中的 note，返回“原始详情”列表，供基类适配为 PlatformPost。
        仅选择 model_type == "note" 的项。
        keyword 由上游传入，覆盖默认 params 中的 keyword。
        """
        gathered: List[Dict[str, Any]] = []
        page = int(self.XHS_SEARCH_DEFAULT_PARAMS.get("page", 1) or 1)
        total_needed = int(65535)

        while len(gathered) < total_needed:
            params = dict(self.XHS_SEARCH_DEFAULT_PARAMS)
            params["keyword"] = keyword
            params["page"] = page
            url = f"{self.base_url}{self.XHS_SEARCH_API}"
            result = self._make_request(url, params, method="GET")
            if not self._check_api_response(result):
                print(f"搜索接口返回异常: {result}")
                break

            data = result.get("data") or {}
            inner = data.get("data") or {}
            items = inner.get("items") or []
            if not isinstance(items, list) or not items:
                break

            for it in items:
                if len(gathered) >= total_needed:
                    break
                try:
                    if not isinstance(it, dict):
                        continue
                    if str(it.get("model_type") or "").lower() != "note":
                        continue
                    note = it.get("note") or {}
                    if not isinstance(note, dict) or not note:
                        continue
                    gathered.append(note)
                except Exception:
                    continue

            # 简单翻页：若本页有数据则继续下一页，否则停止
            if items:
                page += 1
            else:
                break

        return gathered

    def iter_fetch_search_pages(self, keyword: str):
        """
        按页迭代小红书搜索结果：每次 yield 一页 note 字典列表。
        翻页时带上上一次返回的 searchId/sessionId 到下一次请求参数（search_id/session_id）。
        """
        page = int(self.XHS_SEARCH_DEFAULT_PARAMS.get("page", 1) or 1)
        total_needed = int(65535)
        emitted = 0
        search_id = ""
        session_id = ""

        while emitted < total_needed:
            params = dict(self.XHS_SEARCH_DEFAULT_PARAMS)
            params["keyword"] = keyword
            params["page"] = page
            # 仅在有值时携带翻页 token
            if search_id:
                params["search_id"] = search_id
            if session_id:
                params["session_id"] = session_id

            url = f"{self.base_url}{self.XHS_SEARCH_API}"
            log.info("[Xiaohongshu] 开始请求 (keyword=%s, page=%s) params=%s", keyword, page, json.dumps(params, ensure_ascii=False, indent=2))
            result = self._make_request(url, params, method="GET")
            if not self._check_api_response(result):
                print(f"搜索接口返回异常: {result}")
                break

            data = result.get("data") or {}
            # 兼容不同返回：token 可能在 data 或 data.data 内，命名可能为 searchId/sessionId 或下划线风格
            container = data
            inner = container.get("data") or {}
            items = inner.get("items") or container.get("items") or []

            # 提取下一页所需 token
            search_id_new = container.get("searchId") or inner.get("searchId") or container.get("search_id") or inner.get("search_id")
            session_id_new = container.get("sessionId") or inner.get("sessionId") or container.get("session_id") or inner.get("session_id")
            if isinstance(search_id_new, str) and search_id_new:
                search_id = search_id_new
            if isinstance(session_id_new, str) and session_id_new:
                session_id = session_id_new

            if not isinstance(items, list) or not items:
                break

            page_batch: List[Dict[str, Any]] = []
            for it in items:
                try:
                    if not isinstance(it, dict):
                        continue
                    if str(it.get("model_type") or "").lower() != "note":
                        continue
                    note = it.get("note") or {}
                    if not isinstance(note, dict) or not note:
                        continue
                    page_batch.append(note)
                    emitted += 1
                    if emitted >= total_needed:
                        break
                except Exception:
                    continue

            if page_batch:
                yield page_batch

            # 翻页：若本页有数据且未达上限则继续下一页
            if items and emitted < total_needed:
                page += 1
            else:
                break

    # 兼容命名：fetch_search_page
    def fetch_search_page(self) -> List[Dict[str, Any]]:
        return self.fetch_search_posts()

    def fetch_video_danmaku(self, note_id: str, duration: int, start_time: int = 0, end_time: Optional[int] = None) -> Dict[str, Any]:
        """
        小红书目前不支持弹幕获取
        """
        raise NotImplementedError("小红书平台暂不支持弹幕获取")

    # ===== 评论相关方法（实现 CommentsProvider 协议） =====

    def fetch_video_comments_page(self, note_id: str, cursor: int = 0, count: int = 20) -> Dict[str, Any]:
        """获取小红书笔记的顶层评论分页

        TikHub API: /api/v1/xiaohongshu/app/get_note_comments

        参数：
        - note_id: 笔记ID（必需）
        - cursor: 翻页游标，支持两种格式：
          * 简单格式: "682b0133000000001c03618d"
          * JSON格式: {"cursor":"682b0133000000001c03618d","index":2,"pageArea":"ALL"}
          * 首次请求传 0 或空字符串
        - sort_strategy: 排序策略（1: 默认排序，2: 按最新评论排序）

        返回结构：
        {
            "code": 200,
            "data": {
                "code": 0,
                "success": true,
                "data": {
                    "comments": [...],
                    "cursor": "{\"cursor\":\"...\",\"index\":2,\"pageArea\":\"ALL\"}",
                    "has_more": true,
                    "comment_count": 56
                }
            }
        }
        """
        url = f"{self.base_url}/xiaohongshu/app/get_note_comments"
        params = {
            "note_id": note_id,
            "sort_strategy": "1"  # 默认排序
        }
        # 仅在有游标时添加 start 参数
        if cursor and cursor != 0:
            params["start"] = str(cursor) if not isinstance(cursor, str) else cursor

        return self._make_request(url, params)

    def get_video_comments(self, note_id: str, cursor: int = 0, count: int = 20) -> Optional[Dict[str, Any]]:
        """便捷方法，返回评论数据部分

        返回格式：
        {
            "comments": [...],
            "cursor": "{\"cursor\":\"...\",\"index\":2,\"pageArea\":\"ALL\"}",
            "has_more": true,
            "comment_count": 56
        }
        """
        try:
            result = self.fetch_video_comments_page(note_id, cursor, count)
            if self._check_api_response(result):
                # 小红书返回结构：data.data.data
                outer_data = result.get('data') or {}
                inner_data = outer_data.get('data') or {}
                return inner_data
            else:
                log.warning(f"获取小红书评论失败: {result}")
                return None
        except Exception as e:
            log.error(f"获取小红书评论异常: {e}")
            return None

    def fetch_video_comment_replies_page(self, note_id: str, comment_id: str, cursor: int = 0, count: int = 20) -> Dict[str, Any]:
        """获取小红书评论的子评论（楼中楼）

        TikHub API: /api/v1/xiaohongshu/app/get_note_sub_comments

        参数：
        - note_id: 笔记ID
        - comment_id: 顶层评论ID
        - cursor: 子评论游标（从顶层评论的 sub_comment_cursor 字段获取）
        - count: 每页数量
        """
        url = f"{self.base_url}/xiaohongshu/app/get_note_sub_comments"
        params = {
            "note_id": note_id,
            "root_comment_id": comment_id
        }
        # 仅在有游标时添加 cursor 参数
        if cursor and cursor != 0:
            params["cursor"] = str(cursor) if not isinstance(cursor, str) else cursor

        return self._make_request(url, params)

    def get_video_comment_replies(self, note_id: str, comment_id: str, cursor: int = 0, count: int = 20) -> Optional[Dict[str, Any]]:
        """便捷方法，返回子评论数据部分"""
        try:
            result = self.fetch_video_comment_replies_page(note_id, comment_id, cursor, count)
            if self._check_api_response(result):
                # 小红书返回结构：data.data.data
                outer_data = result.get('data') or {}
                inner_data = outer_data.get('data') or {}
                return inner_data
            else:
                log.warning(f"获取小红书子评论失败: {result}")
                return None
        except Exception as e:
            log.error(f"获取小红书子评论异常: {e}")
            return None

    # ===== 作者信息获取能力 =====
    def fetch_author_info(self, author_id: str) -> Dict[str, Any]:
        """
        根据 user_id 获取小红书作者信息（返回原始 API 响应）

        TikHub API:
        GET /api/v1/xiaohongshu/app/get_user_info?user_id=<USER_ID>

        Args:
            author_id (str): 小红书作者 user_id（如：63cf2fa9000000002702afb8）

        Returns:
            Dict[str, Any]: API 返回的原始作者信息
        """
        if not author_id or not isinstance(author_id, str):
            raise ValueError("author_id 不能为空")

        url = f"{self.base_url}/xiaohongshu/app/get_user_info"
        params = {"user_id": author_id}
        return self._make_request(url, params)

    def get_author_adapter(self):
        """获取小红书作者适配器（暂未实现）"""
        from ..adapters import XiaohongshuAuthorAdapter
        return XiaohongshuAuthorAdapter()


    def _validate_video_id(self, note_id: str) -> None:
        """
        验证小红书笔记 ID

        Args:
            note_id (str): 笔记 ID

        Raises:
            ValueError: 笔记 ID 无效
        """
        if not note_id or not isinstance(note_id, str):
            raise ValueError("小红书笔记 ID 不能为空")

        # TODO: 添加小红书笔记 ID 格式验证
        # 小红书笔记 ID 通常是特定格式，可以在这里添加格式检查


# 便捷函数
def fetch_xiaohongshu_video(note_id: str) -> Optional[Dict[str, Any]]:
    """
    便捷函数：获取小红书视频信息

    Args:
        note_id (str): 小红书笔记 ID

    Returns:
        Optional[Dict[str, Any]]: 视频信息，失败返回 None
    """
    fetcher = XiaohongshuFetcher()
    return fetcher.get_video_details(note_id)


if __name__ == "__main__":
    # 测试代码
    test_note_id = "test_note_id_123"

    try:
        fetcher = XiaohongshuFetcher()
        video_info = fetcher.fetch_video_info(test_note_id)
        print("API 返回结果:")
        print(video_info)

        # 使用便捷方法
        video_details = fetcher.get_video_details(test_note_id)
        if video_details:
            print("\n视频详细信息:")
            print(video_details)
        else:
            print("获取视频详细信息失败")

    except Exception as e:
        print(f"错误: {str(e)}")
