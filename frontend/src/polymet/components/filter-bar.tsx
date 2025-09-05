import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  Search,
  Filter,
  Calendar,
  Tag,
  TrendingUp,
  ChevronDown,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { supabase } from "@/lib/supabase";
import { fetchGlobalFilterEnums } from "@/polymet/lib/filters";

interface FilterOption {
  id: string;
  label: string;
  count?: number;
}

export type SentimentValue = "all" | "positive" | "neutral" | "negative";
export type RiskScenario = "all" | string;
export type RelevanceValue = string;

interface FilterBarProps {
  className?: string;
  // controlled selections
  riskScenario: RiskScenario;
  channel: string; // platform key or 'all'
  contentType: string; // 'all' | 'video' | 'image'
  timeRange: "all" | "today" | "week" | "month";
  sentiment: SentimentValue;
  relevance: RelevanceValue;
  riskOptions?: { id: string; label: string; count: number }[]; // optional external override
  channelOptions?: { id: string; label: string; count?: number }[]; // optional external override
  typeOptions?: { id: string; label: string; count?: number }[]; // optional external override
  sentimentOptions?: { id: SentimentValue; label: string }[]; // optional external override
  relevanceOptions?: { id: string; label: string }[]; // optional external override
  onChange: (next: {
    riskScenario?: RiskScenario;
    channel?: string;
    contentType?: string;
    timeRange?: "all" | "today" | "week" | "month";
    sentiment?: SentimentValue;
    relevance?: RelevanceValue;
    search?: string;
  }) => void;
}

