// 中文设计说明：
// 本文件提供首页（内容仪表盘）的一次性返回缓存能力：
// - 仅在从详情页返回首页时生效；其他路径（直达、刷新）不触发数据水合。
// - 将大体量数据（列表、KPI/图表数据等）缓存在内存（模块级单例），TTL=10分钟。
// - 将轻量视图状态（filters/排序/图表层级/滚动位置）存入 sessionStorage，便于初始化与体验优化。

export type FiltersStateLite = {
  timeRange: string;
  relevance: string[];
  priority: string[];
  creatorTypes: string[];
  platforms: string[];
};

export type GlobalMapsLite = {
  relevanceMap: Record<string, string>;
  severityMap: Record<string, string>;
  creatorTypeMap: Record<string, string>;
};

export type DashboardSnapshot = {
  // 视图状态
  filters: FiltersStateLite;
  oldestFirst: boolean;
  chartState: { level: "primary" | "secondary" | "tertiary"; selectedRelevance?: string; selectedSeverity?: string };
  scrollY: number;
  // 列表与分页
  page: number;
  hasMore: boolean;
  allRows: unknown[];
  posts: unknown[];
  totalCount: number;
  // 映射
  risks: Record<string, string[]>;
  sentiments: Record<string, string>;
  relevances: Record<string, string>;
  totalRiskCn: Record<string, string>;
  totalRiskReason: Record<string, string>;
  influencerMap: Record<string, boolean>;
  // KPI/图表数据
  globalPostsLite: { id: number; platform: string; platform_item_id: string }[];
  globalMaps: GlobalMapsLite;
  kpiPrev: { prev: { id: number; platform: string; platform_item_id: string }[]; label?: string };
};

type CacheItem = { snapshot: DashboardSnapshot; ts: number };

const CACHE_TTL_MS = 10 * 60 * 1000; // 10分钟
const CACHE = new Map<string, CacheItem>();

const RETURN_ONCE_FLAG = "dashboard_cache_use_once";
const VIEW_STATE_KEY = "dashboard_view_state";

export const buildCacheKey = (filters: FiltersStateLite, oldestFirst: boolean) => {
  // 稳定化 key：按字段顺序序列化
  const keyObj = {
    timeRange: filters.timeRange,
    relevance: [...filters.relevance].sort(),
    priority: [...filters.priority].sort(),
    creatorTypes: [...filters.creatorTypes].sort(),
    platforms: [...filters.platforms].sort(),
    oldestFirst: Boolean(oldestFirst),
  };
  return `v1:${JSON.stringify(keyObj)}`;
};

export const saveSnapshot = (cacheKey: string, snapshot: DashboardSnapshot) => {
  CACHE.set(cacheKey, { snapshot, ts: Date.now() });
};

export const getSnapshotIfFresh = (cacheKey: string): DashboardSnapshot | null => {
  const item = CACHE.get(cacheKey);
  if (!item) return null;
  if (Date.now() - item.ts > CACHE_TTL_MS) {
    CACHE.delete(cacheKey);
    return null;
  }
  return item.snapshot;
};

export const setReturnOnceMarker = (cacheKey: string) => {
  try {
    const payload = { cacheKey, ts: Date.now() };
    sessionStorage.setItem(RETURN_ONCE_FLAG, JSON.stringify(payload));
  } catch (_) {
    // ignore
  }
};

export const consumeReturnOnceMarker = (): { cacheKey: string; ts: number } | null => {
  try {
    const raw = sessionStorage.getItem(RETURN_ONCE_FLAG);
    if (!raw) return null;
    sessionStorage.removeItem(RETURN_ONCE_FLAG);
    const obj = JSON.parse(raw) as { cacheKey: string; ts: number };
    if (!obj || !obj.cacheKey) return null;
    if (Date.now() - obj.ts > CACHE_TTL_MS) return null;
    return obj;
  } catch (_) {
    return null;
  }
};

// 仅读取一次性标记但不消费（用于首渲染前同步判断）
export const peekReturnOnceMarker = (): { cacheKey: string; ts: number } | null => {
  try {
    const raw = sessionStorage.getItem(RETURN_ONCE_FLAG);
    if (!raw) return null;
    const obj = JSON.parse(raw) as { cacheKey: string; ts: number };
    if (!obj || !obj.cacheKey) return null;
    if (Date.now() - obj.ts > CACHE_TTL_MS) return null;
    return obj;
  } catch (_) {
    return null;
  }
};

// 轻量视图状态：仅用于初始化体验，与一次性数据水合解耦
export const saveViewState = (state: { filters: FiltersStateLite; oldestFirst: boolean; chartState: DashboardSnapshot["chartState"]; scrollY: number }) => {
  try {
    sessionStorage.setItem(VIEW_STATE_KEY, JSON.stringify(state));
  } catch (_) {
    // ignore
  }
};

export const loadViewState = (): { filters: FiltersStateLite; oldestFirst: boolean; chartState: DashboardSnapshot["chartState"]; scrollY: number } | null => {
  try {
    const raw = sessionStorage.getItem(VIEW_STATE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch (_) {
    return null;
  }
};


