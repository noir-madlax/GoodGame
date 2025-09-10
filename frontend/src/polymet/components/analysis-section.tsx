import React from "react";
import { TrendingUp, AlertTriangle, Clock, Target } from "lucide-react";
import { cn } from "@/lib/utils";
// import { Badge } from "@/components/ui/badge";
import { RiskBadge } from "@/components/ui/risk-badge";

interface AnalysisItem {
  id: string;
  type: "trend" | "alert" | "insight" | "recommendation";
  title: string;
  description: string;
  timestamp?: string;
  severity?: "low" | "medium" | "high";
  riskBadges?: string[];
  _ts?: string; // 可选：用于外部锚点定位（例如 mm:ss）
}

interface AnalysisSectionProps {
  title: string;
  icon: React.ReactNode;
  items: AnalysisItem[];
  className?: string;
  onItemClick?: (index: number) => void; // 可选：点击项回调
  renderItemAction?: (index: number) => React.ReactNode; // 可选：悬浮操作（右上角）
  headerRight?: React.ReactNode; // 可选：标题右侧操作
}

export default function AnalysisSection({
  title,
  icon,
  items,
  className,
  onItemClick,
  renderItemAction,
  headerRight,
}: AnalysisSectionProps) {
  const getTypeIcon = (type: AnalysisItem["type"]) => {
    switch (type) {
      case "trend":
        return <TrendingUp className="w-4 h-4" />;

      case "alert":
        return <AlertTriangle className="w-4 h-4" />;

      case "insight":
        return <Target className="w-4 h-4" />;

      default:
        return <Clock className="w-4 h-4" />;
    }
  };

  const getTypeColor = (type: AnalysisItem["type"], severity?: string) => {
    switch (type) {
      case "trend":
        return "text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900/30";
      case "alert":
        return severity === "high"
          ? "text-red-600 bg-red-100 dark:text-red-400 dark:bg-red-900/30"
          : "text-orange-600 bg-orange-100 dark:text-orange-400 dark:bg-orange-900/30";
      case "insight":
        return "text-blue-600 bg-blue-100 dark:text-blue-400 dark:bg-blue-900/30";
      default:
        return "text-purple-600 bg-purple-100 dark:text-purple-400 dark:bg-purple-900/30";
    }
  };

  return (
    <div
      className={cn(
        "rounded-2xl bg-white/10 backdrop-blur-xl border border-white/20",
        "shadow-xl shadow-black/5 hover:shadow-2xl hover:shadow-black/10 transition-all duration-500",
        "hover:bg-white/15",
        className
      )}
    >
      {/* Header */}
      <div className="p-6 border-b border-white/10">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-xl bg-gradient-to-br from-blue-500/20 to-purple-600/20 backdrop-blur-sm">
              {icon}
            </div>
            <h3 className="text-xl font-bold text-gray-900 dark:text-white">
              {title}
            </h3>
          </div>
          {headerRight ? <div className="flex items-center">{headerRight}</div> : null}
        </div>
      </div>

      {/* Content */}
      <div className="p-6 space-y-4">
        {items.map((item, idx) => (
          <div
            key={item.id}
            className="group p-4 rounded-xl bg-white/5 backdrop-blur-sm border border-white/10 hover:bg-white/10 hover:border-white/20 transition-all duration-500 shadow-lg shadow-black/5 hover:shadow-2xl hover:shadow-black/15 hover:scale-[1.02]"
            role={onItemClick ? "button" : undefined}
            tabIndex={onItemClick ? 0 : -1}
            onClick={() => onItemClick?.(idx)}
            onKeyDown={(e) => {
              if (!onItemClick) return;
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onItemClick(idx);
              }
            }}
          >
            <div className="flex items-start space-x-3">
              {/* Type Icon */}
              <div
                className={cn(
                  "p-2 rounded-lg flex items-center justify-center",
                  getTypeColor(item.type, item.severity)
                )}
              >
                {getTypeIcon(item.type)}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-semibold text-gray-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors duration-200">
                    {item.title}
                  </h4>
                  <div className="flex items-center gap-2 flex-wrap justify-end">
                    {renderItemAction && (
                      <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                        {renderItemAction(idx)}
                      </div>
                    )}
                    {(item.riskBadges || []).map((rb, i) => (
                      <RiskBadge
                        key={`${rb}-${i}`}
                        label={rb}
                        severity={rb === "宠物进店" ? "high" : "medium"}
                        size="lg"
                      />
                    ))}
                  </div>
                </div>
                <p className="text-gray-600 dark:text-gray-300 text-sm leading-relaxed whitespace-pre-line">
                  {item.description}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
