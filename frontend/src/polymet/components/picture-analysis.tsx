import React from "react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

/**
 * 图文分析组件：用于展示 ANLALYZE_PICTURE 产出的 timeline 事件。
 * 结构参考：timestamp(图片/标题/评论) + issue/scene_description + 风险标签 + 证据摘要。
 */

export interface PictureItemEvidenceSummary {
  scene_area?: string;
  subject_type?: string;
  subject_behavior?: string;
  objects_involved?: unknown;
  brand_assets?: unknown;
  visibility?: string;
}

export interface PictureItem {
  id: string;
  sourceLabel: string; // 图片 | 标题 | 评论
  riskBadges: string[];
  overview: string; // 问题概述（取 issue）
  scene: string; // 场景详述（scene_description）
  evidence?: PictureItemEvidenceSummary;
  // 片段文本用于在源查看时定位（评论原文或标题原文）
  snippet?: string;
}

interface PictureAnalysisProps {
  items: PictureItem[];
  className?: string;
  onViewSource?: (item: PictureItem) => void;
}

export default function PictureAnalysis({ items, className = "", onViewSource }: PictureAnalysisProps) {
  const chipColor = (label: string) => {
    if (label === "图片") return "bg-blue-500/15 text-blue-600 dark:text-blue-400 border-blue-500/30";
    if (label === "标题") return "bg-purple-500/15 text-purple-600 dark:text-purple-400 border-purple-500/30";
    return "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30";
  };
  return (
    <div className={cn("space-y-6", className)}>
      {items.map((item) => (
        <div key={item.id} className="group p-6 rounded-2xl bg-white/10 backdrop-blur-xl border border-white/20 shadow-xl hover:shadow-2xl hover:bg-white/15 transition-all duration-300">
          <div className="flex items-center justify-between gap-3 mb-2">
            <div className={cn("px-2.5 py-1 rounded-md text-xs border", chipColor(item.sourceLabel))}>{item.sourceLabel}</div>
            <div className="flex flex-wrap gap-2">
              {item.riskBadges.map((rb, i) => (
                <Badge key={`${rb}-${i}`} variant="outline" className="px-2 py-1 text-xs bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 border-red-200 dark:border-red-800">
                  {rb}
                </Badge>
              ))}
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex gap-3 items-start">
              <div className="w-2 h-2 rounded-full bg-blue-500 mt-2 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-3 mb-1">
                  <h4 className="font-medium text-blue-600 dark:text-blue-400">概述：</h4>
                  {onViewSource && (
                    <button
                      className="px-3 py-1.5 rounded-lg text-xs bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/30 hover:bg-blue-500/15 transition opacity-0 group-hover:opacity-100"
                      onClick={() => onViewSource(item)}
                      aria-label="查看原始内容"
                    >
                      查看原始内容
                    </button>
                  )}
                </div>
                <p className="text-gray-700 dark:text-gray-300 text-sm leading-relaxed">{item.overview}</p>
              </div>
            </div>

            <div className="flex gap-3">
              <div className="w-2 h-2 rounded-full bg-green-500 mt-2 flex-shrink-0" />
              <div>
                <h4 className="font-medium text-green-600 dark:text-green-400 mb-1">原始内容：</h4>
                <p className="text-gray-700 dark:text-gray-300 text-sm leading-relaxed">{item.scene}</p>
              </div>
            </div>

            {/* 按需：不再展示证据摘要明细（场景/主体/行为/可见性） */}
          </div>
        </div>
      ))}
    </div>
  );
}


