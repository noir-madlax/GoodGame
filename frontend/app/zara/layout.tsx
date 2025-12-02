/**
 * ZARA 模块布局
 * 
 * 路由: /zara/*
 * 功能: 为所有 ZARA 子页面提供统一的布局结构
 */

import ZaraLayout from '@/zara/layouts/zara-layout';

export default function Layout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <ZaraLayout>{children}</ZaraLayout>;
}