export default function FilterBar({ className, riskScenario, channel, contentType, timeRange, sentiment, relevance, riskOptions, channelOptions, typeOptions, sentimentOptions, relevanceOptions, onChange }: FilterBarProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const openInit: string | null = null;
  const [openMenu, setOpenMenu] = useState<string | null>(openInit);

  // Local enum options loaded from gg_filter_enums when not provided by parent
  const [enumLoaded, setEnumLoaded] = useState(false);
  const [enumChannels, setEnumChannels] = useState<FilterOption[]>([]);
  const [enumTypes, setEnumTypes] = useState<FilterOption[]>([]);
  const [enumSentiments, setEnumSentiments] = useState<{ id: SentimentValue; label: string }[]>([]);
  const [enumRelevances, setEnumRelevances] = useState<FilterOption[]>([]);
  const [enumRisks, setEnumRisks] = useState<{ id: string; label: string; count: number }[]>([]);

  useEffect(() => {
    let cancelled = false;
    const loadEnums = async () => {
      try {
        if (!supabase) return;
        const { channels, types, sentiments, relevances, risks } = await fetchGlobalFilterEnums(supabase);
        if (!cancelled) {
          setEnumChannels(channels);
          setEnumTypes(types);
          setEnumSentiments(sentiments as { id: SentimentValue; label: string }[]);
          setEnumRelevances(relevances);
          setEnumRisks(risks as { id: string; label: string; count: number }[]);
          setEnumLoaded(true);
        }
      } finally {
        // no-op
      }
    };
    // only load if parent did not provide options
    if (!riskOptions && !channelOptions && !typeOptions && !sentimentOptions && !relevanceOptions) {
      loadEnums();
    }
    return () => { cancelled = true; };
  }, [riskOptions, channelOptions, typeOptions, sentimentOptions, relevanceOptions]);

  const riskFilters: FilterOption[] = useMemo(() => {
    if (riskOptions && riskOptions.length > 0) return riskOptions;
    if (enumLoaded) return enumRisks;
    return [{ id: "all", label: "全部场景", count: 0 }];
  }, [riskOptions, enumLoaded, enumRisks]);

  const channelFilters: FilterOption[] = useMemo(() => {
    if (channelOptions && channelOptions.length > 0) return channelOptions as FilterOption[];
    if (enumLoaded) return enumChannels;
    return [{ id: "all", label: "全部渠道" }];
  }, [channelOptions, enumLoaded, enumChannels]);

  const typeFilters: FilterOption[] = useMemo(() => {
    if (typeOptions && typeOptions.length > 0) return typeOptions as FilterOption[];
    if (enumLoaded) return enumTypes;
    return [{ id: "all", label: "全部类型" }];
  }, [typeOptions, enumLoaded, enumTypes]);

  const relevanceFilters: FilterOption[] = useMemo(() => {
    if (relevanceOptions && relevanceOptions.length > 0) return relevanceOptions as FilterOption[];
    if (enumLoaded) return enumRelevances;
    return [{ id: "all", label: "全部相关性" }];
  }, [relevanceOptions, enumLoaded, enumRelevances]);

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
    const btnRef = useRef<HTMLButtonElement | null>(null);
    const menuRef = useRef<HTMLDivElement | null>(null);

    useEffect(() => {
      const handleDown = (e: MouseEvent) => {
        if (!isOpen) return;
        const target = e.target as Node;
        if (btnRef.current?.contains(target)) return;
        if (menuRef.current?.contains(target)) return;
        setOpenMenu(null);
      };
      const handleKey = (e: KeyboardEvent) => {
        if (!isOpen) return;
        if (e.key === "Escape") setOpenMenu(null);
      };
      document.addEventListener("mousedown", handleDown);
      document.addEventListener("keydown", handleKey);
      return () => {
        document.removeEventListener("mousedown", handleDown);
        document.removeEventListener("keydown", handleKey);
      };
    }, [isOpen]);

    return (
      <div className="relative">
        <button
          ref={btnRef}
          onClick={() => setOpenMenu(isOpen ? null : menuId)}
          className={cn(
            "flex items-center space-x-2 px-4 py-2 rounded-xl",
            "bg-white/10 backdrop-blur-xl border",
            selected.id !== "all" ? "border-blue-400/60 text-blue-600 dark:text-blue-400" : "border-white/20",
            "hover:bg-white/20 hover:border-white/30 transition-all duration-300",
            "shadow-lg hover:shadow-xl"
          )}
          disabled={!enumLoaded && !options?.length}
        >
          <div className="text-gray-600 dark:text-gray-300">{icon}</div>
          <span className={cn(
            "text-sm font-medium flex items-center gap-2",
            selected.id !== "all" ? "text-blue-600 dark:text-blue-400" : "text-gray-700 dark:text-gray-200"
          )}>
            {(!enumLoaded && !options?.length) ? (
              <span className="inline-block h-3 w-10 bg-gray-300/50 dark:bg-gray-600/50 rounded animate-pulse" />
            ) : (
              selected.label
            )}
          </span>
          <ChevronDown
            className={cn(
              "w-4 h-4 text-gray-500 transition-transform duration-200",
              isOpen && "rotate-180"
            )}
          />
        </button>

        {isOpen && (
          <div
            ref={menuRef}
            className="absolute top-full left-0 mt-2 w-48 rounded-xl bg-white/95 dark:bg-gray-800/95 backdrop-blur-xl border border-white/20 shadow-2xl z-[3000]"
          >
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
        "shadow-xl shadow-black/5 relative z-[2500]",
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
          placeholder="搜索标题或者作者"
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
          options={relevanceFilters}
          icon={<Filter className="w-4 h-4" />}
          value={relevance}
          menuId="relevance"
          onSelect={(id) => onChange({ relevance: id })}
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
          onSelect={(id) => onChange({ timeRange: id as "all" | "today" | "week" | "month" })}
        />

        <FilterDropdown
          options={(sentimentOptions && sentimentOptions.length > 0
            ? (sentimentOptions as unknown as FilterOption[])
            : (enumLoaded ? (enumSentiments as unknown as FilterOption[]) : ([{ id: "all", label: "全部情绪" }] as FilterOption[])))}
          icon={<Filter className="w-4 h-4" />}
          value={sentiment}
          menuId="sentiment"
          onSelect={(id) => onChange({ sentiment: id as SentimentValue })}
        />
      </div>
    </div>
  );
}
