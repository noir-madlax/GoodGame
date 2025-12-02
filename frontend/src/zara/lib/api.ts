/**
 * ZARA 商品搜索模块 - API 调用函数
 * 
 * 使用页面: zara/pages/* 所有页面
 * 功能: 封装 Supabase 数据库查询和搜索功能
 */

import { supabase } from '@/lib/supabase';
import type {
  Product,
  ProductWithImage,
  TagStats,
  TagGroup,
  CategoryL1,
  CategoryL2,
  SearchParams,
  SearchResult,
  TagType,
} from './types';

// Supabase Storage 公开 URL 前缀
const STORAGE_URL_PREFIX = process.env.NEXT_PUBLIC_SUPABASE_URL 
  ? `${process.env.NEXT_PUBLIC_SUPABASE_URL}/storage/v1/object/public/`
  : '';

/**
 * 获取图片的公开 URL
 * 将 storage_path 转换为可访问的公开 URL
 */
export function getImagePublicUrl(storagePath: string | null): string | null {
  if (!storagePath || !STORAGE_URL_PREFIX) return null;
  return `${STORAGE_URL_PREFIX}${storagePath}`;
}

// ==================== 商品查询 ====================

/**
 * 获取商品列表 (带主图)
 * 
 * @param page 页码 (从 1 开始)
 * @param pageSize 每页数量
 * @param filters 筛选条件
 */
export async function getProducts(
  page: number = 1,
  pageSize: number = 20,
  filters?: {
    tags?: Record<TagType, string[]>;
  }
): Promise<SearchResult> {
  if (!supabase) {
    return { products: [], total: 0, page, pageSize, totalPages: 0 };
  }

  const offset = (page - 1) * pageSize;

  // 基础查询
  let query = supabase
    .from('gg_taobao_products')
    .select(`
      *,
      gg_taobao_product_images!inner (
        image_url,
        storage_path
      )
    `, { count: 'exact' })
    .eq('gg_taobao_product_images.image_type', 'main')
    .range(offset, offset + pageSize - 1)
    .order('id', { ascending: true });

  const { data, error, count } = await query;

  if (error) {
    console.error('获取商品列表失败:', error);
    return { products: [], total: 0, page, pageSize, totalPages: 0 };
  }

  // 转换数据格式
  const products: ProductWithImage[] = (data || []).map((item: any) => {
    const image = item.gg_taobao_product_images?.[0];
    return {
      ...item,
      gg_taobao_product_images: undefined,
      main_image_url: image?.image_url || null,
      storage_url: getImagePublicUrl(image?.storage_path),
    };
  });

  const total = count || 0;

  return {
    products,
    total,
    page,
    pageSize,
    totalPages: Math.ceil(total / pageSize),
  };
}

/**
 * 获取商品总数
 */
export async function getProductCount(): Promise<number> {
  if (!supabase) return 0;

  const { count, error } = await supabase
    .from('gg_taobao_products')
    .select('*', { count: 'exact', head: true });

  if (error) {
    console.error('获取商品总数失败:', error);
    return 0;
  }

  return count || 0;
}

// ==================== 标签查询 ====================

/**
 * 标签类型中文名称映射
 */
const TAG_TYPE_LABELS: Record<TagType, string> = {
  gender: '性别',
  season: '季节',
  year: '年份',
  category: '品类',
  style: '风格',
  material: '材质',
  feature: '特征',
  series: '系列',
};

/**
 * 获取标签统计 (按类型分组)
 * 用于筛选器展示
 */
export async function getTagStats(): Promise<TagGroup[]> {
  if (!supabase) return [];

  const { data, error } = await supabase
    .from('gg_taobao_product_tags')
    .select('tag_type, tag_value');

  if (error) {
    console.error('获取标签统计失败:', error);
    return [];
  }

  // 统计每个标签的数量
  const statsMap: Record<string, Record<string, number>> = {};
  
  for (const row of data || []) {
    const { tag_type, tag_value } = row;
    if (!statsMap[tag_type]) {
      statsMap[tag_type] = {};
    }
    statsMap[tag_type][tag_value] = (statsMap[tag_type][tag_value] || 0) + 1;
  }

  // 转换为 TagGroup 格式
  const tagGroups: TagGroup[] = [];
  const typeOrder: TagType[] = ['gender', 'season', 'category', 'style', 'material', 'feature', 'series'];

  for (const type of typeOrder) {
    if (statsMap[type]) {
      const tags: TagStats[] = Object.entries(statsMap[type])
        .map(([tag_value, count]) => ({
          tag_type: type,
          tag_value,
          count,
        }))
        .sort((a, b) => b.count - a.count);

      tagGroups.push({
        type,
        label: TAG_TYPE_LABELS[type],
        tags,
      });
    }
  }

  return tagGroups;
}

// ==================== 分类查询 ====================

/**
 * 获取一级分类列表
 */
export async function getCategoriesL1(): Promise<CategoryL1[]> {
  if (!supabase) return [];

  const { data, error } = await supabase
    .from('gg_zara_category_l1')
    .select('*')
    .order('sort_order', { ascending: true });

  if (error) {
    console.error('获取一级分类失败:', error);
    return [];
  }

  return data || [];
}

/**
 * 获取二级分类列表
 * 
 * @param l1Id 一级分类 ID (可选，不传则获取全部)
 */
