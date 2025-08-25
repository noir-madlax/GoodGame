"use client"

import type React from "react"

import { useState } from "react"
import { useRouter } from "next/navigation"
import {
  TrendingUp,
  Filter,
  Heart,
  MessageCircle,
  Share2,
  ExternalLink,
  BarChart3,
  Settings,
  Database,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

const mockVideos = [
  {
    id: 1,
    title: "海底捞服务体验分享",
    description: "今天去海底捞吃火锅，服务员小姐姐超级贴心，还帮我们拍照！",
    thumbnail: "/hotpot-restaurant-interior.png",
    platform: "小红书",
    author: "美食达人小王",
    likes: 1234,
    comments: 89,
    shares: 45,
    sentiment: "positive",
    duration: "2:34",
    publishTime: "2小时前",
    contentType: "视频",
    views: 12340,
    riskLevel: "低风险",
  },
  {
    id: 2,
    title: "海底捞排队太久了",
    description: "等了2个小时才吃上，虽然味道不错但是等待时间真的太长了",
    thumbnail: "/people-waiting-in-restaurant-queue.png",
    platform: "抖音",
    author: "吃货小李",
    likes: 567,
    comments: 123,
    shares: 23,
    sentiment: "negative",
    duration: "1:45",
    publishTime: "4小时前",
    contentType: "视频",
    views: 5670,
    riskLevel: "中风险",
  },
  {
    id: 3,
    title: "海底捞新品试吃",
    description: "海底捞推出的新口味锅底真的很不错，推荐大家试试！",
    thumbnail: "/new-hotpot-soup-base-ingredients.png",
    platform: "小红书",
    author: "美食博主",
    likes: 2341,
    comments: 234,
    shares: 156,
    sentiment: "positive",
    duration: "3:12",
    publishTime: "6小时前",
    contentType: "图文",
    views: 23410,
    riskLevel: "低风险",
  },
  {
    id: 4,
    title: "海底捞价格分析",
    description: "对比了几家火锅店的价格，海底捞确实偏贵，但服务确实好",
    thumbnail: "/restaurant-price-comparison-chart.png",
    platform: "抖音",
    author: "理性消费者",
    likes: 890,
    comments: 167,
    shares: 78,
    sentiment: "neutral",
    duration: "4:23",
    publishTime: "8小时前",
    contentType: "视频",
    views: 8900,
    riskLevel: "低风险",
  },
  {
    id: 5,
    title: "海底捞员工服务态度",
    description: "必须夸一下海底捞的员工，真的很用心在服务每一位顾客",
    thumbnail: "/restaurant-staff-serving-customers.png",
    platform: "小红书",
    author: "服务体验师",
    likes: 1567,
    comments: 98,
    shares: 67,
    sentiment: "positive",
    duration: "2:56",
    publishTime: "12小时前",
    contentType: "图文",
    views: 15670,
    riskLevel: "低风险",
  },
  {
    id: 6,
    title: "海底捞食材新鲜度",
    description: "今天的蔬菜感觉不太新鲜，希望能改进一下食材管理",
    thumbnail: "/fresh-vegetables-for-hotpot.png",
    platform: "抖音",
    author: "挑剔食客",
    likes: 234,
    comments: 56,
    shares: 12,
    sentiment: "negative",
    duration: "1:23",
    publishTime: "1天前",
    contentType: "视频",
    views: 2340,
    riskLevel: "高风险",
  },
]

function VideoCard({ video }: { video: (typeof mockVideos)[0] }) {
  const router = useRouter()
  const [isHovered, setIsHovered] = useState(false)

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case "positive":
        return "bg-green-100 text-green-800"
      case "negative":
        return "bg-red-100 text-red-800"
      default:
        return "bg-yellow-100 text-yellow-800"
    }
  }

  const getSentimentText = (sentiment: string) => {
    switch (sentiment) {
      case "positive":
        return "正面"
      case "negative":
        return "负面"
      default:
        return "中性"
    }
  }

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case "高风险":
        return "bg-red-100 text-red-800"
      case "中风险":
        return "bg-yellow-100 text-yellow-800"
      default:
        return "bg-green-100 text-green-800"
    }
  }

  const handleCardClick = () => {
    router.push(`/detail/${video.id}`)
  }

  const handleViewOriginal = (e: React.MouseEvent) => {
    e.stopPropagation()
    window.open(`https://${video.platform.toLowerCase()}.com/video/${video.id}`, "_blank")
  }

  return (
    <Card
      className="group hover:shadow-lg transition-all duration-300 hover:-translate-y-1 overflow-hidden cursor-pointer"
      onClick={handleCardClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="relative">
        <img src={video.thumbnail || "/placeholder.svg"} alt={video.title} className="w-full h-48 object-cover" />
        <div className="absolute inset-0 bg-black/20 group-hover:bg-black/30 transition-colors duration-300" />
        <div className="absolute top-2 left-2">
          <Badge variant="secondary" className="bg-black/50 text-white">
            {video.platform}
          </Badge>
        </div>
        <div className="absolute top-2 right-2 flex gap-1">
          <Badge className={getSentimentColor(video.sentiment)}>{getSentimentText(video.sentiment)}</Badge>
          <Badge className={getRiskColor(video.riskLevel)}>{video.riskLevel}</Badge>
        </div>
        <div className="absolute bottom-2 right-2 bg-black/70 text-white px-2 py-1 rounded text-xs">
          {video.duration}
        </div>
        {isHovered && (
          <div className="absolute bottom-2 left-2">
            <Button
              size="sm"
              className="h-7 px-2 bg-white/90 hover:bg-white text-gray-700 hover:text-gray-900 text-xs rounded-md shadow-sm"
              onClick={handleViewOriginal}
            >
              <ExternalLink className="w-3 h-3 mr-1" />
              查看原内容
            </Button>
          </div>
        )}
      </div>

      <CardContent className="p-4">
        <h3 className="font-semibold text-sm mb-2 line-clamp-2">{video.title}</h3>
        <p className="text-xs text-muted-foreground mb-3 line-clamp-2">{video.description}</p>

        <div className="flex items-center justify-between text-xs text-muted-foreground mb-2">
          <span>@{video.author}</span>
          <span>{video.publishTime}</span>
        </div>

        <div className="flex items-center justify-between text-xs mb-2">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1">
              <Heart className="w-3 h-3" />
              <span>{video.likes}</span>
            </div>
            <div className="flex items-center gap-1">
              <MessageCircle className="w-3 h-3" />
              <span>{video.comments}</span>
            </div>
            <div className="flex items-center gap-1">
              <Share2 className="w-3 h-3" />
              <span>{video.shares}</span>
            </div>
          </div>
          <div className="text-xs text-muted-foreground">{video.views.toLocaleString()} 次播放</div>
        </div>

        <div className="flex items-center justify-between text-xs">
          <Badge variant="outline" className="text-xs">
            {video.contentType}
          </Badge>
        </div>
      </CardContent>
    </Card>
  )
}

