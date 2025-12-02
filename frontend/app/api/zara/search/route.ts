/**
 * ZARA 商品搜索 API
 * 
 * 路由: POST /api/zara/search
 * 
 * 功能:
 * 1. 文本搜索: LLM 意图解析 → 文本向量生成 → 混合搜索
 * 2. 图片搜索: CLIP 向量生成 → 图片向量搜索
 * 3. 混合搜索: 文本 + 图片同时搜索 → RRF 合并
 * 
 * 外部 API:
 * - OpenAI: text-embedding-3-small (文本向量)
 * - OpenRouter + Gemini 2.5 Flash: LLM 意图解析
 * - Replicate CLIP: 图片向量
 */

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import OpenAI from 'openai';

// ============================================================================
// 类型定义
// ============================================================================

// 搜索请求体
interface SearchRequest {
  query?: string;           // 文本查询
  imageBase64?: string;     // 图片 Base64 (可选)
  matchCount?: number;      // 返回数量
}

// LLM 解析结果
interface LLMParseResult {
  isSearch: boolean;        // 是否是搜索意图
  extractedTags: string[];  // 提取的标签
  searchText: string;       // 用于向量搜索的文本
  chatResponse?: string;    // 如果是闲聊，返回回复
}

// 搜索结果
interface SearchResult {
  product_id: number;
  item_id: number;
  item_name: string;
  price_yuan: number;
  main_image_url: string;
  matched_image_url?: string;
  vector_score: number;
  tag_score: number;
  image_score?: number;
  matched_tags: string[];
  final_score: number;
}

// Debug 结果项
interface DebugResultItem {
  rank: number;
  productId: number;
  productName: string;
  vectorScore: number;
  tagScore: number;
  finalScore: number;
  matchedTags: string[];
}

// Debug 信息
interface DebugInfo {
  input: {
    rawQuery: string;
    llmParseTime?: number;
    extractedTags?: string[];
    searchText?: string;
  };
  params: {
    vectorWeight: number;
    tagWeight: number;
    rrf_k: number;
    searchTime?: number;
  };
  results?: DebugResultItem[];       // 前 10 个结果
  bottomResults?: DebugResultItem[]; // 后 10 个结果
}

// ============================================================================
// 初始化客户端
// ============================================================================

// Supabase 客户端
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

// OpenAI 客户端 (用于 Embedding)
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

// OpenRouter 客户端 (用于 LLM 意图解析)
const openrouter = new OpenAI({
  apiKey: process.env.OPENROUTER_API_KEY,
  baseURL: 'https://openrouter.ai/api/v1',
});

// ============================================================================
// 工具函数
// ============================================================================

/**
 * 使用 Gemini 2.5 Flash 解析用户意图
 * 提取搜索标签和搜索文本
 */
async function parseUserIntent(query: string): Promise<LLMParseResult> {
  // const startTime = Date.now(); // 用于调试
  
  try {
    const response = await openrouter.chat.completions.create({
      model: 'google/gemini-2.5-flash',
      messages: [
        {
          role: 'system',
          content: `你是一个商品搜索助手，负责从用户的自然语言输入中提取搜索意图。

你需要：
1. 判断用户是否在搜索商品
2. 如果是搜索，提取关键属性作为标签：品类、颜色、材质、风格、场景、季节等
3. 生成用于向量搜索的简洁搜索文本

可用的标签类型：
- 性别: 女士, 男士, 儿童, 婴儿
- 季节: 春季, 夏季, 秋季, 冬季
- 品类: 连衣裙, T恤, 衬衫, 裤子, 牛仔裤, 外套, 针织衫, 毛衣, 羽绒服, 裙子, 短裙, 长裙 等
- 风格: 休闲, 通勤, 运动, 优雅, 简约, 复古 等
- 材质: 棉, 羊毛, 丝绸, 牛仔, 针织 等
- 特征: 宽松, 修身, 印花, 条纹, 纯色 等

输出格式 (必须是有效的 JSON):
{
  "isSearch": true,
  "extractedTags": ["标签1", "标签2"],
  "searchText": "用于向量搜索的简洁文本"
}`
        },
        {
          role: 'user',
          content: query
        }
      ],
      temperature: 0.3,
      max_tokens: 500,
    });

    const content = response.choices[0]?.message?.content || '';
    
    // 解析 JSON 响应
    const jsonMatch = content.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      const parsed = JSON.parse(jsonMatch[0]);
      return {
        isSearch: parsed.isSearch ?? true,
        extractedTags: parsed.extractedTags || [],
        searchText: parsed.searchText || query,
        chatResponse: parsed.chatResponse,
      };
    }
    
    // 如果解析失败，返回默认值
    return {
      isSearch: true,
      extractedTags: [],
      searchText: query,
    };
  } catch (error) {
    console.error('LLM 解析失败:', error);
    // 降级处理：直接使用原始查询
    return {
      isSearch: true,
      extractedTags: [],
      searchText: query,
    };
  }
}

