/**
 * 搜索配置 API
 * 
 * 路由: /api/zara/search-config
 * 功能: 获取和更新搜索相关配置参数
 */

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

// Supabase 客户端
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

/** 配置项类型 */
interface SearchConfig {
  id: number;
  config_key: string;
  config_value: unknown;
  description: string | null;
  category: string;
  created_at: string;
  updated_at: string;
}

/**
 * GET - 获取所有搜索配置
 */
export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const category = searchParams.get('category');

    let query = supabase
      .from('gg_search_config')
      .select('*')
      .order('category')
      .order('config_key');

    if (category) {
      query = query.eq('category', category);
    }

    const { data, error } = await query;

    if (error) {
      console.error('获取配置失败:', error);
      return NextResponse.json(
        { success: false, error: error.message },
        { status: 500 }
      );
    }

    // 按分类分组
    const configsByCategory: Record<string, SearchConfig[]> = {};
    for (const config of data || []) {
      if (!configsByCategory[config.category]) {
        configsByCategory[config.category] = [];
      }
      configsByCategory[config.category].push(config);
    }

    // 转换为键值对格式（便于前端使用）
    const configMap: Record<string, unknown> = {};
    for (const config of data || []) {
      configMap[config.config_key] = config.config_value;
    }

    return NextResponse.json({
      success: true,
      data: {
        configs: data || [],
        byCategory: configsByCategory,
        map: configMap,
      },
    });
  } catch (error) {
    console.error('API 错误:', error);
    return NextResponse.json(
      { success: false, error: '服务器内部错误' },
      { status: 500 }
    );
  }
}

/**
 * PUT - 更新配置
 */
export async function PUT(request: NextRequest) {
  try {
    const body = await request.json();
    const { config_key, config_value } = body;

    if (!config_key) {
      return NextResponse.json(
        { success: false, error: '缺少 config_key' },
        { status: 400 }
      );
    }

    const { data, error } = await supabase
      .from('gg_search_config')
      .update({
        config_value,
        updated_at: new Date().toISOString(),
      })
      .eq('config_key', config_key)
      .select()
      .single();

    if (error) {
      console.error('更新配置失败:', error);
      return NextResponse.json(
        { success: false, error: error.message },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      data,
    });
  } catch (error) {
    console.error('API 错误:', error);
    return NextResponse.json(
      { success: false, error: '服务器内部错误' },
      { status: 500 }
    );
  }
}

/**
 * POST - 批量更新配置
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { configs } = body;

    if (!configs || !Array.isArray(configs)) {
      return NextResponse.json(
        { success: false, error: '缺少 configs 数组' },
        { status: 400 }
      );
    }

    const results = [];
    const errors = [];

    for (const { config_key, config_value } of configs) {
      const { data, error } = await supabase
        .from('gg_search_config')
        .update({
          config_value,
          updated_at: new Date().toISOString(),
        })
        .eq('config_key', config_key)
        .select()
        .single();

      if (error) {
        errors.push({ config_key, error: error.message });
      } else {
        results.push(data);
      }
    }

    return NextResponse.json({
      success: errors.length === 0,
      data: {
        updated: results,
        errors,
      },
    });
  } catch (error) {
    console.error('API 错误:', error);
    return NextResponse.json(
      { success: false, error: '服务器内部错误' },
      { status: 500 }
    );
  }
}

