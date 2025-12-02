/**
 * ZARA 模块首页 - 重定向到商品搜索页
 * 
 * 路由: /zara
 * 功能: 自动重定向到 /zara/products
 */

import { redirect } from 'next/navigation';

export default function ZaraPage() {
  redirect('/zara/products');
}

