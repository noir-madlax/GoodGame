import React from "react";
import { TrendingUp, AlertTriangle, Clock, Target } from "lucide-react";
import { cn } from "@/lib/utils";

interface AnalysisItem {
  id: string;
  type: "trend" | "alert" | "insight" | "recommendation";
  title: string;
  description: string;
  timestamp?: string;
  severity?: "low" | "medium" | "high";
}

interface AnalysisSectionProps {
  title: string;
  icon: React.ReactNode;
  items: AnalysisItem[];
  className?: string;
}

export default function AnalysisSection({
  title,
  icon,
  items,
  className,
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
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-xl bg-gradient-to-br from-blue-500/20 to-purple-600/20 backdrop-blur-sm">
            {icon}
          </div>
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">
            {title}
          </h3>
        </div>
      </div>

      {/* Content */}
      <div className="p-6 space-y-4">
        {items.map((item, index) => (
          <div
            key={item.id}
            className="group p-4 rounded-xl bg-white/5 backdrop-blur-sm border border-white/10 hover:bg-white/10 hover:border-white/20 transition-all duration-300"
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
                  {item.timestamp && (
                    <span className="text-xs text-gray-500 dark:text-gray-400 bg-gray-100/50 dark:bg-gray-800/50 px-2 py-1 rounded-full">
                      {item.timestamp}
                    </span>
                  )}
                </div>
                <p className="text-gray-600 dark:text-gray-300 text-sm leading-relaxed">
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
