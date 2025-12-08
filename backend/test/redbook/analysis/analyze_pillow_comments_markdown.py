#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
抱枕评论整体分析脚本 - Markdown 输出版本

使用 Gemini 2.5 Flash 一次性分析所有小红书抱枕相关帖子的评论，
直接输出 Markdown 格式的分析报告。

使用方法：
    python analyze_pillow_comments_markdown.py
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("❌ 请安装 google-genai: pip install google-genai")
    sys.exit(1)

# 配置
GEMINI_MODEL = "gemini-2.5-flash"
TEMPERATURE = 0.3  # 稍高温度允许更自然的报告写作


def load_env() -> str:
    """加载环境变量"""
    backend_dir = Path(__file__).parent.parent.parent.parent
    env_path = backend_dir / '.env'
    
    if env_path.exists():
        load_dotenv(env_path)
    
    api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GEMINI_API_KEY_ANALYZE')
    if not api_key:
        raise ValueError("未找到 GEMINI_API_KEY 环境变量")
    
    return api_key


def load_prompt() -> str:
    """加载 Markdown 输出版本的分析 prompt"""
    prompt_path = Path(__file__).parent / 'pillow_comment_analysis_prompt_markdown.txt'
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt 文件不存在: {prompt_path}")
    
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()


def load_post_info(note_id: str, search_dir: Path) -> Optional[Dict[str, Any]]:
    """从搜索结果加载帖子信息"""
    for page_file in search_dir.glob('page_*.json'):
        with open(page_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        items = data.get('data', {}).get('data', {}).get('items', [])
        for item in items:
            if item.get('model_type') != 'note':
                continue
            note = item.get('note', {})
            if note.get('id') == note_id:
                user = note.get('user', {})
                return {
                    'note_id': note_id,
                    'title': note.get('title', ''),
                    'content': note.get('desc', ''),
                    'author_name': user.get('nickname', ''),
                    'note_type': note.get('type', 'normal'),
                    'liked_count': note.get('liked_count', 0),
                    'comments_count': note.get('comments_count', 0),
                    'collected_count': note.get('collected_count', 0)
                }
    return None


def load_all_data() -> Dict[str, Any]:
    """加载所有帖子和评论数据"""
    base_dir = Path(__file__).parent.parent
    comment_dir = base_dir / 'comment' / 'output'
    search_dir = base_dir / 'search' / 'output'
    
    all_posts = []
    total_main = 0
    total_sub = 0
    
    # 遍历所有主评论文件
    for main_file in sorted(comment_dir.glob('main_comments_*.json')):
        note_id = main_file.stem.replace('main_comments_', '')
        
        # 加载帖子信息
        post_info = load_post_info(note_id, search_dir)
        if not post_info:
            continue
        
        # 加载主评论
        with open(main_file, 'r', encoding='utf-8') as f:
            main_data = json.load(f)
        main_comments = main_data.get('comments', [])
        
        # 加载子评论
        sub_file = comment_dir / f'sub_comments_{note_id}.json'
        sub_comments = {}
        if sub_file.exists():
            with open(sub_file, 'r', encoding='utf-8') as f:
                sub_data = json.load(f)
            sub_comments = sub_data.get('sub_comments', {})
        
        total_main += len(main_comments)
        total_sub += sum(len(subs) for subs in sub_comments.values())
        
        all_posts.append({
            'post_info': post_info,
            'main_comments': main_comments,
            'sub_comments': sub_comments
        })
    
    return {
        'posts': all_posts,
        'stats': {
            'total_posts': len(all_posts),
            'total_main_comments': total_main,
            'total_sub_comments': total_sub,
            'total_comments': total_main + total_sub
        }
    }


def format_all_data_for_llm(data: Dict[str, Any]) -> str:
    """格式化所有数据供 LLM 分析"""
    lines = []
    stats = data['stats']
    
    # 数据概览
    lines.append("=" * 60)
    lines.append("数据概览")
    lines.append("=" * 60)
    lines.append(f"帖子总数: {stats['total_posts']}")
    lines.append(f"主评论总数: {stats['total_main_comments']}")
    lines.append(f"子评论总数: {stats['total_sub_comments']}")
    lines.append(f"评论总数: {stats['total_comments']}")
    lines.append("")
    
    # 每个帖子的数据
    for i, post_data in enumerate(data['posts'], 1):
        post_info = post_data['post_info']
        main_comments = post_data['main_comments']
        sub_comments = post_data['sub_comments']
        
        lines.append("=" * 60)
        lines.append(f"【帖子 {i}/{stats['total_posts']}】")
        lines.append("=" * 60)
        lines.append(f"标题: {post_info['title']}")
        lines.append(f"内容: {post_info['content'][:200]}{'...' if len(post_info.get('content', '')) > 200 else ''}")
        lines.append(f"作者: {post_info['author_name']}")
        lines.append(f"类型: {post_info['note_type']}")
        lines.append(f"互动: 👍{post_info['liked_count']} 💬{post_info['comments_count']} ⭐{post_info['collected_count']}")
        lines.append(f"评论数: 主评论 {len(main_comments)} 条，子评论 {sum(len(s) for s in sub_comments.values())} 条")
        lines.append("")
        
        # 评论列表
        lines.append("--- 评论列表 ---")
        for j, comment in enumerate(main_comments, 1):
            comment_id = comment.get('id', '')
            content = comment.get('content', '')
            user = comment.get('user_nickname', '匿名')
            likes = comment.get('like_count', 0)
            sub_count = comment.get('sub_comment_count', 0)
            
            lines.append(f"[{j}] {user}: {content} (👍{likes})")
            
            # 子评论
            if comment_id in sub_comments:
                for sub in sub_comments[comment_id]:
                    sub_content = sub.get('content', '')
                    sub_user = sub.get('user_nickname', '匿名')
                    sub_likes = sub.get('like_count', 0)
                    lines.append(f"    └─ {sub_user}: {sub_content} (👍{sub_likes})")
        
        lines.append("")
    
    return "\n".join(lines)


def main():
    print("=" * 60, flush=True)
    print("抱枕评论整体分析工具 - Markdown 报告版", flush=True)
    print(f"模型: {GEMINI_MODEL}", flush=True)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print("=" * 60, flush=True)
    
    # 1. 加载数据
    print("\n📂 加载数据...", flush=True)
    data = load_all_data()
    stats = data['stats']
    print(f"   帖子: {stats['total_posts']} 个", flush=True)
    print(f"   主评论: {stats['total_main_comments']} 条", flush=True)
    print(f"   子评论: {stats['total_sub_comments']} 条", flush=True)
    print(f"   总计: {stats['total_comments']} 条", flush=True)
    
    # 2. 格式化数据
    print("\n📝 格式化数据...", flush=True)
    formatted_data = format_all_data_for_llm(data)
    print(f"   数据长度: {len(formatted_data):,} 字符", flush=True)
    print(f"   估算 Token: {int(len(formatted_data) * 1.5):,}", flush=True)
    
    # 3. 加载 Prompt
    print("\n📄 加载 Markdown 输出 Prompt...", flush=True)
    prompt = load_prompt()
    print(f"   Prompt 长度: {len(prompt):,} 字符", flush=True)
    
    # 4. 构建完整输入
    full_input = f"{prompt}\n\n{formatted_data}"
    print(f"\n📊 总输入长度: {len(full_input):,} 字符", flush=True)
    print(f"   估算 Token: {int(len(full_input) * 1.5):,}", flush=True)
    
    # 5. 初始化客户端
    print("\n🔌 初始化 Gemini 客户端...", flush=True)
    api_key = load_env()
    client = genai.Client(api_key=api_key)
    
    # 6. 调用 API（不指定 response_mime_type，让模型直接输出 Markdown）
    print(f"\n🤖 调用 Gemini {GEMINI_MODEL}...", flush=True)
    print("   (这可能需要 1-2 分钟，请耐心等待)", flush=True)
    
    start_time = time.time()
    
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=full_input,
            config=types.GenerateContentConfig(
                temperature=TEMPERATURE
                # 不指定 response_mime_type，让模型自由输出 Markdown
            )
        )
        
        elapsed = time.time() - start_time
        print(f"   ✅ 响应完成，耗时: {elapsed:.1f} 秒", flush=True)
        
        result_text = response.text
        print(f"   输出长度: {len(result_text):,} 字符", flush=True)
        
        # 7. 保存结果为 Markdown 文件
        output_dir = Path(__file__).parent / 'output'
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f"pillow_analysis_report_B_{timestamp}.md"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result_text)
        
        print(f"\n💾 报告已保存: {output_file}", flush=True)
        
        # 8. 打印报告开头预览
        print(f"\n{'='*60}", flush=True)
        print("📊 报告预览（前 1000 字符）", flush=True)
        print(f"{'='*60}", flush=True)
        print(result_text[:1000], flush=True)
        if len(result_text) > 1000:
            print("\n... (更多内容请查看完整报告)", flush=True)
        
        print(f"\n{'='*60}", flush=True)
        print("✅ 分析完成！", flush=True)
        print(f"   完整报告请查看: {output_file}", flush=True)
        print(f"{'='*60}", flush=True)
        
    except Exception as e:
        print(f"\n❌ 分析失败: {e}", flush=True)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
