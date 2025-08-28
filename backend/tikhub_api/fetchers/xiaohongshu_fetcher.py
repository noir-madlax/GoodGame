"""
小红书视频获取器
用于调用 TikHub API 获取小红书视频信息
"""

from typing import Dict, Any, Optional, List
from .base_fetcher import BaseFetcher

from ..orm.models import PlatformPost


class XiaohongshuFetcher(BaseFetcher):
    """小红书视频获取器，用于调用 TikHub API 获取小红书视频信息"""

    # 搜索接口与默认配置（改为使用 app/search_notes）
    # 参考示例：/api/v1/xiaohongshu/app/search_notes?keyword=海底捞&page=1&sort_type=general&filter_note_type=不限&filter_note_time=不限
    XHS_SEARCH_API = "/xiaohongshu/app/search_notes"
    XHS_SEARCH_DEFAULT_PARAMS: Dict[str, Any] = {
        "keyword": "海底捞",
        "page": 1,
        "sort_type": "general",
        "filter_note_type": "不限",
        "filter_note_time": "一天内",
    }
    XHS_SEARCH_MAX_ITEMS: int = 10

    @property
    def platform_name(self) -> str:
        """平台名称"""
        return "小红书"

    def get_adapter(self):
        from ..adapters import XiaohongshuVideoAdapter
        return XiaohongshuVideoAdapter()


    @property
    def api_endpoint(self) -> str:
        """API 端点路径"""
        # 切换为 TikHub 小红书 Web v2 feed 接口，数据更完整
        return "/xiaohongshu/web_v2/fetch_feed_notes_v2"

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
        获取视频详细信息（返回 data.note_list[0]）

        Args:
            note_id (str): 小红书笔记 ID

        Returns:
            Optional[Dict[str, Any]]: 单条笔记详情字典（note_list[0]）
        """
        try:
            result = self.fetch_video_info(note_id)

            if self._check_api_response(result):
                payload = result.get("data") or {}
                note_list = payload.get("note_list") or []
                if isinstance(note_list, list) and note_list:
                    return note_list[0]
                else:
                    return None
            else:
                print(f"API 返回信息: {result}")
                return None

        except Exception as e:
            print(f"获取视频信息失败: {str(e)}")
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

    # ===== 小红书搜索能力 =====
    def fetch_search_posts(self) -> List[Dict[str, Any]]:
        """
        内置分页：基于 XHS_SEARCH_DEFAULT_PARAMS 和 XHS_SEARCH_MAX_ITEMS，
        按 page 翻页，解析 data.data.items 中的 note，返回“原始详情”列表，供基类适配为 PlatformPost。
        仅选择 model_type == "note" 的项。
        """
        gathered: List[Dict[str, Any]] = []
        page = int(self.XHS_SEARCH_DEFAULT_PARAMS.get("page", 1) or 1)
        total_needed = int(self.XHS_SEARCH_MAX_ITEMS)

        while len(gathered) < total_needed:
            params = dict(self.XHS_SEARCH_DEFAULT_PARAMS)
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

    # 兼容命名：fetch_search_page
    def fetch_search_page(self) -> List[Dict[str, Any]]:
        return self.fetch_search_posts()

    def fetch_video_danmaku(self, note_id: str, duration: int, start_time: int = 0, end_time: Optional[int] = None) -> Dict[str, Any]:
        """
        小红书目前不支持弹幕获取
        """
        raise NotImplementedError("小红书平台暂不支持弹幕获取")


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
