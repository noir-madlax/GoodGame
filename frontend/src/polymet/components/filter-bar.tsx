import React, { useMemo, useState } from "react";
import {
  Search,
  Filter,
  Calendar,
  Tag,
  TrendingUp,
  ChevronDown,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface FilterOption {
  id: string;
  label: string;
  count?: number;
}

export type SentimentValue = "all" | "positive" | "neutral" | "negative";
export type RiskScenario = "all" | string;

interface FilterBarProps {
  className?: string;
  // controlled selections
  riskScenario: RiskScenario;
  channel: string; // platform key or 'all'
  contentType: string; // 'all' | 'video' | 'image'
  timeRange: "all" | "today" | "week" | "month";
  sentiment: SentimentValue;
  onChange: (next: {
    riskScenario?: RiskScenario;
    channel?: string;
    contentType?: string;
    timeRange?: "all" | "today" | "week" | "month";
    sentiment?: SentimentValue;
    search?: string;
  }) => void;
}

export default function FilterBar({ className, riskScenario, channel, contentType, timeRange, sentiment, onChange }: FilterBarProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const openInit: string | null = null;
  const [openMenu, setOpenMenu] = useState<string | null>(openInit);

  const riskFilters: FilterOption[] = [
    { id: "all", label: "风险场景", count: 1250 },
    { id: "pet-entry", label: "宠物进店", count: 45 },
    { id: "food-safety", label: "用餐卫生", count: 32 },
    { id: "food-security", label: "食品安全", count: 28 },
    { id: "env-hygiene", label: "环境卫生", count: 18 },
  ];

  const channelFilters: FilterOption[] = [
    { id: "all", label: "全部渠道", count: 1250 },
    { id: "douyin", label: "抖音", count: 450 },
    { id: "xiaohongshu", label: "小红书", count: 320 },
    { id: "weibo", label: "微博", count: 280 },
  ];

  const typeFilters: FilterOption[] = [
    { id: "all", label: "全部类型", count: 1250 },
    { id: "video", label: "视频", count: 800 },
    { id: "image", label: "图文", count: 350 },
    { id: "text", label: "文本", count: 100 },
  ];

  const timeFilters: FilterOption[] = [
    { id: "all", label: "全部时间", count: 1250 },
    { id: "today", label: "今天", count: 45 },
    { id: "week", label: "本周", count: 230 },
    { id: "month", label: "本月", count: 680 },
  ];

  const FilterDropdown = ({
    options,
    icon,
    value,
    onSelect,
    menuId,
  }: {
    options: FilterOption[];
    icon: React.ReactNode;
    value: string;
    menuId: string;
    onSelect: (id: string) => void;
  }) => {
    const isOpen = openMenu === menuId;
    const selected = useMemo(() => options.find(o => o.id === value) || options[0], [options, value]);

    return (
      <div className="relative">
        <button
          onClick={() => setOpenMenu(isOpen ? null : menuId)}
          className={cn(
            "flex items-center space-x-2 px-4 py-2 rounded-xl",
            "bg-white/10 backdrop-blur-xl border border-white/20",
            "hover:bg-white/20 hover:border-white/30 transition-all duration-300",
            "shadow-lg hover:shadow-xl"
          )}
        >
          <div className="text-gray-600 dark:text-gray-300">{icon}</div>
          <span className="text-sm font-medium text-gray-700 dark:text-gray-200">
            {selected.label}
          </span>
          <ChevronDown
            className={cn(
              "w-4 h-4 text-gray-500 transition-transform duration-200",
              isOpen && "rotate-180"
            )}
          />
        </button>

        {isOpen && (
          <div className="absolute top-full left-0 mt-2 w-48 rounded-xl bg-white/95 dark:bg-gray-800/95 backdrop-blur-xl border border-white/20 shadow-2xl z-50">
            <div className="p-2 space-y-1">
              {options.map((option) => (
                <button
                  key={option.id}
                  onClick={() => {
                    onSelect(option.id);
                    setOpenMenu(null);
                  }}
                  className={cn(
                    "w-full flex items-center justify-between px-3 py-2 rounded-lg",
                    "hover:bg-blue-500/10 hover:text-blue-600 dark:hover:text-blue-400",
                    "transition-all duration-200",
                    selected.id === option.id &&
                      "bg-blue-500/20 text-blue-600 dark:text-blue-400"
                  )}
                >
                  <span className="text-sm font-medium">{option.label}</span>
                  {option.count && (
                    <span className="text-xs text-gray-500 dark:text-gray-400 bg-gray-100/50 dark:bg-gray-700/50 px-2 py-1 rounded-full">
                      {option.count.toLocaleString()}
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div
      className={cn(
        "p-6 rounded-2xl bg-white/10 backdrop-blur-xl border border-white/20",
        "shadow-xl shadow-black/5",
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">
          舆情内容监控
        </h2>
        <button
          onClick={() => {
            onChange({ riskScenario: "all", channel: "all", contentType: "all", timeRange: "all", sentiment: "all", search: "" });
            setSearchQuery("");
          }}
          className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-gradient-to-r from-blue-500 to-purple-600 text-white font-medium hover:from-blue-600 hover:to-purple-700 transition-all duration-300 hover:scale-105 shadow-lg"
        >
          <TrendingUp className="w-4 h-4" />

          <span>重置筛选</span>
        </button>
      </div>

      {/* Search Bar */}
      <div className="relative mb-6">
        <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />

        <input
          type="text"
          placeholder="搜索关键词、话题或内容..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className={cn(
            "w-full pl-12 pr-4 py-3 rounded-xl",
            "bg-white/10 backdrop-blur-xl border border-white/20",
            "placeholder-gray-400 text-gray-900 dark:text-white",
            "focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50",
            "hover:bg-white/15 transition-all duration-300"
          )}
        />
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4">
        <FilterDropdown
          options={riskFilters}
          icon={<Tag className="w-4 h-4" />}
          value={riskScenario}
          menuId="risk"
          onSelect={(id) => onChange({ riskScenario: id })}
        />

        <FilterDropdown
          options={channelFilters}
          icon={<Filter className="w-4 h-4" />}
          value={channel}
          menuId="channel"
          onSelect={(id) => onChange({ channel: id })}
        />

        <FilterDropdown
          options={typeFilters}
          icon={<Filter className="w-4 h-4" />}
          value={contentType}
          menuId="type"
          onSelect={(id) => onChange({ contentType: id })}
        />

        <FilterDropdown
          options={timeFilters}
          icon={<Calendar className="w-4 h-4" />}
          value={timeRange}
          menuId="time"
          onSelect={(id) => onChange({ timeRange: id as any })}
        />

        <FilterDropdown
          options={[{ id: "all", label: "全部情绪" }, { id: "positive", label: "正向" }, { id: "neutral", label: "中立" }, { id: "negative", label: "负面" }]}
          icon={<Filter className="w-4 h-4" />}
          value={sentiment}
          menuId="sentiment"
          onSelect={(id) => onChange({ sentiment: id as any })}
        />
      </div>
    </div>
  );
}
