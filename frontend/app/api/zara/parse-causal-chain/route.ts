/**
 * 解析自然语言因果链 API
 * 
 * 路由: POST /api/zara/parse-causal-chain
 * 功能: 使用 LLM 将自然语言描述解析为 APU 因果链结构
 */

import { NextRequest, NextResponse } from 'next/server';
import OpenAI from 'openai';

// OpenRouter 客户端
const openrouter = new OpenAI({
  apiKey: process.env.OPENROUTER_API_KEY,
  baseURL: 'https://openrouter.ai/api/v1',
});

/**
 * POST - 解析自然语言为因果链
 */
export async function POST(request: NextRequest) {
  try {
    const { text } = await request.json();

    if (!text) {
      return NextResponse.json({ success: false, error: '缺少输入文本' }, { status: 400 });
    }

    // 构建 Prompt（包含风格维度）
    const prompt = `你是一个服装分析专家。请将以下自然语言描述解析为 APUS 四维度因果链结构。

APUS 因果链结构说明：
- Attribute（属性）：服装的物理特征，如版型、设计、材质等
- Performance（性能）：属性带来的功能效果，如显瘦、保暖、舒适等
- Use（场景）：适合的使用场景，如约会、通勤、度假等
- Style（风格）：整体穿搭风格，如简约、浪漫、休闲、时尚等

用户输入：
"${text}"

请按以下 JSON 格式输出解析结果：
{
  "attribute": "提取的属性关键词（单个）",
  "performance": "提取的性能效果（单个短语）",
  "use": ["场景1", "场景2"],
  "style": "整体风格（2-4个字）"
}

示例：
输入："吊带连衣裙，显瘦显腿长，适合海边度假，浪漫风格"
输出：{"attribute": "吊带设计", "performance": "显瘦显腿长", "use": ["海边度假"], "style": "浪漫优雅"}

输入："高领毛衣保暖显气质，适合冬季约会，温柔优雅风"
输出：{"attribute": "高领设计", "performance": "保暖显气质", "use": ["冬季约会"], "style": "温柔知性"}

输入："阔腿裤宽松舒适不挑腿型，日常通勤百搭，休闲简约风"
输出：{"attribute": "阔腿版型", "performance": "宽松舒适不挑腿型", "use": ["日常通勤", "百搭穿搭"], "style": "休闲简约"}

只输出 JSON，不要其他内容。`;

    const response = await openrouter.chat.completions.create({
      model: 'google/gemini-2.5-flash',
      messages: [{ role: 'user', content: prompt }],
      temperature: 0.3,
      max_tokens: 200,
    });

    const content = response.choices[0]?.message?.content || '';

    // 解析 JSON
    const jsonMatch = content.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
      return NextResponse.json({ success: false, error: '解析失败' }, { status: 500 });
    }

    const parsed = JSON.parse(jsonMatch[0]);

    return NextResponse.json({
      success: true,
      data: {
        attribute: parsed.attribute || '',
        performance: parsed.performance || '',
        use: Array.isArray(parsed.use) ? parsed.use : [parsed.use],
        style: parsed.style || '时尚百搭',
      },
    });
  } catch (error) {
    console.error('解析因果链失败:', error);
    return NextResponse.json({ success: false, error: '服务器错误' }, { status: 500 });
  }
}

