 
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
  const timeRange: "all" | "today" | "week" | "month" = (() => {
    const m = filters.timeRange;
    if (m === "今天") return "today";
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
        // 已移除：旧版基于分析/初筛的 id 白名单预过滤逻辑，统一改为在前端应用筛选，保持行为不变但简化实现

        // 构建基础查询（分页、基础条件、可选的 id 白名单）；count 在首屏单独 range(0,0) 获取
        const buildBaseQuery = () => {
          let q = sb
            .from("gg_platform_post")
            .select(
              // NOTE: we also select relevant_status so that we can use it to
              // backfill brand_relevance when deep analysis is not available.
              "id, platform, platform_item_id, author_id, title, original_url, like_count, comment_count, share_count, cover_url, author_name, author_follower_count, duration_ms, published_at, created_at, relevant_status, is_marked",
              { count: "exact" }
            )
            // 与前端展示排序保持一致：按发布时间为主键，空值时回退创建时间，再用 id 保证稳定顺序
            // PostgREST 支持多重 order，无法直接使用表达式 coalesce，这里通过级联排序达到相同效果
            .order("published_at", { ascending: oldestFirst, nullsFirst: oldestFirst })
            .order("created_at", { ascending: oldestFirst })
            .order("id", { ascending: oldestFirst });
          if (channel !== "all") q = q.eq("platform", channel);
          if (contentType !== "all") q = q.eq("post_type", contentType);
          return q;
        };

        if (isFirst) {
          const { count } = await buildBaseQuery().range(0, 0);
          setTotalCount(count || 0);
        }

        // 统一分页：去除“一次性全量加载”的分支，始终按 PAGE_SIZE 分批拉取
        const start = batchIndex * PAGE_SIZE;
        const end = start + PAGE_SIZE - 1;
        const { data: postData } = await buildBaseQuery().range(start, end);
        const postsSafe: PostRow[] = ((postData || []) as unknown) as PostRow[];

        // 前端时间范围过滤（优先使用 published_at，否则使用 created_at）
        // 时间过滤：支持 今天/近2/近3/近7/15/30/全部
        const baseStartAt = resolveStartAt(timeRange);
        let filteredByTime = filterByTime(postsSafe, baseStartAt);
        if (filters.timeRange === "近2天") {
          const today = new Date();
          const start = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 1);
          const end = new Date(today.getFullYear(), today.getMonth(), today.getDate() + 1);
          filteredByTime = filteredByTime.filter((p) => { const t = new Date((p.published_at || p.created_at)); return t >= start && t < end; });
        }
        if (filters.timeRange === "近3天") {
          const today = new Date();
          const start = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 2);
          const end = new Date(today.getFullYear(), today.getMonth(), today.getDate() + 1);
          filteredByTime = filteredByTime.filter((p) => { const t = new Date((p.published_at || p.created_at)); return t >= start && t < end; });
        }
        if (filters.timeRange === "近15天") {
          const d = new Date(); d.setDate(d.getDate() - 15);
          filteredByTime = filterByTime(postsSafe, d);
        }

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

        // 合并新页数据到累计行（服务端已按发布时间排序）；默认仅追加不重排，确保“稳定追加”体验
        const mergedRows = isFirst ? filteredByTime : [...allRows, ...filteredByTime];

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

        // 最终排序：仅当选择“最旧优先”时在客户端按时间正序排序；
        // 默认“最新优先”保持服务端顺序，避免新批次被插入到列表中部
        const postsSorted = oldestFirst ? sortByPublished(postsAfterFilters, true) : postsAfterFilters;

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
  }, [allRows, channel, contentType, oldestFirst, relevance, riskScenario, sentiment, timeRange, risks, sentiments, relevances, filters.timeRange]);

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
  const [, setExtraMaps] = useState<{ severityMap: Record<string, string>; creatorTypeMap: Record<string, string> }>({ severityMap: {}, creatorTypeMap: {} });
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
        }, { projectId: activeProjectId });
        if (!cancelled) {
          setGlobalPostsLite(ds.posts);
          setGlobalMaps(ds.maps);
          // 计算 KPI 时带入上一周期数据
          setKpiPrev({ prev: ds.previousPosts, label: ds.previousLabel });
        }
      } finally {
        if (!cancelled) setGlobalLoading(false);
      }
    };
    run();
    return () => { cancelled = true; };
  }, [filters, supabase, activeProjectId]);

  const [kpiPrev, setKpiPrev] = useState<{ prev: { id: number; platform: string; platform_item_id: string }[]; label?: string }>({ prev: [] });
  const kpi = useMemo(() => calculateKPI(globalPostsLite, globalMaps, { previousPosts: kpiPrev.prev as any, previousLabel: kpiPrev.label }), [globalPostsLite, globalMaps, kpiPrev]);
  const relevanceChart = useMemo(() => buildRelevanceChartData(globalPostsLite, globalMaps), [globalPostsLite, globalMaps]);

  // 新增：为 KPI 概览准备细分统计数据（总视频 -> 相关性；相关视频 -> 严重度；高优先级 -> 创作者）
  const kpiBreakdown = useMemo(() => {
    // 总视频数：相关/疑似相关/不相关（不含营销）
    const relData = buildRelevanceChartData(globalPostsLite, globalMaps);
    const pickRel = (name: string) => relData.find((d: any) => d.name === name)?.value || 0;
    const totalCount = globalPostsLite.length;

    // 相关视频：严重度分布（高/中/低），来自 “相关” 的二级统计
    const sevGroups = buildSeverityGroups("相关", globalPostsLite, globalMaps);
    const findSev = (name: string) => {
      const item = (sevGroups?.data || []).find((x: any) => x.severity === name);
      return { count: item?.total || 0, percentage: item?.percentage || 0 };
    };

    // 高优先级视频：创作者分布（达人/素人），在所有帖子中 severity=高 的子集中统计
    let highCreator = { 达人: 0, 素人: 0 } as { [k: string]: number };
    // 高优先级视频：平台分布（抖音/小红书）
    let highPlatforms = { 抖音: 0, 小红书: 0 } as { [k: string]: number };
    if (globalPostsLite.length > 0) {
      globalPostsLite.forEach((p) => {
        if (globalMaps.severityMap[p.platform_item_id] === "高") {
          const ct = String(globalMaps.creatorTypeMap[p.platform_item_id] || "未标注");
          if (ct === "达人") highCreator.达人 += 1;
          if (ct === "素人") highCreator.素人 += 1;
          const plat = String(p.platform || "").toLowerCase();
          if (plat === "douyin") highPlatforms.抖音 += 1;
          if (plat === "xiaohongshu") highPlatforms.小红书 += 1;
        }
      });
    }

    return {
      totalRelevance: { 相关: pickRel("相关"), 疑似相关: pickRel("疑似相关"), 不相关: pickRel("不相关"), total: totalCount },
      relevantSeverity: { 高: findSev("高"), 中: findSev("中"), 低: findSev("低") },
      highCreators: { 达人: highCreator.达人, 素人: highCreator.素人 },
      highPlatforms,
    };
  }, [globalPostsLite, globalMaps]);
  const [chartState, setChartState] = useState<{ level: "primary" | "secondary" | "tertiary"; selectedRelevance?: string; selectedSeverity?: string }>({ level: "primary" });
  const severityData = useMemo(() => chartState.level === "secondary" && chartState.selectedRelevance ? buildSeverityGroups(chartState.selectedRelevance, globalPostsLite, globalMaps) : null, [chartState, globalPostsLite, globalMaps]);
  const severityDetail = useMemo(() => (chartState.level === "tertiary" && chartState.selectedRelevance && chartState.selectedSeverity) ? buildSeverityDetail(chartState.selectedSeverity as any, chartState.selectedRelevance, globalPostsLite, globalMaps) : null, [chartState, globalPostsLite, globalMaps]);
  const [chartsLoading, setChartsLoading] = useState(false);

  // —— 列表联动与数量统计 ——
  // 有效筛选：若在二/三级图表，则使用图表选择；否则使用顶部筛选
  const effectiveRelevance = useMemo(() => {
    if (chartState.level === "secondary" || chartState.level === "tertiary") return chartState.selectedRelevance || null;
    return filters.relevance[0] || null;
  }, [chartState, filters.relevance]);
  const effectiveSeverity = useMemo(() => {
    if (chartState.level === "tertiary") return chartState.selectedSeverity || null;
    return null;
  }, [chartState]);

  // 监控结果展示的“匹配总数”：不受分页影响，使用全库数据集或已计算的二/三级统计
  const monitoringMatchCount = useMemo(() => {
    if (chartState.level === "tertiary") return severityDetail?.totalCount || 0;
    if (chartState.level === "secondary") return severityData?.totalCount || 0;
    // 一级：全库数据集长度（已受顶部筛选控制）
    return globalPostsLite.length;
  }, [chartState, severityDetail, severityData, globalPostsLite.length]);

  // 监控结果列表联动：在当前已按顶部筛选过滤后的 posts 上，再应用“有效筛选”
  const visiblePosts = useMemo(() => {
    const mapChartRelToBackfilled = (val: string | null) => {
      if (!val) return val;
      if (val === "疑似相关") return "需人工介入";
      if (val === "不相关") return "可忽略";
      return val;
    };
    let arr = posts;
    const relWanted = mapChartRelToBackfilled(effectiveRelevance);
    if (relWanted && relWanted !== "all") {
      arr = arr.filter((p) => (relevances[p.platform_item_id] || "") === relWanted);
    }
    if (effectiveSeverity) {
      arr = arr.filter((p) => (totalRiskCn[p.platform_item_id] || "未标注") === effectiveSeverity);
    }
    return arr;
  }, [posts, effectiveRelevance, effectiveSeverity, relevances, totalRiskCn]);

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
    const selectedRel = "相关";
    setChartState({ level: "tertiary", selectedRelevance: selectedRel, selectedSeverity: sev });
    setTimeout(() => setChartsLoading(false), 300);
  };

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
        }}
        headerRight={(
          <button
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
        loading={loading || globalLoading}
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
        loading={loading || chartsLoading || globalLoading}
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
        onCardClick={(id) => navigate(`/detail/${id}`)}
        risks={risks}
        sentiments={sentiments}
        relevances={relevances}
        priorityMapCn={totalRiskCn}
        priorityReasonMap={totalRiskReason}
        formatDuration={formatDuration}
        normalizePlatform={normalizePlatform}
        influencerMap={influencerMap}
        matchCount={monitoringMatchCount}
      />

      {/* 弹窗：导入链接分析（请求与 Toast 在组件内部处理） */}
      <ImportAnalyzeDialog isOpen={importOpen} onOpenChange={setImportOpen} />
    </div>
  );
}
