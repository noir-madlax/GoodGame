import { useState } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { ArrowRight, TrendingUp, AlertTriangle, Info } from "lucide-react";

interface RelevanceData {
  name: string;
  value: number;
  percentage: number;
  color: string;
  priority: "high" | "medium" | "low";
  severityBreakdown?: { 高: number; 中: number; 低: number; 未标注: number };
  platformBreakdown?: { 抖音: number; 小红书: number; 其他: number };
}

type TooltipProps = { active?: boolean; payload?: Array<{ payload: RelevanceData }> };

type PieLabelArgs = {
  cx: number; cy: number; midAngle: number; innerRadius: number; outerRadius: number; percent: number; name: string;
};

export default function RelevanceChart({
  data,
  onRelevanceClick,
  className = "",
}: {
  data: RelevanceData[];
  onRelevanceClick: (relevance: string) => void;
  className?: string;
}) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const [listHover, setListHover] = useState(false);

  const getPriorityIcon = (priority: string) => {
    switch (priority) {
      case "high":
        return <AlertTriangle className="w-4 h-4 text-red-500" />;
      case "medium":
        return <TrendingUp className="w-4 h-4 text-orange-500" />;
      default:
        return <Info className="w-4 h-4 text-gray-500" />;
    }
  };

  const CustomTooltip = ({ active, payload }: TooltipProps) => {
    if (active && payload && payload.length) {
      const d = payload[0].payload;
      return (
        <div className="bg-white/95 backdrop-blur-xl border border-white/20 rounded-xl p-4 shadow-2xl max-w-xs">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: d.color }} />
            <h4 className="font-semibold text-gray-900">{d.name}</h4>
            {getPriorityIcon(d.priority)}
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between"><span className="text-gray-600">数量:</span><span className="font-medium text-gray-900">{d.value}</span></div>
            <div className="flex justify-between"><span className="text-gray-600">占比:</span><span className="font-medium text-gray-900">{d.percentage}%</span></div>
          </div>
        </div>
      );
    }
    return null;
  };

  // 扇区标签：大于12%展示“名称 百分比”，否则仅展示百分比；始终居中，避免溢出
  const renderLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent, name }: PieLabelArgs) => {
    if (percent < 0.05) return null;
    const RADIAN = Math.PI / 180;
    const r = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + r * Math.cos(-midAngle * RADIAN);
    const y = cy + r * Math.sin(-midAngle * RADIAN);
    const showName = percent >= 0.12;
    return (
      <text
        x={x}
        y={y}
        fill="white"
        textAnchor="middle"
        dominantBaseline="central"
        className="text-[10px] font-medium"
      >
        {`${showName ? name + " " : ""}${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  const hoveredData = hoveredIndex !== null ? data[hoveredIndex] : null;

  return (
    <div className={`${className}`}>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <div className="h-80 w-full relative">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart onMouseLeave={() => { setHoveredIndex(null); setListHover(false); }}>
                <Pie
                  data={data}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={renderLabel}
                  outerRadius={120}
                  innerRadius={40}
                  dataKey="value"
                  onMouseEnter={(_: unknown, i: number) => { setHoveredIndex(i); setListHover(false); }}
                  onMouseLeave={() => { setHoveredIndex(null); setListHover(false); }}
                  onClick={(d: RelevanceData) => onRelevanceClick(d.name)}
                  className="cursor-pointer"
                >
                  {data.map((e, i) => (
                    <Cell
                      key={i}
                      fill={e.color}
                      stroke={hoveredIndex === i ? "#ffffff" : "transparent"}
                      strokeWidth={hoveredIndex === i ? 3 : 0}
                      style={{
                        filter: hoveredIndex === i ? "brightness(1.1)" : "none",
                        transform: hoveredIndex === i ? "scale(1.02)" : "scale(1)",
                        transformOrigin: "center",
                        transition: "all 0.2s ease",
                      }}
                    />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} wrapperStyle={{ pointerEvents: "none" }} />
              </PieChart>
            </ResponsiveContainer>

            {listHover && hoveredData && (
              <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-[60%] bg-white/95 backdrop-blur-xl border border-white/20 rounded-xl p-3 shadow-2xl text-xs min-w-[160px]">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: hoveredData.color }} />
                  <span className="font-semibold text-gray-900">{hoveredData.name}</span>
                </div>
                <div className="flex justify-between"><span className="text-gray-600">数量:</span><span className="font-medium text-gray-900">{hoveredData.value}</span></div>
                <div className="flex justify-between"><span className="text-gray-600">占比:</span><span className="font-medium text-gray-900">{hoveredData.percentage}%</span></div>
              </div>
            )}
          </div>
        </div>
        <div className="space-y-4">
          <h4 className="font-semibold text-gray-900 dark:text-white">分类统计</h4>
          <div className="space-y-3">
            {data.map((item, index) => (
              <div
                key={item.name}
                className={`p-3 rounded-xl border cursor-pointer transition-all duration-200 ${
                  hoveredIndex === index && listHover ? "bg-white/20 border-white/30 shadow-lg" : "bg-white/10 border-white/20 hover:bg-white/15"
                }`}
                onClick={() => onRelevanceClick(item.name)}
                onMouseEnter={() => { setHoveredIndex(index); setListHover(true); }}
                onMouseLeave={() => { setListHover(false); setHoveredIndex(null); }}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: item.color }} />
                    <span className="font-medium text-gray-900 dark:text-white">{item.name}</span>
                  </div>
                  <ArrowRight className="w-4 h-4 text-gray-400" />
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600 dark:text-gray-400">{item.value} 条</span>
                  <span className="font-medium text-gray-900 dark:text-white">{item.percentage}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}


