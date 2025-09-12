// 中文说明：
// 本文件集中封装首页分析页所需的统计与数据整形逻辑（纯函数，不触发副作用）。
// 目标：从“已按筛选过滤后的帖子集合 + 分析映射”中，计算 KPI、一级饼图、二级/三级柱状图所需的数据结构。
// 这些结构与 @components/analytics 下的可视化组件一一对应。

export type TimeRangeOption = "今天" | "昨天" | "前天" | "近7天" | "近15天" | "近30天" | "全部时间";

export type SeverityLevel = "高" | "中" | "低" | "未标注";

export interface PostLite {
  id: number;
  platform: string;
  platform_item_id: string;
}

export interface AnalysisMaps {
  // 品牌相关性最终值：优先 gg_video_analysis.brand_relevance；否则回填自 relevant_status
  relevanceMap: Record<string, string | undefined>;
  // 严重程度（P0/P1/P2/... -> 高/中/低/未标注）
  severityMap: Record<string, SeverityLevel>;
  // 创作者类型（达人/素人/未标注）
  creatorTypeMap: Record<string, string>;
}

export interface KPITriple {
  current: number;
  previous: number;
  change: number; // 相对变化百分比，正值表示上升
}

export interface KPIResult {
  totalVideos: KPITriple;
  relevantVideos: KPITriple;
  highPriorityVideos: KPITriple; // 以严重程度=高 计数
}

// ========================= 全库统计：加载与过滤（供首页仪表使用） =========================
// 中文说明：
// - 下面导出的方法用于“首页 KPI 与 内容分布”的全库统计加载。
// - 使用页面同一套筛选（时间/平台/相关性/创作者类型/严重度），但不受列表分页限制。
// - 这些方法会被 `pages/content-dashboard.tsx` 引用。

// 为避免循环依赖，仅从 filters.ts 引入纯工具函数
// 说明：resolveStartAt/ filterByTime / backfillRelevance 用于统一时间与相关性回填逻辑
// 注意路径：同级目录
import { resolveStartAt, filterByTime, backfillRelevance } from "@/polymet/lib/filters";

/**
 * 页面顶层筛选子集（与 FilterSection 对齐）。
 * 只列出会影响“全库统计”的筛选项。
 */
export type GlobalAnalyticsFilters = {
  timeRange: "今天" | "昨天" | "前天" | "近7天" | "近15天" | "近30天" | "全部时间";
  platforms: string[]; // ["抖音","小红书"]
  relevance: string[]; // ["相关","疑似相关","不相关","营销"]; 为空表示全部
  priority: string[]; // ["高","中","低","未标注"]，为空表示全部
  creatorTypes: string[]; // ["达人","素人","未标注"]，为空表示全部
};

export interface GlobalDataset {
  // 被 KPI/图表消费的“全库（已按筛选过滤）帖子样本”
  posts: PostLite[];
  // 与 posts 对应的映射（相关性/严重度/创作者类型）。
  maps: AnalysisMaps;
}

/**
 * 将中文平台标签转为表中的 platform key。
 */
const normalizePlatformLabelToKey = (label: string) => {
  if (!label) return label;
  if (label === "抖音") return "douyin";
  if (label === "小红书") return "xiaohongshu";
  return label;
};

/**
 * 加载“全库数据集”（受筛选控制，不受分页影响）。
 * 注意：该函数在页面端调用（传入 supabase 客户端）。
 * 返回的数据结构可直接喂给 calculateKPI/buildRelevanceChartData/buildSeverity*。
 */
