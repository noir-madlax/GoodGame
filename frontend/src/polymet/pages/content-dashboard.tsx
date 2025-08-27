 
import FilterBar from "@/polymet/components/filter-bar";
import VideoGridCard from "@/polymet/components/video-grid-card";
import { Grid, List, SortAsc, MoreHorizontal } from "lucide-react";
import { cn } from "@/lib/utils";
import { useNavigate } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import { supabase } from "@/lib/supabase";
import { Skeleton } from "@/components/ui/skeleton";

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

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      try {
        if (!supabase) {
          setLoading(false);
          return;
        }
        const { data: postData } = await supabase
          .from("gg_platform_post")
          .select(
            "id, platform, platform_item_id, title, like_count, comment_count, share_count, cover_url, author_name, duration_ms, published_at, created_at"
          )
          .order("id", { ascending: false })
          .limit(24);

        const postsSafe = (postData || []) as unknown as PostRow[];

        const ids = postsSafe.map((p) => p.platform_item_id).filter(Boolean);
        const risksMap: Record<string, string[]> = {};
        if (ids.length > 0) {
          const { data: riskData } = await supabase
            .from("gg_video_analysis")
            .select("platform_item_id, risk_types")
            .in("platform_item_id", ids);
          (riskData as unknown as RiskRow[] | null)?.forEach((r) => {
            risksMap[r.platform_item_id] = Array.isArray(r.risk_types)
              ? r.risk_types
              : [];
          });
        }

        if (!cancelled) {
          setPosts(postsSafe);
          setRisks(risksMap);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, []);

  const platformToLabel = (platform: string) => {
    if (platform === "douyin") return "抖音";
    if (platform === "redbook") return "小红书";
    if (platform === "bilibili") return "哔哩哔哩";
    return "其他";
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
      <FilterBar />

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
        {loading &&
          Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="rounded-2xl overflow-hidden animate-pulse">
              <div className="relative">
                <Skeleton className="w-full aspect-video" />
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent animate-[shimmer_1.2s_infinite]" />
              </div>
              <div className="p-4 space-y-3">
                <Skeleton className="h-4 w-5/6" />
                <div className="flex gap-2">
                  <Skeleton className="h-5 w-16 rounded-full" />
                  <Skeleton className="h-5 w-16 rounded-full" />
                  <Skeleton className="h-5 w-16 rounded-full" />
                </div>
                <div className="flex gap-3">
                  <Skeleton className="h-3 w-10" />
                  <Skeleton className="h-3 w-10" />
                  <Skeleton className="h-3 w-10" />
                </div>
              </div>
            </div>
          ))}

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
              thumbnail={p.cover_url || "/placeholder.jpg"}
              duration={formatDuration(p.duration_ms)}
              likes={p.like_count || 0}
              comments={p.comment_count || 0}
              shares={p.share_count || 0}
              author={p.author_name || ""}
              platformLabel={platformToLabel(p.platform)}
              riskTags={risks[p.platform_item_id] || []}
              publishDate={(p.published_at || p.created_at).slice(0, 10)}
              onClick={() => navigate(`/detail/${p.platform_item_id}`)}
            />
          ))}
      </div>

      {/* Load More removed per requirement. Future: implement infinite scroll with skeletons. */}
    </div>
  );
}
