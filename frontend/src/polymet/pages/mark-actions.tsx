import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { cn } from "@/lib/utils";
import { supabase } from "@/lib/supabase";
import { useProject } from "@/polymet/lib/project-context";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * 中文说明：
 * 页面：`/marks` 内容标记和处理
 * 作用：聚合数据库中的“已标记内容”，并展示处理状态。已移除对 localStorage 的依赖。
 * 使用位置：左侧导航 `内容标记和处理`
 */

type MarkItem = {
  id?: number | null;
  platform_item_id?: string | null;
  title?: string;
  platform?: string;
  created_at: string;
  // 捕获日期：数据库 created_at
  // 发布日期：数据库 published_at
  published_at?: string | null;
};

// 兼容历史：已移除本地 advices 的读取

// 已删除本地读取工具

// 迷你折线图（mock）：用于展示“热度趋势”
const Sparkline: React.FC<{ values: number[]; color?: string; width?: number; height?: number }> = ({ values, color = "#3b82f6", width = 120, height = 32 }) => {
  if (!values || values.length === 0) return <svg width={width} height={height} />;
  const max = Math.max(...values);
  const min = Math.min(...values);
  const range = Math.max(1, max - min);
  const step = width / Math.max(1, values.length - 1);
  const points = values
    .map((v, i) => {
      const x = i * step;
      const y = height - ((v - min) / range) * (height - 2) - 1;
      return `${x},${y}`;
    })
    .join(" ");
  return (
    <svg width={width} height={height} className="overflow-visible">
      <polyline fill="none" stroke={color} strokeWidth="2" points={points} />
    </svg>
  );
};

