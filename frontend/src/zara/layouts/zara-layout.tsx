/**
 * ZARA 项目布局组件 - Liquid Glass 风格
 * 
 * 使用页面: app/zara/* 所有页面
 * 功能: 提供左侧导航 + 右侧主内容区域的布局结构
 * 
 * 设计参考: Apple 2025 Liquid Glass Design
 * - 毛玻璃效果 (backdrop-filter: blur)
 * - 渐变透明背景
 * - 内阴影光泽效果
 */

'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import ZaraSidebar from '../components/zara-sidebar';

interface ZaraLayoutProps {
  children: React.ReactNode;
  className?: string;
}

/**
 * ZARA 项目布局
 * 包含左侧导航栏和右侧主内容区域
 */
export default function ZaraLayout({ children, className }: ZaraLayoutProps) {
  return (
    <div
      className={cn(
        'min-h-screen relative overflow-hidden',
        className
      )}
      style={{
        // 海滩背景图 - 更清爽的视觉效果
        backgroundImage: `url('https://images.unsplash.com/photo-1507525428034-b723cf961d3e?q=80&w=2073&auto=format&fit=crop')`,
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        backgroundAttachment: 'fixed',
      }}
    >
      {/* 深色遮罩层 - 提高内容可读性 */}
      <div 
        className="absolute inset-0 pointer-events-none"
        style={{
          background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.75) 0%, rgba(30, 41, 59, 0.65) 100%)',
        }}
      />

      {/* 主布局 */}
      <div className="relative flex h-screen">
        {/* 左侧导航 */}
        <ZaraSidebar />

        {/* 右侧主内容 */}
        <main className="flex-1 overflow-auto">
          <div className="min-h-full p-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
