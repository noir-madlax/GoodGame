import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, Share2, Bookmark, Download, Shield } from "lucide-react";
import VideoPlayerCard from "@/polymet/components/video-player-card";
import AnalysisSection from "@/polymet/components/analysis-section";
import { BarChart3, Clock } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import PlatformBadge from "@/polymet/components/platform-badge";
import { normalizeCoverUrl } from "@/lib/media";
import { DetailMainSkeleton, DetailSidebarSkeleton } from "@/polymet/components/loading-skeletons";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { supabase } from "@/lib/supabase";
import SourcePanel from "@/polymet/components/source-panel";

// 与 SourcePanel 保持一致的最小类型（仅用于本页状态）
type CommentNode = {
  content: string;
  like_count?: number;
  reply_count?: number;
  author_name?: string | null;
  author_avatar_url?: string | null;
  published_at?: string | null;
  replies?: CommentNode[];
};
type CommentsJson = { post?: { id?: number | string; title?: string }; comments?: CommentNode[] };
type TranscriptSegment = { start: string; end?: string; text: string; speaker?: string };
type TranscriptJson = { segments?: TranscriptSegment[] };
type TimelineViewItem = { id: string; type: "trend" | "alert"; title: string; description: string; severity?: "low" | "medium" | "high"; riskBadges?: string[]; _ts?: string; _snippet?: string };

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
  brand_relevance?: string | null;
  relevance_evidence?: string | null;
};

