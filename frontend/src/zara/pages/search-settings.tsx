/**
 * 搜索权重设置页面 - Liquid Glass 风格
 * 
 * 路由: /zara/search-settings
 * 功能: 配置和调整搜索相关参数
 * 
 * 配置分类:
 *   - weights: 搜索权重（向量/标签/RRF）
 *   - apu: APU 三维度权重
 *   - general: 基础配置（模型、阈值等）
 */

'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { cn } from '@/lib/utils';
import { 
  Settings, 
  Save, 
  RefreshCw, 
  Sliders,
  Cpu,
  Scale,
  Check,
  AlertCircle,
  Info,
} from 'lucide-react';

// ============================================================================
// 类型定义
// ============================================================================

interface SearchConfig {
  id: number;
  config_key: string;
  config_value: unknown;
  description: string | null;
  category: string;
  updated_at: string;
}

// ============================================================================
// 组件
// ============================================================================

/** 滑块输入组件 */
const SliderInput: React.FC<{
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  label: string;
  description?: string;
  color: string;
}> = ({ value, onChange, min = 0, max = 1, step = 0.05, label, description, color }) => {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div>
          <span className="text-white font-medium">{label}</span>
          {description && (
            <p className="text-xs text-gray-400 mt-0.5">{description}</p>
          )}
        </div>
        <span 
          className="text-lg font-bold px-3 py-1 rounded-lg"
          style={{ background: `${color}20`, color }}
        >
          {typeof value === 'number' ? value.toFixed(2) : value}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full h-2 rounded-lg appearance-none cursor-pointer"
        style={{
          background: `linear-gradient(to right, ${color} 0%, ${color} ${((value - min) / (max - min)) * 100}%, rgba(100, 116, 139, 0.3) ${((value - min) / (max - min)) * 100}%, rgba(100, 116, 139, 0.3) 100%)`,
        }}
      />
      <div className="flex justify-between text-xs text-gray-500">
        <span>{min}</span>
        <span>{max}</span>
      </div>
    </div>
  );
};

/** 数字输入组件 */
const NumberInput: React.FC<{
  value: number;
  onChange: (value: number) => void;
  label: string;
  description?: string;
  min?: number;
  max?: number;
}> = ({ value, onChange, label, description, min, max }) => {
  return (
    <div className="space-y-2">
      <div>
        <span className="text-white font-medium">{label}</span>
        {description && (
          <p className="text-xs text-gray-400 mt-0.5">{description}</p>
        )}
      </div>
      <input
        type="number"
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
        min={min}
        max={max}
        className="w-full px-4 py-2 rounded-xl bg-slate-700/50 border border-slate-600 text-white outline-none focus:border-blue-500"
      />
    </div>
  );
};

/** 文本输入组件 */
const TextInput: React.FC<{
  value: string;
  onChange: (value: string) => void;
  label: string;
  description?: string;
  readOnly?: boolean;
}> = ({ value, onChange, label, description, readOnly }) => {
  return (
    <div className="space-y-2">
      <div>
        <span className="text-white font-medium">{label}</span>
        {description && (
          <p className="text-xs text-gray-400 mt-0.5">{description}</p>
        )}
      </div>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        readOnly={readOnly}
        className={cn(
          "w-full px-4 py-2 rounded-xl bg-slate-700/50 border border-slate-600 text-white outline-none focus:border-blue-500",
          readOnly && "opacity-60 cursor-not-allowed"
        )}
      />
    </div>
  );
};

/** 配置卡片组件 */
const ConfigCard: React.FC<{
  title: string;
  icon: React.ReactNode;
  color: string;
  children: React.ReactNode;
}> = ({ title, icon, color, children }) => {
  return (
    <div
      className="rounded-xl overflow-hidden"
      style={{
        background: 'rgba(30, 41, 59, 0.6)',
        backdropFilter: 'blur(10px)',
        border: `1px solid ${color}30`,
      }}
    >
      <div 
        className="px-4 py-3 flex items-center gap-2"
        style={{ background: `${color}10`, borderBottom: `1px solid ${color}20` }}
      >
        <span style={{ color }}>{icon}</span>
        <h3 className="font-medium" style={{ color }}>{title}</h3>
      </div>
      <div className="p-4 space-y-4">
        {children}
      </div>
    </div>
  );
};

// ============================================================================
// 主页面
// ============================================================================

