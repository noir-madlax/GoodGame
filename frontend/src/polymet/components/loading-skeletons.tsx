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

export default {
  DashboardCardSkeleton,
  DetailMainSkeleton,
  DetailSidebarSkeleton,
};


