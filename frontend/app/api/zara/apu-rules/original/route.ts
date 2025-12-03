/**
 * APU 原始规则库 API
 * 
 * 路由: /api/zara/apu-rules/original
 * 功能: 获取、更新 APU 原始规则（品类级别）和因果链
 */

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

// Supabase 客户端
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

/**
 * GET - 获取原始规则库
 */
export async function GET() {
  try {
    // 获取品类规则
    const { data: rules, error: rulesError } = await supabase
      .from('gg_apu_rules')
      .select('*')
      .order('category');

    if (rulesError) {
      console.error('获取规则失败:', rulesError);
      return NextResponse.json(
        { success: false, error: rulesError.message },
        { status: 500 }
      );
    }

    // 获取因果链
    const { data: chains, error: chainsError } = await supabase
      .from('gg_apu_causal_chains')
      .select('*')
      .order('rule_id');

    if (chainsError) {
      console.error('获取因果链失败:', chainsError);
      return NextResponse.json(
        { success: false, error: chainsError.message },
        { status: 500 }
      );
    }

    // 将因果链按 rule_id 分组
    const chainsByRuleId: Record<number, typeof chains> = {};
    for (const chain of chains || []) {
      if (!chainsByRuleId[chain.rule_id]) {
        chainsByRuleId[chain.rule_id] = [];
      }
      chainsByRuleId[chain.rule_id].push(chain);
    }

    return NextResponse.json({
      success: true,
      data: {
        rules: rules || [],
        chains: chains || [],
        chainsByRuleId,
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
 * PUT - 更新品类规则
 */
export async function PUT(request: NextRequest) {
  try {
    const body = await request.json();
    const { type, id, ...updateData } = body;

    if (!type || !id) {
      return NextResponse.json(
        { success: false, error: '缺少必要参数' },
        { status: 400 }
      );
    }

    updateData.updated_at = new Date().toISOString();

    if (type === 'rule') {
      const { data, error } = await supabase
        .from('gg_apu_rules')
        .update(updateData)
        .eq('id', id)
        .select()
        .single();

      if (error) {
        return NextResponse.json(
          { success: false, error: error.message },
          { status: 500 }
        );
      }

      return NextResponse.json({ success: true, data });
    } else if (type === 'chain') {
      const { data, error } = await supabase
        .from('gg_apu_causal_chains')
        .update(updateData)
        .eq('id', id)
        .select()
        .single();

      if (error) {
        return NextResponse.json(
          { success: false, error: error.message },
          { status: 500 }
        );
      }

      return NextResponse.json({ success: true, data });
    }

    return NextResponse.json(
      { success: false, error: '未知类型' },
      { status: 400 }
    );
  } catch (error) {
    console.error('API 错误:', error);
    return NextResponse.json(
      { success: false, error: '服务器内部错误' },
      { status: 500 }
    );
  }
}

/**
 * POST - 添加新规则或因果链
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { type, ...insertData } = body;

    if (!type) {
      return NextResponse.json(
        { success: false, error: '缺少 type 参数' },
        { status: 400 }
      );
    }

    if (type === 'rule') {
      const { data, error } = await supabase
        .from('gg_apu_rules')
        .insert(insertData)
        .select()
        .single();

      if (error) {
        return NextResponse.json(
          { success: false, error: error.message },
          { status: 500 }
        );
      }

      return NextResponse.json({ success: true, data });
    } else if (type === 'chain') {
      const { data, error } = await supabase
        .from('gg_apu_causal_chains')
        .insert(insertData)
        .select()
        .single();

      if (error) {
        return NextResponse.json(
          { success: false, error: error.message },
          { status: 500 }
        );
      }

      return NextResponse.json({ success: true, data });
    }

    return NextResponse.json(
      { success: false, error: '未知类型' },
      { status: 400 }
    );
  } catch (error) {
    console.error('API 错误:', error);
    return NextResponse.json(
      { success: false, error: '服务器内部错误' },
      { status: 500 }
    );
  }
}

/**
 * DELETE - 删除规则或因果链
 */
export async function DELETE(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const type = searchParams.get('type');
    const id = searchParams.get('id');

    if (!type || !id) {
      return NextResponse.json(
        { success: false, error: '缺少必要参数' },
        { status: 400 }
      );
    }

    const table = type === 'rule' ? 'gg_apu_rules' : 'gg_apu_causal_chains';

    const { error } = await supabase
      .from(table)
      .delete()
      .eq('id', id);

    if (error) {
      return NextResponse.json(
        { success: false, error: error.message },
        { status: 500 }
      );
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('API 错误:', error);
    return NextResponse.json(
      { success: false, error: '服务器内部错误' },
      { status: 500 }
    );
  }
}

