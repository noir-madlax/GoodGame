 
import FilterBar, { SentimentValue } from "@/polymet/components/filter-bar";
import VideoGridCard from "@/polymet/components/video-grid-card";
// PlatformBadge used inside child; keep import removed
import { normalizeCoverUrl } from "@/lib/media";
import { Grid, List, SortAsc, MoreHorizontal } from "lucide-react";
import { cn } from "@/lib/utils";
import { useNavigate } from "react-router-dom";
import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { supabase } from "@/lib/supabase";
// Skeleton replaced by shared loading skeletons
import { DashboardCardSkeleton } from "@/polymet/components/loading-skeletons";
import { backfillRelevance, buildRelevanceWhitelist, resolveStartAt, filterByTime, sortByPublished, buildAnalysisMaps, buildTopRiskOptions } from "@/polymet/lib/filters";

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
  const [riskOptions, setRiskOptions] = useState<{ id: string; label: string; count: number }[]>([]); // 风险场景 TopN 选项（保留供 FilterBar 覆盖使用）
  // label maps moved to FilterBar; keep page lean
  // filters（筛选器当前值）
  const [riskScenario, setRiskScenario] = useState<string>("all"); // 风险场景
  const [channel, setChannel] = useState<string>("all"); // 渠道/平台
  const [contentType, setContentType] = useState<string>("all"); // 内容类型（视频/图文等）
  const [timeRange, setTimeRange] = useState<"all" | "today" | "week" | "month">("all"); // 时间范围
  const [sentiment, setSentiment] = useState<SentimentValue>("all"); // 情绪
  const [relevance, setRelevance] = useState<string>("all"); // 品牌相关性
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
        const startAt = resolveStartAt(timeRange);
        const filteredByTime = filterByTime(postsSafe, startAt);

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
            .select("platform_item_id, risk_types, sentiment, brand_relevance")
            .in("platform_item_id", ids);
          // 不在这里按 sentiment 过滤，以便枚举选项不受当前筛选影响
          const { data: riskData } = await riskQuery;
          const maps = buildAnalysisMaps((riskData || []) as unknown as { platform_item_id: string; risk_types?: unknown; sentiment?: string | null; brand_relevance?: string | null }[]);
          risksMap = { ...risksMap, ...maps.risksMap };
          sentimentsMap = { ...sentimentsMap, ...maps.sentimentsMap };
          relevanceMap = { ...relevanceMap, ...maps.relevanceMap };
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
  }, [channel, contentType, sentiment, relevance, riskScenario, timeRange, oldestFirst]);

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

  return (
    <div className="space-y-8">
      {/* Filter Bar */}
      <FilterBar
        riskScenario={riskScenario}
        channel={channel}
        contentType={contentType}
        timeRange={timeRange}
        sentiment={sentiment}
        relevance={relevance}
        onChange={(next) => {
          if (next.riskScenario !== undefined) setRiskScenario(next.riskScenario);
          if (next.channel !== undefined) setChannel(next.channel);
          if (next.contentType !== undefined) setContentType(next.contentType);
          if (next.timeRange !== undefined) setTimeRange(next.timeRange);
          if (next.sentiment !== undefined) setSentiment(next.sentiment);
          if (next.relevance !== undefined) setRelevance(next.relevance);
        }}
      />

      {/* Content Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            舆情监控结果
          </h2>
          <p className="text-gray-600 dark:text-gray-400 min-h-6">
            {loading ? (
              <span className="inline-block h-4 w-24 bg-gray-300/50 dark:bg-gray-600/50 rounded animate-pulse" />
            ) : (
              <>共找到 {totalCountText} 条相关内容</>
            )}
          </p>
        </div>

        {/* View Controls */}
        <div className="flex items-center space-x-4">
          {/* Sort Button */}
          <button
            onClick={() => setOldestFirst((v) => !v)}
            className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-gray-100/40 dark:bg-gray-800/30 backdrop-blur-xl border border-white/20 text-gray-700 dark:text-gray-200 transition-all duration-300 hover:bg-gray-100/60 dark:hover:bg-gray-800/50"
            aria-label="Sort by time"
            title="Sort by time"
          >
            <SortAsc className={cn("w-4 h-4 transition-transform", oldestFirst && "rotate-180")} />
            <span className="text-sm font-medium">
              按时间排序
            </span>
          </button>

          {/* View Mode Toggle */}
          <div className="flex items-center rounded-xl bg-white/10 backdrop-blur-xl border border-white/20 p-1">
            <button className="p-2 rounded-lg text-gray-400 bg-transparent cursor-not-allowed" disabled aria-disabled>
              <Grid className="w-4 h-4" />
            </button>
            <button className="p-2 rounded-lg text-gray-400 bg-transparent cursor-not-allowed" disabled aria-disabled>
              <List className="w-4 h-4" />
            </button>
          </div>

          {/* More Options */}
          <button
            className="p-2 rounded-xl bg-gray-100/40 dark:bg-gray-800/30 backdrop-blur-xl border border-white/20 text-gray-400 cursor-not-allowed"
            disabled
            aria-disabled
            title="Not implemented yet"
          >
            <MoreHorizontal className="w-5 h-5 text-gray-600 dark:text-gray-300" />
          </button>
        </div>
      </div>

      {/* Content Grid */}
      <div
        className={cn(
          "grid gap-6 transition-all duration-500 grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
        )}
      >
        {loading && Array.from({ length: 8 }).map((_, i) => <DashboardCardSkeleton key={i} />)}

        {!loading && posts.length === 0 && !loadingMore && (
          <div className="col-span-full flex items-center justify-center text-gray-500 dark:text-gray-400 py-16">
            暂无内容
          </div>
        )}

        {!loading &&
          posts.map((p) => (
            <VideoGridCard
              key={p.id}
              title={p.title}
              platform={normalizePlatform(p.platform)}
              thumbnail={normalizeCoverUrl(p.cover_url)}
              duration={formatDuration(p.duration_ms)}
              likes={p.like_count || 0}
              comments={p.comment_count || 0}
              shares={p.share_count || 0}
              author={p.author_name || ""}
              // Platform badge is rendered inside card; keep for alignment
              platformLabel={normalizePlatform(p.platform)}
              riskTags={risks[p.platform_item_id] || []}
              sentiment={sentiments[p.platform_item_id]}
              brandRelevance={relevances[p.platform_item_id]}
              publishDate={(p.published_at || p.created_at).slice(0, 10)}
              originalUrl={p.original_url || undefined}
              isMarked={Boolean(p.is_marked)}
              onClick={() => navigate(`/detail/${p.platform_item_id}`)}
            />
          ))}

        {loadingMore && Array.from({ length: 8 }).map((_, i) => <DashboardCardSkeleton key={`more-${i}`} />)}
      </div>
      {(!hasMore && !loading && posts.length > 0) && (
        <div className="text-center text-gray-500 dark:text-gray-400 py-6">已到末尾</div>
      )}
      <div ref={sentinelRef} aria-hidden className="h-6" />
    </div>
  );
}
