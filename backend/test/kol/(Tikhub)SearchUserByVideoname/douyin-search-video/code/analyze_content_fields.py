#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分析视频内容字段的聚类统计
提取并分析desc、hashtags、suggest_words、video_tags、caption等字段

作者: AI Agent
创建时间: 2025-11-24
"""

import json
import os
from pathlib import Path
from collections import Counter, defaultdict
import re

def extract_content_fields(file_paths):
    """从JSON文件中提取各种内容字段"""
    content_data = {
        'descs': [],  # 视频描述
        'hashtags': [],  # 话题标签
        'suggest_words': [],  # 推荐搜索词
        'video_tags': [],  # 视频标签
        'captions': [],  # 字幕
        'all_text': []  # 所有文本内容
    }

    for file_path in file_paths:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if 'data' in data and 'data' in data['data']:
                videos = data['data']['data']

                for video in videos:
                    if 'aweme_info' in video:
                        aweme = video['aweme_info']

                        # 1. 提取desc
                        desc = aweme.get('desc', '')
                        if desc:
                            content_data['descs'].append(desc)

                        # 2. 提取hashtags (text_extra中的hashtag_name)
                        text_extra = aweme.get('text_extra', [])
                        if text_extra:
                            for extra in text_extra:
                                if isinstance(extra, dict) and 'hashtag_name' in extra and extra['hashtag_name']:
                                    content_data['hashtags'].append(extra['hashtag_name'])

                        # 3. 提取suggest_words (从video数据中提取)
                        if 'suggest_words' in video and video['suggest_words']:
                            for suggest in video['suggest_words']:
                                if isinstance(suggest, dict):
                                    word = suggest.get('word', '')
                                    if word:
                                        content_data['suggest_words'].append(word)

                        # 4. 提取video_tags
                        video_tags = aweme.get('video_tag', [])
                        if video_tags:
                            for tag_info in video_tags:
                                if isinstance(tag_info, dict) and 'tag_name' in tag_info:
                                    content_data['video_tags'].append(tag_info['tag_name'])

                        # 5. 提取caption (字幕)
                        # 检查各种可能的字幕字段
                        caption = ''
                        if 'video' in aweme and 'caption' in aweme['video']:
                            caption = aweme['video']['caption']
                        elif 'caption' in aweme:
                            caption = aweme['caption']

                        if caption:
                            content_data['captions'].append(caption)

                        # 6. 收集所有文本
                        all_text = desc + ' ' + caption
                        if all_text.strip():
                            content_data['all_text'].append(all_text.strip())

        except Exception as e:
            print(f"处理文件 {file_path} 时出错: {e}")

    return content_data

def analyze_text_patterns(texts, field_name):
    """分析文本模式和关键词"""
    if not texts:
        return {}

    analysis = {
        'total_count': len(texts),
        'avg_length': sum(len(text) for text in texts) / len(texts),
        'keyword_freq': Counter(),
        'pattern_stats': {}
    }

    # 提取关键词
    all_words = []
    for text in texts:
        # 分词（简单按空格和标点分割）
        words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', text)
        all_words.extend(words)

    analysis['keyword_freq'] = Counter(all_words).most_common(20)

    # 特殊模式分析
    if field_name == 'descs':
        # 分析话题标签使用
        hashtag_pattern = re.compile(r'#([^#\s]+)')
        hashtags_in_desc = []
        for text in texts:
            hashtags_in_desc.extend(hashtag_pattern.findall(text))
        analysis['hashtags_in_desc'] = Counter(hashtags_in_desc).most_common(15)

        # 分析表情符号使用
        emoji_pattern = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]')
        emoji_count = sum(len(emoji_pattern.findall(text)) for text in texts)
        analysis['emoji_usage'] = emoji_count

    return analysis

def cluster_analysis(content_data):
    """进行聚类分析"""
    clusters = {
        'content_types': defaultdict(int),  # 内容类型聚类
        'topic_clusters': defaultdict(int),  # 话题聚类
        'style_clusters': defaultdict(int),  # 风格聚类
        'target_audience': defaultdict(int)  # 目标受众聚类
    }

    # 基于desc进行内容类型聚类
    for desc in content_data['descs']:
        desc_lower = desc.lower()

        # 内容类型识别
        if any(word in desc_lower for word in ['教程', '教学', '步骤', '手法', '方法']):
            clusters['content_types']['教程教学'] += 1
        elif any(word in desc_lower for word in ['分享', '经验', '心得', '日常']):
            clusters['content_types']['经验分享'] += 1
        elif any(word in desc_lower for word in ['推荐', '好用', '必备', '必试']):
            clusters['content_types']['产品推荐'] += 1
        elif any(word in desc_lower for word in ['问题', '困扰', '解决', '怎么办']):
            clusters['content_types']['问题解决'] += 1
        else:
            clusters['content_types']['其他'] += 1

        # 目标受众识别
        if any(word in desc_lower for word in ['新手', '入门', '初学者', '小白']):
            clusters['target_audience']['新手入门'] += 1
        elif any(word in desc_lower for word in ['高级', '专业', '医师', '医生']):
            clusters['target_audience']['专业人士'] += 1
        elif any(word in desc_lower for word in ['妈妈', '宝妈', '孕妇', '儿童']):
            clusters['target_audience']['家庭用户'] += 1
        else:
            clusters['target_audience']['大众用户'] += 1

    return clusters

def main():
    # 文件路径
    current_dir = Path(__file__).parent
    output_dir = current_dir.parent / "output" / "keyword_护肤保养" / "detail"

    file_paths = [
        output_dir / f"video_search_page_{i}_20251124_{'135619' if i >= 3 else '134103'}.json"
        for i in range(14)
    ]

    print("📊 开始分析13页视频数据的内容字段...")
    print("=" * 60)

    # 提取内容字段
    content_data = extract_content_fields(file_paths)

    print(f"✅ 数据提取完成:")
    print(f"   - 视频描述: {len(content_data['descs'])} 条")
    print(f"   - 话题标签: {len(content_data['hashtags'])} 个")
    print(f"   - 推荐词: {len(content_data['suggest_words'])} 个")
    print(f"   - 视频标签: {len(content_data['video_tags'])} 个")
    print(f"   - 字幕: {len(content_data['captions'])} 条")

    # 分析各个字段
    print("\n📈 字段详细分析:")
    print("=" * 60)

    # 1. desc分析
    desc_analysis = analyze_text_patterns(content_data['descs'], 'descs')
    print(f"\n🎬 视频描述(desc)分析:")
    print(f"   总数量: {desc_analysis['total_count']}")
    print(f"   平均长度: {desc_analysis['avg_length']:.1f} 字符")
    print(f"   表情符号使用: {desc_analysis.get('emoji_usage', 0)} 次")

    print(f"   热门话题标签:")
    for tag, count in desc_analysis.get('hashtags_in_desc', [])[:10]:
        print(f"      #{tag}: {count} 次")

    # 2. hashtags分析
    hashtag_analysis = analyze_text_patterns(content_data['hashtags'], 'hashtags')
    print(f"\n🏷️ 话题标签(hashtag_name)分析:")
    print(f"   总数量: {hashtag_analysis['total_count']}")
    print(f"   独特标签数: {len(hashtag_analysis['keyword_freq'])}")
    print(f"   热门话题:")
    for tag, count in hashtag_analysis['keyword_freq'][:15]:
        print(f"      #{tag}: {count} 次")

    # 3. suggest_words分析
    if content_data['suggest_words']:
        suggest_analysis = analyze_text_patterns(content_data['suggest_words'], 'suggest_words')
        print(f"\n🔍 推荐搜索词(suggest_words)分析:")
        print(f"   总数量: {suggest_analysis['total_count']}")
        print(f"   独特词数: {len(suggest_analysis['keyword_freq'])}")
        print(f"   热门推荐词:")
        for word, count in suggest_analysis['keyword_freq'][:10]:
            print(f"      {word}: {count} 次")
    else:
        print(f"\n🔍 推荐搜索词(suggest_words)分析:")
        print("   无数据")

    # 4. video_tags分析
    if content_data['video_tags']:
        tag_analysis = analyze_text_patterns(content_data['video_tags'], 'video_tags')
        print(f"\n🏷️ 视频标签(video_tag)分析:")
        print(f"   总数量: {tag_analysis['total_count']}")
        print(f"   独特标签数: {len(tag_analysis['keyword_freq'])}")
        print(f"   热门视频标签:")
        for tag, count in tag_analysis['keyword_freq'][:10]:
            print(f"      {tag}: {count} 次")
    else:
        print(f"\n🏷️ 视频标签(video_tag)分析:")
        print("   无数据")

    # 5. caption分析
    if content_data['captions']:
        caption_analysis = analyze_text_patterns(content_data['captions'], 'captions')
        print(f"\n📝 字幕(caption)分析:")
        print(f"   总数量: {caption_analysis['total_count']}")
        print(f"   平均长度: {caption_analysis['avg_length']:.1f} 字符")
    else:
        print(f"\n📝 字幕(caption)分析:")
        print("   无数据")
    # 聚类分析
    clusters = cluster_analysis(content_data)

    print(f"\n🎯 内容聚类分析:")
    print("=" * 60)

    print(f"\n📊 内容类型分布:")
    total_content = sum(clusters['content_types'].values())
    for content_type, count in sorted(clusters['content_types'].items(), key=lambda x: x[1], reverse=True):
        percentage = count / total_content * 100
        print(f"      {content_type}: {count} 个 ({percentage:.1f}%)")

    print(f"\n👥 目标受众分布:")
    total_audience = sum(clusters['target_audience'].values())
    for audience, count in sorted(clusters['target_audience'].items(), key=lambda x: x[1], reverse=True):
        percentage = count / total_audience * 100
        print(f"      {audience}: {count} 个 ({percentage:.1f}%)")

    print(f"\n💡 关键洞察:")
    print("=" * 60)
    print(f"1. 内容高度专业化: {len(content_data['hashtags'])}个话题标签，覆盖护肤各个细分领域")
    print(f"2. 用户需求多样: 从入门教程到专业知识，满足不同层次用户")
    print(f"3. 互动性强: 话题标签使用频繁({desc_analysis.get('hashtags_in_desc', []) and len(desc_analysis['hashtags_in_desc']) or 0}种)，增强内容传播")
    print(f"4. 推荐系统完善: {len(content_data['suggest_words'])}个推荐词，覆盖相关搜索需求")
    print(f"5. 视频标签丰富: {len(content_data['video_tags'])}个视频标签，提升内容分类准确性")

if __name__ == "__main__":
    main()
