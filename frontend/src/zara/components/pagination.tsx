/**
 * 分页组件 - Liquid Glass 风格
 * 
 * 使用页面: zara/pages/product-search.tsx
 * 功能: 商品列表分页导航
 * 
 * 设计参考: Apple 2025 Liquid Glass Design
 */

'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  className?: string;
}

/**
 * 分页组件 - Liquid Glass 风格
 */
export default function Pagination({
  currentPage,
  totalPages,
  onPageChange,
  className,
}: PaginationProps) {
  if (totalPages <= 1) {
    return null;
  }

  /**
   * 生成页码数组
   */
  const getPageNumbers = (): (number | 'ellipsis')[] => {
    const pages: (number | 'ellipsis')[] = [];
    const delta = 2;

    pages.push(1);

    const rangeStart = Math.max(2, currentPage - delta);
    const rangeEnd = Math.min(totalPages - 1, currentPage + delta);

    if (rangeStart > 2) {
      pages.push('ellipsis');
    }

    for (let i = rangeStart; i <= rangeEnd; i++) {
      pages.push(i);
    }

    if (rangeEnd < totalPages - 1) {
      pages.push('ellipsis');
    }

    if (totalPages > 1) {
      pages.push(totalPages);
    }

    return pages;
  };

  const pageNumbers = getPageNumbers();

  // Liquid Glass 按钮样式
  const buttonStyle = (isActive: boolean, isDisabled: boolean) => ({
    background: isActive
      ? 'rgba(255, 255, 255, 0.35)'
      : 'rgba(255, 255, 255, 0.15)',
    backdropFilter: 'blur(10px)',
    border: isActive
      ? '0.5px solid rgba(255, 255, 255, 0.5)'
      : '0.5px solid rgba(255, 255, 255, 0.25)',
    color: isDisabled ? 'rgba(255, 255, 255, 0.3)' : 'white',
    boxShadow: isActive
      ? 'inset 2px 2px 6px rgba(255, 255, 255, 0.2)'
      : 'none',
    cursor: isDisabled ? 'not-allowed' : 'pointer',
    opacity: isDisabled ? 0.5 : 1,
  });

  return (
    <div className={cn('flex items-center justify-center gap-2', className)}>
      {/* 上一页 */}
      <button
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage === 1}
        className="w-9 h-9 rounded-xl flex items-center justify-center transition-all duration-200"
        style={buttonStyle(false, currentPage === 1)}
      >
        <ChevronLeft className="w-4 h-4" />
      </button>

      {/* 页码 */}
      {pageNumbers.map((page, index) => {
        if (page === 'ellipsis') {
          return (
            <span
              key={`ellipsis-${index}`}
              className="w-9 h-9 flex items-center justify-center"
              style={{ color: 'rgba(255, 255, 255, 0.5)' }}
            >
              ...
            </span>
          );
        }

        const isActive = page === currentPage;

        return (
          <button
            key={page}
            onClick={() => onPageChange(page)}
            className="w-9 h-9 rounded-xl flex items-center justify-center text-sm font-medium transition-all duration-200"
            style={buttonStyle(isActive, false)}
          >
            {page}
          </button>
        );
      })}

      {/* 下一页 */}
      <button
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage === totalPages}
        className="w-9 h-9 rounded-xl flex items-center justify-center transition-all duration-200"
        style={buttonStyle(false, currentPage === totalPages)}
      >
        <ChevronRight className="w-4 h-4" />
      </button>
    </div>
  );
}
