/**
 * 仪表盘状态缓存工具
 * 说明：用于在列表页与详情页之间保留筛选条件与已加载数据，避免返回首页时重新请求。
 */
import type { FiltersState } from "@/polymet/components/analytics/filter-section";
import type { AnalysisMaps } from "@/polymet/lib/analytics";

/**
 * 功能：缓存监控列表中的帖子数据结构。
 * 说明：字段来自 gg_platform_post 与前端计算结果，用于在返回首页时快速恢复 UI。
 */
export type DashboardPostRow = {
  id: number;
  platform: string;
  platform_item_id: string;
  author_id?: string | null;
  title: string;
  original_url?: string | null;
  like_count: number;
  comment_count: number;
  share_count: number;
  cover_url: string | null;
  author_name: string | null;
  author_follower_count?: number | null;
  duration_ms: number;
  published_at: string | null;
  created_at: string;
  is_marked?: boolean | null;
  relevant_status?: string | null;
};

/**
 * 功能：缓存首页涉及的全部状态，包含筛选、分页与衍生图表数据。
 */
export type DashboardCacheState = {
  projectId: string | null;
  filters: FiltersState;
  oldestFirst: boolean;
  page: number;
  hasMore: boolean;
  totalCount: number;
  allRows: DashboardPostRow[];
  posts: DashboardPostRow[];
  risks: Record<string, string[]>;
  sentiments: Record<string, string>;
  relevances: Record<string, string>;
  totalRiskCn: Record<string, string>;
  totalRiskReason: Record<string, string>;
  influencerMap: Record<string, boolean>;
  globalPostsLite: { id: number; platform: string; platform_item_id: string }[];
  globalMaps: AnalysisMaps;
  kpiPrev: { prev: { id: number; platform: string; platform_item_id: string }[]; label?: string };
  globalTotalCount: number; // SQL层面的真实总数（用于KPI显示）
  globalPreviousTotalCount: number; // 上一周期的真实总数
  chartState: { level: "primary" | "secondary" | "tertiary"; selectedRelevance?: string; selectedSeverity?: string };
  scrollTop: number;
  lastUpdated: number;
};

/**
 * 功能：模块级缓存对象。
 * 说明：保持在内存中，浏览器刷新会失效，满足返回上一层的需求即可。
 */
let dashboardCache: DashboardCacheState | null = null;

/**
 * 功能：标记缓存是否需要强制刷新。
 * 场景：详情页执行“标记内容”等操作后需要让首页重新加载。
 */
let cacheDirty = false;

/**
 * 功能：读取缓存。
 */
export const getDashboardCache = () => dashboardCache;

/**
 * 功能：写入缓存。
 * 说明：写入时会自动清除脏标记，表示数据为最新。
 */
export const setDashboardCache = (next: DashboardCacheState) => {
  dashboardCache = { ...next };
  cacheDirty = false;
};

/**
 * 功能：仅更新缓存中的滚动位置。
 * 说明：当离开首页前记录 scrollTop 时使用，保持其余数据不变。
 */
export const updateDashboardScrollTop = (scrollTop?: number) => {
  if (!dashboardCache) return;
  let next = scrollTop;
  if (typeof next !== "number") {
    const container = document.querySelector(DASHBOARD_SCROLL_SELECTOR);
    if (container instanceof HTMLElement) {
      next = container.scrollTop;
    } else {
      next = typeof window !== "undefined" ? window.scrollY : 0;
    }
  }
  dashboardCache = { ...dashboardCache, scrollTop: next || 0 };
};

/**
 * 功能：清空缓存。
 * 场景：切换项目或执行“重置筛选”时调用，避免旧数据干扰。
 */
export const clearDashboardCache = () => {
  dashboardCache = null;
  cacheDirty = false;
};

/**
 * 功能：将缓存标记为脏数据。
 * 场景：详情页修改了列表项（例如标记内容）后，首页需要重新加载。
 */
export const markDashboardCacheDirty = () => {
  cacheDirty = true;
};

/**
 * 功能：判断缓存是否已失效。
 */
export const isDashboardCacheDirty = () => cacheDirty;

export const DASHBOARD_SCROLL_SELECTOR = '[data-dashboard-scroll-container="true"]';

