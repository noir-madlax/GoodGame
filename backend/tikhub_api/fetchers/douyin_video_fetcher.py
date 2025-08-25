from typing import Dict, Any, Optional, List
from .base_fetcher import BaseFetcher


class DouyinVideoFetcher(BaseFetcher):
    """抖音视频获取器，用于调用 TikHub API 获取抖音视频信息"""

    @property
    def platform_name(self) -> str:
        """平台名称"""
        return "抖音"

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
                print(f"API 返回错误: {result.get('message', '未知错误')}")
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
