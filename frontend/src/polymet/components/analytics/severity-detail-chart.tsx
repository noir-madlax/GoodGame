 
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { ArrowLeft, Users } from "lucide-react";
import { Button } from "@/components/ui/button";

interface SeverityDetailData {
  creatorType: string;
  platforms: { 抖音: number; 小红书: number };
  total: number;
}

export default function SeverityDetailChart({
  severityLevel,
  relevanceType,
  data,
  totalCount,
  onBack,
  className = "",
}: {
  severityLevel: string;
  relevanceType: string;
  data: SeverityDetailData[];
  totalCount: number;
  relevanceTotal?: number;
  onBack: () => void;
  className?: string;
}) {
  const creatorColors = { 达人: "#3b82f6", 素人: "#8b5cf6", 未标注: "#6b7280" } as const;
  const displayCreator = (s: string) => (s === "未标注" ? "未知作者" : s);
  const platformColors = { 抖音: "#ff6b6b", 小红书: "#ff8cc8" } as const;

  const chartData = data.map((item) => ({ creatorType: item.creatorType, 抖音: item.platforms.抖音, 小红书: item.platforms.小红书, total: item.total }));

  type TooltipPayload<T> = { payload: T };
  const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: TooltipPayload<{ total: number; 抖音: number; 小红书: number }>[]; label?: string }) => {
    if (active && payload && payload.length) {
      const d = payload[0].payload;
      return (
        <div className="bg-white/95 backdrop-blur-xl border border-white/20 rounded-xl p-4 shadow-2xl max-w-xs">
          <div className="flex items-center gap-2 mb-3"><Users className="w-4 h-4 text-blue-600" /><h4 className="font-semibold text-gray-900">{displayCreator(String(label || ""))}</h4></div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between"><span className="text-gray-600">总数:</span><span className="font-medium text-gray-900">{d.total}</span></div>
          </div>
          <div className="mt-3 pt-3 border-t border-gray-200">
            <h5 className="text-xs font-medium text-gray-700 mb-2 flex items-center gap-1">平台分布</h5>
            <div className="space-y-1">
              <div className="flex justify-between items-center"><div className="flex items-center gap-1">  <img src="/douyin.svg" alt="抖音" className="w-3 h-3" /><span className="text-gray-600">抖音:</span></div><span className="text-gray-900 font-medium">{d.抖音}</span></div>
              <div className="flex justify-between items-center"><div className="flex items-center gap-1"><img src="/xiaohongshu.svg" alt="小红书" className="w-3 h-3" /><span className="text-gray-600">小红书:</span></div><span className="text-gray-900 font-medium">{d.小红书}</span></div>
            </div>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className={`space-y-6 ${className}`}>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-4">
              <Button variant="secondary" size="sm" onClick={onBack} className="bg-gray-100 text-gray-900 border-gray-200 hover:bg-gray-200 dark:bg-white/10 dark:text-white dark:border-white/20 dark:hover:bg-white/20"><ArrowLeft className="w-4 h-4 mr-2" />返回</Button>
              <div><h3 className="text-xl font-bold text-gray-900 dark:text-white">"{relevanceType}"且“优先级{severityLevel}”的内容</h3><p className="text-sm text-gray-600 dark:text-gray-400 mt-1">共 {totalCount} 条内容</p></div>
            </div>
          </div>
          <div className="h-80 w-full"><ResponsiveContainer width="100%" height="100%"><BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}><CartesianGrid strokeDasharray="3 3" stroke="#ffffff20" /><XAxis dataKey="creatorType" stroke="#6b7280" fontSize={12} tick={{ fontSize: 12 }} tickFormatter={(v) => displayCreator(String(v))} /><YAxis stroke="#6b7280" fontSize={12} tick={{ fontSize: 12 }} /><Tooltip content={<CustomTooltip />} /><Bar dataKey="抖音" stackId="platform" fill={platformColors.抖音} radius={[0, 0, 0, 0]} /><Bar dataKey="小红书" stackId="platform" fill={platformColors.小红书} radius={[4, 4, 0, 0]} /></BarChart></ResponsiveContainer></div>
        </div>
        <div className="space-y-4 self-start">
          <h4 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2"><Users className="w-4 h-4" />作者类型统计</h4>
          <div className="space-y-3">
            {data.map((item) => (
              <div key={item.creatorType} className="p-4 rounded-xl border bg-white/10 border-white/20">
                <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: creatorColors[item.creatorType as keyof typeof creatorColors] }} />
                      <span className="font-medium text-gray-900 dark:text-white">{displayCreator(item.creatorType)}</span>
                  </div>
                  <div className="text-right">
                    <div className="font-bold text-gray-900 dark:text-white">{item.total}</div>
                    <div className="text-xs text-gray-600 dark:text-gray-400">{totalCount > 0 ? Math.round((item.total / totalCount) * 100) : 0}%</div>
                  </div>
                </div>
                <div className="space-y-2">
                  <h5 className="text-xs font-medium text-gray-700 dark:text-gray-300 flex items-center gap-1">平台分布</h5>
                  <div className="space-y-1 text-sm">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <img src="/douyin.svg" alt="抖音" className="w-4 h-4" />
                        <span className="text-gray-600 dark:text-gray-400">抖音</span>
                      </div>
                      <span className="font-medium text-gray-900 dark:text-white">{item.platforms.抖音}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <img src="/xiaohongshu.svg" alt="小红书" className="w-4 h-4" />
                        <span className="text-gray-600 dark:text-gray-400">小红书</span>
                      </div>
                      <span className="font-medium text-gray-900 dark:text-white">{item.platforms.小红书}</span>
                    </div>
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


