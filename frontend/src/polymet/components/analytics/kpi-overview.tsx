 
import { TrendingUp, TrendingDown, Minus, Video, Eye, AlertTriangle, Info, TrendingUp as TrendIcon } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

interface KPIData { current: number; previous: number; change: number }
interface PlatformDistribution { 抖音: number; 小红书: number }

export default function KPIOverview({
  data,
  platformDistribution,
  className = "",
  loading = false,
  breakdown,
  onRelevanceClick,
  onSeverityClick,
}: {
  data: { totalVideos: KPIData; relevantVideos: KPIData; highPriorityVideos: KPIData };
  platformDistribution?: { totalVideos: PlatformDistribution; relevantVideos: PlatformDistribution; highPriorityVideos: PlatformDistribution };
  className?: string;
  loading?: boolean;
  breakdown?: {
    totalRelevance?: { 相关: number; 疑似相关: number; 不相关: number; total?: number };
    relevantSeverity?: { 高: { count: number; percentage: number }; 中: { count: number; percentage: number }; 低: { count: number; percentage: number } };
    highCreators?: { 达人: number; 素人: number };
    highPlatforms?: PlatformDistribution;
  };
  onRelevanceClick?: (name: string) => void;
  onSeverityClick?: (severity: string, creatorType?: string) => void;
}) {
  const iconFor = (c: number) => (c > 0 ? <TrendingUp className="w-4 h-4 text-red-500" /> : c < 0 ? <TrendingDown className="w-4 h-4 text-green-500" /> : <Minus className="w-4 h-4 text-gray-500" />);
  const colorFor = (c: number) => (c > 0 ? "text-red-500" : c < 0 ? "text-green-500" : "text-gray-500");
  const PlatformIcons = ({ d }: { d?: PlatformDistribution }) => {
    if (!d) return null;
    return (
      <div className="flex items-center gap-4 mt-2 text-xs">
        <div className="flex items-center gap-1.5"><img src="/douyin.svg" alt="抖音" className="w-3.5 h-3.5" /><span className="text-gray-600 dark:text-gray-400">{d.抖音}</span></div>
        <div className="flex items-center gap-1.5"><img src="/xiaohongshu.svg" alt="小红书" className="w-3.5 h-3.5" /><span className="text-gray-600 dark:text-gray-400">{d.小红书}</span></div>
      </div>
    );
  };
  const cards = [
    { title: "总内容数", icon: <Video className="w-5 h-5 text-blue-600 dark:text-blue-400" />, data: data.totalVideos, bg: "bg-blue-50/50 dark:bg-blue-900/20", border: "border-blue-200/50 dark:border-blue-700/50", dist: platformDistribution?.totalVideos },
    { title: "相关内容", icon: <Eye className="w-5 h-5 text-red-600 dark:text-red-400" />, data: data.relevantVideos, bg: "bg-red-50/50 dark:bg-red-900/20", border: "border-red-200/50 dark:border-red-700/50", dist: platformDistribution?.relevantVideos },
    { title: "高优先级内容", icon: <AlertTriangle className="w-5 h-5 text-purple-600 dark:text-purple-400" />, data: data.highPriorityVideos, bg: "bg-purple-50/50 dark:bg-purple-900/20", border: "border-purple-200/50 dark:border-purple-700/50", dist: platformDistribution?.highPriorityVideos },
  ];
  return (
    <div className={`space-y-4 ${className}`}>
      <h2 className="text-xl font-semibold text-gray-900 dark:text-white">内容分布概览</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {loading && Array.from({ length: 3 }).map((_, i) => (
          <div key={`kpi-skeleton-${i}`} className="p-6 rounded-2xl backdrop-blur-xl border border-white/20 bg-white/10">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <Skeleton className="w-5 h-5 rounded" />
                <Skeleton className="h-5 w-24" />
              </div>
            </div>
            <div className="space-y-3">
              <div className="flex items-end gap-2">
                <Skeleton className="h-8 w-20" />
                <Skeleton className="h-4 w-12" />
              </div>
              <Skeleton className="h-3 w-28" />
              <div className="flex items-center gap-2 mt-2">
                <div className="flex items-center gap-1">
                  <Skeleton className="w-3 h-3 rounded-full" />
                  <Skeleton className="h-3 w-16" />
                </div>
                <div className="flex items-center gap-1">
                  <Skeleton className="w-3 h-3 rounded-full" />
                  <Skeleton className="h-3 w-16" />
                </div>
              </div>
            </div>
          </div>
        ))}
        {!loading && cards.map((c, i) => (
          <div key={i} className={`p-6 rounded-2xl backdrop-blur-xl border ${c.bg} ${c.border} transition-all duration-200 hover:shadow-lg relative`}>
            <div className="flex items-center justify-between mb-4"><div className="flex items-center gap-3">{c.icon}<h3 className="font-medium text-gray-900 dark:text-white">{c.title}</h3></div></div>
            {/* 右侧窄列固定在卡片右上，与标题同高 */}
            <div className="shrink-0 w-24 absolute top-6 right-6">
              {i === 0 && (
                <div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">相关性</div>
                  <div className="space-y-1" aria-label="分类统计">
                    {([
                      { name: "相关", color: "#ef4444" },
                      { name: "疑似相关", color: "#f97316" },
                      { name: "不相关", color: "#6b7280" },
                    ] as const).map((item) => (
                      <div key={item.name} role="button" tabIndex={0} className="group grid grid-cols-[auto_min-content] items-center gap-4 py-0.5 cursor-pointer select-none focus:outline-none" onClick={() => onRelevanceClick?.(item.name)} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onRelevanceClick?.(item.name); }} aria-label={`查看${item.name}详情`}>
                        <div className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-full" style={{ backgroundColor: item.color }} /><span className="text-xs text-gray-700 dark:text-gray-300 group-hover:underline">{item.name}</span></div>
                        <span className="text-xs font-medium text-gray-900 dark:text-white">{breakdown?.totalRelevance?.[item.name as "相关" | "疑似相关" | "不相关"] || 0}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {i === 1 && (
                <div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">优先级</div>
                  <div className="space-y-1" aria-label="严重程度统计">
                    {([
                      { name: "高", icon: <AlertTriangle className="w-3.5 h-3.5 text-red-500" /> },
                      { name: "中", icon: <TrendIcon className="w-3.5 h-3.5 text-orange-500" /> },
                      { name: "低", icon: <Info className="w-3.5 h-3.5 text-green-500" /> },
                    ] as const).map((sev) => (
                      <div key={sev.name} role="button" tabIndex={0} className="group grid grid-cols-[auto_min-content] items-center gap-4 py-0.5 cursor-pointer select-none focus:outline-none" onClick={() => onSeverityClick?.(sev.name)} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onSeverityClick?.(sev.name); }} aria-label={`查看${sev.name}严重度详情`}>
                        <div className="flex items-center gap-1.5">{sev.icon}<span className="text-xs text-gray-700 dark:text-gray-300 group-hover:underline">{sev.name}</span></div>
                        <span className="text-xs font-medium text-gray-900 dark:text-white">{breakdown?.relevantSeverity?.[sev.name as "高" | "中" | "低"].count || 0}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {i === 2 && (
                <div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">作者</div>
                  <div className="space-y-1" aria-label="创作者分布">
                    {[{ name: "达人", color: "#3b82f6" }, { name: "素人", color: "#8b5cf6" }].map((cr) => (
                      <div key={cr.name} role="button" tabIndex={0} className="group grid grid-cols-[auto_min-content] items-center gap-4 py-0.5 cursor-pointer select-none focus:outline-none" onClick={() => onSeverityClick?.("高", cr.name)} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onSeverityClick?.("高", cr.name); }} aria-label={`查看高优先级下${cr.name}详情`}>
                        <div className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-full" style={{ backgroundColor: cr.color }} /><span className="text-xs text-gray-700 dark:text-gray-300 group-hover:underline">{cr.name}</span></div>
                        <span className="text-xs font-medium text-gray-900 dark:text-white">{breakdown?.highCreators?.[cr.name as "达人" | "素人"] || 0}</span>
                      </div>
                    ))}
                  </div>
                  <div className="mt-3">
                    <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">平台</div>
                    <div className="flex items-center gap-4 text-xs">
                      <div className="flex items-center gap-1.5"><img src="/douyin.svg" alt="抖音" className="w-3.5 h-3.5" /><span className="text-gray-600 dark:text-gray-400">{breakdown?.highPlatforms?.抖音 || 0}</span></div>
                      <div className="flex items-center gap-1.5"><img src="/xiaohongshu.svg" alt="小红书" className="w-3.5 h-3.5" /><span className="text-gray-600 dark:text-gray-400">{breakdown?.highPlatforms?.小红书 || 0}</span></div>
                    </div>
                  </div>
                </div>
              )}
            </div>
            <div className="">
              <div className="space-y-2 pr-32">
                <div className="flex items-end gap-2"><span className="text-3xl font-bold text-gray-900 dark:text-white">{c.data.current}</span><div className="flex items-center gap-1 mb-1">{iconFor(c.data.change)}<span className={`text-sm font-medium ${colorFor(c.data.change)}`}>{Math.abs(c.data.change)}%</span></div></div>
                <p className="text-sm text-gray-600 dark:text-gray-400">上一周期: {c.data.previous}</p>
                <PlatformIcons d={c.dist} />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}


