# MP4视频音频字幕提取工具 - 安装说明

## 系统要求
- macOS (您当前的系统)
- Python 3.8+
- FFmpeg

## 安装步骤

### 1. 安装 FFmpeg
```bash
brew install ffmpeg
```

### 2. 安装 Python 依赖
```bash
pip install -r requirements.txt
```

### 3. 运行程序
```bash
python test.py
```

## 使用说明

1. 确保 `test1.mp4` 文件在当前目录下
2. 运行 `python test.py`
3. 首次运行会自动下载 Whisper small 模型（约 244MB）
4. 等待处理完成，会生成两个文件：
   - `test1_subtitles.srt` - 带时间戳的字幕文件
   - `test1_text.txt` - 纯文本文件

## 注意事项

- 首次运行需要下载模型，请确保网络连接正常
- 处理时间取决于视频长度，66MB的视频大约需要几分钟
- 生成的字幕为简体中文 