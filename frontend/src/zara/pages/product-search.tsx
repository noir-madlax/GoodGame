/**
 * 商品搜索页面 - Liquid Glass 风格
 * 
 * 路由: /zara/products
 * 功能: ZARA 商品搜索主页面
 * 
 * 设计参考: Apple 2025 Liquid Glass Design
 */

'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { cn } from '@/lib/utils';
import SearchTrigger from '../components/search-trigger';
import SearchModal, { SearchDebugInfo } from '../components/search-modal';
import ProductGrid from '../components/product-grid';
import TagFilter from '../components/tag-filter';
import Pagination from '../components/pagination';
import { 
  getProducts, 
  getTagStats, 
  aiSearch,
  convertAIResultToProduct,
} from '../lib/api';
import type { 
  ProductWithImage, 
  TagGroup, 
  TagType,
} from '../lib/types';
import { Package, Filter, X, Bug } from 'lucide-react';

/**
 * 商品搜索页面
 */
export default function ProductSearchPage() {
  // 搜索 Modal 状态
  const [searchModalOpen, setSearchModalOpen] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Debug 状态
  const [showDebug, setShowDebug] = useState(false);
  const [debugInfo, setDebugInfo] = useState<SearchDebugInfo | null>(null);

  // 商品数据
  const [products, setProducts] = useState<ProductWithImage[]>([]);
  const [loading, setLoading] = useState(true);
  const [totalCount, setTotalCount] = useState(0);

  // 分页
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const pageSize = 20;

  // 标签筛选
  const [tagGroups, setTagGroups] = useState<TagGroup[]>([]);
  const [selectedTags, setSelectedTags] = useState<Record<TagType, string[]>>({
    gender: [],
    season: [],
    year: [],
    category: [],
    style: [],
    material: [],
    feature: [],
    series: [],
  });
  const [showFilters, setShowFilters] = useState(false);

  /**
   * 加载商品列表
   */
  const loadProducts = useCallback(async (page: number = 1) => {
    setLoading(true);
    try {
      const result = await getProducts(page, pageSize, { tags: selectedTags });
      setProducts(result.products);
      setTotalPages(result.totalPages);
      setTotalCount(result.total);
    } catch (error) {
      console.error('加载商品失败:', error);
    } finally {
      setLoading(false);
    }
  }, [selectedTags]);

  /**
   * 加载标签统计
   */
  const loadTagStats = useCallback(async () => {
    try {
      const stats = await getTagStats();
      setTagGroups(stats);
    } catch (error) {
      console.error('加载标签失败:', error);
    }
  }, []);

  /**
   * 初始加载
   */
  useEffect(() => {
    loadProducts(1);
    loadTagStats();
  }, []);

  /**
   * 标签变化时重新加载
   */
  useEffect(() => {
    if (!searchQuery) {
      loadProducts(1);
      setCurrentPage(1);
    }
  }, [selectedTags]);

  /**
   * 将图片文件转换为 Base64
   */
  const fileToBase64 = useCallback((file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = reader.result as string;
        resolve(result);
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }, []);

  /**
   * 处理搜索 - 使用 AI 智能搜索 API
   */
  const handleSearch = useCallback(async (query: string, imageFile?: File) => {
    setIsSearching(true);
    setSearchQuery(query || (imageFile ? `[图片] ${imageFile.name}` : ''));
    setSearchModalOpen(false);

    try {
      // 准备图片 Base64 (如果有)
      let imageBase64: string | undefined;
      if (imageFile) {
        imageBase64 = await fileToBase64(imageFile);
      }

      // 调用 AI 搜索 API
      const response = await aiSearch(query || undefined, imageBase64, 50);

      if (response.success) {
        // 转换搜索结果为 ProductWithImage 格式
        const productResults = response.results.map(convertAIResultToProduct);
        setProducts(productResults);
        setTotalCount(response.totalCount);
        setTotalPages(1);
        setCurrentPage(1);

        // 设置 Debug 信息
        setDebugInfo(response.debugInfo);
      } else {
        // 搜索失败
        console.error('AI 搜索失败:', response.error, response.message);
        setProducts([]);
        setTotalCount(0);
        setDebugInfo({
          input: {
            rawQuery: query || `[图片] ${imageFile?.name || '未知'}`,
          },
          params: {
            vectorWeight: 0.75,
            tagWeight: 0.25,
            rrf_k: 50,
          },
        });
      }
    } catch (error) {
      console.error('搜索失败:', error);
      setProducts([]);
      setTotalCount(0);
      setDebugInfo(null);
    } finally {
      setIsSearching(false);
    }
  }, [fileToBase64]);

  /**
   * 清除搜索
   */
  const handleClearSearch = useCallback(() => {
    setSearchQuery('');
    setDebugInfo(null);
    loadProducts(1);
    setCurrentPage(1);
  }, [loadProducts]);

  /**
   * 处理标签变化
   */
  const handleTagChange = useCallback((type: TagType, value: string, selected: boolean) => {
    setSelectedTags((prev) => {
      const currentTags = prev[type] || [];
      if (selected) {
        return { ...prev, [type]: [...currentTags, value] };
      } else {
        return { ...prev, [type]: currentTags.filter((t) => t !== value) };
      }
    });
  }, []);

  /**
   * 清除所有筛选
   */
  const handleClearFilters = useCallback(() => {
    setSelectedTags({
      gender: [],
      season: [],
      year: [],
      category: [],
      style: [],
      material: [],
      feature: [],
      series: [],
    });
  }, []);

  /**
   * 处理分页
   */
  const handlePageChange = useCallback((page: number) => {
    setCurrentPage(page);
    loadProducts(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [loadProducts]);

  /**
   * 计算已选标签数量
   */
  const selectedTagCount = Object.values(selectedTags).reduce(
    (sum, tags) => sum + tags.length,
    0
  );

  return (
    <div className="min-h-screen">
      {/* 顶部搜索区域 */}
      <div className="mb-6">
        {/* 搜索栏 */}
        <SearchTrigger onClick={() => setSearchModalOpen(true)} />

        {/* 当前搜索状态 */}
        {searchQuery && (
          <div className="flex items-center justify-center gap-2 mt-4">
            <span 
              className="text-sm"
              style={{ color: 'rgba(255, 255, 255, 0.7)' }}
            >
              搜索结果：
            </span>
            <span 
              className="px-3 py-1 rounded-full text-sm"
              style={{
                background: 'rgba(255, 255, 255, 0.25)',
                color: 'white',
                border: '0.5px solid rgba(255, 255, 255, 0.3)',
              }}
            >
              {searchQuery}
            </span>
            <button
              onClick={handleClearSearch}
              className="p-1 rounded-full transition-colors"
              style={{
                background: 'rgba(255, 255, 255, 0.15)',
              }}
            >
              <X className="w-4 h-4" style={{ color: 'rgba(255, 255, 255, 0.7)' }} />
            </button>
          </div>
        )}
      </div>

      {/* 工具栏 */}
      <div className="flex items-center justify-between mb-6">
        {/* 左侧：商品数量 */}
        <div 
          className="flex items-center gap-2"
          style={{ color: 'rgba(255, 255, 255, 0.8)' }}
        >
          <Package className="w-5 h-5" />
          <span>共 {totalCount} 件商品</span>
        </div>

        {/* 右侧：筛选和 Debug 按钮 */}
        <div className="flex items-center gap-2">
          {/* Debug 按钮 */}
          <button
            onClick={() => setShowDebug(!showDebug)}
            className={cn(
              'flex items-center gap-2 px-3 py-2 rounded-xl',
              'transition-all duration-300'
            )}
            style={{
              background: showDebug
                ? 'rgba(139, 92, 246, 0.3)'
                : 'rgba(255, 255, 255, 0.1)',
              border: showDebug
                ? '0.5px solid rgba(139, 92, 246, 0.5)'
                : '0.5px solid rgba(255, 255, 255, 0.2)',
              color: showDebug ? 'rgb(196, 181, 253)' : 'rgba(255, 255, 255, 0.6)',
              backdropFilter: 'blur(10px)',
            }}
            title="显示/隐藏 Debug 信息"
          >
            <Bug className="w-4 h-4" />
          </button>

          {/* 筛选按钮 */}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-xl',
              'transition-all duration-300'
            )}
            style={{
              background: showFilters
                ? 'rgba(255, 255, 255, 0.3)'
                : 'rgba(255, 255, 255, 0.15)',
              border: '0.5px solid rgba(255, 255, 255, 0.3)',
              color: 'white',
              backdropFilter: 'blur(10px)',
            }}
          >
            <Filter className="w-4 h-4" />
            筛选
            {selectedTagCount > 0 && (
              <span 
                className="px-1.5 py-0.5 text-xs rounded-full"
                style={{
                  background: 'rgba(255, 255, 255, 0.25)',
                }}
              >
                {selectedTagCount}
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Debug 信息面板 (页面内) */}
      {showDebug && debugInfo && (
        <div 
          className="mb-6 rounded-2xl overflow-hidden"
          style={{
            background: 'rgba(17, 24, 39, 0.8)',
            backdropFilter: 'blur(20px)',
            border: '0.5px solid rgba(139, 92, 246, 0.3)',
          }}
        >
          <div className="p-4 space-y-3 text-xs text-white">
            <div className="flex items-center justify-between">
              <h4 className="font-semibold text-violet-400 flex items-center gap-2">
                <Bug className="w-4 h-4" />
                搜索 Debug 信息
              </h4>
              <button
                onClick={() => setShowDebug(false)}
                className="text-gray-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* 输入解析 */}
            {debugInfo.input && (
              <div className="space-y-1">
                <p className="text-gray-400">输入解析:</p>
                <div 
                  className="rounded-lg p-2 space-y-1"
                  style={{ background: 'rgba(255, 255, 255, 0.05)' }}
                >
                  <p>原始输入: <span className="text-green-400">{debugInfo.input.rawQuery}</span></p>
                  {/* 品类过滤 - 最高优先级 */}
                  {debugInfo.input.extractedCategory && (
                    <p className="flex items-center gap-2">
                      <span className="px-2 py-0.5 bg-red-500/30 text-red-300 rounded text-[10px]">🎯 品类过滤</span>
                      <span className="text-red-400 font-bold">{debugInfo.input.extractedCategory}</span>
                    </p>
                  )}
                  {debugInfo.input.searchText && (
                    <p>增强搜索文本: <span className="text-cyan-400">{debugInfo.input.searchText}</span></p>
                  )}
                </div>
              </div>
            )}

            {/* 搜索参数 */}
            {debugInfo.params && (
              <div className="space-y-1">
                <p className="text-gray-400">搜索参数:</p>
                <div 
                  className="rounded-lg p-2 flex flex-wrap gap-3"
                  style={{ background: 'rgba(255, 255, 255, 0.05)' }}
                >
                  <span>向量权重: <span className="text-cyan-400">{debugInfo.params.vectorWeight}</span></span>
                  <span>标签权重: <span className="text-cyan-400">{debugInfo.params.tagWeight}</span></span>
                  <span>RRF k: <span className="text-cyan-400">{debugInfo.params.rrf_k}</span></span>
                  {debugInfo.params.searchTime !== undefined && (
                    <span>搜索耗时: <span className="text-yellow-400">{debugInfo.params.searchTime}ms</span></span>
                  )}
                </div>
              </div>
            )}

            {/* 图片搜索调试信息 */}
            {debugInfo.imageSearch && (
              <div className="space-y-1">
                <p className="text-gray-400">🖼️ 图片搜索调试:</p>
                <div 
                  className="rounded-lg p-2 space-y-2"
                  style={{ background: 'rgba(139, 92, 246, 0.1)' }}
                >
                  {/* 模型对比 - 关键问题提示 */}
                  <div className="flex flex-wrap gap-3 items-center">
                    <span>搜索模型: <span className="text-violet-400">{debugInfo.imageSearch.searchModel}</span></span>
                    <span className="text-gray-500">vs</span>
                    <span>数据库模型: <span className="text-orange-400">{debugInfo.imageSearch.dbModel}</span></span>
                    {debugInfo.imageSearch.searchModel !== debugInfo.imageSearch.dbModel && (
                      <span className="px-2 py-0.5 rounded text-xs bg-red-500/20 text-red-400 border border-red-500/30">
                        ⚠️ 模型不匹配
                      </span>
                    )}
                  </div>
                  
                  {/* 向量信息 */}
                  <div className="flex flex-wrap gap-3">
                    <span>向量维度: <span className="text-cyan-400">{debugInfo.imageSearch.vectorDimension}</span></span>
                    <span>返回数量: <span className={debugInfo.imageSearch.rawResultCount > 0 ? 'text-green-400' : 'text-red-400'}>
                      {debugInfo.imageSearch.rawResultCount}
                    </span></span>
                  </div>
                  
                  {/* 相似度分数 */}
                  {debugInfo.imageSearch.topSimilarities && debugInfo.imageSearch.topSimilarities.length > 0 && (
                    <div>
                      <span className="text-gray-400">前 {debugInfo.imageSearch.topSimilarities.length} 个相似度: </span>
                      <span className="font-mono text-[10px]">
                        {debugInfo.imageSearch.topSimilarities.map((sim, i) => (
                          <span key={i} className={sim > 0.5 ? 'text-green-400' : sim > 0.3 ? 'text-yellow-400' : 'text-red-400'}>
                            {sim.toFixed(4)}{i < debugInfo.imageSearch!.topSimilarities!.length - 1 ? ', ' : ''}
                          </span>
                        ))}
                      </span>
                    </div>
                  )}
                  
                  {/* 错误信息 */}
                  {debugInfo.imageSearch.error && (
                    <div className="text-red-400">
                      ❌ 错误: {debugInfo.imageSearch.error}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* 前 15 个结果详情 */}
            {debugInfo.results && debugInfo.results.length > 0 && (
              <div className="space-y-1">
                <p className="text-gray-400">🔝 前 {debugInfo.results.length} 个结果打分:</p>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-2">
                  {debugInfo.results.map((result, idx) => (
                    <div 
                      key={`top-${idx}-${result.rank}`} 
                      className="rounded-lg p-2"
                      style={{ 
                        background: result.categoryMatched 
                          ? 'rgba(239, 68, 68, 0.15)' 
                          : 'rgba(34, 197, 94, 0.1)',
                        border: result.categoryMatched 
                          ? '1px solid rgba(239, 68, 68, 0.3)' 
                          : 'none'
                      }}
                    >
                      <div className="flex items-center gap-1">
                        <p className="font-medium text-white truncate flex-1">
                        #{result.rank} {result.productName}
                      </p>
                        {result.categoryMatched && (
                          <span className="px-1 py-0.5 text-[8px] bg-red-500/30 text-red-300 rounded shrink-0">
                            品类✓
                          </span>
                      )}
                    </div>
                      {result.scores ? (
                        <>
                          <div className="flex flex-wrap gap-1.5 mt-1 text-[10px]">
                            <span>向量: <span className="text-green-400">{result.scores.vectorSimilarity}</span></span>
                            <span>标签: <span className="text-blue-400">{result.scores.tagMatchScore}</span></span>
                            <span>最终: <span className="text-yellow-400 font-bold">{result.scores.finalScore}</span></span>
                </div>
                          {/* CAPUS 五维度得分 */}
                          {result.scores.capus && (
                            <div className="flex flex-wrap gap-1 mt-1 text-[8px]">
                              <span className="px-1 rounded" style={{ background: result.scores.capus.category > 0 ? 'rgba(239,68,68,0.3)' : 'rgba(100,116,139,0.2)' }}>C:{result.scores.capus.category}</span>
                              <span className="px-1 rounded" style={{ background: result.scores.capus.attribute > 0 ? 'rgba(59,130,246,0.3)' : 'rgba(100,116,139,0.2)' }}>A:{result.scores.capus.attribute}</span>
                              <span className="px-1 rounded" style={{ background: result.scores.capus.performance > 0 ? 'rgba(34,197,94,0.3)' : 'rgba(100,116,139,0.2)' }}>P:{result.scores.capus.performance}</span>
                              <span className="px-1 rounded" style={{ background: result.scores.capus.use > 0 ? 'rgba(245,158,11,0.3)' : 'rgba(100,116,139,0.2)' }}>U:{result.scores.capus.use}</span>
                              <span className="px-1 rounded" style={{ background: result.scores.capus.style > 0 ? 'rgba(236,72,153,0.3)' : 'rgba(100,116,139,0.2)' }}>S:{result.scores.capus.style}</span>
              </div>
            )}
                        </>
                      ) : (
                        <div className="flex flex-wrap gap-1.5 mt-1 text-[10px]">
                          <span>向量: <span className="text-green-400">{result.vectorScore?.toFixed(3) ?? '-'}</span></span>
                          <span>标签: <span className="text-blue-400">{result.tagScore?.toFixed(3) ?? '-'}</span></span>
                          <span>最终: <span className="text-yellow-400 font-bold">{result.finalScore?.toFixed(4) ?? '-'}</span></span>
                      </div>
                      )}
                      {result.matchedTags && result.matchedTags.length > 0 && (
                        <p className="text-[10px] text-violet-400 mt-1 truncate">
                          匹配: [{result.matchedTags.join(', ')}]
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 无数据提示 */}
            {!debugInfo.results && (
              <p className="text-gray-500 text-center py-2">
                暂无详细搜索数据，搜索后会显示匹配详情
              </p>
            )}
          </div>
        </div>
      )}

      {/* 筛选器 */}
      {showFilters && (
        <div className="mb-6">
          <div className="flex items-center justify-between mb-3">
            <h3 
              className="font-medium"
              style={{ color: 'white' }}
            >
              标签筛选
            </h3>
            {selectedTagCount > 0 && (
              <button
                onClick={handleClearFilters}
                className="text-sm px-3 py-1 rounded-lg transition-colors"
                style={{
                  color: 'rgba(255, 255, 255, 0.7)',
                  background: 'rgba(255, 255, 255, 0.1)',
                }}
              >
                清除全部
              </button>
            )}
          </div>
          <TagFilter
            tagGroups={tagGroups}
            selectedTags={selectedTags}
            onTagChange={handleTagChange}
          />
        </div>
      )}

      {/* 商品网格 */}
      <ProductGrid
        products={products}
        loading={loading}
        onProductClick={(product) => {
          console.log('点击商品:', product);
        }}
      />

      {/* 分页 */}
      {!loading && products.length > 0 && (
        <div className="mt-8">
          <Pagination
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={handlePageChange}
          />
        </div>
      )}

      {/* 搜索 Modal */}
      <SearchModal
        open={searchModalOpen}
        onOpenChange={setSearchModalOpen}
        onSearch={handleSearch}
        isSearching={isSearching}
        debugInfo={debugInfo}
        showDebug={showDebug}
        onToggleDebug={() => setShowDebug(!showDebug)}
      />
    </div>
  );
}
