import React from "react";
import { cn } from "@/lib/utils";

type PlatformKey = string;

interface PlatformBadgeProps {
  platform: PlatformKey;
  className?: string;
  size?: "sm" | "md";
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

export const PlatformBadge: React.FC<PlatformBadgeProps> = ({ platform, className, size = "sm" }) => {
  const meta = platformMeta(platform);
  const sizeClasses = size === "sm" ? "px-2 py-1 text-xs" : "px-3 py-1.5 text-sm";
  return (
    <span
      className={cn(
        "rounded-md text-white font-medium inline-flex items-center bg-opacity-80",
        `${meta.color} bg-opacity-70`,
        sizeClasses,
        className
      )}
      aria-label={`platform ${meta.label}`}
    >
      {meta.label}
    </span>
  );
};

export default PlatformBadge;


