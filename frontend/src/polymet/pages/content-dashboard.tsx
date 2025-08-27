 
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
  // filters
  const [riskScenario, setRiskScenario] = useState<string>("all");
  const [channel, setChannel] = useState<string>("all");
  const [contentType, setContentType] = useState<string>("all");
  const [timeRange, setTimeRange] = useState<"all" | "today" | "week" | "month">("all");
  const [sentiment, setSentiment] = useState<SentimentValue>("all");

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      try {
        if (!supabase) {
          setLoading(false);
          return;
        }
        let query = supabase
          .from("gg_platform_post")
          .select(
            "id, platform, platform_item_id, title, like_count, comment_count, share_count, cover_url, author_name, duration_ms, published_at, created_at"
          )
          .order("id", { ascending: false })
          .limit(24);

        if (channel !== "all") query = query.eq("platform", channel);
        if (contentType !== "all") query = query.eq("post_type", contentType);
        // timeRange (basic client filter)
        const { data: postData } = await query;

        const postsSafe = (postData || []) as unknown as PostRow[];

        const ids = postsSafe.map((p) => p.platform_item_id).filter(Boolean);
        const risksMap: Record<string, string[]> = {};
        const sentimentsMap: Record<string, string> = {};
        if (ids.length > 0) {
          let riskQuery = supabase
            .from("gg_video_analysis")
            .select("platform_item_id, risk_types, sentiment")
            .in("platform_item_id", ids);
          if (sentiment !== "all") riskQuery = riskQuery.eq("sentiment", sentiment);
          const { data: riskData } = await riskQuery;
          (riskData as unknown as (RiskRow & { sentiment?: string })[] | null)?.forEach((r) => {
            risksMap[r.platform_item_id] = Array.isArray(r.risk_types)
              ? r.risk_types
              : [];
            if ((r as any).sentiment) sentimentsMap[r.platform_item_id] = String((r as any).sentiment);
          });
        }

        if (!cancelled) {
          setPosts(postsSafe);
          setRisks(risksMap);
          setSentiments(sentimentsMap);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [channel, contentType, sentiment]);

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
        onChange={(next) => {
          if (next.riskScenario !== undefined) setRiskScenario(next.riskScenario);
          if (next.channel !== undefined) setChannel(next.channel);
          if (next.contentType !== undefined) setContentType(next.contentType);
          if (next.timeRange !== undefined) setTimeRange(next.timeRange);
          if (next.sentiment !== undefined) setSentiment(next.sentiment);
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
            className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-gray-100/40 dark:bg-gray-800/30 backdrop-blur-xl border border-white/20 text-gray-400 cursor-not-allowed transition-all duration-300"
            disabled
            aria-disabled
            title="Not implemented yet"
          >
            <SortAsc className="w-4 h-4 text-gray-600 dark:text-gray-300" />

            <span className="text-sm font-medium text-gray-400">
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
              publishDate={(p.published_at || p.created_at).slice(0, 10)}
              onClick={() => navigate(`/detail/${p.platform_item_id}`)}
            />
          ))}
      </div>

      {/* Load More removed per requirement. Future: implement infinite scroll with skeletons. */}
    </div>
  );
}
