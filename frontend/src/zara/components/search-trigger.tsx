/**
 * 搜索触发器组件 - Liquid Glass 风格
 * 
 * 使用页面: zara/pages/product-search.tsx
 * 功能: 点击后打开 AI 搜索 Modal 的搜索栏
 * 
 * 设计参考: Apple 2025 Liquid Glass Design
 */

'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import { Search, Sparkles } from 'lucide-react';

interface SearchTriggerProps {
  onClick: () => void;
  className?: string;
}

/**
 * 搜索触发器 - 科技感设计
 */
export default function SearchTrigger({ onClick, className }: SearchTriggerProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full max-w-2xl mx-auto',
        'flex items-center gap-4 px-6 py-4',
        'rounded-2xl',
        'transition-all duration-300',
        'group',
        'hover:scale-[1.02]',
        className
      )}
      style={{
        // 深色背景 + 科技感边框
        background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.9) 0%, rgba(30, 41, 59, 0.85) 100%)',
        backdropFilter: 'blur(20px) saturate(180%)',
        border: '1px solid rgba(59, 130, 246, 0.3)',
        boxShadow: `
          0 8px 32px rgba(0, 0, 0, 0.3),
          0 0 0 1px rgba(59, 130, 246, 0.1),
          inset 0 1px 0 rgba(255, 255, 255, 0.05)
        `,
      }}
    >
      {/* 搜索图标 - 渐变色按钮 */}
      <div 
        className={cn(
          'w-11 h-11 rounded-xl',
          'flex items-center justify-center',
          'transition-all duration-300',
          'group-hover:scale-110 group-hover:rotate-3'
        )}
        style={{
          background: 'linear-gradient(135deg, #06b6d4 0%, #3b82f6 50%, #8b5cf6 100%)',
          boxShadow: `
            0 4px 20px rgba(59, 130, 246, 0.4),
            0 2px 8px rgba(6, 182, 212, 0.3)
          `,
        }}
      >
        <Search className="w-5 h-5 text-white" />
      </div>

      {/* 提示文字 */}
      <div className="flex-1 text-left">
        <p 
          className="text-base font-medium"
          style={{ color: 'rgba(226, 232, 240, 0.95)' }}
        >
          搜索商品...
        </p>
        <p 
          className="text-xs mt-0.5"
          style={{ color: 'rgba(148, 163, 184, 0.8)' }}
        >
          支持文字描述和图片搜索
        </p>
      </div>

      {/* AI 标识 - 科技感渐变徽章 */}
      <div 
        className="flex items-center gap-1.5 px-4 py-2 rounded-full text-xs font-semibold"
        style={{
          background: 'linear-gradient(135deg, #06b6d4 0%, #3b82f6 50%, #8b5cf6 100%)',
          boxShadow: `
            0 4px 16px rgba(59, 130, 246, 0.4),
            0 2px 8px rgba(139, 92, 246, 0.3),
            inset 0 1px 0 rgba(255, 255, 255, 0.2)
          `,
          color: 'white',
          textShadow: '0 1px 2px rgba(0, 0, 0, 0.2)',
        }}
      >
        <Sparkles className="w-3.5 h-3.5" />
        AI 搜索
      </div>
    </button>
  );
}
