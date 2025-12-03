/**
 * AI 搜索 Modal 组件
 * 
 * 使用页面: zara/pages/product-search.tsx
 * 功能: 类似 ChatGPT 的 AI 对话搜索界面，支持文字和图片输入
 * 
 * 图片上传支持:
 * - 点击按钮选择文件
 * - 拖拽图片到输入区域
 * - Ctrl/Cmd + V 粘贴剪贴板图片
 */

'use client';

import React, { useState, useRef, useCallback, useEffect } from 'react';
import { cn } from '@/lib/utils';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import {
  Send,
  Image as ImageIcon,
  X,
  Sparkles,
  Loader2,
  Upload,
  Clipboard,
} from 'lucide-react';

// Debug 结果项接口
export interface SearchDebugResultItem {
  rank: number;
  productId: number;
  productName: string;
  // 新版打分结构
  scores?: {
    vectorSimilarity: number;
    tagMatchScore: number;
    rrfScore: number;
    finalScore: number;
  };
  matchedTags: string[];
  // 兼容旧版
  vectorScore?: number;
  tagScore?: number;
  finalScore?: number;
}

// APU 意图分析
interface APUIntentDebug {
  attribute: string[];
  performance: string[];
  use: string[];
  style?: string[];
  primaryDimension?: string;
  causalReasoning?: string;
}

// 搜索 Debug 信息接口 - 优化版
export interface SearchDebugInfo {
  // 输入解析
  input?: {
    rawQuery: string;
    searchText?: string;
    extractedTags?: string[];
    apuIntent?: APUIntentDebug;
  };
  // 配置参数（从数据库加载）
  config?: {
    textSearchWeight: number;
    imageSearchWeight: number;
    apuWeights: {
      attribute: number;
      performance: number;
      use: number;
      style: number;
    };
    rankingWeights: {
      searchResult: number;
      personaTag: number;
      userPreference: number;
    };
    rrf_k: number;
    matchCount: number;
    minSimilarity: number;
  };
  // 耗时统计
  timing?: {
    llmParseMs?: number;
    embeddingMs?: number;
    searchMs?: number;
    totalMs: number;
  };
  // 图片搜索调试信息
  imageSearch?: {
    vectorDimension: number;
    searchModel: string;
    dbModel: string;
    rawResultCount: number;
    topSimilarities?: number[];
    error?: string;
  };
  // 结果详情
  results?: SearchDebugResultItem[];
  // 兼容旧版
  params?: {
    vectorWeight?: number;
    tagWeight?: number;
    rrf_k?: number;
    searchTime?: number;
  };
}

interface SearchModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSearch: (query: string, imageFile?: File) => void;
  isSearching?: boolean;
  debugInfo?: SearchDebugInfo | null;
  showDebug?: boolean;
  onToggleDebug?: () => void;
}

/**
 * AI 搜索 Modal
 * 提供类似 ChatGPT 的对话式搜索体验
 */
