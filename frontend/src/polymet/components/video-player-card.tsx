import React from "react";
import { Play, Heart, Share2, MessageCircle, Eye, Clock } from "lucide-react";
import { cn } from "@/lib/utils";

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
  originalUrl?: string;
  videoUrl?: string;
  className?: string;
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
  originalUrl,
  videoUrl,
  className,
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
            src={thumbnail}
            alt={title}
            className="w-full h-full object-cover transition-transform duration-700 hover:scale-110"
          />
        )}

        <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />

        {/* Overlay gradient */}

        {/* Duration */}
        <div className="absolute bottom-4 right-4 px-3 py-1 rounded-full bg-black/60 backdrop-blur-sm text-white text-sm font-medium">
          {duration}
        </div>
      </div>

      {/* Content */}
      <div className="p-8">
        {/* Title */}
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4 line-clamp-2 leading-tight">
          {title}
        </h2>

        {/* Description */}
        <p className="text-gray-600 dark:text-gray-300 mb-6 line-clamp-3 leading-relaxed">
          {description}
        </p>

        {/* Meta Info */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-4 text-sm text-gray-500 dark:text-gray-400">
            <span className="flex items-center space-x-1">
              <Eye className="w-4 h-4" />

              <span>{views.toLocaleString()}</span>
            </span>
            <span className="flex items-center space-x-1">
              <Clock className="w-4 h-4" />

              <span>{timestamp}</span>
            </span>
          </div>
          <span className="text-sm text-gray-500 dark:text-gray-400">
            @{author}
          </span>
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

          {originalUrl && (
            <button
              className="px-6 py-2 rounded-full bg-gradient-to-r from-blue-500 to-purple-600 text-white font-medium hover:from-blue-600 hover:to-purple-700 transition-all duration-300 hover:scale-105 shadow-lg hover:shadow-xl"
              onClick={() => window.open(originalUrl, "_blank")}
            >
              查看原内容
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
