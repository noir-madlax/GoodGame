/**
 * 因果链 CRUD API
 * 
 * 路由: /api/zara/causal-chains
 * 功能: 管理 APU 因果链
 */

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

/**
 * POST - 创建新因果链
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { rule_id, attribute_cause, performance_effect, use_cases, style_result } = body;

    if (!rule_id || !attribute_cause || !performance_effect || !use_cases) {
      return NextResponse.json({ success: false, error: '缺少必要参数' }, { status: 400 });
    }

    const { data, error } = await supabase
      .from('gg_apu_causal_chains')
      .insert({
        rule_id,
        attribute_cause,
        performance_effect,
        use_cases: Array.isArray(use_cases) ? use_cases : [use_cases],
        style_result: style_result || '时尚百搭',
      })
      .select()
      .single();

    if (error) {
      console.error('创建因果链失败:', error);
      return NextResponse.json({ success: false, error: error.message }, { status: 500 });
    }

    return NextResponse.json({ success: true, data });
  } catch (error) {
    console.error('API 错误:', error);
    return NextResponse.json({ success: false, error: '服务器错误' }, { status: 500 });
  }
}

/**
 * DELETE - 删除因果链
 */
export async function DELETE(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const id = searchParams.get('id');

    if (!id) {
      return NextResponse.json({ success: false, error: '缺少 id' }, { status: 400 });
    }

    const { error } = await supabase
      .from('gg_apu_causal_chains')
      .delete()
      .eq('id', parseInt(id, 10));

    if (error) {
      console.error('删除因果链失败:', error);
      return NextResponse.json({ success: false, error: error.message }, { status: 500 });
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('API 错误:', error);
    return NextResponse.json({ success: false, error: '服务器错误' }, { status: 500 });
  }
}

