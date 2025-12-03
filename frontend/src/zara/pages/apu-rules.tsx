/**
 * APU 规则库管理页面 - Liquid Glass 风格
 * 
 * 路由: /zara/apu-rules
 * 功能: 展示和维护 APU 规则库
 * 
 * Tab 1: 原始规则库（品类级别规则 + 因果链）
 * Tab 2: 商品分析结果（商品描述级别的 APU 结果）
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
  BookOpen,
  Package,
  ArrowRight,
  Plus,
  Trash2,
  Tags,
  MapPin,
} from 'lucide-react';

// ============================================================================
// 类型定义
// ============================================================================

/** 品类规则 - APUS 四维度 */
interface CategoryRule {
  id: number;
  category: string;
  attribute_keywords: string[];
  attribute_description: string | null;
  performance_keywords: string[];
  performance_description: string | null;
  use_keywords: string[];
  use_description: string | null;
  style_keywords: string[];
  style_description: string | null;
  created_at: string;
  updated_at: string;
}

/** 因果链 */
interface CausalChain {
  id: number;
  rule_id: number;
  attribute_cause: string;
  performance_effect: string;
  use_cases: string[];
  style_result: string | null;
  created_at: string;
}

/** 商品规则 - APUS 四维度 */
interface ProductRule {
  id: number;
  category: string;
  product_description: string;
  attribute_keywords: string[];
  performance_keywords: string[];
  use_keywords: string[];
  style_keywords: string[];
  is_featured: boolean;
  created_at: string;
  updated_at: string;
}

/** 商品个性化标签 */
interface PersonaTag {
  id: number;
  product_id: number;
  region_tags: string[];
  style_tags: string[];
  audience_tags: string[];
  occasion_tags: string[];
  custom_tags: string[];
  notes: string | null;
  updated_at: string;
  product: {
    id: number;
    item_name: string;
    main_image_url: string;
    price_yuan: number;
  };
}

// ============================================================================
// 通用组件
// ============================================================================

