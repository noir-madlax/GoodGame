// 中文说明：
// 本文件集中封装首页分析页所需的统计与数据整形逻辑（纯函数，不触发副作用）。
// 目标：从"已按筛选过滤后的帖子集合 + 分析映射"中，计算 KPI、一级饼图、二级/三级柱状图所需的数据结构。
// 这些结构与 @components/analytics 下的可视化组件一一对应。

import type { SupabaseClient } from "@supabase/supabase-js";

export type TimeRangeOption = "今天" | "近2天" | "近3天" | "近7天" | "近15天" | "近30天" | "全部时间";

export type SeverityLevel = "高" | "中" | "低" | "未标注";

export interface PostLite {
  id: number;
  platform: string;
  platform_item_id: string;
}

export interface AnalysisMaps {
  // 品牌相关性最终值：优先 gg_video_analysis.brand_relevance；否则回填自 relevant_status
  relevanceMap: Record<string, string | undefined>;
  // 严重程度（此处改为使用 gg_video_analysis.total_risk -> 高/中/低/未标注）
  severityMap: Record<string, SeverityLevel>;
  // 创作者类型（达人/素人/未标注）
  creatorTypeMap: Record<string, string>;
}

export interface KPITriple {
  current: number;
  previous: number;
  change: number; // 相对变化百分比，正值表示上升
  previousLabel?: string; // 展示标签，如“昨天/第3-4天/上个7天”等
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
// 说明：backfillRelevance 用于统一相关性回填逻辑
// 注意路径：同级目录
import { backfillRelevance } from "@/polymet/lib/filters";

/**
 * 页面顶层筛选子集（与 FilterSection 对齐）。
 * 只列出会影响“全库统计”的筛选项。
 */
export type GlobalAnalyticsFilters = {
  timeRange: "今天" | "近2天" | "近3天" | "近7天" | "近15天" | "近30天" | "全部时间";
  platforms: string[]; // ["抖音","小红书"]
  relevance: string[]; // ["相关","疑似相关","不相关","营销"]; 为空表示全部
  priority: string[]; // ["高","中","低","未标注"]，为空表示全部
  creatorTypes: string[]; // ["达人","素人","未标注"]，为空表示全部
};

export interface GlobalDataset {
  // 被 KPI/图表消费的"全库（已按筛选过滤）帖子样本"
  posts: PostLite[];
  // 上一周期帖子样本（用于 KPI 对比）；当选择"全部时间"时为空
  previousPosts: PostLite[];
  // 上一周期展示用标签（如 昨天 / 第3-4天 / 上个7天），全部时间下为空
  previousLabel?: string;
  // 与 posts 对应的映射（相关性/严重度/创作者类型）。
  maps: AnalysisMaps;
  // 当前周期的真实总数（从数据库count获取，用于KPI显示准确的总数）
  totalCount: number;
  // 上一周期的真实总数
  previousTotalCount: number;
  // SQL层面的相关性count（用于KPI分布显示，确保与totalCount一致）
  relevanceCounts: {
    relevant: number; // 相关
    suspicious: number; // 疑似相关
    irrelevant: number; // 不相关
    marketing: number; // 营销
  };
  // SQL层面的严重度count（全局统计，用于统计所有内容的严重度）
  severityCounts: {
    high: number; // 高
    medium: number; // 中
    low: number; // 低
    unmarked: number; // 未标注
  };
  // SQL层面的相关内容的严重度count（只统计"相关"类别，用于"相关内容"卡片）
  relevantSeverityCounts: {
    high: number; // 相关内容中严重度为高的数量
    medium: number; // 相关内容中严重度为中的数量
    low: number; // 相关内容中严重度为低的数量
    unmarked: number; // 相关内容中严重度为未标注的数量
  };
  // 高优先级内容的创作者和平台分布（用于"高优先级内容"卡片的细分统计）
  highPriorityBreakdown: {
    creatorTypes: {
      达人: number;
      素人: number;
      未标注: number;
    };
    platforms: {
      抖音: number;
      小红书: number;
      其他: number;
    };
  };
  // 各相关性类别的严重度分布（用于二级图表）
  severityByRelevance: Record<string, {
    high: number;
    medium: number;
    low: number;
    unmarked: number;
    total: number;
  }>;
  // 相关内容的真实总数（从数据库count获取）
  relevantTotalCount: number;
  // 高优先级内容的真实总数（从数据库count获取）
  highPriorityTotalCount: number;
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
  sb: SupabaseClient,
  filters: GlobalAnalyticsFilters,
  options?: { projectId?: string | null }
): Promise<GlobalDataset> => {
  // 1) 拉取基础帖子（时间/平台范围）；不分页
  const { timeRange, platforms } = filters;
  
  // 计算时间范围的起始日期
  const today = new Date();
  const startOfToday = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  let currentStartDate: Date | null = null;
  let previousStartDate: Date | null = null;
  let previousEndDate: Date | null = null;
  let previousLabel: string | undefined = undefined;
  
  if (timeRange === "今天") {
    currentStartDate = startOfToday;
    const ps = new Date(startOfToday.getTime()); 
    ps.setDate(ps.getDate() - 1);
    previousStartDate = ps;
    previousEndDate = startOfToday;
    previousLabel = "昨天";
  } else if (timeRange === "近2天" || timeRange === "近3天" || timeRange === "近7天" || timeRange === "近15天" || timeRange === "近30天") {
    const map: Record<string, number> = { "近2天": 2, "近3天": 3, "近7天": 7, "近15天": 15, "近30天": 30 };
    const n = map[timeRange];
    const s = new Date(startOfToday.getTime()); 
    s.setDate(s.getDate() - (n - 1));
    currentStartDate = s;
    
    const ps = new Date(startOfToday.getTime()); 
    ps.setDate(ps.getDate() - (2 * n));
    const pe = new Date(startOfToday.getTime()); 
    pe.setDate(pe.getDate() - (n - 1));
    previousStartDate = ps;
    previousEndDate = pe;
    previousLabel = `上个${n}天`;
  }
  
  // 构建当前周期查询（在SQL层面做时间过滤）
  let q = sb
    .from("gg_platform_post")
    .select(
      "id, platform, platform_item_id, published_at, created_at, relevant_status",
      { count: "exact" }
    );
  if (options?.projectId) {
    q = q.eq("project_id", options.projectId);
  }
  if (platforms && platforms.length > 0) {
    const keys = platforms.map((p) => normalizePlatformLabelToKey(p));
    q = q.in("platform", keys);
  }
  // 在SQL层面做时间过滤（性能优化的关键）
  if (currentStartDate) {
    q = q.gte("published_at", currentStartDate.toISOString());
  }
  
  // 分批查询以突破Supabase的max-rows限制（默认1000）
  type PostRow = {
    id: number; platform: string; platform_item_id: string;
    published_at?: string | null; created_at: string; relevant_status?: string | null;
  };
  let timeFiltered: PostRow[] = [];
  let currentTotalCount = 0;
  
  // 首次查询获取总数
  const { count: totalCount } = await q.range(0, 0);
  currentTotalCount = totalCount || 0;
  
  // 分批查询（每批999条，确保不超过Supabase的max-rows限制）
  const batchSize = 999;
  for (let offset = 0; offset < currentTotalCount; offset += batchSize) {
    const end = Math.min(offset + batchSize - 1, currentTotalCount - 1);
    const { data: batchRows } = await q.range(offset, end);
    if (batchRows && batchRows.length > 0) {
      timeFiltered = timeFiltered.concat(batchRows as PostRow[]);
    }
  }
  
  // 查询上一周期数据（如果需要）
  let previousFiltered: PostRow[] = [];
  let previousTotalCount = 0;
  if (previousStartDate && previousEndDate) {
    let prevQ = sb
      .from("gg_platform_post")
      .select("id, platform, platform_item_id, published_at, created_at, relevant_status", { count: "exact" });
    if (options?.projectId) {
      prevQ = prevQ.eq("project_id", options.projectId);
    }
    if (platforms && platforms.length > 0) {
      const keys = platforms.map((p) => normalizePlatformLabelToKey(p));
      prevQ = prevQ.in("platform", keys);
    }
    prevQ = prevQ.gte("published_at", previousStartDate.toISOString());
    prevQ = prevQ.lt("published_at", previousEndDate.toISOString());
    
    // 分批查询上一周期数据
    const { count: prevTotalCount } = await prevQ.range(0, 0);
    previousTotalCount = prevTotalCount || 0;
    
    const batchSize = 999;
    for (let offset = 0; offset < previousTotalCount; offset += batchSize) {
      const end = Math.min(offset + batchSize - 1, previousTotalCount - 1);
      const { data: batchRows } = await prevQ.range(offset, end);
      if (batchRows && batchRows.length > 0) {
        previousFiltered = previousFiltered.concat(batchRows as PostRow[]);
      }
    }
  }

  // 2) 拉取分析映射（brand_relevance/total_risk/creatorTypes）
  const ids = Array.from(new Set([...timeFiltered, ...previousFiltered].map((p) => p.platform_item_id).filter(Boolean)));
  // 重要：先对所有帖子预填充为"未标注"，避免没有分析记录的内容被排除出统计
  const severityMap: Record<string, SeverityLevel> = ids.reduce((acc, id) => {
    acc[id] = "未标注";
    return acc;
  }, {} as Record<string, SeverityLevel>);
  const creatorTypeMap: Record<string, string> = ids.reduce((acc, id) => {
    acc[id] = "未标注";
    return acc;
  }, {} as Record<string, string>);
  const relevanceMapRaw: Record<string, string> = {};
  // 改为直接查询project_id，避免URL过长问题
  if (options?.projectId) {
    let analysisQuery = sb
      .from("gg_video_analysis")
      .select("platform_item_id, brand_relevance, total_risk, total_risk_reason, \"creatorTypes\"", { count: "exact" })
      .eq("project_id", options.projectId);
    
    // 分批查询分析数据
    const { count: analysisCount } = await analysisQuery.range(0, 0);
    const analysisTotal = analysisCount || 0;
    
    type ARow = { platform_item_id: string; brand_relevance?: string | null; total_risk?: string | null; total_risk_reason?: string | null; creatorTypes?: string | null };
    
    const batchSize = 999;
    for (let offset = 0; offset < analysisTotal; offset += batchSize) {
      const end = Math.min(offset + batchSize - 1, analysisTotal - 1);
      const { data: batchRows } = await analysisQuery.range(offset, end);
      (batchRows || []).forEach((r: ARow) => {
        if (!r.platform_item_id) return;
        if (!ids.includes(r.platform_item_id)) return;
        if (r.brand_relevance) relevanceMapRaw[r.platform_item_id] = String(r.brand_relevance);
        severityMap[r.platform_item_id] = mapTotalRiskToCn(r.total_risk || "");
        creatorTypeMap[r.platform_item_id] = String(r.creatorTypes || "未标注") || "未标注";
      });
    }
  }

  // 3) 相关性回填（细分覆盖初筛）
  const relevanceMap = backfillRelevance(relevanceMapRaw as Record<string, string>, timeFiltered);

  // 4) 形成 PostLite 与 AnalysisMaps
  let postsLite: PostLite[] = timeFiltered.map((p) => ({ id: p.id, platform: String(p.platform || ""), platform_item_id: p.platform_item_id }));
  const previousPostsLite: PostLite[] = previousFiltered.map((p) => ({ id: p.id, platform: String(p.platform || ""), platform_item_id: p.platform_item_id }));
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

  // 6) 计算SQL层面的相关性分布count
  // 直接统计所有已加载数据的相关性分布（包括"其他"类别），确保总和等于实际加载数
  const relevantCount = timeFiltered.filter(p => {
    const rel = relevanceMap[p.platform_item_id];
    return rel === "相关";
  }).length;
  const suspiciousCount = timeFiltered.filter(p => {
    const rel = relevanceMap[p.platform_item_id];
    return rel === "疑似相关" || rel === "需人工介入";
  }).length;
  const irrelevantCount = timeFiltered.filter(p => {
    const rel = relevanceMap[p.platform_item_id];
    return rel === "不相关" || rel === "可忽略" || rel === "无关";
  }).length;
  const marketingCount = timeFiltered.filter(p => {
    const rel = relevanceMap[p.platform_item_id];
    return rel === "营销" || rel === "营销内容";
  }).length;
  
  // 计算已分类的总数
  const categorizedCount = relevantCount + suspiciousCount + irrelevantCount + marketingCount;
  // 未分类的记录数（空值、未知值等）
  const uncategorizedCount = timeFiltered.length - categorizedCount;

  // 如果timeFiltered.length < currentTotalCount，说明SQL只返回了部分数据
  // 按比例调整每个分类的count，同时保持总和等于totalCount
  const loadedTotal = timeFiltered.length;
  const actualTotal = currentTotalCount || loadedTotal;
  const scale = loadedTotal > 0 ? actualTotal / loadedTotal : 1;
  
  // 按比例调整，并确保总和等于actualTotal（使用floor确保不超出）
  const scaledRelevant = Math.floor(relevantCount * scale);
  const scaledSuspicious = Math.floor(suspiciousCount * scale);
  const scaledIrrelevant = Math.floor(irrelevantCount * scale);
  const scaledMarketing = Math.floor(marketingCount * scale);
  
  // 将剩余的数字（由于floor造成的差异）分配到"不相关"类别
  const scaledSum = scaledRelevant + scaledSuspicious + scaledIrrelevant + scaledMarketing;
  const remainder = actualTotal - scaledSum;
  
  const relevanceCounts = {
    relevant: scaledRelevant,
    suspicious: scaledSuspicious,
    irrelevant: scaledIrrelevant + remainder, // 将余数加到"不相关"
    marketing: scaledMarketing,
  };

  // 7) 计算严重度分布count（用于"相关内容"卡片）
  const highCount = timeFiltered.filter(p => severityMap[p.platform_item_id] === "高").length;
  const mediumCount = timeFiltered.filter(p => severityMap[p.platform_item_id] === "中").length;
  const lowCount = timeFiltered.filter(p => severityMap[p.platform_item_id] === "低").length;
  const unmarkedCount = timeFiltered.filter(p => severityMap[p.platform_item_id] === "未标注").length;
  
  // 按比例调整严重度count
  const scaledHigh = Math.floor(highCount * scale);
  const scaledMedium = Math.floor(mediumCount * scale);
  const scaledLow = Math.floor(lowCount * scale);
  const scaledUnmarked = Math.floor(unmarkedCount * scale);
  
  const sevSum = scaledHigh + scaledMedium + scaledLow + scaledUnmarked;
  const sevRemainder = actualTotal - sevSum;
  
  const severityCounts = {
    high: scaledHigh,
    medium: scaledMedium,
    low: scaledLow,
    unmarked: scaledUnmarked + sevRemainder, // 将余数加到"未标注"
  };

  // 8) 计算相关内容的严重度分布（只统计"相关"类别的内容）
  // 这是"相关内容"卡片中高中低的正确统计口径
  const relevantHighCount = timeFiltered.filter(p => {
    const rel = relevanceMap[p.platform_item_id];
    return rel === "相关" && severityMap[p.platform_item_id] === "高";
  }).length;
  const relevantMediumCount = timeFiltered.filter(p => {
    const rel = relevanceMap[p.platform_item_id];
    return rel === "相关" && severityMap[p.platform_item_id] === "中";
  }).length;
  const relevantLowCount = timeFiltered.filter(p => {
    const rel = relevanceMap[p.platform_item_id];
    return rel === "相关" && severityMap[p.platform_item_id] === "低";
  }).length;
  const relevantUnmarkedCount = timeFiltered.filter(p => {
    const rel = relevanceMap[p.platform_item_id];
    return rel === "相关" && severityMap[p.platform_item_id] === "未标注";
  }).length;

  // 按比例调整相关内容的严重度count
  const scaledRelevantHigh = Math.floor(relevantHighCount * scale);
  const scaledRelevantMedium = Math.floor(relevantMediumCount * scale);
  const scaledRelevantLow = Math.floor(relevantLowCount * scale);
  const scaledRelevantUnmarked = Math.floor(relevantUnmarkedCount * scale);

  const relevantSevSum = scaledRelevantHigh + scaledRelevantMedium + scaledRelevantLow + scaledRelevantUnmarked;
  const relevantSevRemainder = scaledRelevant - relevantSevSum;

  const relevantSeverityCounts = {
    high: scaledRelevantHigh,
    medium: scaledRelevantMedium,
    low: scaledRelevantLow,
    unmarked: scaledRelevantUnmarked + relevantSevRemainder, // 将余数加到"未标注"
  };

  // 9) 计算高优先级内容的创作者和平台分布
  const highPriorityPosts = timeFiltered.filter(p => severityMap[p.platform_item_id] === "高");
  const highCreatorDaren = highPriorityPosts.filter(p => creatorTypeMap[p.platform_item_id] === "达人").length;
  const highCreatorSuren = highPriorityPosts.filter(p => creatorTypeMap[p.platform_item_id] === "素人").length;
  const highCreatorUnmarked = highPriorityPosts.filter(p => creatorTypeMap[p.platform_item_id] === "未标注").length;
  const highPlatformDouyin = highPriorityPosts.filter(p => p.platform.toLowerCase() === "douyin").length;
  const highPlatformXhs = highPriorityPosts.filter(p => p.platform.toLowerCase() === "xiaohongshu").length;

  // 按比例调整高优先级的细分统计
  const scaledHighCreatorDaren = Math.floor(highCreatorDaren * scale);
  const scaledHighCreatorSuren = Math.floor(highCreatorSuren * scale);
  const scaledHighCreatorUnmarked = Math.floor(highCreatorUnmarked * scale);
  const scaledHighPlatformDouyin = Math.floor(highPlatformDouyin * scale);
  const scaledHighPlatformXhs = Math.floor(highPlatformXhs * scale);

  const highPriorityBreakdown = {
    creatorTypes: {
      达人: scaledHighCreatorDaren,
      素人: scaledHighCreatorSuren,
      未标注: scaledHighCreatorUnmarked,
    },
    platforms: {
      抖音: scaledHighPlatformDouyin,
      小红书: scaledHighPlatformXhs,
      其他: scaledHigh - scaledHighPlatformDouyin - scaledHighPlatformXhs,
    },
  };

  // 10) 计算各相关性类别的严重度分布（用于二级图表）
  const severityByRelevance: Record<string, { high: number; medium: number; low: number; unmarked: number; total: number }> = {};

  const relevanceTypes = ["相关", "疑似相关", "不相关", "营销"];
  relevanceTypes.forEach(relType => {
    const postsInRel = timeFiltered.filter(p => {
      const rel = relevanceMap[p.platform_item_id];
      if (relType === "疑似相关") return rel === "疑似相关" || rel === "需人工介入";
      if (relType === "不相关") return rel === "不相关" || rel === "可忽略" || rel === "无关";
      if (relType === "营销") return rel === "营销" || rel === "营销内容";
      return rel === relType;
    });

    const highInRel = postsInRel.filter(p => severityMap[p.platform_item_id] === "高").length;
    const mediumInRel = postsInRel.filter(p => severityMap[p.platform_item_id] === "中").length;
    const lowInRel = postsInRel.filter(p => severityMap[p.platform_item_id] === "低").length;
    const unmarkedInRel = postsInRel.filter(p => severityMap[p.platform_item_id] === "未标注").length;

    // 按比例调整
    const scaledHighInRel = Math.floor(highInRel * scale);
    const scaledMediumInRel = Math.floor(mediumInRel * scale);
    const scaledLowInRel = Math.floor(lowInRel * scale);
    const scaledUnmarkedInRel = Math.floor(unmarkedInRel * scale);

    const totalInRel = postsInRel.length;
    const scaledTotalInRel = Math.floor(totalInRel * scale);
    const relSevSum = scaledHighInRel + scaledMediumInRel + scaledLowInRel + scaledUnmarkedInRel;
    const relSevRemainder = scaledTotalInRel - relSevSum;

    severityByRelevance[relType] = {
      high: scaledHighInRel,
      medium: scaledMediumInRel,
      low: scaledLowInRel,
      unmarked: scaledUnmarkedInRel + relSevRemainder,
      total: scaledTotalInRel,
    };
  });

  // 11) 计算相关内容和高优先级内容的真实总数
  // 相关内容总数 = relevanceCounts.relevant（已经按比例调整）
  const relevantTotalCount = relevanceCounts.relevant;
  // 高优先级内容总数 = severityCounts.high（已经按比例调整）
  const highPriorityTotalCount = severityCounts.high;

  // 注意：totalCount是SQL层面的总数（受时间/平台筛选影响），
  // 如果用户选择了相关性/优先级/创作者类型筛选，这些是前端筛选，
  // 所以实际的posts.length可能小于totalCount。
  return { 
    posts: postsLite, 
    previousPosts: previousPostsLite, 
    previousLabel, 
    maps,
    totalCount: currentTotalCount || 0,
    previousTotalCount: previousTotalCount || 0,
    relevanceCounts,
    severityCounts,
    relevantSeverityCounts, // 新增：相关内容的严重度分布
    highPriorityBreakdown, // 新增：高优先级内容的创作者和平台分布
    severityByRelevance, // 新增：各相关性类别的严重度分布
    relevantTotalCount,
    highPriorityTotalCount,
  };
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
 * 将 total_risk 英文枚举映射为中文等级。
 * 允许输入：high/medium/low；其他与空值 -> 未标注。
 */
export const mapTotalRiskToCn = (val?: string | null): SeverityLevel => {
  const raw = String(val || "").trim().toLowerCase();
  if (!raw) return "未标注";
  if (raw === "high" || raw === "高") return "高";
  if (raw === "medium" || raw === "中") return "中";
  if (raw === "low" || raw === "低") return "低";
  return "未标注";
};

/**
 * 计算 KPI 三项。
 * @param posts - 当前周期的帖子列表（可能已应用前端筛选）
 * @param maps - 分析映射数据
 * @param options - 可选参数，包括上一周期数据、标签、以及SQL层面的真实总数
 */
export function calculateKPI(posts: PostLite[], maps: AnalysisMaps, options?: { 
  previousPosts?: PostLite[]; 
  previousLabel?: string; 
  totalCount?: number; // SQL层面的真实总数（优先使用此值）
  previousTotalCount?: number; // 上一周期的真实总数
  relevantCount?: number; // SQL层面的相关内容真实count（优先使用此值）
  highPriorityCount?: number; // SQL层面的高优先级内容真实count（优先使用此值）
}): KPIResult {
  // 优先使用options中的totalCount（从数据库count获取的真实总数），
  // 如果没有提供，则回退到posts.length（前端筛选后的数量）
  const total = options?.totalCount !== undefined ? options.totalCount : posts.length;
  
  // 优先使用options中的relevantCount（从数据库count获取的真实相关数），
  // 如果没有提供，则回退到前端数组统计
  const relevant = options?.relevantCount !== undefined 
    ? options.relevantCount 
    : posts.filter((p) => {
        const rel = maps.relevanceMap[p.platform_item_id];
        // 口径修正：仅将"相关"计入 KPI 的"相关内容"，不再包含"疑似相关/营销"。
        // 背景：与"相关性统计"卡片的"相关"保持一致，避免 112/120 口径不一致。
        return rel === "相关";
      }).length;
  
  // 优先使用options中的highPriorityCount（从数据库count获取的真实高优先级数），
  // 如果没有提供，则回退到前端数组统计
  const high = options?.highPriorityCount !== undefined 
    ? options.highPriorityCount 
    : posts.filter((p) => maps.severityMap[p.platform_item_id] === "高").length;

  const prev = options?.previousPosts || [];
  const prevLabel = options?.previousLabel;
  // 同样优先使用previousTotalCount（数据库count），否则使用prev.length
  const prevTotal = options?.previousTotalCount !== undefined ? options.previousTotalCount : prev.length;
  const prevRelevant = prev.filter((p) => maps.relevanceMap[p.platform_item_id] === "相关").length;
  const prevHigh = prev.filter((p) => maps.severityMap[p.platform_item_id] === "高").length;

  const triple = (curr: number, prevValue: number): KPITriple => {
    const base = prevValue === 0 ? 0 : Math.round(((curr - prevValue) / Math.max(prevValue, 1)) * 100);
    return { current: curr, previous: prevValue, change: base, previousLabel: prevLabel };
  };

  return {
    totalVideos: triple(total, prevTotal),
    relevantVideos: triple(relevant, prevRelevant),
    highPriorityVideos: triple(high, prevHigh),
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
  const countPlatform = (list: PostLite[], key: string) => list.filter((x) => String(x.platform || "").toLowerCase().includes(key)).length;
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
        platforms: {
          抖音: countPlatform(arr, "douyin"),
          小红书: countPlatform(arr, "xiaohongshu"),
          其他: Math.max(0, arr.length - countPlatform(arr, "douyin") - countPlatform(arr, "xiaohongshu")),
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

  return { severityLevel: severity, relevanceType: selectedRelevance, totalCount: total, relevanceTotal: onRel.length, data };
}


