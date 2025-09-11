import os
import requests
from typing import Optional
from urllib.parse import urlparse
import time


class VideoDownloader:
    """视频下载工具类，用于下载网络视频流"""

    def __init__(self, download_dir: str = "downloads"):
        """
        初始化下载器

        Args:
            download_dir (str): 下载目录，默认为 "downloads"
        """
        self.download_dir = download_dir
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        # 确保下载目录存在
        os.makedirs(self.download_dir, exist_ok=True)

    def download_video(self, url: str, filename: Optional[str] = None,
                      chunk_size: int = 8192, timeout: int = 30) -> Optional[str]:
        """
        下载视频文件

        Args:
            url (str): 视频下载链接
            filename (Optional[str]): 保存的文件名，如果为 None 则自动生成
            chunk_size (int): 下载块大小，默认 8192 字节
            timeout (int): 请求超时时间，默认 30 秒

        Returns:
            Optional[str]: 下载成功返回文件路径，失败返回 None
        """
        if not url:
            print("错误: URL 不能为空")
            return None

        try:
            # 发送 HEAD 请求获取文件信息
            head_response = requests.head(url, headers=self.headers, timeout=timeout)
            head_response.raise_for_status()

            # 获取文件大小
            content_length = head_response.headers.get('Content-Length')
            file_size = int(content_length) if content_length else 0

            # 生成文件名
            if filename is None:
                # 从 URL 中提取文件名，或使用时间戳
                parsed_url = urlparse(url)
                url_filename = os.path.basename(parsed_url.path)
                if url_filename and '.' in url_filename:
                    filename = url_filename
                else:
                    # 使用时间戳生成文件名
                    timestamp = int(time.time())
                    filename = f"video_{timestamp}.mp4"

            # 确保文件名有扩展名
            if not filename.endswith('.mp4'):
                filename += '.mp4'

            file_path = os.path.join(self.download_dir, filename)

            print(f"开始下载视频: {filename}")
            if file_size > 0:
                print(f"文件大小: {self._format_size(file_size)}")

            # 下载文件
            response = requests.get(url, headers=self.headers, stream=True, timeout=timeout)
            response.raise_for_status()

            downloaded_size = 0
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)

                        # 显示下载进度
                        if file_size > 0:
                            progress = (downloaded_size / file_size) * 100
                            print(f"\r下载进度: {progress:.1f}% ({self._format_size(downloaded_size)}/{self._format_size(file_size)})", end='')

            print(f"\n✅ 下载完成: {file_path}")
            return file_path

        except requests.RequestException as e:
            print(f"❌ 下载失败 - 网络错误: {str(e)}")
            return None
        except IOError as e:
            print(f"❌ 下载失败 - 文件写入错误: {str(e)}")
            return None
        except Exception as e:
            print(f"❌ 下载失败 - 未知错误: {str(e)}")
            return None

    def download_video_as_bytes(self, url: str, timeout: int = 30) -> Optional[bytes]:
        """
        以字节流的形式下载视频内容并返回 bytes。

        Args:
            url (str): 视频下载链接
            timeout (int): 请求超时时间，默认 30 秒

        Returns:
            Optional[bytes]: 成功返回视频的二进制内容，失败返回 None
        """
        if not url:
            print("错误: URL 不能为空")
            return None
        try:
            response = requests.get(url, headers=self.headers, stream=True, timeout=timeout)
            response.raise_for_status()
            chunks = []
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    chunks.append(chunk)
            return b"".join(chunks)
        except requests.RequestException as e:
            print(f"❌ 下载失败(字节流) - 网络错误: {str(e)}")
            return None
        except Exception as e:
            print(f"❌ 下载失败(字节流) - 未知错误: {str(e)}")
            return None

    def download_video_as_bytes_with_retry(self, url: str, max_retries: int = 3, **kwargs) -> Optional[bytes]:
        """
        带重试的字节流下载。

        Args:
            url (str): 视频下载链接
            max_retries (int): 最大重试次数
            **kwargs: 透传给 download_video_as_bytes 的参数

        Returns:
            Optional[bytes]: 成功返回视频的二进制内容，失败返回 None
        """
        for attempt in range(max_retries + 1):
            if attempt > 0:
                print(f"(字节流) 第 {attempt} 次重试下载...")
                time.sleep(2)
            data = self.download_video_as_bytes(url, **kwargs)
            if data is not None:
                return data
        print(f"❌ 下载失败(字节流)，已重试 {max_retries} 次")
        return None


    def download_video_with_retry(self, url: str, filename: Optional[str] = None,
                                 max_retries: int = 3, **kwargs) -> Optional[str]:
        """
        带重试机制的视频下载

        Args:
            url (str): 视频下载链接
            filename (Optional[str]): 保存的文件名
            max_retries (int): 最大重试次数，默认 3 次
            **kwargs: 其他传递给 download_video 的参数

        Returns:
            Optional[str]: 下载成功返回文件路径，失败返回 None
        """
        for attempt in range(max_retries + 1):
            if attempt > 0:
                print(f"第 {attempt} 次重试下载...")
                time.sleep(2)  # 重试前等待 2 秒

            result = self.download_video(url, filename, **kwargs)
            if result:
                return result

        print(f"❌ 下载失败，已重试 {max_retries} 次")
        return None

    def _format_size(self, size_bytes: int) -> str:
        """
        格式化文件大小显示

        Args:
            size_bytes (int): 字节大小

        Returns:
            str: 格式化后的大小字符串
        """
        if size_bytes == 0:
            return "0B"

        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1

        return f"{size_bytes:.1f}{size_names[i]}"

    def set_download_dir(self, download_dir: str):
        """
        设置下载目录

        Args:
            download_dir (str): 新的下载目录
        """
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)


# 便捷函数
def download_video_from_url(url: str, download_dir: str = "downloads",
                           filename: Optional[str] = None) -> Optional[str]:
    """
    便捷函数：从 URL 下载视频

    Args:
        url (str): 视频下载链接
        download_dir (str): 下载目录，默认为 "downloads"
        filename (Optional[str]): 文件名，如果为 None 则自动生成

    Returns:
        Optional[str]: 下载成功返回文件路径，失败返回 None
    """
    downloader = VideoDownloader(download_dir)
    return downloader.download_video_with_retry(url, filename)
