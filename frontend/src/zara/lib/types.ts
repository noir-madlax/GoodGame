/**
 * ZARA 商品搜索模块 - 类型定义
 * 
 * 使用页面: zara/pages/* 所有页面
 * 功能: 定义商品、图片、标签、分类等数据结构
 */

// ==================== 商品相关类型 ====================

/**
 * 商品信息
 * 对应数据库表: gg_taobao_products
 */
export interface Product {
  id: number;                    // 数据库 ID
  item_id: number;               // 淘宝商品 ID
  item_name: string;             // 商品名称
  shop_name: string | null;      // 店铺名称
  price_yuan: number;            // 当前价格
  discount_price_yuan: number | null;  // 折扣价
  order_count: string | null;    // 销量 (如 "1000+")
  item_loc: string | null;       // 发货地
  created_at: string;            // 创建时间
  updated_at: string;            // 更新时间
}

/**
 * 商品图片信息
 * 对应数据库表: gg_taobao_product_images
 */
export interface ProductImage {
  id: number;
  product_id: number;
  item_id: number;
  image_type: 'main' | 'sub';    // 主图或副图
  image_index: number;           // 图片序号
  image_url: string;             // 原始图片 URL
  storage_path: string | null;   // Supabase Storage 路径
}

/**
 * 商品卡片展示数据 (包含主图)
 * 用于商品列表展示
 */
export interface ProductWithImage extends Product {
  main_image_url: string | null;  // 主图 URL
  storage_url: string | null;     // Storage 公开 URL
  tags?: string[];                // 标签列表
}

// ==================== 标签相关类型 ====================

/**
 * 商品标签
 * 对应数据库表: gg_taobao_product_tags
 */
export interface ProductTag {
  id: number;
  product_id: number;
  tag_type: TagType;             // 标签类型
  tag_value: string;             // 标签值
}

/**
 * 标签类型枚举
 */
export type TagType = 
  | 'gender'      // 性别: 女装/男装/童装
  | 'season'      // 季节: 春季/夏季/秋季/冬季
  | 'year'        // 年份: 2025/2024
  | 'category'    // 品类: T恤/连衣裙/外套
  | 'style'       // 风格: 修身/宽松/休闲
  | 'material'    // 材质: 棉/羊毛/皮革
  | 'feature'     // 特征: 长袖/短袖/圆领
  | 'series';     // 系列: 新款/TRF/ZW

/**
 * 标签统计信息 (用于筛选器展示)
 */
export interface TagStats {
  tag_type: TagType;
  tag_value: string;
  count: number;
}

/**
 * 标签分组 (用于筛选器展示)
 */
export interface TagGroup {
  type: TagType;
  label: string;                 // 中文显示名称
  tags: TagStats[];
}

// ==================== 分类相关类型 ====================

/**
 * 一级分类
 * 对应数据库表: gg_zara_category_l1
 */
export interface CategoryL1 {
  id: number;
  name: string;
  sort_order: number;
}

/**
 * 二级分类
 * 对应数据库表: gg_zara_category_l2
 */
export interface CategoryL2 {
  id: number;
  l1_id: number;
  name: string;
  is_new: boolean;
  is_hot: boolean;
  sort_order: number;
}

/**
 * 三级分类
 * 对应数据库表: gg_zara_category_l3
 */
export interface CategoryL3 {
  id: number;
  l2_id: number;
  name: string;
  sort_order: number;
}

// ==================== 搜索相关类型 ====================

/**
 * 搜索请求参数
 */
export interface SearchParams {
  query?: string;                // 文字搜索词
  imageFile?: File;              // 图片文件 (图片搜索)
  categoryL1?: number;           // 一级分类 ID
  categoryL2?: number;           // 二级分类 ID
  tags?: Record<TagType, string[]>;  // 标签筛选
  sortBy?: SortOption;           // 排序方式
  page?: number;                 // 页码
  pageSize?: number;             // 每页数量
}

/**
 * 排序选项
 */
export type SortOption = 
  | 'relevance'      // 综合 (相似度)
  | 'price_asc'      // 价格从低到高
  | 'price_desc'     // 价格从高到低
  | 'sales_desc';    // 销量从高到低

/**
 * 搜索结果
 */
export interface SearchResult {
  products: ProductWithImage[];  // 商品列表
  total: number;                 // 总数量
  page: number;                  // 当前页码
  pageSize: number;              // 每页数量
  totalPages: number;            // 总页数
}

/**
 * AI 搜索消息
 */
export interface SearchMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  imageUrl?: string;             // 用户上传的图片预览
  timestamp: Date;
}

