/**
 * 商品卡片组件 - Liquid Glass 风格
 * 
 * 使用页面: zara/pages/product-search.tsx
 * 功能: 展示单个商品的卡片视图
 * 
 * 设计参考: Apple 2025 Liquid Glass Design
 */

'use client';

import React, { useState } from 'react';
import { cn } from '@/lib/utils';
import { MapPin, ShoppingBag } from 'lucide-react';
import type { ProductWithImage } from '../lib/types';

interface ProductCardProps {
  product: ProductWithImage;
  onClick?: (product: ProductWithImage) => void;
  className?: string;
}

/**
 * 商品卡片 - Liquid Glass 风格
 */
export default function ProductCard({ 
  product, 
  onClick,
  className 
}: ProductCardProps) {
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);

  // 优先使用 Storage URL，其次使用原始 URL
  const imageUrl = product.storage_url || product.main_image_url;

  /**
   * 处理卡片点击
   */
  const handleClick = () => {
    onClick?.(product);
  };

  /**
   * 格式化价格显示
   */
  const formatPrice = (price: number | null): string => {
    if (price === null || price === undefined) return '--';
    return `¥${price.toFixed(2)}`;
  };

  return (
    <div
      onClick={handleClick}
      className={cn(
        'group rounded-2xl overflow-hidden cursor-pointer',
        'transition-all duration-300',
        'hover:scale-[1.02] hover:-translate-y-1',
        className
      )}
      style={{
        // Liquid Glass 效果
        background: `linear-gradient(135deg, 
          rgba(255, 255, 255, 0.22) 0%, 
          rgba(255, 255, 255, 0.12) 50%,
          rgba(255, 255, 255, 0.08) 100%
        )`,
        backdropFilter: 'blur(10px) saturate(200%)',
        border: '0.5px solid rgba(255, 255, 255, 0.3)',
        boxShadow: `
          0 8px 32px rgba(0, 0, 0, 0.12),
          0 2px 8px rgba(0, 0, 0, 0.08),
          inset 5.33px 4px 12px rgba(255, 255, 255, 0.25)
        `,
      }}
    >
      {/* 顶部高光边 */}
      <div 
        className="absolute top-0 left-0 right-0 h-px rounded-t-2xl"
        style={{
          background: 'linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.5), transparent)',
        }}
      />

      {/* 图片区域 */}
      <div 
        className="relative aspect-square overflow-hidden"
        style={{
          background: 'rgba(0, 0, 0, 0.15)',
        }}
      >
        {/* 加载占位 */}
        {!imageLoaded && !imageError && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div 
              className="w-8 h-8 rounded-full animate-spin"
              style={{
                border: '2px solid rgba(255, 255, 255, 0.3)',
                borderTopColor: 'rgba(255, 255, 255, 0.8)',
              }}
            />
          </div>
        )}

        {/* 商品图片 */}
        {imageUrl && !imageError ? (
          <img
            src={imageUrl}
            alt={product.item_name}
            className={cn(
              'w-full h-full object-cover transition-all duration-500',
              'group-hover:scale-105',
              imageLoaded ? 'opacity-100' : 'opacity-0'
            )}
            onLoad={() => setImageLoaded(true)}
            onError={() => setImageError(true)}
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center">
            <ShoppingBag className="w-12 h-12" style={{ color: 'rgba(255, 255, 255, 0.4)' }} />
          </div>
        )}
      </div>

      {/* 信息区域 */}
      <div className="p-4 space-y-3">
        {/* 商品名称 */}
        <h3 
          className="text-sm font-medium leading-tight line-clamp-2 min-h-[2.5rem]"
          title={product.item_name}
          style={{ 
            color: 'white',
            textShadow: '0 1px 4px rgba(0, 0, 0, 0.2)',
          }}
        >
          {product.item_name}
        </h3>

        {/* 价格 */}
        <div className="flex items-baseline gap-2">
          <span 
            className="text-lg font-bold"
            style={{ 
              color: '#ff6b6b',
              textShadow: '0 2px 8px rgba(255, 107, 107, 0.3)',
            }}
          >
            {formatPrice(product.price_yuan)}
          </span>
          {product.discount_price_yuan && product.discount_price_yuan < product.price_yuan && (
            <span 
              className="text-xs line-through"
              style={{ color: 'rgba(255, 255, 255, 0.5)' }}
            >
              {formatPrice(product.discount_price_yuan)}
            </span>
          )}
        </div>

        {/* 发货地和销量 */}
        <div 
          className="flex items-center justify-between text-xs"
          style={{ color: 'rgba(255, 255, 255, 0.6)' }}
        >
          {/* 发货地 */}
          <div className="flex items-center gap-1">
            <MapPin className="w-3 h-3" />
            <span>{product.item_loc || '未知'}</span>
          </div>

          {/* 销量 */}
          {product.order_count && (
            <span>销量 {product.order_count}</span>
          )}
        </div>

        {/* 标签 */}
        {product.tags && product.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 pt-1">
            {product.tags.slice(0, 3).map((tag, index) => (
              <span
                key={index}
                className="px-2 py-0.5 text-xs rounded-full"
                style={{
                  background: 'rgba(255, 255, 255, 0.15)',
                  color: 'rgba(255, 255, 255, 0.8)',
                  border: '0.5px solid rgba(255, 255, 255, 0.2)',
                }}
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
