"""
基础视频获取器抽象类
定义所有平台视频获取器的通用接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import os
import requests
from dotenv import load_dotenv

# 仓储用于落库统一领域模型
from ..orm.post_repository import PostRepository

# 加载环境变量
load_dotenv()


class BaseFetcher(ABC):
    """视频获取器基础抽象类"""

    def __init__(self):
        """初始化基础配置"""
        self.api_key = os.getenv('tikhub_API_KEY')
        if not self.api_key:
            raise ValueError("未找到 tikhub_API_KEY 环境变量")

        self.base_url = "https://api.tikhub.io/api/v1"
        self.headers = {
            'accept': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """平台名称"""
        pass

    @property
    @abstractmethod
    def api_endpoint(self) -> str:
        """API 端点路径"""
        pass

    @abstractmethod
    def fetch_video_info(self, video_id: str) -> Dict[str, Any]:
        """
        获取视频信息的抽象方法

        Args:
            video_id (str): 视频 ID

        Returns:
            Dict[str, Any]: API 返回的视频信息

        Raises:
            requests.RequestException: 请求异常
            ValueError: 参数错误
        """
        pass

    @abstractmethod
    def get_video_details(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        获取视频详细信息的抽象方法

        Args:
            video_id (str): 视频 ID

        Returns:
            Optional[Dict[str, Any]]: 视频详细信息，失败返回 None
        """
        pass

    @abstractmethod
    def get_adapter(self):
        """返回该平台的视频适配器，实现 to_post(details)->PlatformPost。"""
        pass

    def get_platform_post(self, video_id: str):
        """高层统一入口：获取领域模型 PlatformPost。
        - 默认基于 fetch_video_info -> get_video_details -> adapter.to_post
        - 子类可重写定制
        """
        details = self.get_video_details(video_id)
        if not details:
            return None
        adapter = self.get_adapter()
        return adapter.to_post(details)

    @abstractmethod
    def fetch_search_posts(self, keyword: str):
        """获取搜索结果的原始条目列表（供适配器消费）。
        参数：
        - keyword: 搜索关键词（由上游传入，不再写死在子类默认配置）

        返回的每个元素应当是适配器 to_post 可直接处理的“详情数据结构”。
        例如：
        - 抖音：{"aweme_detail": { ... }}
        - 小红书：note 字典本身
        子类负责分页与去重，尽量只返回需要的数量。
        """
        pass

    def get_search_posts(self, keyword: str):
        """统一入口：按批查询→转换→落库，返回已落库的 PlatformPost 列表。
        - 子类实现 fetch_search_posts(keyword) 负责分页抓取“原始详情”列表
        - 这里统一调用 adapter.to_post 转为 PlatformPost
        - 逐条 upsert 到仓库（PostRepository），并回填 id
        """
        try:
            raw_items = self.fetch_search_posts(keyword) or []
        except Exception:
            raw_items = []
        posts = []
        adapter = self.get_adapter()
        for raw in raw_items:
            try:
                post = adapter.to_post(raw)
                # 尽力附带原始详情，便于后续弹幕/排查
                try:
                    setattr(post, "raw_details", raw)
                except Exception:
                    pass
                # 入库并返回保存后的对象（带 id）
                saved = PostRepository.upsert_post(post)
                # 若需要，尽力把 id 回写到原对象
                try:
                    if getattr(post, "id", None) is None and getattr(saved, "id", None) is not None:
                        setattr(post, "id", saved.id)
                except Exception:
                    pass
                posts.append(saved)
            except Exception:
                continue
        return posts


    @abstractmethod
    def get_download_urls(self, video_id: str) -> Optional[List[str]]:
        """
        获取视频下载链接的抽象方法

        Args:
            video_id (str): 视频 ID

        Returns:
            Optional[List[str]]: 下载链接列表，失败返回 None
        """
        pass

    def get_preferred_download_url(self, video_id: str) -> Optional[str]:
        """
        便捷方法：返回一个可下载的视频 URL（单条）。
        - 默认策略：调用 get_download_urls(video_id) 并返回第一个非空 URL
        - 子类可重写以实现平台特定的“无水印/高清优先”等策略

        Args:
            video_id (str): 平台视频 ID

        Returns:
            Optional[str]: 可下载的视频 URL，失败返回 None
        """
        try:
            self._validate_video_id(video_id)
            urls = self.get_download_urls(video_id) or []
            for u in urls:
                if isinstance(u, str) and u.strip():
                    return u
            return None
        except Exception:
            return None

    def get_download_url_by_post_id(self, post_id: int) -> Optional[str]:
        """
        便捷方法：根据 post_id 返回一个可下载的视频 URL。
        始终调用平台接口获取最新下载地址（通过 platform_item_id -> get_preferred_download_url）。

        Args:
            post_id (int): 平台帖子在本地数据库中的主键 ID

        Returns:
            Optional[str]: 可下载的视频 URL，失败返回 None
        """
        try:
            if not isinstance(post_id, int) or post_id <= 0:
                raise ValueError("post_id 必须为正整数")

            post = PostRepository.get_by_id(post_id)
            if not post:
                return None

            platform_item_id = getattr(post, "platform_item_id", None)
            if not platform_item_id:
                return None

            return self.get_preferred_download_url(platform_item_id)
        except Exception:
            return None




    def _make_request(self, url: str, params: Dict[str, Any], method: str = "GET") -> Dict[str, Any]:
        """
        发送 HTTP 请求的通用方法

        Args:
            url (str): 请求 URL
            params (Dict[str, Any]): 请求参数（GET 使用 query params，POST 使用 JSON body）
            method (str): 请求方法，支持 "GET" 或 "POST"，默认 "GET"

        Returns:
            Dict[str, Any]: API 响应

        Raises:
            requests.RequestException: 请求异常
        """
        try:
            method_upper = method.upper()
            if method_upper == "POST":
                response = requests.post(url, headers=self.headers, json=params)
            else:
                response = requests.get(url, headers=self.headers, params=params)

            # 尝试解析 JSON 响应
            try:
                json_data = response.json()

                # 检查业务逻辑状态码
                if json_data.get('code') == 200:
                    # 业务逻辑成功，返回数据
                    return json_data
                else:
                    # 业务逻辑失败，但仍然返回数据以便上层处理
                    return json_data

            except ValueError:
                # JSON 解析失败，检查 HTTP 状态码
                response.raise_for_status()
                raise requests.RequestException(f"响应不是有效的 JSON 格式")

        except requests.RequestException as e:
            raise requests.RequestException(f"请求 {self.platform_name} API 失败: {str(e)}")

    def _validate_video_id(self, video_id: str) -> None:
        """
        验证视频 ID 的通用方法

        Args:
            video_id (str): 视频 ID

        Raises:
            ValueError: 视频 ID 无效
        """
        if not video_id or not isinstance(video_id, str):
            raise ValueError(f"{self.platform_name} 视频 ID 不能为空")

    def _check_api_response(self, response: Dict[str, Any]) -> bool:
        """
        检查 API 响应状态的通用方法

        Args:
            response (Dict[str, Any]): API 响应

        Returns:
            bool: 响应是否成功
        """
        # 默认检查 code 字段，子类可以重写此方法
        return response.get('code') == 200

    def __str__(self) -> str:
        """字符串表示"""
        return f"{self.__class__.__name__}(platform={self.platform_name})"

    def __repr__(self) -> str:
        """对象表示"""
        return self.__str__()
