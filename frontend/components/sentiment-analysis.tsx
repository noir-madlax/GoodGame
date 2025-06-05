"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  ThumbsUp,
  ThumbsDown,
  AlertCircle,
  CheckCircle2,
  BarChart3,
  MessageSquare,
  Clock,
  TrendingUp,
  ArrowUpRight,
  Download,
} from "lucide-react"
import { Progress } from "@/components/ui/progress"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

export function SentimentAnalysis() {
  const [activeTab, setActiveTab] = useState("overview")
  const [platformFilter, setPlatformFilter] = useState("all")
  const [dimensionFilter, setDimensionFilter] = useState("all")
  const [sentimentFilter, setSentimentFilter] = useState("all")

  const comments = {
    positive: [
      {
        id: 1,
        content: "刺客信条幻影刺客的画面真的太惊艳了，育碧这次做得很棒！",
        platform: "哔哩哔哩",
        date: "2025-04-15",
        confidence: 0.92,
        keywords: ["画面", "育碧"],
        dimension: "视觉效果",
        verified: true,
      },
      {
        id: 2,
        content: "育碧这次的开放世界设计真的很用心，每个角落都有惊喜",
        platform: "百度贴吧",
        date: "2025-04-05",
        confidence: 0.89,
        keywords: ["开放世界", "育碧"],
        dimension: "游戏设计",
        verified: false,
      },
      {
        id: 3,
        content: "这代的战斗系统有了很大改进，玩起来非常流畅",
        platform: "微博",
        date: "2025-04-12",
        confidence: 0.87,
        keywords: ["战斗系统"],
        dimension: "游戏玩法",
        verified: true,
      },
      {
        id: 4,
        content: "音效和配乐真的绝了，完全沉浸在游戏世界中",
        platform: "小红书",
        date: "2025-04-08",
        confidence: 0.91,
        keywords: ["音效", "配乐"],
        dimension: "音频体验",
        verified: false,
      },
    ],
    negative: [
      {
        id: 5,
        content: "游戏优化还是有问题，高配置电脑都有点卡顿",
        platform: "百度贴吧",
        date: "2025-04-12",
        confidence: 0.85,
        keywords: ["优化", "卡顿"],
        dimension: "技术表现",
        verified: true,
      },
      {
        id: 6,
        content: "剧情设计太过于老套，没有新意",
        platform: "哔哩哔哩",
        date: "2025-04-08",
        confidence: 0.78,
        keywords: ["剧情"],
        dimension: "故事剧情",
        verified: false,
      },
      {
        id: 7,
        content: "任务设计太过重复，做了几个小时就感觉无聊了",
        platform: "微博",
        date: "2025-04-10",
        confidence: 0.82,
        keywords: ["任务", "重复"],
        dimension: "游戏设计",
        verified: true,
      },
      {
        id: 8,
        content: "AI太傻了，敌人的行为模式太容易预测",
        platform: "抖音",
        date: "2025-04-14",
        confidence: 0.79,
        keywords: ["AI", "敌人"],
        dimension: "游戏玩法",
        verified: false,
      },
    ],
    neutral: [
      {
        id: 9,
        content: "剧情设计中规中矩，没有特别惊喜的地方",
        platform: "微博",
        date: "2025-04-10",
        confidence: 0.78,
        keywords: ["剧情"],
        dimension: "故事剧情",
        verified: true,
      },
      {
        id: 10,
        content: "这代的任务设计和之前的作品差不多",
        platform: "哔哩哔哩",
        date: "2025-04-07",
        confidence: 0.75,
        keywords: ["任务设计"],
        dimension: "游戏设计",
        verified: false,
      },
      {
        id: 11,
        content: "角色塑造一般，没有特别出彩的地方",
        platform: "百度贴吧",
        date: "2025-04-09",
        confidence: 0.77,
        keywords: ["角色"],
        dimension: "故事剧情",
        verified: true,
      },
      {
        id: 12,
        content: "游戏难度适中，不算太难也不会太简单",
        platform: "小红书",
        date: "2025-04-11",
        confidence: 0.81,
        keywords: ["难度"],
        dimension: "游戏玩法",
        verified: false,
      },
    ],
  }

  // 获取所有评论
  const getAllComments = () => {
    return [...comments.positive, ...comments.negative, ...comments.neutral]
  }

  // 过滤评论
  const filterComments = (type?: "positive" | "negative" | "neutral") => {
    const commentsToFilter = type ? comments[type] : getAllComments()

    return commentsToFilter.filter((comment) => {
      const matchesPlatform = platformFilter === "all" || comment.platform === platformFilter
      const matchesDimension = dimensionFilter === "all" || comment.dimension === dimensionFilter

      if (type) {
        return matchesPlatform && matchesDimension
      } else {
        // 当显示所有评论时，还要根据情感筛选
        let commentType = "neutral"
        if (comments.positive.includes(comment)) commentType = "positive"
        else if (comments.negative.includes(comment)) commentType = "negative"

        const matchesSentiment = sentimentFilter === "all" || commentType === sentimentFilter
        return matchesPlatform && matchesDimension && matchesSentiment
      }
    })
  }

  const handleVerify = (id: number, type: "positive" | "negative" | "neutral") => {
    console.log(`验证评论 ${id} 为 ${type}`)
  }

  const handleCorrect = (id: number, currentType: string, newType: string) => {
    console.log(`将评论 ${id} 从 ${currentType} 更正为 ${newType}`)
  }

  const getSentimentBadge = (comment: any) => {
    if (comments.positive.includes(comment)) {
      return <Badge className="bg-green-500">正面</Badge>
    } else if (comments.negative.includes(comment)) {
      return <Badge className="bg-red-500">负面</Badge>
    } else {
      return <Badge className="bg-gray-500">中性</Badge>
    }
  }

  const getSentimentType = (comment: any) => {
    if (comments.positive.includes(comment)) return "positive"
    if (comments.negative.includes(comment)) return "negative"
    return "neutral"
  }

  const renderCommentList = (type?: "positive" | "negative" | "neutral") => {
    const filteredComments = filterComments(type)

    return filteredComments.length > 0 ? (
      filteredComments.map((comment) => {
        const sentimentType = getSentimentType(comment)
        return (
          <Card key={comment.id} className="mb-4">
            <CardContent className="pt-6">
              <div className="flex justify-between items-start mb-2">
                <div className="flex items-center gap-2">
                  <Badge variant="outline">{comment.platform}</Badge>
                  <span className="text-sm text-muted-foreground">{comment.date}</span>
                  <Badge variant="secondary">{comment.dimension}</Badge>
                  {getSentimentBadge(comment)}
                </div>
                <div className="flex items-center gap-1">
                  <Progress value={comment.confidence * 100} className="w-24 h-2" />
                  <span className="text-xs">{(comment.confidence * 100).toFixed(0)}%</span>
                </div>
              </div>

              <p className="mb-4">{comment.content}</p>

              <div className="flex justify-between items-center">
                <div className="flex flex-wrap gap-2">
                  {comment.keywords.map((keyword, idx) => (
                    <Badge key={idx} variant="secondary">
                      {keyword}
                    </Badge>
                  ))}
                </div>

                <div className="flex gap-2">
                  {!comment.verified ? (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleVerify(comment.id, sentimentType)}
                      className="flex items-center gap-1"
                    >
                      <CheckCircle2 className="h-4 w-4" />
                      验证
                    </Button>
                  ) : (
                    <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                      <CheckCircle2 className="h-3 w-3 mr-1" />
                      已验证
                    </Badge>
                  )}

                  <div className="flex gap-1">
                    {sentimentType !== "positive" && (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleCorrect(comment.id, sentimentType, "positive")}
                        className="h-8 w-8 text-green-600"
                      >
                        <ThumbsUp className="h-4 w-4" />
                      </Button>
                    )}

                    {sentimentType !== "negative" && (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleCorrect(comment.id, sentimentType, "negative")}
                        className="h-8 w-8 text-red-600"
                      >
                        <ThumbsDown className="h-4 w-4" />
                      </Button>
                    )}

                    {sentimentType !== "neutral" && (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleCorrect(comment.id, sentimentType, "neutral")}
                        className="h-8 w-8 text-gray-600"
                      >
                        <AlertCircle className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )
      })
    ) : (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <p className="text-muted-foreground mb-2">没有符合条件的评论</p>
        <p className="text-sm text-muted-foreground">尝试更改筛选条件</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* 概览统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-orange-50">
          <CardHeader className="pb-2">
            <CardTitle className="text-orange-700 flex items-center gap-2">
              <MessageSquare className="h-5 w-5" />
              总评论数
            </CardTitle>
            <CardDescription className="text-orange-600">1,248 条</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between text-xs text-orange-600">
              <span>较上周</span>
              <span className="flex items-center">
                +12% <TrendingUp className="ml-1 h-3 w-3" />
              </span>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-green-50">
          <CardHeader className="pb-2">
            <CardTitle className="text-green-700 flex items-center gap-2">
              <ThumbsUp className="h-5 w-5" />
              正面评论
            </CardTitle>
            <CardDescription className="text-green-600">65% · 812 条</CardDescription>
          </CardHeader>
          <CardContent>
            <Progress value={65} className="h-2 bg-green-200" indicatorClassName="bg-green-600" />
          </CardContent>
        </Card>

        <Card className="bg-red-50">
          <CardHeader className="pb-2">
            <CardTitle className="text-red-700 flex items-center gap-2">
              <ThumbsDown className="h-5 w-5" />
              负面评论
            </CardTitle>
            <CardDescription className="text-red-600">20% · 249 条</CardDescription>
          </CardHeader>
          <CardContent>
            <Progress value={20} className="h-2 bg-red-200" indicatorClassName="bg-red-600" />
          </CardContent>
        </Card>

        <Card className="bg-purple-50">
          <CardHeader className="pb-2">
            <CardTitle className="text-purple-700 flex items-center gap-2">
              <Clock className="h-5 w-5" />
              平均响应时间
            </CardTitle>
            <CardDescription className="text-purple-600">4.5 小时</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between text-xs text-purple-600">
              <span>较上周</span>
              <span className="flex items-center">-0.8 小时</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 主要内容区域 */}
      <Card>
        <CardHeader>
          <CardTitle>智能分析中心</CardTitle>
          <CardDescription>AI情感分析、舆情追踪和预警监控</CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="overview" value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="mb-4">
              <TabsTrigger value="overview">分析概览</TabsTrigger>
              <TabsTrigger value="classification">分级筛查</TabsTrigger>
              <TabsTrigger value="trends">趋势追踪</TabsTrigger>
              <TabsTrigger value="alerts">预警监控</TabsTrigger>
            </TabsList>

            <TabsContent value="overview">
              <div className="space-y-6">
                {/* 情感分布图表 */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <Card>
                    <CardHeader className="py-3">
                      <CardTitle className="text-base">各维度情感分布</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        {[
                          { dimension: "视觉效果", positive: 92, negative: 3, neutral: 5 },
                          { dimension: "游戏玩法", positive: 68, negative: 22, neutral: 10 },
                          { dimension: "故事剧情", positive: 45, negative: 35, neutral: 20 },
                          { dimension: "技术表现", positive: 30, negative: 60, neutral: 10 },
                          { dimension: "游戏设计", positive: 65, negative: 20, neutral: 15 },
                        ].map((item, i) => (
                          <div key={i} className="space-y-1">
                            <div className="flex justify-between text-sm">
                              <span className="font-medium">{item.dimension}</span>
                              <div className="flex gap-4 text-xs">
                                <span className="text-green-600">{item.positive}%</span>
                                <span className="text-red-600">{item.negative}%</span>
                                <span className="text-gray-600">{item.neutral}%</span>
                              </div>
                            </div>
                            <div className="flex h-4 overflow-hidden rounded">
                              <div className="bg-green-500" style={{ width: `${item.positive}%` }}></div>
                              <div className="bg-red-500" style={{ width: `${item.negative}%` }}></div>
                              <div className="bg-gray-500" style={{ width: `${item.neutral}%` }}></div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader className="py-3">
                      <CardTitle className="text-base">平台分布</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        {[
                          { platform: "哔哩哔哩", count: 562, percent: 45, color: "bg-orange-500" },
                          { platform: "百度贴吧", count: 374, percent: 30, color: "bg-blue-500" },
                          { platform: "微博", count: 187, percent: 15, color: "bg-pink-500" },
                          { platform: "小红书", count: 87, percent: 7, color: "bg-red-500" },
                          { platform: "抖音", count: 38, percent: 3, color: "bg-purple-500" },
                        ].map((item, i) => (
                          <div key={i} className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <div className={`w-3 h-3 rounded ${item.color}`}></div>
                              <span className="text-sm">{item.platform}</span>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="text-sm text-muted-foreground">{item.count}条</span>
                              <span className="text-sm font-medium">{item.percent}%</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {/* 热点话题 */}
                <Card>
                  <CardHeader className="py-3">
                    <CardTitle className="text-base">热点话题</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="space-y-3">
                        {[
                          { topic: "画面质量", count: 342, trend: "+12%", sentiment: "positive" },
                          { topic: "游戏优化", count: 256, trend: "+8%", sentiment: "negative" },
                          { topic: "剧情设计", count: 187, trend: "-3%", sentiment: "neutral" },
                          { topic: "战斗系统", count: 145, trend: "+5%", sentiment: "positive" },
                          { topic: "开放世界", count: 132, trend: "+2%", sentiment: "positive" },
                        ].map((item, i) => (
                          <div key={i} className="flex items-center justify-between p-3 border rounded">
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-sm">{i + 1}.</span>
                              <span>{item.topic}</span>
                              <Badge
                                className={
                                  item.sentiment === "positive"
                                    ? "bg-green-500"
                                    : item.sentiment === "negative"
                                      ? "bg-red-500"
                                      : "bg-gray-500"
                                }
                              >
                                {item.sentiment === "positive"
                                  ? "正面"
                                  : item.sentiment === "negative"
                                    ? "负面"
                                    : "中性"}
                              </Badge>
                            </div>
                            <div className="flex items-center gap-4">
                              <span className="text-sm text-muted-foreground">{item.count}次提及</span>
                              <span
                                className={`text-xs ${item.trend.startsWith("+") ? "text-green-600" : "text-red-600"}`}
                              >
                                {item.trend}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>

                      <div className="flex flex-wrap gap-2 items-center justify-center">
                        {[
                          { word: "画面", size: "text-3xl", weight: "font-bold", color: "text-orange-500" },
                          { word: "优化", size: "text-2xl", weight: "font-semibold", color: "text-red-500" },
                          { word: "剧情", size: "text-xl", weight: "font-medium", color: "text-blue-500" },
                          { word: "战斗", size: "text-lg", weight: "font-medium", color: "text-green-500" },
                          { word: "开放世界", size: "text-xl", weight: "font-semibold", color: "text-purple-500" },
                          { word: "任务", size: "text-base", weight: "font-normal", color: "text-gray-500" },
                          { word: "育碧", size: "text-2xl", weight: "font-bold", color: "text-blue-600" },
                          { word: "幻影刺客", size: "text-xl", weight: "font-medium", color: "text-orange-600" },
                          { word: "卡顿", size: "text-lg", weight: "font-medium", color: "text-red-600" },
                          { word: "角色", size: "text-base", weight: "font-normal", color: "text-green-600" },
                        ].map((item, i) => (
                          <span
                            key={i}
                            className={`${item.size} ${item.weight} ${item.color} px-2 py-1 cursor-pointer hover:opacity-80`}
                          >
                            {item.word}
                          </span>
                        ))}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            <TabsContent value="classification">
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <div className="flex gap-2">
                    <Select value={platformFilter} onValueChange={setPlatformFilter}>
                      <SelectTrigger className="w-[150px]">
                        <SelectValue placeholder="平台筛选" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">所有平台</SelectItem>
                        <SelectItem value="哔哩哔哩">哔哩哔哩</SelectItem>
                        <SelectItem value="百度贴吧">百度贴吧</SelectItem>
                        <SelectItem value="微博">微博</SelectItem>
                        <SelectItem value="小红书">小红书</SelectItem>
                        <SelectItem value="抖音">抖音</SelectItem>
                      </SelectContent>
                    </Select>

                    <Select value={dimensionFilter} onValueChange={setDimensionFilter}>
                      <SelectTrigger className="w-[150px]">
                        <SelectValue placeholder="维度筛选" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">所有维度</SelectItem>
                        <SelectItem value="视觉效果">视觉效果</SelectItem>
                        <SelectItem value="游戏玩法">游戏玩法</SelectItem>
                        <SelectItem value="故事剧情">故事剧情</SelectItem>
                        <SelectItem value="技术表现">技术表现</SelectItem>
                        <SelectItem value="游戏设计">游戏设计</SelectItem>
                        <SelectItem value="音频体验">音频体验</SelectItem>
                      </SelectContent>
                    </Select>

                    <Select value={sentimentFilter} onValueChange={setSentimentFilter}>
                      <SelectTrigger className="w-[150px]">
                        <SelectValue placeholder="情感筛选" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">所有情感</SelectItem>
                        <SelectItem value="positive">正面</SelectItem>
                        <SelectItem value="negative">负面</SelectItem>
                        <SelectItem value="neutral">中性</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <Button variant="outline" size="sm">
                    <Download className="mr-2 h-4 w-4" />
                    导出数据
                  </Button>
                </div>

                <Tabs defaultValue="all">
                  <TabsList>
                    <TabsTrigger value="all">全部评论</TabsTrigger>
                    <TabsTrigger value="positive">正面评论</TabsTrigger>
                    <TabsTrigger value="negative">负面评论</TabsTrigger>
                    <TabsTrigger value="neutral">中性评论</TabsTrigger>
                  </TabsList>

                  <TabsContent value="all" className="mt-4">
                    {renderCommentList()}
                  </TabsContent>
                  <TabsContent value="positive" className="mt-4">
                    {renderCommentList("positive")}
                  </TabsContent>
                  <TabsContent value="negative" className="mt-4">
                    {renderCommentList("negative")}
                  </TabsContent>
                  <TabsContent value="neutral" className="mt-4">
                    {renderCommentList("neutral")}
                  </TabsContent>
                </Tabs>
              </div>
            </TabsContent>

            <TabsContent value="trends">
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <div className="space-x-2">
                    <Button variant="outline" size="sm">
                      日
                    </Button>
                    <Button variant="outline" size="sm" className="bg-muted">
                      周
                    </Button>
                    <Button variant="outline" size="sm">
                      月
                    </Button>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm">
                      <Download className="mr-2 h-4 w-4" />
                      导出数据
                    </Button>
                  </div>
                </div>

                <div className="border rounded-md p-4">
                  <div className="h-80 flex items-center justify-center">
                    <div className="text-center">
                      <BarChart3 className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
                      <p className="text-muted-foreground">情感趋势图表</p>
                      <p className="text-sm text-muted-foreground">展示正面、负面、中性评论随时间的变化趋势</p>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <Card>
                    <CardHeader className="py-3">
                      <CardTitle className="text-base">情感趋势</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span>正面情感</span>
                          <span className="font-medium">65%</span>
                        </div>
                        <Progress value={65} className="h-2" />

                        <div className="flex justify-between text-sm">
                          <span>负面情感</span>
                          <span className="font-medium">20%</span>
                        </div>
                        <Progress value={20} className="h-2" />

                        <div className="flex justify-between text-sm">
                          <span>中性情感</span>
                          <span className="font-medium">15%</span>
                        </div>
                        <Progress value={15} className="h-2" />
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader className="py-3">
                      <CardTitle className="text-base">平台活跃度</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span>哔哩哔哩</span>
                          <span className="font-medium">45%</span>
                        </div>
                        <Progress value={45} className="h-2 bg-orange-100" indicatorClassName="bg-orange-500" />

                        <div className="flex justify-between text-sm">
                          <span>百度贴吧</span>
                          <span className="font-medium">30%</span>
                        </div>
                        <Progress value={30} className="h-2 bg-blue-100" indicatorClassName="bg-blue-500" />

                        <div className="flex justify-between text-sm">
                          <span>微博</span>
                          <span className="font-medium">15%</span>
                        </div>
                        <Progress value={15} className="h-2 bg-pink-100" indicatorClassName="bg-pink-500" />
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader className="py-3">
                      <CardTitle className="text-base">用户活跃度</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span>新增讨论</span>
                          <span className="font-medium">+124</span>
                        </div>
                        <Progress value={60} className="h-2" />

                        <div className="flex justify-between text-sm">
                          <span>活跃用户</span>
                          <span className="font-medium">+86</span>
                        </div>
                        <Progress value={40} className="h-2" />

                        <div className="flex justify-between text-sm">
                          <span>互动率</span>
                          <span className="font-medium">32%</span>
                        </div>
                        <Progress value={32} className="h-2" />
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="alerts">
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <h3 className="font-medium">预警监控设置</h3>
                  <Button>添加预警规则</Button>
                </div>

                <Card>
                  <CardContent className="p-0">
                    <div className="divide-y">
                      <div className="p-4 flex items-center justify-between">
                        <div className="flex items-start gap-3">
                          <div className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center text-red-600">
                            <AlertCircle className="h-5 w-5" />
                          </div>
                          <div>
                            <h4 className="font-medium">负面评论激增预警</h4>
                            <p className="text-sm text-muted-foreground">当负面评论在1小时内增加超过20%时触发</p>
                          </div>
                        </div>
                        <Badge>已启用</Badge>
                      </div>

                      <div className="p-4 flex items-center justify-between">
                        <div className="flex items-start gap-3">
                          <div className="w-8 h-8 rounded-full bg-orange-100 flex items-center justify-center text-orange-600">
                            <AlertCircle className="h-5 w-5" />
                          </div>
                          <div>
                            <h4 className="font-medium">关键词监控预警</h4>
                            <p className="text-sm text-muted-foreground">监控"崩溃"、"bug"、"退款"等关键词</p>
                          </div>
                        </div>
                        <Badge>已启用</Badge>
                      </div>

                      <div className="p-4 flex items-center justify-between">
                        <div className="flex items-start gap-3">
                          <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-600">
                            <AlertCircle className="h-5 w-5" />
                          </div>
                          <div>
                            <h4 className="font-medium">热点话题预警</h4>
                            <p className="text-sm text-muted-foreground">当某个话题在短时间内讨论量激增时触发</p>
                          </div>
                        </div>
                        <Badge variant="outline">已禁用</Badge>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="py-3">
                    <CardTitle className="text-base">最近预警记录</CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    <div className="divide-y">
                      <div className="p-4 flex items-center justify-between">
                        <div className="flex items-start gap-3">
                          <div className="w-2 h-2 rounded-full bg-red-500 mt-2"></div>
                          <div>
                            <h4 className="font-medium">负面评论激增</h4>
                            <p className="text-sm text-muted-foreground">
                              2025-04-15 14:32 - 关于游戏优化问题的负面评论增加了25%
                            </p>
                          </div>
                        </div>
                        <Button variant="ghost" size="sm" className="gap-1">
                          查看详情
                          <ArrowUpRight className="h-4 w-4" />
                        </Button>
                      </div>

                      <div className="p-4 flex items-center justify-between">
                        <div className="flex items-start gap-3">
                          <div className="w-2 h-2 rounded-full bg-orange-500 mt-2"></div>
                          <div>
                            <h4 className="font-medium">关键词监控触发</h4>
                            <p className="text-sm text-muted-foreground">
                              2025-04-12 09:15 - 检测到多条包含"崩溃"关键词的评论
                            </p>
                          </div>
                        </div>
                        <Button variant="ghost" size="sm" className="gap-1">
                          查看详情
                          <ArrowUpRight className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  )
}
