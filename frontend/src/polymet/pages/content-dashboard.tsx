 
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
import { backfillRelevance, buildRelevanceWhitelist, resolveStartAt, filterByTime, sortByPublished, buildAnalysisMaps, buildTopRiskOptions } from "@/polymet/lib/filters";
import { calculateKPI, buildRelevanceChartData, buildSeverityGroups, buildSeverityDetail, mapDbSeverityToCn, AnalysisMaps, loadGlobalDataset } from "@/polymet/lib/analytics";

export default function ContentDashboard() {
  const navigate = useNavigate();

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

  type PostRow = {
    id: number;
    platform: string;
    platform_item_id: string;
    title: string;
    original_url?: string | null;
    like_count: number;
    comment_count: number;
    share_count: number;
    cover_url: string | null;
    author_name: string | null;
    duration_ms: number;
    published_at: string | null;
    created_at: string;
    is_marked?: boolean | null;
    /**
     * 中文设计说明：
     * 1) relevant_status 来源于 gg_platform_post，属于【初筛】结论；值域：yes/no/maybe/unknown。
     * 2) brand_relevance 来源于 gg_video_analysis，属于【细分分析】结论；值域：相关/疑似相关/不相关（或缺省）。
     * 3) 业务优先级：细分覆盖初筛。即：若 brand_relevance 存在，用它作为“最终相关性”；否则，使用 relevant_status 做回填。
     * 4) 回填映射：
     *    yes   -> 相关
     *    maybe -> 疑似相关
     *    no    -> 不相关
     *    其余  -> 不设置（视为未知，不参与“相关性”筛选命中）
     * 5) 页面筛选“相关性=相关/疑似相关/不相关”时，统一针对“最终相关性”生效。
     */
    relevant_status?: string | null;
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
  // label maps moved to FilterBar; keep page lean
  // filters（筛选器当前值）
  // 新顶层筛选（与设计稿一致）
  // 默认时间改为“全部时间”
  const [filters, setFilters] = useState<FiltersState>({ timeRange: "全部时间", relevance: [], priority: [], creatorTypes: [], platforms: [] });
  // 为保持旧数据加载逻辑，这里映射出必要的旧筛选位
  const riskScenario = "all"; // 本页一期不暴露风险场景选择；保留旧变量
  const channel = filters.platforms.length === 1 ? (filters.platforms[0] === "抖音" ? "douyin" : filters.platforms[0] === "小红书" ? "xiaohongshu" : "all") : "all";
  const contentType = "all";
  const timeRange: "all" | "today" | "week" | "month" = (() => {
    const m = filters.timeRange;
    if (m === "今天") return "today";
    if (m === "昨天" || m === "前天") return "today"; // 实际过滤在下方自定义逻辑补充
    if (m === "近7天") return "week";
    if (m === "近15天" || m === "近30天") return "month";
    return "all";
  })();
  const sentiment = "all" as const; // 本版先不提供情绪筛选入口
  const relevance = filters.relevance[0] || "all";
  const [oldestFirst, setOldestFirst] = useState(false); // 排序方向（false=最新优先，true=最旧优先）
  const sentinelRef = useRef<HTMLDivElement | null>(null); // 无限滚动的哨兵元素

  /**
   * 功能：按页拉取帖子并在前端应用时间过滤、分析映射、相关性回填、筛选与排序。
   * 调用时机：首屏加载与滚动触底追加；每次筛选条件或排序方向变更后会重置并重新请求。
   * 参数：batchIndex - 分页索引，从 0 开始。
   */
  const fetchBatch = useCallback(async (batchIndex: number) => {
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
        // 预取：当情绪/相关性/风险场景任一筛选被激活时，先从分析/初筛构建 platform_item_id 白名单
        const analysisFiltered = sentiment !== "all" || relevance !== "all" || riskScenario !== "all";
        let idWhitelist: string[] | null = null;
        if (analysisFiltered) {
          idWhitelist = await buildRelevanceWhitelist(sb, { sentiment, relevance, riskScenario });
          // If analysis filter active but no matching ids, short-circuit to empty result
          if (idWhitelist.length === 0) {
            if (!cancelled) {
              setTotalCount(0);
              setHasMore(false);
              setAllRows([]);
              setPosts([]);
              setRisks({});
              setSentiments({});
              setRelevances({});
            }
            return;
          }
        }

        // 构建基础查询（分页、基础条件、可选的 id 白名单）；count 在首屏单独 range(0,0) 获取
        const buildBaseQuery = () => {
          let q = sb
            .from("gg_platform_post")
            .select(
              // NOTE: we also select relevant_status so that we can use it to
              // backfill brand_relevance when deep analysis is not available.
              "id, platform, platform_item_id, title, original_url, like_count, comment_count, share_count, cover_url, author_name, duration_ms, published_at, created_at, relevant_status, is_marked",
              { count: "exact" }
            )
            .order("id", { ascending: false });
          if (channel !== "all") q = q.eq("platform", channel);
          if (contentType !== "all") q = q.eq("post_type", contentType);
          if (idWhitelist && idWhitelist.length > 0) q = q.in("platform_item_id", idWhitelist);
          return q;
        };

        if (isFirst) {
          const { count } = await buildBaseQuery().range(0, 0);
          setTotalCount(count || 0);
        }

        const start = batchIndex * PAGE_SIZE;
        const end = start + PAGE_SIZE - 1;
        const { data: postData } = await buildBaseQuery().range(start, end);
        const postsSafe = (postData || []) as unknown as PostRow[];

        // 前端时间范围过滤（优先使用 published_at，否则使用 created_at）
        // 时间过滤：支持 今天/昨天/前天/近7/15/30/全部
        const baseStartAt = resolveStartAt(timeRange);
        let filteredByTime = filterByTime(postsSafe, baseStartAt);
        if (filters.timeRange === "昨天") {
          const today = new Date();
          const start = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 1);
          const end = new Date(today.getFullYear(), today.getMonth(), today.getDate());
          filteredByTime = filteredByTime.filter((p) => {
            const t = new Date((p.published_at || p.created_at));
            return t >= start && t < end;
          });
        }
        if (filters.timeRange === "前天") {
          const today = new Date();
          const start = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 2);
          const end = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 1);
          filteredByTime = filteredByTime.filter((p) => {
            const t = new Date((p.published_at || p.created_at));
            return t >= start && t < end;
          });
        }
        if (filters.timeRange === "近15天") {
          const d = new Date(); d.setDate(d.getDate() - 15);
          filteredByTime = filterByTime(postsSafe, d);
        }

        // 动态统计（示例保留）：从当前页数据统计平台与类型集合
        const platformSet = new Set<string>();
        const typeSet = new Set<string>();
        filteredByTime.forEach((p) => {
          if (p.platform) platformSet.add(String(p.platform));
          // post_type not in selected fields; fetch inferred via risks? We rely on postsSafe earlier selection includes post_type? It doesn't.
        });

        // fetch post_type via another lightweight query scoped by ids to avoid schema change
        const idsForTypes = filteredByTime.map((p) => p.id);
        if (idsForTypes.length > 0) {
          const { data: typeRows } = await sb
            .from("gg_platform_post")
            .select("id, post_type")
            .in("id", idsForTypes);
          (typeRows || []).forEach((r: { id: number; post_type: string | null }) => {
            if (r.post_type) typeSet.add(String(r.post_type));
          });
        }

        const ids = filteredByTime.map((p) => p.platform_item_id).filter(Boolean); // 本页涉及的平台内容主键集合
        let risksMap: Record<string, string[]> = { ...risks };
        let sentimentsMap: Record<string, string> = { ...sentiments };
        let relevanceMap: Record<string, string> = { ...relevances };
        // 读取分析数据并构建映射（风险/情绪/品牌相关性），并据此生成风险 TopN 选项
        if (ids.length > 0) {
          const riskQuery = sb
            .from("gg_video_analysis")
            .select("platform_item_id, risk_types, sentiment, brand_relevance, severity, \"creatorTypes\"")
            .in("platform_item_id", ids);
          // 不在这里按 sentiment 过滤，以便枚举选项不受当前筛选影响
          const { data: riskData } = await riskQuery;
          const mapsRaw = (riskData || []) as unknown as { platform_item_id: string; risk_types?: unknown; sentiment?: string | null; brand_relevance?: string | null; severity?: string | null; creatorTypes?: string | null }[];
          const maps = buildAnalysisMaps(mapsRaw);
          risksMap = { ...risksMap, ...maps.risksMap };
          sentimentsMap = { ...sentimentsMap, ...maps.sentimentsMap };
          relevanceMap = { ...relevanceMap, ...maps.relevanceMap };
          // 构建严重度与创作者类型映射（用于图表/KPI）
          const sevMap: Record<string, string> = {};
          const ctMap: Record<string, string> = {};
          mapsRaw.forEach((r) => {
            if (r.platform_item_id) {
              sevMap[r.platform_item_id] = mapDbSeverityToCn(r.severity || "");
              const ct = String(r.creatorTypes || "").trim();
              ctMap[r.platform_item_id] = ct || "未标注";
            }
          });
          setExtraMaps({ severityMap: sevMap, creatorTypeMap: ctMap });
          // ignore counts/sets in page scope
          setRiskOptions(buildTopRiskOptions(maps.riskCountMap, 8));
        }

        // 回填相关性（细分覆盖初筛）
        // --------------------------------------------------------------
        // 若某条内容具备 brand_relevance（来自 gg_video_analysis），则以其为准。
        // 否则使用 gg_platform_post.relevant_status（初筛）进行回填，映射关系：
        // yes->相关；maybe->疑似相关；no->不相关；unknown/null->忽略。
        const relevanceMapBackfilled = backfillRelevance(relevanceMap, filteredByTime);

        // 合并新页数据到累计行，用于在前端统一再筛选/排序
        const mergedRows = batchIndex === 0 ? filteredByTime : [...allRows, ...filteredByTime];

        // 在累计行上应用筛选条件（情绪 / 风险场景 / 品牌相关性）
        let postsAfterFilters = mergedRows;
        if (sentiment !== "all") {
          postsAfterFilters = postsAfterFilters.filter((p) => sentimentsMap[p.platform_item_id] === sentiment);
        }
        if (riskScenario !== "all") {
          postsAfterFilters = postsAfterFilters.filter((p) => (risksMap[p.platform_item_id] || []).includes(riskScenario));
        }
        if (relevance !== "all") {
          postsAfterFilters = postsAfterFilters.filter((p) => (relevanceMapBackfilled[p.platform_item_id] || "") === relevance);
        }

        // 最终按时间排序（优先 published_at，否则 created_at）
        const postsSorted = sortByPublished(postsAfterFilters, oldestFirst);

        // options are loaded by FilterBar from gg_filter_enums; page no longer sets them

        if (!cancelled) {
          setHasMore(postsSafe.length === PAGE_SIZE);
          setAllRows(mergedRows);
          setPosts(postsSorted);
          setRisks(risksMap);
          setSentiments(sentimentsMap);
          setRelevances(relevanceMapBackfilled);
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
  }, [allRows, channel, contentType, oldestFirst, relevance, riskScenario, sentiment, timeRange, risks, sentiments, relevances]);

  // 首屏加载与筛选/排序变化时：重置分页与累计数据，并拉取第一页
  useEffect(() => {
    setPage(0);
    setAllRows([]);
    setHasMore(true);
    fetchBatch(0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [channel, contentType, sentiment, relevance, riskScenario, timeRange, oldestFirst, filters.timeRange]);

  /**
   * 功能：触发下一页加载（被滚动观察器调用）。
   * 说明：当不在加载中且仍有更多数据时，页码 +1 并发起请求。
   */
  const handleLoadMore = useCallback(() => {
    if (loading || loadingMore || !hasMore) return;
    const next = page + 1;
    setPage(next);
    fetchBatch(next);
  }, [fetchBatch, hasMore, loading, loadingMore, page]);

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

  const normalizePlatform = normalizePlatformKey; // 平台 key 归一化（如 xhs -> xiaohongshu）
  const formatDuration = formatDurationMs; // 毫秒时长格式化为 mm:ss

  const totalCountText = useMemo(() => (totalCount || posts.length).toLocaleString(), [totalCount, posts.length]);

  // —— 新增：图表与 KPI（全库统计版本） ——
  const [extraMaps, setExtraMaps] = useState<{ severityMap: Record<string, string>; creatorTypeMap: Record<string, string> }>({ severityMap: {}, creatorTypeMap: {} });
  const [globalLoading, setGlobalLoading] = useState(false);
  const [globalPostsLite, setGlobalPostsLite] = useState<{ id: number; platform: string; platform_item_id: string }[]>([]);
  const [globalMaps, setGlobalMaps] = useState<AnalysisMaps>({ relevanceMap: {}, severityMap: {} as any, creatorTypeMap: {} });

  // 根据筛选项加载“全库统计”数据集（独立于分页列表）
  useEffect(() => {
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
        });
        if (!cancelled) {
          setGlobalPostsLite(ds.posts);
          setGlobalMaps(ds.maps);
        }
      } finally {
        if (!cancelled) setGlobalLoading(false);
      }
    };
    run();
    return () => { cancelled = true; };
  }, [filters, supabase]);

  const kpi = useMemo(() => calculateKPI(globalPostsLite, globalMaps), [globalPostsLite, globalMaps]);
  const relevanceChart = useMemo(() => buildRelevanceChartData(globalPostsLite, globalMaps), [globalPostsLite, globalMaps]);
  const [chartState, setChartState] = useState<{ level: "primary" | "secondary" | "tertiary"; selectedRelevance?: string; selectedSeverity?: string }>({ level: "primary" });
  const severityData = useMemo(() => chartState.level === "secondary" && chartState.selectedRelevance ? buildSeverityGroups(chartState.selectedRelevance, globalPostsLite, globalMaps) : null, [chartState, globalPostsLite, globalMaps]);
  const severityDetail = useMemo(() => (chartState.level === "tertiary" && chartState.selectedRelevance && chartState.selectedSeverity) ? buildSeverityDetail(chartState.selectedSeverity as any, chartState.selectedRelevance, globalPostsLite, globalMaps) : null, [chartState, globalPostsLite, globalMaps]);
  const [chartsLoading, setChartsLoading] = useState(false);

  const handleRelevanceClick = (name: string) => {
    setChartsLoading(true);
    setChartState({ level: "secondary", selectedRelevance: name });
    setFilters({ ...filters, relevance: [name], priority: [] });
    setTimeout(() => setChartsLoading(false), 300);
  };
  const handleBackToPrimary = () => {
    setChartsLoading(true);
    setChartState({ level: "primary" });
    setFilters({ timeRange: "全部时间", relevance: [], priority: [], creatorTypes: [], platforms: [] });
    setTimeout(() => setChartsLoading(false), 300);
  };
  const handleBackToSecondary = () => {
    setChartsLoading(true);
    setChartState({ level: "secondary", selectedRelevance: chartState.selectedRelevance });
    setFilters({ ...filters, relevance: chartState.selectedRelevance ? [chartState.selectedRelevance] : [], priority: [] });
    setTimeout(() => setChartsLoading(false), 300);
  };
  const handleSeverityClick = (sev: string) => {
    setChartsLoading(true);
    setChartState({ level: "tertiary", selectedRelevance: chartState.selectedRelevance, selectedSeverity: sev });
    setFilters({ ...filters, priority: [sev] });
    setTimeout(() => setChartsLoading(false), 300);
  };

  return (
    <div className="space-y-8">
      {/* 顶部筛选（新） */}
      <FilterSection filters={filters} onFiltersChange={setFilters} />

      {/* KPI */}
      <KPIOverview data={kpi} loading={loading || globalLoading} />

      {/* 图表：一级/二级/三级联动 */}
      <ContentAnalysisSection
        chartState={chartState}
        relevanceData={relevanceChart}
        severityData={severityData as any}
        severityDetailData={severityDetail as any}
        loading={loading || chartsLoading || globalLoading}
        onRelevanceClick={handleRelevanceClick}
        onBackToPrimary={handleBackToPrimary}
        onBackToSecondary={handleBackToSecondary}
        onSeverityClick={handleSeverityClick}
      />

      <MonitoringResults
        posts={posts}
        loading={loading}
        loadingMore={loadingMore}
        hasMore={hasMore}
        totalCountText={totalCountText}
        oldestFirst={oldestFirst}
        onToggleSort={() => setOldestFirst((v) => !v)}
        sentinelRef={sentinelRef}
        onCardClick={(id) => navigate(`/detail/${id}`)}
        risks={risks}
        sentiments={sentiments}
        relevances={relevances}
        formatDuration={formatDuration}
        normalizePlatform={normalizePlatform}
      />
    </div>
  );
}
