 
// 说明：旧 FilterBar 暂停在本页使用，保留组件文件供其他页面复用。
// import FilterBar, { SentimentValue } from "@/polymet/components/filter-bar";
import FilterSection, { FiltersState } from "@/polymet/components/analytics/filter-section";
import KPIOverview from "@/polymet/components/analytics/kpi-overview";
import ContentAnalysisSection from "@/polymet/components/analytics/content-analysis-section";
// 卡片渲染已抽到 MonitoringResults 内部
// import VideoGridCard from "@/polymet/components/video-grid-card";
// import { normalizeCoverUrl } from "@/lib/media";
// import { Grid, List, SortAsc, MoreHorizontal } from "lucide-react";
// import { cn } from "@/lib/utils";
import { useNavigate } from "react-router-dom";
import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { supabase } from "@/lib/supabase";
// Skeleton replaced by shared loading skeletons
// 骨架已在 MonitoringResults 内部使用
// import { DashboardCardSkeleton } from "@/polymet/components/loading-skeletons";
import MonitoringResults from "@/polymet/components/monitoring/monitoring-results";
import { backfillRelevance, resolveStartAt, filterByTime, sortByPublished, buildAnalysisMaps, buildTopRiskOptions } from "@/polymet/lib/filters";
import { calculateKPI, buildRelevanceChartData, buildSeverityGroups, buildSeverityDetail, mapDbSeverityToCn, AnalysisMaps, loadGlobalDataset } from "@/polymet/lib/analytics";
import { useProject } from "@/polymet/lib/project-context";
import ImportAnalyzeDialog from "@/polymet/components/import-analyze-dialog";
import { getDashboardCache, setDashboardCache, clearDashboardCache, isDashboardCacheDirty, updateDashboardScrollTop, DASHBOARD_SCROLL_SELECTOR } from "@/polymet/lib/dashboard-cache";

