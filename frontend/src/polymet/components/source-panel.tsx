import React, { useEffect, useMemo, useState } from "react";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Tabs, TabsContent } from "@/components/ui/tabs";
import { MessageCircle, Subtitles, X, Search } from "lucide-react";
import { cn } from "@/lib/utils";

type CommentNode = {
  content: string;
  like_count?: number;
  reply_count?: number;
  author_name?: string | null;
  author_avatar_url?: string | null;
  published_at?: string | null; // ISO
  replies?: CommentNode[];
};

type CommentsJson = {
  post?: { id?: number | string; title?: string };
  comments?: CommentNode[];
};

type TranscriptSegment = {
  start: string; // mm:ss
  end?: string; // mm:ss
  text: string;
  speaker?: string;
};

type TranscriptJson = {
  segments?: TranscriptSegment[];
};

interface SourcePanelProps {
  open: boolean;
  onOpenChange: (next: boolean) => void;
  commentsJson?: CommentsJson | null;
  transcriptJson?: TranscriptJson | null;
  // 新增：加载状态（用于骨架屏）
  commentsLoading?: boolean;
  transcriptLoading?: boolean;
  // 锚点：评论路径（如 "12-0-0"）与字幕索引或时间
  anchorCommentPath?: string | null;
  anchorSegmentIndex?: number | null;
  anchorSegmentStart?: string | null; // mm:ss，若无索引则按 start 匹配
  defaultTab?: "comments" | "transcript";
}

// 计算评论树形的唯一路径 id，如 c-3-0-1
const buildCommentDomId = (path: number[]) => `c-${path.join("-")}`;

// 高亮某个元素并在 3s 后淡出
const useHighlight = (elementId: string | null | undefined, enabled: boolean) => {
  useEffect(() => {
    if (!enabled || !elementId) return;
    const el = document.getElementById(elementId);
    if (!el) return;
    el.classList.add("ring-2", "ring-primary/40", "bg-primary/5");
    el.scrollIntoView({ block: "center" });
    const t = setTimeout(() => {
      el.classList.remove("ring-2", "ring-primary/40", "bg-primary/5");
    }, 3000);
    return () => clearTimeout(t);
  }, [elementId, enabled]);
};

// 保留递归渲染实现（当前未直接使用，保留以备多层楼中楼扩展）。
// 为避免未使用告警，不导出也不引用，仅作占位类型。
// 占位注释：如需多层楼中楼递归渲染，可在此处实现 CommentItem 组件

