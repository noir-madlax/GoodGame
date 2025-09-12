import React from "react";
import { TrendingUp, TrendingDown, Minus, Video, Eye, AlertTriangle } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

interface KPIData { current: number; previous: number; change: number }
interface PlatformDistribution { 抖音: number; 小红书: number }

export default function KPIOverview({
  data,
  platformDistribution,
  className = "",
  loading = false,
}: {
  data: { totalVideos: KPIData; relevantVideos: KPIData; highPriorityVideos: KPIData };
  platformDistribution?: { totalVideos: PlatformDistribution; relevantVideos: PlatformDistribution; highPriorityVideos: PlatformDistribution };
  className?: string;
  loading?: boolean;
}) {
  const iconFor = (c: number) => (c > 0 ? <TrendingUp className="w-4 h-4 text-red-500" /> : c < 0 ? <TrendingDown className="w-4 h-4 text-green-500" /> : <Minus className="w-4 h-4 text-gray-500" />);
  const colorFor = (c: number) => (c > 0 ? "text-red-500" : c < 0 ? "text-green-500" : "text-gray-500");
  const PlatformIcons = ({ d }: { d?: PlatformDistribution }) => {
    if (!d) return null;
    return (
      <div className="flex items-center gap-2 mt-2">
        <div className="flex items-center gap-1"><div className="w-3 h-3 rounded-full bg-red-500" /><span className="text-xs text-gray-600 dark:text-gray-400">抖音: {d.抖音}</span></div>
        <div className="flex items-center gap-1"><div className="w-3 h-3 rounded-full bg-pink-500" /><span className="text-xs text-gray-600 dark:text-gray-400">小红书: {d.小红书}</span></div>
      </div>
    );
  };
  const cards = [
    { title: "总视频数", icon: <Video className="w-5 h-5 text-blue-600 dark:text-blue-400" />, data: data.totalVideos, bg: "bg-blue-50/50 dark:bg-blue-900/20", border: "border-blue-200/50 dark:border-blue-700/50", dist: platformDistribution?.totalVideos },
    { title: "相关视频", icon: <Eye className="w-5 h-5 text-red-600 dark:text-red-400" />, data: data.relevantVideos, bg: "bg-red-50/50 dark:bg-red-900/20", border: "border-red-200/50 dark:border-red-700/50", dist: platformDistribution?.relevantVideos },
    { title: "高优先级视频", icon: <AlertTriangle className="w-5 h-5 text-purple-600 dark:text-purple-400" />, data: data.highPriorityVideos, bg: "bg-purple-50/50 dark:bg-purple-900/20", border: "border-purple-200/50 dark:border-purple-700/50", dist: platformDistribution?.highPriorityVideos },
  ];
  return (
    <div className={`space-y-4 ${className}`}>
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white">关键指标概览</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {loading && Array.from({ length: 3 }).map((_, i) => (
          <div key={`kpi-skeleton-${i}`} className="p-6 rounded-2xl backdrop-blur-xl border border-white/20 bg-white/10">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <Skeleton className="w-5 h-5 rounded" />
                <Skeleton className="h-5 w-24" />
              </div>
            </div>
            <div className="space-y-3">
              <div className="flex items-end gap-2">
                <Skeleton className="h-8 w-20" />
                <Skeleton className="h-4 w-12" />
              </div>
              <Skeleton className="h-3 w-28" />
              <div className="flex items-center gap-2 mt-2">
                <div className="flex items-center gap-1">
                  <Skeleton className="w-3 h-3 rounded-full" />
                  <Skeleton className="h-3 w-16" />
                </div>
                <div className="flex items-center gap-1">
                  <Skeleton className="w-3 h-3 rounded-full" />
                  <Skeleton className="h-3 w-16" />
                </div>
              </div>
            </div>
          </div>
        ))}
        {!loading && cards.map((c, i) => (
          <div key={i} className={`p-6 rounded-2xl backdrop-blur-xl border ${c.bg} ${c.border} transition-all duration-200 hover:shadow-lg`}>
            <div className="flex items-center justify-between mb-4"><div className="flex items-center gap-3">{c.icon}<h3 className="font-medium text-gray-900 dark:text-white">{c.title}</h3></div></div>
            <div className="space-y-2">
              <div className="flex items-end gap-2"><span className="text-3xl font-bold text-gray-900 dark:text-white">{c.data.current}</span><div className="flex items-center gap-1 mb-1">{iconFor(c.data.change)}<span className={`text-sm font-medium ${colorFor(c.data.change)}`}>{Math.abs(c.data.change)}%</span></div></div>
              <p className="text-sm text-gray-600 dark:text-gray-400">上一周期: {c.data.previous}</p>
              <PlatformIcons d={c.dist} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}


