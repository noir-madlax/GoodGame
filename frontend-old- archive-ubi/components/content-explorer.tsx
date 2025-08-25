"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  MessageSquare,
  Download,
  Video,
  Radio,
  FileText,
  Search,
  Filter,
  Calendar,
  SlidersHorizontal,
  Hash,
} from "lucide-react"
import { Progress } from "@/components/ui/progress"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"

// 模拟评论和弹幕数据
const contentData = [
  {
    id: 1,
    content: "刺客信条幻影刺客的画面真的太惊艳了，育碧这次做得很棒！",
    platform: "哔哩哔哩",
    contentType: "评论",
    sourceType: "视频内容",
    date: "2025-04-15",
    sentiment: "positive",
    confidence: 0.92,
    keywords: ["画面", "育碧"],
    dimension: "视觉效果",
    verified: true,
    author: "游戏UP主小明",
    engagement: { likes: 1240, comments: 89, shares: 45 },
    url: "https://www.bilibili.com/video/BV1xx411c7mD",
  },
  {
    id: 2,
    content: "育碧这次的开放世界设计真的很用心，每个角落都有惊喜",
    platform: "百度贴吧",
    contentType: "评论",
    sourceType: "图文内容",
    date: "2025-04-05",
    sentiment: "positive",
    confidence: 0.89,
    keywords: ["开放世界", "育碧"],
    dimension: "游戏设计",
    verified: false,
    author: "玩家A",
    engagement: { likes: 234, comments: 12, shares: 8 },
    url: "https://tieba.baidu.com/p/8521364782",
  },
  {
    id: 3,
    content: "巴辛姆帅炸了！！！",
    platform: "哔哩哔哩",
    contentType: "弹幕",
    sourceType: "视频内容",
    date: "2025-04-12",
    sentiment: "positive",
    confidence: 0.95,
    keywords: ["巴辛姆"],
    dimension: "故事剧情",
    verified: false,
    author: "弹幕用户001",
    engagement: { likes: 0, comments: 0, shares: 0 },
    url: "https://www.bilibili.com/video/BV1xx411c7mD?t=245",
  },
  {
    id: 4,
    content: "直播中体验了新的战斗系统，确实比之前流畅很多",
    platform: "抖音",
    contentType: "评论",
    sourceType: "直播内容",
    date: "2025-04-08",
    sentiment: "positive",
    confidence: 0.91,
    keywords: ["战斗系统", "直播"],
    dimension: "游戏玩法",
    verified: false,
    author: "主播小王",
    engagement: { likes: 890, comments: 156, shares: 67 },
    url: "https://www.douyin.com/video/7234567890123456789",
  },
  {
    id: 5,
    content: "游戏优化还是有问题，高配置电脑都有点卡顿",
    platform: "百度贴吧",
    contentType: "评论",
    sourceType: "图文内容",
    date: "2025-04-12",
    sentiment: "negative",
    confidence: 0.85,
    keywords: ["优化", "卡顿"],
    dimension: "技术表现",
    verified: true,
    author: "玩家B",
    engagement: { likes: 445, comments: 78, shares: 12 },
    url: "https://tieba.baidu.com/p/8521498765",
  },
  {
    id: 6,
    content: "又卡了又卡了",
    platform: "哔哩哔哩",
    contentType: "弹幕",
    sourceType: "直播内容",
    date: "2025-04-08",
    sentiment: "negative",
    confidence: 0.88,
    keywords: ["卡顿"],
    dimension: "技术表现",
    verified: false,
    author: "弹幕用户002",
    engagement: { likes: 0, comments: 0, shares: 0 },
    url: "https://live.bilibili.com/12345?t=1680",
  },
  {
    id: 7,
    content: "弹幕里都在说任务设计太重复，确实有点无聊",
    platform: "哔哩哔哩",
    contentType: "评论",
    sourceType: "视频内容",
    date: "2025-04-10",
    sentiment: "negative",
    confidence: 0.82,
    keywords: ["任务", "重复"],
    dimension: "游戏设计",
    verified: true,
    author: "观众C",
    engagement: { likes: 123, comments: 23, shares: 3 },
    url: "https://www.bilibili.com/video/BV1xx411c7mD?p=2",
  },
  {
    id: 8,
    content: "6666666",
    platform: "抖音",
    contentType: "弹幕",
    sourceType: "直播内容",
    date: "2025-04-14",
    sentiment: "positive",
    confidence: 0.75,
    keywords: ["6"],
    dimension: "游戏玩法",
    verified: false,
    author: "弹幕用户003",
    engagement: { likes: 0, comments: 0, shares: 0 },
    url: "https://www.douyin.com/live/7234567890123456789",
  },
  {
    id: 9,
    content: "剧情设计中规中矩，没有特别惊喜的地方",
    platform: "微博",
    contentType: "评论",
    sourceType: "图文内容",
    date: "2025-04-10",
    sentiment: "neutral",
    confidence: 0.78,
    keywords: ["剧情"],
    dimension: "故事剧情",
    verified: true,
    author: "玩家D",
    engagement: { likes: 89, comments: 12, shares: 4 },
    url: "https://weibo.com/u/7342567891/ILpquvw",
  },
  {
    id: 10,
    content: "还行吧",
    platform: "哔哩哔哩",
    contentType: "弹幕",
    sourceType: "视频内容",
    date: "2025-04-07",
    sentiment: "neutral",
    confidence: 0.65,
    keywords: [],
    dimension: "游戏玩法",
    verified: false,
    author: "弹幕用户004",
    engagement: { likes: 0, comments: 0, shares: 0 },
    url: "https://www.bilibili.com/video/BV1xx411c7mD?t=156",
  },
]