export const loadGlobalDataset = async (
  sb: any,
  filters: GlobalAnalyticsFilters
): Promise<GlobalDataset> => {
  // 1) 拉取基础帖子（时间/平台范围）；不分页
  const { timeRange, platforms } = filters;
  let q = sb
    .from("gg_platform_post")
    .select(
      "id, platform, platform_item_id, published_at, created_at, relevant_status",
      { count: "exact" }
    );
  if (platforms && platforms.length > 0) {
    const keys = platforms.map((p) => normalizePlatformLabelToKey(p));
    q = q.in("platform", keys);
  }
  // 由于时间范围包含“昨天/前天/15天”等，需要前端裁切
  const { data: postRows } = await q.limit(200000); // 安全上限；业务可根据体量调整
  type PostRow = {
    id: number; platform: string; platform_item_id: string;
    published_at?: string | null; created_at: string; relevant_status?: string | null;
  };
  const basePosts = (postRows || []) as PostRow[];
  // 时间过滤（与页面一致）
  const baseStartAt = resolveStartAt(
    timeRange === "今天" ? "today" : timeRange === "近7天" ? "week" : timeRange === "近15天" || timeRange === "近30天" ? "month" : "all"
  );
  let timeFiltered = filterByTime(basePosts, baseStartAt);
  if (timeRange === "昨天") {
    const today = new Date();
    const s = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 1);
    const e = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    timeFiltered = timeFiltered.filter((p) => {
      const t = new Date((p.published_at || p.created_at));
      return t >= s && t < e;
    });
  }
  if (timeRange === "前天") {
    const today = new Date();
    const s = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 2);
    const e = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 1);
    timeFiltered = timeFiltered.filter((p) => {
      const t = new Date((p.published_at || p.created_at));
      return t >= s && t < e;
    });
  }
  if (timeRange === "近15天") {
    const d = new Date(); d.setDate(d.getDate() - 15);
    timeFiltered = filterByTime(timeFiltered, d);
  }

  // 2) 拉取分析映射（brand_relevance/severity/creatorTypes）
  const ids = Array.from(new Set(timeFiltered.map((p) => p.platform_item_id).filter(Boolean)));
  let severityMap: Record<string, SeverityLevel> = {};
  let creatorTypeMap: Record<string, string> = {};
  let relevanceMapRaw: Record<string, string> = {};
  if (ids.length > 0) {
    const { data: aRows } = await sb
      .from("gg_video_analysis")
      .select("platform_item_id, brand_relevance, severity, \"creatorTypes\"")
      .in("platform_item_id", ids);
    type ARow = { platform_item_id: string; brand_relevance?: string | null; severity?: string | null; creatorTypes?: string | null };
    (aRows || []).forEach((r: ARow) => {
      if (!r.platform_item_id) return;
      if (r.brand_relevance) relevanceMapRaw[r.platform_item_id] = String(r.brand_relevance);
      severityMap[r.platform_item_id] = mapDbSeverityToCn(r.severity || "");
      creatorTypeMap[r.platform_item_id] = String(r.creatorTypes || "未标注") || "未标注";
    });
  }

  // 3) 相关性回填（细分覆盖初筛）
  const relevanceMap = backfillRelevance(relevanceMapRaw as Record<string, string>, timeFiltered);

  // 4) 形成 PostLite 与 AnalysisMaps
  let postsLite: PostLite[] = timeFiltered.map((p) => ({ id: p.id, platform: String(p.platform || ""), platform_item_id: p.platform_item_id }));
  const maps: AnalysisMaps = { relevanceMap, severityMap, creatorTypeMap };

  // 5) 应用“全库统计”的筛选（多选）；为空则表示不过滤
  const { relevance, priority, creatorTypes } = filters;
  if (relevance && relevance.length > 0) {
    const set = new Set(relevance.map((s) => (s === "营销内容" ? "营销" : s)));
    postsLite = postsLite.filter((p) => set.has(String(maps.relevanceMap[p.platform_item_id] || "")) || (set.has("营销") && maps.relevanceMap[p.platform_item_id] === "营销内容"));
  }
  if (priority && priority.length > 0) {
    const set = new Set(priority);
    postsLite = postsLite.filter((p) => set.has(maps.severityMap[p.platform_item_id]));
  }
  if (creatorTypes && creatorTypes.length > 0) {
    const set = new Set(creatorTypes);
    postsLite = postsLite.filter((p) => set.has(maps.creatorTypeMap[p.platform_item_id] || "未标注"));
  }

  return { posts: postsLite, maps };
};

