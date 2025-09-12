import React from "react";
import RelevanceChart from "@/polymet/components/analytics/relevance-chart";
import SeverityAnalysis from "@/polymet/components/analytics/severity-analysis";
import SeverityDetailChart from "@/polymet/components/analytics/severity-detail-chart";
import { SectionSkeleton } from "@/polymet/components/loading-skeletons";
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
  severityDetailData?: { severityLevel: string; relevanceType: string; totalCount: number; data: any[] } | null;
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
            ? `"${chartState.selectedRelevance}"详细分析`
            : `"${chartState.selectedRelevance}" - "${chartState.selectedSeverity}"详细分布`}
      </h2>

      {loading ? (
        <div className="p-6 rounded-2xl bg-white/10 backdrop-blur-xl border border-white/20">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* 左侧：甜甜圈图占位 */}
            <div className="lg:col-span-2 flex items-center justify-center">
              <div className="relative w-[320px] h-[320px] max-w-full">
                <div className="absolute inset-0 rounded-full bg-white/10 animate-pulse" />
                <div className="absolute inset-6 rounded-full bg-transparent border-8 border-white/20" />
                <div className="absolute inset-24 rounded-full bg-white/10" />
              </div>
            </div>
            {/* 右侧：分类统计占位 */}
            <div className="space-y-4">
              <Skeleton className="h-5 w-24" />
              <div className="space-y-3">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="p-3 rounded-xl bg-white/10 border border-white/20">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-white/30" />
                        <Skeleton className="h-4 w-16" />
                      </div>
                      <Skeleton className="h-4 w-4 rounded" />
                    </div>
                    <div className="flex justify-between text-sm">
                      <Skeleton className="h-3 w-12" />
                      <Skeleton className="h-3 w-10" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="p-6 rounded-2xl bg-white/10 backdrop-blur-xl border border-white/20 min-h-[320px]">
          {chartState.level === "primary" ? (
            <RelevanceChart data={relevanceData} onRelevanceClick={onRelevanceClick} />
          ) : chartState.level === "secondary" ? (
            severityData && (
              <SeverityAnalysis
                relevanceType={severityData.relevanceType}
                data={severityData.data}
                totalCount={severityData.totalCount}
                onBack={onBackToPrimary}
                onSeverityClick={onSeverityClick}
              />
            )
          ) : (
            severityDetailData && (
              <SeverityDetailChart
                severityLevel={severityDetailData.severityLevel}
                relevanceType={severityDetailData.relevanceType}
                data={severityDetailData.data}
                totalCount={severityDetailData.totalCount}
                onBack={onBackToSecondary}
              />
            )
          )}
        </div>
      )}
    </div>
  );
}


