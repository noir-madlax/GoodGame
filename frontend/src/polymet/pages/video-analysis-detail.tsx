import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, Share2, Bookmark, Download, Shield } from "lucide-react";
import { Tooltip, TooltipProvider, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import VideoPlayerCard from "@/polymet/components/video-player-card";
import AnalysisSection from "@/polymet/components/analysis-section";
import { BarChart3, Clock, MessageCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import PlatformBadge from "@/polymet/components/platform-badge";
import { normalizeCoverUrl } from "@/lib/media";
import { DetailMainSkeleton, DetailSidebarSkeleton, SectionSkeleton } from "@/polymet/components/loading-skeletons";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { supabase } from "@/lib/supabase";
import SourcePanel from "@/polymet/components/source-panel";
import TimelineAnalysis, { TimelineItem as TLItem } from "@/polymet/components/timeline-analysis";
import CommentsAnalysis, { CommentAnalysisItem } from "@/polymet/components/comments-analysis";

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
  is_marked?: boolean;
  process_status?: string | null;
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
  const [analysisLoading, setAnalysisLoading] = useState<boolean>(false);
  const [commentsJson, setCommentsJson] = useState<CommentsJson | null>(null);
  const [transcriptJson, setTranscriptJson] = useState<TranscriptJson | null>(null);
  const [commentsLoading, setCommentsLoading] = useState<boolean>(false);
  const [transcriptLoading, setTranscriptLoading] = useState<boolean>(false);
  const [panelOpen, setPanelOpen] = useState(false);
  const [activeBottomTab, setActiveBottomTab] = useState<"timeline" | "comments">("timeline");
  // 标记提示文案与淡出效果（2 秒自动消失）
  const [markTip, setMarkTip] = useState<string | null>(null);
  const [markTipFading, setMarkTipFading] = useState<boolean>(false);
  // 处理建议（本地持久化，用于“内容标记和处理”页展示）
  const handleGenerateAdvice = () => {
    try {
      const payload = {
        id,
        title: post?.title || "",
        platform: post?.platform || "",
        platform_item_id: post?.platform_item_id || id,
        summary: analysis?.summary || "",
        sentiment: analysis?.sentiment || "",
        risk_types: analysis?.risk_types || [],
        created_at: new Date().toISOString(),
      };
      const key = "gg_action_advices";
      const arr = JSON.parse(localStorage.getItem(key) || "[]");
      arr.unshift(payload);
      localStorage.setItem(key, JSON.stringify(arr.slice(0, 200)));
      // 同步数据库：置为处理中
      if (id && supabase) {
        void supabase
          .from("gg_platform_post")
          .update({ process_status: "处理中" })
          .eq("platform_item_id", id);
      }
      // 不弹窗
    } catch (e) {
      console.error(e);
    }
  };

  const handleMarkContent = async () => {
    const currentlyMarked = Boolean(post?.is_marked);
    const nextMarked = !currentlyMarked;
    if (!id || !supabase) return;
    // 乐观更新：立即反馈
    setPost((prev) => (prev ? { ...prev, is_marked: nextMarked, process_status: nextMarked ? "已标记" : null } : prev));
    setMarkTip(nextMarked ? "已标记" : "已取消标记");
    try {
      const { error } = await supabase
        .from("gg_platform_post")
        .update(nextMarked ? { is_marked: true, process_status: "已标记" } : { is_marked: false, process_status: null })
        .eq("platform_item_id", id);
      if (error) {
        // 回滚本地
        setPost((prev) => (prev ? { ...prev, is_marked: currentlyMarked, process_status: currentlyMarked ? "已标记" : null } : prev));
        setMarkTip("操作失败，请重试");
        console.error("toggle mark error", error);
      }
    } catch (e) {
      setPost((prev) => (prev ? { ...prev, is_marked: currentlyMarked, process_status: currentlyMarked ? "已标记" : null } : prev));
      setMarkTip("操作失败，请重试");
      console.error(e);
    }
  };

  // 页面加载时不触发提示；提示仅在点击时展示

  // 提示 2 秒自动消失
  useEffect(() => {
    if (!markTip) return;
    setMarkTipFading(false);
    const t1 = setTimeout(() => setMarkTipFading(true), 1500); // 1.5s 后开始淡出
    const t2 = setTimeout(() => setMarkTip(null), 2000); // 2s 后移除
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, [markTip]);
  // 本地锚点状态：避免仅依赖 URL 导致不刷新
  const [anchorCommentPathState, setAnchorCommentPathState] = useState<string | null>(null);
  const [anchorSegStartState, setAnchorSegStartState] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      try {
        if (!supabase || !id) return;
        setAnalysisLoading(true);
        const { data: postRows } = await supabase
          .from("gg_platform_post")
          .select(
            "id, platform, platform_item_id, title, cover_url, original_url, author_name, like_count, comment_count, share_count, play_count, duration_ms, post_type, published_at, created_at, is_marked, process_status"
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
      } finally {
        if (!cancelled) setAnalysisLoading(false);
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

  // 渲染平台 SVG 图标（与首页一致），目前支持：抖音/小红书
  const renderPlatformLogo = (keyRaw?: string) => {
    const key = String(keyRaw || "").toLowerCase();
    if (key.includes("douyin")) {
      return <img src="/douyin.svg" alt="抖音" className="w-5 h-5" />;
    }
    if (key.includes("xiaohongshu") || key.includes("xhs")) {
      return <img src="/xiaohongshu.svg" alt="小红书" className="w-5 h-5" />;
    }
    return null;
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

  // 转换为 TimelineAnalysis 组件所需的数据结构
  const timelineViewData: TLItem[] = useMemo(() => {
    // 仅展示来源为 video 的事件
    const rawTimeline = (analysis as { timeline?: { events?: unknown[] } | unknown[] | null } | null)?.timeline;
    const arrRaw = (rawTimeline && (((rawTimeline as { events?: unknown[] }).events) || rawTimeline)) || [];
    const events = Array.isArray(arrRaw) ? (arrRaw as Record<string, unknown>[]) : [];
    const videoIdxs: number[] = [];
    events.forEach((e, i) => {
      const src = (e as { source?: string }).source;
      if (src === "video" || src === undefined || src === null) videoIdxs.push(i);
    });
    return timelineItems.filter((_, i) => videoIdxs.includes(i)).map((t) => {
      const overview = String(t.description || "").split("\n").find((l) => l.startsWith("问题概述："))?.replace(/^问题概述：/, "") || "";
      const audio = String(t.description || "").split("\n").find((l) => l.startsWith("音频/字幕："))?.replace(/^音频\/字幕：/, "") || "";
      const scene = String(t.description || "").split("\n").find((l) => l.startsWith("场景详述："))?.replace(/^场景详述：/, "") || "";
      return {
        id: t.id,
        timestamp: (t._ts || "").match(/\d{2}:\d{2}/)?.[0] || String(t._ts || ""),
        riskBadges: t.riskBadges || [],
        snippet: t._snippet || "",
        videoData: { overview, audio, scene },
      } as TLItem;
    });
  }, [timelineItems, analysis]);

  // 评论分析：按现有原始评论构建占位（无逐评论分析结构时）
  const commentAnalysisData: CommentAnalysisItem[] = useMemo(() => {
    const rawTimeline = (analysis as { timeline?: { events?: unknown[] } | unknown[] | null } | null)?.timeline;
    const arrRaw = (rawTimeline && (((rawTimeline as { events?: unknown[] }).events) || rawTimeline)) || [];
    const events = Array.isArray(arrRaw) ? (arrRaw as Record<string, unknown>[]) : [];
    const commentEvents = events.filter((e) => {
      const src = (e as { source?: string }).source;
      return src === "comment" || src === "comments";
    });
    return commentEvents.map((e, idx) => {
      const riskRaw = (e as { risk_type?: unknown }).risk_type as unknown;
      const riskBadges = Array.isArray(riskRaw)
        ? (riskRaw as unknown[]).map((x) => String(x))
        : (typeof riskRaw === "string" && riskRaw ? [String(riskRaw as string)] : []);
      return {
        id: String(idx + 1),
        riskBadges,
        commentData: {
          id: String((e as { comment_id?: unknown }).comment_id || `c-${idx + 1}`),
          author: String((e as { comment_author?: unknown }).comment_author || "用户"),
          overview: String((e as { issue?: unknown; comment_text?: unknown }).issue || (e as { comment_text?: unknown }).comment_text || ""),
          audio: String((e as { audio_transcript?: unknown }).audio_transcript || ""),
          scene: String((e as { scene_description?: unknown }).scene_description || ""),
        },
        snippet: String((e as { comment_text?: unknown }).comment_text || ""),
      } as CommentAnalysisItem;
    });
  }, [analysis]);

  // 点击“查看原始内容”触发的打开与锚点定位
  const handleViewSourceFromTimeline = (item: TLItem) => {
    const start = String(item.timestamp || "").match(/\d{2}:\d{2}/)?.[0] || null;
    const snippet = item.snippet || "";
    const commentPath = findCommentPathBySnippet(commentsJson, snippet);
    setPanelOpen(true);
    if (start) {
      setAnchorSegStartState(start);
      setAnchorCommentPathState(null);
      const sp = new URLSearchParams(searchParams);
      sp.set("seg_start", start);
      setSearchParams(sp, { replace: true });
      setActiveBottomTab("timeline");
      return;
    }
    if (commentPath) {
      setAnchorCommentPathState(commentPath);
      setAnchorSegStartState(null);
      const sp = new URLSearchParams(searchParams);
      sp.set("comment_path", commentPath);
      setSearchParams(sp, { replace: true });
      setActiveBottomTab("timeline");
    }
  };

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
            onClick={() => navigate("/dashboard")}
            aria-label="Go back"
          >
            <ArrowLeft className="w-5 h-5 text-gray-700 dark:text-gray-300" />
          </button>
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">内容分析详情</h1>
           
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <div className="relative flex items-center space-x-3">
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button className="p-3 rounded-xl bg-white/10 backdrop-blur-xl border border-white/20 hover:bg-white/20 transition-all duration-300 shadow-lg hover:shadow-xl">
                    <Share2 className="w-5 h-5 text-gray-700 dark:text-gray-300" />
                  </button>
                </TooltipTrigger>
                <TooltipContent>转发分析结果</TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    onClick={handleMarkContent}
                    className={cn(
                      "p-3 rounded-xl backdrop-blur-xl border transition-all duration-300 shadow-lg hover:shadow-xl",
                      post?.is_marked
                        ? "bg-yellow-50/60 border-yellow-400 hover:bg-yellow-100"
                        : "bg-white/10 border-white/20 hover:bg-white/20"
                    )}
                    aria-label="标记内容"
                  >
                    <Bookmark className={cn("w-5 h-5", post?.is_marked ? "text-yellow-500" : "text-gray-700 dark:text-gray-300")} />
                  </button>
                </TooltipTrigger>
                <TooltipContent>{post?.is_marked ? "取消标记" : "标记内容"}</TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button className="p-3 rounded-xl bg-white/10 backdrop-blur-xl border border-white/20 hover:bg-white/20 transition-all duration-300 shadow-lg hover:shadow-xl">
                    <Download className="w-5 h-5 text-gray-700 dark:text-gray-300" />
                  </button>
                </TooltipTrigger>
                <TooltipContent>下载内容</TooltipContent>
              </Tooltip>
            </TooltipProvider>
            {markTip && (
              <div
                className={cn(
                  // 位置：略微左移、上移，且不挡交互
                  "pointer-events-none absolute left-[44%] -translate-x-1/2 top-[48px]",
                  // 文案：弱化灰色并带轻微透明度
                  "text-xs px-1 py-0.5 whitespace-nowrap text-gray-500/80",
                  // 动画：渐隐
                  "transition-opacity duration-500",
                  markTipFading ? "opacity-0" : "opacity-100"
                )}
              >
                {markTip}
              </div>
            )}
          </div>
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
              onGenerateAdvice={handleGenerateAdvice}
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
                <span className="flex items-center ">
                  {renderPlatformLogo(post?.platform)}
                  <PlatformBadge platform={post?.platform || ""} size="md" variant="panel" />
                </span>
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
          {analysisLoading ? (
            <SectionSkeleton rows={4} />
          ) : (
            <AnalysisSection
              title="内容解析"
              icon={<BarChart3 className="w-5 h-5 text-blue-600 dark:text-blue-400" />}
              items={keyPointItems}
            />
          )}
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

      {/* 底部双 Tab：时间轴分析 / 评论分析 */}
      <div className="rounded-2xl bg-white/10 backdrop-blur-xl border border-white/20 shadow-xl">
        <div className="p-6 border-b border-white/10 flex items-center justify-between">
          <div className="flex-1">
            <div className="flex">
              <div className="flex-1">
                <div className="inline-block">
                  <div className="flex-1">
                    <div className="">
                      {/* Tabs header */}
                      <div className="">
                        <div className="inline-block">
                          <div className="">
                            {/* mimic Tabs */}
                            <div className="grid w-fit grid-cols-2 bg-white/10 backdrop-blur-xl border border-white/20 rounded-xl overflow-hidden">
                              <button
                                onClick={() => setActiveBottomTab("timeline")}
                                className={cn(
                                  "flex items-center space-x-2 px-4 py-2 text-sm font-medium",
                                  activeBottomTab === "timeline"
                                    ? "bg-white/20 text-blue-600 dark:text-blue-400"
                                    : "text-gray-700 dark:text-gray-300 hover:bg-white/10"
                                )}
                              >
                                <Clock className="w-4 h-4" />
                                <span>时间轴分析</span>
                              </button>
                              <button
                                onClick={() => setActiveBottomTab("comments")}
                                className={cn(
                                  "flex items-center space-x-2 px-4 py-2 text-sm font-medium",
                                  activeBottomTab === "comments"
                                    ? "bg-white/20 text-green-600 dark:text-green-400"
                                    : "text-gray-700 dark:text-gray-300 hover:bg-white/10"
                                )}
                              >
                                <MessageCircle className="w-4 h-4" />
                                <span>评论分析</span>
                              </button>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <button
            className="px-4 py-2 rounded-xl bg-gradient-to-r from-blue-500 to-purple-600 text-white font-medium hover:from-blue-600 hover:to-purple-700 transition-all duration-300"
            onClick={() => setPanelOpen(true)}
          >
            查看原始评论和字幕
          </button>
        </div>

        <div className="p-6">
          {activeBottomTab === "timeline" ? (
            analysisLoading ? (
              <SectionSkeleton rows={6} />
            ) : (
              <TimelineAnalysis items={timelineViewData} onViewSource={handleViewSourceFromTimeline} />
            )
          ) : (
            <CommentsAnalysis
              items={commentAnalysisData}
              onViewSource={(item) => {
                setPanelOpen(true);
                const snippet = item.snippet || item.commentData.overview || "";
                const path = findCommentPathBySnippet(commentsJson, snippet);
                if (path) {
                  setAnchorCommentPathState(path);
                  setAnchorSegStartState(null);
                  const sp = new URLSearchParams(searchParams);
                  sp.set("comment_path", path);
                  setSearchParams(sp, { replace: true });
                }
              }}
            />
          )}
        </div>
      </div>
    </div>
  );
}