/** 关键词标签组件 */
const KeywordTags: React.FC<{
  keywords: string[];
  color: 'blue' | 'green' | 'purple' | 'cyan' | 'amber';
  editable?: boolean;
  onChange?: (keywords: string[]) => void;
}> = ({ keywords, color, editable = false, onChange }) => {
  const [inputValue, setInputValue] = useState('');
  
  const colorStyles = {
    blue: { bg: 'rgba(59, 130, 246, 0.2)', border: 'rgba(59, 130, 246, 0.4)', text: '#93c5fd' },
    green: { bg: 'rgba(34, 197, 94, 0.2)', border: 'rgba(34, 197, 94, 0.4)', text: '#86efac' },
    purple: { bg: 'rgba(139, 92, 246, 0.2)', border: 'rgba(139, 92, 246, 0.4)', text: '#c4b5fd' },
    cyan: { bg: 'rgba(6, 182, 212, 0.2)', border: 'rgba(6, 182, 212, 0.4)', text: '#67e8f9' },
    amber: { bg: 'rgba(245, 158, 11, 0.2)', border: 'rgba(245, 158, 11, 0.4)', text: '#fcd34d' },
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
  
  return (
    <div className="flex flex-wrap gap-1.5">
      {keywords.map((keyword, index) => (
        <span
          key={index}
          className="px-2 py-0.5 rounded-full text-xs flex items-center gap-1"
          style={{ background: style.bg, border: `0.5px solid ${style.border}`, color: style.text }}
        >
          {keyword}
          {editable && (
            <button onClick={() => handleRemoveKeyword(index)} className="hover:opacity-70">
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
          onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddKeyword())}
          onBlur={handleAddKeyword}
          placeholder="添加..."
          className="px-2 py-0.5 rounded-full text-xs w-16 bg-transparent border border-dashed outline-none"
          style={{ borderColor: style.border, color: style.text }}
        />
      )}
    </div>
  );
};

/** 自然语言因果链输入组件 */
const CausalChainInput: React.FC<{
  ruleId: number;
  onAdd: () => void;
}> = ({ ruleId, onAdd }) => {
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState<{ attribute: string; performance: string; use: string[]; style: string } | null>(null);
  
  // 示例话术（包含风格维度）
  const examples = [
    '吊带连衣裙，显瘦显腿长，适合海边度假，浪漫风格',
    '高领毛衣保暖显气质，适合冬季约会，温柔优雅风',
    '阔腿裤宽松舒适不挑腿型，日常通勤百搭，休闲简约风',
  ];
  
  const handleParse = async () => {
    if (!inputValue.trim()) return;
    setLoading(true);
    
    try {
      // 调用 LLM 解析自然语言
      const response = await fetch('/api/zara/parse-causal-chain', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: inputValue, ruleId }),
      });
      const data = await response.json();
      if (data.success && data.data) {
        setPreview(data.data);
      }
    } catch (error) {
      console.error('解析失败:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const handleConfirm = async () => {
    if (!preview) return;
    setLoading(true);
    
    try {
      await fetch('/api/zara/causal-chains', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          rule_id: ruleId,
          attribute_cause: preview.attribute,
          performance_effect: preview.performance,
          use_cases: preview.use,
          style_result: preview.style,
        }),
      });
      setInputValue('');
      setPreview(null);
      onAdd();
    } catch (error) {
      console.error('保存失败:', error);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="mb-4 p-3 rounded-lg" style={{ background: 'rgba(139, 92, 246, 0.1)', border: '1px solid rgba(139, 92, 246, 0.2)' }}>
      <p className="text-xs text-purple-400 mb-2">💡 输入一句自然语言描述，系统将自动解析为因果链</p>
      
      {/* 示例 */}
      <div className="flex flex-wrap gap-2 mb-2">
        {examples.map((ex, i) => (
          <button
            key={i}
            onClick={() => setInputValue(ex)}
            className="px-3 py-1 text-xs rounded-full transition-all hover:opacity-80 whitespace-nowrap"
            style={{ background: 'rgba(139, 92, 246, 0.2)', color: '#c4b5fd' }}
          >
            {ex}
          </button>
        ))}
      </div>
      
      {/* 输入框 */}
      <div className="flex gap-2">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="例如：吊带连衣裙，显瘦显腿长，适合海边度假，浪漫风格"
          className="flex-1 px-3 py-2 rounded-lg text-sm bg-slate-800/50 border border-slate-600 text-white outline-none focus:border-purple-500"
        />
        <button
          onClick={handleParse}
          disabled={loading || !inputValue.trim()}
          className="px-4 py-2 rounded-lg text-sm font-medium transition-all disabled:opacity-50"
          style={{ background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.4), rgba(59, 130, 246, 0.3))', color: '#c4b5fd' }}
        >
          {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : '解析'}
        </button>
      </div>
      
      {/* 预览 */}
      {preview && (
        <div className="mt-3 p-2 rounded-lg" style={{ background: 'rgba(255, 255, 255, 0.05)' }}>
          <p className="text-xs text-gray-400 mb-2">解析结果预览：</p>
          <div className="flex items-center gap-2 text-xs flex-wrap">
            <span className="px-2 py-1 rounded bg-blue-500/20 text-blue-300">{preview.attribute}</span>
            <ArrowRight className="w-3 h-3 text-gray-500" />
            <span className="px-2 py-1 rounded bg-green-500/20 text-green-300">{preview.performance}</span>
            <ArrowRight className="w-3 h-3 text-gray-500" />
            <span className="px-2 py-1 rounded bg-purple-500/20 text-purple-300">{preview.use.join(', ')}</span>
            <ArrowRight className="w-3 h-3 text-gray-500" />
            <span className="px-2 py-1 rounded bg-amber-500/20 text-amber-300">{preview.style}</span>
          </div>
          <div className="flex gap-2 mt-2">
            <button
              onClick={handleConfirm}
              disabled={loading}
              className="px-3 py-1 rounded text-xs font-medium"
              style={{ background: 'rgba(34, 197, 94, 0.3)', color: '#86efac' }}
            >
              确认添加
            </button>
            <button
              onClick={() => setPreview(null)}
              className="px-3 py-1 rounded text-xs font-medium"
              style={{ background: 'rgba(239, 68, 68, 0.3)', color: '#fca5a5' }}
            >
              取消
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// Tab 1: 原始规则库组件
// ============================================================================

/** 品类规则卡片 */
const CategoryRuleCard: React.FC<{
  rule: CategoryRule;
  chains: CausalChain[];
  expanded: boolean;
  onToggle: () => void;
  onUpdate: (rule: CategoryRule) => Promise<void>;
}> = ({ rule, chains, expanded, onToggle, onUpdate }) => {
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
  
  return (
    <div
      className="rounded-xl overflow-hidden transition-all duration-300"
      style={{
        background: 'rgba(30, 41, 59, 0.6)',
        backdropFilter: 'blur(10px)',
        border: expanded ? '1px solid rgba(6, 182, 212, 0.4)' : '1px solid rgba(100, 116, 139, 0.2)',
      }}
    >
      {/* 头部 */}
      <div className="flex items-center justify-between p-4 cursor-pointer" onClick={onToggle}>
        <div className="flex items-center gap-3">
          <span
            className="px-3 py-1.5 rounded-lg text-sm font-medium"
            style={{ background: 'rgba(6, 182, 212, 0.2)', border: '0.5px solid rgba(6, 182, 212, 0.4)', color: '#67e8f9' }}
          >
            {rule.category}
          </span>
          <span className="text-gray-400 text-sm">
            {rule.attribute_keywords.length} 属性 · {rule.performance_keywords.length} 性能 · {rule.use_keywords.length} 场景 · {(rule.style_keywords || []).length} 风格
          </span>
          {chains.length > 0 && (
            <span className="text-purple-400 text-sm">· {chains.length} 因果链</span>
          )}
        </div>
        {expanded ? <ChevronUp className="w-5 h-5 text-gray-400" /> : <ChevronDown className="w-5 h-5 text-gray-400" />}
      </div>
      
      {/* 详情 */}
      {expanded && (
        <div className="px-4 pb-4 space-y-4" style={{ borderTop: '1px solid rgba(100, 116, 139, 0.2)' }}>
          {/* 工具栏 */}
          <div className="flex items-center justify-end gap-2 pt-3">
            {editing ? (
              <>
                <button onClick={() => { setEditedRule(rule); setEditing(false); }}
                  className="p-2 rounded-lg" style={{ background: 'rgba(239, 68, 68, 0.2)', border: '0.5px solid rgba(239, 68, 68, 0.4)' }}>
                  <X className="w-4 h-4 text-red-400" />
                </button>
                <button onClick={handleSave} disabled={saving}
                  className="p-2 rounded-lg" style={{ background: 'rgba(34, 197, 94, 0.2)', border: '0.5px solid rgba(34, 197, 94, 0.4)' }}>
                  {saving ? <RefreshCw className="w-4 h-4 text-green-400 animate-spin" /> : <Check className="w-4 h-4 text-green-400" />}
                </button>
              </>
            ) : (
              <button onClick={() => setEditing(true)}
                className="p-2 rounded-lg" style={{ background: 'rgba(59, 130, 246, 0.2)', border: '0.5px solid rgba(59, 130, 246, 0.4)' }}>
                <Edit2 className="w-4 h-4 text-blue-400" />
              </button>
            )}
          </div>
          
          {/* APUS 四维度 */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-3 rounded-lg" style={{ background: 'rgba(59, 130, 246, 0.1)' }}>
              <h4 className="text-xs font-medium text-blue-400 mb-1">Attribute (物理属性)</h4>
              <p className="text-xs text-gray-400 mb-2">{rule.attribute_description}</p>
              <KeywordTags
                keywords={editing ? editedRule.attribute_keywords : rule.attribute_keywords}
                color="blue"
                editable={editing}
                onChange={(kw) => setEditedRule({ ...editedRule, attribute_keywords: kw })}
              />
            </div>
            
            <div className="p-3 rounded-lg" style={{ background: 'rgba(34, 197, 94, 0.1)' }}>
              <h4 className="text-xs font-medium text-green-400 mb-1">Performance (性能)</h4>
              <p className="text-xs text-gray-400 mb-2">{rule.performance_description}</p>
              <KeywordTags
                keywords={editing ? editedRule.performance_keywords : rule.performance_keywords}
                color="green"
                editable={editing}
                onChange={(kw) => setEditedRule({ ...editedRule, performance_keywords: kw })}
              />
            </div>
            
            <div className="p-3 rounded-lg" style={{ background: 'rgba(139, 92, 246, 0.1)' }}>
              <h4 className="text-xs font-medium text-purple-400 mb-1">Use (使用场景)</h4>
              <p className="text-xs text-gray-400 mb-2">{rule.use_description}</p>
              <KeywordTags
                keywords={editing ? editedRule.use_keywords : rule.use_keywords}
                color="purple"
                editable={editing}
                onChange={(kw) => setEditedRule({ ...editedRule, use_keywords: kw })}
              />
            </div>
            
            <div className="p-3 rounded-lg" style={{ background: 'rgba(245, 158, 11, 0.1)' }}>
              <h4 className="text-xs font-medium text-amber-400 mb-1">Style (风格)</h4>
              <p className="text-xs text-gray-400 mb-2">{rule.style_description}</p>
              <KeywordTags
                keywords={editing ? editedRule.style_keywords : (rule.style_keywords || [])}
                color="amber"
                editable={editing}
                onChange={(kw) => setEditedRule({ ...editedRule, style_keywords: kw })}
              />
            </div>
          </div>
          
          {/* 因果链 */}
          <div className="mt-4">
            <h4 className="text-xs font-medium text-gray-400 mb-2">因果关系链</h4>
            
            {/* 编辑模式下显示自然语言输入 */}
            {editing && (
              <CausalChainInput ruleId={rule.id} onAdd={() => {}} />
            )}
            
            {/* 现有因果链列表 */}
            <div className="space-y-2">
              {chains.map((chain) => (
                <div
                  key={chain.id}
                  className="flex items-center gap-2 p-2 rounded-lg text-xs flex-wrap"
                  style={{ background: 'rgba(255, 255, 255, 0.03)' }}
                >
                  <span className="text-blue-400">{chain.attribute_cause}</span>
                  <ArrowRight className="w-3 h-3 text-gray-500" />
                  <span className="text-green-400">{chain.performance_effect}</span>
                  <ArrowRight className="w-3 h-3 text-gray-500" />
                  <span className="text-purple-400">{chain.use_cases.join(', ')}</span>
                  {chain.style_result && (
                    <>
                      <ArrowRight className="w-3 h-3 text-gray-500" />
                      <span className="text-amber-400">{chain.style_result}</span>
                    </>
                  )}
                </div>
              ))}
              {chains.length === 0 && !editing && (
                <p className="text-xs text-gray-500">暂无因果链</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

/** 原始规则库 Tab */
const OriginalRulesTab: React.FC = () => {
  const [rules, setRules] = useState<CategoryRule[]>([]);
  const [chains, setChains] = useState<CausalChain[]>([]);
  const [chainsByRuleId, setChainsByRuleId] = useState<Record<number, CausalChain[]>>({});
  const [loading, setLoading] = useState(true);
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());
  
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/zara/apu-rules/original');
      const data = await response.json();
      if (data.success) {
        setRules(data.data.rules);
        setChains(data.data.chains);
        setChainsByRuleId(data.data.chainsByRuleId);
      }
    } catch (error) {
      console.error('加载规则失败:', error);
    } finally {
      setLoading(false);
    }
  }, []);
  
  useEffect(() => { loadData(); }, [loadData]);
  
  const handleUpdateRule = async (rule: CategoryRule) => {
    try {
      const response = await fetch('/api/zara/apu-rules/original', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: 'rule', ...rule }),
      });
      const data = await response.json();
      if (data.success) {
        setRules((prev) => prev.map((r) => (r.id === rule.id ? { ...r, ...rule } : r)));
      }
    } catch (error) {
      console.error('更新失败:', error);
    }
  };
  
  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin" />
      </div>
    );
  }
  
  return (
    <div className="space-y-4">
      {/* 说明 */}
      <div className="p-4 rounded-xl" style={{ background: 'rgba(6, 182, 212, 0.1)', border: '1px solid rgba(6, 182, 212, 0.2)' }}>
        <div className="flex items-start gap-3">
          <BookOpen className="w-5 h-5 text-cyan-400 shrink-0 mt-0.5" />
          <div className="text-sm">
            <p className="text-cyan-400 font-medium mb-1">什么是原始规则库？</p>
            <p className="text-gray-400">
              这是 LLM 分析商品时的参考规则。每个品类定义了可能的属性、性能、场景和风格关键词，
              以及因果关系链（如"凉感面料 → 凉爽透气 → 夏季日常 → 简约百搭"）。
              修改这些规则后，重新运行商品分析可以得到更准确的结果。
            </p>
          </div>
        </div>
      </div>
      
      {/* 统计 */}
      <div className="flex items-center justify-between">
        <span className="text-gray-400">共 {rules.length} 个品类规则 · {chains.length} 条因果链</span>
        <button onClick={loadData} className="p-2 rounded-lg hover:bg-slate-700/50">
          <RefreshCw className={cn('w-4 h-4 text-gray-400', loading && 'animate-spin')} />
        </button>
      </div>
      
      {/* 规则列表 */}
      <div className="space-y-3">
        {rules.map((rule) => (
          <CategoryRuleCard
            key={rule.id}
            rule={rule}
            chains={chainsByRuleId[rule.id] || []}
            expanded={expandedIds.has(rule.id)}
            onToggle={() => {
              setExpandedIds((prev) => {
                const next = new Set(prev);
                next.has(rule.id) ? next.delete(rule.id) : next.add(rule.id);
                return next;
              });
            }}
            onUpdate={handleUpdateRule}
          />
        ))}
      </div>
    </div>
  );
};

// ============================================================================
// Tab 2: 商品分析结果组件
// ============================================================================

/** 商品规则卡片 */
const ProductRuleCard: React.FC<{
  rule: ProductRule;
  expanded: boolean;
  onToggle: () => void;
  onUpdate: (rule: ProductRule) => Promise<void>;
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
  
  const handleToggleFeatured = async () => {
    await onUpdate({ ...rule, is_featured: !rule.is_featured });
  };
  
  return (
    <div
      className="rounded-xl overflow-hidden transition-all duration-300"
      style={{
        background: 'rgba(30, 41, 59, 0.6)',
        backdropFilter: 'blur(10px)',
        border: expanded ? '1px solid rgba(59, 130, 246, 0.4)' : '1px solid rgba(100, 116, 139, 0.2)',
      }}
    >
      <div className="flex items-center justify-between p-4 cursor-pointer" onClick={onToggle}>
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <span className="px-2 py-1 rounded-lg text-xs font-medium shrink-0"
            style={{ background: 'rgba(6, 182, 212, 0.2)', border: '0.5px solid rgba(6, 182, 212, 0.4)', color: '#67e8f9' }}>
            {rule.category}
          </span>
          <span className="text-white font-medium truncate" title={rule.product_description}>
            {rule.product_description}
          </span>
          {rule.is_featured && <Star className="w-4 h-4 shrink-0" style={{ color: '#fbbf24', fill: '#fbbf24' }} />}
        </div>
        {expanded ? <ChevronUp className="w-5 h-5 text-gray-400" /> : <ChevronDown className="w-5 h-5 text-gray-400" />}
      </div>
      
      {expanded && (
        <div className="px-4 pb-4 space-y-4" style={{ borderTop: '1px solid rgba(100, 116, 139, 0.2)' }}>
          <div className="flex items-center justify-end gap-2 pt-3">
            <button onClick={handleToggleFeatured}
              className="p-2 rounded-lg transition-colors"
              style={{ background: rule.is_featured ? 'rgba(251, 191, 36, 0.2)' : 'rgba(100, 116, 139, 0.2)' }}
              title={rule.is_featured ? '取消精选' : '标为精选'}>
              {rule.is_featured ? <StarOff className="w-4 h-4" style={{ color: '#fbbf24' }} /> : <Star className="w-4 h-4 text-gray-400" />}
            </button>
            {editing ? (
              <>
                <button onClick={() => { setEditedRule(rule); setEditing(false); }}
                  className="p-2 rounded-lg" style={{ background: 'rgba(239, 68, 68, 0.2)' }}>
                  <X className="w-4 h-4 text-red-400" />
                </button>
                <button onClick={handleSave} disabled={saving}
                  className="p-2 rounded-lg" style={{ background: 'rgba(34, 197, 94, 0.2)' }}>
                  {saving ? <RefreshCw className="w-4 h-4 text-green-400 animate-spin" /> : <Check className="w-4 h-4 text-green-400" />}
                </button>
              </>
            ) : (
              <button onClick={() => setEditing(true)}
                className="p-2 rounded-lg" style={{ background: 'rgba(59, 130, 246, 0.2)' }}>
                <Edit2 className="w-4 h-4 text-blue-400" />
              </button>
            )}
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-3 rounded-lg" style={{ background: 'rgba(59, 130, 246, 0.1)' }}>
              <h4 className="text-xs font-medium text-blue-400 mb-2">Attribute (物理属性)</h4>
              <KeywordTags keywords={editing ? editedRule.attribute_keywords : rule.attribute_keywords}
                color="blue" editable={editing}
                onChange={(kw) => setEditedRule({ ...editedRule, attribute_keywords: kw })} />
            </div>
            <div className="p-3 rounded-lg" style={{ background: 'rgba(34, 197, 94, 0.1)' }}>
              <h4 className="text-xs font-medium text-green-400 mb-2">Performance (性能)</h4>
              <KeywordTags keywords={editing ? editedRule.performance_keywords : rule.performance_keywords}
                color="green" editable={editing}
                onChange={(kw) => setEditedRule({ ...editedRule, performance_keywords: kw })} />
            </div>
            <div className="p-3 rounded-lg" style={{ background: 'rgba(139, 92, 246, 0.1)' }}>
              <h4 className="text-xs font-medium text-purple-400 mb-2">Use (使用场景)</h4>
              <KeywordTags keywords={editing ? editedRule.use_keywords : rule.use_keywords}
                color="purple" editable={editing}
                onChange={(kw) => setEditedRule({ ...editedRule, use_keywords: kw })} />
            </div>
            <div className="p-3 rounded-lg" style={{ background: 'rgba(245, 158, 11, 0.1)' }}>
              <h4 className="text-xs font-medium text-amber-400 mb-2">Style (风格)</h4>
              <KeywordTags keywords={editing ? editedRule.style_keywords : (rule.style_keywords || [])}
                color="amber" editable={editing}
                onChange={(kw) => setEditedRule({ ...editedRule, style_keywords: kw })} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

/** 商品分析结果 Tab */
const ProductResultsTab: React.FC = () => {
  const [rules, setRules] = useState<ProductRule[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [selectedCategory, setSelectedCategory] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());
  const [showFilters, setShowFilters] = useState(false);
  
  const loadRules = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: page.toString(), pageSize: pageSize.toString() });
      if (selectedCategory) params.set('category', selectedCategory);
      if (searchQuery) params.set('search', searchQuery);
      
      const response = await fetch(`/api/zara/apu-rules?${params}`);
      const data = await response.json();
      if (data.success && data.data) {
        setRules(data.data.rules);
        setTotal(data.data.total);
        setCategories(data.data.categories);
      }
    } catch (error) {
      console.error('加载失败:', error);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, selectedCategory, searchQuery]);
  
  useEffect(() => { loadRules(); }, [page, selectedCategory]);
  
  const handleUpdateRule = async (rule: ProductRule) => {
    try {
      const response = await fetch('/api/zara/apu-rules', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(rule),
      });
      const data = await response.json();
      if (data.success) {
        setRules((prev) => prev.map((r) => (r.id === rule.id ? { ...r, ...rule } : r)));
      }
    } catch (error) {
      console.error('更新失败:', error);
    }
  };
  
  if (loading && rules.length === 0) {
    return (
      <div className="flex items-center justify-center py-20">
        <RefreshCw className="w-8 h-8 text-blue-400 animate-spin" />
      </div>
    );
  }
  
  return (
    <div className="space-y-4">
      {/* 说明 */}
      <div className="p-4 rounded-xl" style={{ background: 'rgba(59, 130, 246, 0.1)', border: '1px solid rgba(59, 130, 246, 0.2)' }}>
        <div className="flex items-start gap-3">
          <Package className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" />
          <div className="text-sm">
            <p className="text-blue-400 font-medium mb-1">什么是商品分析结果？</p>
            <p className="text-gray-400">
              这是使用原始规则库对每个商品进行 LLM 分析后的结果。
              包含商品的核心描述和提取出的 APUS 四维度信息（属性、性能、场景、风格）。
              这些数据用于向量化搜索，让用户能用自然语言找到商品。
            </p>
          </div>
        </div>
      </div>
      
      {/* 搜索筛选 */}
      <div className="flex flex-col md:flex-row gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input type="text" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && loadRules()}
            placeholder="搜索商品描述..."
            className="w-full pl-10 pr-4 py-2 rounded-xl bg-slate-700/50 border border-slate-600 text-white placeholder:text-gray-400 outline-none focus:border-blue-500" />
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setShowFilters(!showFilters)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl transition-all"
            style={{ background: showFilters ? 'rgba(59, 130, 246, 0.2)' : 'rgba(100, 116, 139, 0.2)' }}>
            <Filter className="w-4 h-4" />
            筛选
          </button>
          <button onClick={loadRules}
            className="px-4 py-2 rounded-xl" style={{ background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)', color: 'white' }}>
            搜索
          </button>
        </div>
      </div>
      
      {showFilters && (
        <div className="flex flex-wrap gap-2 pt-2">
          <button onClick={() => setSelectedCategory('')}
            className="px-3 py-1.5 rounded-lg text-sm"
            style={{ background: !selectedCategory ? 'rgba(59, 130, 246, 0.3)' : 'rgba(100, 116, 139, 0.2)', color: !selectedCategory ? '#93c5fd' : '#94a3b8' }}>
            全部
          </button>
          {categories.map((cat) => (
            <button key={cat} onClick={() => setSelectedCategory(cat)}
              className="px-3 py-1.5 rounded-lg text-sm"
              style={{ background: selectedCategory === cat ? 'rgba(59, 130, 246, 0.3)' : 'rgba(100, 116, 139, 0.2)', color: selectedCategory === cat ? '#93c5fd' : '#94a3b8' }}>
              {cat}
            </button>
          ))}
        </div>
      )}
      
      {/* 统计 */}
      <div className="flex items-center justify-between">
        <span className="text-gray-400">共 {total} 条结果{selectedCategory && ` · ${selectedCategory}`}</span>
        <button onClick={loadRules} className="p-2 rounded-lg hover:bg-slate-700/50">
          <RefreshCw className={cn('w-4 h-4 text-gray-400', loading && 'animate-spin')} />
        </button>
      </div>
      
      {/* 列表 */}
      <div className="space-y-3">
        {rules.map((rule) => (
          <ProductRuleCard key={rule.id} rule={rule}
            expanded={expandedIds.has(rule.id)}
            onToggle={() => {
              setExpandedIds((prev) => {
                const next = new Set(prev);
                next.has(rule.id) ? next.delete(rule.id) : next.add(rule.id);
                return next;
              });
            }}
            onUpdate={handleUpdateRule} />
        ))}
      </div>
      
      {/* 分页 */}
      {total > pageSize && (
        <div className="flex items-center justify-center gap-2 mt-6">
          <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
            className="px-4 py-2 rounded-lg disabled:opacity-50"
            style={{ background: 'rgba(100, 116, 139, 0.2)', color: '#94a3b8' }}>
            上一页
          </button>
          <span className="text-gray-400 px-4">{page} / {Math.ceil(total / pageSize)}</span>
          <button onClick={() => setPage((p) => p + 1)} disabled={page >= Math.ceil(total / pageSize)}
            className="px-4 py-2 rounded-lg disabled:opacity-50"
            style={{ background: 'rgba(100, 116, 139, 0.2)', color: '#94a3b8' }}>
            下一页
          </button>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// Tab 3: 标签个性化规则组件（基于标签维护，影响多个商品）
// ============================================================================

/** 标签规则类型 */
interface TagPersonaRule {
  id: number;
  tag_name: string;
  tag_type: string;
  region_south_weight: number;
  region_north_weight: number;
  season_tags: string[];
  style_tags: string[];
  audience_tags: string[];
  affected_product_count: number;
  notes: string | null;
  updated_at: string;
}

/** 标签规则卡片 */
const TagRuleCard: React.FC<{
  rule: TagPersonaRule;
  onUpdate: (id: number, data: Partial<TagPersonaRule>) => void;
}> = ({ rule, onUpdate }) => {
  const [editing, setEditing] = useState(false);
  const [localRule, setLocalRule] = useState({
    region_south_weight: rule.region_south_weight,
    region_north_weight: rule.region_north_weight,
  });

  const handleSave = () => {
    onUpdate(rule.id, localRule);
    setEditing(false);
  };

  // 标签类型颜色
  const typeColors: Record<string, { bg: string; text: string }> = {
    attribute: { bg: 'rgba(59, 130, 246, 0.2)', text: '#93c5fd' },
    performance: { bg: 'rgba(34, 197, 94, 0.2)', text: '#86efac' },
    use: { bg: 'rgba(139, 92, 246, 0.2)', text: '#c4b5fd' },
    style: { bg: 'rgba(236, 72, 153, 0.2)', text: '#f9a8d4' },
    category: { bg: 'rgba(6, 182, 212, 0.2)', text: '#67e8f9' },
  };
  const typeColor = typeColors[rule.tag_type] || typeColors.attribute;

  // 南北方偏好指示
  const getSouthNorthIndicator = () => {
    const diff = rule.region_south_weight - rule.region_north_weight;
    if (diff > 0.3) return { text: '南方偏好', color: '#fcd34d' };
    if (diff < -0.3) return { text: '北方偏好', color: '#60a5fa' };
    return { text: '通用', color: '#9ca3af' };
  };
  const indicator = getSouthNorthIndicator();

  return (
    <div className="rounded-xl overflow-hidden" style={{ background: 'rgba(30, 41, 59, 0.6)', border: '1px solid rgba(100, 116, 139, 0.2)' }}>
      <div className="flex items-center justify-between p-4">
        <div className="flex items-center gap-3">
          {/* 标签名称 */}
          <span
            className="px-3 py-1.5 rounded-lg text-sm font-medium"
            style={{ background: typeColor.bg, color: typeColor.text }}
          >
            {rule.tag_name}
          </span>
          {/* 标签类型 */}
          <span className="text-xs text-gray-500">
            {rule.tag_type === 'attribute' ? '属性' : 
             rule.tag_type === 'performance' ? '性能' : 
             rule.tag_type === 'use' ? '场景' : 
             rule.tag_type === 'style' ? '风格' : '品类'}
          </span>
          {/* 影响商品数 */}
          <span className="text-xs px-2 py-0.5 rounded-full bg-slate-700/50 text-gray-400">
            影响 {rule.affected_product_count} 件商品
          </span>
        </div>
        
        <div className="flex items-center gap-2">
          {/* 南北偏好指示 */}
          <span className="text-xs px-2 py-0.5 rounded-full" style={{ background: `${indicator.color}20`, color: indicator.color }}>
            {indicator.text}
          </span>
          {/* 编辑按钮 */}
          <button
            onClick={() => editing ? handleSave() : setEditing(true)}
            className="p-2 rounded-lg hover:bg-slate-700/50"
          >
            {editing ? <Check className="w-4 h-4 text-green-400" /> : <Edit2 className="w-4 h-4 text-gray-400" />}
          </button>
        </div>
      </div>

      {/* 编辑区域 */}
      {editing && (
        <div className="px-4 pb-4 space-y-3" style={{ borderTop: '1px solid rgba(100, 116, 139, 0.2)' }}>
          {/* 南北权重滑块 */}
          <div className="grid grid-cols-2 gap-4 pt-3">
            <div>
              <p className="text-xs text-amber-400 mb-2">南方权重: {localRule.region_south_weight.toFixed(2)}</p>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={localRule.region_south_weight}
                onChange={(e) => setLocalRule({ ...localRule, region_south_weight: parseFloat(e.target.value) })}
                className="w-full h-2 rounded-lg appearance-none cursor-pointer"
                style={{ background: `linear-gradient(to right, #fcd34d 0%, #fcd34d ${localRule.region_south_weight * 100}%, rgba(100, 116, 139, 0.3) ${localRule.region_south_weight * 100}%, rgba(100, 116, 139, 0.3) 100%)` }}
              />
            </div>
            <div>
              <p className="text-xs text-blue-400 mb-2">北方权重: {localRule.region_north_weight.toFixed(2)}</p>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={localRule.region_north_weight}
                onChange={(e) => setLocalRule({ ...localRule, region_north_weight: parseFloat(e.target.value) })}
                className="w-full h-2 rounded-lg appearance-none cursor-pointer"
                style={{ background: `linear-gradient(to right, #60a5fa 0%, #60a5fa ${localRule.region_north_weight * 100}%, rgba(100, 116, 139, 0.3) ${localRule.region_north_weight * 100}%, rgba(100, 116, 139, 0.3) 100%)` }}
              />
            </div>
          </div>
          
          {/* 季节和风格标签 */}
          <div className="flex flex-wrap gap-2">
            {(rule.season_tags || []).map((t) => (
              <span key={t} className="px-2 py-0.5 text-xs rounded-full bg-cyan-500/20 text-cyan-300">{t}</span>
            ))}
            {(rule.style_tags || []).map((t) => (
              <span key={t} className="px-2 py-0.5 text-xs rounded-full bg-purple-500/20 text-purple-300">{t}</span>
            ))}
            {(rule.audience_tags || []).map((t) => (
              <span key={t} className="px-2 py-0.5 text-xs rounded-full bg-pink-500/20 text-pink-300">{t}</span>
            ))}
          </div>
          
          {rule.notes && (
            <p className="text-xs text-gray-500">{rule.notes}</p>
          )}
        </div>
      )}
    </div>
  );
};

/** 标签个性化规则 Tab */
const PersonaTagsTab: React.FC = () => {
  const [rules, setRules] = useState<TagPersonaRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState<string>('');
  const [typeCounts, setTypeCounts] = useState<Record<string, number>>({
    attribute: 0,
    performance: 0,
    use: 0,
    style: 0,
  });
  const [total, setTotal] = useState(0);

  const loadRules = useCallback(async () => {
    setLoading(true);
    try {
      const url = filterType 
        ? `/api/zara/tag-persona-rules?tagType=${filterType}` 
        : '/api/zara/tag-persona-rules';
      const response = await fetch(url);
      const data = await response.json();
      if (data.success) {
        setRules(data.data || []);
        if (data.typeCounts) {
          setTypeCounts(data.typeCounts);
        }
        if (data.total !== undefined) {
          setTotal(data.total);
        }
      }
    } catch (error) {
      console.error('加载失败:', error);
    } finally {
      setLoading(false);
    }
  }, [filterType]);

  useEffect(() => {
    loadRules();
  }, [loadRules]);

  const handleUpdateRule = async (id: number, data: Partial<TagPersonaRule>) => {
    try {
      await fetch('/api/zara/tag-persona-rules', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, ...data }),
      });
      loadRules();
    } catch (error) {
      console.error('更新失败:', error);
    }
  };

  // 类型名称映射
  const typeLabels: Record<string, string> = {
    '': '全部',
    'attribute': '属性',
    'performance': '性能',
    'use': '场景',
    'style': '风格',
  };

  if (loading && rules.length === 0) {
    return (
      <div className="flex items-center justify-center py-20">
        <RefreshCw className="w-8 h-8 text-amber-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 说明 */}
      <div className="p-4 rounded-xl" style={{ background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.1), rgba(236, 72, 153, 0.1))', border: '1px solid rgba(245, 158, 11, 0.2)' }}>
        <div className="flex items-start gap-3">
          <MapPin className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="text-sm">
            <p className="text-amber-400 font-medium mb-1">千人千面个性化规则（基于标签）</p>
            <p className="text-gray-400">
              通过维护标签级别的区域偏好权重，实现千人千面推荐。
              例如：将"短袖"标签的南方权重设为 0.8、北方权重设为 0.3，
              则南方用户搜索时会优先看到短袖商品。
              每个标签会影响多个商品，定期异步更新，无需实时计算。
            </p>
          </div>
        </div>
      </div>

      {/* 筛选和统计 */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <span className="text-gray-400 text-sm">筛选：</span>
          {['', 'attribute', 'performance', 'use', 'style'].map((type) => {
            const count = type === '' ? total : typeCounts[type] || 0;
            const label = type === '' ? '全部' : 
              type === 'attribute' ? '属性' : 
              type === 'performance' ? '性能' : 
              type === 'use' ? '场景' : '风格';
            return (
              <button
                key={type}
                onClick={() => setFilterType(type)}
                className={cn(
                  'px-3 py-1 text-xs rounded-full transition-all',
                  filterType === type
                    ? 'bg-amber-500/30 text-amber-300'
                    : 'bg-slate-700/50 text-gray-400 hover:bg-slate-600/50'
                )}
              >
                {label} ({count})
              </button>
            );
          })}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-gray-400 text-sm">共 {rules.length} 个标签规则</span>
          <button onClick={loadRules} className="p-2 rounded-lg hover:bg-slate-700/50">
            <RefreshCw className={cn('w-4 h-4 text-gray-400', loading && 'animate-spin')} />
          </button>
        </div>
      </div>

      {/* 列表 */}
      <div className="space-y-2">
        {rules.map((rule) => (
          <TagRuleCard key={rule.id} rule={rule} onUpdate={handleUpdateRule} />
        ))}
        {rules.length === 0 && (
          <p className="text-center text-gray-500 py-8">暂无标签规则</p>
        )}
      </div>
    </div>
  );
};

// ============================================================================
// 主页面
// ============================================================================

export default function APURulesPage() {
  const [activeTab, setActiveTab] = useState<'original' | 'results' | 'persona'>('original');
  
  return (
    <div className="min-h-screen">
      {/* 页面标题 */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, #8b5cf6, #3b82f6)', boxShadow: '0 4px 20px rgba(139, 92, 246, 0.4)' }}>
            <Brain className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold"
              style={{ background: 'linear-gradient(90deg, #c4b5fd, #93c5fd)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              商品理解管理
            </h1>
            <p className="text-sm text-gray-400">APUS 四维度：属性(A) · 性能(P) · 场景(U) · 风格(S)</p>
          </div>
        </div>
      </div>
      
      {/* Tab 切换 */}
      <div className="flex gap-2 mb-6 flex-wrap">
        <button onClick={() => setActiveTab('original')}
          className={cn('flex items-center gap-2 px-4 py-2.5 rounded-xl font-medium transition-all')}
          style={{
            background: activeTab === 'original' ? 'linear-gradient(135deg, rgba(6, 182, 212, 0.3), rgba(59, 130, 246, 0.2))' : 'rgba(100, 116, 139, 0.2)',
            border: activeTab === 'original' ? '1px solid rgba(6, 182, 212, 0.5)' : '1px solid rgba(100, 116, 139, 0.3)',
            color: activeTab === 'original' ? '#67e8f9' : '#94a3b8',
          }}>
          <BookOpen className="w-4 h-4" />
          原始规则库
        </button>
        <button onClick={() => setActiveTab('results')}
          className={cn('flex items-center gap-2 px-4 py-2.5 rounded-xl font-medium transition-all')}
          style={{
            background: activeTab === 'results' ? 'linear-gradient(135deg, rgba(59, 130, 246, 0.3), rgba(139, 92, 246, 0.2))' : 'rgba(100, 116, 139, 0.2)',
            border: activeTab === 'results' ? '1px solid rgba(59, 130, 246, 0.5)' : '1px solid rgba(100, 116, 139, 0.3)',
            color: activeTab === 'results' ? '#93c5fd' : '#94a3b8',
          }}>
          <Package className="w-4 h-4" />
          商品分析结果
        </button>
        <button onClick={() => setActiveTab('persona')}
          className={cn('flex items-center gap-2 px-4 py-2.5 rounded-xl font-medium transition-all')}
          style={{
            background: activeTab === 'persona' ? 'linear-gradient(135deg, rgba(245, 158, 11, 0.3), rgba(236, 72, 153, 0.2))' : 'rgba(100, 116, 139, 0.2)',
            border: activeTab === 'persona' ? '1px solid rgba(245, 158, 11, 0.5)' : '1px solid rgba(100, 116, 139, 0.3)',
            color: activeTab === 'persona' ? '#fcd34d' : '#94a3b8',
          }}>
          <MapPin className="w-4 h-4" />
          商品个性化标签
        </button>
      </div>
      
      {/* Tab 内容 */}
      {activeTab === 'original' && <OriginalRulesTab />}
      {activeTab === 'results' && <ProductResultsTab />}
      {activeTab === 'persona' && <PersonaTagsTab />}
    </div>
  );
}
