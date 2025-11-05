#!/usr/bin/env python3
"""
视频切割脚本
将大视频文件切割成多个 30 分钟的分段文件
使用 ffmpeg 进行切割
"""

import subprocess
import os
import sys
from pathlib import Path


def get_video_duration(video_path):
    """获取视频时长（秒）"""
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        duration = float(result.stdout.strip())
        return duration
    except subprocess.CalledProcessError as e:
        print(f"错误：无法获取视频时长 - {e}")
        sys.exit(1)
    except ValueError:
        print("错误：无法解析视频时长")
        sys.exit(1)


def split_video(input_file, segment_duration=1800, output_dir=None):
    """
    切割视频文件
    
    Args:
        input_file: 输入视频文件路径
        segment_duration: 每段时长（秒），默认 1800 秒 = 30 分钟
        output_dir: 输出目录，默认为输入文件所在目录
    """
    input_path = Path(input_file)
    
    if not input_path.exists():
        print(f"错误：文件不存在 - {input_file}")
        sys.exit(1)
    
    # 设置输出目录
    if output_dir is None:
        output_dir = input_path.parent
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    
    # 获取视频总时长
    total_duration = get_video_duration(str(input_path))
    print(f"视频总时长: {total_duration:.2f} 秒 ({total_duration/60:.2f} 分钟)")
    
    # 计算需要切割的段数
    num_segments = int(total_duration / segment_duration) + (1 if total_duration % segment_duration > 0 else 0)
    print(f"将切割成 {num_segments} 段，每段 {segment_duration/60} 分钟")
    
    # 获取文件名（不含扩展名）和扩展名
    file_stem = input_path.stem
    file_ext = input_path.suffix
    
    # 切割视频
    for i in range(num_segments):
        start_time = i * segment_duration
        output_file = output_dir / f"{file_stem}_part{i+1:02d}{file_ext}"
        
        print(f"\n正在处理第 {i+1}/{num_segments} 段...")
        print(f"起始时间: {start_time} 秒")
        print(f"输出文件: {output_file}")
        
        # 使用 ffmpeg 切割
        # -ss: 起始时间
        # -t: 持续时间
        # -c copy: 直接复制流，不重新编码（速度快）
        # -avoid_negative_ts make_zero: 避免负时间戳问题
        cmd = [
            'ffmpeg',
            '-i', str(input_path),
            '-ss', str(start_time),
            '-t', str(segment_duration),
            '-c', 'copy',
            '-avoid_negative_ts', 'make_zero',
            '-y',  # 覆盖已存在的文件
            str(output_file)
        ]
        
        try:
            subprocess.run(cmd, check=True)
            print(f"✓ 第 {i+1} 段切割完成")
        except subprocess.CalledProcessError as e:
            print(f"✗ 第 {i+1} 段切割失败 - {e}")
            continue
    
    print(f"\n所有切割完成！输出目录: {output_dir}")


def main():
    # 默认视频文件
    default_video = "喜剧之王单口季第 2 季 第 2 期（四） 大鹏回应张彩林戏份一剪梅.ts"
    
    # 获取脚本所在目录
    script_dir = Path(__file__).parent
    video_path = script_dir / default_video
    
    # 如果命令行提供了参数，使用命令行参数
    if len(sys.argv) > 1:
        video_path = Path(sys.argv[1])
    
    # 检查 ffmpeg 和 ffprobe 是否安装
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        subprocess.run(['ffprobe', '-version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("错误：需要安装 ffmpeg 和 ffprobe")
        print("macOS 安装: brew install ffmpeg")
        print("Ubuntu 安装: sudo apt-get install ffmpeg")
        sys.exit(1)
    
    print(f"开始切割视频: {video_path}")
    print("=" * 60)
    
    # 切割视频，30 分钟一段
    split_video(str(video_path), segment_duration=1800)


if __name__ == "__main__":
    main()

