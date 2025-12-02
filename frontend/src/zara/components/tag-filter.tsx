/**
 * 标签筛选器组件 - Liquid Glass 风格
 * 
 * 使用页面: zara/pages/product-search.tsx
 * 功能: 按标签类型分组展示可选标签，支持多选筛选
 * 
 * 设计参考: Apple 2025 Liquid Glass Design
 */

'use client';

import React, { useState } from 'react';
import { cn } from '@/lib/utils';
import { ChevronDown, ChevronUp } from 'lucide-react';
import type { TagGroup, TagType } from '../lib/types';

interface TagFilterProps {
  tagGroups: TagGroup[];
  selectedTags: Record<TagType, string[]>;
  onTagChange: (type: TagType, value: string, selected: boolean) => void;
  className?: string;
}

/**
 * 标签筛选器 - Liquid Glass 风格
 */
export default function TagFilter({
  tagGroups,
  selectedTags,
  onTagChange,
  className,
}: TagFilterProps) {
  // 控制每个分组的展开状态
  // 默认展开: 性别、季节、品类、材质、特征
  const [expandedGroups, setExpandedGroups] = useState<Set<TagType>>(
    new Set(['gender', 'season', 'category', 'material', 'feature'])
  );

  /**
   * 切换分组展开状态
   */
  const toggleGroup = (type: TagType) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(type)) {
        next.delete(type);
      } else {
        next.add(type);
      }
      return next;
    });
  };

  /**
   * 检查标签是否被选中
   */
  const isTagSelected = (type: TagType, value: string): boolean => {
    return selectedTags[type]?.includes(value) || false;
  };

  /**
   * 处理标签点击
   */
  const handleTagClick = (type: TagType, value: string) => {
    const selected = isTagSelected(type, value);
    onTagChange(type, value, !selected);
  };

  if (tagGroups.length === 0) {
    return null;
  }

  return (
    <div className={cn('space-y-3', className)}>
      {tagGroups.map((group) => {
        const isExpanded = expandedGroups.has(group.type);
        const selectedCount = selectedTags[group.type]?.length || 0;

        return (
          <div
            key={group.type}
            className="rounded-2xl overflow-hidden"
            style={{
              // Liquid Glass 效果
              background: `linear-gradient(135deg, 
                rgba(255, 255, 255, 0.18) 0%, 
                rgba(255, 255, 255, 0.08) 100%
              )`,
              backdropFilter: 'blur(10px) saturate(200%)',
              border: '0.5px solid rgba(255, 255, 255, 0.25)',
              boxShadow: `
                0 4px 16px rgba(0, 0, 0, 0.08),
                inset 3px 2px 8px rgba(255, 255, 255, 0.2)
              `,
            }}
          >
            {/* 分组标题 */}
            <button
              onClick={() => toggleGroup(group.type)}
              className={cn(
                'w-full flex items-center justify-between px-4 py-3',
                'transition-all duration-200'
              )}
              style={{
                borderBottom: isExpanded ? '0.5px solid rgba(255, 255, 255, 0.15)' : 'none',
              }}
            >
              <div className="flex items-center gap-2">
                <span 
                  className="font-medium"
                  style={{ color: 'white' }}
                >
                  {group.label}
                </span>
                {selectedCount > 0 && (
                  <span 
                    className="px-2 py-0.5 text-xs rounded-full"
                    style={{
                      background: 'rgba(255, 255, 255, 0.25)',
                      color: 'white',
                    }}
                  >
                    {selectedCount}
                  </span>
                )}
              </div>
              {isExpanded ? (
                <ChevronUp className="w-4 h-4" style={{ color: 'rgba(255, 255, 255, 0.6)' }} />
              ) : (
                <ChevronDown className="w-4 h-4" style={{ color: 'rgba(255, 255, 255, 0.6)' }} />
              )}
            </button>

            {/* 标签列表 */}
            {isExpanded && (
              <div className="px-4 pb-4 pt-2 flex flex-wrap gap-2">
                {group.tags.map((tag) => {
                  const selected = isTagSelected(group.type, tag.tag_value);

                  return (
                    <button
                      key={tag.tag_value}
                      onClick={() => handleTagClick(group.type, tag.tag_value)}
                      className={cn(
                        'px-3 py-1.5 rounded-full text-sm',
                        'transition-all duration-200'
                      )}
                      style={{
                        background: selected
                          ? 'rgba(255, 255, 255, 0.35)'
                          : 'rgba(255, 255, 255, 0.12)',
                        border: selected
                          ? '0.5px solid rgba(255, 255, 255, 0.5)'
                          : '0.5px solid rgba(255, 255, 255, 0.2)',
                        color: selected ? 'white' : 'rgba(255, 255, 255, 0.8)',
                        boxShadow: selected
                          ? 'inset 2px 2px 6px rgba(255, 255, 255, 0.2)'
                          : 'none',
                      }}
                    >
                      {tag.tag_value}
                      <span 
                        className="ml-1.5 text-xs"
                        style={{ color: selected ? 'rgba(255, 255, 255, 0.7)' : 'rgba(255, 255, 255, 0.5)' }}
                      >
                        {tag.count}
                      </span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
