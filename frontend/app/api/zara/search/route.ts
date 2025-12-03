/**
 * ZARA 商品搜索 API
 * 
 * 路由: POST /api/zara/search
 * 
 * 功能:
 * 1. 文本搜索: APU 意图解析 → 文本向量生成 → 混合搜索
 * 2. 图片搜索: TinyCLIP 向量生成 (512维) → 图片向量搜索
 * 3. 混合搜索: 文本 + 图片同时搜索 → RRF 合并
 * 
 * APU 三维度理论:
 * - Attribute (属性): 物理特性 - 外观、材质、版型等
 * - Performance (性能): 性能表现 - 舒适度、保暖性等
 * - Use (使用): 使用场景 - 日常、通勤、约会等
 * 
 * 搜索权重: 向量搜索 0.9 + 标签匹配 0.1
 * 
 * 外部 API:
 * - OpenAI: text-embedding-3-small (文本向量)
 * - OpenRouter + Gemini 2.5 Flash: LLM APU 意图解析
 * - Replicate TinyCLIP: 图片向量 (512维)
 */

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import OpenAI from 'openai';
import { buildSearchPrompt } from '@/zara/lib/apu-prompt-builder';

// ============================================================================
// 类型定义
// ============================================================================

// 搜索请求体
interface SearchRequest {
  query?: string;           // 文本查询
  imageBase64?: string;     // 图片 Base64 (可选)
  matchCount?: number;      // 返回数量
}

