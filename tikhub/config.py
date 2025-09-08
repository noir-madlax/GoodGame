# -*- coding: utf-8 -*-
"""
配置文件
"""

# TikHub API配置
TIKHUB_API_KEY = "44wGVlZTxXwGkXQljmuJpycPy0AHsqGF6JQj3gD3ukhczVZVS/RN+xm6Lg=="  # 在这里填入你的TikHub API密钥
TIKHUB_BASE_URL = "https://api.tikhub.io"

# 请求配置
REQUEST_TIMEOUT = 30  # 请求超时时间(秒)
MAX_RETRIES = 3  # 最大重试次数

# 小红书相关配置
XIAOHONGSHU_CONFIG = {
    "default_limit": 20,  # 默认获取数量
    "max_limit": 100,     # 最大获取数量
} 