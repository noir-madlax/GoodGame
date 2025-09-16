import { useState } from "react";
import { Heart, MessageCircle, Share2, ExternalLink, Bookmark, BadgeCheck } from "lucide-react";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
// import { Badge } from "@/components/ui/badge";
import { RiskBadge } from "@/components/ui/risk-badge";
// PlatformBadge no longer used on grid card after design update
import { normalizeCoverUrl, onImageErrorSetPlaceholder } from "@/lib/media";
import { PlatformBadge } from "@/polymet/components/platform-badge";

interface VideoGridCardProps {
  title: string;
  thumbnail: string;
  duration: string; // mm:ss
  originalUrl?: string;
  likes: number;
  comments: number;
  shares: number;
  author: string;
  authorFollowerCount?: number;
  platformLabel: string; // 平台 key，用于兼容旧调用
  platform?: string; // 新：平台 key（douyin/xiaohongshu/...）
  riskTags: string[]; // 来自 gg_video_analysis.risk_types
  sentiment?: string; // negative | neutral | positive
  brandRelevance?: string;
  publishDate: string; // YYYY-MM-DD
  className?: string;
  onClick?: () => void; // Optional click handler so parent can control navigation
  isMarked?: boolean; // 是否已标记，用于左下角图标
}

export default function VideoGridCard({
  title,
  thumbnail,
  duration,
  originalUrl,
  likes,
  comments,
  shares,
  author,
  authorFollowerCount = 0,
  platformLabel,
  platform,
  riskTags,
  sentiment,
  brandRelevance,
  publishDate,
  className,
  onClick,
  isMarked,
}: VideoGridCardProps) {
  const [isPortrait, setIsPortrait] = useState<boolean>(false);

  // Tuning knobs for portrait cover rendering. Adjust as needed without touching logic.
  // Increase Y to crop更多上下内容（>1 会放大竖向，裁掉上下）；
  // Increase X 可微调横向填充避免留边。
  const PORTRAIT_SCALE_X = 1.0; // 横向轻微放大
  const PORTRAIT_SCALE_Y = 1.0; // 约裁掉上下各 ~15% - 20%
  const PORTRAIT_POSITION_Y = "40%"; // 焦点（可调 40%-60%）
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
  // Deprecated color map kept for backward compatibility; no longer used

  return (
    <div
      className={cn(
        "group relative overflow-hidden rounded-2xl bg-white/10 backdrop-blur-xl border border-white/20",
        "shadow-lg shadow-black/5 hover:shadow-2xl hover:shadow-black/15 transition-all duration-500",
        "hover:scale-[1.02] hover:bg-white/15 hover:border-white/30 cursor-pointer",
        className
      )}
      role="button"
      tabIndex={0}
      aria-label={`Open detail for ${title}`}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick?.();
        }
      }}
    >
      {/* Thumbnail */}
      <div className="relative aspect-video overflow-hidden">
        {/* Blurred backdrop for portrait images to avoid empty bands */}
        {isPortrait && (
          <img
            src={thumbnail}
            alt=""
            aria-hidden
            className="absolute inset-0 w-full h-full object-cover blur-xl scale-110 opacity-60"
          />
        )}
        {/* Foreground cover */}
        <img
          src={normalizeCoverUrl(thumbnail)}
          alt={title}
          loading="lazy"
          onLoad={(e) => {
            const el = e.currentTarget;
            setIsPortrait(el.naturalHeight > el.naturalWidth);
          }}
          onError={onImageErrorSetPlaceholder}
          className={cn(
            "relative w-full h-full transition-transform duration-700 object-cover",
          )}
          style={{
            objectPosition: `50% ${PORTRAIT_POSITION_Y}`,
            transform: isPortrait
              ? `scale(${PORTRAIT_SCALE_X}, ${PORTRAIT_SCALE_Y})`
              : "scale(1,1)",
          }}
        />

        <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-black/20" />

        {/* 左下角：已标记图标，仅图标显示 */}
        {isMarked && (
          <div className="absolute bottom-2 left-2 px-1.5 py-1 rounded-md bg-black/60 backdrop-blur-sm">
            <Bookmark className="w-4 h-4 text-yellow-400" aria-label="已标记" />
          </div>
        )}

        {/* Play Button removed per requirement: do not show on hover */}

        {/* Duration + 原内容图标（仅 hover 显示；点击仅图标生效） */}
        <div className="absolute bottom-2 right-2 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
          {originalUrl && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    className="p-1 rounded-md bg-black/70 backdrop-blur-sm text-white hover:bg-black/80 focus:outline-none focus:ring-2 focus:ring-white/40"
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
                    <ExternalLink className="w-3.5 h-3.5" />
                  </button>
                </TooltipTrigger>
                <TooltipContent side="top">点击查看原内容</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
          <div className="px-2 py-1 rounded-md bg-black/70 backdrop-blur-sm text-white text-xs font-medium">
            {duration}
          </div>
        </div>

        {/* Left-top: Relevance badge (weak visual) */}
        {brandRelevance && (
          <div className="absolute top-2 left-2">
            <span className="px-2 py-1 rounded-md bg-black/35 backdrop-blur-[2px] text-white/80 text-[10px] font-medium inline-flex items-center gap-1">
              {brandRelevance}
              {brandRelevance.includes("疑似") || brandRelevance.includes("需人工介入") ? (
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-red-500" aria-hidden />
              ) : null}
              {brandRelevance.includes("不相关") || brandRelevance.includes("可忽略") ? (
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-400" aria-hidden />
              ) : null}
            </span>
          </div>
        )}

        {/* Sentiment Badge */}
        {sentiment && (
          <div className="absolute top-2 right-2">
            <span
              className={cn(
                "px-2 py-1 rounded-md text-white text-xs font-medium",
                sentiment === "negative" ? "bg-red-500" : sentiment === "positive" ? "bg-green-500" : "bg-gray-500"
              )}
            >
              {sentiment === "negative" ? "负面" : sentiment === "positive" ? "正向" : "中立"}
            </span>
          </div>
        )}

        {/* Brand Relevance Badge (top-right below sentiment) */}
        {brandRelevance && (
          <div className="absolute top-10 right-2">
           
          </div>
        )}

        {/* More Options removed per requirement: hide the menu on hover */}
      </div>

      {/* Content */}
      <div className="p-4 flex flex-col h-full">
        {/* Title */}
        <div className="mb-2 min-h-[48px] max-h-[48px] overflow-hidden">
          <h3 className="font-semibold text-gray-900 dark:text-white line-clamp-2 text-sm leading-tight group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors duration-200">
            {title}
          </h3>
        </div>

        {/* Risk Badges - fixed height to keep cards aligned even when empty */}
        <div className="flex flex-wrap gap-1.5 mb-3 min-h-[28px] max-h-[28px] overflow-hidden">
          {riskTags.map((tag, index) => (
            <RiskBadge key={index} label={tag} severity="medium" size="sm" />
          ))}
        </div>

        {/* Stats + Platform Logo */}
        <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 mb-3">
          <div className="flex items-center space-x-3">
            <span className="flex items-center space-x-1">
              <Heart className="w-3 h-3" />

              <span>{likes}</span>
            </span>
            <span className="flex items-center space-x-1">
              <MessageCircle className="w-3 h-3" />

              <span>{comments}</span>
            </span>
            <span className="flex items-center space-x-1">
              <Share2 className="w-3 h-3" />

              <span>{shares}</span>
            </span>
          </div>
          <div className="flex items-center">
            {renderPlatformLogo(platform || platformLabel)}
          </div>
        </div>

        {/* Author & Time */}
        <div className="flex items-center justify-between text-xs">
          <span className="text-gray-600 dark:text-gray-300 font-medium inline-flex items-center gap-1">
            <span>{String(author || "").replace(/^@+/, "")}</span>
            {authorFollowerCount > 1000 && (
              <BadgeCheck className="w-3.5 h-3.5 text-blue-500" aria-label="大V" />
            )}
          </span>
          <span className="text-gray-500 dark:text-gray-400">
            {publishDate}
          </span>
        </div>
      </div>

      {/* Hover Overlay */}
      <div className="absolute inset-0 bg-gradient-to-t from-blue-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />
    </div>
  );
}