export default function HomePage() {
  const [activeTab, setActiveTab] = useState("content")
  const [filters, setFilters] = useState({
    riskTheme: "all",
    platform: "all",
    contentType: "all",
    publishTime: "all",
    views: "all",
  })

  const navigationItems = [
    { id: "content", label: "舆情内容", icon: BarChart3, active: true },
    { id: "search-config", label: "内容检索配置", icon: Database, active: false },
    { id: "analysis-config", label: "舆情分析配置", icon: Settings, active: false },
  ]

  return (
    <div className="min-h-screen bg-gray-50 flex">
      <div className="w-64 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-emerald-600 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-gray-900">海底捞舆情分析</h1>
            </div>
          </div>
        </div>

        <nav className="flex-1 p-4">
          <ul className="space-y-2">
            {navigationItems.map((item) => (
              <li key={item.id}>
                <button
                  onClick={() => item.active && setActiveTab(item.id)}
                  disabled={!item.active}
                  className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition-colors ${
                    activeTab === item.id && item.active
                      ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                      : item.active
                        ? "text-gray-700 hover:bg-gray-50"
                        : "text-gray-400 cursor-not-allowed"
                  }`}
                >
                  <item.icon className="w-5 h-5" />
                  <span className="font-medium">{item.label}</span>
                </button>
              </li>
            ))}
          </ul>
        </nav>
      </div>

      <div className="flex-1 flex flex-col">
        <header className="bg-white border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">舆情内容监控</h2>
            </div>

            <div className="flex items-center gap-3">
              <Select value={filters.riskTheme} onValueChange={(value) => setFilters({ ...filters, riskTheme: value })}>
                <SelectTrigger className="w-40">
                  <SelectValue placeholder="舆论风险主题" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部主题</SelectItem>
                  <SelectItem value="food-safety">食安风险</SelectItem>
                  <SelectItem value="ground-pollution">地面污染</SelectItem>
                  <SelectItem value="customer-area-rest">在顾客区域休息</SelectItem>
                  <SelectItem value="kitchen-chaos">后厨管理混乱</SelectItem>
                  <SelectItem value="passage-blocked">通道堵塞</SelectItem>
                  <SelectItem value="debris-accumulation">杂物堆积</SelectItem>
                  <SelectItem value="staff-service">员工服务不当</SelectItem>
                  <SelectItem value="staff-discipline">员工纪律松懈</SelectItem>
                </SelectContent>
              </Select>

              <Select value={filters.platform} onValueChange={(value) => setFilters({ ...filters, platform: value })}>
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="内容渠道" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部渠道</SelectItem>
                  <SelectItem value="xiaohongshu">小红书</SelectItem>
                  <SelectItem value="douyin">抖音</SelectItem>
                  <SelectItem value="weibo">微博</SelectItem>
                </SelectContent>
              </Select>

              <Select
                value={filters.contentType}
                onValueChange={(value) => setFilters({ ...filters, contentType: value })}
              >
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="内容类型" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部类型</SelectItem>
                  <SelectItem value="video">视频</SelectItem>
                  <SelectItem value="image">图文</SelectItem>
                  <SelectItem value="text">纯文本</SelectItem>
                </SelectContent>
              </Select>

              <Select
                value={filters.publishTime}
                onValueChange={(value) => setFilters({ ...filters, publishTime: value })}
              >
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="发布时间" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部时间</SelectItem>
                  <SelectItem value="1h">1小时内</SelectItem>
                  <SelectItem value="24h">24小时内</SelectItem>
                  <SelectItem value="7d">7天内</SelectItem>
                </SelectContent>
              </Select>

              <Select value={filters.views} onValueChange={(value) => setFilters({ ...filters, views: value })}>
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="访问量" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部</SelectItem>
                  <SelectItem value="high">高访问量</SelectItem>
                  <SelectItem value="medium">中等访问量</SelectItem>
                  <SelectItem value="low">低访问量</SelectItem>
                </SelectContent>
              </Select>

              <Button variant="outline" size="sm">
                <Filter className="w-4 h-4 mr-2" />
                重置筛选
              </Button>
            </div>
          </div>
        </header>

        <main className="flex-1 p-6">
          {activeTab === "content" && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {mockVideos.map((video) => (
                  <VideoCard key={video.id} video={video} />
                ))}
              </div>
            </div>
          )}

          {activeTab === "search-config" && (
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <Database className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">内容检索配置</h3>
                <p className="text-gray-500">此功能正在开发中，敬请期待</p>
              </div>
            </div>
          )}

          {activeTab === "analysis-config" && (
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <Settings className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">舆情分析配置</h3>
                <p className="text-gray-500">此功能正在开发中，敬请期待</p>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