// LLM APU 解析结果
interface LLMParseResult {
  isSearch: boolean;                    // 是否是搜索意图
  primaryDimension?: string;            // 主要关注的维度: attribute/performance/use
  intentAnalysis?: {                    // APU 意图分析
    attribute: string[];                // 物理属性需求
    performance: string[];              // 性能需求
    use: string[];                      // 使用场景
  };
  causalReasoning?: string;             // 因果推理过程
  extractedTags: string[];              // 提取的标签
  searchText: string;                   // 用于向量搜索的文本
  chatResponse?: string;                // 如果是闲聊，返回回复
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
  // 图片搜索调试信息
  imageSearch?: {
    vectorDimension: number;          // 向量维度
    vectorSample: number[];           // 向量前 5 个值（用于验证）
    searchModel: string;              // 使用的搜索模型
    dbModel: string;                  // 数据库中存储的模型
    rawResultCount: number;           // 原始返回数量
    minSimilarityThreshold: number;   // 最低相似度阈值
    topSimilarities?: number[];       // 前几个相似度分数
    error?: string;                   // 错误信息
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
// 配置加载
// ============================================================================

/** 搜索配置缓存 */
let configCache: Record<string, unknown> | null = null;
let configCacheTime = 0;
const CONFIG_CACHE_TTL = 60 * 1000; // 1 分钟缓存

/**
 * 从数据库加载搜索配置
 * 带缓存，避免每次请求都查询数据库
 */
async function loadSearchConfig(): Promise<Record<string, unknown>> {
  const now = Date.now();
  if (configCache && now - configCacheTime < CONFIG_CACHE_TTL) {
    return configCache;
  }

  try {
    const { data, error } = await supabase
      .from('gg_search_config')
      .select('config_key, config_value');

    if (error) {
      console.error('加载搜索配置失败:', error);
      // 返回默认配置
      return getDefaultConfig();
    }

    const config: Record<string, unknown> = {};
    for (const item of data || []) {
      config[item.config_key] = item.config_value;
    }

    configCache = config;
    configCacheTime = now;
    return config;
  } catch (err) {
    console.error('加载搜索配置异常:', err);
    return getDefaultConfig();
  }
}

/**
 * 获取默认配置
 */
function getDefaultConfig(): Record<string, unknown> {
  return {
    vector_weight: 0.9,
    tag_weight: 0.1,
    rrf_k: 50,
    match_count: 50,
    min_similarity: 0.3,
    llm_temperature: 0.3,
  };
}

/**
 * 获取配置值
 */
function getConfigValue(config: Record<string, unknown>, key: string, defaultValue: number): number {
  const value = config[key];
  if (value === undefined || value === null) return defaultValue;
  if (typeof value === 'number') return value;
  if (typeof value === 'string') {
    const parsed = parseFloat(value);
    return isNaN(parsed) ? defaultValue : parsed;
  }
  return defaultValue;
}

// ============================================================================
// 工具函数
// ============================================================================

/**
 * 使用 APU 三维度理论解析用户意图
 * 从数据库加载规则，构建 Prompt，调用 LLM
 * 
 * APU 维度:
 * - Attribute: 用户想要什么物理特征
 * - Performance: 用户关心什么性能
 * - Use: 用户在什么场景使用
 */
async function parseUserIntent(query: string): Promise<LLMParseResult> {
  try {
    // 构建 APU Prompt（包含从数据库加载的规则）
    const apuPrompt = await buildSearchPrompt(supabase, query);
    
    const response = await openrouter.chat.completions.create({
      model: 'google/gemini-2.5-flash',
      messages: [
        {
          role: 'user',
          content: apuPrompt
        }
      ],
      temperature: 0.3,
      max_tokens: 800,
    });

    const content = response.choices[0]?.message?.content || '';
    
    // 解析 JSON 响应
    const jsonMatch = content.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      const parsed = JSON.parse(jsonMatch[0]);
      return {
        isSearch: parsed.isSearch ?? true,
        primaryDimension: parsed.primary_dimension,
        intentAnalysis: parsed.intent_analysis,
        causalReasoning: parsed.causal_reasoning,
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
    console.error('APU 意图解析失败:', error);
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
 * 使用 Replicate TinyCLIP 生成图片向量 (512维)
 * 
 * 参考: https://replicate.com/negu63/tinyclip/api
 * 
 * TinyCLIP 输入参数:
 * - url: 图片 URL
 * - image_base64: Base64 编码的图片 (不含 data: 前缀)
 * - text: 文本输入
 * 
 * TinyCLIP 输出格式:
 * - 图片输入: { "image_vector": [...] } (512 维)
 * - 文本输入: { "text_vector": [...] } (512 维)
 * 
 * 优势:
 * - 512 维向量，与数据库中的图片向量维度匹配
 * - 响应速度快
 */

// TinyCLIP 模型版本 ID
const TINYCLIP_VERSION = 'f1905b91cb2d384a76764d14189c76b15daea3588197c67fe29042c7f386699c';

// 超时设置 (毫秒)
const TINYCLIP_TIMEOUT_MS = 30000;

// 最大轮询次数
const TINYCLIP_MAX_POLLS = 30;

async function generateImageEmbedding(imageBase64: string): Promise<number[]> {
  const startTime = Date.now();
  
  // 去除 data URL 前缀，TinyCLIP 需要纯 Base64 字符串
  const pureBase64 = imageBase64.startsWith('data:') 
    ? imageBase64.split(',')[1] 
    : imageBase64;
  
  // 创建预测请求
  const response = await fetch('https://api.replicate.com/v1/predictions', {
    method: 'POST',
    headers: {
      'Authorization': `Token ${process.env.REPLICATE_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      version: TINYCLIP_VERSION,
      input: {
        // TinyCLIP 使用 image_base64 参数接收 Base64 编码的图片
        image_base64: pureBase64,
      },
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(`TinyCLIP API 创建预测失败: ${JSON.stringify(error)}`);
  }

  let prediction = await response.json();
  console.log('TinyCLIP 预测 ID:', prediction.id, '状态:', prediction.status);
  
  // 轮询等待预测完成，带超时控制
  let pollCount = 0;
  while (
    prediction.status !== 'succeeded' && 
    prediction.status !== 'failed' && 
    pollCount < TINYCLIP_MAX_POLLS
  ) {
    // 检查是否超时
    if (Date.now() - startTime > TINYCLIP_TIMEOUT_MS) {
      throw new Error(`TinyCLIP 预测超时 (${TINYCLIP_TIMEOUT_MS}ms)`);
    }
    
    await new Promise(resolve => setTimeout(resolve, 1000));
    pollCount++;
    
    const pollResponse = await fetch(prediction.urls.get, {
      headers: {
        'Authorization': `Token ${process.env.REPLICATE_API_KEY}`,
      },
    });
    prediction = await pollResponse.json();
    console.log(`TinyCLIP 轮询 ${pollCount}: ${prediction.status}`);
  }

  // 检查最终状态
  if (prediction.status === 'failed') {
    throw new Error(`TinyCLIP 预测失败: ${prediction.error}`);
  }
  
  if (prediction.status !== 'succeeded') {
    throw new Error(`TinyCLIP 预测未完成，状态: ${prediction.status}`);
  }

  const duration = Date.now() - startTime;
  console.log(`TinyCLIP 图片向量生成完成，耗时: ${duration}ms`);

  // 解析返回的向量
  const output = prediction.output;
  
  // TinyCLIP 图片输入返回格式: { "image_vector": [...] }
  if (output && output.image_vector && Array.isArray(output.image_vector)) {
    const vector = output.image_vector;
    console.log(`TinyCLIP 返回 image_vector 维度: ${vector.length}`);
    return vector;
  }
  
  // 兜底: 检查其他可能的字段名
  if (output && output.embedding && Array.isArray(output.embedding)) {
    console.log(`TinyCLIP 返回 embedding 维度: ${output.embedding.length}`);
    return output.embedding;
  }
  
  console.error('TinyCLIP 返回格式异常:', JSON.stringify(output));
  throw new Error(`TinyCLIP 返回格式异常: ${JSON.stringify(output)}`);
}

/**
 * 将数组转换为 pgvector 格式字符串
 */
function toVectorString(arr: number[]): string {
  return `[${arr.join(',')}]`;
}

/**
 * 执行文本混合搜索
 * 权重从数据库配置读取
 */
async function hybridSearchByText(
  embedding: number[],
  tags: string[],
  matchCount: number = 50,
  config?: Record<string, unknown>
): Promise<SearchResult[]> {
  // 加载配置
  const searchConfig = config || await loadSearchConfig();
  
  // 从配置获取权重
  const vectorWeight = getConfigValue(searchConfig, 'vector_weight', 0.9);
  const tagWeight = getConfigValue(searchConfig, 'tag_weight', 0.1);
  const rrfK = getConfigValue(searchConfig, 'rrf_k', 50);
  
  console.log(`搜索权重: vector=${vectorWeight}, tag=${tagWeight}, rrf_k=${rrfK}`);
  
  // pgvector 需要向量格式为 "[...]" 字符串
  const { data, error } = await supabase.rpc('hybrid_search_products', {
    query_embedding: toVectorString(embedding),
    tag_values: tags,
    match_count: matchCount,
    vector_weight: vectorWeight,
    tag_weight: tagWeight,
    rrf_k: rrfK,
  });

  if (error) {
    console.error('混合搜索失败:', error);
    throw error;
  }

  return data || [];
}

/**
 * 执行图片搜索
 * 
 * 注意：当前数据库中的向量是用 openai/clip-vit-base-patch32 生成的
 * 而搜索使用的是 TinyCLIP 模型，两者向量空间不完全兼容
 * 需要降低相似度阈值才能获取结果
 */
async function searchByImage(
  imageEmbedding: number[],
  textEmbedding?: number[],
  tags?: string[],
  matchCount: number = 50
): Promise<{ results: SearchResult[]; debugInfo: { rawCount: number; topSimilarities: number[] } }> {
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

  const results = data || [];
  
  // 提取相似度调试信息
  const topSimilarities = results.slice(0, 5).map((r: SearchResult) => r.image_score || 0);
  
  console.log('图片搜索结果数量:', results.length);
  console.log('前 5 个相似度:', topSimilarities);

  return {
    results,
    debugInfo: {
      rawCount: results.length,
      topSimilarities,
    }
  };
}

/**
 * 直接使用底层函数搜索图片（绕过相似度阈值限制）
 * 用于调试和验证向量兼容性
 */
async function searchByImageDirect(
  imageEmbedding: number[],
  matchCount: number = 50
): Promise<{ results: SearchResult[]; debugInfo: { rawCount: number; topSimilarities: number[] } }> {
  // 直接调用底层搜索函数，设置最低阈值为 0
  const { data, error } = await supabase.rpc('search_products_by_image_vector', {
    query_embedding: toVectorString(imageEmbedding),
    match_count: matchCount,
    min_similarity: 0.0,  // 设置为 0，获取所有结果
  });

  if (error) {
    console.error('直接图片搜索失败:', error);
    throw error;
  }

  const results = data || [];
  const topSimilarities = results.slice(0, 10).map((r: { similarity: number }) => r.similarity);
  
  console.log('直接搜索结果数量:', results.length);
  console.log('前 10 个相似度:', topSimilarities);

  // 转换为标准格式
  const standardResults: SearchResult[] = results.map((r: {
    product_id: number;
    item_id: number;
    item_name: string;
    price_yuan: number;
    main_image_url: string;
    matched_image_url: string;
    similarity: number;
  }) => ({
    product_id: r.product_id,
    item_id: r.item_id,
    item_name: r.item_name,
    price_yuan: r.price_yuan,
    main_image_url: r.main_image_url,
    matched_image_url: r.matched_image_url,
    vector_score: 0,
    tag_score: 0,
    image_score: r.similarity,
    matched_tags: [],
    final_score: r.similarity,
  }));

  return {
    results: standardResults,
    debugInfo: {
      rawCount: results.length,
      topSimilarities,
    }
  };
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
    // 加载搜索配置
    const searchConfig = await loadSearchConfig();
    const vectorWeight = getConfigValue(searchConfig, 'vector_weight', 0.9);
    const tagWeight = getConfigValue(searchConfig, 'tag_weight', 0.1);
    const rrfK = getConfigValue(searchConfig, 'rrf_k', 50);

    const debugInfo: DebugInfo = {
      input: {
        rawQuery: query || '[图片搜索]',
      },
      params: {
        vectorWeight,         // 从数据库配置读取
        tagWeight,            // 从数据库配置读取
        rrf_k: rrfK,          // 从数据库配置读取
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

      // Step 3: 混合搜索 (使用数据库配置)
      results = await hybridSearchByText(embedding, parseResult.extractedTags, matchCount, searchConfig);
    }
    // 情况 2: 只有图片
    // 使用 TinyCLIP 生成 512 维图片向量
    // 注意：数据库中的向量是 openai/clip-vit-base-patch32 生成的
    // TinyCLIP 与 clip-vit-base-patch32 的向量空间可能不完全兼容
    else if (imageBase64 && !query) {
      console.log('图片搜索：使用 TinyCLIP 生成图片向量进行搜索');
      
      // Step 1: 生成图片向量 (TinyCLIP 512维)
      const imageEmbedding = await generateImageEmbedding(imageBase64);
      console.log('图片向量维度:', imageEmbedding.length);
      console.log('图片向量前 5 个值:', imageEmbedding.slice(0, 5));
      
      debugInfo.input.rawQuery = '[图片搜索]';
      debugInfo.input.searchText = '[图片向量搜索]';
      
      // 添加图片搜索调试信息
      debugInfo.imageSearch = {
        vectorDimension: imageEmbedding.length,
        vectorSample: imageEmbedding.slice(0, 5),
        searchModel: 'TinyCLIP (negu63/tinyclip)',
        dbModel: 'openai/clip-vit-base-patch32',
        rawResultCount: 0,
        minSimilarityThreshold: 0.0,  // 使用 0 阈值进行调试
        topSimilarities: [],
      };
      
      // Step 2: 使用直接搜索函数（绕过阈值限制，用于调试）
      try {
        const searchResult = await searchByImageDirect(imageEmbedding, matchCount);
        results = searchResult.results;
        debugInfo.imageSearch.rawResultCount = searchResult.debugInfo.rawCount;
        debugInfo.imageSearch.topSimilarities = searchResult.debugInfo.topSimilarities;
      } catch (searchError) {
        console.error('图片搜索出错:', searchError);
        debugInfo.imageSearch.error = searchError instanceof Error ? searchError.message : '未知错误';
        results = [];
      }
      
      // 更新 debug 参数
      debugInfo.params.vectorWeight = 1.0;  // 纯图片搜索
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

      // 添加图片搜索调试信息
      debugInfo.imageSearch = {
        vectorDimension: imageEmbedding.length,
        vectorSample: imageEmbedding.slice(0, 5),
        searchModel: 'TinyCLIP (negu63/tinyclip)',
        dbModel: 'openai/clip-vit-base-patch32',
        rawResultCount: 0,
        minSimilarityThreshold: 0.2,
        topSimilarities: [],
      };

      // Step 3: 图片 + 文本混合搜索
      const searchResult = await searchByImage(
        imageEmbedding,
        textEmbedding,
        parseResult.extractedTags,
        matchCount
      );
      results = searchResult.results;
      debugInfo.imageSearch.rawResultCount = searchResult.debugInfo.rawCount;
      debugInfo.imageSearch.topSimilarities = searchResult.debugInfo.topSimilarities;

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

