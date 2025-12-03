/**
 * 标签个性化规则 API
 * 
 * 路由: /api/zara/tag-persona-rules
 * 功能: 管理基于标签的千人千面推荐规则
 */

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

/**
 * GET - 获取标签规则列表
 */
export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const tagType = searchParams.get('tagType');
    const tagName = searchParams.get('tagName');

    // 获取每个类型的数量统计
    const { data: countData } = await supabase
      .from('gg_tag_persona_rules')
      .select('tag_type');

    const typeCounts: Record<string, number> = {
      attribute: 0,
      performance: 0,
      use: 0,
      style: 0,
    };
    
    for (const item of countData || []) {
      if (item.tag_type && typeCounts[item.tag_type] !== undefined) {
        typeCounts[item.tag_type]++;
      }
    }

    // 获取规则列表
    let query = supabase
      .from('gg_tag_persona_rules')
      .select('*')
      .order('affected_product_count', { ascending: false });

    if (tagType) {
      query = query.eq('tag_type', tagType);
    }

    if (tagName) {
      query = query.eq('tag_name', tagName);
    }

    const { data, error } = await query;

    if (error) {
      console.error('获取标签规则失败:', error);
      return NextResponse.json({ success: false, error: error.message }, { status: 500 });
    }

    return NextResponse.json({
      success: true,
      data,
      typeCounts,
      total: (countData || []).length,
    });
  } catch (error) {
    console.error('API 错误:', error);
    return NextResponse.json({ success: false, error: '服务器错误' }, { status: 500 });
  }
}

/**
 * PUT - 更新标签规则
 */
export async function PUT(request: NextRequest) {
  try {
    const body = await request.json();
    const { 
      id,
      region_south_weight,
      region_north_weight,
      season_tags,
      style_tags,
      audience_tags,
      notes,
    } = body;

    if (!id) {
      return NextResponse.json({ success: false, error: '缺少 id' }, { status: 400 });
    }

    const updateData: Record<string, unknown> = {
      updated_at: new Date().toISOString(),
    };

    if (region_south_weight !== undefined) updateData.region_south_weight = region_south_weight;
    if (region_north_weight !== undefined) updateData.region_north_weight = region_north_weight;
    if (season_tags !== undefined) updateData.season_tags = season_tags;
    if (style_tags !== undefined) updateData.style_tags = style_tags;
    if (audience_tags !== undefined) updateData.audience_tags = audience_tags;
    if (notes !== undefined) updateData.notes = notes;

    const { data, error } = await supabase
      .from('gg_tag_persona_rules')
      .update(updateData)
      .eq('id', id)
      .select()
      .single();

    if (error) {
      console.error('更新标签规则失败:', error);
      return NextResponse.json({ success: false, error: error.message }, { status: 500 });
    }

    return NextResponse.json({ success: true, data });
  } catch (error) {
    console.error('API 错误:', error);
    return NextResponse.json({ success: false, error: '服务器错误' }, { status: 500 });
  }
}

/**
 * POST - 创建新标签规则
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { 
      tag_name,
      tag_type,
      region_south_weight = 0.5,
      region_north_weight = 0.5,
      season_tags = [],
      style_tags = [],
      audience_tags = [],
      notes,
    } = body;

    if (!tag_name || !tag_type) {
      return NextResponse.json({ success: false, error: '缺少必要参数' }, { status: 400 });
    }

    const { data, error } = await supabase
      .from('gg_tag_persona_rules')
      .insert({
        tag_name,
        tag_type,
        region_south_weight,
        region_north_weight,
        season_tags,
        style_tags,
        audience_tags,
        notes,
      })
      .select()
      .single();

    if (error) {
      console.error('创建标签规则失败:', error);
      return NextResponse.json({ success: false, error: error.message }, { status: 500 });
    }

    return NextResponse.json({ success: true, data });
  } catch (error) {
    console.error('API 错误:', error);
    return NextResponse.json({ success: false, error: '服务器错误' }, { status: 500 });
  }
}

