import React from "react";
import { User } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import parseEmojiAliases from "@/polymet/lib/emoji";

/**
 * 评论分析组件（用于详情页底部 Tab）
 * 需求要点：
 * - 不展示风险等级胶囊。
 * - 右侧展示风险标签（若有）。
 * - 支持空态：无数据时显示“原内容无评论”。
 */

export interface CommentAnalysisItem {
  id: string; // 占位/自增
  timestamp?: string; // 可选
  riskBadges: string[]; // 风险标签，可为空
  commentData: {
    id: string; // 占位显示
    author: string;
    overview: string; // 概述（可用评论文本）
    audio?: string; // 无则空（不展示）
    scene?: string; // 无则空
  };
  snippet?: string; // 用于外部定位原内容
}

interface CommentsAnalysisProps {
  items: CommentAnalysisItem[];
  className?: string;
  onViewSource?: (item: CommentAnalysisItem) => void;
}

export default function CommentsAnalysis({ items, className = "", onViewSource }: CommentsAnalysisProps) {
  if (!items || items.length === 0) {
    return (
      <div className={cn("p-6 rounded-2xl bg-white/10 backdrop-blur-xl border border-white/20 text-sm text-gray-600 dark:text-gray-300", className)}>
        原内容无评论
      </div>
    );
  }

  return (
    <div className={cn("space-y-4", className)}>
      {items.map((item) => (
        <div key={item.id} className="group p-6 rounded-2xl bg-white/5 backdrop-blur-xl border border-white/10 hover:bg-white/10 hover:border-white/20 shadow-lg shadow-black/5 hover:shadow-2xl hover:shadow-black/15 transition-all duration-300">
          {/* 抬头：用户名 + 悬浮操作 + 风险标签 */}
          <div className="flex items-start justify-between mb-3">
            <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
              <User className="w-4 h-4" />
              <span>用户名：{item.commentData.author || "用户"}</span>
              {onViewSource && (
                <div className="ml-2">
                  <button
                    className="px-3 py-1.5 rounded-lg text-xs bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/30 hover:bg-blue-500/15 transition opacity-0 group-hover:opacity-100"
                    onClick={() => onViewSource(item)}
                    style={{ marginRight: "4px" }}
                  >
                    查看原始内容
                  </button>
                </div>
              )}
            </div>
            <div className="flex flex-wrap gap-2">
              {(item.riskBadges || []).map((badge, i) => (
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

          {/* 三段内容 */}
          <div className="space-y-4">
            <div className="flex gap-3">
              <div className="w-2 h-2 rounded-full bg-blue-500 mt-2 flex-shrink-0" />
              <div>
                <h4 className="font-medium text-blue-600 dark:text-blue-400 mb-1">问题概述：</h4>
                <p className="text-gray-800 dark:text-gray-200 leading-relaxed">{parseEmojiAliases(String(item.commentData.overview || ""))}</p>
              </div>
            </div>
            <div className="flex gap-3">
              <div className="w-2 h-2 rounded-full bg-purple-500 mt-2 flex-shrink-0" />
              <div>
                <h4 className="font-medium text-purple-600 dark:text-purple-400 mb-1">场景详述：</h4>
                <p className="text-gray-800 dark:text-gray-200 leading-relaxed">{parseEmojiAliases(String(item.commentData.scene || ""))}</p>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}


