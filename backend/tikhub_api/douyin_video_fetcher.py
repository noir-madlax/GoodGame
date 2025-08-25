import os
import requests
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class DouyinVideoFetcher:
    """抖音视频获取器，用于调用 TikHub API 获取抖音视频信息"""
    
    def __init__(self):
        """初始化，从环境变量获取 API Key"""
        self.api_key = os.getenv('tikhub_API_KEY')
        if not self.api_key:
            raise ValueError("未找到 tikhub_API_KEY 环境变量")
        
        self.base_url = "https://api.tikhub.io/api/v1/douyin/web"
        self.headers = {
            'accept': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
    
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
        if not aweme_id:
            raise ValueError("aweme_id 不能为空")
        
        url = f"{self.base_url}/fetch_one_video"
        params = {'aweme_id': aweme_id}
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()  # 如果状态码不是 2xx，会抛出异常
            
            return response.json()
            
        except requests.RequestException as e:
            raise requests.RequestException(f"请求 TikHub API 失败: {str(e)}")
    
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
            if result.get('code') == 200:  # 修正状态码判断
                return result.get('data')
            else:
                print(f"API 返回错误: {result.get('message', '未知错误')}")
                return None

        except Exception as e:
            print(f"获取视频信息失败: {str(e)}")
            return None

    def get_download_urls(self, aweme_id: str) -> Optional[list]:
        """
        获取视频下载链接列表

        Args:
            aweme_id (str): 抖音视频 ID

        Returns:
            Optional[list]: 下载链接列表，如果获取失败返回 None
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
