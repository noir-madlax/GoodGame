import React from "react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

/**
 * 时间轴分析组件（用于视频分析详情页底部 Tab）
 * 需求要点：
 * - 左侧时间锚（圆点+时间）+ 右侧内容卡片。
 * - 右上角展示风险标签（红色描边样式）。
 * - 不展示“风险等级”胶囊。
 * - 悬浮卡片时，在卡片右上角显示“查看原始内容”按钮；点击后外部回调处理（打开抽屉并锚点定位）。
 * - 组件内不直接操作抽屉，以便复用。
 */

export interface TimelineItem {
  id: string;
  timestamp: string; // mm:ss
  riskBadges: string[];
  videoData: {
    overview: string;
    audio: string;
    scene: string;
  };
  // 可选：外部用于定位的片段文本
  snippet?: string;
}

interface TimelineAnalysisProps {
  items: TimelineItem[];
  className?: string;
  onViewSource?: (item: TimelineItem) => void; // 点击“查看原始内容”时触发
}

export default function TimelineAnalysis({ items, className = "", onViewSource }: TimelineAnalysisProps) {
  return (
    <div className={cn("space-y-6", className)}>
      {items.map((item, index) => (
        <div key={item.id} className="relative">
          {/* 竖向连接线：连接上下两个蓝色圆点 */}
          {index < items.length - 1 && (
            <div className="absolute left-[22px] top-16 bottom-0 w-0.5 bg-gradient-to-b from-blue-600 to-transparent dark:from-blue-400" />
          )}

          <div className="flex gap-6">
            {/* 左侧时间锚点 */}
            <div className="flex flex-col items-center">
              <div className="w-6 h-6 rounded-full bg-blue-500 flex items-center justify-center shadow-lg">
                <div className="w-2 h-2 rounded-full bg-white" />
              </div>
              <div className="mt-2 text-sm font-medium text-gray-600 dark:text-gray-400">{item.timestamp}</div>
            </div>

            {/* 右侧内容卡片 */}
            <div className="group flex-1 p-6 rounded-2xl bg-white/10 backdrop-blur-xl border border-white/20 shadow-xl hover:shadow-2xl hover:bg-white/15 transition-all duration-300 relative">
              {/* 顶部行移除，减少无效留白 */}


              {/* 内容三段 */}
              <div className="space-y-4">
                <div className="flex gap-3 items-start">
                  <div className="w-2 h-2 rounded-full bg-blue-500 mt-2 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-3 mb-1">
                      <div className="flex items-center gap-2">
                        <h4 className="font-medium text-blue-600 dark:text-blue-400">问题概述：</h4>
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
                      <div className="flex flex-wrap gap-2">
                        {item.riskBadges.map((badge, i) => (
                          <Badge
                            key={`${badge}-${i}`}
                            variant="outline"
                            className="px-2 py-1 text-xs bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 border-red-200 dark:border-red-800"
                          >
                            {badge}
                          </Badge>
                        ))}
                      </div>
                    </div>
                    <p className="text-gray-700 dark:text-gray-300 text-sm leading-relaxed">{item.videoData.overview}</p>
                  </div>
                </div>
                <div className="flex gap-3">
                  <div className="w-2 h-2 rounded-full bg-purple-500 mt-2 flex-shrink-0" />
                  <div>
                    <h4 className="font-medium text-purple-600 dark:text-purple-400 mb-1">音频/字幕：</h4>
                    <p className="text-gray-700 dark:text-gray-300 text-sm leading-relaxed">{item.videoData.audio}</p>
                  </div>
                </div>
                <div className="flex gap-3">
                  <div className="w-2 h-2 rounded-full bg-green-500 mt-2 flex-shrink-0" />
                  <div>
                    <h4 className="font-medium text-green-600 dark:text-green-400 mb-1">场景详述：</h4>
                    <p className="text-gray-700 dark:text-gray-300 text-sm leading-relaxed">{item.videoData.scene}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}


