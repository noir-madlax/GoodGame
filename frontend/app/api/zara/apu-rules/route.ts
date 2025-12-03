/**
 * APU 规则库 API
 * 
 * 路由: /api/zara/apu-rules
 * 功能: 获取、更新、删除 APU 规则
 */

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

// Supabase 客户端
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

/**
 * GET - 获取规则库列表
 */
export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const category = searchParams.get('category');
    const page = parseInt(searchParams.get('page') || '1');
    const pageSize = parseInt(searchParams.get('pageSize') || '20');
    const search = searchParams.get('search');
    
    // 构建查询
    let query = supabase
      .from('gg_apu_product_rules')
      .select('*', { count: 'exact' });
    
    // 按品类筛选
    if (category) {
      query = query.eq('category', category);
    }
    
    // 搜索商品描述
    if (search) {
      query = query.ilike('product_description', `%${search}%`);
    }
    
    // 分页
    const offset = (page - 1) * pageSize;
    query = query
      .order('category')
      .order('product_description')
      .range(offset, offset + pageSize - 1);
    
    const { data, error, count } = await query;
    
    if (error) {
      console.error('获取规则库失败:', error);
      return NextResponse.json(
        { success: false, error: error.message },
        { status: 500 }
      );
    }
    
    // 获取所有品类列表
    const { data: categoriesData } = await supabase
      .from('gg_apu_product_rules')
      .select('category')
      .order('category');
    
    const categories = [...new Set(categoriesData?.map(c => c.category) || [])];
    
    return NextResponse.json({
      success: true,
      data: {
        rules: data || [],
        total: count || 0,
        page,
        pageSize,
        totalPages: Math.ceil((count || 0) / pageSize),
        categories,
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
 * PUT - 更新规则
 */
export async function PUT(request: NextRequest) {
  try {
    const body = await request.json();
    const { id, ...updateData } = body;
    
    if (!id) {
      return NextResponse.json(
        { success: false, error: '缺少规则 ID' },
        { status: 400 }
      );
    }
    
    // 更新时间
    updateData.updated_at = new Date().toISOString();
    
    const { data, error } = await supabase
      .from('gg_apu_product_rules')
      .update(updateData)
      .eq('id', id)
      .select()
      .single();
    
    if (error) {
      console.error('更新规则失败:', error);
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
 * DELETE - 删除规则
 */
export async function DELETE(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const id = searchParams.get('id');
    
    if (!id) {
      return NextResponse.json(
        { success: false, error: '缺少规则 ID' },
        { status: 400 }
      );
    }
    
    const { error } = await supabase
      .from('gg_apu_product_rules')
      .delete()
      .eq('id', id);
    
    if (error) {
      console.error('删除规则失败:', error);
      return NextResponse.json(
        { success: false, error: error.message },
        { status: 500 }
      );
    }
    
    return NextResponse.json({
      success: true,
    });
  } catch (error) {
    console.error('API 错误:', error);
    return NextResponse.json(
      { success: false, error: '服务器内部错误' },
      { status: 500 }
    );
  }
}