export default function MarkActionsPage() {
  const navigate = useNavigate();
  // 合并后的单一数据列表：包含标记内容与处理建议两种来源
  const [marks, setMarks] = useState<MarkItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const { activeProjectId } = useProject();
  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      try {
        if (!supabase) return;
        const { data } = await supabase
          .from("gg_platform_post")
          .select("id, platform_item_id, title, platform, created_at, published_at, is_marked, process_status")
          .eq("project_id", activeProjectId || null)
          .eq("is_marked", true)
          .order("id", { ascending: false })
          .limit(200);
        if (!cancelled) {
          type Row = { id: number; platform_item_id: string; title: string; platform: string; created_at: string; published_at?: string | null };
          const rows = (data || []).map((r: Row) => ({
            id: r.id,
            platform_item_id: r.platform_item_id,
            title: r.title,
            platform: r.platform,
            created_at: r.created_at,
            published_at: r.published_at ?? null,
          })) as MarkItem[];
          setMarks(rows);
        }
      } catch (e) {
        // 忽略加载错误，保留空列表
        console.error(e);
      }
      finally {
        if (!cancelled) setLoading(false);
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [activeProjectId]);

  // 合并两类来源为单一渲染行，并计算热度趋势与日/周变化
  const rows = useMemo(() => {
    const unique = marks;
    return unique.map((item, index) => {
      // 四种不同的 mock 形态：上升、波动、峰值、下降
      const variant = index % 4; // 0..3
      const baseLen = 14;
      let heat: number[] = [];

      if (variant === 0) {
        // 渐进上升型
        heat = Array.from({ length: baseLen }, (_, i) => 10 + i * 6 + (i % 3 === 0 ? 8 : 0));
      } else if (variant === 1) {
        // 高波动型
        heat = Array.from({ length: baseLen }, (_, i) => 60 + Math.round(Math.sin(i * 1.2) * 35) + (i % 2 === 0 ? 12 : -8));
      } else if (variant === 2) {
        // 中段峰值型
        heat = Array.from({ length: baseLen }, (_, i) => {
          const peak = 7;
          const dist = Math.abs(i - peak);
          return 40 + Math.max(0, 70 - dist * 12) + (i % 4 === 0 ? 6 : 0);
        });
      } else {
        // 逐步下降型
        heat = Array.from({ length: baseLen }, (_, i) => 120 - i * 7 + (i % 3 === 0 ? 5 : -3));
      }
      const len = heat.length;
      const dayDelta = len >= 2 ? heat[len - 1] - heat[len - 2] : 0;
      const weekDelta = len >= 8 ? heat[len - 1] - heat[len - 8] : dayDelta;
      // 状态：直接使用数据库的 process_status；若为空显示“已标记”
      const status = (item as any).process_status || "已标记";
      return { item, heat, dayDelta, weekDelta, status };
    });
  }, [marks]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">标记内容与处理</h2>
          </div>
        </div>
      </div>

      <div className="p-4 rounded-2xl bg-white/10 backdrop-blur-xl border border-white/20 shadow-xl">
        {loading ? (
          <div className="space-y-4">
            {/* 表头占位 */}
            <div className="flex items-center justify-between px-3">
              <Skeleton className="h-5 w-24" />
              <Skeleton className="h-5 w-20" />
              <Skeleton className="h-5 w-20" />
              <Skeleton className="h-5 w-40" />
              <Skeleton className="h-5 w-16" />
              <Skeleton className="h-5 w-24" />
            </div>
            {/* 行占位，更贴近实际行样式，减少小块数量 */}
            {Array.from({ length: 5 }).map((_, i) => (
              <div
                key={i}
                className="flex items-center gap-4 p-3 rounded-xl bg-white/5 border border-white/10"
              >
                <div className="w-[22%]">
                  <Skeleton className="h-4 w-3/4 mb-2" />
                  <Skeleton className="h-3 w-1/2" />
                </div>
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-4 flex-1" />
                <Skeleton className="h-6 w-16 rounded-full" />
                <div className="flex gap-2 w-[160px] justify-end">
                  <Skeleton className="h-7 w-16 rounded-lg" />
                  <Skeleton className="h-7 w-16 rounded-lg" />
                </div>
              </div>
            ))}
          </div>
        ) : rows.length === 0 ? (
          <div className="text-center text-gray-500 py-16">暂无数据</div>
        ) : (
          <div className="overflow-auto">
            <table className="min-w-full text-sm">
              <thead className="sticky top-0 bg-white/5">
                <tr className="text-left text-gray-600 dark:text-gray-300">
                  <th className="px-3 py-2 w-[22%]">标题/ID</th>
                  <th className="px-3 py-2 whitespace-nowrap">舆情生成日期</th>
                  <th className="px-3 py-2 whitespace-nowrap">捕获日期</th>
                  <th className="px-3 py-2">热度趋势</th>
                  <th className="px-3 py-2 whitespace-nowrap w-[120px]">状态</th>
                  <th className="px-3 py-2 text-right whitespace-nowrap">操作</th>
                </tr>
              </thead>
              <tbody>
                {rows.map(({ item, heat, dayDelta, weekDelta, status }, idx) => (
                  <tr key={idx} className="border-t border-white/10 hover:bg-white/5">
                    <td className="px-3 py-3">
                      <div className="font-medium text-gray-900 dark:text-white line-clamp-1">{item.title || item.platform_item_id}</div>
                      <div className="text-xs text-gray-500 mt-1">{item.platform_item_id || item.id}</div>
                    </td>
                    <td className="px-3 py-3 text-gray-600 dark:text-gray-400 whitespace-nowrap">{item.published_at ? String(item.published_at).slice(0,10) : "-"}</td>
                    <td className="px-3 py-3 text-gray-600 dark:text-gray-400 whitespace-nowrap">{item.created_at ? String(item.created_at).slice(0,10) : "-"}</td>
                    <td className="px-3 py-3">
                      <div className="flex items-center gap-4">
                        <Sparkline values={heat} color="#22c55e" />
                        <div className="text-xs text-gray-600 dark:text-gray-300 whitespace-nowrap">
                          日变化 <span className={cn(dayDelta >= 0 ? "text-green-600" : "text-red-500")}>{dayDelta >= 0 ? `+${dayDelta}` : dayDelta}</span>
                          <span className="mx-2">/</span>
                          周变化 <span className={cn(weekDelta >= 0 ? "text-green-600" : "text-red-500")}>{weekDelta >= 0 ? `+${weekDelta}` : weekDelta}</span>
                        </div>
                      </div>
                    </td>
                    <td className="px-3 py-3 whitespace-nowrap">
                      <span className={cn(
                        "inline-flex items-center px-2 py-1 rounded-full text-xs",
                        status === "有建议" && "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300",
                        status === "已标记" && "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
                      )}>{status}</span>
                    </td>
                    <td className="px-3 py-3 whitespace-nowrap">
                      <div className="flex items-center gap-2 justify-end whitespace-nowrap">
                        <button
                          className="px-3 py-1 rounded-lg text-xs border border-blue-500/30 text-blue-600 hover:bg-blue-500/10"
                          onClick={() => navigate(`/detail/${item.id}`)}
                          aria-label="内容分析"
                        >
                          内容分析
                        </button>
                        <button
                          className="px-3 py-1 rounded-lg text-xs border border-purple-500/30 text-purple-600 hover:bg-purple-500/10"
                          onClick={() => navigate(`/suggestions/${item.id}`)}
                          aria-label="查看建议">查看建议</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}


