/**
 * 商品网格组件 - Liquid Glass 风格
 * 
 * 使用页面: zara/pages/product-search.tsx
 * 功能: 以网格形式展示商品卡片列表
 * 
 * 设计参考: Apple 2025 Liquid Glass Design
 */

'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import ProductCard from './product-card';
import type { ProductWithImage } from '../lib/types';
import { Package } from 'lucide-react';

interface ProductGridProps {
  products: ProductWithImage[];
  loading?: boolean;
  onProductClick?: (product: ProductWithImage) => void;
  className?: string;
}

/**
 * 加载骨架屏 - Liquid Glass 风格
 */
function ProductSkeleton() {
  return (
    <div 
      className="rounded-2xl overflow-hidden animate-pulse relative"
      style={{
        background: `linear-gradient(135deg, 
          rgba(255, 255, 255, 0.22) 0%, 
          rgba(255, 255, 255, 0.12) 50%,
          rgba(255, 255, 255, 0.08) 100%
        )`,
        backdropFilter: 'blur(10px) saturate(200%)',
        border: '0.5px solid rgba(255, 255, 255, 0.3)',
        boxShadow: `
          0 8px 32px rgba(0, 0, 0, 0.12),
          inset 5.33px 4px 12px rgba(255, 255, 255, 0.25)
        `,
      }}
    >
      {/* Shimmer 效果 */}
      <div 
        className="absolute inset-0"
        style={{
          background: 'linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.15), transparent)',
          animation: 'shimmer 2s infinite',
        }}
      />
      
      {/* 图片占位 */}
      <div 
        className="aspect-square"
        style={{ background: 'rgba(255, 255, 255, 0.1)' }}
      />
      
      {/* 内容占位 */}
      <div className="p-4 space-y-3">
        <div 
          className="h-4 rounded w-full"
          style={{ background: 'rgba(255, 255, 255, 0.15)' }}
        />
        <div 
          className="h-4 rounded w-3/4"
          style={{ background: 'rgba(255, 255, 255, 0.15)' }}
        />
        <div 
          className="h-6 rounded w-1/3"
          style={{ background: 'rgba(255, 255, 255, 0.15)' }}
        />
        <div 
          className="h-3 rounded w-1/2"
          style={{ background: 'rgba(255, 255, 255, 0.1)' }}
        />
      </div>
    </div>
  );
}

/**
 * 空状态组件 - Liquid Glass 风格
 */
function EmptyState() {
  return (
    <div 
      className="col-span-full flex flex-col items-center justify-center py-20 rounded-2xl"
      style={{
        background: `linear-gradient(135deg, 
          rgba(255, 255, 255, 0.18) 0%, 
          rgba(255, 255, 255, 0.08) 100%
        )`,
        backdropFilter: 'blur(10px)',
        border: '0.5px solid rgba(255, 255, 255, 0.25)',
      }}
    >
      <Package 
        className="w-16 h-16 mb-4" 
        style={{ color: 'rgba(255, 255, 255, 0.4)' }}
      />
      <p 
        className="text-lg font-medium"
        style={{ color: 'rgba(255, 255, 255, 0.8)' }}
      >
        暂无商品
      </p>
      <p 
        className="text-sm mt-1"
        style={{ color: 'rgba(255, 255, 255, 0.5)' }}
      >
        试试其他搜索条件
      </p>
    </div>
  );
}

/**
 * 商品网格 - Liquid Glass 风格
 */
export default function ProductGrid({
  products,
  loading = false,
  onProductClick,
  className,
}: ProductGridProps) {
  // 加载状态显示骨架屏
  if (loading) {
    return (
      <div
        className={cn(
          'grid gap-4',
          'grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5',
          className
        )}
      >
        {Array.from({ length: 10 }).map((_, index) => (
          <ProductSkeleton key={index} />
        ))}
        
        {/* 添加 shimmer 动画 */}
        <style jsx global>{`
          @keyframes shimmer {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(100%); }
          }
        `}</style>
      </div>
    );
  }

  // 空状态
  if (products.length === 0) {
    return (
      <div className={cn('grid', className)}>
        <EmptyState />
      </div>
    );
  }

  // 商品网格
  return (
    <div
      className={cn(
        'grid gap-4',
        'grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5',
        className
      )}
    >
      {products.map((product, index) => (
        <ProductCard
          key={`${product.id}-${index}`}
          product={product}
          onClick={onProductClick}
        />
      ))}
    </div>
  );
}
