#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
创建数据库表并导入搜索用户数据

表设计：
1. gg_douyin_user_search - 搜索用户基础信息表
2. gg_xingtu_kol_mapping - UID到星图KOL ID的映射表
3. gg_xingtu_kol_base_info - 星图KOL基础信息表
4. gg_xingtu_kol_audience - 星图KOL受众画像表
5. gg_xingtu_kol_price - 星图KOL服务报价表
6. gg_xingtu_kol_content - 星图KOL内容定位表
7. gg_xingtu_kol_conversion - 星图KOL转化能力表
"""

import os
import json
from pathlib import Path
from datetime import datetime
from supabase import create_client, Client

# Supabase配置
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

def load_env():
    """加载环境变量"""
    from dotenv import load_dotenv
    backend_dir = Path(__file__).parent.parent.parent.parent.parent
    env_path = backend_dir / '.env'
    
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ 从 {env_path} 加载环境变量")
    
    global SUPABASE_URL, SUPABASE_KEY
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("未找到 SUPABASE_URL 或 SUPABASE_KEY")


# SQL建表语句
CREATE_TABLES_SQL = """
-- 1. 搜索用户基础信息表
CREATE TABLE IF NOT EXISTS gg_douyin_user_search (
    uid TEXT PRIMARY KEY,                    -- 用户UID（抖音数字ID）
    sec_uid TEXT,                            -- 加密用户ID
    nickname TEXT,                           -- 昵称
    unique_id TEXT,                          -- 抖音号
    gender INTEGER,                          -- 性别（0=未知，1=男，2=女）
    follower_count BIGINT,                   -- 粉丝数
    verification_type INTEGER,               -- 认证类型（0=无，1=个人，2=企业）
    avatar_url TEXT,                         -- 头像URL
    signature TEXT,                          -- 个性签名
    live_status INTEGER,                     -- 直播状态
    
    -- 扩展字段（JSON格式）
    extra_info JSONB,                        -- 其他字段（display_info, user_tags等）
    
    -- 完整原始数据
    raw_data JSONB,                          -- 完整的user_info数据
    
    -- 搜索来源信息
    search_keyword TEXT,                     -- 搜索关键词
    search_date TIMESTAMP,                   -- 搜索时间
    
    -- 元数据
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_user_search_nickname ON gg_douyin_user_search(nickname);
CREATE INDEX IF NOT EXISTS idx_user_search_follower ON gg_douyin_user_search(follower_count DESC);
CREATE INDEX IF NOT EXISTS idx_user_search_keyword ON gg_douyin_user_search(search_keyword);
CREATE INDEX IF NOT EXISTS idx_user_search_date ON gg_douyin_user_search(search_date);

COMMENT ON TABLE gg_douyin_user_search IS '抖音搜索用户基础信息表';
COMMENT ON COLUMN gg_douyin_user_search.uid IS '用户UID（主键）';
COMMENT ON COLUMN gg_douyin_user_search.follower_count IS '粉丝数量';
COMMENT ON COLUMN gg_douyin_user_search.extra_info IS '扩展信息JSON';
COMMENT ON COLUMN gg_douyin_user_search.raw_data IS '完整原始数据JSON';


-- 2. UID到星图KOL ID的映射表
CREATE TABLE IF NOT EXISTS gg_xingtu_kol_mapping (
    id SERIAL PRIMARY KEY,
    uid TEXT NOT NULL UNIQUE,                -- 抖音用户UID
    kol_id TEXT,                             -- 星图KOL ID
    is_xingtu_kol BOOLEAN DEFAULT FALSE,     -- 是否为星图KOL
    
    -- 查询信息
    check_date TIMESTAMP,                    -- 查询时间
    error_message TEXT,                      -- 如果不是KOL，记录错误信息
    
    -- 元数据
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kol_mapping_uid ON gg_xingtu_kol_mapping(uid);
CREATE INDEX IF NOT EXISTS idx_kol_mapping_kol_id ON gg_xingtu_kol_mapping(kol_id);
CREATE INDEX IF NOT EXISTS idx_kol_mapping_is_xingtu ON gg_xingtu_kol_mapping(is_xingtu_kol);

COMMENT ON TABLE gg_xingtu_kol_mapping IS 'UID到星图KOL ID的映射表';
COMMENT ON COLUMN gg_xingtu_kol_mapping.is_xingtu_kol IS '是否为星图KOL';


-- 3. 星图KOL基础信息表（对应接口1.2）
CREATE TABLE IF NOT EXISTS gg_xingtu_kol_base_info (
    kol_id TEXT PRIMARY KEY,                 -- 星图KOL ID
    kol_name TEXT,                           -- KOL名称
    kol_avatar TEXT,                         -- 头像URL
    fans_count BIGINT,                       -- 粉丝数
    aweme_count INTEGER,                     -- 作品数
    vertical_category TEXT,                  -- 垂直领域
    tags TEXT[],                             -- 标签数组
    
    -- 完整原始数据
    raw_data JSONB,                          -- 完整的接口返回数据
    
    -- 元数据
    fetch_date TIMESTAMP,                    -- 获取时间
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kol_base_fans ON gg_xingtu_kol_base_info(fans_count DESC);
CREATE INDEX IF NOT EXISTS idx_kol_base_category ON gg_xingtu_kol_base_info(vertical_category);

COMMENT ON TABLE gg_xingtu_kol_base_info IS '星图KOL基础信息表';


-- 4. 星图KOL受众画像表（对应接口1.3）
CREATE TABLE IF NOT EXISTS gg_xingtu_kol_audience (
    id SERIAL PRIMARY KEY,
    kol_id TEXT NOT NULL UNIQUE,            -- 星图KOL ID
    
    -- 性别分布
    gender_distribution JSONB,               -- 性别分布数据
    
    -- 年龄分布
    age_distribution JSONB,                  -- 年龄分布数据
    
    -- 地域分布
    region_distribution JSONB,               -- 地域分布数据
    
    -- 兴趣标签
    interest_tags JSONB,                     -- 兴趣标签数据
    
    -- 完整原始数据
    raw_data JSONB,                          -- 完整的接口返回数据
    
    -- 元数据
    fetch_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kol_audience_kol_id ON gg_xingtu_kol_audience(kol_id);

COMMENT ON TABLE gg_xingtu_kol_audience IS '星图KOL受众画像表';


-- 5. 星图KOL服务报价表（对应接口1.4）
CREATE TABLE IF NOT EXISTS gg_xingtu_kol_price (
    id SERIAL PRIMARY KEY,
    kol_id TEXT NOT NULL UNIQUE,            -- 星图KOL ID
    
    -- 视频报价
    video_price_min DECIMAL(10,2),           -- 视频报价最低价
    video_price_max DECIMAL(10,2),           -- 视频报价最高价
    
    -- 直播报价
    live_price_min DECIMAL(10,2),            -- 直播报价最低价
    live_price_max DECIMAL(10,2),            -- 直播报价最高价
    
    -- 图文报价
    image_price_min DECIMAL(10,2),           -- 图文报价最低价
    image_price_max DECIMAL(10,2),           -- 图文报价最高价
    
    -- 历史订单
    order_count INTEGER,                     -- 历史订单数
    
    -- 完整原始数据
    raw_data JSONB,                          -- 完整的接口返回数据
    
    -- 元数据
    fetch_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kol_price_kol_id ON gg_xingtu_kol_price(kol_id);
CREATE INDEX IF NOT EXISTS idx_kol_price_video ON gg_xingtu_kol_price(video_price_min, video_price_max);

COMMENT ON TABLE gg_xingtu_kol_price IS '星图KOL服务报价表';


-- 6. 星图KOL内容定位表（对应接口1.5）
CREATE TABLE IF NOT EXISTS gg_xingtu_kol_content (
    id SERIAL PRIMARY KEY,
    kol_id TEXT NOT NULL UNIQUE,            -- 星图KOL ID
    
    -- 垂直领域
    vertical_field TEXT,                     -- 垂直领域
    
    -- 内容风格
    content_style TEXT[],                    -- 内容风格标签
    
    -- 合作案例
    cooperation_cases JSONB,                 -- 合作案例数据
    
    -- 完整原始数据
    raw_data JSONB,                          -- 完整的接口返回数据
    
    -- 元数据
    fetch_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kol_content_kol_id ON gg_xingtu_kol_content(kol_id);
CREATE INDEX IF NOT EXISTS idx_kol_content_field ON gg_xingtu_kol_content(vertical_field);

COMMENT ON TABLE gg_xingtu_kol_content IS '星图KOL内容定位表';


-- 7. 星图KOL转化能力表（对应接口1.6）
CREATE TABLE IF NOT EXISTS gg_xingtu_kol_conversion (
    id SERIAL PRIMARY KEY,
    kol_id TEXT NOT NULL UNIQUE,            -- 星图KOL ID
    
    -- 转化能力
    conversion_rate DECIMAL(5,2),            -- 转化率
    
    -- 互动数据
    interaction_data JSONB,                  -- 互动数据
    
    -- GMV能力
    gmv_ability JSONB,                       -- GMV能力数据
    
    -- 完整原始数据
    raw_data JSONB,                          -- 完整的接口返回数据
    
    -- 元数据
    fetch_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kol_conversion_kol_id ON gg_xingtu_kol_conversion(kol_id);
CREATE INDEX IF NOT EXISTS idx_kol_conversion_rate ON gg_xingtu_kol_conversion(conversion_rate DESC);

COMMENT ON TABLE gg_xingtu_kol_conversion IS '星图KOL转化能力表';
"""


def load_all_users_from_searches():
    """加载所有搜索结果中的用户数据"""
    script_dir = Path(__file__).parent.parent
    
    # 收集所有用户数据
    all_users = {}
    
    # 1. 加载"护肤"搜索结果
    output_dir1 = script_dir / "output"
    if output_dir1.exists():
        print(f"\n📂 处理目录: {output_dir1}")
        users = load_users_from_directory(output_dir1, "护肤")
        print(f"   找到 {len(users)} 个用户")
        for uid, user in users.items():
            if uid not in all_users:
                all_users[uid] = user
    
    # 2. 加载"护肤 达人 博主"搜索结果
    output_dirs = list(script_dir.glob("output_kol_full_*"))
    for output_dir in output_dirs:
        print(f"\n📂 处理目录: {output_dir}")
        users = load_users_from_directory(output_dir, "护肤 达人 博主")
        print(f"   找到 {len(users)} 个用户")
        for uid, user in users.items():
            if uid not in all_users:
                all_users[uid] = user
    
    print(f"\n✅ 总共找到 {len(all_users)} 个唯一用户")
    return list(all_users.values())


def load_users_from_directory(output_dir: Path, keyword: str):
    """从指定目录加载用户数据"""
    detail_dir = output_dir / "detail"
    
    users = {}
    
    if not detail_dir.exists():
        return users
    
    # 遍历所有page文件
    page_files = sorted(detail_dir.glob("page_*_request_response.json"))
    
    for page_file in page_files:
        with open(page_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        response = data.get('response', {})
        response_data = response.get('data', {})
        inner_data = response_data.get('data', [])
        
        if not isinstance(inner_data, list):
            continue
        
        for item in inner_data:
            user_info = item.get('user_info', {})
            uid = user_info.get('uid')
            
            if not uid:
                continue
            
            # 准备核心字段
            user_record = {
                'uid': str(uid),
                'sec_uid': user_info.get('sec_uid'),
                'nickname': user_info.get('nickname'),
                'unique_id': user_info.get('unique_id'),
                'gender': user_info.get('gender'),
                'follower_count': user_info.get('follower_count'),
                'verification_type': user_info.get('verification_type'),
                'avatar_url': user_info.get('avatar_thumb', {}).get('url_list', [None])[0],
                'signature': user_info.get('signature'),
                'live_status': user_info.get('live_status'),
                
                # 扩展信息
                'extra_info': {
                    'display_info': user_info.get('display_info'),
                    'user_tags': user_info.get('user_tags'),
                    'versatile_display': user_info.get('versatile_display'),
                    'weibo_verify': user_info.get('weibo_verify'),
                    'custom_verify': user_info.get('custom_verify'),
                    'enterprise_verify_reason': user_info.get('enterprise_verify_reason'),
                },
                
                # 完整原始数据
                'raw_data': user_info,
                
                # 搜索信息
                'search_keyword': keyword,
                'search_date': datetime.now().isoformat()
            }
            
            users[uid] = user_record
    
    return users


def import_users_to_supabase(users: list):
    """导入用户数据到Supabase"""
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print(f"\n📤 开始导入 {len(users)} 个用户到数据库...")
    
    # 分批导入（每批100条）
    batch_size = 100
    total_imported = 0
    total_updated = 0
    total_errors = 0
    
    for i in range(0, len(users), batch_size):
        batch = users[i:i+batch_size]
        
        try:
            # 使用upsert（插入或更新）
            response = supabase.table('gg_douyin_user_search').upsert(
                batch,
                on_conflict='uid'
            ).execute()
            
            batch_count = len(batch)
            total_imported += batch_count
            
            print(f"   ✅ 批次 {i//batch_size + 1}: 导入 {batch_count} 条数据")
            
        except Exception as e:
            total_errors += len(batch)
            print(f"   ❌ 批次 {i//batch_size + 1} 失败: {e}")
    
    print(f"\n✅ 导入完成！")
    print(f"   成功: {total_imported} 条")
    print(f"   失败: {total_errors} 条")
    
    return total_imported, total_errors


def main():
    """主函数"""
    print("=" * 60)
    print("创建数据库表并导入搜索用户数据")
    print("=" * 60)
    
    # 1. 加载环境变量
    print("\n1️⃣ 加载环境变量...")
    load_env()
    print(f"✅ Supabase URL: {SUPABASE_URL[:30]}...")
    
    # 2. 创建表结构（通过MCP完成）
    print("\n2️⃣ 数据库表结构已设计")
    print("   请使用MCP工具执行建表SQL")
    print("   建表SQL已保存到本文件的 CREATE_TABLES_SQL 变量中")
    
    # 3. 加载用户数据
    print("\n3️⃣ 加载用户数据...")
    users = load_all_users_from_searches()
    
    if not users:
        print("❌ 未找到用户数据")
        return
    
    # 4. 导入数据到Supabase
    print("\n4️⃣ 导入数据到Supabase...")
    imported, errors = import_users_to_supabase(users)
    
    # 5. 验证数据
    print("\n5️⃣ 验证导入结果...")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    try:
        # 查询总数
        response = supabase.table('gg_douyin_user_search').select('uid', count='exact').execute()
        count = response.count
        print(f"✅ 数据库中共有 {count} 条用户记录")
        
        # 查询粉丝数TOP 5
        response = supabase.table('gg_douyin_user_search').select('nickname, follower_count').order('follower_count', desc=True).limit(5).execute()
        print(f"\n📊 粉丝数 TOP 5:")
        for user in response.data:
            print(f"   {user['nickname']}: {user['follower_count']:,} 粉丝")
    
    except Exception as e:
        print(f"❌ 验证失败: {e}")
    
    print(f"\n{'='*60}")
    print("✅ 全部完成！")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