export const SourcePanel: React.FC<SourcePanelProps> = ({
  open,
  onOpenChange,
  commentsJson,
  transcriptJson,
  commentsLoading = false,
  transcriptLoading = false,
  anchorCommentPath,
  anchorSegmentIndex,
  anchorSegmentStart,
  defaultTab = "comments",
}) => {
  const [activeTab, setActiveTab] = useState<"comments" | "transcript">("comments");
  const [searchQuery, setSearchQuery] = useState("");
  const segments = useMemo(() => (transcriptJson?.segments || []) as TranscriptSegment[], [transcriptJson]);
  const normalizeAvatarUrl = (url?: string | null) => {
    if (!url) return "";
    const u = String(url).trim();
    if (u.startsWith("//")) return `https:${u}`;
    if (u.startsWith("http://") || u.startsWith("https://")) return u;
    return u;
  };
  // 解析评论锚点 id
  const commentAnchorId = useMemo(() => {
    if (!anchorCommentPath) return null;
    const parts = anchorCommentPath
      .split("-")
      .map((x) => parseInt(x, 10))
      .filter((n) => !Number.isNaN(n));
    if (parts.length === 0) return null;
    return buildCommentDomId(parts);
  }, [anchorCommentPath]);

  // 解析字幕锚点 id（t-idx）
  const transcriptAnchorId = useMemo(() => {
    if (typeof anchorSegmentIndex === "number" && anchorSegmentIndex >= 0) return `t-${anchorSegmentIndex}`;
    if (anchorSegmentStart) {
      const idx = segments.findIndex((s) => s.start === anchorSegmentStart);
      if (idx >= 0) return `t-${idx}`;
      // 近似：取 start 不大于给定 start 的最后一条
      const toSec = (t: string) => {
        const [m, s] = t.split(":").map((n) => parseInt(n, 10) || 0);
        return m * 60 + s;
      };
      const target = toSec(anchorSegmentStart);
      let near = -1;
      segments.forEach((s, i) => {
        const v = toSec(s.start);
        if (v <= target) near = i;
      });
      if (near >= 0) return `t-${near}`;
    }
    return null;
  }, [anchorSegmentIndex, anchorSegmentStart, segments]);

  // 根据默认 tab 与锚点判断初始 tab
  // 根据锚点切换受控 tab
  useEffect(() => {
    if (transcriptAnchorId) setActiveTab("transcript");
    else if (commentAnchorId) setActiveTab("comments");
    else setActiveTab(defaultTab);
  }, [commentAnchorId, transcriptAnchorId, defaultTab]);

  // 高亮效果
  useHighlight(commentAnchorId, open);
  useHighlight(transcriptAnchorId, open);

  // 记录 tabs 当前值（受控 to uncontrolled：用 ref 保存初始，仅用于默认）
  // 受控 Tab：直接使用 activeTab，不再需要 defaultValueRef

  // 过滤
  const filteredComments = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return commentsJson?.comments || [];
    const res: CommentNode[] = [];
    const walk = (nodes: CommentNode[], path: number[]): void => {
      nodes.forEach((n, i) => {
        const ok = String(n.content || "").toLowerCase().includes(q);
        if (ok) res.push(n);
        const children = n.replies || [];
        if (children.length > 0) walk(children, [...path, i]);
      });
    };
    walk(commentsJson?.comments || [], []);
    return res;
  }, [commentsJson, searchQuery]);

  const filteredSegments = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return segments;
    return segments.filter((s) => s.text.toLowerCase().includes(q) || s.start.includes(q));
  }, [segments, searchQuery]);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent hideCloseButton side="right" className="w-[820px] sm:w-[820px] max-w-[90vw] sm:max-w-none p-0 border-l bg-white/95 dark:bg-gray-900/95 backdrop-blur-xl">
        {/* Hidden title for accessibility to satisfy Radix Dialog requirement */}
        <SheetHeader>
          <SheetTitle className="sr-only">原始评论与字幕</SheetTitle>
        </SheetHeader>
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-white/10 bg-white/5 backdrop-blur-sm sticky top-0 z-20">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-xl bg-gradient-to-br from-blue-500/20 to-purple-600/20">
              {activeTab === "comments" ? (
                <MessageCircle className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              ) : (
                <Subtitles className="w-5 h-5 text-purple-600 dark:text-purple-400" />
              )}
            </div>
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">原始评论与字幕</h2>
          </div>
          <button
            onClick={() => onOpenChange(false)}
            className="p-2 rounded-xl bg-white/10 hover:bg-white/20 transition-all duration-200 border border-white/20 hover:border-white/30"
          >
            <X className="w-5 h-5 text-gray-700 dark:text-gray-300" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-white/10 bg-white/5">
          <button
            onClick={() => setActiveTab("comments")}
            className={cn(
              "flex-1 px-6 py-4 text-sm font-medium transition-all duration-200 relative",
              activeTab === "comments"
                ? "text-blue-600 dark:text-blue-400 bg-blue-50/50 dark:bg-blue-900/20"
                : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-white/5"
            )}
          >
            <div className="flex items-center justify-center space-x-2">
              <MessageCircle className="w-4 h-4" />
              <span>评论</span>
              {(commentsLoading ? null : ((commentsJson?.comments || []).length > 0)) && (
                <span className="ml-2 text-xs px-2 py-0.5 rounded-full bg-white/20 border border-white/30">{(commentsJson?.comments || []).length}</span>
              )}
            </div>
            {activeTab === "comments" && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-blue-500 to-purple-600" />
            )}
          </button>
          <button
            onClick={() => setActiveTab("transcript")}
            className={cn(
              "flex-1 px-6 py-4 text-sm font-medium transition-all duration-200 relative",
              activeTab === "transcript"
                ? "text-purple-600 dark:text-purple-400 bg-purple-50/50 dark:bg-purple-900/20"
                : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-white/5"
            )}
          >
            <div className="flex items-center justify-center space-x-2">
              <Subtitles className="w-4 h-4" />
              <span>字幕</span>
              {(transcriptLoading ? null : (segments.length > 0)) && (
                <span className="ml-2 text-xs px-2 py-0.5 rounded-full bg-white/20 border border-white/30">{segments.length}</span>
              )}
            </div>
            {activeTab === "transcript" && (
              <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-purple-500 to-pink-600" />
            )}
          </button>
        </div>

        {/* Search */}
        <div className="p-4 border-b border-white/10 bg-white/5 sticky top-[73px] z-10">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder={`搜索${activeTab === "comments" ? "评论" : "字幕"}内容...`}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-3 rounded-xl bg-white/10 backdrop-blur-sm border border-white/20 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all duration-200"
            />
          </div>
        </div>

        {/* Content */}
        <Tabs value={activeTab} className="w-full">
          <TabsContent value="comments" className={cn("px-6 pb-6 pt-4", activeTab === "comments" ? "block" : "hidden")}> 
            {commentsLoading ? (
              <div className="max-h-[70vh] overflow-auto pr-2 space-y-3">
                {Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="p-4 rounded-xl bg-white/10 backdrop-blur-sm border border-white/20 animate-pulse">
                    <div className="flex items-center gap-3 mb-3">
                      <div className="w-8 h-8 rounded-full bg-gray-300/40" />
                      <div className="flex-1">
                        <div className="h-3 w-32 bg-gray-300/40 rounded" />
                        <div className="h-3 w-24 bg-gray-200/30 rounded mt-2" />
                      </div>
                    </div>
                    <div className="h-3 w-full bg-gray-300/30 rounded" />
                    <div className="h-3 w-5/6 bg-gray-200/30 rounded mt-2" />
                  </div>
                ))}
              </div>
            ) : (commentsJson?.comments && (commentsJson.comments.length > 0)) ? (
              <div className="max-h-[70vh] overflow-auto pr-2 space-y-4">
                {(filteredComments.length > 0 ? filteredComments : commentsJson.comments).map((c, idx) => (
                  <div key={idx} id={`c-${idx}`} className="p-4 rounded-xl bg-white/10 backdrop-blur-sm border border-white/20 hover:bg-white/15 hover:border-white/30 transition-all duration-300">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center space-x-3">
                        {c.author_avatar_url ? (
                          <img src={normalizeAvatarUrl(c.author_avatar_url)} alt="avatar" className="w-8 h-8 rounded-full object-cover" onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }} />
                        ) : (
                          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-sm font-medium">评</div>
                        )}
                        <div className="leading-tight">
                          <h4 className="font-medium text-gray-900 dark:text-white">{c.author_name || "评论"}</h4>
                          {c.published_at && (
                            <div className="text-xs text-gray-500 dark:text-gray-400">{String(c.published_at).replace("T"," ").slice(0,16)}</div>
                          )}
                        </div>
                      </div>
                      {/* 右侧：评论ID + 情绪 Badge 右对齐 */}
                      <div className="flex items-center gap-2">
                        <span className="text-xs px-2 py-1 rounded-md bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 border border-white/10">评论ID: c-{idx}</span>
                        {(typeof c.like_count === "number") && (
                          <span className="text-xs px-2 py-0.5 rounded-full border bg-gray-100 dark:bg-gray-900/30 text-gray-700 dark:text-gray-400 border-gray-200 dark:border-gray-800">赞 {c.like_count || 0}</span>
                        )}
                        {(typeof c.reply_count === "number") && (
                          <span className="text-xs px-2 py-0.5 rounded-full border bg-gray-100 dark:bg-gray-900/30 text-gray-700 dark:text-gray-400 border-gray-200 dark:border-gray-800">回复 {c.reply_count || 0}</span>
                        )}
                        <span
                          className={cn(
                            "text-xs px-2 py-0.5 rounded-full border",
                            String(c.content || "").match(/不|差|累|压榨|烦|问题|麻|哭|怒|气|骂|糟|烂/)
                              ? "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 border-red-200 dark:border-red-800"
                              : "bg-gray-100 dark:bg-gray-900/30 text-gray-700 dark:text-gray-400 border-gray-200 dark:border-gray-800"
                          )}
                        >
                          {String(c.content || "").match(/不|差|累|压榨|烦|问题|麻|哭|怒|气|骂|糟|烂/) ? "负面" : "中性"}
                        </span>
                      </div>
                    </div>
                    <div className="whitespace-pre-wrap leading-relaxed text-gray-900 dark:text-gray-100">{c.content}</div>
                    {(c.replies || []).map((r, i) => (
                      <div key={i} className="mt-3 ml-4 pl-3 border-l">
                        <div className="flex items-start gap-2 mb-1">
                          {r.author_avatar_url ? (
                            <img src={normalizeAvatarUrl(r.author_avatar_url)} alt="avatar" className="w-5 h-5 rounded-full object-cover" onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }} />
                          ) : (
                            <div className="w-5 h-5 rounded-full bg-blue-500 text-white text-[10px] flex items-center justify-center">评</div>
                          )}
                          <div className="text-xs text-gray-600 dark:text-gray-300">
                            <span className="mr-2">{r.author_name || "用户"}</span>
                            {r.published_at && <span className="text-gray-400">{String(r.published_at).replace("T"," ").slice(0,16)}</span>}
                          </div>
                        </div>
                        <div className="text-sm whitespace-pre-wrap text-gray-800 dark:text-gray-200">{r.content}</div>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-gray-500">暂无评论数据</div>
            )}
          </TabsContent>

          <TabsContent value="transcript" className={cn("px-6 pb-6 pt-4", activeTab === "transcript" ? "block" : "hidden")}> 
            {transcriptLoading ? (
              <div className="max-h-[70vh] overflow-auto pr-2 space-y-3">
                {Array.from({ length: 8 }).map((_, i) => (
                  <div key={i} className="p-4 rounded-xl bg-white/10 backdrop-blur-sm border border-white/20 animate-pulse">
                    <div className="flex items-start space-x-3">
                      <div className="px-10 py-3 rounded-full bg-gray-300/30" />
                      <div className="flex-1">
                        <div className="h-3 w-full bg-gray-300/30 rounded" />
                        <div className="h-3 w-4/5 bg-gray-200/30 rounded mt-2" />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : segments.length > 0 ? (
              <div className="max-h-[70vh] overflow-auto pr-2 space-y-3">
                {(filteredSegments.length > 0 ? filteredSegments : segments).map((seg, idx) => (
                  <div key={idx} id={`t-${idx}`} className="p-4 rounded-xl bg-white/10 backdrop-blur-sm border border-white/20 hover:bg-white/15 hover:border-white/30 transition-all duration-300">
                    <div className="flex items-start gap-3">
                      <div className="flex-shrink-0 ">
                        <div className="px-3 py-1 rounded-full bg-gradient-to-r from-purple-500/20 to-pink-500/20 border border-purple-200/20 dark:border-purple-800/20">
                          <span className="text-xs font-mono text-purple-700 dark:text-purple-300">{seg.end ? `${seg.start}–${seg.end}` : seg.start}</span>
                        </div>
                      </div>
                      <div className="flex-1 flex mt-1.5 items-start justify-between gap-3">
                        <p className="text-gray-700 dark:text-gray-300 text-sm leading-relaxed whitespace-pre-wrap m-0 flex-1">{seg.text}</p>
                        <span className="text-xs px-2 py-0.5 rounded-full border bg-gray-100 dark:bg-gray-900/30 text-gray-700 dark:text-gray-400 border-gray-200 dark:border-gray-800 flex-shrink-0 self-start">中性</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-gray-500">暂无字幕数据</div>
            )}
          </TabsContent>
        </Tabs>
      </SheetContent>
    </Sheet>
  );
};

export default SourcePanel;