/**
 * 使用 OpenAI 生成文本向量
 */
async function generateTextEmbedding(text: string): Promise<number[]> {
  const response = await openai.embeddings.create({
    model: 'text-embedding-3-small',
    input: text,
  });
  
  return response.data[0].embedding;
}

/**
 * 使用 Replicate CLIP 生成图片向量
 */
async function generateImageEmbedding(imageBase64: string): Promise<number[]> {
  const response = await fetch('https://api.replicate.com/v1/predictions', {
    method: 'POST',
    headers: {
      'Authorization': `Token ${process.env.REPLICATE_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      version: '75b33f253f7714a281ad3e9b28f63e3232d583716ef6718f2e46641077ea040a',
      input: {
        inputs: imageBase64.startsWith('data:') ? imageBase64 : `data:image/jpeg;base64,${imageBase64}`,
      },
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(`Replicate API 错误: ${JSON.stringify(error)}`);
  }

  const prediction = await response.json();
  
  // 等待预测完成
  let result = prediction;
  while (result.status !== 'succeeded' && result.status !== 'failed') {
    await new Promise(resolve => setTimeout(resolve, 1000));
    const pollResponse = await fetch(result.urls.get, {
      headers: {
        'Authorization': `Token ${process.env.REPLICATE_API_KEY}`,
      },
    });
    result = await pollResponse.json();
  }

  if (result.status === 'failed') {
    throw new Error(`Replicate 预测失败: ${result.error}`);
  }

  // 打印完整返回结果用于调试
  console.log('Replicate API 完整返回:', JSON.stringify(result, null, 2));

  // 返回向量
  // Replicate openai/clip 模型返回格式:
  // - output: { embedding: [...] } (768维向量)
  const output = result.output;
  
  // 新格式: output.embedding (openai/clip 模型)
  if (output && typeof output === 'object' && 'embedding' in output) {
    const embedding = output.embedding;
    if (Array.isArray(embedding)) {
      console.log(`Replicate 返回 embedding 维度: ${embedding.length}`);
      return embedding;
    }
  }
  
  // 旧格式兼容: 如果是数组的数组，取第一个
  if (Array.isArray(output) && Array.isArray(output[0])) {
    return output[0];
  }
  
  // 旧格式兼容: 如果直接是数组
  if (Array.isArray(output)) {
    return output;
  }
  
  console.error('Replicate 返回格式异常:', typeof output, JSON.stringify(output));
  throw new Error(`Replicate 返回格式异常: ${typeof output}`);
}

/**
 * 将数组转换为 pgvector 格式字符串
 */
function toVectorString(arr: number[]): string {
  return `[${arr.join(',')}]`;
}

/**
 * 执行文本混合搜索
 */
async function hybridSearchByText(
  embedding: number[],
  tags: string[],
  matchCount: number = 50
): Promise<SearchResult[]> {
  // pgvector 需要向量格式为 "[...]" 字符串
  const { data, error } = await supabase.rpc('hybrid_search_products', {
    query_embedding: toVectorString(embedding),
    tag_values: tags,
    match_count: matchCount,
    vector_weight: 0.75,
    tag_weight: 0.25,
    rrf_k: 50,
  });

  if (error) {
    console.error('混合搜索失败:', error);
    throw error;
  }

  return data || [];
}

/**
 * 执行图片搜索
 */
async function searchByImage(
  imageEmbedding: number[],
  textEmbedding?: number[],
  tags?: string[],
  matchCount: number = 50
): Promise<SearchResult[]> {
  // pgvector 需要向量格式为 "[...]" 字符串
  const { data, error } = await supabase.rpc('hybrid_search_with_image', {
    image_embedding: toVectorString(imageEmbedding),
    text_embedding: textEmbedding ? toVectorString(textEmbedding) : null,
    tag_values: tags || [],
    match_count: matchCount,
    image_weight: 0.5,
    text_weight: textEmbedding ? 0.3 : 0,
    tag_weight: tags && tags.length > 0 ? 0.2 : 0,
    rrf_k: 50,
  });

  if (error) {
    console.error('图片搜索失败:', error);
    throw error;
  }

  return data || [];
}

// ============================================================================
// API 路由处理
// ============================================================================

export async function POST(request: NextRequest) {
  const startTime = Date.now();
  
  try {
    const body: SearchRequest = await request.json();
    const { query, imageBase64, matchCount = 50 } = body;

    // 验证输入
    if (!query && !imageBase64) {
      return NextResponse.json(
        { error: '请提供搜索文本或图片' },
        { status: 400 }
      );
    }

    let results: SearchResult[] = [];
    const debugInfo: DebugInfo = {
      input: {
        rawQuery: query || '[图片搜索]',
      },
      params: {
        vectorWeight: 0.75,
        tagWeight: 0.25,
        rrf_k: 50,
      },
    };

    // 情况 1: 只有文本
    if (query && !imageBase64) {
      // Step 1: LLM 意图解析
      const llmStartTime = Date.now();
      const parseResult = await parseUserIntent(query);
      const llmParseTime = Date.now() - llmStartTime;

      debugInfo.input.llmParseTime = llmParseTime;
      debugInfo.input.extractedTags = parseResult.extractedTags;
      debugInfo.input.searchText = parseResult.searchText;

      // Step 2: 生成文本向量
      const embedding = await generateTextEmbedding(parseResult.searchText);

      // Step 3: 混合搜索
      results = await hybridSearchByText(embedding, parseResult.extractedTags, matchCount);
    }
    // 情况 2: 只有图片
    else if (imageBase64 && !query) {
      // Step 1: 生成图片向量
      const imageEmbedding = await generateImageEmbedding(imageBase64);

      // Step 2: 图片搜索
      results = await searchByImage(imageEmbedding, undefined, undefined, matchCount);
      
      debugInfo.params.vectorWeight = 1;
      debugInfo.params.tagWeight = 0;
    }
    // 情况 3: 文本 + 图片
    else if (query && imageBase64) {
      // Step 1: LLM 意图解析
      const llmStartTime = Date.now();
      const parseResult = await parseUserIntent(query);
      const llmParseTime = Date.now() - llmStartTime;

      debugInfo.input.llmParseTime = llmParseTime;
      debugInfo.input.extractedTags = parseResult.extractedTags;
      debugInfo.input.searchText = parseResult.searchText;

      // Step 2: 并行生成向量
      const [textEmbedding, imageEmbedding] = await Promise.all([
        generateTextEmbedding(parseResult.searchText),
        generateImageEmbedding(imageBase64),
      ]);

      // Step 3: 图片 + 文本混合搜索
      results = await searchByImage(
        imageEmbedding,
        textEmbedding,
        parseResult.extractedTags,
        matchCount
      );

      debugInfo.params.vectorWeight = 0.3;
      debugInfo.params.tagWeight = 0.2;
    }

    // 计算总耗时
    const searchTime = Date.now() - startTime;
    debugInfo.params.searchTime = searchTime;

    // 生成结果 Debug 信息 (前 10 + 后 10)
    const topResults = results.slice(0, 10).map((r, i) => ({
      rank: i + 1,
      productId: r.product_id,
      productName: r.item_name,
      vectorScore: r.vector_score || r.image_score || 0,
      tagScore: r.tag_score,
      finalScore: r.final_score,
      matchedTags: r.matched_tags || [],
    }));
    
    const bottomResults = results.length > 10 
      ? results.slice(-10).map((r, i) => ({
          rank: results.length - 9 + i,
          productId: r.product_id,
          productName: r.item_name,
          vectorScore: r.vector_score || r.image_score || 0,
          tagScore: r.tag_score,
          finalScore: r.final_score,
          matchedTags: r.matched_tags || [],
        }))
      : [];
    
    debugInfo.results = topResults;
    debugInfo.bottomResults = bottomResults;

    return NextResponse.json({
      success: true,
      results,
      debugInfo,
      totalCount: results.length,
    });

  } catch (error) {
    console.error('搜索 API 错误:', error);
    return NextResponse.json(
      { 
        error: '搜索失败', 
        message: error instanceof Error ? error.message : '未知错误' 
      },
      { status: 500 }
    );
  }
}

