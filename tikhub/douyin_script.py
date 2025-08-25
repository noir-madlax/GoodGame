# -*- coding: utf-8 -*-
"""
抖音数据获取脚本
使用 TikHub 官方 Python SDK
文档: https://github.com/TikHub/TikHub-API-Python-SDK
"""

import asyncio
import csv
import json
import os
from datetime import datetime
from tikhub import Client
from config import TIKHUB_API_KEY


class DouyinScript:
    """抖音数据获取脚本"""
    
    def __init__(self):
        """初始化客户端"""
        self.client = Client(
            base_url="https://api.tikhub.io", 
            api_key=TIKHUB_API_KEY,
            max_retries=3,
            max_connections=50,
            timeout=60,
            max_tasks=50
        )
    
    async def get_video_info(self, video_id: str):
        """
        获取视频信息
        
        Args:
            video_id: 视频ID
        """
        try:
            # 使用 DouyinWeb 获取视频信息
            video_info = await self.client.DouyinWeb.fetch_one_video(aweme_id=video_id)
            print(f"视频信息: {video_info}")
            return video_info
        except Exception as e:
            print(f"获取视频信息失败: {e}")
            return None
    
    async def get_video_comments(self, video_id: str, cursor: int = 0, count: int = 20):
        """
        获取视频评论
        
        Args:
            video_id: 视频ID
            cursor: 游标，用于分页
            count: 每页评论数量
        """
        try:
            print(f"正在请求评论，参数: aweme_id={video_id}, cursor={cursor}, count={count}")
            comments = await self.client.DouyinWeb.fetch_video_comments(
                aweme_id=video_id, 
                cursor=cursor,
                count=count
            )
            print(f"视频评论: {comments}")
            
            # 检查API响应状态
            if comments and comments.get('code') != 200:
                print(f"API返回错误: {comments}")
                return None
                
            return comments
        except Exception as e:
            print(f"获取视频评论失败: {e}")
            return None
    
    async def get_comment_replies(self, video_id: str, comment_id: str, cursor: int = 0, count: int = 20):
        """
        获取评论回复
        
        Args:
            video_id: 视频ID
            comment_id: 评论ID
            cursor: 游标，用于分页
            count: 每页回复数量
        """
        try:
            replies = await self.client.DouyinWeb.fetch_video_comments_reply(
                item_id=video_id,
                comment_id=comment_id,
                cursor=cursor,
                count=count
            )
            print(f"评论回复: {replies}")
            return replies
        except Exception as e:
            print(f"获取评论回复失败: {e}")
            return None
    
    async def get_all_comments(self, video_id: str):
        """
        获取视频的所有评论（包括子评论）
        
        Args:
            video_id: 视频ID
            
        Returns:
            所有评论的列表
        """
        all_comments = []
        cursor = 0
        page = 1
        
        print(f"开始获取视频 {video_id} 的所有评论...")
        
        while True:
            print(f"正在获取第 {page} 页评论...")
            
            # 获取当前页评论
            result = await self.get_video_comments(video_id, cursor)
            if not result or not result.get('data'):
                break
            
            data = result['data']
            comments = data.get('comments', [])
            
            # 处理 comments 为 None 的情况
            if comments is None:
                comments = []
            
            if not comments:
                break
            
            # 处理每条评论
            for comment in comments:
                # 添加主评论
                comment_info = self.extract_comment_info(comment, video_id, is_sub_comment=False)
                all_comments.append(comment_info)
                
                # 获取子评论（如果有的话）
                reply_count = comment.get('reply_comment_total', 0)
                if reply_count > 0:
                    await self.get_all_comment_replies(video_id, comment.get('cid'), all_comments)
            
            # 检查是否有下一页
            has_more = data.get('has_more', False)
            if not has_more:
                break
            
            cursor = data.get('cursor', 0)
            page += 1
            
            # 添加延迟避免请求过快
            await asyncio.sleep(1)
        
        print(f"总共获取到 {len(all_comments)} 条评论（包括子评论）")
        return all_comments
    
    async def get_all_comment_replies(self, video_id: str, comment_id: str, all_comments: list):
        """
        获取评论的所有回复
        
        Args:
            video_id: 视频ID
            comment_id: 主评论ID
            all_comments: 存储所有评论的列表
        """
        cursor = 0
        page = 1
        max_pages = 10  # 设置最大页数限制，防止死循环
        
        while page <= max_pages:
            try:
                print(f"正在获取评论 {comment_id} 的第 {page} 页回复...")
                
                replies_result = await self.get_comment_replies(video_id, comment_id, cursor)
                
                if not replies_result or not replies_result.get('data'):
                    print("没有更多回复数据")
                    break
                
                data = replies_result['data']
                replies = data.get('comments', [])
                
                # 处理 replies 为 None 的情况
                if replies is None:
                    replies = []
                
                if not replies:
                    print("当前页没有回复评论")
                    break
                
                print(f"获取到 {len(replies)} 条回复评论")
                
                for reply in replies:
                    reply_info = self.extract_comment_info(reply, video_id, is_sub_comment=True, parent_id=comment_id)
                    all_comments.append(reply_info)
                
                # 检查是否有更多回复
                has_more = data.get('has_more', False)
                if not has_more:
                    print("已获取所有回复评论")
                    break
                
                cursor = data.get('cursor', 0)
                page += 1
                
                # 添加延迟
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"获取评论回复失败: {e}")
                break
        
        if page > max_pages:
            print(f"已达到最大页数限制 ({max_pages})，停止获取")
        
        print(f"评论 {comment_id} 的回复获取完成，共 {page-1} 页")
    
    def extract_comment_info(self, comment: dict, video_id: str, is_sub_comment: bool = False, parent_id: str = None):
        """
        提取评论信息
        
        Args:
            comment: 评论数据
            video_id: 视频ID
            is_sub_comment: 是否为子评论
            parent_id: 父评论ID（仅子评论有）
            
        Returns:
            格式化的评论信息
        """
        user_info = comment.get('user', {})
        
        return {
            '视频ID': video_id,
            '评论ID': comment.get('cid', ''),
            '评论类型': '子评论' if is_sub_comment else '主评论',
            '父评论ID': parent_id if is_sub_comment else '',
            '用户ID': user_info.get('uid', ''),
            '用户昵称': user_info.get('nickname', ''),
            '用户抖音号': user_info.get('unique_id', ''),
            '评论内容': comment.get('text', ''),
            '点赞数': comment.get('digg_count', 0),
            '回复数': comment.get('reply_comment_total', 0),
            '评论时间戳': comment.get('create_time', ''),
            '评论时间': self.format_timestamp(comment.get('create_time', 0)),
            '用户头像': user_info.get('avatar_thumb', {}).get('url_list', [''])[0] if user_info.get('avatar_thumb') else '',
            '用户认证': user_info.get('verification_type', 0),
            '用户粉丝数': user_info.get('follower_count', 0),
            '用户关注数': user_info.get('following_count', 0),
            '用户获赞数': user_info.get('total_favorited', 0),
            'IP属地': comment.get('ip_label', ''),
        }
    
    def format_timestamp(self, timestamp):
        """
        格式化时间戳
        
        Args:
            timestamp: 时间戳
            
        Returns:
            格式化的时间字符串
        """
        try:
            if timestamp:
                return datetime.fromtimestamp(int(timestamp)).strftime('%Y-%m-%d %H:%M:%S')
            return ''
        except:
            return str(timestamp)
    
    def save_comments_to_csv(self, comments: list, video_id: str):
        """
        保存评论到CSV文件
        
        Args:
            comments: 评论列表
            video_id: 视频ID
        """
        if not comments:
            print("没有评论数据可保存")
            return
        
        # 创建文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"douyin_comments_{video_id}_{timestamp}.csv"
        
        # 确保目录存在
        os.makedirs('exports', exist_ok=True)
        filepath = os.path.join('exports', filename)
        
        # 写入CSV文件
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                if comments:
                    fieldnames = comments[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    
                    writer.writeheader()
                    writer.writerows(comments)
                    
                    print(f"评论数据已保存到: {filepath}")
                    print(f"共保存 {len(comments)} 条评论")
        except Exception as e:
            print(f"保存CSV文件失败: {e}")
    
    async def export_video_comments(self, video_id: str):
        """
        导出视频评论到CSV
        
        Args:
            video_id: 视频ID
        """
        print(f"开始导出视频 {video_id} 的评论...")
        
        # 先获取视频信息
        video_info = await self.get_video_info(video_id)
        if video_info:
            print(f"视频标题: {video_info.get('data', {}).get('desc', '未知')}")
        
        # 获取所有评论
        all_comments = await self.get_all_comments(video_id)
        
        if all_comments:
            # 保存到CSV
            self.save_comments_to_csv(all_comments, video_id)
        else:
            print("没有获取到评论数据")


def main():
    """主函数"""
    script = DouyinScript()
    
    print("抖音评论获取工具")
    print("=" * 50)
    print("支持的视频ID格式:")
    print("1. 纯数字ID: 7318104042671967527")
    print("2. 从抖音链接中提取的ID")
    print("注意: 如果遇到400错误，可能是视频不存在或无权限访问")
    print("=" * 50)
    
    # 获取用户输入的video_id
    video_id = input("请输入抖音视频ID: ").strip()
    
    if not video_id:
        print("视频ID不能为空！")
        return
    
    # 简单验证视频ID格式（应该是数字）
    if not video_id.isdigit():
        print("警告: 视频ID应该是纯数字格式")
        confirm = input("是否继续？(y/n): ").strip().lower()
        if confirm != 'y':
            return
    
    async def export_comments():
        await script.export_video_comments(video_id)
    
    # 运行导出评论功能
    asyncio.run(export_comments())


if __name__ == "__main__":
    main() 