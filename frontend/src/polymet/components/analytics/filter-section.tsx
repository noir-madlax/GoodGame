import React from "react"; // 保留默认导入以兼容可能的 JSX 运行时配置
import { ChevronDown, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuCheckboxItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";

export interface FiltersState {
  timeRange: "今天" | "近2天" | "近3天" | "近7天" | "近15天" | "近30天" | "全部时间";
  relevance: string[]; // 相关/疑似相关/不相关/营销
  priority: string[]; // 高/中/低/未标注
  creatorTypes: string[]; // 达人/素人/未标注
  platforms: string[]; // 抖音/小红书
  customTimeRange?: { start: string; end: string };
}

interface Props {
  filters: FiltersState;
  onFiltersChange: (next: FiltersState) => void;
  className?: string;
  headerRight?: React.ReactNode;
  // 新增：当点击“重置筛选”时的额外回调（用于页面级同步重置图表联动等）
  onResetAll?: () => void;
}

// 说明：此组件从 sample 代码移植，并小幅调整时间枚举与默认态；作为首页顶层数据范围控制器。
export default function FilterSection({ filters, onFiltersChange, className = "", headerRight, onResetAll }: Props) {
  const isFilterActive = (filterArray: string[], filterType: string) => {
    if (filterType === "timeRange") return filters.timeRange !== "全部时间"; // 全部时间视为未激活
    return filterArray && filterArray.length > 0;
  };

  const getFilterDisplayText = (arr: string[], fallback: string) => {
    if (!arr || arr.length === 0) return fallback;
    if (arr.length === 1) return arr[0];
    return `${arr[0]} 等${arr.length}项`;
  };

  const timeRangeOptions = ["今天", "近2天", "近3天", "近7天", "近15天", "近30天", "全部时间"] as const;
  const platformOptions = ["抖音", "小红书"];

  const handleTimeRangeSelect = (timeRange: FiltersState["timeRange"]) => {
    onFiltersChange({ ...filters, timeRange });
  };

  const handleMulti = (key: keyof FiltersState, value: string, checked: boolean) => {
    const curr = (filters[key] as string[]) || [];
    const next = checked ? [...curr, value] : curr.filter((v) => v !== value);
    onFiltersChange({ ...filters, [key]: next } as FiltersState);
  };

  const handleReset = () => {
    onFiltersChange({ timeRange: "全部时间", relevance: [], priority: [], creatorTypes: [], platforms: [] });
    // 通知父级同时重置其它与筛选联动的页面状态（例如图表联动层级）
    onResetAll?.();
  };

  return (
    <div className={`space-y-4 ${className}`}>
      <div className="flex items-center gap-10 ">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">内容筛选</h2>
        <div className="ml-auto flex items-center">{headerRight}</div>
      </div>

      <div className="flex flex-wrap gap-3">
        {/* 时间范围 */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="outline"
              className={`h-10 px-4 ${isFilterActive([], "timeRange") ? "bg-blue-100 border-blue-300 text-blue-700 hover:bg-blue-200" : "bg-white/10 backdrop-blur-xl border-white/20 text-gray-900 dark:text-white hover:bg-white/20"}`}
            >
              {filters.timeRange}
              <ChevronDown className="w-4 h-4 ml-2" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-48">
            {timeRangeOptions.map((opt) => (
              <DropdownMenuCheckboxItem key={opt} checked={filters.timeRange === opt} onCheckedChange={() => handleTimeRangeSelect(opt)}>
                {opt}
              </DropdownMenuCheckboxItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>

        {/* 相关性 
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="outline"
              className={`h-10 px-4 ${isFilterActive(filters.relevance, "relevance") ? "bg-blue-100 border-blue-300 text-blue-700 hover:bg-blue-200" : "bg-white/10 backdrop-blur-xl border-white/20 text-gray-900 dark:text-white hover:bg-white/20"}`}
            >
              {getFilterDisplayText(filters.relevance, "全部相关性")}
              <ChevronDown className="w-4 h-4 ml-2" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-48">
            {relevanceOptions.map((opt) => (
              <DropdownMenuCheckboxItem key={opt} checked={filters.relevance.includes(opt)} onCheckedChange={(c) => handleMulti("relevance", opt, c)}>
                {opt}
              </DropdownMenuCheckboxItem>
            ))}
            {filters.relevance.length > 0 && (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuCheckboxItem checked={false} onCheckedChange={() => onFiltersChange({ ...filters, relevance: [] })}>
                  <X className="w-3 h-3 mr-2" />清除选择
                </DropdownMenuCheckboxItem>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>

        {/* 优先级 
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="outline"
              className={`h-10 px-4 ${isFilterActive(filters.priority, "priority") ? "bg-blue-100 border-blue-300 text-blue-700 hover:bg-blue-200" : "bg-white/10 backdrop-blur-xl border-white/20 text-gray-900 dark:text-white hover:bg-white/20"}`}
            >
              {getFilterDisplayText(filters.priority, "全部优先级")}
              <ChevronDown className="w-4 h-4 ml-2" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-48">
            {priorityOptions.map((opt) => (
              <DropdownMenuCheckboxItem key={opt} checked={filters.priority.includes(opt)} onCheckedChange={(c) => handleMulti("priority", opt, c)}>
                {opt}
              </DropdownMenuCheckboxItem>
            ))}
            {filters.priority.length > 0 && (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuCheckboxItem checked={false} onCheckedChange={() => onFiltersChange({ ...filters, priority: [] })}>
                  <X className="w-3 h-3 mr-2" />清除选择
                </DropdownMenuCheckboxItem>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>

        {/* 作者类型 
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="outline"
              className={`h-10 px-4 ${isFilterActive(filters.creatorTypes, "creatorTypes") ? "bg-blue-100 border-blue-300 text-blue-700 hover:bg-blue-200" : "bg-white/10 backdrop-blur-xl border-white/20 text-gray-900 dark:text-white hover:bg-white/20"}`}
            >
              {getFilterDisplayText(filters.creatorTypes, "全部作者")}
              <ChevronDown className="w-4 h-4 ml-2" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-48">
            {creatorTypeOptions.map((opt) => (
              <DropdownMenuCheckboxItem key={opt} checked={filters.creatorTypes.includes(opt)} onCheckedChange={(c) => handleMulti("creatorTypes", opt, c)}>
                {opt}
              </DropdownMenuCheckboxItem>
            ))}
            {filters.creatorTypes.length > 0 && (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuCheckboxItem checked={false} onCheckedChange={() => onFiltersChange({ ...filters, creatorTypes: [] })}>
                  <X className="w-3 h-3 mr-2" />清除选择
                </DropdownMenuCheckboxItem>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>

        {/* 平台 */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="outline"
              className={`h-10 px-4 ${isFilterActive(filters.platforms, "platforms") ? "bg-blue-100 border-blue-300 text-blue-700 hover:bg-blue-200" : "bg-white/10 backdrop-blur-xl border-white/20 text-gray-900 dark:text-white hover:bg-white/20"}`}
            >
              {getFilterDisplayText(filters.platforms, "全部平台")}
              <ChevronDown className="w-4 h-4 ml-2" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-48">
            {platformOptions.map((opt) => (
              <DropdownMenuCheckboxItem key={opt} checked={filters.platforms.includes(opt)} onCheckedChange={(c) => handleMulti("platforms", opt, c)}>
                {opt}
              </DropdownMenuCheckboxItem>
            ))}
            {filters.platforms.length > 0 && (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuCheckboxItem checked={false} onCheckedChange={() => onFiltersChange({ ...filters, platforms: [] })}>
                  <X className="w-3 h-3 mr-2" />清除选择
                </DropdownMenuCheckboxItem>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
        <span
          role="button"
          tabIndex={0}
          aria-label="重置筛选"
          onClick={handleReset}
          onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") handleReset(); }}
          className="text-xs mt-4 text-gray-500 hover:text-gray-900 cursor-pointer select-none"
        >
          重置筛选
        </span>
      </div>
    </div>
  );
}


