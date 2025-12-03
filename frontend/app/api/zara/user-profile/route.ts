/**
 * 用户画像 API
 * 
 * 路由: /api/zara/user-profile
 * 功能: 管理用户画像和历史聊天记录，提取用户偏好标签
 */

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

/**
 * GET - 获取用户画像列表或单个用户详情
 */
export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const userId = searchParams.get('userId');
    const includeHistory = searchParams.get('includeHistory') === 'true';

    if (userId) {
      // 获取单个用户详情
      const { data: profile, error: profileError } = await supabase
        .from('gg_user_profile')
        .select('*')
        .eq('user_id', userId)
        .single();

      if (profileError && profileError.code !== 'PGRST116') {
        console.error('获取用户画像失败:', profileError);
        return NextResponse.json({ success: false, error: profileError.message }, { status: 500 });
      }

      let chatHistory = [];
      if (includeHistory) {
        const { data: history, error: historyError } = await supabase
          .from('gg_user_chat_history')
          .select('*')
          .eq('user_id', userId)
          .order('created_at', { ascending: false })
          .limit(50);

        if (historyError) {
          console.error('获取聊天记录失败:', historyError);
        } else {
          chatHistory = history || [];
        }
      }

      return NextResponse.json({
        success: true,
        data: {
          profile,
          chatHistory,
        },
      });
    } else {
      // 获取所有用户画像列表
      const { data, error } = await supabase
        .from('gg_user_profile')
        .select('*')
        .order('last_active_at', { ascending: false });

      if (error) {
        console.error('获取用户列表失败:', error);
        return NextResponse.json({ success: false, error: error.message }, { status: 500 });
      }

      return NextResponse.json({
        success: true,
        data,
      });
    }
  } catch (error) {
    console.error('API 错误:', error);
    return NextResponse.json({ success: false, error: '服务器错误' }, { status: 500 });
  }
}

/**
 * POST - 记录用户聊天并更新画像
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const {
      user_id,
      query,
      search_text,
      extracted_tags,
      intent_attribute,
      intent_performance,
      intent_use,
      result_count,
      session_id,
    } = body;

    if (!user_id || !query) {
      return NextResponse.json({ success: false, error: '缺少必要参数' }, { status: 400 });
    }

    // 1. 记录聊天历史
    const { error: chatError } = await supabase
      .from('gg_user_chat_history')
      .insert({
        user_id,
        query,
        search_text,
        extracted_tags,
        intent_attribute,
        intent_performance,
        intent_use,
        result_count,
        session_id,
      });

    if (chatError) {
      console.error('记录聊天失败:', chatError);
      return NextResponse.json({ success: false, error: chatError.message }, { status: 500 });
    }

    // 2. 更新用户画像（简单累加）
    // 获取现有画像
    const { data: existingProfile } = await supabase
      .from('gg_user_profile')
      .select('*')
      .eq('user_id', user_id)
      .single();

    // 更新标签云
    const tagCloud = existingProfile?.tag_cloud || {};
    for (const tag of extracted_tags || []) {
      tagCloud[tag] = (tagCloud[tag] || 0) + 1;
    }
    for (const attr of intent_attribute || []) {
      tagCloud[attr] = (tagCloud[attr] || 0) + 1;
    }
    for (const perf of intent_performance || []) {
      tagCloud[perf] = (tagCloud[perf] || 0) + 1;
    }
    for (const use of intent_use || []) {
      tagCloud[use] = (tagCloud[use] || 0) + 1;
    }

    // Upsert 用户画像
    const { error: profileError } = await supabase
      .from('gg_user_profile')
      .upsert({
        user_id,
        total_searches: (existingProfile?.total_searches || 0) + 1,
        tag_cloud: tagCloud,
        last_active_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }, { onConflict: 'user_id' });

    if (profileError) {
      console.error('更新用户画像失败:', profileError);
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('API 错误:', error);
    return NextResponse.json({ success: false, error: '服务器错误' }, { status: 500 });
  }
}

