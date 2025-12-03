/**
 * 商品个性化标签 API
 * 
 * 路由: /api/zara/product-persona-tags
 * 功能: 管理商品的千人千面标签（区域、风格、人群、场景）
 */

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

/**
 * GET - 获取商品个性化标签列表
 */
export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const page = parseInt(searchParams.get('page') || '1', 10);
    const pageSize = parseInt(searchParams.get('pageSize') || '20', 10);
    const productId = searchParams.get('productId');
    const offset = (page - 1) * pageSize;

    let query = supabase
      .from('gg_product_persona_tags')
      .select(`
        *,
        product:gg_taobao_products(id, item_name, main_image_url, price_yuan)
      `, { count: 'exact' });

    if (productId) {
      query = query.eq('product_id', parseInt(productId, 10));
    }

    const { data, count, error } = await query
      .order('updated_at', { ascending: false })
      .range(offset, offset + pageSize - 1);

    if (error) {
      console.error('获取商品标签失败:', error);
      return NextResponse.json({ success: false, error: error.message }, { status: 500 });
    }

    return NextResponse.json({
      success: true,
      data,
      totalCount: count,
      currentPage: page,
      pageSize,
      totalPages: Math.ceil((count || 0) / pageSize),
    });
  } catch (error) {
    console.error('API 错误:', error);
    return NextResponse.json({ success: false, error: '服务器错误' }, { status: 500 });
  }
}

/**
 * PUT - 更新商品个性化标签
 */
export async function PUT(request: NextRequest) {
  try {
    const body = await request.json();
    const { product_id, region_tags, style_tags, audience_tags, occasion_tags, custom_tags, notes } = body;

    if (!product_id) {
      return NextResponse.json({ success: false, error: '缺少 product_id' }, { status: 400 });
    }

    const { data, error } = await supabase
      .from('gg_product_persona_tags')
      .upsert({
        product_id,
        region_tags: region_tags || [],
        style_tags: style_tags || [],
        audience_tags: audience_tags || [],
        occasion_tags: occasion_tags || [],
        custom_tags: custom_tags || [],
        notes,
        updated_at: new Date().toISOString(),
      }, { onConflict: 'product_id' })
      .select()
      .single();

    if (error) {
      console.error('更新商品标签失败:', error);
      return NextResponse.json({ success: false, error: error.message }, { status: 500 });
    }

    return NextResponse.json({ success: true, data });
  } catch (error) {
    console.error('API 错误:', error);
    return NextResponse.json({ success: false, error: '服务器错误' }, { status: 500 });
  }
}

