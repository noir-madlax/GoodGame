# 小红书评论抓取工具

使用 TikHub API v2 接口获取小红书笔记的所有评论（包括子评论）并导出为 CSV 文件。

## 🚀 快速开始

### 1. 创建虚拟环境
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或者在Windows上: venv\Scripts\activate
```

### 2. 安装依赖
```bash
pip install tikhub
```

### 3. 配置API密钥
在 `config.py` 文件中填入你的 TikHub API 密钥（已配置）

### 4. 运行脚本
```bash
python xiaohongshu_script.py
```

## 📋 使用说明

1. 运行脚本后，会提示输入小红书笔记ID
2. 脚本会自动获取该笔记的所有评论和子评论
3. 评论数据会自动保存到 `exports/` 目录下的CSV文件中

## 📊 导出数据格式

CSV文件包含以下字段：
- 评论ID
- 评论类型（主评论/子评论）
- 父评论ID
- 用户ID
- 用户昵称
- 评论内容
- 点赞数
- 评论时间
- 评论时间戳
- IP属地
- 是否作者
- 用户头像

## 🔧 功能特性

- ✅ 使用 TikHub API v2 接口
- ✅ 自动分页获取所有评论
- ✅ 递归获取所有子评论
- ✅ 自动导出为CSV格式
- ✅ 错误处理和重试机制
- ✅ 请求速率限制

## 📁 文件结构

```
tikhub/
├── xiaohongshu_script.py  # 主脚本
├── config.py              # 配置文件
├── requirements.txt       # 依赖文件
├── README.md             # 说明文档
└── exports/              # 导出目录（自动创建）
```

## ⚠️ 注意事项

- 请确保你的 TikHub API 密钥有效且有足够的额度
- 脚本会自动添加请求延迟以避免触发限流
- 大量评论的笔记可能需要较长时间处理 