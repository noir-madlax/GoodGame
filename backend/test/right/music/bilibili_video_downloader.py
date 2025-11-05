#!/usr/bin/env python3
"""
B站视频下载器
功能：
1. 通过 BVID 获取视频详情信息
2. 获取视频播放地址
3. 下载视频文件到指定目录

支持两种 API：
- TikHub API (优先尝试)
- Bilibili 公开 API (备用)
"""

import os
import json
import time
import requests
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.parse import urlparse, parse_qs

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


def load_api_key() -> str:
    """从环境变量或 .env 文件加载 TikHub 的 API Key"""
    api_key = os.getenv("tikhub_API_KEY")
    if api_key:
        return api_key
    
    # 尝试加载项目根目录的 .env 文件
    project_root = Path(__file__).resolve().parents[3]  # backend 目录
    backend_env = project_root / ".env"
    
    if load_dotenv and backend_env.exists():
        load_dotenv(backend_env)
        api_key = os.getenv("tikhub_API_KEY")
        if api_key:
            return api_key
    
    # 手动读取 .env 文件
    if backend_env.exists():
        for line in backend_env.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("tikhub_API_KEY"):
                parts = line.split("=", 1)
                if len(parts) == 2:
                    return parts[1].strip()
    
    raise RuntimeError("tikhub_API_KEY not found in environment or .env files")


def extract_bvid_from_url(url: str) -> Optional[str]:
    """从 B站 URL 中提取 BVID
    
    Args:
        url: B站视频链接
        
    Returns:
        BVID 字符串，例如 "BV1vwGPzDEUr"
    """
    try:
        # 方法1: 从路径中提取 /video/BV...
        if "/video/" in url:
            parts = url.split("/video/")
            if len(parts) > 1:
                bvid = parts[1].split("?")[0].split("/")[0]
                if bvid.startswith("BV"):
                    return bvid
        
        # 方法2: 从查询参数中提取
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        if "bvid" in params:
            return params["bvid"][0]
        
        return None
    except Exception as e:
        print(f"提取 BVID 失败: {e}")
        return None