export default function SearchSettingsPage() {
  // 配置状态
  const [configs, setConfigs] = useState<SearchConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 本地编辑状态
  const [localValues, setLocalValues] = useState<Record<string, unknown>>({});
  const [hasChanges, setHasChanges] = useState(false);

  /**
   * 加载配置
   */
  const loadConfigs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/zara/search-config');
      const data = await response.json();
      if (data.success) {
        setConfigs(data.data.configs);
        // 初始化本地值
        const values: Record<string, unknown> = {};
        for (const config of data.data.configs) {
          values[config.config_key] = config.config_value;
        }
        setLocalValues(values);
        setHasChanges(false);
      } else {
        setError(data.error);
      }
    } catch (err) {
      setError('加载配置失败');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * 保存配置
   */
  const saveConfigs = useCallback(async () => {
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      const configsToUpdate = Object.entries(localValues).map(([config_key, config_value]) => ({
        config_key,
        config_value,
      }));

      const response = await fetch('/api/zara/search-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ configs: configsToUpdate }),
      });

      const data = await response.json();
      if (data.success) {
        setSaved(true);
        setHasChanges(false);
        setTimeout(() => setSaved(false), 3000);
      } else {
        setError(data.error || '保存失败');
      }
    } catch (err) {
      setError('保存配置失败');
      console.error(err);
    } finally {
      setSaving(false);
    }
  }, [localValues]);

  /**
   * 更新本地值
   */
  const updateValue = useCallback((key: string, value: unknown) => {
    setLocalValues((prev) => ({ ...prev, [key]: value }));
    setHasChanges(true);
  }, []);

  /**
   * 获取配置值
   */
  const getValue = useCallback((key: string, defaultValue: unknown = 0) => {
    const value = localValues[key];
    if (value === undefined || value === null) return defaultValue;
    if (typeof value === 'string') {
      // 尝试解析字符串（如 "0.9" 或 '"model-name"'）
      try {
        return JSON.parse(value);
      } catch {
        return value;
      }
    }
    return value;
  }, [localValues]);

  /**
   * 初始加载
   */
  useEffect(() => {
    loadConfigs();
  }, [loadConfigs]);

  return (
    <div className="min-h-screen">
      {/* 页面标题 */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div 
              className="w-10 h-10 rounded-xl flex items-center justify-center"
              style={{ 
                background: 'linear-gradient(135deg, #f59e0b, #ef4444)', 
                boxShadow: '0 4px 20px rgba(245, 158, 11, 0.4)' 
              }}
            >
              <Settings className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 
                className="text-2xl font-bold"
                style={{ 
                  background: 'linear-gradient(90deg, #fcd34d, #f87171)', 
                  WebkitBackgroundClip: 'text', 
                  WebkitTextFillColor: 'transparent' 
                }}
              >
                搜索权重设置
              </h1>
              <p className="text-sm text-gray-400">
                配置搜索参数和 APU 权重
              </p>
            </div>
          </div>

          {/* 操作按钮 */}
          <div className="flex items-center gap-3">
            {saved && (
              <span className="flex items-center gap-1 text-green-400 text-sm">
                <Check className="w-4 h-4" />
                已保存
              </span>
            )}
            {error && (
              <span className="flex items-center gap-1 text-red-400 text-sm">
                <AlertCircle className="w-4 h-4" />
                {error}
              </span>
            )}
            <button
              onClick={loadConfigs}
              disabled={loading}
              className="p-2 rounded-lg transition-colors hover:bg-slate-700/50"
            >
              <RefreshCw className={cn("w-5 h-5 text-gray-400", loading && "animate-spin")} />
            </button>
            <button
              onClick={saveConfigs}
              disabled={saving || !hasChanges}
              className={cn(
                "flex items-center gap-2 px-4 py-2 rounded-xl font-medium transition-all",
                hasChanges 
                  ? "bg-gradient-to-r from-amber-500 to-orange-500 text-white" 
                  : "bg-slate-700/50 text-gray-400 cursor-not-allowed"
              )}
            >
              {saving ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <Save className="w-4 h-4" />
              )}
              保存设置
            </button>
          </div>
        </div>
      </div>

      {/* 加载中 */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <RefreshCw className="w-8 h-8 text-amber-400 animate-spin" />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 多模态搜索权重 */}
          <ConfigCard
            title="多模态搜索权重"
            icon={<Scale className="w-5 h-5" />}
            color="#3b82f6"
          >
            <div 
              className="p-3 rounded-lg mb-4 flex items-start gap-2"
              style={{ background: 'rgba(59, 130, 246, 0.1)' }}
            >
              <Info className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
              <p className="text-xs text-gray-400">
                当用户同时使用文字和图片搜索时，这两个权重决定各自的影响程度。权重和应为 1。
              </p>
            </div>

            <SliderInput
              value={Number(getValue('text_search_weight', 0.5))}
              onChange={(v) => updateValue('text_search_weight', v)}
              label="文字搜索权重"
              description="基于文字描述的语义搜索权重"
              color="#3b82f6"
            />

            <SliderInput
              value={Number(getValue('image_search_weight', 0.5))}
              onChange={(v) => updateValue('image_search_weight', v)}
              label="图片搜索权重"
              description="基于图片相似度的搜索权重"
              color="#8b5cf6"
            />

            {/* 权重总和提示 */}
            <div 
              className="p-3 rounded-lg flex items-center justify-between"
              style={{ 
                background: 'rgba(100, 116, 139, 0.1)',
                border: '1px solid rgba(100, 116, 139, 0.2)'
              }}
            >
              <span className="text-gray-400 text-sm">多模态权重总和</span>
              <span 
                className={cn(
                  "font-bold",
                  Math.abs(
                    Number(getValue('text_search_weight', 0.5)) +
                    Number(getValue('image_search_weight', 0.5)) - 1
                  ) < 0.01 ? "text-green-400" : "text-amber-400"
                )}
              >
                {(
                  Number(getValue('text_search_weight', 0.5)) +
                  Number(getValue('image_search_weight', 0.5))
                ).toFixed(2)}
              </span>
            </div>

            <NumberInput
              value={Number(getValue('rrf_k', 50))}
              onChange={(v) => updateValue('rrf_k', v)}
              label="RRF k 参数"
              description="Reciprocal Rank Fusion 融合参数"
              min={1}
              max={100}
            />

            <NumberInput
              value={Number(getValue('match_count', 50))}
              onChange={(v) => updateValue('match_count', v)}
              label="最大返回数量"
              description="搜索返回的最大结果数"
              min={10}
              max={200}
            />

            <SliderInput
              value={Number(getValue('min_similarity', 0.3))}
              onChange={(v) => updateValue('min_similarity', v)}
              label="最小相似度阈值"
              description="低于此阈值的结果将被过滤"
              color="#22c55e"
            />
          </ConfigCard>

          {/* APUS 四维度权重 */}
          <ConfigCard
            title="APUS 四维度权重"
            icon={<Sliders className="w-5 h-5" />}
            color="#8b5cf6"
          >
            <div 
              className="p-3 rounded-lg mb-4 flex items-start gap-2"
              style={{ background: 'rgba(139, 92, 246, 0.1)' }}
            >
              <Info className="w-4 h-4 text-purple-400 shrink-0 mt-0.5" />
              <p className="text-xs text-gray-400">
                APUS 四维度：属性(A) · 性能(P) · 场景(U) · 风格(S)。权重影响搜索匹配优先级。
              </p>
            </div>

            <SliderInput
              value={Number(getValue('apu_attribute_weight', 0.35))}
              onChange={(v) => updateValue('apu_attribute_weight', v)}
              label="Attribute 权重 (属性)"
              description="外观、材质、版型等物理特征"
              color="#3b82f6"
            />

            <SliderInput
              value={Number(getValue('apu_performance_weight', 0.25))}
              onChange={(v) => updateValue('apu_performance_weight', v)}
              label="Performance 权重 (性能)"
              description="舒适度、保暖性、透气性等功能表现"
              color="#22c55e"
            />

            <SliderInput
              value={Number(getValue('apu_use_weight', 0.25))}
              onChange={(v) => updateValue('apu_use_weight', v)}
              label="Use 权重 (场景)"
              description="日常、通勤、约会等适用场合"
              color="#f59e0b"
            />

            <SliderInput
              value={Number(getValue('apu_style_weight', 0.15))}
              onChange={(v) => updateValue('apu_style_weight', v)}
              label="Style 权重 (风格)"
              description="简约、时尚、复古等风格偏好"
              color="#ec4899"
            />

            {/* 权重总和提示 */}
            <div 
              className="p-3 rounded-lg flex items-center justify-between"
              style={{ 
                background: 'rgba(100, 116, 139, 0.1)',
                border: '1px solid rgba(100, 116, 139, 0.2)'
              }}
            >
              <span className="text-gray-400 text-sm">APUS 权重总和</span>
              <span 
                className={cn(
                  "font-bold",
                  Math.abs(
                    Number(getValue('apu_attribute_weight', 0.35)) +
                    Number(getValue('apu_performance_weight', 0.25)) +
                    Number(getValue('apu_use_weight', 0.25)) +
                    Number(getValue('apu_style_weight', 0.15)) - 1
                  ) < 0.01 ? "text-green-400" : "text-amber-400"
                )}
              >
                {(
                  Number(getValue('apu_attribute_weight', 0.35)) +
                  Number(getValue('apu_performance_weight', 0.25)) +
                  Number(getValue('apu_use_weight', 0.25)) +
                  Number(getValue('apu_style_weight', 0.15))
                ).toFixed(2)}
              </span>
            </div>
          </ConfigCard>

          {/* 排序设置 */}
          <ConfigCard
            title="排序设置"
            icon={<Sliders className="w-5 h-5" />}
            color="#ec4899"
          >
            <div 
              className="p-3 rounded-lg mb-4 flex items-start gap-2"
              style={{ background: 'rgba(236, 72, 153, 0.1)' }}
            >
              <Info className="w-4 h-4 text-pink-400 shrink-0 mt-0.5" />
              <p className="text-xs text-gray-400">
                最终排序权重 = 搜索结果权重 + 商品个性化权重 + 用户偏好权重。三者之和建议为 1。
              </p>
            </div>

            <SliderInput
              value={Number(getValue('search_result_weight', 0.5))}
              onChange={(v) => updateValue('search_result_weight', v)}
              label="搜索结果权重"
              description="基于 APUS 四维度的多模态搜索结果权重"
              color="#3b82f6"
            />

            <SliderInput
              value={Number(getValue('persona_tag_weight', 0.3))}
              onChange={(v) => updateValue('persona_tag_weight', v)}
              label="商品个性化标签权重"
              description="基于标签的区域偏好（南方/北方）和风格偏好"
              color="#f59e0b"
            />

            <SliderInput
              value={Number(getValue('user_preference_weight', 0.2))}
              onChange={(v) => updateValue('user_preference_weight', v)}
              label="用户偏好权重"
              description="基于历史对话提取的用户偏好标签"
              color="#ec4899"
            />

            {/* 权重总和提示 */}
            <div 
              className="p-3 rounded-lg flex items-center justify-between mt-2"
              style={{ 
                background: 'rgba(100, 116, 139, 0.1)',
                border: '1px solid rgba(100, 116, 139, 0.2)'
              }}
            >
              <span className="text-gray-400 text-sm">排序权重总和</span>
              <span 
                className={cn(
                  "font-bold",
                  Math.abs(
                    Number(getValue('search_result_weight', 0.5)) +
                    Number(getValue('persona_tag_weight', 0.3)) +
                    Number(getValue('user_preference_weight', 0.2)) - 1
                  ) < 0.01 ? "text-green-400" : "text-amber-400"
                )}
              >
                {(
                  Number(getValue('search_result_weight', 0.5)) +
                  Number(getValue('persona_tag_weight', 0.3)) +
                  Number(getValue('user_preference_weight', 0.2))
                ).toFixed(2)}
              </span>
            </div>
          </ConfigCard>

          {/* 模型配置 */}
          <ConfigCard
            title="模型配置"
            icon={<Cpu className="w-5 h-5" />}
            color="#06b6d4"
          >
            <TextInput
              value={String(getValue('llm_model', 'google/gemini-2.5-flash')).replace(/"/g, '')}
              onChange={(v) => updateValue('llm_model', `"${v}"`)}
              label="LLM 模型"
              description="用于意图解析的大语言模型"
            />

            <SliderInput
              value={Number(getValue('llm_temperature', 0.3))}
              onChange={(v) => updateValue('llm_temperature', v)}
              label="LLM Temperature"
              description="生成多样性参数，越低越确定"
              color="#06b6d4"
            />

            <TextInput
              value={String(getValue('embedding_model', 'text-embedding-3-small')).replace(/"/g, '')}
              onChange={(v) => updateValue('embedding_model', `"${v}"`)}
              label="Embedding 模型"
              description="用于文本向量化的模型"
              readOnly
            />

            <NumberInput
              value={Number(getValue('embedding_dimensions', 1536))}
              onChange={(v) => updateValue('embedding_dimensions', v)}
              label="向量维度"
              description="Embedding 向量的维度"
              min={256}
              max={4096}
            />
          </ConfigCard>

          {/* 使用说明 */}
          <div
            className="rounded-xl p-6"
            style={{
              background: 'rgba(30, 41, 59, 0.6)',
              backdropFilter: 'blur(10px)',
              border: '1px solid rgba(100, 116, 139, 0.2)',
            }}
          >
            <h3 className="text-white font-medium mb-4 flex items-center gap-2">
              <Info className="w-5 h-5 text-gray-400" />
              参数说明
            </h3>
            <div className="space-y-3 text-sm text-gray-400">
              <div>
                <span className="text-blue-400 font-medium">向量搜索权重</span>
                <p className="mt-1">
                  基于语义相似度匹配商品。使用增强文本（包含 APU 三维度信息）进行向量化，
                  能够理解用户的自然语言描述。建议设置较高权重（0.8-0.9）。
                </p>
              </div>
              <div>
                <span className="text-purple-400 font-medium">标签搜索权重</span>
                <p className="mt-1">
                  基于标签精确匹配商品。适合明确的品类筛选。建议设置较低权重（0.1-0.2）。
                </p>
              </div>
              <div>
                <span className="text-amber-400 font-medium">APU 权重</span>
                <p className="mt-1">
                  属性权重最高时，搜索更偏向物理特征（如"短袖"、"圆领"）匹配；
                  性能权重高时偏向功能（如"保暖"、"透气"）；
                  场景权重高时偏向使用场合（如"约会"、"通勤"）。
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

