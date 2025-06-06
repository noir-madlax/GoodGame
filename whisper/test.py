#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MP4视频音频字幕提取工具
使用OpenAI Whisper进行中文语音识别，生成带时间戳的SRT字幕文件
"""

import os
import sys
import whisper
from pathlib import Path
import subprocess

def check_ffmpeg():
    """检查系统是否安装了ffmpeg"""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        print("✅ FFmpeg 已安装")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ FFmpeg 未安装")
        print("请先安装 FFmpeg:")
        print("brew install ffmpeg")
        return False

def format_timestamp(seconds):
    """将秒数转换为SRT时间戳格式 (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millisecs = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"

def generate_srt(result, output_path):
    """生成SRT字幕文件"""
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, segment in enumerate(result['segments'], 1):
            start_time = format_timestamp(segment['start'])
            end_time = format_timestamp(segment['end'])
            text = segment['text'].strip()
            
            f.write(f"{i}\n")
            f.write(f"{start_time} --> {end_time}\n")
            f.write(f"{text}\n\n")
    
    print(f"✅ SRT字幕文件已生成: {output_path}")

def extract_audio_subtitles(video_path, output_dir=".", model_size="tiny"):
    """从MP4视频中提取音频并生成中文字幕
    
    Args:
        video_path: 视频文件路径
        output_dir: 输出目录
        model_size: 模型大小 ('tiny', 'base', 'small', 'medium', 'large')
                   tiny: 39MB, 最快但准确度较低
                   base: 74MB, 平衡速度和准确度  
                   small: 244MB, 较好准确度
    """
    
    # 检查输入文件是否存在
    if not os.path.exists(video_path):
        print(f"❌ 视频文件不存在: {video_path}")
        return False
    
    # 检查ffmpeg
    if not check_ffmpeg():
        return False
    
    print(f"🎬 开始处理视频: {video_path}")
    print(f"📁 输出目录: {output_dir}")
    
    # 获取文件名（不含扩展名）
    video_name = Path(video_path).stem
    
    try:
        # 加载Whisper模型 - 添加重试机制
        print(f"🤖 正在加载 Whisper {model_size} 模型...")
        print("⏳ 首次使用会下载模型文件，请耐心等待...")
        
        # 显示模型信息
        model_info = {
            'tiny': '39MB - 最快速度，适合快速测试',
            'base': '74MB - 平衡速度和准确度',
            'small': '244MB - 较好准确度',
            'medium': '769MB - 高准确度',
            'large': '1550MB - 最高准确度'
        }
        print(f"📋 使用模型: {model_size} ({model_info.get(model_size, '未知')})")
        
        model = None
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                model = whisper.load_model(model_size)
                print("✅ 模型加载完成")
                break
            except Exception as e:
                print(f"⚠️  模型加载失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if "checksum" in str(e).lower():
                    print("🔄 检测到校验和错误，清理缓存后重试...")
                    # 清理可能损坏的缓存文件
                    import shutil
                    cache_dir = os.path.expanduser("~/.cache/whisper")
                    if os.path.exists(cache_dir):
                        shutil.rmtree(cache_dir)
                        print("🗑️  已清理模型缓存")
                
                if attempt == max_retries - 1:
                    print("❌ 模型加载失败，已达到最大重试次数")
                    print("💡 建议:")
                    print("   1. 检查网络连接是否稳定")
                    print("   2. 尝试使用更小的模型: 将 'small' 改为 'base' 或 'tiny'")
                    print("   3. 手动清理缓存: rm -rf ~/.cache/whisper")
                    return False
                else:
                    print(f"⏳ 等待 3 秒后重试...")
                    import time
                    time.sleep(3)
        
        if model is None:
            return False
        
        # 进行语音识别
        print("🎵 开始音频识别...")
        print("⏳ 这可能需要几分钟时间，请耐心等待...")
        
        # 设置识别参数：指定中文，启用详细输出
        result = model.transcribe(
            video_path,
            language='zh',  # 指定中文
            verbose=True,   # 显示进度
            word_timestamps=False  # 不需要单词级时间戳
        )
        
        print("✅ 音频识别完成")
        
        # 生成输出文件路径
        srt_path = os.path.join(output_dir, f"{video_name}_subtitles.srt")
        txt_path = os.path.join(output_dir, f"{video_name}_text.txt")
        
        # 生成SRT字幕文件
        generate_srt(result, srt_path)
        
        # 生成纯文本文件
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(result['text'])
        print(f"✅ 纯文本文件已生成: {txt_path}")
        
        # 显示识别结果统计
        print(f"\n📊 识别结果统计:")
        print(f"   总段落数: {len(result['segments'])}")
        print(f"   识别语言: {result.get('language', 'zh')}")
        print(f"   总文字长度: {len(result['text'])} 字符")
        
        # 显示前几段内容预览
        print(f"\n📝 内容预览:")
        for i, segment in enumerate(result['segments'][:3], 1):
            start_time = format_timestamp(segment['start'])
            end_time = format_timestamp(segment['end'])
            text = segment['text'].strip()
            print(f"   {i}. [{start_time} - {end_time}] {text}")
        
        if len(result['segments']) > 3:
            print(f"   ... 还有 {len(result['segments']) - 3} 段内容")
        
        return True
        
    except Exception as e:
        print(f"❌ 处理过程中出现错误: {str(e)}")
        return False

def main():
    """主函数"""
    print("🎬 MP4视频音频字幕提取工具")
    print("=" * 50)
    
    # 设置视频文件路径
    video_file = "test1.mp4"
    
    # 检查文件是否存在
    if not os.path.exists(video_file):
        print(f"❌ 找不到视频文件: {video_file}")
        print("请确保 test1.mp4 文件在当前目录下")
        return
    
    # 显示文件信息
    file_size = os.path.getsize(video_file) / (1024 * 1024)  # MB
    print(f"📁 视频文件: {video_file}")
    print(f"📏 文件大小: {file_size:.1f} MB")
    print()
    
    # 开始处理
    success = extract_audio_subtitles(video_file)
    
    if success:
        print("\n🎉 处理完成！")
        print("📄 生成的文件:")
        print(f"   - test1_subtitles.srt (带时间戳的字幕文件)")
        print(f"   - test1_text.txt (纯文本文件)")
    else:
        print("\n❌ 处理失败，请检查错误信息")

if __name__ == "__main__":
    main()