class BilibiliVideoDownloader:
    """B站视频下载器类"""
    
    # TikHub API 的多个可用端点
    TIKHUB_BASE_URLS = [
        "https://api.tikhub.io",
        "https://open.tikhub.cn",
        "https://tikhub.io"
    ]
    
    # Bilibili 公开 API
    BILIBILI_API_BASE = "https://api.bilibili.com"
    
    def __init__(self, api_key: Optional[str], output_dir: Path):
        """初始化下载器
        
        Args:
            api_key: TikHub API Key（可选）
            output_dir: 输出目录路径
        """
        self.api_key = api_key
        self.output_dir = output_dir
        self.tikhub_headers = {
            "Authorization": f"Bearer {api_key}" if api_key else "",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        self.bilibili_headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": "https://www.bilibili.com/"
        }
        
        # 确保输出目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _try_request(self, endpoint: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """尝试使用多个 base URL 发起请求
        
        Args:
            endpoint: API 端点路径
            params: 请求参数
            
        Returns:
            API 响应的 JSON 数据，失败返回 None
        """
        last_error = None
        
        for base_url in self.TIKHUB_BASE_URLS:
            url = f"{base_url}{endpoint}"
            try:
                print(f"正在请求: {url}")
                print(f"参数: {json.dumps(params, ensure_ascii=False)}")
                
                response = requests.get(
                    url,
                    headers=self.tikhub_headers,
                    params=params,
                    timeout=60
                )
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"请求成功，使用的 base URL: {base_url}")
                        return data
                    except Exception as e:
                        print(f"JSON 解析失败: {e}")
                        last_error = e
                        continue
                else:
                    print(f"HTTP 状态码: {response.status_code}")
                    last_error = Exception(f"HTTP {response.status_code}")
                    continue
                    
            except Exception as e:
                print(f"请求失败 ({base_url}): {e}")
                last_error = e
                continue
        
        if last_error:
            print(f"所有 base URL 都失败了，最后错误: {last_error}")
        
        return None
    
    def fetch_video_detail_bilibili(self, bvid: str) -> Optional[Dict[str, Any]]:
        """使用 Bilibili 公开 API 获取视频详情
        
        Args:
            bvid: B站视频的 BVID
            
        Returns:
            视频详情数据，失败返回 None
        """
        url = f"{self.BILIBILI_API_BASE}/x/web-interface/view"
        params = {"bvid": bvid}
        
        try:
            print(f"正在请求 Bilibili API: {url}")
            response = requests.get(url, headers=self.bilibili_headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0:  # Bilibili API 成功返回 code=0
                    print("✓ Bilibili API 请求成功")
                    return data
                else:
                    print(f"Bilibili API 返回错误: {data.get('message')}")
            else:
                print(f"HTTP 状态码: {response.status_code}")
        except Exception as e:
            print(f"请求 Bilibili API 失败: {e}")
        
        return None
    
    def fetch_video_detail(self, bvid: str) -> Optional[Dict[str, Any]]:
        """获取视频详情信息（优先使用 TikHub，失败则使用 Bilibili 公开 API）
        
        Args:
            bvid: B站视频的 BVID
            
        Returns:
            视频详情数据，失败返回 None
        """
        print(f"\n========== 步骤1: 获取视频详情 ==========")
        print(f"BVID: {bvid}")
        
        # 方案1: 尝试使用 TikHub API
        if self.api_key:
            print("\n尝试使用 TikHub API...")
            endpoint = "/api/v1/bilibili/web/fetch_video_detail"
            params = {"bvid": bvid}
            result = self._try_request(endpoint, params)
            
            if result and result.get("code") == 200:
                print("✓ TikHub API 获取成功")
                return result
            else:
                print("✗ TikHub API 获取失败，尝试 Bilibili 公开 API...")
        
        # 方案2: 使用 Bilibili 公开 API
        print("\n使用 Bilibili 公开 API...")
        result = self.fetch_video_detail_bilibili(bvid)
        
        if result:
            print("✓ 视频详情获取成功")
            return result
        else:
            print("✗ 视频详情获取失败")
            return None
    
    def fetch_play_url_bilibili(self, bvid: str, cid: str) -> Optional[Dict[str, Any]]:
        """使用 Bilibili 公开 API 获取视频播放地址
        
        Args:
            bvid: B站视频的 BVID
            cid: 视频的 CID
            
        Returns:
            播放地址数据，失败返回 None
        """
        url = f"{self.BILIBILI_API_BASE}/x/player/playurl"
        params = {
            "bvid": bvid,
            "cid": cid,
            "qn": 80,  # 清晰度：80=1080P, 64=720P, 32=480P, 16=360P
            "fnval": 0  # 返回格式：0=FLV/MP4
        }
        
        try:
            print(f"正在请求 Bilibili 播放地址 API: {url}")
            response = requests.get(url, headers=self.bilibili_headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0:
                    print("✓ Bilibili 播放地址 API 请求成功")
                    return data
                else:
                    print(f"Bilibili API 返回错误: {data.get('message')}")
            else:
                print(f"HTTP 状态码: {response.status_code}")
        except Exception as e:
            print(f"请求 Bilibili 播放地址 API 失败: {e}")
        
        return None
    
    def fetch_play_url(self, bvid: str, cid: str) -> Optional[Dict[str, Any]]:
        """获取视频播放地址（优先使用 TikHub，失败则使用 Bilibili 公开 API）
        
        Args:
            bvid: B站视频的 BVID
            cid: 视频的 CID（从详情中获取）
            
        Returns:
            播放地址数据，失败返回 None
        """
        print(f"\n========== 步骤2: 获取视频播放地址 ==========")
        print(f"BVID: {bvid}, CID: {cid}")
        
        # 方案1: 尝试使用 TikHub API
        if self.api_key:
            print("\n尝试使用 TikHub API...")
            endpoint = "/api/v1/bilibili/web/fetch_play_url"
            params = {"bvid": bvid, "cid": cid}
            result = self._try_request(endpoint, params)
            
            if result and result.get("code") == 200:
                print("✓ TikHub API 获取成功")
                return result
            else:
                print("✗ TikHub API 获取失败，尝试 Bilibili 公开 API...")
        
        # 方案2: 使用 Bilibili 公开 API
        print("\n使用 Bilibili 公开 API...")
        result = self.fetch_play_url_bilibili(bvid, cid)
        
        if result:
            print("✓ 播放地址获取成功")
            return result
        else:
            print("✗ 播放地址获取失败")
            return None
    
    def download_video(self, url: str, filename: str) -> bool:
        """下载视频文件
        
        Args:
            url: 视频下载地址
            filename: 保存的文件名
            
        Returns:
            下载是否成功
        """
        print(f"\n========== 步骤3: 下载视频文件 ==========")
        print(f"文件名: {filename}")
        
        filepath = self.output_dir / filename
        
        try:
            # 添加 Referer 和 User-Agent 头，防止 B站 403
            download_headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Referer": "https://www.bilibili.com/"
            }
            
            print(f"开始下载: {url}")
            response = requests.get(url, headers=download_headers, stream=True, timeout=300)
            response.raise_for_status()
            
            # 获取文件大小
            total_size = int(response.headers.get('content-length', 0))
            print(f"文件大小: {total_size / (1024*1024):.2f} MB")
            
            # 下载文件
            downloaded_size = 0
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        # 显示进度
                        if total_size > 0:
                            progress = (downloaded_size / total_size) * 100
                            print(f"\r下载进度: {progress:.1f}%", end='', flush=True)
            
            print(f"\n✓ 视频下载成功: {filepath}")
            return True
            
        except Exception as e:
            print(f"\n✗ 视频下载失败: {e}")
            return False
    
    def save_json(self, data: Dict[str, Any], filename: str) -> Path:
        """保存 JSON 数据到文件
        
        Args:
            data: 要保存的数据
            filename: 文件名
            
        Returns:
            保存的文件路径
        """
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✓ JSON 保存成功: {filepath}")
        return filepath
    
    def process_video(self, url_or_bvid: str) -> bool:
        """处理视频：获取详情和下载
        
        Args:
            url_or_bvid: B站视频链接或 BVID
            
        Returns:
            处理是否成功
        """
        # 提取 BVID
        if url_or_bvid.startswith("http"):
            bvid = extract_bvid_from_url(url_or_bvid)
            if not bvid:
                print(f"✗ 无法从 URL 中提取 BVID: {url_or_bvid}")
                return False
        else:
            bvid = url_or_bvid
        
        print(f"\n{'='*50}")
        print(f"开始处理视频: {bvid}")
        print(f"{'='*50}")
        
        # 1. 获取视频详情
        video_detail = self.fetch_video_detail(bvid)
        if not video_detail:
            print("✗ 无法获取视频详情")
            return False
        
        # 保存详情信息
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        detail_filename = f"bilibili_{bvid}_detail_{timestamp}.json"
        self.save_json(video_detail, detail_filename)
        
        # 提取关键信息（兼容 TikHub 和 Bilibili API 的返回格式）
        try:
            # 尝试 TikHub API 格式
            if "data" in video_detail and "data" in video_detail.get("data", {}):
                data = video_detail["data"]["data"]
            # 尝试 Bilibili 公开 API 格式
            elif "data" in video_detail:
                data = video_detail["data"]
            else:
                print("✗ 无法解析视频详情数据结构")
                return False
            
            title = data.get("title", "未知标题")
            cid = data.get("cid")
            owner = data.get("owner", {})
            owner_name = owner.get("name", "未知UP主")
            desc = data.get("desc", "")
            
            print(f"\n视频信息:")
            print(f"  标题: {title}")
            print(f"  UP主: {owner_name}")
            print(f"  简介: {desc[:100]}..." if len(desc) > 100 else f"  简介: {desc}")
            print(f"  CID: {cid}")
            
            if not cid:
                print("✗ 无法获取 CID")
                return False
        except Exception as e:
            print(f"✗ 解析视频详情失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # 2. 获取播放地址
        play_url_data = self.fetch_play_url(bvid, str(cid))
        if not play_url_data:
            print("✗ 无法获取播放地址")
            return False
        
        # 保存播放地址信息
        playurl_filename = f"bilibili_{bvid}_playurl_{timestamp}.json"
        self.save_json(play_url_data, playurl_filename)
        
        # 提取下载地址（兼容 TikHub 和 Bilibili API 的返回格式）
        try:
            # 尝试 TikHub API 格式
            if "data" in play_url_data and "data" in play_url_data.get("data", {}):
                play_data = play_url_data["data"]["data"]
            # 尝试 Bilibili 公开 API 格式
            elif "data" in play_url_data:
                play_data = play_url_data["data"]
            else:
                print("✗ 无法解析播放地址数据结构")
                return False
            
            durl = play_data.get("durl", [])
            
            if not durl:
                print("✗ 未找到下载地址")
                print(f"播放地址数据: {json.dumps(play_data, ensure_ascii=False, indent=2)[:500]}")
                return False
            
            # 获取第一个视频流的 URL
            video_url = durl[0].get("url")
            if not video_url:
                print("✗ 视频 URL 为空")
                return False
            
            print(f"\n下载地址: {video_url[:100]}...")
            
        except Exception as e:
            print(f"✗ 解析播放地址失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # 3. 下载视频
        # 清理文件名中的特殊字符
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_'))[:50]
        video_filename = f"bilibili_{bvid}_{safe_title}.mp4"
        
        success = self.download_video(video_url, video_filename)
        
        if success:
            print(f"\n{'='*50}")
            print(f"✓ 全部完成！")
            print(f"{'='*50}")
            print(f"\n输出文件:")
            print(f"  视频详情: {detail_filename}")
            print(f"  播放地址: {playurl_filename}")
            print(f"  视频文件: {video_filename}")
            print(f"\n所有文件保存在: {self.output_dir}")
        
        return success


def main():
    """主函数"""
    # B站视频链接
    video_url = "https://www.bilibili.com/video/BV1vwGPzDEUr?buvid=4a8ff982501d4c982953d1926a14c5a0&from_spmid=search.search-result.0.0&is_story_h5=false&mid=81viHxdKD6KP0KQuEUnjtQ%3D%3D&plat_id=116&share_from=ugc&share_medium=iphone&share_plat=ios&share_session_id=29B4ECAE-7BA7-45C1-91FF-EB470D50BDDB&share_source=COPY&share_tag=s_i&spmid=united.player-video-detail.0.0&timestamp=1762245188&unique_k=v96ekIj&up_id=1832807524&vd_source=3d1a30968b278a2beb02c0503f296200"
    
    try:
        # 尝试加载 API Key（可选）
        print("正在加载 TikHub API Key...")
        try:
            api_key = load_api_key()
            print("✓ API Key 加载成功")
        except Exception:
            print("⚠ API Key 未找到，将使用 Bilibili 公开 API")
            api_key = None
        
        # 设置输出目录
        output_dir = Path(__file__).resolve().parent / "output"
        print(f"输出目录: {output_dir}")
        
        # 创建下载器
        downloader = BilibiliVideoDownloader(api_key, output_dir)
        
        # 处理视频
        success = downloader.process_video(video_url)
        
        if not success:
            print("\n处理失败，请检查错误信息")
            exit(1)
        
    except Exception as e:
        print(f"\n发生错误: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()