/**
 * 将数据库的 severity 文本（如 P0/p0/P1...）映射为中文等级。
 */
export const mapDbSeverityToCn = (val?: string | null): SeverityLevel => {
  const raw = String(val || "").trim().toUpperCase();
  if (raw === "P0") return "高";
  if (raw === "P1") return "中";
  if (raw === "P2") return "低";
  return "未标注";
};

/**
 * 计算 KPI 三项。这里的 previous 仅做示例：按当前值的 80%/85%/90% 估算。
 * 若后续有真实“上一周期”数据，可在此替换来源。
 */
export function calculateKPI(posts: PostLite[], maps: AnalysisMaps): KPIResult {
  const total = posts.length;
  const relevant = posts.filter((p) => {
    const rel = maps.relevanceMap[p.platform_item_id];
    return rel === "相关" || rel === "疑似相关" || rel === "营销" || rel === "营销内容";
  }).length;
  const high = posts.filter((p) => maps.severityMap[p.platform_item_id] === "高").length;

  const triple = (curr: number, prevRatio: number): KPITriple => {
    const previous = Math.round(curr * prevRatio);
    const base = previous === 0 ? 0 : Math.round(((curr - previous) / Math.max(previous, 1)) * 100);
    return { current: curr, previous, change: base };
  };

  return {
    totalVideos: triple(total, 0.8),
    relevantVideos: triple(relevant, 0.85),
    highPriorityVideos: triple(high, 0.9),
  };
}

/**
 * 一级：相关性饼图数据（名称/数量/占比/颜色等）。
 */
export function buildRelevanceChartData(posts: PostLite[], maps: AnalysisMaps) {
  const total = posts.length;
  const normalizeRel = (v?: string) => {
    const s = String(v || "").trim();
    if (s === "需人工介入") return "疑似相关";
    if (s === "可忽略" || s === "无关") return "不相关";
    if (s === "营销内容") return "营销";
    return s;
  };
  const colorMap: Record<string, string> = {
    "相关": "#ef4444",
    "疑似相关": "#f97316",
    "不相关": "#6b7280",
    "营销": "#8b5cf6",
    "营销内容": "#8b5cf6",
  };
  const groups: Record<string, PostLite[]> = { 相关: [], 疑似相关: [], 不相关: [], 营销: [] };
  posts.forEach((p) => {
    const rel = normalizeRel(maps.relevanceMap[p.platform_item_id] || "");
    if (rel === "相关") groups["相关"].push(p);
    else if (rel === "疑似相关") groups["疑似相关"].push(p);
    else if (rel === "不相关") groups["不相关"].push(p);
    else if (rel === "营销" || rel === "营销内容") groups["营销"].push(p);
  });

  const toPlatform = (key: string) => String(key || "");
  const platformCount = (arr: PostLite[], platform: string) => arr.filter((x) => toPlatform(x.platform).includes(platform)).length;

  return ["相关", "疑似相关", "不相关", "营销"].map((name) => {
    const arr = groups[name] || [];
    const value = arr.length;
    const percentage = total > 0 ? Math.round((value / total) * 100 * 10) / 10 : 0;
    return {
      name,
      value,
      percentage,
      color: colorMap[name] || "#6b7280",
      priority: name === "相关" ? ("high" as const) : name === "疑似相关" ? ("medium" as const) : ("low" as const),
      severityBreakdown: {
        高: arr.filter((p) => maps.severityMap[p.platform_item_id] === "高").length,
        中: arr.filter((p) => maps.severityMap[p.platform_item_id] === "中").length,
        低: arr.filter((p) => maps.severityMap[p.platform_item_id] === "低").length,
        未标注: arr.filter((p) => maps.severityMap[p.platform_item_id] === "未标注").length,
      },
      platformBreakdown: {
        抖音: platformCount(arr, "douyin"),
        小红书: platformCount(arr, "xiaohongshu"),
        其他: value - platformCount(arr, "douyin") - platformCount(arr, "xiaohongshu"),
      },
    };
  });
}

