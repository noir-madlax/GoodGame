// no React import needed with JSX transform
import { Heart, Share2, MessageCircle, Eye, Clock, FileText, ExternalLink as LinkIcon } from "lucide-react";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { normalizeCoverUrl, onImageErrorSetPlaceholder } from "@/lib/media";
import AuthorTooltip, { AuthorTooltipData, formatFollowersCn } from "@/components/ui/author-tooltip";

interface VideoPlayerCardProps {
  title: string;
  description: string;
  thumbnail: string;
  duration: string;
  views: number;
  likes: number;
  comments: number;
  shares?: number;
  timestamp: string;
  author: string;
  authorFollowerCount?: number;
  isInfluencer?: boolean; // 是否达人（≥10万粉丝，帖子或作者任一满足）
  authorTooltipData?: AuthorTooltipData;
  originalUrl?: string;
  videoUrl?: string;
  className?: string;
  brandRelevance?: string;
  relevanceEvidence?: string;
  onGenerateAdvice?: () => void;
}

export default function VideoPlayerCard({
  title,
  description,
  thumbnail,
  duration,
  views,
  likes,
  comments,
  shares = 0,
  timestamp,
  author,
  authorFollowerCount = 0,
  isInfluencer,
  authorTooltipData,
  originalUrl,
  videoUrl,
  className,
  brandRelevance,
  relevanceEvidence,
  onGenerateAdvice,
}: VideoPlayerCardProps) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-3xl bg-white/10 backdrop-blur-xl border border-white/20",
        "shadow-2xl shadow-black/10 hover:shadow-3xl hover:shadow-black/20 transition-all duration-500",
        "hover:scale-[1.02] hover:bg-white/15",
        className
      )}
    >
      {/* Video Thumbnail */}
      <div className="relative aspect-video overflow-hidden rounded-t-3xl">
        {videoUrl ? (
          <video
            className="w-full h-full object-cover"
            controls
            poster={thumbnail}
            src={videoUrl}
          />
        ) : (
          <img
            src={normalizeCoverUrl(thumbnail)}
            alt={title}
            className="w-full h-full object-cover transition-transform duration-700 hover:scale-110"
            referrerPolicy="no-referrer"
            onError={onImageErrorSetPlaceholder}
          />
        )}

        <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />

        {/* Overlay gradient */}

        {/* 原内容图标 + Duration 常显（仅点击图标跳原链） */}
        <div className="absolute bottom-4 right-4 flex items-center gap-2">
          {originalUrl && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    className="p-2 rounded-full bg-black/60 text-white hover:bg-black/70 focus:outline-none focus:ring-2 focus:ring-white/40"
                    aria-label="点击查看原内容"
                    onClick={(e) => {
                      e.stopPropagation();
                      window.open(originalUrl, "_blank");
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        e.stopPropagation();
                        if (originalUrl) window.open(originalUrl, "_blank");
                      }
                    }}
                  >
                    <LinkIcon className="w-4 h-4" />
                  </button>
                </TooltipTrigger>
                <TooltipContent side="top">点击查看原内容</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
          <div className="px-3 py-1 rounded-full bg-black/60 backdrop-blur-sm text-white text-sm font-medium">
            {duration}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-8">
        {/* Title */}
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4 line-clamp-2 leading-tight">
          {title}
        </h2>

        {/* Meta Info */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-4 text-sm text-gray-500 dark:text-gray-400">
            <span className="flex items-center space-x-1">
              <Clock className="w-4 h-4" />

              <span>{timestamp}</span>
            </span>
          </div>
          <AuthorTooltip
            data={{
              authorName: authorTooltipData?.authorName || String(author || "").replace(/^@+/, ""),
              followerCount: authorTooltipData?.followerCount ?? authorFollowerCount,
              avatarUrl: authorTooltipData?.avatarUrl,
              shareUrl: authorTooltipData?.shareUrl,
              signature: authorTooltipData?.signature,
              location: authorTooltipData?.location,
              accountCertInfo: authorTooltipData?.accountCertInfo,
              verificationType: authorTooltipData?.verificationType,
              nickname: authorTooltipData?.nickname,
            }}
          >
            <span className="text-sm text-gray-500 dark:text-gray-400 inline-flex items-center gap-2">
              {(isInfluencer || authorFollowerCount >= 100000) && (
                <img src="/v-badge.svg" alt="达人" className="w-4 h-4" aria-hidden />
              )}
              <span>{authorTooltipData?.nickname || String(author || "").replace(/^@+/, "")}</span>
              <span className="text-gray-600 dark:text-gray-300 inline-flex items-center gap-1"><img src="/follower.svg" alt="粉丝" className="w-3.5 h-3.5" aria-hidden />{formatFollowersCn(authorTooltipData?.followerCount ?? authorFollowerCount)}</span>
            </span>
          </AuthorTooltip>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-6">
            <button className="flex items-center space-x-2 text-gray-600 dark:text-gray-300 hover:text-red-500 transition-colors duration-200">
              <Heart className="w-5 h-5" />

              <span className="font-medium">{likes}</span>
            </button>
            <button className="flex items-center space-x-2 text-gray-600 dark:text-gray-300 hover:text-blue-500 transition-colors duration-200">
              <MessageCircle className="w-5 h-5" />

              <span className="font-medium">{comments}</span>
            </button>
            <div className="flex items-center space-x-2 text-gray-600 dark:text-gray-300">
              <Share2 className="w-5 h-5" />
              <span className="font-medium">{shares}</span>
            </div>
          </div>

          <button
            className="px-6 py-2 rounded-full bg-gradient-to-r from-blue-500 to-purple-600 text-white font-medium hover:from-blue-600 hover:to-purple-700 transition-all duration-300 hover:scale-105 shadow-lg hover:shadow-xl"
            onClick={() => onGenerateAdvice && onGenerateAdvice()}
          >
            查看处理建议
          </button>
        </div>

        {/* Summary Section moved below meta and actions */}
        {description && (
          <div className="mt-6">
            <div className="flex items-center gap-2 mb-2">
              <FileText className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              <span className="text-lg font-bold text-gray-900 dark:text-gray-100">总结</span>
            </div>
            <p className="text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap">
              {description}
            </p>
          </div>
        )}

        {/* Brand relevance and evidence */}
        {(brandRelevance || relevanceEvidence) && (
          <div className="mt-6">
            <div className="flex items-center gap-2 mb-2">
              <LinkIcon className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              <span className="text-lg font-bold text-gray-900 dark:text-gray-100">相关性与证据</span>
              {brandRelevance && (
                <span
                  className={cn(
                    "inline-block ml-4 px-2 py-1 rounded-full text-xs font-medium",
                    brandRelevance.includes("疑似")
                      ? "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300"
                      : "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300"
                  )}
                >
                  {brandRelevance}
                </span>
              )}
            </div>
            
            {relevanceEvidence && (
              <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                {relevanceEvidence}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// 粉丝格式化已在 AuthorTooltip 内导出 formatFollowersCn
