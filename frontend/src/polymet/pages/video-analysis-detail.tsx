import React from "react";
import { ArrowLeft, Share2, Bookmark, Download } from "lucide-react";
import VideoPlayerCard from "@/polymet/components/video-player-card";
import AnalysisSection from "@/polymet/components/analysis-section";
import {
  BarChart3,
  Eye,
  Clock,
  AlertTriangle,
  Target,
  TrendingUp,
} from "lucide-react";

export default function VideoAnalysisDetail() {
  const trendAnalysis = [
    {
      id: "1",
      type: "trend" as const,
      title: "宠物话题",
      description:
        "视频显示，在海底捞用餐区，两只宠物狗与顾客同桌生在桌上，并使用印有品牌Logo的餐具进食。",
      timestamp: "刚刚",
    },
    {
      id: "2",
      type: "alert" as const,
      title: "用餐卫生",
      description: "宠物狗使用餐厅品牌Logo的餐具进食。",
      severity: "medium" as const,
    },
  ];

  const keyPoints = [
    {
      id: "3",
      type: "insight" as const,
      title: "宠物进店",
      description: "两只宠物狗在餐厅区域与顾客同桌就餐。",
    },
    {
      id: "4",
      type: "recommendation" as const,
      title: "用餐卫生",
      description: "宠物狗使用带有品牌Logo的餐具进食。",
    },
  ];

  const timeline = [
    {
      id: "5",
      type: "trend" as const,
      title: "00:00:00 - 风险等级：中",
      description:
        "在海底捞餐厅的用餐区，一名男子与两只宠物狗只（一只金毛犬和一只拉布拉多），这两只宠物人一样坐在桌上，桌面摆着餐具。",
      timestamp: "宠物进店",
    },
    {
      id: "6",
      type: "alert" as const,
      title: "00:11:40 - 风险等级：高",
      description: "宠物狗使用带有品牌Logo头像的餐具进食。",
      severity: "high" as const,
      timestamp: "用餐卫生",
    },
  ];

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <button className="p-3 rounded-xl bg-white/10 backdrop-blur-xl border border-white/20 hover:bg-white/20 transition-all duration-300 shadow-lg hover:shadow-xl">
            <ArrowLeft className="w-5 h-5 text-gray-700 dark:text-gray-300" />
          </button>
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
              舆情详情分析
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              基于AI的深度舆情内容分析
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <button className="p-3 rounded-xl bg-white/10 backdrop-blur-xl border border-white/20 hover:bg-white/20 transition-all duration-300 shadow-lg hover:shadow-xl">
            <Share2 className="w-5 h-5 text-gray-700 dark:text-gray-300" />
          </button>
          <button className="p-3 rounded-xl bg-white/10 backdrop-blur-xl border border-white/20 hover:bg-white/20 transition-all duration-300 shadow-lg hover:shadow-xl">
            <Bookmark className="w-5 h-5 text-gray-700 dark:text-gray-300" />
          </button>
          <button className="p-3 rounded-xl bg-white/10 backdrop-blur-xl border border-white/20 hover:bg-white/20 transition-all duration-300 shadow-lg hover:shadow-xl">
            <Download className="w-5 h-5 text-gray-700 dark:text-gray-300" />
          </button>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
        {/* Video Player - Takes 2 columns on xl screens */}
        <div className="xl:col-span-2">
          <VideoPlayerCard
            title="大晚上去海底捞吃饭看到的小可爱 😍 #当你有只喵馋小狗 #养狗当然就是用来玩的 #被小狗治愈的一万个瞬间 #狗狗的心思都写在脸上了 #狗狗"
            description="视频显示，在海底捞用餐区，两只宠物狗与顾客同桌生在桌上，并使用印有品牌Logo的餐具进食。"
            thumbnail="https://images.unsplash.com/photo-1574158622682-e40e69881006?w=800&h=450&fit=crop"
            duration="0:27"
            views={1250}
            likes={55}
            comments={12}
            timestamp="2024/8/25 19:49:21"
            author="douyin"
            className="h-fit"
          />
        </div>

        {/* Quick Stats */}
        <div className="space-y-6">
          <div className="p-6 rounded-2xl bg-white/10 backdrop-blur-xl border border-white/20 shadow-xl">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">
              内容概览
            </h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-gray-600 dark:text-gray-400">
                  风险等级
                </span>
                <span className="px-3 py-1 rounded-full bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400 text-sm font-medium">
                  中等风险
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-600 dark:text-gray-400">
                  内容类型
                </span>
                <span className="text-gray-900 dark:text-white font-medium">
                  视频
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-600 dark:text-gray-400">
                  发布平台
                </span>
                <span className="text-gray-900 dark:text-white font-medium">
                  抖音
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-600 dark:text-gray-400">
                  分析状态
                </span>
                <span className="px-3 py-1 rounded-full bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 text-sm font-medium">
                  已完成
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Analysis Sections */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
        <AnalysisSection
          title="舆情分析总结"
          icon={
            <BarChart3 className="w-5 h-5 text-blue-600 dark:text-blue-400" />
          }
          items={trendAnalysis}
        />

        <AnalysisSection
          title="关键观察点"
          icon={<Eye className="w-5 h-5 text-green-600 dark:text-green-400" />}
          items={keyPoints}
        />
      </div>

      {/* Timeline Analysis - Full Width */}
      <AnalysisSection
        title="时间轴分析"
        icon={
          <Clock className="w-5 h-5 text-purple-600 dark:text-purple-400" />
        }
        items={timeline}
        className="w-full"
      />
    </div>
  );
}
