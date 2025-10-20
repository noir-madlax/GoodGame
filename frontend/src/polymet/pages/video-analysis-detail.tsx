import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, Share2, Bookmark, Download, Shield, RotateCcw } from "lucide-react";
import { Tooltip, TooltipProvider, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import VideoPlayerCard from "@/polymet/components/video-player-card";
import AnalysisSection from "@/polymet/components/analysis-section";
import { BarChart3, Clock, MessageCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import PlatformBadge from "@/polymet/components/platform-badge";
import { normalizeCoverUrl } from "@/lib/media";
import { DetailMainSkeleton, DetailSidebarSkeleton, SectionSkeleton } from "@/polymet/components/loading-skeletons";
import { useNavigate, useParams, useSearchParams, useLocation } from "react-router-dom";
import { supabase } from "@/lib/supabase";
import SourcePanel from "@/polymet/components/source-panel";
import TimelineAnalysis, { TimelineItem as TLItem } from "@/polymet/components/timeline-analysis";
import PictureAnalysis, { PictureItem as PicItem } from "@/polymet/components/picture-analysis";
import CommentsAnalysis, { CommentAnalysisItem } from "@/polymet/components/comments-analysis";
import HandlingSuggestionsPanel from "@/polymet/components/handling-suggestions-panel";
import type { AuthorTooltipData } from "@/polymet/components/author-tooltip";
import { markDashboardCacheDirty, isDashboardCacheDirty } from "@/polymet/lib/dashboard-cache";

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
  author_id?: string | null;
  title: string;
  cover_url: string | null;
  original_url: string | null;
  video_url?: string[] | string | null;  // 支持列表（新格式）或单个字符串（旧格式）
  author_name: string | null;
  author_follower_count?: number | null;
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
  // 新增：后端 analysis_status，用于准确展示分析状态
  analysis_status?: string | null;
  relevant_status?: string | null;
  // 初筛详细结果(JSON/字符串)，用于在未分析也为不相关时展示原因
  relevant_result?: unknown | null;
};

type AuthorProfile = {
  nickname?: string | null;
  avatar_url?: string | null;
  share_url?: string | null;
  follower_count?: number | null;
  signature?: string | null;
  location?: string | null;
  account_cert_info?: string | null;
  verification_type?: number | null;
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
  total_risk?: string | null;
  total_risk_reason?: string | null;
};

export default function VideoAnalysisDetail() {
  const navigate = useNavigate();
  const location = useLocation();
  const { id } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const [post, setPost] = useState<PostRow | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisRow | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState<boolean>(false);
  const [commentsJson, setCommentsJson] = useState<CommentsJson | null>(null);
  const [transcriptJson, setTranscriptJson] = useState<TranscriptJson | null>(null);
  const [pictureContent, setPictureContent] = useState<string | null>(null);
  const [pictureCoverUrl, setPictureCoverUrl] = useState<string | null>(null);
  const [commentsLoading, setCommentsLoading] = useState<boolean>(false);
  const [transcriptLoading, setTranscriptLoading] = useState<boolean>(false);
  const [panelOpen, setPanelOpen] = useState(false);
  const [isInfluencer, setIsInfluencer] = useState<boolean>(false);
  const [activeBottomTab, setActiveBottomTab] = useState<"timeline" | "comments">("timeline");
  // 标记提示文案与淡出效果（2 秒自动消失）
  const [markTip, setMarkTip] = useState<string | null>(null);
  const [markTipFading, setMarkTipFading] = useState<boolean>(false);
  // 处理建议面板开关
  const [suggestionsOpen, setSuggestionsOpen] = useState<boolean>(false);
  const [authorProfile, setAuthorProfile] = useState<AuthorProfile | null>(null);
  // 失败态重试：将 analysis_status 改回 pending
  const handleRetryAnalysis = async () => {
    try {
      if (!post?.id || !supabase) return;
      const pid = post.id;
      // 立即本地更新为 pending（分析中）
      setPost((prev) => (prev ? { ...prev, analysis_status: "pending" } : prev));
      const { error } = await supabase
        .from("gg_platform_post")
        .update({ analysis_status: "pending" })
        .eq("id", pid);
      if (error) {
        // 回滚：若失败，恢复原状态
        setPost((prev) => (prev ? { ...prev, analysis_status: post.analysis_status } : prev));
        console.error("retry analysis error", error);
      } else {
        markDashboardCacheDirty();
      }
    } catch (e) {
      // 回滚：异常时恢复原状态
      setPost((prev) => (prev ? { ...prev, analysis_status: post?.analysis_status } : prev));
      console.error(e);
    }
  };
  // 查看处理建议（只读跳转，不做写入）
  const handleViewAdvice = () => {
    if (!post?.id) return;
    markDashboardCacheDirty();
    navigate(`/suggestions/${post.id}`);
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
        .eq("id", id);
      if (error) {
        // 回滚本地
        setPost((prev) => (prev ? { ...prev, is_marked: currentlyMarked, process_status: currentlyMarked ? "已标记" : null } : prev));
        setMarkTip("操作失败，请重试");
        console.error("toggle mark error", error);
      } else {
        markDashboardCacheDirty();
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
            // 增加 analysis_status 字段以驱动前端状态展示
            "id, platform, platform_item_id, author_id, title, cover_url, original_url, author_name, author_follower_count, like_count, comment_count, share_count, play_count, duration_ms, post_type, published_at, created_at, is_marked, process_status, content, analysis_status, relevant_status, relevant_result"
          )
          .eq("id", id)
          .limit(1);
        if (!postRows || !postRows[0]) return;
        const p = postRows[0] as unknown as PostRow;
        // 计算达人：先看帖子粉丝数，再看 gg_authors
        let infl = Number(p.author_follower_count || 0) >= 100000;
        if (!infl && p.author_id) {
          const { data: aRows } = await supabase
            .from("gg_authors")
            .select("follower_count")
            .eq("platform_author_id", p.author_id)
            .limit(1);
          const fc = Array.isArray(aRows) && aRows[0] ? Number((aRows[0] as { follower_count?: number }).follower_count || 0) : 0;
          if (fc >= 100000) infl = true;
        }
        // 加载作者资料用于 Tooltip 展示
        let profile: AuthorProfile | null = null;
        if (p.author_id) {
          const { data: profRows } = await supabase
            .from("gg_authors")
            .select("nickname, avatar_url, share_url, follower_count, signature, location, account_cert_info, verification_type")
            .eq("platform_author_id", p.author_id)
            .limit(1);
          profile = (profRows && (profRows[0] as AuthorProfile)) || null;
        }
        const { data: aRows } = await supabase
          .from("gg_video_analysis")
          .select("summary, sentiment, brand, key_points, risk_types, timeline, brand_relevance, relevance_evidence, total_risk, total_risk_reason")
          .eq("platform_item_id", p.platform_item_id)
          .order("id", { ascending: false })
          .limit(1);
        const a = (aRows && (aRows[0] as AnalysisRow)) || null;
        if (!cancelled) {
          setPost(p);
          setAnalysis(a);
          setAuthorProfile(profile);
          setIsInfluencer(infl);
          // 初始不加载评论/字幕，按需加载
          setCommentsJson(null);
          setTranscriptJson(null);
          setPictureContent((p as any).content || null);
          setPictureCoverUrl(p.cover_url || null);
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
          const targetPlatformItemId = post?.platform_item_id || id;
          const { data: srcRows } = await supabase
            .from("gg_video_analysis")
            .select("transcript_json")
            .eq("platform_item_id", targetPlatformItemId)
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

  // 统一的分析状态映射：根据后端枚举值渲染中文标签与颜色
  const ANALYSIS_STATUS_MAP: Record<string, { label: string; className: string }> = {
    init: { label: "未开始", className: "bg-gray-200 dark:bg-gray-800 text-gray-700 dark:text-gray-300" },
    pending: { label: "分析中", className: "bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400" },
    analyzed: { label: "已完成", className: "bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400" },
    screening_failed: { label: "初筛失败", className: "bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400" },
    comments_failed: { label: "评论获取失败", className: "bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400" },
    analysis_failed: { label: "分析失败", className: "bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400" },
  };

  // 渲染分析状态：优先使用后端 analysis_status；若缺失且已有分析结果，则视为已完成；否则视为未开始
  const renderAnalysisStatus = (status?: string | null, hasAnalysis?: boolean) => {
    const key = String(status || "").toLowerCase();
    const map = ANALYSIS_STATUS_MAP[key];
    if (map) {
      return <span className={`px-3 py-1 rounded-full text-sm font-medium ${map.className}`}>{map.label}</span>;
    }
    if (hasAnalysis) {
      const ok = ANALYSIS_STATUS_MAP["analyzed"];
      return <span className={`px-3 py-1 rounded-full text-sm font-medium ${ok.className}`}>{ok.label}</span>;
    }
    const init = ANALYSIS_STATUS_MAP["init"];
    return <span className={`px-3 py-1 rounded-full text-sm font-medium ${init.className}`}>{init.label}</span>;
  };

  const isFailedStatus = (s?: string | null) => {
    const key = String(s || "").toLowerCase();
    return key === "screening_failed" || key === "comments_failed" || key === "analysis_failed";
  };

  // 相关性标签渲染：优先使用分析表 brand_relevance，其次使用帖子表 relevant_status
  const renderRelevanceBadge = (brandRel?: string | null, fallbackRel?: string | null) => {
    const raw = (brandRel ?? fallbackRel ?? "").toString().trim().toLowerCase();
    const toLabel = (v: string) => {
      if (!v) return "未标注";
      if (["相关", "relevant", "related", "yes"].includes(v)) return "相关";
      if (["疑似相关", "suspected", "suspect", "possible", "可能相关"].includes(v)) return "疑似相关";
      if (["不相关", "irrelevant", "none", "no"].includes(v)) return "不相关";
      return v;
    };
    const label = toLabel(raw);
    const color = label === "相关" ? "bg-emerald-600"
      : label === "疑似相关" ? "bg-amber-500"
      : label === "不相关" ? "bg-gray-500"
      : "bg-gray-500";
    return (
      <span className={`px-3 py-1 rounded-full text-white text-sm font-medium ${color}`}>{label}</span>
    );
  };

  // 提取初筛 relevant_result 的决策理由，仅展示 decision_reason；若不存在则做宽松回退
  const extractScreeningEvidence = (val: unknown): string | null => {
    if (val == null) return null;
    if (typeof val === "string") return val;
    if (Array.isArray(val)) {
      // 优先找数组元素中的 decision_reason
      for (const it of val as unknown[]) {
        if (it && typeof it === "object" && (it as any).decision_reason) {
          const v = (it as any).decision_reason;
          return typeof v === "string" ? v : JSON.stringify(v);
        }
      }
      const list = (val as unknown[]).map((x) => (typeof x === "string" ? x : typeof x === "object" && x ? JSON.stringify(x) : String(x)));
      return list.join("\n");
    }
    if (typeof val === "object") {
      const obj = val as Record<string, unknown>;
      if (obj["decision_reason"]) {
        const v = obj["decision_reason"];
        return typeof v === "string" ? v : JSON.stringify(v);
      }
      const candidateKeys = [
        "reason",
        "evidence",
        "analysis",
        "explanation",
        "summary",
        "desc",
        "detail",
        "details",
        "text",
        "message",
      ];
      for (const k of candidateKeys) {
        if (obj[k]) {
          const v = obj[k];
          if (typeof v === "string") return v;
          if (Array.isArray(v)) return (v as unknown[]).map((x) => (typeof x === "string" ? x : JSON.stringify(x))).join("\n");
          if (typeof v === "object") return JSON.stringify(v);
        }
      }
      return JSON.stringify(obj);
    }
    return String(val);
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
  const hasContentAnalysis = (keyPointItems || []).length > 0;

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

  // 图文分析视图数据：将 source 为 image/title/comment 的事件映射
  const pictureViewData: PicItem[] = useMemo(() => {
    const raw = (analysis as { timeline?: { events?: unknown[] } | unknown[] | null } | null)?.timeline;
    const list = (raw && ((raw as { events?: unknown[] }).events || raw)) || [];
    const arr = Array.isArray(list) ? (list as Record<string, any>[]) : [];
    return arr
      .filter((e) => {
        const src = e.source;
        return src === "image" || src === "title" || src === "comment";
      })
      .map((e, idx) => {
        const riskRaw = e.risk_type as unknown;
        const riskBadges = Array.isArray(riskRaw)
          ? (riskRaw as unknown[]).map((x) => String(x))
          : typeof riskRaw === "string" && riskRaw
          ? [String(riskRaw)]
          : [];
        const evidence = e.evidence || {};
        const tsLabel = ((): string => {
          const t = String(e.timestamp || "");
          if (t === "评论") return "内容"; // 统一显示为“内容”
          return t || "图片";
        })();
        return {
          id: String(idx + 1),
          sourceLabel: tsLabel,
          riskBadges,
          overview: String(e.issue || ""),
          scene: String(e.scene_description || ""),
          evidence: {
            scene_area: evidence.scene_area,
            subject_type: evidence.subject_type,
            subject_behavior: evidence.subject_behavior,
            visibility: evidence.visibility,
          },
          snippet: String(e.evidence?.audio_quote || ""),
        } as PicItem;
      });
  }, [analysis]);

  

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

  // 是否存在任何底部可视化数据（时间轴/图文/评论）
  const hasAnyBottomData = useMemo(() => {
    const a = (timelineViewData || []).length > 0;
    const b = (pictureViewData || []).length > 0;
    const c = (commentAnalysisData || []).length > 0;
    return a || b || c;
  }, [timelineViewData, pictureViewData, commentAnalysisData]);

  // 点击“查看原始内容”触发的打开与锚点定位
  const handleViewSourceFromTimeline = (item: TLItem) => {
    const start = String(item.timestamp || "").match(/\d{2}:\d{2}/)?.[0] || null;
    const snippet = item.snippet || "";
    const commentPath = findCommentPathBySnippet(commentsJson, snippet);
    setPanelOpen(true);
    // 图文模式：直接打开图文页签（不做时间定位）
    const isPicture = post?.post_type && ["image","images","graphic","note"].includes(String(post.post_type).toLowerCase());
    if (isPicture) {
      setActiveBottomTab("timeline");
      return;
    }
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
            onClick={() => {
              if (location.state && (location.state as { fromDashboard?: boolean }).fromDashboard && !isDashboardCacheDirty()) {
                navigate(-1);
                return;
              }
              markDashboardCacheDirty();
              navigate("/dashboard");
            }}
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
              authorFollowerCount={(authorProfile?.follower_count ?? post.author_follower_count) || 0}
              isInfluencer={isInfluencer}
              authorTooltipData={{
                authorName: authorProfile?.nickname || post.author_name || "作者",
                followerCount: authorProfile?.follower_count ?? post.author_follower_count ?? 0,
                avatarUrl: authorProfile?.avatar_url || null,
                shareUrl: authorProfile?.share_url || null,
                signature: authorProfile?.signature || null,
                location: authorProfile?.location || null,
                accountCertInfo: authorProfile?.account_cert_info || null,
                verificationType: authorProfile?.verification_type || null,
                nickname: authorProfile?.nickname || null,
                isInfluencer: isInfluencer,
              } as AuthorTooltipData}
              originalUrl={post.original_url || undefined}
              videoUrl={
                Array.isArray(post.video_url)
                  ? post.video_url[0] || undefined
                  : post.video_url || undefined
              }
              brandRelevance={
                analysis?.brand_relevance
                  ? analysis.brand_relevance
                  : (String(post?.relevant_status || "").toLowerCase() === "no" ? "无关" : undefined)
              }
              relevanceEvidence={
                analysis?.relevance_evidence || (
                  String(post?.relevant_status || "").toLowerCase() === "no" ? (extractScreeningEvidence(post?.relevant_result) || undefined) : undefined
                )
              }
              // 传递优先级及其判定理由，用于在左侧卡片显示“优先级判定说明”
              totalRisk={analysis?.total_risk || undefined}
              totalRiskReason={analysis?.total_risk_reason || undefined}
              className="h-fit"
              onGenerateAdvice={handleViewAdvice}
            />
          ) : (
            <DetailMainSkeleton />
          )}
          
        </div>

        {/* Quick Stats */}
        <div className="space-y-6">
          {post ? (
          <div className="p-6 rounded-2xl bg-white/10 backdrop-blur-xl border border-white/20 shadow-xl group relative">
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
              {/* 相关性：优先 gg_video_analysis.brand_relevance，其次 gg_platform_post.relevant_status */}
              <div className="flex items-center justify-between">
                <span className="text-gray-600 dark:text-gray-400">相关性</span>
                {renderRelevanceBadge(analysis?.brand_relevance || null, post?.relevant_status || null)}
              </div>
              {/* total_risk 徽标与理由 */}
              <div className="flex items-center justify-between">
                <span className="text-gray-600 dark:text-gray-400">优先级</span>
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <span
                        className={cn(
                          "px-3 py-1 rounded-full text-white text-sm font-medium",
                          ((t) => (t === "高" ? "bg-red-600" : t === "中" ? "bg-amber-500" : t === "低" ? "bg-emerald-600" : "bg-gray-500"))(
                            ((v) => { const s = String(v || "").trim().toLowerCase(); if (!s) return "未标注"; if (s === "high" || s === "高") return "高"; if (s === "medium" || s === "中") return "中"; if (s === "low" || s === "低") return "低"; return "未标注"; })(analysis?.total_risk)
                          )
                        )}
                      >
                        {((v) => { const s = String(v || "").trim().toLowerCase(); if (!s) return "未知优先级"; if (s === "high" || s === "高") return "高"; if (s === "medium" || s === "中") return "中"; if (s === "low" || s === "低") return "低"; return "未知优先级"; })(analysis?.total_risk)}
                      </span>
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs whitespace-pre-wrap">
                      {analysis?.total_risk_reason || "无判定理由"}
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-600 dark:text-gray-400">舆情状态</span>
                <span className={
                  analysis?.sentiment === "negative"
                    ? "px-3 py-1 rounded-full bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 text-sm font-medium"
                    : analysis?.sentiment === "positive"
                    ? "px-3 py-1 rounded-full bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 text-sm font-medium"
                    : "px-3 py-1 rounded-full bg-gray-200 dark:bg-gray-800 text-gray-700 dark:text-gray-300 text-sm font-medium"
                }>
                  {analysis?.sentiment === "negative" ? "负面" : analysis?.sentiment === "positive" ? "正向" : "未知"}
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
                <span className="flex items-center gap-2">
                  {/* 仅失败态时显示重试按钮；并在悬停卡片时可见 */}
                  {isFailedStatus(post?.analysis_status) && (
                    <button
                      onClick={handleRetryAnalysis}
                      className="opacity-0 group-hover:opacity-100 transition-opacity duration-200 inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium border border-white/30 bg-white/10 hover:bg-white/20"
                      aria-label="重试分析"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      <span>重试</span>
                    </button>
                  )}
                  {renderAnalysisStatus(post?.analysis_status, Boolean(analysis))}
                </span>
              </div>
            </div>
          </div>
          ) : (
            <DetailSidebarSkeleton />
          )}

          {/* Sentiment Analysis Summary */}
          {analysisLoading ? (
            <SectionSkeleton rows={4} />
          ) : hasContentAnalysis ? (
            <AnalysisSection
              title="内容解析"
              icon={<BarChart3 className="w-5 h-5 text-blue-600 dark:text-blue-400" />}
              items={keyPointItems}
            />
          ) : null}
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
        mode={(post?.post_type && ["image","images","graphic","note"].includes(String(post.post_type).toLowerCase())) ? "picture" : "video"}
        pictureContent={pictureContent}
        pictureCoverUrl={pictureCoverUrl}
        pictureTitle={post?.title || null}
      />

      {/* 处理建议面板 */}
      <HandlingSuggestionsPanel
        open={suggestionsOpen}
        onClose={() => setSuggestionsOpen(false)}
        postId={post?.id}
      />

      {/* 底部双 Tab：时间轴分析/图文分析 或 评论分析（无数据则隐藏整个区域） */}
      {hasAnyBottomData && (
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
                                <span>{(post?.post_type && ["image","images","graphic","note"].includes(String(post.post_type).toLowerCase())) ? "图文分析" : "时间轴分析"}</span>
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
            {(post?.post_type && ["image","images","graphic","note"].includes(String(post.post_type).toLowerCase())) ? "查看原始评论和图文" : "查看原始评论和字幕"}
          </button>
        </div>

        <div className="p-6">
          {activeBottomTab === "timeline" ? (
            analysisLoading ? (
              <SectionSkeleton rows={6} />
            ) : (
              (post?.post_type && ["image","images","graphic","note"].includes(String(post.post_type).toLowerCase())) ? (
                <PictureAnalysis
                  items={pictureViewData}
                  onViewSource={() => {
                    setPanelOpen(true);
                    // 图文来源无法通过时间定位，打开面板并默认停留在图文/评论
                  }}
                />
              ) : (
                <TimelineAnalysis items={timelineViewData} onViewSource={handleViewSourceFromTimeline} />
              )
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
      )}
    </div>
  );
}
