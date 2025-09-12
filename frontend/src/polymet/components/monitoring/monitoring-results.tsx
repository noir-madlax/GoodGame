import React, { MutableRefObject } from "react";
import { Grid, List, MoreHorizontal, SortAsc } from "lucide-react";
import { cn } from "@/lib/utils";
import { DashboardCardSkeleton } from "@/polymet/components/loading-skeletons";
import VideoGridCard from "@/polymet/components/video-grid-card";
import { normalizeCoverUrl } from "@/lib/media";

export interface PostRowLite {
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
}

export default function MonitoringResults({
  posts,
  loading,
  loadingMore,
  hasMore,
  totalCountText,
  oldestFirst,
  onToggleSort,
  sentinelRef,
  onCardClick,
  risks,
  sentiments,
  relevances,
  formatDuration,
  normalizePlatform,
}: {
  posts: PostRowLite[];
  loading: boolean;
  loadingMore: boolean;
  hasMore: boolean;
  totalCountText: string;
  oldestFirst: boolean;
  onToggleSort: () => void;
  sentinelRef: MutableRefObject<HTMLDivElement | null>;
  onCardClick: (id: number) => void;
  risks: Record<string, string[]>;
  sentiments: Record<string, string>;
  relevances: Record<string, string>;
  formatDuration: (ms: number) => string;
  normalizePlatform: (k: string) => string;
}) {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">舆情监控结果</h2>
        </div>
        <div className="flex items-center space-x-4">
          <button onClick={onToggleSort} className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-gray-100/40 dark:bg-gray-800/30 backdrop-blur-xl border border-white/20 text-gray-700 dark:text-gray-200 transition-all duration-300 hover:bg-gray-100/60 dark:hover:bg-gray-800/50" aria-label="Sort by time" title="Sort by time">
            <SortAsc className={cn("w-4 h-4 transition-transform", oldestFirst && "rotate-180")} />
            <span className="text-sm font-medium">按时间排序</span>
          </button>
          <div className="flex items-center rounded-xl bg-white/10 backdrop-blur-xl border border-white/20 p-1">
            <button className="p-2 rounded-lg text-gray-400 bg-transparent cursor-not-allowed" disabled aria-disabled>
              <Grid className="w-4 h-4" />
            </button>
            <button className="p-2 rounded-lg text-gray-400 bg-transparent cursor-not-allowed" disabled aria-disabled>
              <List className="w-4 h-4" />
            </button>
          </div>
          <button className="p-2 rounded-xl bg-gray-100/40 dark:bg-gray-800/30 backdrop-blur-xl border border-white/20 text-gray-400 cursor-not-allowed" disabled aria-disabled title="Not implemented yet">
            <MoreHorizontal className="w-5 h-5 text-gray-600 dark:text-gray-300" />
          </button>
        </div>
      </div>

      <div className={cn("grid gap-6 transition-all duration-500 grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4")}> 
        {loading && Array.from({ length: 8 }).map((_, i) => <DashboardCardSkeleton key={i} />)}
        {!loading && posts.length === 0 && !loadingMore && (
          <div className="col-span-full flex items-center justify-center text-gray-500 dark:text-gray-400 py-16">暂无内容</div>
        )}
        {!loading && posts.map((p) => (
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
            platformLabel={normalizePlatform(p.platform)}
            riskTags={risks[p.platform_item_id] || []}
            sentiment={sentiments[p.platform_item_id]}
            brandRelevance={relevances[p.platform_item_id]}
            publishDate={(p.published_at || p.created_at).slice(0, 10)}
            originalUrl={p.original_url || undefined}
            isMarked={Boolean(p.is_marked)}
            onClick={() => onCardClick(p.id)}
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


