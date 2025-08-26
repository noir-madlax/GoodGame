import React from "react";
import { Play, Eye, Heart, MessageCircle, MoreHorizontal } from "lucide-react";
import { cn } from "@/lib/utils";

interface VideoGridCardProps {
  title: string;
  thumbnail: string;
  duration: string;
  views: number;
  likes: number;
  comments: number;
  author: string;
  category: string;
  tags: string[];
  publishTime: string;
  className?: string;
  onClick?: () => void;
}

export default function VideoGridCard({
  title,
  thumbnail,
  duration,
  views,
  likes,
  comments,
  author,
  category,
  tags,
  publishTime,
  className,
  onClick,
}: VideoGridCardProps) {
  const getCategoryColor = (category: string) => {
    const colors = {
      抖音: "bg-red-500",
      内容: "bg-blue-500",
      小红书: "bg-pink-500",
      正面: "bg-green-500",
      低风险: "bg-yellow-500",
      科普: "bg-purple-500",
      中风险: "bg-orange-500",
      图文: "bg-indigo-500",
    };
    return colors[category as keyof typeof colors] || "bg-gray-500";
  };

  const handleKeyDown: React.KeyboardEventHandler<HTMLDivElement> = (e) => {
    if (!onClick) return;
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onClick();
    }
  };

  return (
    <div
      className={cn(
        "group relative overflow-hidden rounded-2xl bg-white/10 backdrop-blur-xl border border-white/20",
        "shadow-lg shadow-black/5 hover:shadow-2xl hover:shadow-black/15 transition-all duration-500",
        "hover:scale-[1.02] hover:bg-white/15 hover:border-white/30",
        onClick && "cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500",
        className
      )}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : -1}
      onClick={onClick}
      onKeyDown={handleKeyDown}
      aria-label={onClick ? `Open details for ${title}` : undefined}
    >
      {/* Thumbnail */}
      <div className="relative aspect-video overflow-hidden">
        <img
          src={thumbnail}
          alt={title}
          className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110"
        />

        <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-black/20" />

        {/* Play Button */}
        <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300">
          <button className="w-12 h-12 rounded-full bg-white/20 backdrop-blur-md border border-white/30 flex items-center justify-center hover:bg-white/30 transition-all duration-300 hover:scale-110">
            <Play className="w-5 h-5 text-white ml-0.5" fill="white" />
          </button>
        </div>

        {/* Duration */}
        <div className="absolute bottom-2 right-2 px-2 py-1 rounded-md bg-black/70 backdrop-blur-sm text-white text-xs font-medium">
          {duration}
        </div>

        {/* Category Badge */}
        <div
          className={cn(
            "absolute top-2 left-2 px-2 py-1 rounded-md text-white text-xs font-medium",
            getCategoryColor(category)
          )}
        >
          {category}
        </div>

        {/* More Options */}
        <button className="absolute top-2 right-2 w-8 h-8 rounded-full bg-black/50 backdrop-blur-sm flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300 hover:bg-black/70">
          <MoreHorizontal className="w-4 h-4 text-white" />
        </button>
      </div>

      {/* Content */}
      <div className="p-4">
        {/* Title */}
        <h3 className="font-semibold text-gray-900 dark:text-white mb-2 line-clamp-2 text-sm leading-tight group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors duration-200">
          {title}
        </h3>

        {/* Tags */}
        <div className="flex flex-wrap gap-1 mb-3">
          {tags.slice(0, 3).map((tag, index) => (
            <span
              key={index}
              className="px-2 py-1 rounded-full bg-gray-100/50 dark:bg-gray-800/50 text-xs text-gray-600 dark:text-gray-400 backdrop-blur-sm"
            >
              {tag}
            </span>
          ))}
        </div>

        {/* Stats */}
        <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 mb-3">
          <div className="flex items-center space-x-3">
            <span className="flex items-center space-x-1">
              <Eye className="w-3 h-3" />

              <span>{views.toLocaleString()}</span>
            </span>
            <span className="flex items-center space-x-1">
              <Heart className="w-3 h-3" />

              <span>{likes}</span>
            </span>
            <span className="flex items-center space-x-1">
              <MessageCircle className="w-3 h-3" />

              <span>{comments}</span>
            </span>
          </div>
        </div>

        {/* Author & Time */}
        <div className="flex items-center justify-between text-xs">
          <span className="text-gray-600 dark:text-gray-300 font-medium">
            @{author}
          </span>
          <span className="text-gray-500 dark:text-gray-400">
            {publishTime}
          </span>
        </div>
      </div>

      {/* Hover Overlay */}
      <div className="absolute inset-0 bg-gradient-to-t from-blue-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />
    </div>
  );
}
