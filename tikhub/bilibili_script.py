# -*- coding: utf-8 -*-
"""
B站视频数据获取脚本
使用 TikHub 官方 Python SDK V2
文档: https://github.com/TikHub/TikHub-API-Python-SDK-V2
"""

import csv
import json
import os
import time
from datetime import datetime
import tikhub_sdk_v2
from tikhub_sdk_v2.rest import ApiException
from config import TIKHUB_API_KEY


class BilibiliScript:
    """B站视频数据获取脚本"""
    
    def __init__(self):
        """初始化客户端"""
        # 配置SDK V2
        self.configuration = tikhub_sdk_v2.Configuration(
            host="https://api.tikhub.io"
        )
        self.configuration.access_token = f'Bearer {TIKHUB_API_KEY}'
        
        self.api_client = tikhub_sdk_v2.ApiClient(self.configuration)
        self.bilibili_api = tikhub_sdk_v2.BilibiliWebAPIApi(self.api_client)
    
    def get_video_detail(self, video_id: str):
        """
        获取B站视频详情
        
        Args:
            video_id: 视频ID (可以是BV号或AV号)
        """
        try:
            print(f"\n[请求前] API: BilibiliWebAPIApi.fetch_one_video")
            print(f"[请求前] 参数: video_id={video_id}")
            
            # 使用 BilibiliWebAPIApi 获取视频详情
            if video_id.startswith('BV'):
                response = self.bilibili_api.fetch_one_video_api_v1_bilibili_web_fetch_one_video_get(
                    bv_id=video_id,
                    _preload_content=False
                )
            elif video_id.startswith('av') or video_id.isdigit():
                # 处理AV号
                aid = video_id.replace('av', '') if video_id.startswith('av') else video_id
                response = self.bilibili_api.fetch_one_video_api_v1_bilibili_web_fetch_one_video_get(
                    aid=aid,
                    _preload_content=False
                )
            else:
                print(f"无法识别的视频ID格式: {video_id}")
                return None
                
            # 解析响应
            response_data = response.json() if hasattr(response, 'json') else response
            
            print(f"\n[请求后] API: BilibiliWebAPIApi.fetch_one_video")
            print(f"[请求后] 完整响应: {json.dumps(response_data, ensure_ascii=False, indent=2)}")
            
            return response_data
            
        except ApiException as e:
            print(f"API异常: {e}")
            return None
        except Exception as e:
            print(f"获取视频详情失败: {str(e)}")
            return None

    def get_video_comments(self, video_id: str, page: int = 1, page_size: int = 20):
        """
        获取B站视频评论
        
        Args:
            video_id: 视频ID (可以是BV号或AV号)
            page: 页码，从1开始
            page_size: 每页数量
        """
        try:
            print(f"\n[请求前] API: BilibiliWebAPIApi.fetch_video_comments")
            print(f"[请求前] 参数: video_id={video_id}, pn={page}, ps={page_size}")
            
            # 使用 BilibiliWebAPIApi 获取视频评论
            if video_id.startswith('BV'):
                response = self.bilibili_api.fetch_collect_folders_api_v1_bilibili_web_fetch_video_comments_get(
                    bv_id=video_id,
                    pn=page,
                    _preload_content=False
                )
            elif video_id.startswith('av') or video_id.isdigit():
                # 处理AV号
                aid = video_id.replace('av', '') if video_id.startswith('av') else video_id
                response = self.bilibili_api.fetch_collect_folders_api_v1_bilibili_web_fetch_video_comments_get(
                    aid=aid,
                    pn=page,
                    _preload_content=False
                )
            else:
                print(f"无法识别的视频ID格式: {video_id}")
                return None
            
            # 解析响应
            response_data = response.json() if hasattr(response, 'json') else response
            
            print(f"\n[请求后] API: BilibiliWebAPIApi.fetch_video_comments")
            print(f"[请求后] 完整响应: {json.dumps(response_data, ensure_ascii=False, indent=2)}")
            
            return response_data
            
        except ApiException as e:
            print(f"API异常: {e}")
            return None
        except Exception as e:
            print(f"获取评论失败: {str(e)}")
            return None

    def get_comment_replies(self, video_id: str, comment_id: str, page: int = 1, page_size: int = 20):
        """
        获取评论回复
        
        Args:
            video_id: 视频ID
            comment_id: 主评论ID
            page: 页码，从1开始
            page_size: 每页数量
        """
        try:
            print(f"\n[请求前] API: BilibiliWebAPIApi.fetch_comment_reply")
            print(f"[请求前] 参数: video_id={video_id}, rpid={comment_id}, pn={page}, ps={page_size}")
            
            # 使用 BilibiliWebAPIApi 获取评论回复
            if video_id.startswith('BV'):
                response = self.bilibili_api.fetch_collect_folders_api_v1_bilibili_web_fetch_comment_reply_get(
                    bv_id=video_id,
                    rpid=comment_id,
                    pn=page,
                    _preload_content=False
                )
            elif video_id.startswith('av') or video_id.isdigit():
                # 处理AV号
                aid = video_id.replace('av', '') if video_id.startswith('av') else video_id
                response = self.bilibili_api.fetch_collect_folders_api_v1_bilibili_web_fetch_comment_reply_get(
                    aid=aid,
                    rpid=comment_id,
                    pn=page,
                    _preload_content=False
                )
            else:
                print(f"无法识别的视频ID格式: {video_id}")
                return None
                
            # 解析响应
            response_data = response.json() if hasattr(response, 'json') else response
            
            print(f"\n[请求后] API: BilibiliWebAPIApi.fetch_comment_reply")
            print(f"[请求后] 完整响应: {json.dumps(response_data, ensure_ascii=False, indent=2)}")
            
            return response_data
            
        except ApiException as e:
            print(f"API异常: {e}")
            return None
        except Exception as e:
            print(f"获取评论回复失败: {str(e)}")
            return None

    def get_all_comments(self, video_id: str):
        """
        获取视频的所有评论（包括子评论）
        
        Args:
            video_id: 视频ID
            
        Returns:
            所有评论的列表
        """
        all_comments = []
        page = 1
        max_pages = 50  # 设置最大页数限制，防止死循环
        
        print(f"开始获取B站视频 {video_id} 的所有评论...")
        
        while page <= max_pages:
            print(f"正在获取第 {page} 页评论...")
            
            # 获取当前页评论
            result = self.get_video_comments(video_id, page, 20)
            if not result or result.get('code') != 200:
                print(f"获取评论失败或到达最后一页")
                break
            
            data = result.get('data', {}).get('data', {})
            comments = data.get('replies', [])
            
            if not comments:
                print("当前页没有评论")
                break
            
            print(f"获取到 {len(comments)} 条评论")
            
            # 处理每条评论
            for comment in comments:
                # 添加主评论
                comment_info = self.extract_comment_info(comment, video_id, is_sub_comment=False)
                all_comments.append(comment_info)
                
                # 获取子评论（如果有的话）
                comment_id = str(comment.get('rpid', ''))
                if comment.get('rcount', 0) > 0 and comment_id:
                    self.get_comment_sub_replies(video_id, comment_id, all_comments)
            
            # 检查是否有下一页
            page_info = data.get('page', {})
            total_pages = page_info.get('count', 0) // 20 + 1
            
            if page >= total_pages:
                print("已到达最后一页")
                break
            
            page += 1
            
            # 添加延迟避免请求过快
            time.sleep(1)
        
        print(f"总共获取到 {len(all_comments)} 条评论（包括子评论）")
        return all_comments

    def get_comment_sub_replies(self, video_id: str, comment_id: str, all_comments: list):
        """
        获取评论的子回复
        
        Args:
            video_id: 视频ID
            comment_id: 主评论ID
            all_comments: 存储所有评论的列表
        """
        page = 1
        max_pages = 10  # 设置最大页数限制，防止死循环
        
        while page <= max_pages:
            try:
                print(f"获取评论 {comment_id} 的第 {page} 页回复...")
                
                replies_result = self.get_comment_replies(video_id, comment_id, page, 20)
                
                if not replies_result or replies_result.get('code') != 200:
                    print(f"获取回复失败或到达最后一页")
                    break
                
                data = replies_result.get('data', {}).get('data', {})
                replies = data.get('replies', [])
                
                if not replies:
                    print("当前页没有回复")
                    break
                
                print(f"获取到 {len(replies)} 条回复")
                
                # 处理每条回复
                for reply in replies:
                    reply_info = self.extract_comment_info(reply, video_id, is_sub_comment=True, parent_id=comment_id)
                    all_comments.append(reply_info)
                
                # 检查是否有下一页
                page_info = data.get('page', {})
                total_pages = page_info.get('count', 0) // 20 + 1
                
                if page >= total_pages:
                    print("回复已到达最后一页")
                    break
                
                page += 1
                
                # 添加延迟避免请求过快
                time.sleep(0.5)
                
            except Exception as e:
                print(f"获取子评论失败: {e}")
                break

    def extract_comment_info(self, comment: dict, video_id: str, is_sub_comment: bool = False, parent_id: str = None):
        """
        提取评论信息
        
        Args:
            comment: 评论数据
            video_id: 视频ID
            is_sub_comment: 是否为子评论
            parent_id: 父评论ID（如果是子评论）
        """
        member = comment.get('member', {})
        
        # 格式化时间
        timestamp = comment.get('ctime', 0)
        formatted_time = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S') if timestamp else ''
        
        return {
            '视频ID': video_id,
            '评论ID': str(comment.get('rpid', '')),
            '评论类型': '子评论' if is_sub_comment else '主评论',
            '父评论ID': parent_id if is_sub_comment else '',
            '用户ID': str(member.get('mid', '')),
            '用户昵称': member.get('uname', ''),
            '用户等级': member.get('level_info', {}).get('current_level', 0),
            'VIP类型': member.get('vip', {}).get('vipType', 0),
            '认证状态': member.get('official_verify', {}).get('type', -1),
            '评论内容': comment.get('content', {}).get('message', ''),
            '点赞数': comment.get('like', 0),
            '评论时间戳': timestamp,
            '评论时间': formatted_time,
            '楼层': comment.get('floor', 0),
            '回复数': comment.get('rcount', 0),
            '用户头像': member.get('avatar', ''),
            '用户性别': member.get('sex', ''),
            '设备信息': comment.get('reply_control', {}).get('location', ''),
        }

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
        
        # 创建exports目录
        os.makedirs('exports', exist_ok=True)
        
        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"exports/bilibili_comments_{video_id}_{timestamp}.csv"
        
        # 写入CSV文件
        with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            if comments:
                writer = csv.DictWriter(csvfile, fieldnames=comments[0].keys())
                writer.writeheader()
                writer.writerows(comments)
        
        print(f"评论数据已保存到: {filename}")
        print(f"总共保存了 {len(comments)} 条评论")

    def export_video_comments(self, video_id: str):
        """
        导出视频评论到CSV
        
        Args:
            video_id: 视频ID
        """
        print(f"开始导出B站视频 {video_id} 的评论...")
        
        # 获取所有评论
        comments = self.get_all_comments(video_id)
        
        if comments:
            # 保存到CSV
            self.save_comments_to_csv(comments, video_id)
            print("✅ 评论导出完成!")
        else:
            print("❌ 没有获取到评论数据")


def main():
    """主函数"""
    # 创建脚本实例
    script = BilibiliScript()
    
    # 获取用户输入的视频ID
    video_id = input("请输入B站视频ID（BV号或AV号）: ").strip()
    
    if not video_id:
        print("❌ 请输入有效的视频ID")
        return
    
    # 导出评论
    script.export_video_comments(video_id)


if __name__ == "__main__":
    main() 