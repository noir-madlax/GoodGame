import React from "react";
import RelevanceChart from "@/polymet/components/analytics/relevance-chart";
import SeverityAnalysis from "@/polymet/components/analytics/severity-analysis";
import SeverityDetailChart from "@/polymet/components/analytics/severity-detail-chart";
import { Skeleton } from "@/components/ui/skeleton";

// 说明：为了加快集成，先复用 sample 的三个可视化实现；后续若删除 sample 目录，请将这三个组件文件平移到 components/analytics 并更新引用。

export default function ContentAnalysisSection({
  chartState,
  relevanceData,
  severityData,
  severityDetailData,
  onRelevanceClick,
  onBackToPrimary,
  onBackToSecondary,
  onSeverityClick,
  className = "",
  loading = false,
}: {
  chartState: { level: "primary" | "secondary" | "tertiary"; selectedRelevance?: string; selectedSeverity?: string };
  relevanceData: any[];
  severityData?: { relevanceType: string; totalCount: number; data: any[] } | null;
  severityDetailData?: { severityLevel: string; relevanceType: string; totalCount: number; relevanceTotal?: number; data: any[] } | null;
  onRelevanceClick: (name: string) => void;
  onBackToPrimary: () => void;
  onBackToSecondary: () => void;
  onSeverityClick: (severity: string, creatorType?: string) => void;
  className?: string;
  loading?: boolean;
}) {
  return (
    <div className={`space-y-4 ${className}`}>
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
        {chartState.level === "primary"
          ? "内容分布"
          : chartState.level === "secondary"
            ? "内容优先级分布"
            : "创作者类型与平台分布"}
      </h2>

      {loading ? (
        <div className="p-6 rounded-2xl bg-white/10 backdrop-blur-xl border border-white/20">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* 左侧：柱状图骨架 */}
            <div className="lg:col-span-2">
              <div className="mb-4 flex items-center gap-4">
                <Skeleton className="h-8 w-20 rounded-md" />
                <Skeleton className="h-6 w-64" />
              </div>
              <div className="h-80 w-full grid grid-cols-12 items-end gap-2">
                {Array.from({ length: 12 }).map((_, i) => (
                  <Skeleton key={i} className="w-full" style={{ height: `${10 + ((i % 6) + 1) * 12}px` }} />
                ))}
              </div>
            </div>
            {/* 右侧：统计卡骨架 */}
            <div className="space-y-4 self-start">
              <Skeleton className="h-5 w-24" />
              <div className="space-y-3">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="p-3 rounded-xl bg-white/10 border border-white/20">
                    <div className="flex items-center justify-between mb-2">
                      <Skeleton className="h-4 w-16" />
                      <Skeleton className="h-4 w-12" />
                    </div>
                    <div className="space-y-2">
                      {Array.from({ length: 3 }).map((_, j) => (
                        <div key={j} className="flex items-center justify-between">
                          <div className="flex items-center gap-2"><Skeleton className="h-2 w-2 rounded-full" /><Skeleton className="h-3 w-10" /></div>
                          <Skeleton className="h-3 w-6" />
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="p-6 rounded-2xl bg-white/10 backdrop-blur-xl border border-white/20">
          {chartState.level === "primary" && (
            <RelevanceChart data={relevanceData as any} onRelevanceClick={onRelevanceClick} />
          )}
          {chartState.level === "secondary" && severityData && (
            <SeverityAnalysis
              relevanceType={severityData.relevanceType}
              data={severityData.data as any}
              totalCount={severityData.totalCount}
              onBack={onBackToPrimary}
              onSeverityClick={onSeverityClick}
            />
          )}
          {chartState.level === "tertiary" && severityDetailData && (
            <SeverityDetailChart
              severityLevel={severityDetailData.severityLevel}
              relevanceType={severityDetailData.relevanceType}
              data={severityDetailData.data as any}
              totalCount={severityDetailData.totalCount}
              relevanceTotal={severityDetailData.relevanceTotal}
              onBack={onBackToSecondary}
            />
          )}
        </div>
      )}
    </div>
  );
}


