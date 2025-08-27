import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, Share2, Bookmark, Download, Shield } from "lucide-react";
import VideoPlayerCard from "@/polymet/components/video-player-card";
import AnalysisSection from "@/polymet/components/analysis-section";
import { BarChart3, Clock } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import PlatformBadge from "@/polymet/components/platform-badge";
import { normalizeCoverUrl } from "@/lib/media";
import { DetailMainSkeleton, DetailSidebarSkeleton } from "@/polymet/components/loading-skeletons";
import { useNavigate, useParams } from "react-router-dom";
import { supabase } from "@/lib/supabase";

type PostRow = {
  id: number;
  platform: string;
  platform_item_id: string;
  title: string;
  cover_url: string | null;
  original_url: string | null;
  video_url?: string | null;
  author_name: string | null;
  like_count: number;
  comment_count: number;
  share_count: number;
  play_count: number;
  duration_ms: number;
  post_type?: string | null;
  published_at: string | null;
  created_at: string;
};

type AnalysisRow = {
  summary?: string;
  sentiment?: string;
  brand?: string;
  key_points?: unknown[];
  risk_types?: string[];
  timeline?: { events?: unknown[] } | unknown[] | null;
};

export default function VideoAnalysisDetail() {
  const navigate = useNavigate();
  const { id } = useParams();
  const [post, setPost] = useState<PostRow | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisRow | null>(null);

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      try {
        if (!supabase || !id) return;
        const { data: postRows } = await supabase
          .from("gg_platform_post")
          .select(
            "id, platform, platform_item_id, title, cover_url, original_url, author_name, like_count, comment_count, share_count, play_count, duration_ms, post_type, published_at, created_at"
          )
          .eq("platform_item_id", id)
          .limit(1);
        if (!postRows || !postRows[0]) return;
        const p = postRows[0] as unknown as PostRow;
        const { data: aRows } = await supabase
          .from("gg_video_analysis")
          .select("summary, sentiment, brand, key_points, risk_types, timeline")
          .eq("platform_item_id", id)
          .order("id", { ascending: false })
          .limit(1);
        const a = (aRows && (aRows[0] as AnalysisRow)) || null;
        if (!cancelled) {
          setPost(p);
          setAnalysis(a);
        }
      } catch (error) {
        console.error("Failed to load analysis detail", error);
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [id]);

  const formatDuration = (ms: number) => {
    const total = Math.max(0, Math.round((ms || 0) / 1000));
    const m = Math.floor(total / 60)
      .toString()
      .padStart(1, "0");
    const s = (total % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  };

  const typeBadge = (postType?: string | null) => {
    const key = String(postType || "video").toLowerCase();
    const label = key === "image" || key === "images" || key === "graphic" || key === "note" ? "图文" : "视频";
    const color = label === "视频" ? "bg-blue-500" : "bg-emerald-500";
    return (
      <span className={`px-3 py-1 rounded-full ${color} text-white text-sm font-medium`}>{label}</span>
    );
  };

  const keyPointItems = useMemo(() => {
    const arr = (analysis?.key_points as unknown[]) || [];
    return arr.map((kp, idx) => {
      const str = String(kp);
      const parts = str.split(/[:：]/);
      const title = parts[0] || "要点";
      const description = parts.slice(1).join(":").trim() || str;
      return { id: String(idx + 1), type: "trend" as const, title, description };
    });
  }, [analysis?.key_points]);

  const timelineItems = useMemo(() => {
    const raw = (analysis as { timeline?: { events?: unknown[] } | unknown[] | null } | null)?.timeline;
    const list = (raw && ((raw as { events?: unknown[] }).events || raw)) || [];
    if (!Array.isArray(list)) return [] as { id: string; type: "trend" | "alert"; title: string; description: string; severity?: "low" | "medium" | "high"; riskBadges?: string[] }[];
    return (list as Record<string, unknown>[]).map((t, i: number) => {
      const severityNum = (t?.severity as number | undefined) || undefined;
      const riskTypes = Array.isArray(t?.risk_type)
        ? (t.risk_type as string[])
        : (typeof t?.risk_type === "string" && t.risk_type
            ? [t.risk_type]
            : []);

      // Evidence exists but currently unused in UI; keep for future extension

      const lines: string[] = [];
      if (t?.issue) lines.push(`问题概述：${t.issue}`);
      if (t?.audio_transcript) lines.push(`音频/字幕：${t.audio_transcript}`);
      if (t?.scene_description) lines.push(`场景详述：${t.scene_description}`);

   

     

      return {
        id: String(i + 1),
        type: severityNum && severityNum >= 4 ? ("alert" as const) : ("trend" as const),
        title: `${t?.timestamp || ""}${severityNum ? ` - 风险等级：${severityNum}` : ""}`,
        description: lines.join("\n"),
        severity: severityNum
          ? severityNum >= 4
            ? ("high" as const)
            : ("medium" as const)
          : undefined,
        riskBadges: riskTypes,
      };
    });
  }, [analysis]);

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <button
            className="p-3 rounded-xl bg-white/10 backdrop-blur-xl border border-white/20 hover:bg-white/20 transition-all duration-300 shadow-lg hover:shadow-xl"
            onClick={() => navigate(-1)}
            aria-label="Go back"
          >
            <ArrowLeft className="w-5 h-5 text-gray-700 dark:text-gray-300" />
          </button>
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">舆情详情分析</h1>
            <p className="text-gray-600 dark:text-gray-400">
              基于AI的深度舆情内容分析
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <button className="p-3 rounded-xl bg-white/10 backdrop-blur-xl border border-white/20 hover:bg-white/20 transition-all duration-300 shadow-lg hover:shadow-xl">
            <Share2 className="w-5 h-5 text-gray-700 dark:text-gray-300" />
          </button>
          <button className="p-3 rounded-xl bg-white/10 backdrop-blur-xl border border-white/20 hover:bg-white/20 transition-all duration-300 shadow-lg hover:shadow-xl">
            <Bookmark className="w-5 h-5 text-gray-700 dark:text-gray-300" />
          </button>
          <button className="p-3 rounded-xl bg-white/10 backdrop-blur-xl border border-white/20 hover:bg-white/20 transition-all duration-300 shadow-lg hover:shadow-xl">
            <Download className="w-5 h-5 text-gray-700 dark:text-gray-300" />
          </button>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Video Player - Smaller size */}
        <div className="">
          {post ? (
            <VideoPlayerCard
              title={post.title}
              description={analysis?.summary || ""}
              thumbnail={normalizeCoverUrl(post.cover_url)}
              duration={formatDuration(post.duration_ms)}
              views={post.play_count || 0}
              likes={post.like_count || 0}
              comments={post.comment_count || 0}
              shares={post.share_count || 0}
              timestamp={(post.published_at || post.created_at).slice(0, 19).replace("T", " ")}
              author={post.author_name || ""}
              originalUrl={post.original_url || undefined}
              videoUrl={post.video_url || undefined}
              className="h-fit"
            />
          ) : (
            <DetailMainSkeleton />
          )}
        </div>

        {/* Quick Stats */}
        <div className="space-y-6">
          {post ? (
          <div className="p-6 rounded-2xl bg-white/10 backdrop-blur-xl border border-white/20 shadow-xl">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">
              内容概览
            </h3>

            {/* Key Risk Badges */}
            <div className="flex flex-wrap gap-2 mb-4">
              {(analysis?.risk_types || []).map((rt, i) => (
                <Badge
                  key={i}
                  variant={"secondary"}
                  className="px-3 py-1 text-xs font-medium bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400 border border-orange-200 dark:border-orange-800 rounded-full flex items-center gap-1"
                >
                  <Shield className="w-3 h-3" />
                  {rt}
                </Badge>
              ))}
            </div>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-gray-600 dark:text-gray-400">舆情状态</span>
                <span className={
                  analysis?.sentiment === "negative"
                    ? "px-3 py-1 rounded-full bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 text-sm font-medium"
                    : analysis?.sentiment === "positive"
                    ? "px-3 py-1 rounded-full bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 text-sm font-medium"
                    : "px-3 py-1 rounded-full bg-gray-200 dark:bg-gray-800 text-gray-700 dark:text-gray-300 text-sm font-medium"
                }>
                  {analysis?.sentiment === "negative" ? "负面" : analysis?.sentiment === "positive" ? "正向" : "中立"}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-600 dark:text-gray-400">
                  内容类型
                </span>
                {typeBadge(post?.post_type)}
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-600 dark:text-gray-400">
                  发布平台
                </span>
                <PlatformBadge platform={post?.platform || ""} size="md" variant="panel" />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-600 dark:text-gray-400">
                  分析状态
                </span>
                {analysis ? (
                  <span className="px-3 py-1 rounded-full bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 text-sm font-medium">已完成</span>
                ) : (
                  <span className="px-3 py-1 rounded-full bg-gray-200 dark:bg-gray-800 text-gray-700 dark:text-gray-300 text-sm font-medium">待分析</span>
                )}
              </div>
            </div>
          </div>
          ) : (
            <DetailSidebarSkeleton />
          )}

          {/* Sentiment Analysis Summary */}
          <AnalysisSection
            title="舆情分析总结"
            icon={
              <BarChart3 className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            }
            items={keyPointItems}
          />
        </div>
      </div>

      {/* Timeline Analysis - Full Width */}
      <AnalysisSection
        title="时间轴分析"
        icon={
          <Clock className="w-5 h-5 text-purple-600 dark:text-purple-400" />
        }
        items={timelineItems}
        className="w-full"
      />
    </div>
  );
}
