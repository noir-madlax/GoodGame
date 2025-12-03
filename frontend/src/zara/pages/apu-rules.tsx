/**
 * APU 规则库管理页面 - Liquid Glass 风格
 * 
 * 路由: /zara/apu-rules
 * 功能: 展示和维护 APU 规则库（5 维度结构）
 * 
 * 5 维度:
 *   - 商品类型 (category)
 *   - 商品描述 (product_description)
 *   - Attribute (物理属性)
 *   - Performance (性能)
 *   - Use (使用场景)
 */

'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { cn } from '@/lib/utils';
import { 
  Brain, 
  Search, 
  ChevronDown, 
  ChevronUp,
  Edit2,
  Save,
  X,
  Check,
  Filter,
  RefreshCw,
  Star,
  StarOff,
} from 'lucide-react';

// ============================================================================
// 类型定义
// ============================================================================

interface APURule {
  id: number;
  category: string;
  product_description: string;
  attribute_keywords: string[];
  performance_keywords: string[];
  use_keywords: string[];
  is_featured: boolean;
  created_at: string;
  updated_at: string;
}

interface APURulesResponse {
  success: boolean;
  data?: {
    rules: APURule[];
    total: number;
    page: number;
    pageSize: number;
    totalPages: number;
    categories: string[];
  };
  error?: string;
}

// ============================================================================
// 组件
// ============================================================================

/**
 * 关键词标签组件
 */
