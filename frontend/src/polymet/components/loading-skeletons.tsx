import React from "react";
import { Skeleton } from "@/components/ui/skeleton";

export const DashboardCardSkeleton: React.FC = () => (
  <div className="rounded-2xl overflow-hidden animate-pulse">
    <div className="relative">
      <Skeleton className="w-full aspect-video" />
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent animate-[shimmer_1.2s_infinite]" />
    </div>
    <div className="p-4 space-y-3">
      <Skeleton className="h-4 w-5/6" />
      <div className="flex gap-2">
        <Skeleton className="h-5 w-16 rounded-full" />
        <Skeleton className="h-5 w-16 rounded-full" />
        <Skeleton className="h-5 w-16 rounded-full" />
      </div>
      <div className="flex gap-3">
        <Skeleton className="h-3 w-10" />
        <Skeleton className="h-3 w-10" />
        <Skeleton className="h-3 w-10" />
      </div>
    </div>
  </div>
);

export const DetailMainSkeleton: React.FC = () => (
  <div className="rounded-3xl overflow-hidden border border-white/20">
    <div className="relative aspect-video">
      <Skeleton className="w-full h-full" />
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent animate-[shimmer_1.2s_infinite]" />
    </div>
    <div className="p-8 space-y-4">
      <Skeleton className="h-7 w-2/3" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-11/12" />
      <div className="flex items-center justify-between pt-2">
        <div className="flex items-center space-x-4">
          <Skeleton className="h-4 w-16" />
          <Skeleton className="h-4 w-24" />
        </div>
        <Skeleton className="h-4 w-24" />
      </div>
    </div>
  </div>
);

export const DetailSidebarSkeleton: React.FC = () => (
  <div className="p-6 rounded-2xl bg-white/10 backdrop-blur-xl border border-white/20 shadow-xl">
    <Skeleton className="h-6 w-24 mb-4" />
    <div className="space-y-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="flex items-center justify-between">
          <Skeleton className="h-4 w-20" />
          <Skeleton className="h-6 w-24 rounded-full" />
        </div>
      ))}
    </div>
  </div>
);

// 通用的分析板块骨架（用于“内容解析”“时间轴分析”等）
export const SectionSkeleton: React.FC<{ rows?: number }> = ({ rows = 5 }) => (
  <div className="rounded-2xl bg-white/10 backdrop-blur-xl border border-white/20 shadow-xl">
    <div className="p-6 border-b border-white/10 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <Skeleton className="h-8 w-8 rounded-xl" />
        <Skeleton className="h-6 w-24" />
      </div>
      <Skeleton className="h-8 w-28 rounded-xl" />
    </div>
    <div className="p-6 space-y-4">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="p-4 rounded-xl bg-white/5 backdrop-blur-sm border border-white/10">
          <div className="flex items-start gap-3">
            <Skeleton className="h-8 w-8 rounded-lg" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-2/3" />
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-3 w-5/6" />
            </div>
          </div>
        </div>
      ))}
    </div>
  </div>
);

export default {
  DashboardCardSkeleton,
  DetailMainSkeleton,
  DetailSidebarSkeleton,
  SectionSkeleton,
};


