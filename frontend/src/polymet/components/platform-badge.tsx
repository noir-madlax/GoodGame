import React from "react";
import { cn } from "@/lib/utils";

type PlatformKey = string;

interface PlatformBadgeProps {
  platform: PlatformKey;
  className?: string;
  size?: "sm" | "md";
  variant?: "overlay" | "panel"; // overlay: on thumbnail; panel: in cards/sidebars
}

const platformMeta = (platform: PlatformKey) => {
  const key = String(platform || "").toLowerCase();
  // Brand-inspired colors: Douyin pink (#FE2C55) and XHS red (#FF2442)
  if (key === "douyin" || key === "tiktok-cn") {
    return { label: "抖音", color: "bg-[#FE2C55]" };
  }
  if (key === "xiaohongshu" || key === "redbook" || key === "xhs") {
    return { label: "小红书", color: "bg-[#FF2442]" };
  }
  if (key === "bilibili" || key === "bili") {
    return { label: "B站", color: "bg-indigo-500" };
  }
  if (key === "weibo") {
    return { label: "微博", color: "bg-orange-500" };
  }
  return { label: "other", color: "bg-gray-500" };
};

export const PlatformBadge: React.FC<PlatformBadgeProps> = ({ platform, className, size = "sm", variant = "panel" }) => {
  const meta = platformMeta(platform);
  const baseSize = size === "sm" ? "text-xs px-2 py-1" : "text-sm px-3 py-1.5";
  if (variant === "overlay") {
    // On image: glass backdrop + small brand dot + white text
    return (
      <span
        className={cn(
          "inline-flex items-center gap-0 rounded-md text-white",
          "bg-black/45 backdrop-blur-sm ",
          baseSize,
          className
        )}
        aria-label={`platform ${meta.label}`}
      >
        <span className={cn( meta.color.replace("bg-", "bg-"))} aria-hidden />
        {meta.label}
      </span>
    );
  }
  // Panel/default: subtle neutral chip with brand-colored text and dot
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md",
        "bg-gray-200/70 dark:bg-gray-800/70 text-gray-900 dark:text-gray-100",
        "border border-black/10 dark:border-white/10",
        baseSize,
        className
      )}
      aria-label={`platform ${meta.label}`}
    >
     
      <span className={cn(meta.color.replace("bg-", "text-"))}>{meta.label}</span>
    </span>
  );
};

export default PlatformBadge;


