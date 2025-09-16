import React, { useState } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { ArrowLeft, AlertTriangle, TrendingUp, Info, Users, Filter } from "lucide-react";
import { Button } from "@/components/ui/button";

interface SeverityGroup {
  severity: string;
  total: number;
  percentage: number;
  creators: { 达人: number; 素人: number; 未标注: number };
  platforms?: { 抖音: number; 小红书: number; 其他: number };
  sentiment?: { 正面: number; 负面: number; 中性: number; 未标注: number };
}

export default function SeverityAnalysis({
  relevanceType,
  data,
  totalCount,
  onBack,
  onSeverityClick,
  className = "",
}: {
  relevanceType: string;
  data: SeverityGroup[];
  totalCount: number;
  onBack: () => void;
  onSeverityClick?: (severity: string, creatorType?: string) => void;
  className?: string;
}) {
  const [selectedSeverity, setSelectedSeverity] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);

  const severityColors = { 高: "#ef4444", 中: "#f97316", 低: "#22c55e", 未标注: "#6b7280" } as const;
  const creatorColors = { 达人: "#3b82f6", 素人: "#8b5cf6", 未标注: "#6b7280" } as const;

  const getSeverityIcon = (s: string) => (s === "高" ? <AlertTriangle className="w-4 h-4 text-red-500" /> : s === "中" ? <TrendingUp className="w-4 h-4 text-orange-500" /> : s === "低" ? <Info className="w-4 h-4 text-green-500" /> : <Info className="w-4 h-4 text-gray-500" />);

  const chartData = data.map((item) => ({ severity: item.severity || "未知", total: item.total || 0, percentage: item.percentage || 0, ...item.creators }));

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const severityData = payload[0].payload;
      if (!severityData || severityData.total === undefined || severityData.percentage === undefined) return null;
      return (
        <div className="bg-white/95 backdrop-blur-xl border border-white/20 rounded-xl p-4 shadow-2xl max-w-xs">
          <div className="flex items-center gap-2 mb-3">{getSeverityIcon(label)}<h4 className="font-semibold text-gray-900">{label}</h4></div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between"><span className="text-gray-600">总数:</span><span className="font-medium text-gray-900">{severityData.total}</span></div>
            <div className="flex justify-between"><span className="text-gray-600">占比:</span><span className="font-medium text-gray-900">{severityData.percentage}%</span></div>
          </div>
          <div className="mt-3 pt-3 border-t border-gray-200">
            <h5 className="text-xs font-medium text-gray-700 mb-2 flex items-center gap-1"><Users className="w-3 h-3" />创作者属性分布</h5>
            <div className="space-y-1">
              {(Object.entries(severityData) as [string, unknown][])
                .filter(([key]) => ["达人", "素人", "未标注"].includes(key))
                .map(([creator, count]) => (
                  <div key={creator} className="flex justify-between items-center">
                    <div className="flex items-center gap-1">
                      <div className="w-2 h-2 rounded-full" style={{ backgroundColor: creatorColors[creator as keyof typeof creatorColors] }} />
                      <span className="text-gray-600">{creator}:</span>
                    </div>
                    <span className="text-gray-900 font-medium">{count as number}</span>
                  </div>
                ))}
            </div>
          </div>
        </div>
      );
    }
    return null;
  };

  const handleBarClick = (d: any) => {
    setSelectedSeverity(d.severity);
    onSeverityClick?.(d.severity);
  };

  return (
    <div className={`space-y-6 ${className}`}>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-4">
              <Button variant="secondary" size="sm" onClick={onBack} className="bg-gray-100 text-gray-900 border-gray-200 hover:bg-gray-200 dark:bg-white/10 dark:text-white dark:border-white/20 dark:hover:bg-white/20"><ArrowLeft className="w-4 h-4 mr-2" />返回</Button>
              <div>
                <h3 className="text-xl font-bold text-gray-900 dark:text-white">"{relevanceType}" 的内容</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">点击柱状图查看对应内容列表</p>
              </div>
            </div>
          </div>
          <div className="h-80 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff20" />
                <XAxis dataKey="severity" stroke="#6b7280" fontSize={12} tick={{ fontSize: 12 }} />
                <YAxis stroke="#6b7280" fontSize={12} tick={{ fontSize: 12 }} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="total" radius={[4, 4, 0, 0]} onClick={handleBarClick} className="cursor-pointer" label={{ position: "inside", fill: "#ffffff", fontSize: 12, fontWeight: "bold", formatter: (value: number, entry: any) => (entry && entry.percentage !== undefined ? `${entry.percentage}%` : `${value}`) }}>
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={severityColors[entry.severity as keyof typeof severityColors]} stroke={selectedSeverity === entry.severity ? "#ffffff" : "透明"} strokeWidth={selectedSeverity === entry.severity ? 2 : 0} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="space-y-4 self-start">
          <div className="flex items-center justify-between"><h4 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2"><Filter className="w-4 h-4" />优先级统计</h4>{data.length > 2 && (<Button variant="ghost" size="sm" onClick={() => setIsExpanded(!isExpanded)} className="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white">{isExpanded ? "收起" : `展开全部 (${data.length})`}</Button>)}</div>
          <div className="space-y-3">
            {data.filter((item) => (["高", "中"].includes(item.severity) ? true : isExpanded)).map((item) => (
              <div key={item.severity} className={`p-4 rounded-xl border cursor-pointer transition-all duration-200 ${selectedSeverity === item.severity ? "bg-white/20 border-white/30 shadow-lg" : "bg-white/10 border-white/20 hover:bg-white/15"}`} onClick={() => handleBarClick(item)}>
                <div className="flex items-center justify-between mb-3"><div className="flex items-center gap-2">{getSeverityIcon(item.severity)}<span className="font-medium text-gray-900 dark:text-white">{item.severity}</span></div><div className="text-right"><div className="font-bold text-gray-900 dark:text-white">{item.total}</div><div className="text-xs text-gray-600 dark:text-gray-400">{item.percentage}%</div></div></div>
                <div className="space-y-2">
                  <h5 className="text-xs font-medium text-gray-700 dark:text-gray-300 flex items-center gap-1"><Users className="w-3 h-3" />创作者分布</h5>
                  <div className="space-y-1 text-sm">
                    {Object.entries(item.creators).map(([creator, count]) => (
                      <div key={creator} className="flex items-center justify-between" onClick={(e) => { e.stopPropagation(); onSeverityClick?.(item.severity, creator); }} role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.stopPropagation(); onSeverityClick?.(item.severity, creator); } }} aria-label={`查看${creator}在${item.severity}优先级下的明细`}>
                        <div className="flex items-center gap-2"><div className="w-2 h-2 rounded-full" style={{ backgroundColor: creatorColors[creator as keyof typeof creatorColors] }} /><span className="text-gray-600 dark:text-gray-400">{creator}</span></div>
                        <span className="font-medium text-gray-900 dark:text-white">{count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

 