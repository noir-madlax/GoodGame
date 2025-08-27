 
import FilterBar, { SentimentValue } from "@/polymet/components/filter-bar";
import VideoGridCard from "@/polymet/components/video-grid-card";
// PlatformBadge used inside child; keep import removed
import { normalizeCoverUrl } from "@/lib/media";
import { Grid, List, SortAsc, MoreHorizontal } from "lucide-react";
import { cn } from "@/lib/utils";
import { useNavigate } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import { supabase } from "@/lib/supabase";
// Skeleton replaced by shared loading skeletons
import { DashboardCardSkeleton } from "@/polymet/components/loading-skeletons";

export default function ContentDashboard() {
  const navigate = useNavigate();

  type PostRow = {
    id: number;
    platform: string;
    platform_item_id: string;
    title: string;
    like_count: number;
    comment_count: number;
    share_count: number;
    cover_url: string | null;
    author_name: string | null;
    duration_ms: number;
    published_at: string | null;
    created_at: string;
  };

  type RiskRow = { platform_item_id: string; risk_types: string[] };

  const [loading, setLoading] = useState(true);
  const [posts, setPosts] = useState<PostRow[]>([]);
  const [risks, setRisks] = useState<Record<string, string[]>>({});
  const [sentiments, setSentiments] = useState<Record<string, string>>({});
  const [relevances, setRelevances] = useState<Record<string, string>>({});
  const [riskOptions, setRiskOptions] = useState<{ id: string; label: string; count: number }[]>([]);
  const [channelOptions, setChannelOptions] = useState<{ id: string; label: string }[]>([]);
  const [typeOptions, setTypeOptions] = useState<{ id: string; label: string }[]>([]);
  const [sentimentOptions, setSentimentOptions] = useState<{ id: SentimentValue; label: string }[]>([]);
  const [relevanceOptions, setRelevanceOptions] = useState<{ id: string; label: string }[]>([]);
  const PLATFORM_LABELS: Record<string, string> = {
    douyin: "抖音",
    xiaohongshu: "小红书",
    xhs: "小红书",
    weibo: "微博",
  };
  const TYPE_LABELS: Record<string, string> = {
    video: "视频",
    image: "图文",
    note: "图文",
    text: "文本",
    unknown: "其他",
  };
  // filters
  const [riskScenario, setRiskScenario] = useState<string>("all");
  const [channel, setChannel] = useState<string>("all");
  const [contentType, setContentType] = useState<string>("all");
  const [timeRange, setTimeRange] = useState<"all" | "today" | "week" | "month">("all");
  const [sentiment, setSentiment] = useState<SentimentValue>("all");
  const [relevance, setRelevance] = useState<string>("all");
  const [oldestFirst, setOldestFirst] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      try {
        if (!supabase) {
          setLoading(false);
          return;
        }
        setLoading(true);
        let query = supabase
          .from("gg_platform_post")
          .select(
            "id, platform, platform_item_id, title, like_count, comment_count, share_count, cover_url, author_name, duration_ms, published_at, created_at"
          )
          .order("id", { ascending: false })
          .limit(24);

        if (channel !== "all") query = query.eq("platform", channel);
        if (contentType !== "all") query = query.eq("post_type", contentType);
        const { data: postData } = await query;

        const postsSafe = (postData || []) as unknown as PostRow[];

        // client-side time range filter using published_at/created_at
        const now = new Date();
        let startAt: Date | null = null;
        if (timeRange === "today") {
          startAt = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        } else if (timeRange === "week") {
          const d = new Date(now);
          d.setDate(d.getDate() - 7);
          startAt = d;
        } else if (timeRange === "month") {
          const d = new Date(now);
          d.setMonth(d.getMonth() - 1);
          startAt = d;
        }

        const filteredByTime = startAt
          ? postsSafe.filter((p) => {
              const ts = new Date((p.published_at || p.created_at));
              return ts >= startAt!;
            })
          : postsSafe;

        // dynamic filter options from actual data
        const platformSet = new Set<string>();
        const typeSet = new Set<string>();
        filteredByTime.forEach((p) => {
          if (p.platform) platformSet.add(String(p.platform));
          // post_type not in selected fields; fetch inferred via risks? We rely on postsSafe earlier selection includes post_type? It doesn't.
        });

        // fetch post_type via another lightweight query scoped by ids to avoid schema change
        const idsForTypes = filteredByTime.map((p) => p.id);
        if (idsForTypes.length > 0) {
          const { data: typeRows } = await supabase
            .from("gg_platform_post")
            .select("id, post_type")
            .in("id", idsForTypes);
          (typeRows || []).forEach((r: any) => {
            if (r.post_type) typeSet.add(String(r.post_type));
          });
        }

        const ids = filteredByTime.map((p) => p.platform_item_id).filter(Boolean);
        const risksMap: Record<string, string[]> = {};
        const sentimentsMap: Record<string, string> = {};
        const relevanceMap: Record<string, string> = {};
        const riskCountMap: Record<string, number> = {};
        const sentimentSet = new Set<string>();
        const relevanceSet = new Set<string>();
        if (ids.length > 0) {
          let riskQuery = supabase
            .from("gg_video_analysis")
            .select("platform_item_id, risk_types, sentiment, brand_relevance")
            .in("platform_item_id", ids);
          // 不在这里按 sentiment 过滤，以便枚举选项不受当前筛选影响
          const { data: riskData } = await riskQuery;
          (riskData as unknown as (RiskRow & { sentiment?: string; brand_relevance?: string })[] | null)?.forEach((r) => {
            const raw = (r as any).risk_types;
            const names: string[] = Array.isArray(raw)
              ? raw.map((x: any) => (typeof x === "string" ? x : (x?.category || x?.scenario || ""))).filter(Boolean)
              : [];
            risksMap[r.platform_item_id] = names;
            names.forEach((name) => {
              riskCountMap[name] = (riskCountMap[name] || 0) + 1;
            });
            if ((r as any).sentiment) sentimentsMap[r.platform_item_id] = String((r as any).sentiment);
            if ((r as any).sentiment) sentimentSet.add(String((r as any).sentiment));
            if ((r as any).brand_relevance) {
              const rel = String((r as any).brand_relevance);
              relevanceMap[r.platform_item_id] = rel;
              relevanceSet.add(rel);
            }
          });
        }

        // apply riskScenario and sentiment filter on posts
        let postsAfterFilters = filteredByTime;
        if (sentiment !== "all") {
          postsAfterFilters = postsAfterFilters.filter((p) => sentimentsMap[p.platform_item_id] === sentiment);
        }
        if (riskScenario !== "all") {
          postsAfterFilters = postsAfterFilters.filter((p) => (risksMap[p.platform_item_id] || []).includes(riskScenario));
        }
        if (relevance !== "all") {
          postsAfterFilters = postsAfterFilters.filter((p) => (relevanceMap[p.platform_item_id] || "") === relevance);
        }

        // sort by time using published_at if present, else created_at
        const postsSorted = [...postsAfterFilters].sort((a, b) => {
          const ta = new Date((a.published_at || a.created_at)).getTime();
          const tb = new Date((b.published_at || b.created_at)).getTime();
          return oldestFirst ? ta - tb : tb - ta;
        });

        // build risk options for dropdown (top 8)
        const riskOpts = [
          { id: "all", label: "全部场景", count: Object.values(riskCountMap).reduce((a, b) => a + b, 0) },
          ...Object.entries(riskCountMap)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 8)
            .map(([k, v]) => ({ id: k, label: k, count: v })),
        ];

        const channelOpts = [{ id: "all", label: "全部渠道" }, ...Array.from(platformSet).map((p) => ({ id: p, label: PLATFORM_LABELS[p] || p }))];
        const typeOpts = [{ id: "all", label: "全部类型" }, ...Array.from(typeSet).map((t) => ({ id: t, label: TYPE_LABELS[t] || t }))];
        const sentimentOpts: { id: SentimentValue; label: string }[] = [
          { id: "all", label: "全部情绪" },
          ...Array.from(sentimentSet).map((s) => ({ id: s as SentimentValue, label: s === "positive" ? "正向" : s === "neutral" ? "中立" : "负面" })),
        ];
        const relevanceOpts = [{ id: "all", label: "全部相关性" }, ...Array.from(relevanceSet).map((r) => ({ id: r, label: r }))];

        if (!cancelled) {
          setPosts(postsSorted);
          setRisks(risksMap);
          setSentiments(sentimentsMap);
          setRelevances(relevanceMap);
          setRiskOptions(riskOpts);
          setChannelOptions(channelOpts);
          setTypeOptions(typeOpts);
          setSentimentOptions(sentimentOpts);
          setRelevanceOptions(relevanceOpts);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [channel, contentType, sentiment, relevance, riskScenario, timeRange, oldestFirst]);

  const normalizePlatform = (platform: string) => {
    const key = String(platform || "").toLowerCase();
    if (key === "xiaohongshu" || key === "xhs") return "xiaohongshu";
    return key;
  };

  const formatDuration = (ms: number) => {
    const total = Math.max(0, Math.round(ms / 1000));
    const m = Math.floor(total / 60)
      .toString()
      .padStart(1, "0");
    const s = (total % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  };

  const totalCountText = useMemo(() => posts.length.toLocaleString(), [posts.length]);

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
        riskOptions={riskOptions}
        channelOptions={channelOptions}
        typeOptions={typeOptions}
        sentimentOptions={sentimentOptions}
        relevanceOptions={relevanceOptions}
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
            内容监控结果
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            共找到 {totalCountText} 条相关内容
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

        {!loading && posts.length === 0 && (
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
              onClick={() => navigate(`/detail/${p.platform_item_id}`)}
            />
          ))}
      </div>

      {/* Load More removed per requirement. Future: implement infinite scroll with skeletons. */}
    </div>
  );
}
