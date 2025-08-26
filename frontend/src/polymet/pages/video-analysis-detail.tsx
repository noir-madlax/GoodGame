import React from "react";
import {
  ArrowLeft,
  Share2,
  Bookmark,
  Download,
  AlertTriangle,
  Shield,
} from "lucide-react";
import VideoPlayerCard from "@/polymet/components/video-player-card";
import AnalysisSection from "@/polymet/components/analysis-section";
import { BarChart3, Clock } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { useNavigate, useParams } from "react-router-dom";

export default function VideoAnalysisDetail() {
  const navigate = useNavigate();
  const { id } = useParams();
  const trendAnalysis = [
    {
      id: "1",
      type: "trend" as const,
      title: "宠物入店",
      description:
        "视频显示，在海底捞用餐区，两只宠物狗与顾客同桌生在桌上，并使用印有品牌Logo的餐具进食。",
      timestamp: "6小时前",
    },
    {
      id: "2",
      type: "alert" as const,
      title: "用餐卫生",
      description: "宠物狗使用餐厅品牌Logo的餐具进食。",
      severity: "medium" as const,
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
      riskBadge: "宠物进店",
    },
    {
      id: "6",
      type: "alert" as const,
      title: "00:11:40 - 风险等级：高",
      description: "宠物狗使用带有品牌Logo头像的餐具进食。",
      severity: "high" as const,
      timestamp: "用餐卫生",
      riskBadge: "用餐卫生",
    },
  ];

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <button
            className="p-3 rounded-xl bg-white/10 backdrop-blur-xl border border-white/20 hover:bg-white/20 transition-all duration-300 shadow-lg hover:shadow-xl"
            onClick={() => navigate(-1)}
            aria-label="Go back"
          >
            <ArrowLeft className="w-5 h-5 text-gray-700 dark:text-gray-300" />
          </button>
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
              舆情详情分析 {id ? `#${id}` : ""}
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
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Video Player - Smaller size */}
        <div className="">
          <VideoPlayerCard
            title="大晚上去海底捞吃饭看到的小可爱 😍 #当你有只喵馋小狗"
            description="视频显示，在海底捞用餐区，两只宠物狗与顾客同桌生在桌上，并使用印有品牌Logo的餐具进食。"
            thumbnail="https://images.unsplash.com/photo-1574158622682-e40e69881006?w=600&h=338&fit=crop"
            duration="0:27"
            views={1250}
            likes={55}
            comments={12}
            timestamp="2024/8/25 19:49:21"
            author="CC记录"
            className="h-fit"
          />
        </div>

        {/* Quick Stats */}
        <div className="space-y-6">
          <div className="p-6 rounded-2xl bg-white/10 backdrop-blur-xl border border-white/20 shadow-xl">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-4">
              内容概览
            </h3>

            {/* Key Risk Badges */}
            <div className="flex flex-wrap gap-2 mb-4">
              <Badge
                variant="destructive"
                className="px-3 py-1 text-xs font-medium bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 border border-red-200 dark:border-red-800 rounded-full flex items-center gap-1"
              >
                <AlertTriangle className="w-3 h-3" />
                宠物进店
              </Badge>
              <Badge
                variant="secondary"
                className="px-3 py-1 text-xs font-medium bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400 border border-orange-200 dark:border-orange-800 rounded-full flex items-center gap-1"
              >
                <Shield className="w-3 h-3" />
                用餐卫生
              </Badge>
            </div>
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

          {/* Sentiment Analysis Summary */}
          <AnalysisSection
            title="舆情分析总结"
            icon={
              <BarChart3 className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            }
            items={trendAnalysis}
          />
        </div>
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