export default function VideoAnalysisDetail() {
  const navigate = useNavigate();
  const { id } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const [post, setPost] = useState<PostRow | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisRow | null>(null);
  const [commentsJson, setCommentsJson] = useState<CommentsJson | null>(null);
  const [transcriptJson, setTranscriptJson] = useState<TranscriptJson | null>(null);
  const [commentsLoading, setCommentsLoading] = useState<boolean>(false);
  const [transcriptLoading, setTranscriptLoading] = useState<boolean>(false);
  const [panelOpen, setPanelOpen] = useState(false);
  // 本地锚点状态：避免仅依赖 URL 导致不刷新
  const [anchorCommentPathState, setAnchorCommentPathState] = useState<string | null>(null);
  const [anchorSegStartState, setAnchorSegStartState] = useState<string | null>(null);

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
          .select("summary, sentiment, brand, key_points, risk_types, timeline, brand_relevance, relevance_evidence")
          .eq("platform_item_id", id)
          .order("id", { ascending: false })
          .limit(1);
        const a = (aRows && (aRows[0] as AnalysisRow)) || null;
        if (!cancelled) {
          setPost(p);
          setAnalysis(a);
          // 初始不加载评论/字幕，按需加载
          setCommentsJson(null);
          setTranscriptJson(null);
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

  // 异步预加载：进入页面即不阻塞主信息，后台并行加载评论与字幕
  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      try {
        if (!supabase || !id) return;
        // 字幕
        if (!transcriptJson) {
          setTranscriptLoading(true);
          const { data: srcRows } = await supabase
            .from("gg_video_analysis")
            .select("transcript_json")
            .eq("platform_item_id", id)
            .order("id", { ascending: false })
            .limit(1);
          const src = (srcRows && (srcRows[0] as { transcript_json?: TranscriptJson | null })) || {};
          if (!cancelled) setTranscriptJson(src.transcript_json || null);
        }
        // 评论（仅当 post 已知）
        if (post && !commentsJson) {
          setCommentsLoading(true);
          const { data: commentRows } = await supabase
            .from("gg_platform_post_comments")
            .select("id, parent_comment_id, content, like_count, reply_count, author_name, author_avatar_url, published_at")
            .eq("post_id", post.id)
            .order("published_at", { ascending: true, nullsFirst: true })
            .order("id", { ascending: true });

          let commentsFromRaw: CommentsJson | null = null;
          if (Array.isArray(commentRows) && commentRows.length > 0) {
            type Row = { id: number; parent_comment_id: number | null; content: string; like_count: number; reply_count: number; author_name?: string | null; author_avatar_url?: string | null; published_at?: string | null };
            const nodeById = new Map<number, CommentNode & { _id: number; _parent?: number | null }>();
            const roots: (CommentNode & { _id: number })[] = [];
            (commentRows as Row[]).forEach((r) => {
              nodeById.set(r.id, {
                _id: r.id,
                content: r.content || "",
                like_count: r.like_count || 0,
                reply_count: r.reply_count || 0,
                author_name: r.author_name ?? null,
                author_avatar_url: r.author_avatar_url ?? null,
                published_at: r.published_at ?? null,
                replies: [],
                _parent: r.parent_comment_id ?? null,
              });
            });
            nodeById.forEach((node) => {
              if (node._parent) {
                const parent = nodeById.get(node._parent);
                if (parent) (parent.replies = parent.replies || []).push(node);
              } else {
                roots.push(node);
              }
            });
            const strip = (n: CommentNode & { _id: number }): CommentNode => ({
              content: n.content,
              like_count: n.like_count,
              reply_count: n.reply_count,
              author_name: n.author_name,
              author_avatar_url: n.author_avatar_url,
              published_at: n.published_at,
              replies: (n.replies || []).map((c) => strip(c as CommentNode & { _id: number })),
            });
            commentsFromRaw = { comments: roots.map((r) => strip(r)) };
          }
          if (!cancelled) setCommentsJson(commentsFromRaw);
        }
      } catch (error) {
        console.error("Failed to load panel sources", error);
      } finally {
        if (!cancelled) {
          setTranscriptLoading(false);
          setCommentsLoading(false);
        }
      }
    };
    run();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, post]);

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

  const timelineItems: TimelineViewItem[] = useMemo(() => {
    const raw = (analysis as { timeline?: { events?: unknown[] } | unknown[] | null } | null)?.timeline;
    const list = (raw && ((raw as { events?: unknown[] }).events || raw)) || [];
    if (!Array.isArray(list)) return [] as TimelineViewItem[];
    return (list as Record<string, unknown>[]).map((t, i: number) => {
      const severityNum = (t?.severity as number | undefined) || undefined;
      const rawRisk = (t as { risk_type?: unknown }).risk_type;
      const riskTypes: string[] = Array.isArray(rawRisk)
        ? (rawRisk as unknown[]).map((x) => String(x))
        : (typeof rawRisk === "string" && rawRisk ? [String(rawRisk)] : []);

      // Evidence exists but currently unused in UI; keep for future extension

      const lines: string[] = [];
      if ((t as { issue?: string }).issue) lines.push(`问题概述：${(t as { issue?: string }).issue}`);
      if ((t as { audio_transcript?: string }).audio_transcript) lines.push(`音频/字幕：${(t as { audio_transcript?: string }).audio_transcript}`);
      if ((t as { scene_description?: string }).scene_description) lines.push(`场景详述：${(t as { scene_description?: string }).scene_description}`);

   

     

      return {
        id: String(i + 1),
        type: severityNum && severityNum >= 4 ? ("alert" as const) : ("trend" as const),
        title: `${(t as { timestamp?: string }).timestamp || ""}${severityNum ? ` - 风险等级：${severityNum}` : ""}`,
        description: lines.join("\n"),
        severity: severityNum
          ? severityNum >= 4
            ? ("high" as const)
            : ("medium" as const)
          : undefined,
        riskBadges: riskTypes,
        _ts: String((t as { timestamp?: string }).timestamp || ""),
        _snippet: (t as { audio_transcript?: string; comment_text?: string }).audio_transcript || (t as { comment_text?: string }).comment_text || "",
      };
    });
  }, [analysis]);

  // 在 comments 树中根据片段文本查找路径，如 "12-0-1"
  const findCommentPathBySnippet = (root: CommentsJson | null, snippetRaw: string): string | null => {
    if (!root || !root.comments || !snippetRaw) return null;
    const snippet = snippetRaw.trim();
    if (!snippet || snippet.length < 4) return null;
    let hit: Array<number> | null = null;
    const dfs = (nodes: CommentNode[], path: number[]) => {
      for (let i = 0; i < nodes.length; i++) {
        const n = nodes[i];
        if (String(n.content || "").includes(snippet)) {
          hit = [...path, i];
          return true;
        }
        const children = n.replies || [];
        if (children.length > 0) {
          if (dfs(children, [...path, i])) return true;
        }
      }
      return false;
    };
    dfs(root.comments, []);
    return Array.isArray(hit) ? (hit as number[]).map((n) => String(n)).join("-") : null;
  };

  // 读取锚点参数
  const anchorCommentPath = searchParams.get("comment_path");
  const anchorSegIndexRaw = searchParams.get("seg_index");
  const anchorSegIndex = anchorSegIndexRaw ? parseInt(anchorSegIndexRaw, 10) : null;
  const anchorSegStart = searchParams.get("seg_start");

  // 初始化本地状态（仅在首渲染时同步一次）
  useEffect(() => {
    if (anchorCommentPath && !anchorCommentPathState) setAnchorCommentPathState(anchorCommentPath);
    if (anchorSegStart && !anchorSegStartState) setAnchorSegStartState(anchorSegStart);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
              brandRelevance={analysis?.brand_relevance || undefined}
              relevanceEvidence={analysis?.relevance_evidence || undefined}
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
            title="内容解析"
            icon={
              <BarChart3 className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            }
            items={keyPointItems}
          />
        </div>
      </div>

      {/* 溯源 Panel */}
      <SourcePanel
        open={panelOpen}
        onOpenChange={setPanelOpen}
        commentsJson={commentsJson}
        transcriptJson={transcriptJson}
        commentsLoading={commentsLoading}
        transcriptLoading={transcriptLoading}
        anchorCommentPath={anchorCommentPathState || anchorCommentPath}
        anchorSegmentIndex={Number.isFinite(anchorSegIndex as number) ? (anchorSegIndex as number) : null}
        anchorSegmentStart={anchorSegStartState || anchorSegStart}
        defaultTab="comments"
      />

      {/* Timeline Analysis - Full Width */}
      <AnalysisSection
        title="时间轴分析"
        icon={<Clock className="w-5 h-5 text-purple-600 dark:text-purple-400" />}
        items={timelineItems}
        className="w-full"
        headerRight={(
          <button
            className="px-4 py-2 rounded-xl bg-gradient-to-r from-blue-500 to-purple-600 text-white text-sm font-medium hover:from-blue-600 hover:to-purple-700 transition-all duration-300 hover:scale-105 shadow-lg"
            onClick={() => setPanelOpen(true)}
          >
            查看原始评论与字幕
          </button>
        )}
        renderItemAction={(idx) => (
          <button
            className="px-2 py-1 rounded-lg text-xs bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20 hover:bg-blue-500/20 transition"
            onClick={(e) => {
              e.stopPropagation();
              // 从 _ts 中提取 mm:ss
              const raw = (timelineItems[idx] as TimelineViewItem)?._ts || "";
              const mmssMatch = String(raw).match(/(\d{2}:\d{2})/);
              const start = mmssMatch ? mmssMatch[1] : null;
              // 若是评论型事件，尝试用片段匹配评论树，得到 comment_path
              const snippet = (timelineItems[idx] as TimelineViewItem)?._snippet || "";
              const commentPath = findCommentPathBySnippet(commentsJson, snippet);
              setPanelOpen(true);
              if (start) {
                setAnchorSegStartState(start);
                setAnchorCommentPathState(null);
                const sp = new URLSearchParams(searchParams);
                sp.set("seg_start", start);
                setSearchParams(sp, { replace: true });
              } else if (commentPath) {
                setAnchorCommentPathState(commentPath);
                setAnchorSegStartState(null);
                const sp = new URLSearchParams(searchParams);
                sp.set("comment_path", commentPath);
                setSearchParams(sp, { replace: true });
              }
            }}
            title="查看原文"
            aria-label="查看原文"
          >
            查看原文
          </button>
        )}
        onItemClick={(idx) => {
          // 点击整行也触发：优先解析 _ts
          const raw = (timelineItems[idx] as TimelineViewItem)?._ts || "";
          const mmssMatch = String(raw).match(/(\d{2}:\d{2})/);
          const start = mmssMatch ? mmssMatch[1] : null;
          const snippet = (timelineItems[idx] as TimelineViewItem)?._snippet || "";
          const commentPath = findCommentPathBySnippet(commentsJson, snippet);
          setPanelOpen(true);
          if (start) {
            setAnchorSegStartState(start);
            setAnchorCommentPathState(null);
            const sp = new URLSearchParams(searchParams);
            sp.set("seg_start", start);
            setSearchParams(sp, { replace: true });
          } else if (commentPath) {
            setAnchorCommentPathState(commentPath);
            setAnchorSegStartState(null);
            const sp = new URLSearchParams(searchParams);
            sp.set("comment_path", commentPath);
            setSearchParams(sp, { replace: true });
          }
        }}
      />
    </div>
  );
}
