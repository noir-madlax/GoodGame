# TikHub API 抖音视频下载工具

这是一个用于调用 TikHub API 获取抖音视频信息并下载视频的 Python 工具包。

## 功能特性

- ✅ 调用 TikHub API 获取抖音视频详细信息
- ✅ 解析视频下载链接
- ✅ 下载视频到本地
- ✅ 支持重试机制
- ✅ 显示下载进度
- ✅ 自动生成安全的文件名
- ✅ 完整的错误处理

## 文件结构

```
backend/tikhub_api/
├── __init__.py                 # 包初始化文件
├── douyin_video_fetcher.py     # 抖音视频信息获取器
├── video_downloader.py         # 视频下载工具类
├── workflow.py                 # 完整工作流程
├── test_download.py            # 测试脚本
├── requirements.txt            # 依赖管理
└── README.md                   # 说明文档
```

## 下载目录结构

下载的文件会按以下结构保存：

```
downloads/
└── douyin/
    └── {视频ID}/
        ├── {视频ID}.mp4        # 视频文件
        └── video_info.json     # 完整的视频信息
```

## 安装依赖

```bash
cd backend/tikhub_api
pip install -r requirements.txt
```

## 环境配置

确保在 `backend/.env` 文件中配置了 TikHub API Key：

```env
tikhub_API_KEY=your_api_key_here
```

## 使用方法

### 1. 基础使用 - 获取视频信息

```python
from douyin_video_fetcher import DouyinVideoFetcher

# 创建获取器
fetcher = DouyinVideoFetcher()

# 获取视频信息
aweme_id = "7499608775142608186"
video_info = fetcher.fetch_video_info(aweme_id)
print(video_info)
```

### 2. 获取下载链接

```python
# 获取下载链接列表
download_urls = fetcher.get_download_urls(aweme_id)
if download_urls:
    print(f"找到 {len(download_urls)} 个下载链接")
    print(f"第一个链接: {download_urls[0]}")
```

### 3. 下载视频

```python
from video_downloader import VideoDownloader

# 创建下载器
downloader = VideoDownloader("downloads")

# 下载视频
if download_urls:
    file_path = downloader.download_video_with_retry(
        download_urls[0], 
        "my_video.mp4"
    )
    if file_path:
        print(f"下载成功: {file_path}")
```

### 4. 完整流程 - 一键下载

```python
from workflow import download_douyin_video_complete

# 一键下载抖音视频
aweme_id = "7499608775142608186"
file_path = download_douyin_video_complete(aweme_id, "downloads")

if file_path:
    print(f"视频已下载到: {file_path}")
    # 视频信息保存在: downloads/douyin/{aweme_id}/video_info.json
```

## 运行示例

### 运行完整工作流
```bash
cd backend/tikhub_api
python workflow.py
```

### 运行测试
```bash
cd backend/tikhub_api
python test_download.py
```

## API 说明

### DouyinVideoFetcher 类

- `fetch_video_info(aweme_id)`: 获取完整的视频信息
- `get_video_details(aweme_id)`: 获取视频详细信息
- `get_download_urls(aweme_id)`: 获取下载链接列表

### VideoDownloader 类

- `download_video(url, filename)`: 下载视频
- `download_video_with_retry(url, filename, max_retries)`: 带重试的下载
- `set_download_dir(download_dir)`: 设置下载目录

## 便捷函数

- `fetch_douyin_video(aweme_id)`: 快速获取视频信息
- `download_video_from_url(url, download_dir, filename)`: 快速下载视频
- `download_douyin_video_complete(aweme_id, base_download_dir)`: 完整下载流程，包含目录结构创建和信息保存

## 错误处理

工具包包含完整的错误处理机制：

- 网络连接错误
- API 调用失败
- 文件写入错误
- 无效的视频 ID
- 下载链接失效

## 注意事项

1. 确保 API Key 有效且有足够的调用次数
2. 下载的视频文件可能较大，请确保有足够的磁盘空间
3. 某些视频可能有地域限制或访问限制
4. 请遵守相关法律法规和平台使用条款

## 故障排除

### 常见问题

1. **API Key 错误**
   - 检查 `.env` 文件中的 API Key 是否正确
   - 确认 API Key 是否有效

2. **下载失败**
   - 检查网络连接
   - 尝试使用重试机制
   - 确认视频链接是否有效

3. **文件保存失败**
   - 检查下载目录权限
   - 确认磁盘空间是否充足

### 调试模式

可以在代码中添加更多调试信息：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 许可证

本项目仅供学习和研究使用，请遵守相关法律法规。