const KeywordTags: React.FC<{
  keywords: string[];
  color: 'blue' | 'green' | 'purple';
  editable?: boolean;
  onChange?: (keywords: string[]) => void;
}> = ({ keywords, color, editable = false, onChange }) => {
  const [inputValue, setInputValue] = useState('');
  
  const colorStyles = {
    blue: {
      bg: 'rgba(59, 130, 246, 0.2)',
      border: 'rgba(59, 130, 246, 0.4)',
      text: '#93c5fd',
    },
    green: {
      bg: 'rgba(34, 197, 94, 0.2)',
      border: 'rgba(34, 197, 94, 0.4)',
      text: '#86efac',
    },
    purple: {
      bg: 'rgba(139, 92, 246, 0.2)',
      border: 'rgba(139, 92, 246, 0.4)',
      text: '#c4b5fd',
    },
  };
  
  const style = colorStyles[color];
  
  const handleAddKeyword = () => {
    if (inputValue.trim() && onChange) {
      onChange([...keywords, inputValue.trim()]);
      setInputValue('');
    }
  };
  
  const handleRemoveKeyword = (index: number) => {
    if (onChange) {
      onChange(keywords.filter((_, i) => i !== index));
    }
  };
  
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddKeyword();
    }
  };
  
  return (
    <div className="flex flex-wrap gap-1.5">
      {keywords.map((keyword, index) => (
        <span
          key={index}
          className="px-2 py-0.5 rounded-full text-xs flex items-center gap-1"
          style={{
            background: style.bg,
            border: `0.5px solid ${style.border}`,
            color: style.text,
          }}
        >
          {keyword}
          {editable && (
            <button
              onClick={() => handleRemoveKeyword(index)}
              className="hover:opacity-70"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </span>
      ))}
      {editable && (
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={handleKeyPress}
          onBlur={handleAddKeyword}
          placeholder="添加..."
          className="px-2 py-0.5 rounded-full text-xs w-16 bg-transparent border border-dashed outline-none"
          style={{
            borderColor: style.border,
            color: style.text,
          }}
        />
      )}
    </div>
  );
};

/**
 * 规则卡片组件
 */
const RuleCard: React.FC<{
  rule: APURule;
  expanded: boolean;
  onToggle: () => void;
  onUpdate: (rule: APURule) => Promise<void>;
}> = ({ rule, expanded, onToggle, onUpdate }) => {
  const [editing, setEditing] = useState(false);
  const [editedRule, setEditedRule] = useState(rule);
  const [saving, setSaving] = useState(false);
  
  const handleSave = async () => {
    setSaving(true);
    try {
      await onUpdate(editedRule);
      setEditing(false);
    } finally {
      setSaving(false);
    }
  };
  
  const handleCancel = () => {
    setEditedRule(rule);
    setEditing(false);
  };
  
  const handleToggleFeatured = async () => {
    const updated = { ...rule, is_featured: !rule.is_featured };
    await onUpdate(updated);
  };
  
  return (
    <div
      className="rounded-xl overflow-hidden transition-all duration-300"
      style={{
        background: 'rgba(30, 41, 59, 0.6)',
        backdropFilter: 'blur(10px)',
        border: expanded 
          ? '1px solid rgba(59, 130, 246, 0.4)' 
          : '1px solid rgba(100, 116, 139, 0.2)',
      }}
    >
      {/* 头部 */}
      <div
        className="flex items-center justify-between p-4 cursor-pointer"
        onClick={onToggle}
      >
        <div className="flex items-center gap-3 flex-1 min-w-0">
          {/* 品类标签 */}
          <span
            className="px-2 py-1 rounded-lg text-xs font-medium shrink-0"
            style={{
              background: 'rgba(6, 182, 212, 0.2)',
              border: '0.5px solid rgba(6, 182, 212, 0.4)',
              color: '#67e8f9',
            }}
          >
            {rule.category}
          </span>
          
          {/* 商品描述 */}
          <span 
            className="text-white font-medium truncate"
            title={rule.product_description}
          >
            {rule.product_description}
          </span>
          
          {/* 精选标记 */}
          {rule.is_featured && (
            <Star 
              className="w-4 h-4 shrink-0" 
              style={{ color: '#fbbf24', fill: '#fbbf24' }} 
            />
          )}
        </div>
        
        {/* 展开/收起按钮 */}
        <div className="flex items-center gap-2">
          {expanded ? (
            <ChevronUp className="w-5 h-5 text-gray-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-gray-400" />
          )}
        </div>
      </div>
      
      {/* 详情（展开时显示） */}
      {expanded && (
        <div 
          className="px-4 pb-4 space-y-4"
          style={{ borderTop: '1px solid rgba(100, 116, 139, 0.2)' }}
        >
          {/* 工具栏 */}
          <div className="flex items-center justify-end gap-2 pt-3">
            <button
              onClick={handleToggleFeatured}
              className="p-2 rounded-lg transition-colors"
              style={{
                background: rule.is_featured 
                  ? 'rgba(251, 191, 36, 0.2)' 
                  : 'rgba(100, 116, 139, 0.2)',
                border: rule.is_featured 
                  ? '0.5px solid rgba(251, 191, 36, 0.4)' 
                  : '0.5px solid rgba(100, 116, 139, 0.3)',
              }}
              title={rule.is_featured ? '取消精选' : '标为精选'}
            >
              {rule.is_featured ? (
                <StarOff className="w-4 h-4" style={{ color: '#fbbf24' }} />
              ) : (
                <Star className="w-4 h-4 text-gray-400" />
              )}
            </button>
            
            {editing ? (
              <>
                <button
                  onClick={handleCancel}
                  className="p-2 rounded-lg transition-colors"
                  style={{
                    background: 'rgba(239, 68, 68, 0.2)',
                    border: '0.5px solid rgba(239, 68, 68, 0.4)',
                  }}
                >
                  <X className="w-4 h-4 text-red-400" />
                </button>
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="p-2 rounded-lg transition-colors"
                  style={{
                    background: 'rgba(34, 197, 94, 0.2)',
                    border: '0.5px solid rgba(34, 197, 94, 0.4)',
                  }}
                >
                  {saving ? (
                    <RefreshCw className="w-4 h-4 text-green-400 animate-spin" />
                  ) : (
                    <Check className="w-4 h-4 text-green-400" />
                  )}
                </button>
              </>
            ) : (
              <button
                onClick={() => setEditing(true)}
                className="p-2 rounded-lg transition-colors"
                style={{
                  background: 'rgba(59, 130, 246, 0.2)',
                  border: '0.5px solid rgba(59, 130, 246, 0.4)',
                }}
              >
                <Edit2 className="w-4 h-4 text-blue-400" />
              </button>
            )}
          </div>
          
          {/* APU 三维度 */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Attribute */}
            <div 
              className="p-3 rounded-lg"
              style={{ background: 'rgba(59, 130, 246, 0.1)' }}
            >
              <h4 className="text-xs font-medium text-blue-400 mb-2">
                Attribute (物理属性)
              </h4>
              <KeywordTags
                keywords={editing ? editedRule.attribute_keywords : rule.attribute_keywords}
                color="blue"
                editable={editing}
                onChange={(keywords) => setEditedRule({ ...editedRule, attribute_keywords: keywords })}
              />
            </div>
            
            {/* Performance */}
            <div 
              className="p-3 rounded-lg"
              style={{ background: 'rgba(34, 197, 94, 0.1)' }}
            >
              <h4 className="text-xs font-medium text-green-400 mb-2">
                Performance (性能)
              </h4>
              <KeywordTags
                keywords={editing ? editedRule.performance_keywords : rule.performance_keywords}
                color="green"
                editable={editing}
                onChange={(keywords) => setEditedRule({ ...editedRule, performance_keywords: keywords })}
              />
            </div>
            
            {/* Use */}
            <div 
              className="p-3 rounded-lg"
              style={{ background: 'rgba(139, 92, 246, 0.1)' }}
            >
              <h4 className="text-xs font-medium text-purple-400 mb-2">
                Use (使用场景)
              </h4>
              <KeywordTags
                keywords={editing ? editedRule.use_keywords : rule.use_keywords}
                color="purple"
                editable={editing}
                onChange={(keywords) => setEditedRule({ ...editedRule, use_keywords: keywords })}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

/**
 * APU 规则库管理页面
 */
export default function APURulesPage() {
  // 数据状态
  const [rules, setRules] = useState<APURule[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  
  // 筛选状态
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  
  // UI 状态
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());
  const [showFilters, setShowFilters] = useState(false);
  
  /**
   * 加载规则列表
   */
  const loadRules = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        pageSize: pageSize.toString(),
      });
      
      if (selectedCategory) {
        params.set('category', selectedCategory);
      }
      if (searchQuery) {
        params.set('search', searchQuery);
      }
      
      const response = await fetch(`/api/zara/apu-rules?${params}`);
      const data: APURulesResponse = await response.json();
      
      if (data.success && data.data) {
        setRules(data.data.rules);
        setTotal(data.data.total);
        setCategories(data.data.categories);
      }
    } catch (error) {
      console.error('加载规则失败:', error);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, selectedCategory, searchQuery]);
  
  /**
   * 更新规则
   */
  const handleUpdateRule = useCallback(async (rule: APURule) => {
    try {
      const response = await fetch('/api/zara/apu-rules', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(rule),
      });
      
      const data = await response.json();
      
      if (data.success) {
        // 更新本地状态
        setRules(prev => prev.map(r => r.id === rule.id ? { ...r, ...rule } : r));
      } else {
        console.error('更新失败:', data.error);
      }
    } catch (error) {
      console.error('更新规则失败:', error);
    }
  }, []);
  
  /**
   * 切换展开状态
   */
  const handleToggleExpand = useCallback((id: number) => {
    setExpandedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);
  
  /**
   * 搜索
   */
  const handleSearch = useCallback(() => {
    setPage(1);
    loadRules();
  }, [loadRules]);
  
  /**
   * 初始加载
   */
  useEffect(() => {
    loadRules();
  }, [page, selectedCategory]);
  
  /**
   * 搜索回车
   */
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };
  
  return (
    <div className="min-h-screen">
      {/* 页面标题 */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div 
            className="w-10 h-10 rounded-xl flex items-center justify-center"
            style={{
              background: 'linear-gradient(135deg, #8b5cf6 0%, #3b82f6 100%)',
              boxShadow: '0 4px 20px rgba(139, 92, 246, 0.4)',
            }}
          >
            <Brain className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 
              className="text-2xl font-bold"
              style={{
                background: 'linear-gradient(90deg, #c4b5fd 0%, #93c5fd 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}
            >
              增强理解管理
            </h1>
            <p className="text-sm text-gray-400">
              APU 规则库（Attribute-Performance-Use）
            </p>
          </div>
        </div>
      </div>
      
      {/* 搜索和筛选栏 */}
      <div 
        className="mb-6 p-4 rounded-xl"
        style={{
          background: 'rgba(30, 41, 59, 0.6)',
          backdropFilter: 'blur(10px)',
          border: '1px solid rgba(100, 116, 139, 0.2)',
        }}
      >
        <div className="flex flex-col md:flex-row gap-4">
          {/* 搜索框 */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="搜索商品描述..."
              className="w-full pl-10 pr-4 py-2 rounded-xl bg-slate-700/50 border border-slate-600 text-white placeholder:text-gray-400 outline-none focus:border-blue-500 transition-colors"
            />
          </div>
          
          {/* 品类筛选 */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={cn(
                'flex items-center gap-2 px-4 py-2 rounded-xl transition-all',
              )}
              style={{
                background: showFilters ? 'rgba(59, 130, 246, 0.2)' : 'rgba(100, 116, 139, 0.2)',
                border: showFilters ? '0.5px solid rgba(59, 130, 246, 0.4)' : '0.5px solid rgba(100, 116, 139, 0.3)',
                color: showFilters ? '#93c5fd' : '#94a3b8',
              }}
            >
              <Filter className="w-4 h-4" />
              筛选
            </button>
            
            <button
              onClick={handleSearch}
              className="px-4 py-2 rounded-xl transition-all"
              style={{
                background: 'linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%)',
                color: 'white',
              }}
            >
              搜索
            </button>
          </div>
        </div>
        
        {/* 品类筛选器（展开时显示） */}
        {showFilters && (
          <div 
            className="mt-4 pt-4 flex flex-wrap gap-2"
            style={{ borderTop: '1px solid rgba(100, 116, 139, 0.2)' }}
          >
            <button
              onClick={() => setSelectedCategory('')}
              className={cn(
                'px-3 py-1.5 rounded-lg text-sm transition-all',
              )}
              style={{
                background: !selectedCategory ? 'rgba(59, 130, 246, 0.3)' : 'rgba(100, 116, 139, 0.2)',
                border: !selectedCategory ? '0.5px solid rgba(59, 130, 246, 0.5)' : '0.5px solid rgba(100, 116, 139, 0.3)',
                color: !selectedCategory ? '#93c5fd' : '#94a3b8',
              }}
            >
              全部
            </button>
            {categories.map(category => (
              <button
                key={category}
                onClick={() => setSelectedCategory(category)}
                className="px-3 py-1.5 rounded-lg text-sm transition-all"
                style={{
                  background: selectedCategory === category ? 'rgba(59, 130, 246, 0.3)' : 'rgba(100, 116, 139, 0.2)',
                  border: selectedCategory === category ? '0.5px solid rgba(59, 130, 246, 0.5)' : '0.5px solid rgba(100, 116, 139, 0.3)',
                  color: selectedCategory === category ? '#93c5fd' : '#94a3b8',
                }}
              >
                {category}
              </button>
            ))}
          </div>
        )}
      </div>
      
      {/* 统计信息 */}
      <div className="flex items-center justify-between mb-4">
        <span className="text-gray-400">
          共 {total} 条规则
          {selectedCategory && ` · ${selectedCategory}`}
        </span>
        
        <button
          onClick={loadRules}
          className="p-2 rounded-lg transition-colors hover:bg-slate-700/50"
        >
          <RefreshCw className={cn("w-4 h-4 text-gray-400", loading && "animate-spin")} />
        </button>
      </div>
      
      {/* 规则列表 */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <RefreshCw className="w-8 h-8 text-blue-400 animate-spin" />
        </div>
      ) : rules.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-gray-400">
          <Brain className="w-12 h-12 mb-4 opacity-50" />
          <p>暂无规则数据</p>
        </div>
      ) : (
        <div className="space-y-3">
          {rules.map(rule => (
            <RuleCard
              key={rule.id}
              rule={rule}
              expanded={expandedIds.has(rule.id)}
              onToggle={() => handleToggleExpand(rule.id)}
              onUpdate={handleUpdateRule}
            />
          ))}
        </div>
      )}
      
      {/* 分页 */}
      {!loading && rules.length > 0 && total > pageSize && (
        <div className="mt-8 flex items-center justify-center gap-2">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-4 py-2 rounded-lg transition-all disabled:opacity-50"
            style={{
              background: 'rgba(100, 116, 139, 0.2)',
              border: '0.5px solid rgba(100, 116, 139, 0.3)',
              color: '#94a3b8',
            }}
          >
            上一页
          </button>
          
          <span className="text-gray-400 px-4">
            {page} / {Math.ceil(total / pageSize)}
          </span>
          
          <button
            onClick={() => setPage(p => p + 1)}
            disabled={page >= Math.ceil(total / pageSize)}
            className="px-4 py-2 rounded-lg transition-all disabled:opacity-50"
            style={{
              background: 'rgba(100, 116, 139, 0.2)',
              border: '0.5px solid rgba(100, 116, 139, 0.3)',
              color: '#94a3b8',
            }}
          >
            下一页
          </button>
        </div>
      )}
    </div>
  );
}