export function ContentExplorer() {
  const [searchTerm, setSearchTerm] = useState("")
  const [platformFilter, setPlatformFilter] = useState("all")
  const [contentTypeFilter, setContentTypeFilter] = useState("all")
  const [sourceTypeFilter, setSourceTypeFilter] = useState("all")
  const [dimensionFilter, setDimensionFilter] = useState("all")
  const [sentimentFilter, setSentimentFilter] = useState("all")
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false)
  const [selectedContent, setSelectedContent] = useState<any>(null)
  const [showContentDetail, setShowContentDetail] = useState(false)

  // 过滤内容
  const filteredContent = contentData.filter((item) => {
    // 搜索词过滤
    const matchesSearch =
      searchTerm === "" ||
      item.content.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.author.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.keywords.some((keyword) => keyword.toLowerCase().includes(searchTerm.toLowerCase()))

    // 平台过滤
    const matchesPlatform = platformFilter === "all" || item.platform === platformFilter

    // 内容类型过滤
    const matchesContentType = contentTypeFilter === "all" || item.contentType === contentTypeFilter

    // 来源类型过滤
    const matchesSourceType = sourceTypeFilter === "all" || item.sourceType === sourceTypeFilter

    // 维度过滤
    const matchesDimension = dimensionFilter === "all" || item.dimension === dimensionFilter

    // 情感过滤
    const matchesSentiment = sentimentFilter === "all" || item.sentiment === sentimentFilter

    return (
      matchesSearch &&
      matchesPlatform &&
      matchesContentType &&
      matchesSourceType &&
      matchesDimension &&
      matchesSentiment
    )
  })

  // 查看内容详情
  const viewContentDetail = (item: any) => {
    setSelectedContent(item)
    setShowContentDetail(true)
  }

  // 获取情感标签
  const getSentimentBadge = (sentiment: string) => {
    switch (sentiment) {
      case "positive":
        return <Badge className="bg-green-500">正面</Badge>
      case "negative":
        return <Badge className="bg-red-500">负面</Badge>
      default:
        return <Badge className="bg-gray-500">中性</Badge>
    }
  }

  // 获取内容类型图标
  const getContentTypeIcon = (contentType: string) => {
    switch (contentType) {
      case "弹幕":
        return <Hash className="h-4 w-4" />
      default:
        return <MessageSquare className="h-4 w-4" />
    }
  }

  // 获取来源类型图标
  const getSourceTypeIcon = (sourceType: string) => {
    switch (sourceType) {
      case "视频内容":
        return <Video className="h-4 w-4" />
      case "直播内容":
        return <Radio className="h-4 w-4" />
      default:
        return <FileText className="h-4 w-4" />
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>内容查询中心</CardTitle>
          <CardDescription>搜索、筛选和分析全网评论和弹幕数据</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {/* 搜索和基础筛选 */}
            <div className="flex flex-col md:flex-row gap-4">
              <div className="flex-1 relative">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="搜索评论、弹幕内容、作者或关键词..."
                  className="pl-8"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>

              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
                  className={showAdvancedFilters ? "bg-muted" : ""}
                >
                  <Filter className="h-4 w-4" />
                </Button>
                <Button variant="outline" size="icon">
                  <Calendar className="h-4 w-4" />
                </Button>
                <Button variant="outline" size="icon">
                  <SlidersHorizontal className="h-4 w-4" />
                </Button>
                <Button variant="outline">
                  <Download className="mr-2 h-4 w-4" />
                  导出
                </Button>
              </div>
            </div>

            {/* 高级筛选 */}
            {showAdvancedFilters && (
              <div className="grid grid-cols-1 md:grid-cols-5 gap-4 p-4 border rounded-md bg-muted/30">
                <div>
                  <label className="text-sm font-medium mb-1 block">平台</label>
                  <Select value={platformFilter} onValueChange={setPlatformFilter}>
                    <SelectTrigger>
                      <SelectValue placeholder="选择平台" />
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
                </div>

                <div>
                  <label className="text-sm font-medium mb-1 block">内容类型</label>
                  <Select value={contentTypeFilter} onValueChange={setContentTypeFilter}>
                    <SelectTrigger>
                      <SelectValue placeholder="选择类型" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">全部</SelectItem>
                      <SelectItem value="评论">评论</SelectItem>
                      <SelectItem value="弹幕">弹幕</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <label className="text-sm font-medium mb-1 block">来源类型</label>
                  <Select value={sourceTypeFilter} onValueChange={setSourceTypeFilter}>
                    <SelectTrigger>
                      <SelectValue placeholder="选择来源" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">全部来源</SelectItem>
                      <SelectItem value="图文内容">图文内容</SelectItem>
                      <SelectItem value="视频内容">视频内容</SelectItem>
                      <SelectItem value="直播内容">直播内容</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <label className="text-sm font-medium mb-1 block">维度</label>
                  <Select value={dimensionFilter} onValueChange={setDimensionFilter}>
                    <SelectTrigger>
                      <SelectValue placeholder="选择维度" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">所有维度</SelectItem>
                      <SelectItem value="视觉效果">视觉效果</SelectItem>
                      <SelectItem value="游戏玩法">游戏玩法</SelectItem>
                      <SelectItem value="故事剧情">故事剧情</SelectItem>
                      <SelectItem value="技术表现">技术表现</SelectItem>
                      <SelectItem value="游戏设计">游戏设计</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <label className="text-sm font-medium mb-1 block">情感倾向</label>
                  <Select value={sentimentFilter} onValueChange={setSentimentFilter}>
                    <SelectTrigger>
                      <SelectValue placeholder="选择情感" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">所有情感</SelectItem>
                      <SelectItem value="positive">正面</SelectItem>
                      <SelectItem value="negative">负面</SelectItem>
                      <SelectItem value="neutral">中性</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            )}

            {/* 内容列表 */}
            <Tabs defaultValue="all">
              <TabsList>
                <TabsTrigger value="all">全部内容</TabsTrigger>
                <TabsTrigger value="comments">评论</TabsTrigger>
                <TabsTrigger value="barrage">弹幕</TabsTrigger>
                <TabsTrigger value="positive">正面</TabsTrigger>
                <TabsTrigger value="negative">负面</TabsTrigger>
              </TabsList>

              <TabsContent value="all" className="mt-4">
                <div className="space-y-4">
                  {filteredContent.map((item) => (
                    <Card key={item.id} className="overflow-hidden">
                      <CardContent className="p-4">
                        <div className="flex justify-between items-start mb-2">
                          <div className="flex items-center gap-2 flex-wrap">
                            <Badge variant="outline">{item.platform}</Badge>
                            <div className="flex items-center gap-1">
                              {getContentTypeIcon(item.contentType)}
                              <Badge variant="secondary">{item.contentType}</Badge>
                            </div>
                            <div className="flex items-center gap-1">
                              {getSourceTypeIcon(item.sourceType)}
                              <Badge variant="outline">{item.sourceType}</Badge>
                            </div>
                            <span className="text-sm text-muted-foreground">{item.date}</span>
                            <Badge variant="secondary">{item.dimension}</Badge>
                            {getSentimentBadge(item.sentiment)}
                          </div>
                          <div className="flex items-center gap-1">
                            <Progress value={item.confidence * 100} className="w-24 h-2" />
                            <span className="text-xs">{(item.confidence * 100).toFixed(0)}%</span>
                          </div>
                        </div>

                        <p className="mb-3 line-clamp-2">{item.content}</p>

                        <div className="flex justify-between items-center">
                          <div className="flex items-center gap-4">
                            <span className="text-sm text-muted-foreground">作者: {item.author}</span>
                            {item.contentType === "评论" && (
                              <div className="flex items-center gap-3 text-sm text-muted-foreground">
                                <span>👍 {item.engagement.likes}</span>
                                <span>💬 {item.engagement.comments}</span>
                                <span>🔄 {item.engagement.shares}</span>
                              </div>
                            )}
                          </div>

                          <Button variant="ghost" size="sm" onClick={() => viewContentDetail(item)}>
                            查看详情
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  ))}

                  {filteredContent.length === 0 && (
                    <div className="flex flex-col items-center justify-center py-12 text-center">
                      <p className="text-muted-foreground mb-2">没有符合条件的内容</p>
                      <p className="text-sm text-muted-foreground">尝试更改筛选条件</p>
                    </div>
                  )}
                </div>
              </TabsContent>

              <TabsContent value="comments" className="mt-4">
                <div className="space-y-4">
                  {filteredContent
                    .filter((item) => item.contentType === "评论")
                    .map((item) => (
                      <Card key={item.id} className="overflow-hidden">
                        <CardContent className="p-4">
                          <div className="flex justify-between items-start mb-2">
                            <div className="flex items-center gap-2 flex-wrap">
                              <Badge variant="outline">{item.platform}</Badge>
                              <div className="flex items-center gap-1">
                                {getContentTypeIcon(item.contentType)}
                                <Badge variant="secondary">{item.contentType}</Badge>
                              </div>
                              <div className="flex items-center gap-1">
                                {getSourceTypeIcon(item.sourceType)}
                                <Badge variant="outline">{item.sourceType}</Badge>
                              </div>
                              <span className="text-sm text-muted-foreground">{item.date}</span>
                              <Badge variant="secondary">{item.dimension}</Badge>
                              {getSentimentBadge(item.sentiment)}
                            </div>
                            <div className="flex items-center gap-1">
                              <Progress value={item.confidence * 100} className="w-24 h-2" />
                              <span className="text-xs">{(item.confidence * 100).toFixed(0)}%</span>
                            </div>
                          </div>

                          <p className="mb-3 line-clamp-2">{item.content}</p>

                          <div className="flex justify-between items-center">
                            <div className="flex items-center gap-4">
                              <span className="text-sm text-muted-foreground">作者: {item.author}</span>
                              <div className="flex items-center gap-3 text-sm text-muted-foreground">
                                <span>👍 {item.engagement.likes}</span>
                                <span>💬 {item.engagement.comments}</span>
                                <span>🔄 {item.engagement.shares}</span>
                              </div>
                            </div>

                            <Button variant="ghost" size="sm" onClick={() => viewContentDetail(item)}>
                              查看详情
                            </Button>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                </div>
              </TabsContent>

              <TabsContent value="barrage" className="mt-4">
                <div className="space-y-4">
                  {filteredContent
                    .filter((item) => item.contentType === "弹幕")
                    .map((item) => (
                      <Card key={item.id} className="overflow-hidden">
                        <CardContent className="p-4">
                          <div className="flex justify-between items-start mb-2">
                            <div className="flex items-center gap-2 flex-wrap">
                              <Badge variant="outline">{item.platform}</Badge>
                              <div className="flex items-center gap-1">
                                {getContentTypeIcon(item.contentType)}
                                <Badge variant="secondary">{item.contentType}</Badge>
                              </div>
                              <div className="flex items-center gap-1">
                                {getSourceTypeIcon(item.sourceType)}
                                <Badge variant="outline">{item.sourceType}</Badge>
                              </div>
                              <span className="text-sm text-muted-foreground">{item.date}</span>
                              <Badge variant="secondary">{item.dimension}</Badge>
                              {getSentimentBadge(item.sentiment)}
                            </div>
                            <div className="flex items-center gap-1">
                              <Progress value={item.confidence * 100} className="w-24 h-2" />
                              <span className="text-xs">{(item.confidence * 100).toFixed(0)}%</span>
                            </div>
                          </div>

                          <p className="mb-3 line-clamp-2">{item.content}</p>

                          <div className="flex justify-between items-center">
                            <div className="flex items-center gap-4">
                              <span className="text-sm text-muted-foreground">作者: {item.author}</span>
                              <span className="text-sm text-muted-foreground">弹幕时间: {item.date}</span>
                            </div>

                            <Button variant="ghost" size="sm" onClick={() => viewContentDetail(item)}>
                              查看详情
                            </Button>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                </div>
              </TabsContent>

              <TabsContent value="positive" className="mt-4">
                <div className="space-y-4">
                  {filteredContent
                    .filter((item) => item.sentiment === "positive")
                    .map((item) => (
                      <Card key={item.id} className="overflow-hidden">
                        <CardContent className="p-4">
                          <div className="flex justify-between items-start mb-2">
                            <div className="flex items-center gap-2 flex-wrap">
                              <Badge variant="outline">{item.platform}</Badge>
                              <div className="flex items-center gap-1">
                                {getContentTypeIcon(item.contentType)}
                                <Badge variant="secondary">{item.contentType}</Badge>
                              </div>
                              <div className="flex items-center gap-1">
                                {getSourceTypeIcon(item.sourceType)}
                                <Badge variant="outline">{item.sourceType}</Badge>
                              </div>
                              <span className="text-sm text-muted-foreground">{item.date}</span>
                              <Badge variant="secondary">{item.dimension}</Badge>
                              {getSentimentBadge(item.sentiment)}
                            </div>
                            <div className="flex items-center gap-1">
                              <Progress value={item.confidence * 100} className="w-24 h-2" />
                              <span className="text-xs">{(item.confidence * 100).toFixed(0)}%</span>
                            </div>
                          </div>

                          <p className="mb-3 line-clamp-2">{item.content}</p>

                          <div className="flex justify-between items-center">
                            <div className="flex items-center gap-4">
                              <span className="text-sm text-muted-foreground">作者: {item.author}</span>
                              {item.contentType === "评论" && (
                                <div className="flex items-center gap-3 text-sm text-muted-foreground">
                                  <span>👍 {item.engagement.likes}</span>
                                  <span>💬 {item.engagement.comments}</span>
                                  <span>🔄 {item.engagement.shares}</span>
                                </div>
                              )}
                            </div>

                            <Button variant="ghost" size="sm" onClick={() => viewContentDetail(item)}>
                              查看详情
                            </Button>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                </div>
              </TabsContent>

              <TabsContent value="negative" className="mt-4">
                <div className="space-y-4">
                  {filteredContent
                    .filter((item) => item.sentiment === "negative")
                    .map((item) => (
                      <Card key={item.id} className="overflow-hidden">
                        <CardContent className="p-4">
                          <div className="flex justify-between items-start mb-2">
                            <div className="flex items-center gap-2 flex-wrap">
                              <Badge variant="outline">{item.platform}</Badge>
                              <div className="flex items-center gap-1">
                                {getContentTypeIcon(item.contentType)}
                                <Badge variant="secondary">{item.contentType}</Badge>
                              </div>
                              <div className="flex items-center gap-1">
                                {getSourceTypeIcon(item.sourceType)}
                                <Badge variant="outline">{item.sourceType}</Badge>
                              </div>
                              <span className="text-sm text-muted-foreground">{item.date}</span>
                              <Badge variant="secondary">{item.dimension}</Badge>
                              {getSentimentBadge(item.sentiment)}
                            </div>
                            <div className="flex items-center gap-1">
                              <Progress value={item.confidence * 100} className="w-24 h-2" />
                              <span className="text-xs">{(item.confidence * 100).toFixed(0)}%</span>
                            </div>
                          </div>

                          <p className="mb-3 line-clamp-2">{item.content}</p>

                          <div className="flex justify-between items-center">
                            <div className="flex items-center gap-4">
                              <span className="text-sm text-muted-foreground">作者: {item.author}</span>
                              {item.contentType === "评论" && (
                                <div className="flex items-center gap-3 text-sm text-muted-foreground">
                                  <span>👍 {item.engagement.likes}</span>
                                  <span>💬 {item.engagement.comments}</span>
                                  <span>🔄 {item.engagement.shares}</span>
                                </div>
                              )}
                            </div>

                            <Button variant="ghost" size="sm" onClick={() => viewContentDetail(item)}>
                              查看详情
                            </Button>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                </div>
              </TabsContent>
            </Tabs>

            {/* 分页 */}
            <div className="flex justify-center mt-6">
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" disabled>
                  上一页
                </Button>
                <Button variant="outline" size="sm" className="bg-muted">
                  1
                </Button>
                <Button variant="outline" size="sm">
                  2
                </Button>
                <Button variant="outline" size="sm">
                  3
                </Button>
                <Button variant="outline" size="sm">
                  下一页
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 内容详情弹窗 */}
      <Dialog open={showContentDetail} onOpenChange={setShowContentDetail}>
        <DialogContent className="max-w-3xl">
          {selectedContent && (
            <>
              <DialogHeader>
                <DialogTitle>{selectedContent.contentType}详情</DialogTitle>
                <DialogDescription>查看完整{selectedContent.contentType}内容和分析</DialogDescription>
              </DialogHeader>

              <div className="space-y-4 mt-4">
                <div className="flex justify-between items-start">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge variant="outline">{selectedContent.platform}</Badge>
                    <div className="flex items-center gap-1">
                      {getContentTypeIcon(selectedContent.contentType)}
                      <Badge variant="secondary">{selectedContent.contentType}</Badge>
                    </div>
                    <div className="flex items-center gap-1">
                      {getSourceTypeIcon(selectedContent.sourceType)}
                      <Badge variant="outline">{selectedContent.sourceType}</Badge>
                    </div>
                    <span className="text-sm text-muted-foreground">{selectedContent.date}</span>
                    <Badge variant="secondary">{selectedContent.dimension}</Badge>
                    {getSentimentBadge(selectedContent.sentiment)}
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="text-xs">置信度:</span>
                    <Progress value={selectedContent.confidence * 100} className="w-24 h-2" />
                    <span className="text-xs">{(selectedContent.confidence * 100).toFixed(0)}%</span>
                  </div>
                </div>

                <div className="p-4 border rounded-md bg-muted/30">
                  <p className="mb-2">{selectedContent.content}</p>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">作者: {selectedContent.author}</span>
                    {selectedContent.contentType === "评论" && (
                      <div className="flex items-center gap-3 text-sm text-muted-foreground">
                        <span>👍 {selectedContent.engagement.likes}</span>
                        <span>💬 {selectedContent.engagement.comments}</span>
                        <span>🔄 {selectedContent.engagement.shares}</span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <h4 className="text-sm font-medium mb-2">关键词分析</h4>
                    <div className="flex flex-wrap gap-2">
                      {selectedContent.keywords.length > 0 ? (
                        selectedContent.keywords.map((keyword: string, idx: number) => (
                          <Badge key={idx} variant="secondary">
                            {keyword}
                          </Badge>
                        ))
                      ) : (
                        <span className="text-sm text-muted-foreground">无关键词</span>
                      )}
                    </div>
                  </div>

                  <div>
                    <h4 className="text-sm font-medium mb-2">情感分析</h4>
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span>正面</span>
                        <span className="font-medium">
                          {selectedContent.sentiment === "positive"
                            ? "85%"
                            : selectedContent.sentiment === "neutral"
                              ? "35%"
                              : "15%"}
                        </span>
                      </div>
                      <Progress
                        value={
                          selectedContent.sentiment === "positive"
                            ? 85
                            : selectedContent.sentiment === "neutral"
                              ? 35
                              : 15
                        }
                        className="h-2 bg-green-100"
                        indicatorClassName="bg-green-500"
                      />

                      <div className="flex justify-between text-sm">
                        <span>负面</span>
                        <span className="font-medium">
                          {selectedContent.sentiment === "negative"
                            ? "80%"
                            : selectedContent.sentiment === "neutral"
                              ? "30%"
                              : "5%"}
                        </span>
                      </div>
                      <Progress
                        value={
                          selectedContent.sentiment === "negative"
                            ? 80
                            : selectedContent.sentiment === "neutral"
                              ? 30
                              : 5
                        }
                        className="h-2 bg-red-100"
                        indicatorClassName="bg-red-500"
                      />

                      <div className="flex justify-between text-sm">
                        <span>中性</span>
                        <span className="font-medium">{selectedContent.sentiment === "neutral" ? "35%" : "10%"}</span>
                      </div>
                      <Progress
                        value={selectedContent.sentiment === "neutral" ? 35 : 10}
                        className="h-2 bg-gray-100"
                        indicatorClassName="bg-gray-500"
                      />
                    </div>
                  </div>
                </div>

                <div>
                  <h4 className="text-sm font-medium mb-2">原始链接</h4>
                  <div className="flex items-center gap-2">
                    <Input value={selectedContent.url} readOnly />
                    <Button variant="outline" size="sm" onClick={() => window.open(selectedContent.url, "_blank")}>
                      访问
                    </Button>
                  </div>
                </div>

                <div className="flex justify-end gap-2">
                  <Button variant="outline">标记为误判</Button>
                  <Button>添加到报告</Button>
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