export default function SearchModal({
  open,
  onOpenChange,
  onSearch,
  isSearching = false,
  debugInfo = null,
  showDebug = false,
  onToggleDebug,
}: SearchModalProps) {
  // 输入状态
  const [inputText, setInputText] = useState('');
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  // Refs
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dropZoneRef = useRef<HTMLDivElement>(null);

  /**
   * 处理图片文件
   */
  const processImageFile = useCallback((file: File) => {
    if (!file.type.startsWith('image/')) {
      console.warn('不支持的文件类型:', file.type);
      return;
    }
    
    setSelectedImage(file);
    // 生成预览 URL
    const reader = new FileReader();
    reader.onloadend = () => {
      setImagePreview(reader.result as string);
    };
    reader.readAsDataURL(file);
  }, []);

  /**
   * 处理图片选择
   */
  const handleImageSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      processImageFile(file);
    }
  }, [processImageFile]);

  /**
   * 清除选中的图片
   */
  const handleClearImage = useCallback(() => {
    setSelectedImage(null);
    setImagePreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, []);

  /**
   * 处理搜索提交
   */
  const handleSubmit = useCallback(() => {
    const query = inputText.trim();
    if (!query && !selectedImage) return;

    onSearch(query, selectedImage || undefined);
    
    // 清空输入
    setInputText('');
    handleClearImage();
  }, [inputText, selectedImage, onSearch, handleClearImage]);

  /**
   * 处理键盘事件
   */
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    // Cmd/Ctrl + Enter 提交
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      handleSubmit();
    }
  }, [handleSubmit]);

  /**
   * 处理粘贴事件 - 支持粘贴图片
   */
  const handlePaste = useCallback((e: React.ClipboardEvent) => {
    const items = e.clipboardData?.items;
    if (!items) return;

    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.type.startsWith('image/')) {
        e.preventDefault();
        const file = item.getAsFile();
        if (file) {
          processImageFile(file);
        }
        return;
      }
    }
  }, [processImageFile]);

  /**
   * 处理拖拽进入
   */
  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  /**
   * 处理拖拽离开
   */
  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    // 检查是否真的离开了拖拽区域
    if (dropZoneRef.current && !dropZoneRef.current.contains(e.relatedTarget as Node)) {
      setIsDragging(false);
    }
  }, []);

  /**
   * 处理拖拽上传
   */
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    
    const file = e.dataTransfer.files?.[0];
    if (file) {
      processImageFile(file);
    }
  }, [processImageFile]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  /**
   * 打开时聚焦输入框
   */
  useEffect(() => {
    if (open && textareaRef.current) {
      setTimeout(() => {
        textareaRef.current?.focus();
      }, 100);
    }
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent 
        ref={dropZoneRef}
        className={cn(
          'sm:max-w-2xl p-0 gap-0 overflow-hidden',
          // Liquid Glass 样式
          'bg-white/70 dark:bg-gray-900/70',
          'backdrop-blur-xl backdrop-saturate-150',
          'border border-white/30 dark:border-white/10',
          'shadow-[0_8px_32px_rgba(0,0,0,0.12)]',
          'rounded-3xl',
          // 拖拽状态
          isDragging && 'ring-2 ring-blue-500 ring-offset-2'
        )}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
      >
        {/* 拖拽覆盖层 */}
        {isDragging && (
          <div className={cn(
            'absolute inset-0 z-50',
            'bg-blue-500/10 backdrop-blur-sm',
            'flex items-center justify-center',
            'border-2 border-dashed border-blue-500',
            'rounded-3xl'
          )}>
            <div className="text-center">
              <Upload className="w-12 h-12 mx-auto text-blue-500 mb-2" />
              <p className="text-blue-600 dark:text-blue-400 font-medium">
                释放鼠标上传图片
              </p>
            </div>
          </div>
        )}

        {/* 头部 */}
        <DialogHeader className={cn(
          'p-6 pb-4',
          'border-b border-white/20 dark:border-white/10',
          'bg-gradient-to-r from-white/50 to-white/30 dark:from-gray-800/50 dark:to-gray-800/30'
        )}>
          <DialogTitle className="flex items-center gap-3 text-xl">
            <div className={cn(
              'w-10 h-10 rounded-2xl',
              'bg-gradient-to-br from-violet-500 to-purple-600',
              'flex items-center justify-center',
              'shadow-lg shadow-violet-500/30'
            )}>
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="text-gray-900 dark:text-white font-semibold">智能搜索</span>
              <p className="text-sm font-normal text-gray-500 dark:text-gray-400 mt-0.5">
                输入文字描述或上传图片，AI 帮你找到心仪商品
              </p>
            </div>
          </DialogTitle>
        </DialogHeader>

        {/* 内容区域 */}
        <div className="p-6 space-y-4">
          {/* 搜索提示 */}
          <div className="space-y-2">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              💡 搜索示例：
            </p>
            <div className="flex flex-wrap gap-2">
              {[
                '我想要去沙滩，给我推荐下好的连衣裙',
                '秋季通勤穿的针织衫',
                '宽松休闲的牛仔裤',
                '保暖的羽绒服',
              ].map((example, index) => (
                <button
                  key={index}
                  onClick={() => setInputText(example)}
                  className={cn(
                    'px-3 py-1.5 text-sm rounded-full',
                    // Liquid Glass 样式
                    'bg-white/60 dark:bg-white/10',
                    'backdrop-blur-sm',
                    'border border-white/40 dark:border-white/10',
                    'text-gray-600 dark:text-gray-300',
                    'hover:bg-white/80 dark:hover:bg-white/20',
                    'transition-all duration-200',
                    'shadow-sm'
                  )}
                >
                  {example}
                </button>
              ))}
            </div>
          </div>

          {/* 图片预览 */}
          {imagePreview && (
            <div className={cn(
              'relative inline-block',
              'p-2 rounded-2xl',
              'bg-white/60 dark:bg-white/10',
              'backdrop-blur-sm',
              'border border-white/40 dark:border-white/10'
            )}>
              <img
                src={imagePreview}
                alt="上传的图片"
                className="max-h-40 rounded-xl object-cover"
              />
              <button
                onClick={handleClearImage}
                className={cn(
                  'absolute -top-2 -right-2 w-7 h-7 rounded-full',
                  'bg-red-500/90 backdrop-blur-sm text-white',
                  'flex items-center justify-center',
                  'hover:bg-red-600 transition-colors',
                  'shadow-lg'
                )}
              >
                <X className="w-4 h-4" />
              </button>
              <div className="mt-2 text-xs text-gray-500 text-center">
                {selectedImage?.name}
              </div>
            </div>
          )}

          {/* 输入区域 */}
          <div className={cn(
            'relative rounded-2xl transition-all duration-200',
            // Liquid Glass 样式
            'bg-white/60 dark:bg-white/5',
            'backdrop-blur-sm',
            'border-2 border-white/40 dark:border-white/10',
            'focus-within:border-violet-500/50 dark:focus-within:border-violet-400/50',
            'focus-within:shadow-lg focus-within:shadow-violet-500/10',
            'shadow-sm'
          )}>
            <Textarea
              ref={textareaRef}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              onPaste={handlePaste}
              placeholder="描述你想要的商品，或者上传/粘贴一张图片..."
              className={cn(
                'min-h-[120px] max-h-[200px] resize-none',
                'border-0 bg-transparent',
                'focus:ring-0 focus-visible:ring-0',
                'text-gray-900 dark:text-white',
                'placeholder:text-gray-400',
                'p-4 pb-14'
              )}
            />

            {/* 底部工具栏 */}
            <div className="absolute bottom-3 left-3 right-3 flex items-center justify-between">
              {/* 左侧：上传图片 */}
              <div className="flex items-center gap-2">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  onChange={handleImageSelect}
                  className="hidden"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => fileInputRef.current?.click()}
                  className={cn(
                    'text-gray-500 hover:text-violet-600 dark:hover:text-violet-400',
                    'hover:bg-violet-500/10',
                    'rounded-xl'
                  )}
                >
                  <ImageIcon className="w-5 h-5 mr-1" />
                  上传图片
                </Button>

                {/* 粘贴提示 */}
                <span className="text-xs text-gray-400 flex items-center gap-1">
                  <Clipboard className="w-3 h-3" />
                  Ctrl+V 粘贴
                </span>
              </div>

              {/* 右侧：发送按钮 */}
              <Button
                onClick={handleSubmit}
                disabled={(!inputText.trim() && !selectedImage) || isSearching}
                className={cn(
                  'rounded-xl px-4',
                  'bg-gradient-to-r from-violet-500 to-purple-600',
                  'hover:from-violet-600 hover:to-purple-700',
                  'text-white',
                  'shadow-lg shadow-violet-500/30',
                  'disabled:opacity-50 disabled:shadow-none'
                )}
              >
                {isSearching ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    搜索中...
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4 mr-2" />
                    搜索
                  </>
                )}
              </Button>
            </div>
          </div>

          {/* 快捷键提示 */}
          <p className="text-xs text-gray-400 text-center">
            按 <kbd className="px-1.5 py-0.5 bg-white/60 dark:bg-white/10 backdrop-blur-sm rounded text-gray-500 border border-white/40 dark:border-white/10">⌘</kbd> + <kbd className="px-1.5 py-0.5 bg-white/60 dark:bg-white/10 backdrop-blur-sm rounded text-gray-500 border border-white/40 dark:border-white/10">Enter</kbd> 快速搜索
            {' | '}
            拖拽或粘贴图片上传
          </p>
        </div>

        {/* Debug 信息面板 - 优化版 */}
        {showDebug && debugInfo && (
          <div className={cn(
            'border-t border-white/20 dark:border-white/10',
            'bg-gray-900/95 backdrop-blur-xl',
            'text-white text-xs',
            'max-h-[400px] overflow-auto'
          )}>
            <div className="p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="font-semibold text-violet-400">🔍 搜索 Debug 信息</h4>
                <button onClick={onToggleDebug} className="text-gray-400 hover:text-white">
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* 输入解析与 APU 意图 */}
              {debugInfo.input && (
                <div className="space-y-1">
                  <p className="text-gray-400 font-medium">📝 输入解析:</p>
                  <div className="bg-white/5 rounded-lg p-3 space-y-2">
                    <p>原始输入: <span className="text-green-400">{debugInfo.input.rawQuery}</span></p>
                    {/* 提取的品类 - 最高优先级 */}
                    {debugInfo.input.extractedCategory && (
                      <p className="flex items-center gap-2">
                        <span className="px-2 py-0.5 bg-red-500/20 text-red-300 rounded text-[10px]">🎯 品类过滤</span>
                        <span className="text-red-400 font-bold">{debugInfo.input.extractedCategory}</span>
                      </p>
                    )}
                    {/* 增强搜索文本 */}
                    {debugInfo.input.searchText && (
                      <p>增强搜索文本: <span className="text-cyan-400">{debugInfo.input.searchText}</span></p>
                    )}
                    {/* APU 意图分析 */}
                    {debugInfo.input.apuIntent && (
                      <div className="mt-2 pt-2 border-t border-white/10">
                        <p className="text-purple-400 mb-1">APUS 四维度意图分析:</p>
                        <div className="grid grid-cols-2 gap-2 text-[10px]">
                          <p>属性(A): <span className="text-blue-300">{debugInfo.input.apuIntent.attribute?.join(', ') || '-'}</span></p>
                          <p>性能(P): <span className="text-green-300">{debugInfo.input.apuIntent.performance?.join(', ') || '-'}</span></p>
                          <p>场景(U): <span className="text-amber-300">{debugInfo.input.apuIntent.use?.join(', ') || '-'}</span></p>
                          <p>风格(S): <span className="text-pink-300">{debugInfo.input.apuIntent.style?.join(', ') || '-'}</span></p>
                        </div>
                        {debugInfo.input.apuIntent.primaryDimension && (
                          <p className="mt-1">主要维度: <span className="text-yellow-400">{debugInfo.input.apuIntent.primaryDimension}</span></p>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* 配置参数 */}
              {debugInfo.config && (
                <div className="space-y-1">
                  <p className="text-gray-400 font-medium">⚙️ 搜索配置:</p>
                  <div className="bg-white/5 rounded-lg p-3 space-y-2">
                    {/* 实际参与计算的权重 */}
                    <div>
                      <p className="text-cyan-300 text-[10px] mb-1">📊 实际搜索计算权重:</p>
                      <div className="flex flex-wrap gap-2 text-[10px]">
                        <span className="px-2 py-0.5 bg-green-500/20 rounded">向量相似度: 主要</span>
                        <span className="px-2 py-0.5 bg-blue-500/20 rounded">标签匹配: 辅助</span>
                        <span className="px-2 py-0.5 bg-red-500/20 rounded">品类加权: {debugInfo.config.capusWeights?.category ? (1 + debugInfo.config.capusWeights.category * 3).toFixed(1) : '2.2'}x</span>
                      </div>
                    </div>
                    {/* CAPUS 五维度权重（规划中） */}
                    <div>
                      <p className="text-purple-300 text-[10px] mb-1">🎯 CAPUS 五维度配置 (影响增强文本生成):</p>
                      <div className="flex flex-wrap gap-2 text-[10px]">
                        <span className="px-2 py-0.5 bg-red-500/20 rounded">品类: {debugInfo.config.capusWeights?.category || 0.30}</span>
                        <span className="px-2 py-0.5 bg-blue-500/20 rounded">属性: {debugInfo.config.capusWeights?.attribute || 0.25}</span>
                        <span className="px-2 py-0.5 bg-green-500/20 rounded">性能: {debugInfo.config.capusWeights?.performance || 0.20}</span>
                        <span className="px-2 py-0.5 bg-amber-500/20 rounded">场景: {debugInfo.config.capusWeights?.use || 0.15}</span>
                        <span className="px-2 py-0.5 bg-pink-500/20 rounded">风格: {debugInfo.config.capusWeights?.style || 0.10}</span>
                      </div>
                    </div>
                    {/* 排序权重 */}
                    <div>
                      <p className="text-cyan-300 text-[10px] mb-1">排序权重:</p>
                      <div className="flex flex-wrap gap-2 text-[10px]">
                        <span className="px-2 py-0.5 bg-blue-500/20 rounded">搜索结果: {debugInfo.config.rankingWeights.searchResult}</span>
                        <span className="px-2 py-0.5 bg-amber-500/20 rounded">个性化标签: {debugInfo.config.rankingWeights.personaTag}</span>
                        <span className="px-2 py-0.5 bg-pink-500/20 rounded">用户偏好: {debugInfo.config.rankingWeights.userPreference}</span>
                      </div>
                    </div>
                    {/* 其他参数 */}
                    <div className="flex flex-wrap gap-3 text-[10px] pt-1 border-t border-white/10">
                      <span>RRF k: <span className="text-cyan-400">{debugInfo.config.rrf_k}</span></span>
                      <span>最大数量: <span className="text-cyan-400">{debugInfo.config.matchCount}</span></span>
                      <span>最小相似度: <span className="text-cyan-400">{debugInfo.config.minSimilarity}</span></span>
                    </div>
                  </div>
                </div>
              )}

              {/* 耗时统计 */}
              {debugInfo.timing && (
                <div className="space-y-1">
                  <p className="text-gray-400 font-medium">⏱️ 耗时统计:</p>
                  <div className="bg-white/5 rounded-lg p-2 flex flex-wrap gap-3">
                    {debugInfo.timing.llmParseMs && (
                      <span>LLM解析: <span className="text-yellow-400">{debugInfo.timing.llmParseMs}ms</span></span>
                    )}
                    {debugInfo.timing.embeddingMs && (
                      <span>向量化: <span className="text-cyan-400">{debugInfo.timing.embeddingMs}ms</span></span>
                    )}
                    {debugInfo.timing.searchMs && (
                      <span>搜索: <span className="text-green-400">{debugInfo.timing.searchMs}ms</span></span>
                    )}
                    <span>总耗时: <span className="text-amber-400 font-bold">{debugInfo.timing.totalMs}ms</span></span>
                  </div>
                </div>
              )}

              {/* 结果详情打分 */}
              {debugInfo.results && debugInfo.results.length > 0 && (
                <div className="space-y-1">
                  <p className="text-gray-400 font-medium">📊 结果打分详情 (Top {debugInfo.results.length}):</p>
                  <div className="space-y-1.5 max-h-[200px] overflow-auto">
                    {debugInfo.results.map((result, idx) => (
                      <div 
                        key={`result-${idx}-${result.rank}`} 
                        className="rounded-lg p-2"
                        style={{ 
                          background: result.categoryMatched 
                            ? 'rgba(239, 68, 68, 0.15)' 
                            : 'rgba(255, 255, 255, 0.05)',
                          border: result.categoryMatched 
                            ? '1px solid rgba(239, 68, 68, 0.3)' 
                            : 'none'
                        }}
                      >
                        <div className="flex items-center gap-2">
                          <p className="font-medium text-white text-[11px] flex-1">
                            #{result.rank} {result.productName.slice(0, 30)}...
                          </p>
                          {result.categoryMatched && (
                            <span className="px-1.5 py-0.5 text-[9px] bg-red-500/30 text-red-300 rounded">
                              ✓ 品类匹配
                            </span>
                          )}
                        </div>
                        <div className="grid grid-cols-2 gap-1 mt-1 text-[10px]">
                          {result.scores ? (
                            <>
                              <span>向量相似度: <span className="text-green-400">{result.scores.vectorSimilarity}</span></span>
                              <span>标签匹配分: <span className="text-blue-400">{result.scores.tagMatchScore}</span></span>
                              <span>品类加权: <span className={result.categoryMatched ? "text-red-400" : "text-gray-500"}>{result.categoryMatched ? `${result.scores.categoryWeight} (生效)` : '无'}</span></span>
                              <span>最终得分: <span className="text-yellow-400 font-bold">{result.scores.finalScore}</span></span>
                            </>
                          ) : (
                            <>
                              <span>向量: <span className="text-green-400">{(result as unknown as { vectorScore: number }).vectorScore?.toFixed(3) || '-'}</span></span>
                              <span>最终: <span className="text-yellow-400 font-bold">{(result as unknown as { finalScore: number }).finalScore?.toFixed(3) || '-'}</span></span>
                            </>
                          )}
                        </div>
                        {result.matchedTags && result.matchedTags.length > 0 && (
                          <p className="text-[10px] mt-1">
                            匹配标签: <span className="text-purple-400">[{result.matchedTags.join(', ')}]</span>
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
