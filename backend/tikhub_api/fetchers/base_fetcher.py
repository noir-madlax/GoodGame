"""
基础视频获取器抽象类
定义所有平台视频获取器的通用接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import os
import requests
from dotenv import load_dotenv

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
    def get_download_urls(self, video_id: str) -> Optional[List[str]]:
        """
        获取视频下载链接的抽象方法

        Args:
            video_id (str): 视频 ID

        Returns:
            Optional[List[str]]: 下载链接列表，失败返回 None
        """
        pass

    @abstractmethod
    def fetch_video_danmaku(self, video_id: str, duration: int, start_time: int = 0,
                             end_time: Optional[int] = None) -> Dict[str, Any]:
        """
        获取视频弹幕的抽象方法（由具体平台实现）

        Args:
            video_id (str): 视频 ID
            duration (int): 视频时长（毫秒）
            start_time (int): 开始时间（毫秒），默认 0
            end_time (Optional[int]): 结束时间（毫秒），默认 None 表示使用 duration-1

        Returns:
            Dict[str, Any]: API 返回的原始响应
        """
        pass

    def get_video_danmaku(self, video_id: str, duration: int, start_time: int = 0,
                           end_time: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        获取视频弹幕的便捷方法（调用平台实现并做通用成功检查）

        Args:
            video_id (str): 视频 ID
            duration (int): 视频时长（毫秒）
            start_time (int): 开始时间（毫秒），默认 0
            end_time (Optional[int]): 结束时间（毫秒），默认 None 表示使用 duration-1

        Returns:
            Optional[Dict[str, Any]]: 成功时返回 data 字段内容，失败返回 None
        """
        try:
            result = self.fetch_video_danmaku(video_id, duration, start_time, end_time)
            if self._check_api_response(result):
                return result.get('data')
            else:
                print(f"获取弹幕失败: {result.get('message', '未知错误')}")
                return None
        except Exception as e:
            print(f"获取弹幕信息失败: {str(e)}")
            return None


    def _make_request(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送 HTTP 请求的通用方法

        Args:
            url (str): 请求 URL
            params (Dict[str, Any]): 请求参数

        Returns:
            Dict[str, Any]: API 响应

        Raises:
            requests.RequestException: 请求异常
        """
        try:
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