export async function getCategoriesL2(l1Id?: number): Promise<CategoryL2[]> {
  if (!supabase) return [];

  let query = supabase
    .from('gg_zara_category_l2')
    .select('*')
    .order('sort_order', { ascending: true });

  if (l1Id) {
    query = query.eq('l1_id', l1Id);
  }

  const { data, error } = await query;

  if (error) {
    console.error('获取二级分类失败:', error);
    return [];
  }

  return data || [];
}

// ==================== 搜索功能 ====================

/**
 * AI 搜索 API 响应类型
 */
export interface AISearchResponse {
  success: boolean;
  results: AISearchResult[];
  debugInfo: AISearchDebugInfo;
  totalCount: number;
  error?: string;
  message?: string;
}

/**
 * AI 搜索结果项
 */
export interface AISearchResult {
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

/**
 * AI 搜索 Debug 结果项
 */
export interface AISearchDebugResultItem {
  rank: number;
  productId: number;
  productName: string;
  vectorScore: number;
  tagScore: number;
  finalScore: number;
  matchedTags: string[];
}

/**
 * AI 搜索 Debug 信息
 */
export interface AISearchDebugInfo {
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
  results?: AISearchDebugResultItem[];       // 前 10 个结果
  bottomResults?: AISearchDebugResultItem[]; // 后 10 个结果
}

/**
 * AI 智能搜索 (调用后端 API)
 * 支持文本搜索、图片搜索、混合搜索
 * 
 * @param query 搜索文本 (可选)
 * @param imageBase64 图片 Base64 (可选)
 * @param matchCount 返回数量
 */
export async function aiSearch(
  query?: string,
  imageBase64?: string,
  matchCount: number = 50
): Promise<AISearchResponse> {
  try {
    const response = await fetch('/api/zara/search', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query,
        imageBase64,
        matchCount,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      console.error('AI 搜索 API 错误:', data);
      return {
        success: false,
        results: [],
        debugInfo: {
          input: { rawQuery: query || '[图片搜索]' },
          params: { vectorWeight: 0.75, tagWeight: 0.25, rrf_k: 50 },
        },
        totalCount: 0,
        error: data.error || '搜索失败',
        message: data.message,
      };
    }

    return data;
  } catch (error) {
    console.error('AI 搜索请求失败:', error);
    return {
      success: false,
      results: [],
      debugInfo: {
        input: { rawQuery: query || '[图片搜索]' },
        params: { vectorWeight: 0.75, tagWeight: 0.25, rrf_k: 50 },
      },
      totalCount: 0,
      error: '网络请求失败',
      message: error instanceof Error ? error.message : '未知错误',
    };
  }
}

/**
 * 将 AI 搜索结果转换为 ProductWithImage 格式
 * 使用 Supabase Storage URL 替代原始阿里 CDN URL
 */
export function convertAIResultToProduct(result: AISearchResult): ProductWithImage {
  // 生成 Supabase Storage URL
  // 格式: product-images/{item_id}/main.jpg
  const storageUrl = getImagePublicUrl(`product-images/${result.item_id}/main.jpg`);
  
  return {
    // Product 基础字段
    id: result.product_id,
    item_id: result.item_id,
    item_name: result.item_name,
    price_yuan: result.price_yuan,
    shop_name: null,
    discount_price_yuan: null,
    order_count: null,
    item_loc: null,
    created_at: '',
    updated_at: '',
    // ProductWithImage 扩展字段
    main_image_url: result.main_image_url, // 保留原始 URL 作为备用
    storage_url: storageUrl, // 使用 Supabase Storage URL
  };
}

/**
 * 文本向量搜索 (旧版，使用模糊搜索作为备选)
 * 
 * @deprecated 请使用 aiSearch 函数
 * @param queryText 搜索文本
 * @param limit 返回数量
 */
export async function searchByText(
  queryText: string,
  limit: number = 20
): Promise<ProductWithImage[]> {
  if (!supabase || !queryText.trim()) return [];

  // 使用模糊搜索作为备选方案
  const { data, error } = await supabase
    .from('gg_taobao_products')
    .select(`
      *,
      gg_taobao_product_images!inner (
        image_url,
        storage_path
      )
    `)
    .eq('gg_taobao_product_images.image_type', 'main')
    .ilike('item_name', `%${queryText}%`)
    .limit(limit);

  if (error) {
    console.error('文本搜索失败:', error);
    return [];
  }

  return (data || []).map((item: any) => {
    const image = item.gg_taobao_product_images?.[0];
    return {
      ...item,
      gg_taobao_product_images: undefined,
      main_image_url: image?.image_url || null,
      storage_url: getImagePublicUrl(image?.storage_path),
    };
  });
}

/**
 * 综合搜索
 * 支持文本和标签筛选
 */
export async function search(params: SearchParams): Promise<SearchResult> {
  const {
    query,
    tags,
    sortBy = 'relevance',
    page = 1,
    pageSize = 20,
  } = params;

  // 如果有搜索词，使用文本搜索
  if (query && query.trim()) {
    const products = await searchByText(query, pageSize);
    return {
      products,
      total: products.length,
      page: 1,
      pageSize,
      totalPages: 1,
    };
  }

  // 否则使用普通列表查询
  return getProducts(page, pageSize, { tags });
}

