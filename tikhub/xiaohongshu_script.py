# -*- coding: utf-8 -*-
"""
小红书数据获取脚本
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


class XiaohongshuScript:
    """小红书数据获取脚本"""
    
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
    
    async def get_user_info(self, user_id: str):
        """
        获取用户信息
        
        Args:
            user_id: 用户ID
        """
        try:
            # 使用 XiaohongshuWeb 获取用户信息
            user_info = await self.client.XiaohongshuWeb.get_user_info(user_id=user_id)
            print(f"用户信息: {user_info}")
            return user_info
        except Exception as e:
            print(f"获取用户信息失败: {e}")
            return None
    
    async def get_user_notes(self, user_id: str, cursor: str = ""):
        """
        获取用户笔记
        
        Args:
            user_id: 用户ID
            cursor: 游标，用于分页
        """
        try:
            notes = await self.client.XiaohongshuWeb.get_user_notes(
                user_id=user_id, 
                cursor=cursor
            )
            print(f"用户笔记: {notes}")
            return notes
        except Exception as e:
            print(f"获取用户笔记失败: {e}")
            return None
    
    async def get_note_detail(self, note_id: str):
        """
        获取笔记详情
        
        Args:
            note_id: 笔记ID
        """
        try:
            note_detail = await self.client.XiaohongshuWeb.get_note_detail(note_id=note_id)
            print(f"笔记详情: {note_detail}")
            return note_detail
        except Exception as e:
            print(f"获取笔记详情失败: {e}")
            return None
    
    async def search_notes(self, keyword: str, page: int = 1):
        """
        搜索笔记
        
        Args:
            keyword: 搜索关键词
            page: 页码
        """
        try:
            search_results = await self.client.XiaohongshuWeb.get_note_by_keyword(
                keyword=keyword,
                page=page
            )
            print(f"搜索结果: {search_results}")
            return search_results
        except Exception as e:
            print(f"搜索笔记失败: {e}")
            return None
    
    async def get_note_comments(self, note_id: str, cursor: str = ""):
        """
        获取笔记评论 - 使用v2接口
        
        Args:
            note_id: 笔记ID
            cursor: 游标，用于分页
        """
        try:
            # 直接调用API端点，因为SDK可能没有包含v2接口
            endpoint = f"/api/v1/xiaohongshu/web/get_note_comments_v2?note_id={note_id}&cursor={cursor}"
            full_url = f"{self.client.client.base_url}{endpoint}"
            
            # 打印请求信息
            print(f"请求的 URL: {full_url}")
            print(f"bodyJson: {{'note_id': '{note_id}', 'cursor': '{cursor}'}}")
            
            comments = await self.client.client.fetch_get_json(endpoint)
            
            # 打印返回信息
            print(f"请求的 URL: {full_url}")
            print(f"返回的 response: {json.dumps(comments, ensure_ascii=False, indent=2)}")
            
            if comments and comments.get('data') and comments['data'].get('data'):
                comment_count = len(comments['data']['data'].get('comments', []))
                print(f"获取到 {comment_count} 条评论")
            return comments
        except Exception as e:
            print(f"获取笔记评论失败: {e}")
            return None
    
    async def get_all_comments(self, note_id: str):
        """
        获取笔记的所有评论（包括子评论）- 使用v2接口
        
        Args:
            note_id: 笔记ID
            
        Returns:
            所有评论的列表
        """
        all_comments = []
        cursor = ""
        page = 1
        
        print(f"开始获取笔记 {note_id} 的所有评论...")
        
        while True:
            print(f"正在获取第 {page} 页评论...")
            
            # 获取当前页评论
            result = await self.get_note_comments(note_id, cursor)
            if not result or not result.get('data') or not result['data'].get('data'):
                break
            
            data = result['data']['data']
            comments = data.get('comments', [])
            
            if not comments:
                break
            
            # 处理每条评论
            for comment in comments:
                # 添加主评论
                comment_info = self.extract_comment_info(comment, note_id, is_sub_comment=False)
                all_comments.append(comment_info)
                
                # 获取子评论（如果有的话）
                await self.get_comment_replies(note_id, comment.get('id'), all_comments)
            
            # 检查是否有下一页
            if not data.get('has_more', False):
                break
            
            cursor = data.get('cursor', "")
            page += 1
            
            # 添加延迟避免请求过快
            await asyncio.sleep(1)
        
        print(f"总共获取到 {len(all_comments)} 条评论（包括子评论）")
        return all_comments
    
    async def get_comment_replies(self, note_id: str, comment_id: str, all_comments: list):
        """
        获取评论回复 - 使用v2接口
        
        Args:
            note_id: 笔记ID
            comment_id: 主评论ID
            all_comments: 存储所有评论的列表
        """
        cursor = ""
        page = 1
        previous_cursor = None
        max_pages = 10  # 设置最大页数限制，防止死循环
        
        while page <= max_pages:
            try:
                # 使用v2接口获取评论回复
                endpoint = f"/api/v1/xiaohongshu/web/get_note_comment_replies_v2?note_id={note_id}&comment_id={comment_id}&cursor={cursor}"
                full_url = f"{self.client.client.base_url}{endpoint}"
                
                # 打印请求信息
                print(f"请求第 {page} 页回复评论")
                print(f"请求的 URL: {full_url}")
                print(f"bodyJson: {{'note_id': '{note_id}', 'comment_id': '{comment_id}', 'cursor': '{cursor}'}}")
                
                replies_result = await self.client.client.fetch_get_json(endpoint)
                
                # 打印返回信息
                print(f"返回的 response: {json.dumps(replies_result, ensure_ascii=False, indent=2)}")
                
                if not replies_result or not replies_result.get('data') or not replies_result['data'].get('data'):
                    print("没有更多回复数据")
                    break
                
                data = replies_result['data']['data']
                replies = data.get('comments', [])
                
                if not replies:
                    print("当前页没有回复评论")
                    break
                
                print(f"获取到 {len(replies)} 条回复评论")
                
                for reply in replies:
                    reply_info = self.extract_comment_info(reply, note_id, is_sub_comment=True, parent_id=comment_id)
                    all_comments.append(reply_info)
                
                # 检查是否有更多回复
                has_more = data.get('has_more', False)
                new_cursor = data.get('cursor', "")
                
                print(f"has_more: {has_more}, new_cursor: {new_cursor}")
                
                # 如果没有更多数据，退出循环
                if not has_more:
                    print("已获取所有回复评论")
                    break
                
                # 如果cursor没有变化，说明可能陷入死循环，退出
                if new_cursor == previous_cursor:
                    print("检测到cursor重复，退出循环防止死循环")
                    break
                
                # 如果new_cursor为空，退出循环
                if not new_cursor:
                    print("新cursor为空，退出循环")
                    break
                
                previous_cursor = cursor
                cursor = new_cursor
                page += 1
                
                # 添加延迟
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"获取评论回复失败: {e}")
                break
        
        if page > max_pages:
            print(f"已达到最大页数限制 ({max_pages})，停止获取")
        
        print(f"评论 {comment_id} 的回复获取完成，共 {page-1} 页")
    
    def extract_comment_info(self, comment: dict, note_id: str, is_sub_comment: bool = False, parent_id: str = None):
        """
        提取评论信息
        
        Args:
            comment: 评论数据
            note_id: 笔记ID
            is_sub_comment: 是否为子评论
            parent_id: 父评论ID（仅子评论有）
            
        Returns:
            格式化的评论信息
        """
        user_info = comment.get('user', {})
        show_tags = comment.get('show_tags', [])
        
        return {
            '笔记ID': note_id,
            '评论ID': comment.get('id', ''),
            '评论类型': '子评论' if is_sub_comment else '主评论',
            '父评论ID': parent_id if is_sub_comment else '',
            '用户ID': user_info.get('userid', ''),
            '用户昵称': user_info.get('nickname', ''),
            '用户红薯号': user_info.get('red_id', ''),
            '评论内容': comment.get('content', ''),
            '点赞数': comment.get('like_count', 0),
            '评论时间戳': comment.get('time', ''),
            '评论分数': comment.get('score', 0),
            '是否作者': 'is_author' in show_tags,
            '用户头像': user_info.get('images', ''),
            '是否隐藏': comment.get('hidden', False),
            '评论状态': comment.get('status', 0),
            '语言代码': comment.get('text_language_code', ''),
        }
    
    def save_comments_to_csv(self, comments: list, note_id: str):
        """
        保存评论到CSV文件
        
        Args:
            comments: 评论列表
            note_id: 笔记ID
        """
        if not comments:
            print("没有评论数据可保存")
            return
        
        # 创建文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"xiaohongshu_comments_{note_id}_{timestamp}.csv"
        
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
    
    async def export_note_comments(self, note_id: str):
        """
        导出笔记评论到CSV
        
        Args:
            note_id: 笔记ID
        """
        print(f"开始导出笔记 {note_id} 的评论...")
        
        # 获取所有评论
        all_comments = await self.get_all_comments(note_id)
        
        if all_comments:
            # 保存到CSV
            self.save_comments_to_csv(all_comments, note_id)
        else:
            print("没有获取到评论数据")


def main():
    """主函数"""
    script = XiaohongshuScript()
    
    # 获取用户输入的note_id
    note_id = input("请输入小红书笔记ID: ").strip()
    
    if not note_id:
        print("笔记ID不能为空！")
        return
    
    async def export_comments():
        await script.export_note_comments(note_id)
    
    # 运行导出评论功能
    asyncio.run(export_comments())


if __name__ == "__main__":
    main() 