/**
 * 二级：严重程度统计（按选中的相关性子集进行分组）。
 */
export function buildSeverityGroups(selectedRelevance: string, posts: PostLite[], maps: AnalysisMaps) {
  const normalizeRel = (v?: string) => {
    const s = String(v || "").trim();
    if (s === "需人工介入") return "疑似相关";
    if (s === "可忽略" || s === "无关") return "不相关";
    if (s === "营销内容") return "营销";
    return s;
  };
  const filtered = posts.filter((p) => {
    const rel = normalizeRel(maps.relevanceMap[p.platform_item_id] || "");
    if (selectedRelevance === "营销") return rel === "营销" || rel === "营销内容";
    return rel === selectedRelevance;
  });
  const total = filtered.length;
  const sevList: SeverityLevel[] = ["高", "中", "低", "未标注"];
  return {
    relevanceType: selectedRelevance,
    totalCount: total,
    data: sevList.map((s) => {
      const arr = filtered.filter((p) => maps.severityMap[p.platform_item_id] === s);
      return {
        severity: s,
        total: arr.length,
        percentage: total > 0 ? Math.round((arr.length / total) * 100 * 10) / 10 : 0,
        creators: {
          达人: arr.filter((p) => (maps.creatorTypeMap[p.platform_item_id] || "未标注") === "达人").length,
          素人: arr.filter((p) => (maps.creatorTypeMap[p.platform_item_id] || "未标注") === "素人").length,
          未标注: arr.filter((p) => !maps.creatorTypeMap[p.platform_item_id] || maps.creatorTypeMap[p.platform_item_id] === "未标注").length,
        },
      };
    }),
  };
}

/**
 * 三级：严重程度 + 创作者类型 × 平台堆叠数据（示例实现）。
 * 由于平台字段来自帖子自身，按当前过滤子集计算每个创作者类型下抖音/小红书数量。
 */
export function buildSeverityDetail(severity: SeverityLevel, selectedRelevance: string, posts: PostLite[], maps: AnalysisMaps) {
  const normalizeRel = (v?: string) => {
    const s = String(v || "").trim();
    if (s === "需人工介入") return "疑似相关";
    if (s === "可忽略" || s === "无关") return "不相关";
    if (s === "营销内容") return "营销";
    return s;
  };
  const onRel = posts.filter((p) => {
    const rel = normalizeRel(maps.relevanceMap[p.platform_item_id] || "");
    if (selectedRelevance === "营销") return rel === "营销" || rel === "营销内容";
    return rel === selectedRelevance;
  });
  const arr = onRel.filter((p) => maps.severityMap[p.platform_item_id] === severity);
  const total = arr.length;
  const groupByCreator: Record<string, PostLite[]> = { 达人: [], 素人: [], 未标注: [] };
  arr.forEach((p) => {
    const raw = String(maps.creatorTypeMap[p.platform_item_id] || "未标注").trim();
    const ct = (raw === "达人" || raw === "素人" || raw === "未标注") ? raw : ("未标注" as const);
    if (!groupByCreator[ct]) groupByCreator[ct] = [];
    groupByCreator[ct].push(p);
  });

  const countPlatform = (list: PostLite[], key: string) => list.filter((x) => String(x.platform || "").toLowerCase().includes(key)).length;

  const data = ["达人", "素人", "未标注"].map((creator) => {
    const list = groupByCreator[creator] || [];
    return {
      creatorType: creator,
      platforms: {
        抖音: countPlatform(list, "douyin"),
        小红书: countPlatform(list, "xiaohongshu"),
      },
      total: list.length,
    };
  });

  return { severityLevel: severity, relevanceType: selectedRelevance, totalCount: total, data };
}