export default function ContentDashboard() {
  const navigate = useNavigate();
  const { activeProjectId } = useProject();
  const [importOpen, setImportOpen] = useState(false);

  /**
   * 功能：平台 key 归一化（小写、别名合并，如 xhs/xiaohongshu -> xiaohongshu）。
   * 使用位置：传入卡片与徽章，保证平台文案一致。
   */
  const normalizePlatformKey = (platform: string) => {
    const key = String(platform || "").toLowerCase();
    if (key === "xiaohongshu" || key === "xhs") return "xiaohongshu";
    return key;
  };

  /**
   * 功能：毫秒时长格式化为 mm:ss 文本，用于卡片与播放器时长展示。
   */
  const formatDurationMs = (ms: number) => {
    const total = Math.max(0, Math.round(ms / 1000));
    const m = Math.floor(total / 60)
      .toString()
      .padStart(1, "0");
    const s = (total % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  };

  /**
   * 功能：将数据库中的 total_risk 值规范化为中文“高/中/低/未标注”。
   * 使用位置：分析映射阶段，兼容后端写入英文(high/medium/low)或中文（高/中/低）。
   */
  const normalizeTotalRiskToCn = (val: string | null | undefined): string => {
    const t = String(val || "").trim().toLowerCase();
    if (!t) return "未标注";
    if (t === "high" || t === "高") return "高";
    if (t === "medium" || t === "中") return "中";
    if (t === "low" || t === "低") return "低";
    return "未标注";
  };

  type PostRow = {
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
    /**
     * 中文设计说明：
     * 1) relevant_status 来源于 gg_platform_post，属于【初筛】结论；值域：yes/no/maybe/unknown。
     * 2) brand_relevance 来源于 gg_video_analysis，属于【细分分析】结论；值域：相关/疑似相关/不相关（或缺省）。
     * 3) 业务优先级：细分覆盖初筛。即：若 brand_relevance 存在，用它作为"最终相关性"；否则，使用 relevant_status 做回填。
     * 4) 回填映射：
     *    yes   -> 相关
     *    maybe -> 疑似相关
     *    no    -> 不相关
     *    其余  -> 不设置（视为未知，不参与"相关性"筛选命中）
     * 5) 页面筛选"相关性=相关/疑似相关/不相关"时，统一针对"最终相关性"生效。
     */
    relevant_status?: string | null;
  };

  /**
   * 统一的筛选条件模型
   * 说明：内容分布概览、内容分布图表、舆情监控结果使用相同的筛选条件
   */
  type EffectiveFilters = {
    projectId: string | null;
    timeRange: string;
    channel: string;
    contentType: string;
    sentiment: string;
    riskScenario: string;
    topRelevance: string;
    chartRelevance: string | null;
    chartSeverity: string | null;
    oldestFirst: boolean;
  };

  /**
   * 辅助函数：映射图表相关性到数据库值
   */
  const mapChartRelToDbValue = (chartRel: string | null): string | null => {
    if (!chartRel) return null;
    if (chartRel === "相关") return "相关";
    if (chartRel === "疑似相关") return "需人工介入";
    if (chartRel === "不相关") return "可忽略";
    if (chartRel === "营销") return "营销";
    return null;
  };

  /**
   * 辅助函数：映射中文严重度到数据库值数组
   * 注意：gg_video_analysis.total_risk 存储的是中文值（"低"、"中"、"高"）
   */
  const mapCnSeverityToDbValues = (cn: string | null): string[] => {
    if (!cn) return [];
    if (cn === "高") return ["高", "high", "eP0"];
    if (cn === "中") return ["中", "medium", "P1"];
    if (cn === "低") return ["低", "low", "P2"];
    return [];
  };

  /**
   * 辅助函数：映射图表相关性到数据库 relevant_status 字段值
   */
  const mapChartRelToRelevantStatus = (cn: string | null): string | null => {
    if (!cn) return null;
    if (cn === "相关") return "yes";
    if (cn === "不相关") return "no";
    if (cn === "疑似相关") return "suspected";
    return null;
  };

  /**
   * 辅助函数：映射图表相关性到 gg_video_analysis.brand_relevance 可能的值数组
   * 注意：gg_video_analysis 中"不相关"存储为"无关"
   */
  const mapChartRelToBrandRelevance = (cn: string | null): string[] => {
    if (!cn) return [];
    if (cn === "相关") return ["相关"];
    if (cn === "不相关") return ["无关", "不相关"]; // 数据库中主要是"无关"
    if (cn === "疑似相关") return ["疑似相关"];
    return [];
  };

  // RiskRow kept in lib/content; local type not required here after refactor

  const PAGE_SIZE = 20; // 每次分页拉取的帖子数量
  const [loading, setLoading] = useState(true); // 首屏加载态
  const [loadingMore, setLoadingMore] = useState(false); // 滚动分页追加加载态
  const [hasMore, setHasMore] = useState(true); // 是否还有更多分页数据
  const [page, setPage] = useState(0); // 当前分页页码（从 0 开始）
  const [allRows, setAllRows] = useState<PostRow[]>([]); // 已累计的原始帖子行（用于在前端统一再过滤/排序）
  const [posts, setPosts] = useState<PostRow[]>([]); // 渲染到页面的帖子（已应用筛选与排序）
  const [totalCount, setTotalCount] = useState<number>(0); // 符合条件的总量（服务端 count）
  const [risks, setRisks] = useState<Record<string, string[]>>({}); // 映射：platform_item_id -> 风险场景列表
  const [sentiments, setSentiments] = useState<Record<string, string>>({}); // 映射：platform_item_id -> 情绪
  const [relevances, setRelevances] = useState<Record<string, string>>({}); // 映射：platform_item_id -> 品牌相关性（细分覆盖初筛后的最终值）
  // filter options are now loaded inside FilterBar from gg_filter_enums
  // 说明：保留占位，后续如需在筛选条中加入“风险场景”可直接使用此 state。
  const [, setRiskOptions] = useState<{ id: string; label: string; count: number }[]>([]);
  // 基于 total_risk 的优先级映射（中文）与理由
  const [totalRiskCn, setTotalRiskCn] = useState<Record<string, string>>({});
  const [totalRiskReason, setTotalRiskReason] = useState<Record<string, string>>({});
  // 达人映射：platform_item_id -> 是否达人
  const [influencerMap, setInfluencerMap] = useState<Record<string, boolean>>({});
  // label maps moved to FilterBar; keep page lean
  // filters（筛选器当前值）
  // 新顶层筛选（与设计稿一致）
  // 默认时间改为“全部时间”
  const [filters, setFilters] = useState<FiltersState>({ timeRange: "全部时间", relevance: [], priority: [], creatorTypes: [], platforms: [] });
  // 为保持旧数据加载逻辑，这里映射出必要的旧筛选位
  const riskScenario = "all"; // 本页一期不暴露风险场景选择；保留旧变量
  const channel = filters.platforms.length === 1 ? (filters.platforms[0] === "抖音" ? "douyin" : filters.platforms[0] === "小红书" ? "xiaohongshu" : "all") : "all";
  const contentType = "all";
  // 将中文时间范围直接传给 resolveStartAt，它现在支持中文
  const timeRange = filters.timeRange;
  const sentiment = "all" as const; // 本版先不提供情绪筛选入口
  const relevance = filters.relevance[0] || "all";
  const [oldestFirst, setOldestFirst] = useState(false); // 排序方向（false=最新优先，true=最旧优先）
  const sentinelRef = useRef<HTMLDivElement | null>(null); // 无限滚动的哨兵元素
  const skipListFetchRef = useRef(false);
  const skipGlobalFetchRef = useRef(false);
  const restoredFromCacheRef = useRef(false);

  useEffect(() => {
    const cache = getDashboardCache();
    const currentProjectId = activeProjectId || null;
    if (!cache) {
      return;
    }
    if (cache.projectId !== currentProjectId) {
      clearDashboardCache();
      return;
    }
    if (isDashboardCacheDirty()) {
      setFilters(cache.filters);
      setOldestFirst(cache.oldestFirst);
      setChartState(cache.chartState);
      clearDashboardCache();
      return;
    }
    skipListFetchRef.current = true;
    skipGlobalFetchRef.current = true;
    restoredFromCacheRef.current = true;
    setFilters(cache.filters);
    setOldestFirst(cache.oldestFirst);
    setPage(cache.page);
    setHasMore(cache.hasMore);
    setTotalCount(cache.totalCount);
    setAllRows(cache.allRows);
    setPosts(cache.posts);
    setRisks(cache.risks);
    setSentiments(cache.sentiments);
    setRelevances(cache.relevances);
    setTotalRiskCn(cache.totalRiskCn);
    setTotalRiskReason(cache.totalRiskReason);
    setInfluencerMap(cache.influencerMap);
    setGlobalPostsLite(cache.globalPostsLite);
    setGlobalMaps(cache.globalMaps);
    setKpiPrev(cache.kpiPrev);
    // 恢复SQL层面的真实总数
    setGlobalTotalCount(cache.globalTotalCount || 0);
    setGlobalPreviousTotalCount(cache.globalPreviousTotalCount || 0);
    setGlobalRelevanceCounts(cache.globalRelevanceCounts || { relevant: 0, suspicious: 0, irrelevant: 0, marketing: 0 });
    setGlobalSeverityCounts(cache.globalSeverityCounts || { high: 0, medium: 0, low: 0, unmarked: 0 });
    setGlobalRelevantSeverityCounts(cache.globalRelevantSeverityCounts || { high: 0, medium: 0, low: 0, unmarked: 0 });
    setGlobalHighPriorityBreakdown(cache.globalHighPriorityBreakdown || { creatorTypes: { 达人: 0, 素人: 0, 未标注: 0 }, platforms: { 抖音: 0, 小红书: 0, 其他: 0 } });
    setGlobalSeverityByRelevance(cache.globalSeverityByRelevance || {});
    setGlobalRelevantTotal(cache.globalRelevantTotal || 0);
    setGlobalHighPriorityTotal(cache.globalHighPriorityTotal || 0);
    setChartState(cache.chartState);
    setLoading(false);
    setLoadingMore(false);
    setGlobalLoading(false);
    requestAnimationFrame(() => {
      const container = document.querySelector(DASHBOARD_SCROLL_SELECTOR);
      if (container instanceof HTMLElement) {
        container.scrollTo({ top: cache.scrollTop ?? 0, behavior: "auto" });
      }
    });
  }, [activeProjectId]);

  /**
   * 功能：按页拉取帖子并在前端应用时间过滤、分析映射、相关性回填、筛选与排序。
   * 调用时机：首屏加载与滚动触底追加；每次筛选条件或排序方向变更后会重置并重新请求。
   * 参数：batchIndex - 分页索引，从 0 开始。
   *       filters - 统一的筛选条件
   */
  const fetchBatch = useCallback(async (batchIndex: number, filters: EffectiveFilters) => {
    let cancelled = false;
    const run = async () => {
      try {
        if (!supabase) {
          setLoading(false);
          setLoadingMore(false);
          return;
        }
        const sb = supabase!;
        const isFirst = batchIndex === 0;
        if (isFirst) {
          setLoading(true);
        } else {
          setLoadingMore(true);
        }

        // 【重构】使用优化后的查询逻辑：
        // 利用 gg_video_analysis.published_at 字段（已通过数据库迁移添加）
        // 直接在 gg_video_analysis 表查询，无需多步查询
        let chartFilteredIds: string[] | null = null;
        
        if (filters.chartRelevance || filters.chartSeverity) {
          console.log('[DEBUG] Generating chartFilteredIds, chartRelevance:', filters.chartRelevance, 'chartSeverity:', filters.chartSeverity);
          const idSet = new Set<string>();
          
          // 从 gg_video_analysis 一次性查询符合条件的 platform_item_id
          let analysisQuery = sb
            .from("gg_video_analysis")
            .select("platform_item_id");
          
          if (filters.projectId) {
            analysisQuery = analysisQuery.eq("project_id", filters.projectId);
          }
          
          // 关键优化：直接在 gg_video_analysis 应用时间筛选
          const startAt = resolveStartAt(filters.timeRange);
          if (startAt) {
            analysisQuery = analysisQuery.gte("published_at", startAt.toISOString());
          }
          
          // 应用图表层级的相关性筛选
          if (filters.chartRelevance) {
            const brandRelValues = mapChartRelToBrandRelevance(filters.chartRelevance);
            console.log('[DEBUG] brandRelValues for chartRelevance:', filters.chartRelevance, '=', brandRelValues);
            if (brandRelValues.length > 0) {
              analysisQuery = analysisQuery.in("brand_relevance", brandRelValues);
            }
          }
          
          // 应用图表层级的严重度筛选
          if (filters.chartSeverity) {
            const sevValues = mapCnSeverityToDbValues(filters.chartSeverity);
            if (sevValues.length > 0) {
              analysisQuery = analysisQuery.in("total_risk", sevValues);
            }
          }
          
          // 【修复】使用分批查询突破Supabase的max-rows限制（默认1000条）
          // 首先获取总数（使用单独的count查询）
          const countQuery = sb.from("gg_video_analysis").select("*", { count: "exact", head: true });
          // 复制所有筛选条件到count查询
          let analysisCountQuery = countQuery;
          if (filters.projectId) {
            analysisCountQuery = analysisCountQuery.eq("project_id", filters.projectId);
          }
          if (startAt) {
            analysisCountQuery = analysisCountQuery.gte("published_at", startAt.toISOString());
          }
          if (filters.chartRelevance) {
            const brandRelValues = mapChartRelToBrandRelevance(filters.chartRelevance);
            if (brandRelValues.length > 0) {
              analysisCountQuery = analysisCountQuery.in("brand_relevance", brandRelValues);
            }
          }
          if (filters.chartSeverity) {
            const sevValues = mapCnSeverityToDbValues(filters.chartSeverity);
            if (sevValues.length > 0) {
              analysisCountQuery = analysisCountQuery.in("total_risk", sevValues);
            }
          }
          const { count: analysisCount } = await analysisCountQuery;
          console.log('[DEBUG] analysisCount:', analysisCount || 0);
          
          // 分批查询（每批999条）
          const batchSize = 999;
          const totalAnalysisCount = analysisCount || 0;
          for (let offset = 0; offset < totalAnalysisCount; offset += batchSize) {
            const end = Math.min(offset + batchSize - 1, totalAnalysisCount - 1);
            const { data: batchData } = await analysisQuery.range(offset, end);
            if (batchData && batchData.length > 0) {
              batchData.forEach((r: { platform_item_id: string }) => {
                if (r.platform_item_id) idSet.add(r.platform_item_id);
              });
            }
          }
          console.log('[DEBUG] idSet size after analysisData:', idSet.size);
          
          // 回填逻辑：如果只有相关性筛选（没有严重度筛选），也从 gg_platform_post 查询
          // 因为有些相关内容只在 relevant_status 中标记，没有经过详细分析
          // 【关键修复】只包含在gg_video_analysis中没有brand_relevance记录的内容，避免重复计数
          if (filters.chartRelevance && !filters.chartSeverity) {
            // 首先获取所有有brand_relevance的platform_item_id（无论相关性如何）
            let allAnalysisQuery = sb
              .from("gg_video_analysis")
              .select("platform_item_id");
            
            if (filters.projectId) {
              allAnalysisQuery = allAnalysisQuery.eq("project_id", filters.projectId);
            }
            if (startAt) {
              allAnalysisQuery = allAnalysisQuery.gte("published_at", startAt.toISOString());
            }
            
            // 分批获取所有有brand_relevance的ID
            const allAnalysisCountQuery = sb.from("gg_video_analysis").select("*", { count: "exact", head: true });
            let tempQuery = allAnalysisCountQuery;
            if (filters.projectId) {
              tempQuery = tempQuery.eq("project_id", filters.projectId);
            }
            if (startAt) {
              tempQuery = tempQuery.gte("published_at", startAt.toISOString());
            }
            const { count: allAnalysisCount } = await tempQuery;
            
            const allAnalysisIds = new Set<string>();
            for (let offset = 0; offset < (allAnalysisCount || 0); offset += batchSize) {
              const end = Math.min(offset + batchSize - 1, (allAnalysisCount || 0) - 1);
              const { data: batchData } = await allAnalysisQuery.range(offset, end);
              if (batchData && batchData.length > 0) {
                batchData.forEach((r: { platform_item_id: string }) => {
                  if (r.platform_item_id) allAnalysisIds.add(r.platform_item_id);
                });
              }
            }
            console.log('[DEBUG] Total IDs with brand_relevance:', allAnalysisIds.size);
            
            // 然后查询gg_platform_post，只包含不在allAnalysisIds中的内容
            const relStatusValue = mapChartRelToRelevantStatus(filters.chartRelevance);
            console.log('[DEBUG] Fallback query, relStatusValue:', relStatusValue);
            
            if (relStatusValue) {
              // 由于Supabase不支持NOT IN，我们需要先获取所有匹配的数据，然后在客户端过滤
              let postQuery = sb
                .from("gg_platform_post")
                .select("platform_item_id");
              
              if (filters.projectId) {
                postQuery = postQuery.eq("project_id", filters.projectId);
              }
              if (startAt) {
                postQuery = postQuery.gte("published_at", startAt.toISOString());
              }
              postQuery = postQuery.eq("relevant_status", relStatusValue);
              
              // 获取总数
              let postCountQuery = sb.from("gg_platform_post").select("*", { count: "exact", head: true });
              if (filters.projectId) {
                postCountQuery = postCountQuery.eq("project_id", filters.projectId);
              }
              if (startAt) {
                postCountQuery = postCountQuery.gte("published_at", startAt.toISOString());
              }
              postCountQuery = postCountQuery.eq("relevant_status", relStatusValue);
              const { count: postCount } = await postCountQuery;
              console.log('[DEBUG] postCount (fallback before filter):', postCount || 0);
              
              // 分批查询并过滤
              let addedCount = 0;
              for (let offset = 0; offset < (postCount || 0); offset += batchSize) {
                const end = Math.min(offset + batchSize - 1, (postCount || 0) - 1);
                const { data: batchData } = await postQuery.range(offset, end);
                if (batchData && batchData.length > 0) {
                  batchData.forEach((r: { platform_item_id: string }) => {
                    // 【关键】只添加那些不在allAnalysisIds中的ID
                    if (r.platform_item_id && !allAnalysisIds.has(r.platform_item_id)) {
                      idSet.add(r.platform_item_id);
                      addedCount++;
                    }
                  });
                }
              }
              console.log('[DEBUG] IDs added from fallback (after filter):', addedCount);
            }
            console.log('[DEBUG] idSet size after postData fallback:', idSet.size);
          }
          
          chartFilteredIds = Array.from(idSet);
          console.log('[DEBUG] Final chartFilteredIds length:', chartFilteredIds.length);
          
          // 如果没有符合条件的数据，提前返回
          if (chartFilteredIds.length === 0) {
            console.log('[DEBUG] chartFilteredIds is empty, returning early');
            if (!cancelled) {
              setHasMore(false);
              setAllRows([]);
              setPosts([]);
              setTotalCount(0);
            }
            return;
          }
        }

        // 【修复】处理大量ID的分批查询逻辑
        // 当 chartFilteredIds 数量超过阈值时，需要分批查询以避免 URL 过长
        const MAX_IDS_PER_QUERY = 100; // Supabase .in() 查询的最大ID数量
        const needsBatchQuery = chartFilteredIds && chartFilteredIds.length > MAX_IDS_PER_QUERY;
        
        // 构建SQL查询，应用所有筛选条件
        const buildQuery = (idsSubset?: string[]) => {
          let q = sb
            .from("gg_platform_post")
            .select(
              "id, platform, platform_item_id, author_id, title, original_url, like_count, comment_count, share_count, cover_url, author_name, author_follower_count, duration_ms, published_at, created_at, relevant_status, is_marked",
              { count: "exact" }
            );
          
          // 排序
          q = q
            .order("published_at", { ascending: filters.oldestFirst, nullsFirst: filters.oldestFirst })
            .order("created_at", { ascending: filters.oldestFirst })
            .order("id", { ascending: filters.oldestFirst });
          
          // 应用所有筛选条件
          if (filters.projectId) {
            q = q.eq("project_id", filters.projectId);
          }
          
          // 【优化】图表层级筛选：使用传入的 ID 子集或完整的 chartFilteredIds
          const idsToUse = idsSubset || chartFilteredIds;
          if (idsToUse && idsToUse.length > 0) {
            q = q.in("platform_item_id", idsToUse);
          }
          
          // 时间筛选
          const startAt = resolveStartAt(filters.timeRange);
          if (startAt) {
            q = q.gte("published_at", startAt.toISOString());
          }
          
          // 平台、内容类型
          if (filters.channel !== "all") q = q.eq("platform", filters.channel);
          if (filters.contentType !== "all") q = q.eq("post_type", filters.contentType);
          
          // 顶部筛选的相关性（只在没有图表层级筛选时生效）
          if (filters.topRelevance !== "all" && !filters.chartRelevance) {
            q = q.eq("relevant_status", filters.topRelevance);
          }
          
          return q;
        };

        if (isFirst) {
          // 【修复】totalCount 就是 chartFilteredIds 的数量（已经过滤）
          if (chartFilteredIds && chartFilteredIds.length > 0) {
            setTotalCount(chartFilteredIds.length);
            console.log('[DEBUG] Total count:', chartFilteredIds.length);
          } else {
            // 没有图表筛选时，从数据库查询总数
            const { count } = await buildQuery().range(0, 0);
            setTotalCount(count || 0);
          }
        }

        // 【优化】分页策略与数据查询
        let batchSize = PAGE_SIZE;
        let postsSafe: PostRow[] = [];
        
        if (needsBatchQuery) {
          // 【修复】需要分批查询时的逻辑
          console.log('[DEBUG] Using batch query for', chartFilteredIds!.length, 'IDs');
          
          // 计算当前批次需要查询的数据范围
          const start = batchIndex * batchSize;
          const end = start + batchSize - 1;
          
          // 如果起始位置超出 chartFilteredIds 范围，说明没有更多数据
          if (start >= chartFilteredIds!.length) {
            setHasMore(false);
            if (!cancelled) {
              setLoading(false);
              setLoadingMore(false);
            }
            return;
          }
          
          // 从 chartFilteredIds 中取出需要的ID
          const idsToFetch = chartFilteredIds!.slice(start, Math.min(end + 1, chartFilteredIds!.length));
          console.log('[DEBUG] Fetching IDs from', start, 'to', Math.min(end, chartFilteredIds!.length - 1), '(', idsToFetch.length, 'IDs)');
          
          // 使用这些ID查询数据
          const { data: postData } = await buildQuery(idsToFetch);
          postsSafe = ((postData || []) as unknown) as PostRow[];
          
          // 检查是否还有更多数据
          if (end >= chartFilteredIds!.length - 1) {
            setHasMore(false);
          }
        } else {
          // 数据量较小，使用原有的范围查询逻辑
          if (chartFilteredIds && chartFilteredIds.length <= 100) {
            batchSize = chartFilteredIds.length;
          }
          
          const start = batchIndex * batchSize;
          const end = start + batchSize - 1;
          const { data: postData } = await buildQuery().range(start, end);
          postsSafe = ((postData || []) as unknown) as PostRow[];
        }

        // 已在SQL层面完成所有筛选，无需前端过滤
        let filteredByChart = postsSafe;

        // SQL 层面已经做了时间过滤，前端不再需要二次过滤
        // 保留 filteredByTime 变量名以保持代码连贯性
        let filteredByTime = filteredByChart;

        // 已移除：示例性平台/类型集合统计与额外 post_type 查询（无消费方）

        const ids = filteredByTime.map((p) => p.platform_item_id).filter(Boolean); // 本页涉及的平台内容主键集合
        // —— 新增：达人判定（帖子 author_follower_count 或 gg_authors.follower_count 任一≥10万） ——
        const influencerMapLocal: Record<string, boolean> = {};
        if (filteredByTime.length > 0) {
          // 先用帖子字段进行快速判定
          filteredByTime.forEach((p) => {
            if (Number(p.author_follower_count || 0) >= 100000) {
              influencerMapLocal[p.platform_item_id] = true;
            }
          });
          // 收集作者 id 与平台集合
          const authorIds = Array.from(new Set((filteredByTime.map((p) => String(p.author_id || "")).filter(Boolean)) as string[]));
          const platforms = Array.from(new Set((filteredByTime.map((p) => String(p.platform || "")).filter(Boolean)) as string[]));
          if (authorIds.length > 0) {
            // 查询 gg_authors 的粉丝数
            let q = sb
              .from("gg_authors")
              .select("platform, platform_author_id, follower_count")
              .in("platform_author_id", authorIds);
            if (platforms.length > 0 && platforms.length <= 5) {
              q = q.in("platform", platforms);
            }
            const { data: rowsAuthors } = await q;
            const authorsMap: Record<string, number> = {};
            (rowsAuthors || []).forEach((r: { platform: string; platform_author_id: string; follower_count: number }) => {
              if (!r || !r.platform_author_id) return;
              authorsMap[r.platform_author_id] = Number(r.follower_count || 0);
            });
            filteredByTime.forEach((p) => {
              const aid = String(p.author_id || "");
              if (!aid) return;
              const fc = Number(authorsMap[aid] || 0);
              if (fc >= 100000) influencerMapLocal[p.platform_item_id] = true;
            });
          }
        }
        let risksMap: Record<string, string[]> = { ...risks };
        let sentimentsMap: Record<string, string> = { ...sentiments };
        let relevanceMap: Record<string, string> = { ...relevances };
        // 读取分析数据并构建映射（风险/情绪/品牌相关性），并据此生成风险 TopN 选项
        if (ids.length > 0) {
          const riskQuery = sb
            .from("gg_video_analysis")
            .select("platform_item_id, risk_types, sentiment, brand_relevance, total_risk, total_risk_reason, severity, \"creatorTypes\"")
            .in("platform_item_id", ids);
          // 不在这里按 sentiment 过滤，以便枚举选项不受当前筛选影响
          const { data: riskData } = await riskQuery;
          const mapsRaw = (riskData || []) as unknown as { platform_item_id: string; risk_types?: unknown; sentiment?: string | null; brand_relevance?: string | null; total_risk?: string | null; total_risk_reason?: string | null; severity?: string | null; creatorTypes?: string | null }[];
          const maps = buildAnalysisMaps(mapsRaw);
          risksMap = { ...risksMap, ...maps.risksMap };
          sentimentsMap = { ...sentimentsMap, ...maps.sentimentsMap };
          relevanceMap = { ...relevanceMap, ...maps.relevanceMap };
          // 构建严重度与创作者类型映射（用于图表/KPI）
          const sevMap: Record<string, string> = {};
          const ctMap: Record<string, string> = {};
          const trMap: Record<string, string> = {};
          const trReason: Record<string, string> = {};
          mapsRaw.forEach((r) => {
            if (r.platform_item_id) {
              // 兼容旧 severity；但优先在列表图标使用 total_risk
              sevMap[r.platform_item_id] = mapDbSeverityToCn(r.severity || "");
              trMap[r.platform_item_id] = normalizeTotalRiskToCn(r.total_risk);
              if (r.total_risk_reason) trReason[r.platform_item_id] = String(r.total_risk_reason);
              const ct = String(r.creatorTypes || "").trim();
              ctMap[r.platform_item_id] = ct || "未标注";
            }
          });
          setExtraMaps({ severityMap: sevMap, creatorTypeMap: ctMap });
          setTotalRiskCn((prev) => ({ ...prev, ...trMap }));
          setTotalRiskReason((prev) => ({ ...prev, ...trReason }));
          // ignore counts/sets in page scope
          setRiskOptions(buildTopRiskOptions(maps.riskCountMap, 8));
        }

        // 回填相关性（细分覆盖初筛）
        // --------------------------------------------------------------
        // 若某条内容具备 brand_relevance（来自 gg_video_analysis），则以其为准。
        // 否则使用 gg_platform_post.relevant_status（初筛）进行回填，映射关系：
        // yes->相关；maybe->疑似相关；no->不相关；unknown/null->忽略。
        const relevanceMapBackfilled = backfillRelevance(relevanceMap, filteredByTime);

        // 合并新页数据到累计行（服务端已按发布时间排序，且已在SQL层面应用了所有筛选）
        const mergedRows = isFirst ? filteredByTime : [...allRows, ...filteredByTime];

        // SQL已经应用了所有筛选条件，前端不再需要二次筛选
        // 直接使用合并后的数据
        const postsSorted = mergedRows;

        // options are loaded by FilterBar from gg_filter_enums; page no longer sets them

        if (!cancelled) {
          // 分页：是否还有更多由本页返回数量决定
          setHasMore(postsSafe.length === PAGE_SIZE);
          setAllRows(mergedRows);
          setPosts(postsSorted);
          setRisks(risksMap);
          setSentiments(sentimentsMap);
          setRelevances(relevanceMapBackfilled);
          setInfluencerMap((prev) => ({ ...prev, ...influencerMapLocal }));
          // no-op: totalRisk maps 已通过 setTotalRiskCn/Reason 维护
          // no-op: options handled by FilterBar
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
          setLoadingMore(false);
        }
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [allRows, risks, sentiments, relevances, supabase, activeProjectId]);

  const normalizePlatform = normalizePlatformKey; // 平台 key 归一化（如 xhs -> xiaohongshu）
  const formatDuration = formatDurationMs; // 毫秒时长格式化为 mm:ss

  const totalCountText = useMemo(() => (totalCount || posts.length).toLocaleString(), [totalCount, posts.length]);

  // —— 新增：图表与 KPI（全库统计版本） ——
  const [, setExtraMaps] = useState<{ severityMap: Record<string, string>; creatorTypeMap: Record<string, string> }>({ severityMap: {}, creatorTypeMap: {} });
  const [globalLoading, setGlobalLoading] = useState(false);
  const [globalPostsLite, setGlobalPostsLite] = useState<{ id: number; platform: string; platform_item_id: string }[]>([]);
  const [globalMaps, setGlobalMaps] = useState<AnalysisMaps>({ relevanceMap: {}, severityMap: {} as any, creatorTypeMap: {} });
  const [kpiPrev, setKpiPrev] = useState<{ prev: { id: number; platform: string; platform_item_id: string }[]; label?: string }>({ prev: [] });
  // 新增：存储SQL层面的真实总数（用于KPI显示）
  const [globalTotalCount, setGlobalTotalCount] = useState<number>(0);
  const [globalPreviousTotalCount, setGlobalPreviousTotalCount] = useState<number>(0);
  // 新增：存储SQL层面的相关性分布count（用于KPI分布显示）
  const [globalRelevanceCounts, setGlobalRelevanceCounts] = useState<{relevant: number; suspicious: number; irrelevant: number; marketing: number}>({ relevant: 0, suspicious: 0, irrelevant: 0, marketing: 0 });
  // 新增：存储SQL层面的严重度分布count（全局统计）
  const [globalSeverityCounts, setGlobalSeverityCounts] = useState<{high: number; medium: number; low: number; unmarked: number}>({ high: 0, medium: 0, low: 0, unmarked: 0 });
  // 新增：存储SQL层面的相关内容的严重度分布count（只统计"相关"类别）
  const [globalRelevantSeverityCounts, setGlobalRelevantSeverityCounts] = useState<{high: number; medium: number; low: number; unmarked: number}>({ high: 0, medium: 0, low: 0, unmarked: 0 });
  // 新增：存储高优先级内容的创作者和平台分布
  const [globalHighPriorityBreakdown, setGlobalHighPriorityBreakdown] = useState<{
    creatorTypes: { 达人: number; 素人: number; 未标注: number };
    platforms: { 抖音: number; 小红书: number; 其他: number };
  }>({ creatorTypes: { 达人: 0, 素人: 0, 未标注: 0 }, platforms: { 抖音: 0, 小红书: 0, 其他: 0 } });
  // 新增：存储各相关性类别的严重度分布（用于二级图表）
  const [globalSeverityByRelevance, setGlobalSeverityByRelevance] = useState<Record<string, {high: number; medium: number; low: number; unmarked: number; total: number}>>({});
  // 新增：存储相关内容和高优先级内容的真实总数
  const [globalRelevantTotal, setGlobalRelevantTotal] = useState<number>(0);
  const [globalHighPriorityTotal, setGlobalHighPriorityTotal] = useState<number>(0);
  const [chartState, setChartState] = useState<{ level: "primary" | "secondary" | "tertiary"; selectedRelevance?: string; selectedSeverity?: string }>({ level: "primary" });

  /**
   * 计算有效的筛选条件（统一筛选条件模型）
   * 说明：图表层级的筛选优先于顶部筛选，所有查询模块使用相同的筛选条件
   */
  const effectiveFilters = useMemo<EffectiveFilters>(() => {
    const chartRel = (chartState.level === "secondary" || chartState.level === "tertiary") 
      ? chartState.selectedRelevance || null
      : null;
    const chartSev = chartState.level === "tertiary" 
      ? chartState.selectedSeverity || null
      : null;
    
    return {
      projectId: activeProjectId || null,
      timeRange: filters.timeRange,
      channel,
      contentType,
      sentiment,
      riskScenario,
      topRelevance: relevance,
      chartRelevance: chartRel,
      chartSeverity: chartSev,
      oldestFirst,
    };
  }, [
    activeProjectId,
    filters.timeRange,
    channel,
    contentType,
    sentiment,
    riskScenario,
    relevance,
    chartState.level,
    chartState.selectedRelevance,
    chartState.selectedSeverity,
    oldestFirst,
  ]);

  /**
   * 功能：触发下一页加载（被滚动观察器调用）。
   * 说明：当不在加载中且仍有更多数据时，页码 +1 并发起请求。
   */
  const handleLoadMore = useCallback(() => {
    if (loading || loadingMore || !hasMore) return;
    const next = page + 1;
    setPage(next);
    fetchBatch(next, effectiveFilters);
  }, [fetchBatch, hasMore, loading, loadingMore, page, effectiveFilters]);

  // 监听有效筛选条件变化：重置分页与累计数据，并拉取第一页
  useEffect(() => {
    if (skipListFetchRef.current) {
      skipListFetchRef.current = false;
      return;
    }
    setPage(0);
    setAllRows([]);
    setPosts([]); // 清空posts，避免显示旧数据
    setTotalCount(0); // 重置totalCount为0而不是undefined，避免显示错误的总数
    setHasMore(true);
    fetchBatch(0, effectiveFilters);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [effectiveFilters]);

  // 交叉观察器：观察底部哨兵，一旦进入视口则触发下一页加载
  useEffect(() => {
    const node = sentinelRef.current;
    if (!node) return;
    const observer = new IntersectionObserver((entries) => {
      const first = entries[0];
      if (first.isIntersecting) handleLoadMore();
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, [handleLoadMore]);

  // 根据筛选项加载"全库统计"数据集（独立于分页列表）
  useEffect(() => {
    if (skipGlobalFetchRef.current) {
      skipGlobalFetchRef.current = false;
      return;
    }
    let cancelled = false;
    const run = async () => {
      try {
        if (!supabase) return;
        setGlobalLoading(true);
        const ds = await loadGlobalDataset(supabase, {
          timeRange: filters.timeRange,
          platforms: filters.platforms,
          relevance: filters.relevance,
          priority: filters.priority,
          creatorTypes: filters.creatorTypes,
        }, { projectId: activeProjectId });
        if (!cancelled) {
          setGlobalPostsLite(ds.posts);
          setGlobalMaps(ds.maps);
          setKpiPrev({ prev: ds.previousPosts, label: ds.previousLabel });
          // 设置SQL层面的真实总数
          setGlobalTotalCount(ds.totalCount);
          setGlobalPreviousTotalCount(ds.previousTotalCount);
          // 设置SQL层面的相关性分布count
          setGlobalRelevanceCounts(ds.relevanceCounts);
          // 设置SQL层面的严重度分布count
          setGlobalSeverityCounts(ds.severityCounts);
          // 设置SQL层面的相关内容的严重度分布count
          setGlobalRelevantSeverityCounts(ds.relevantSeverityCounts);
          // 设置高优先级内容的创作者和平台分布
          setGlobalHighPriorityBreakdown(ds.highPriorityBreakdown);
          // 设置各相关性类别的严重度分布
          setGlobalSeverityByRelevance(ds.severityByRelevance);
          // 设置相关内容和高优先级内容的真实总数
          setGlobalRelevantTotal(ds.relevantTotalCount);
          setGlobalHighPriorityTotal(ds.highPriorityTotalCount);
        }
      } finally {
        if (!cancelled) setGlobalLoading(false);
      }
    };
    run();
    return () => { cancelled = true; };
  }, [filters, supabase, activeProjectId]);

  const kpi = useMemo(() => calculateKPI(globalPostsLite, globalMaps, { 
    previousPosts: kpiPrev.prev as any, 
    previousLabel: kpiPrev.label,
    totalCount: globalTotalCount, // 传入SQL层面的真实总数
    previousTotalCount: globalPreviousTotalCount,
    relevantCount: globalRelevantTotal, // 传入SQL层面的相关内容真实count
    highPriorityCount: globalHighPriorityTotal // 传入SQL层面的高优先级内容真实count
  }), [globalPostsLite, globalMaps, kpiPrev, globalTotalCount, globalPreviousTotalCount, globalRelevantTotal, globalHighPriorityTotal]);
  const relevanceChart = useMemo(() => buildRelevanceChartData(globalPostsLite, globalMaps), [globalPostsLite, globalMaps]);

  // 新增：为 KPI 概览准备细分统计数据（总视频 -> 相关性；相关视频 -> 严重度；高优先级 -> 创作者）
  const kpiBreakdown = useMemo(() => {
    // 总视频数：相关/疑似相关/不相关（不含营销）
    // 使用 globalRelevanceCounts（SQL层面的count）而不是 globalPostsLite.length
    const pickRel = (name: string) => {
      if (name === "相关") return globalRelevanceCounts.relevant;
      if (name === "疑似相关") return globalRelevanceCounts.suspicious;
      if (name === "不相关") return globalRelevanceCounts.irrelevant;
      if (name === "营销") return globalRelevanceCounts.marketing;
      return 0;
    };
    const totalCount = globalTotalCount; // 使用SQL count而不是数组长度

    // 相关视频：严重度分布（高/中/低），使用SQL层面的count
    // 重要修正：使用 globalRelevantSeverityCounts（只统计"相关"类别的严重度）
    // 而不是 globalSeverityCounts（全局严重度，包括所有相关性类型）
    const findSev = (name: string) => {
      let count = 0;
      if (name === "高") count = globalRelevantSeverityCounts.high;
      else if (name === "中") count = globalRelevantSeverityCounts.medium;
      else if (name === "低") count = globalRelevantSeverityCounts.low;
      // 这里返回的count是绝对数量，不需要计算百分比
      const percentage = globalRelevantTotal > 0 ? Math.round((count / globalRelevantTotal) * 100) : 0;
      return { count, percentage };
    };

    // 高优先级视频：创作者分布（达人/素人），直接使用SQL统计的结果
    // 重要修正：使用 globalHighPriorityBreakdown（SQL统计）
    // 而不是遍历 globalPostsLite 数组（可能不完整）
    const highCreator = globalHighPriorityBreakdown.creatorTypes;
    const highPlatforms = globalHighPriorityBreakdown.platforms;

    return {
      totalRelevance: { 相关: pickRel("相关"), 疑似相关: pickRel("疑似相关"), 不相关: pickRel("不相关"), total: totalCount },
      relevantSeverity: { 高: findSev("高"), 中: findSev("中"), 低: findSev("低") },
      highCreators: { 达人: highCreator.达人, 素人: highCreator.素人 },
      highPlatforms,
    };
  }, [globalRelevanceCounts, globalRelevantSeverityCounts, globalHighPriorityBreakdown, globalTotalCount, globalRelevantTotal]);
  // 二级图表数据：基于SQL预先统计的数据
  const severityData = useMemo(() => {
    if (chartState.level !== "secondary" || !chartState.selectedRelevance) return null;
    
    const selectedRel = chartState.selectedRelevance;
    const relData = globalSeverityByRelevance[selectedRel];
    
    // 如果SQL统计中没有该相关性类别的数据，回退到使用buildSeverityGroups
    if (!relData) {
      return buildSeverityGroups(selectedRel, globalPostsLite, globalMaps);
    }
    
    // 使用SQL统计的数据，但需要计算创作者和平台分布（从globalPostsLite中筛选）
    const normalizeRel = (v?: string) => {
      const s = String(v || "").trim();
      if (s === "需人工介入") return "疑似相关";
      if (s === "可忽略" || s === "无关") return "不相关";
      if (s === "营销内容") return "营销";
      return s;
    };
    
    const filtered = globalPostsLite.filter((p) => {
      const rel = normalizeRel(globalMaps.relevanceMap[p.platform_item_id] || "");
      if (selectedRel === "营销") return rel === "营销" || rel === "营销内容";
      return rel === selectedRel;
    });
    
    const sevList: ("高" | "中" | "低" | "未标注")[] = ["高", "中", "低", "未标注"];
    const countPlatform = (list: typeof filtered, key: string) => 
      list.filter((x) => String(x.platform || "").toLowerCase().includes(key)).length;
    
    return {
      relevanceType: selectedRel,
      totalCount: relData.total, // 使用SQL统计的总数
      data: sevList.map((s) => {
        const arr = filtered.filter((p) => globalMaps.severityMap[p.platform_item_id] === s);
        const count = s === "高" ? relData.high : s === "中" ? relData.medium : s === "低" ? relData.low : relData.unmarked;
        return {
          severity: s,
          total: count, // 使用SQL统计的count
          percentage: relData.total > 0 ? Math.round((count / relData.total) * 100 * 10) / 10 : 0,
          creators: {
            达人: arr.filter((p) => (globalMaps.creatorTypeMap[p.platform_item_id] || "未标注") === "达人").length,
            素人: arr.filter((p) => (globalMaps.creatorTypeMap[p.platform_item_id] || "未标注") === "素人").length,
            未标注: arr.filter((p) => !globalMaps.creatorTypeMap[p.platform_item_id] || globalMaps.creatorTypeMap[p.platform_item_id] === "未标注").length,
          },
          platforms: {
            抖音: countPlatform(arr, "douyin"),
            小红书: countPlatform(arr, "xiaohongshu"),
            其他: Math.max(0, arr.length - countPlatform(arr, "douyin") - countPlatform(arr, "xiaohongshu")),
          },
        };
      }),
    };
  }, [chartState, globalSeverityByRelevance, globalPostsLite, globalMaps]);
  const severityDetail = useMemo(() => (chartState.level === "tertiary" && chartState.selectedRelevance && chartState.selectedSeverity) ? buildSeverityDetail(chartState.selectedSeverity as any, chartState.selectedRelevance, globalPostsLite, globalMaps) : null, [chartState, globalPostsLite, globalMaps]);
  const [chartsLoading, setChartsLoading] = useState(false);

  // 监控结果列表：直接使用 posts（SQL查询已应用所有筛选条件）
  const visiblePosts = posts;

  const handleRelevanceClick = (name: string) => {
    setChartsLoading(true);
    // 按你的要求：点击仅联动图表层级，不修改全局筛选
    setChartState({ level: "secondary", selectedRelevance: name });
    setTimeout(() => setChartsLoading(false), 300);
  };
  const handleBackToPrimary = () => {
    setChartsLoading(true);
    // 返回一级：只重置图表层级，不修改顶部筛选
    setChartState({ level: "primary" });
    setTimeout(() => setChartsLoading(false), 300);
  };
  const handleBackToSecondary = () => {
    setChartsLoading(true);
    // 返回二级：保持已选相关性，仅更新图表层级
    setChartState({ level: "secondary", selectedRelevance: chartState.selectedRelevance });
    setTimeout(() => setChartsLoading(false), 300);
  };
  // 扩展：支持可选创作者类型，若传入则进入第三级并设置创作者过滤
  const handleSeverityClick = (sev: string, _creatorType?: string) => {
    setChartsLoading(true);
    // 按你的要求：点击仅联动图表层级，不修改全局筛选
    // 修复：不要硬编码为“相关”，应继承当前二级图所选的相关性
    const rel = chartState.selectedRelevance || "相关";
    setChartState({ level: "tertiary", selectedRelevance: rel, selectedSeverity: sev });
    setTimeout(() => setChartsLoading(false), 300);
  };

  useEffect(() => {
    if (loading || globalLoading) return;
    setDashboardCache({
      projectId: activeProjectId || null,
      filters: {
        ...filters,
        relevance: [...filters.relevance],
        priority: [...filters.priority],
        creatorTypes: [...filters.creatorTypes],
        platforms: [...filters.platforms],
      },
      oldestFirst,
      page,
      hasMore,
      totalCount,
      allRows,
      posts,
      risks,
      sentiments,
      relevances,
      totalRiskCn,
      totalRiskReason,
      influencerMap,
      globalPostsLite,
      globalMaps,
      kpiPrev,
      globalTotalCount, // 新增：缓存SQL层面的真实总数
      globalPreviousTotalCount, // 新增：缓存上一周期的真实总数
      globalRelevanceCounts, // 新增：缓存SQL层面的相关性分布count
      globalSeverityCounts, // 新增：缓存SQL层面的严重度分布count（全局）
      globalRelevantSeverityCounts, // 新增：缓存SQL层面的相关内容的严重度分布count
      globalHighPriorityBreakdown, // 新增：缓存高优先级内容的创作者和平台分布
      globalSeverityByRelevance, // 新增：缓存各相关性类别的严重度分布
      globalRelevantTotal, // 新增：缓存相关内容真实总数
      globalHighPriorityTotal, // 新增：缓存高优先级内容真实总数
      chartState,
      scrollTop: (() => {
        const container = document.querySelector(DASHBOARD_SCROLL_SELECTOR);
        if (container instanceof HTMLElement) return container.scrollTop;
        return window.scrollY;
      })(),
      lastUpdated: Date.now(),
    });
  }, [activeProjectId, filters, oldestFirst, page, hasMore, totalCount, allRows, posts, risks, sentiments, relevances, totalRiskCn, totalRiskReason, influencerMap, globalPostsLite, globalMaps, kpiPrev, globalTotalCount, globalPreviousTotalCount, globalRelevanceCounts, globalSeverityCounts, globalRelevantSeverityCounts, globalHighPriorityBreakdown, globalSeverityByRelevance, globalRelevantTotal, globalHighPriorityTotal, chartState, loading, globalLoading]);

  useEffect(() => {
    const handleBeforeUnload = () => {
      updateDashboardScrollTop();
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, []);

  return (
    <div className="space-y-8">
      {/* 顶部筛选（新） */}
      <FilterSection
        filters={filters}
        onFiltersChange={setFilters}
        onResetAll={() => {
          // 当用户点击“重置筛选”，除恢复筛选外，将图表层级同步回到一级，
          // 从而让“内容优先级分布”和“舆情监控结果”一起回到初始视图。
          setChartState({ level: "primary" });
          clearDashboardCache();
        }}
        headerRight={(
          <button
            hidden={true}
            //暂时先把这个按钮隐藏了，不删除代码。
            onClick={() => setImportOpen(true)}
            className="px-4 py-2 rounded-xl bg-gradient-to-r from-blue-500 to-purple-600 text-white font-medium hover:from-blue-600 hover:to-purple-700 transition-all duration-300 hover:scale-105 shadow-lg"
          >
            导入链接分析
          </button>
        )}
      />

      {/* KPI */}
      <KPIOverview
        data={kpi}
        loading={!restoredFromCacheRef.current && (loading || globalLoading)}
        breakdown={kpiBreakdown as any}
        onRelevanceClick={handleRelevanceClick}
        onSeverityClick={handleSeverityClick}
        showTrend={filters.timeRange !== "全部时间"}
      />

      {/* 图表：一级/二级/三级联动 */}
      <ContentAnalysisSection
        chartState={chartState}
        relevanceData={relevanceChart}
        severityData={severityData as any}
        severityDetailData={severityDetail as any}
        loading={!restoredFromCacheRef.current && (loading || chartsLoading || globalLoading)}
        onRelevanceClick={handleRelevanceClick}
        onBackToPrimary={handleBackToPrimary}
        onBackToSecondary={handleBackToSecondary}
        onSeverityClick={handleSeverityClick}
      />

      <MonitoringResults
        posts={visiblePosts}
        loading={loading}
        loadingMore={loadingMore}
        hasMore={hasMore}
        totalCountText={totalCountText}
        oldestFirst={oldestFirst}
        onToggleSort={() => setOldestFirst((v) => !v)}
        sentinelRef={sentinelRef}
        onCardClick={(id) => {
          updateDashboardScrollTop();
          navigate(`/detail/${id}`, { state: { fromDashboard: true } });
        }}
        risks={risks}
        sentiments={sentiments}
        relevances={relevances}
        priorityMapCn={totalRiskCn}
        priorityReasonMap={totalRiskReason}
        formatDuration={formatDuration}
        normalizePlatform={normalizePlatform}
        influencerMap={influencerMap}
        totalCount={totalCount}
      />

      {/* 弹窗：导入链接分析（请求与 Toast 在组件内部处理） */}
      <ImportAnalyzeDialog isOpen={importOpen} onOpenChange={setImportOpen} />
    </div>
  );
}
