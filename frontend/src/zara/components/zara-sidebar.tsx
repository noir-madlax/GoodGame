/**
 * ZARA 左侧导航栏组件 - Liquid Glass 风格
 * 
 * 使用页面: zara/layouts/zara-layout.tsx
 * 功能: 显示 ZARA 项目的一级导航菜单
 * 
 * 设计参考: Apple 2025 Liquid Glass Design
 */

'use client';

import React from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { cn } from '@/lib/utils';
import { 
  Package, 
  Sparkles,
} from 'lucide-react';

/**
 * 导航项配置
 */
interface NavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  path: string;
}

/**
 * 导航菜单配置
 */
const navItems: NavItem[] = [
  {
    id: 'products',
    label: '商品搜索',
    icon: <Package className="w-5 h-5" />,
    path: '/zara/products',
  },
];

/**
 * ZARA 左侧导航栏 - Liquid Glass 风格
 */
export default function ZaraSidebar() {
  const pathname = usePathname();
  const router = useRouter();

  /**
   * 处理导航点击
   */
  const handleNavClick = (path: string) => {
    router.push(path);
  };

  return (
    <aside 
      className="w-64 h-screen flex flex-col"
      style={{
        // 深色半透明背景 - 更好的对比度
        background: `linear-gradient(180deg, 
          rgba(15, 23, 42, 0.9) 0%, 
          rgba(30, 41, 59, 0.85) 100%
        )`,
        backdropFilter: 'blur(20px) saturate(180%)',
        borderRight: '1px solid rgba(100, 116, 139, 0.3)',
        boxShadow: `
          4px 0 24px rgba(0, 0, 0, 0.3),
          inset -1px 0 0 rgba(255, 255, 255, 0.05)
        `,
      }}
    >
      {/* Logo 区域 */}
      <div 
        className="p-6"
        style={{
          borderBottom: '1px solid rgba(100, 116, 139, 0.2)',
        }}
      >
        <div className="flex items-center gap-3">
          {/* ZARA Logo - 渐变色图标 */}
          <div 
            className="w-11 h-11 rounded-xl flex items-center justify-center"
            style={{
              background: 'linear-gradient(135deg, #06b6d4 0%, #3b82f6 50%, #8b5cf6 100%)',
              boxShadow: `
                0 4px 20px rgba(59, 130, 246, 0.4),
                0 2px 8px rgba(6, 182, 212, 0.3)
              `,
            }}
          >
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 
              className="text-lg font-bold tracking-wide"
              style={{
                background: 'linear-gradient(90deg, #06b6d4 0%, #3b82f6 50%, #8b5cf6 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
              }}
            >
              ZARA 搜索
            </h1>
            <p 
              className="text-xs"
              style={{
                color: 'rgba(148, 163, 184, 0.9)',
              }}
            >
              智能商品搜索
            </p>
          </div>
        </div>
      </div>

      {/* 导航菜单 */}
      <nav className="flex-1 p-4 space-y-2">
        {navItems.map((item) => {
          const isActive = pathname === item.path || pathname?.startsWith(item.path + '/');
          
          return (
            <button
              key={item.id}
              onClick={() => handleNavClick(item.path)}
              className={cn(
                'w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300',
                'text-left font-medium',
                'hover:bg-slate-700/50'
              )}
              style={{
                background: isActive 
                  ? 'linear-gradient(135deg, rgba(59, 130, 246, 0.2) 0%, rgba(139, 92, 246, 0.15) 100%)'
                  : 'transparent',
                border: isActive 
                  ? '1px solid rgba(59, 130, 246, 0.4)' 
                  : '1px solid transparent',
                boxShadow: isActive 
                  ? '0 4px 16px rgba(59, 130, 246, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.05)'
                  : 'none',
                color: isActive ? '#60a5fa' : 'rgba(203, 213, 225, 0.9)',
              }}
            >
              {item.icon}
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>
    </aside>
  );
}
