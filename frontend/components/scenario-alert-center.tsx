"use client"

import { useState, useEffect, useRef } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  AlertCircle,
  Bug,
  Heart,
  Lightbulb,
  Bell,
  Settings,
  Plus,
  CheckCircle,
  TrendingUp,
  TrendingDown,
  ArrowUpRight,
} from "lucide-react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"

export function ScenarioAlertCenter() {
  const [timeRange, setTimeRange] = useState("7d")
  const alertTrendChartRef = useRef<HTMLCanvasElement>(null)

  // 模拟场景预警数据
  const scenarioAlerts = [
    {
      id: 1,
      type: "negative_surge",
      title: "负面舆情激增",
      description: "游戏优化问题相关负面评论在过去2小时内增长35%",
      severity: "high",
      icon: AlertCircle,
      color: "text-red-600",
      bgColor: "bg-red-50",
      action: "立即公关",
      time: "2小时前",
      status: "active",
      category: "public_relations",
      trend: {
        direction: "up",
        value: 35,
      },
      relatedComments: 124,
    },
    {
      id: 2,
      type: "bug_report",
      title: "技术问题反馈",
      description: "检测到多个关于存档丢失的bug报告，需要开发团队关注",
      severity: "medium",
      icon: Bug,
      color: "text-orange-600",
      bgColor: "bg-orange-50",
      action: "技术修复",
      time: "4小时前",
      status: "active",
      category: "technical",
      trend: {
        direction: "up",
        value: 28,
      },
      relatedComments: 87,
    },
    {
      id: 3,
      type: "viral_meme",
      title: "玩家梗爆火",
      description: "巴辛姆的某个动作成为热门梗，传播度很高",
      severity: "low",
      icon: Heart,
      color: "text-pink-600",
      bgColor: "bg-pink-50",
      action: "营销机会",
      time: "6小时前",
      status: "active",
      category: "marketing",
      trend: {
        direction: "up",
        value: 156,
      },
      relatedComments: 342,
    },
    {
      id: 4,
      type: "feature_request",
      title: "功能改进建议",
      description: "玩家普遍希望增加快速旅行功能，可作为下版本参考",
      severity: "low",
      icon: Lightbulb,
      color: "text-blue-600",
      bgColor: "bg-blue-50",
      action: "产品反馈",
      time: "1天前",
      status: "active",
      category: "product",
      trend: {
        direction: "stable",
        value: 12,
      },
      relatedComments: 56,
    },
    {
      id: 5,
      type: "negative_surge",
      title: "直播卡顿问题",
      description: "多位主播直播时出现游戏卡顿，引发负面讨论",
      severity: "medium",
      icon: AlertCircle,
      color: "text-red-600",
      bgColor: "bg-red-50",
      action: "技术修复",
      time: "8小时前",
      status: "resolved",
      category: "technical",
      trend: {
        direction: "down",
        value: 15,
      },
      relatedComments: 78,
    },
    {
      id: 6,
      type: "viral_meme",
      title: "玩家创意内容",
      description: "玩家创作的游戏同人视频获得大量点赞和转发",
      severity: "low",
      icon: Heart,
      color: "text-pink-600",
      bgColor: "bg-pink-50",
      action: "营销机会",
      time: "2天前",
      status: "resolved",
      category: "marketing",
      trend: {
        direction: "down",
        value: 8,
      },
      relatedComments: 245,
    },
  ]

  // 预警规则
  const alertRules = [
    {
      id: 1,
      name: "负面评论激增预警",
      description: "当负面评论在1小时内增加超过20%时触发",
      category: "public_relations",
      severity: "high",
      enabled: true,
    },
    {
      id: 2,
      name: "关键词监控预警",
      description: "监控崩溃、bug、退款等关键词",
      category: "technical",
      severity: "medium",
      enabled: true,
    },
    {
      id: 3,
      name: "热点话题预警",
      description: "当某个话题在短时间内讨论量激增时触发",
      category: "marketing",
      severity: "low",
      enabled: false,
    },
    {
      id: 4,
      name: "玩家建议聚合",
      description: "当多个玩家提出相似功能建议时触发",
      category: "product",
      severity: "low",
      enabled: true,
    },
  ]

  // 统计数据
  const alertStats = {
    total: 24,
    active: 4,
    resolved: 20,
    byCategory: {
      public_relations: 8,
      technical: 10,
      marketing: 4,
      product: 2,
    },
    bySeverity: {
      high: 5,
      medium: 12,
      low: 7,
    },
    trend: [
      { date: "04-13", count: 2, pr: 1, tech: 1, marketing: 0, product: 0 },
      { date: "04-14", count: 3, pr: 1, tech: 1, marketing: 1, product: 0 },
      { date: "04-15", count: 5, pr: 2, tech: 2, marketing: 0, product: 1 },
      { date: "04-16", count: 8, pr: 3, tech: 3, marketing: 1, product: 1 },
      { date: "04-17", count: 4, pr: 1, tech: 2, marketing: 1, product: 0 },
      { date: "04-18", count: 1, pr: 0, tech: 1, marketing: 0, product: 0 },
      { date: "04-19", count: 1, pr: 0, tech: 0, marketing: 1, product: 0 },
    ],
  }

  useEffect(() => {
    drawAlertTrendChart()
  }, [])

  const drawAlertTrendChart = () => {
    const canvas = alertTrendChartRef.current
    if (!canvas) return

    const ctx = canvas.getContext("2d")
    if (!ctx) return

    // 设置画布尺寸
    canvas.width = 800
    canvas.height = 300

    // 清除画布
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    // 定义图表区域
    const padding = 40
    const chartWidth = canvas.width - padding * 2
    const chartHeight = canvas.height - padding * 2

    // 绘制坐标轴
    ctx.beginPath()
    ctx.moveTo(padding, padding)
    ctx.lineTo(padding, canvas.height - padding)
    ctx.lineTo(canvas.width - padding, canvas.height - padding)
    ctx.strokeStyle = "#e5e7eb"
    ctx.lineWidth = 1
    ctx.stroke()

    // 绘制网格线
    for (let i = 1; i <= 4; i++) {
      const y = padding + (i * chartHeight) / 5
      ctx.beginPath()
      ctx.moveTo(padding, y)
      ctx.lineTo(canvas.width - padding, y)
      ctx.strokeStyle = "#f3f4f6"
      ctx.lineWidth = 1
      ctx.stroke()
    }

    // 计算最大值
    const maxCount = Math.max(...alertStats.trend.map((item) => item.count))
    const barWidth = (chartWidth / alertStats.trend.length) * 0.7
    const barSpacing = (chartWidth / alertStats.trend.length) * 0.3

    // 绘制柱状图
    alertStats.trend.forEach((item, index) => {
      const x = padding + index * (barWidth + barSpacing) + barSpacing / 2

      // 绘制公关预警柱形
      const prHeight = (item.pr / maxCount) * chartHeight
      ctx.fillStyle = "#ef4444" // 红色
      ctx.fillRect(x, canvas.height - padding - prHeight, barWidth / 4, prHeight)

      // 绘制技术预警柱形
      const techHeight = (item.tech / maxCount) * chartHeight
      ctx.fillStyle = "#f97316" // 橙色
      ctx.fillRect(x + barWidth / 4, canvas.height - padding - techHeight, barWidth / 4, techHeight)

      // 绘制营销预警柱形
      const marketingHeight = (item.marketing / maxCount) * chartHeight
      ctx.fillStyle = "#ec4899" // 粉色
      ctx.fillRect(x + barWidth / 2, canvas.height - padding - marketingHeight, barWidth / 4, marketingHeight)

      // 绘制产品预警柱形
      const productHeight = (item.product / maxCount) * chartHeight
      ctx.fillStyle = "#3b82f6" // 蓝色
      ctx.fillRect(x + (barWidth * 3) / 4, canvas.height - padding - productHeight, barWidth / 4, productHeight)

      // 绘制总数曲线
      if (index === 0) {
        ctx.beginPath()
        ctx.moveTo(x + barWidth / 2, canvas.height - padding - (item.count / maxCount) * chartHeight)
      } else {
        ctx.lineTo(x + barWidth / 2, canvas.height - padding - (item.count / maxCount) * chartHeight)
      }
    })

    // 完成总数曲线
    ctx.strokeStyle = "#6b7280"
    ctx.lineWidth = 2
    ctx.stroke()

    // 添加数据点
    alertStats.trend.forEach((item, index) => {
      const x = padding + index * (barWidth + barSpacing) + barSpacing / 2 + barWidth / 2
      const y = canvas.height - padding - (item.count / maxCount) * chartHeight

      ctx.beginPath()
      ctx.arc(x, y, 4, 0, 2 * Math.PI)
      ctx.fillStyle = "#6b7280"
      ctx.fill()
    })

    // 添加日期标签
    ctx.fillStyle = "#6b7280"
    ctx.font = "12px Arial"
    ctx.textAlign = "center"
    ctx.textBaseline = "top"

    alertStats.trend.forEach((item, index) => {
      const x = padding + index * (barWidth + barSpacing) + barSpacing / 2 + barWidth / 2
      ctx.fillText(item.date, x, canvas.height - padding + 10)
    })

    // 添加Y轴标签
    ctx.textAlign = "right"
    ctx.textBaseline = "middle"
    for (let i = 0; i <= 5; i++) {
      const y = canvas.height - padding - (i * chartHeight) / 5
      const value = Math.round((i * maxCount) / 5).toString()
      ctx.fillText(value, padding - 10, y)
    }

    // 添加图例
    const legendY = 20
    const legendSpacing = 100
    ctx.textAlign = "left"
    ctx.textBaseline = "middle"

    // 总数图例
    ctx.beginPath()
    ctx.moveTo(padding, legendY)
    ctx.lineTo(padding + 20, legendY)
    ctx.strokeStyle = "#6b7280"
    ctx.lineWidth = 2
    ctx.stroke()
    ctx.beginPath()
    ctx.arc(padding + 10, legendY, 4, 0, 2 * Math.PI)
    ctx.fillStyle = "#6b7280"
    ctx.fill()
    ctx.fillStyle = "#6b7280"
    ctx.fillText("总数", padding + 25, legendY)

    // 公关图例
    ctx.fillStyle = "#ef4444"
    ctx.fillRect(padding + legendSpacing, legendY - 5, 10, 10)
    ctx.fillStyle = "#6b7280"
    ctx.fillText("公关", padding + legendSpacing + 15, legendY)

    // 技术图例
    ctx.fillStyle = "#f97316"
    ctx.fillRect(padding + legendSpacing * 2, legendY - 5, 10, 10)
    ctx.fillStyle = "#6b7280"
    ctx.fillText("技术", padding + legendSpacing * 2 + 15, legendY)

    // 营销图例
    ctx.fillStyle = "#ec4899"
    ctx.fillRect(padding + legendSpacing * 3, legendY - 5, 10, 10)
    ctx.fillStyle = "#6b7280"
    ctx.fillText("营销", padding + legendSpacing * 3 + 15, legendY)

    // 产品图例
    ctx.fillStyle = "#3b82f6"
    ctx.fillRect(padding + legendSpacing * 4, legendY - 5, 10, 10)
    ctx.fillStyle = "#6b7280"
    ctx.fillText("产品", padding + legendSpacing * 4 + 15, legendY)
  }

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case "high":
        return <Badge className="bg-red-500">紧急</Badge>
      case "medium":
        return <Badge className="bg-orange-500">重要</Badge>
      case "low":
        return <Badge className="bg-blue-500">关注</Badge>
      default:
        return <Badge className="bg-gray-500">一般</Badge>
    }
  }

  const getCategoryBadge = (category: string) => {
    switch (category) {
      case "public_relations":
        return (
          <Badge variant="outline" className="border-red-200 text-red-700">
            公关
          </Badge>
        )
      case "technical":
        return (
          <Badge variant="outline" className="border-orange-200 text-orange-700">
            技术
          </Badge>
        )
      case "marketing":
        return (
          <Badge variant="outline" className="border-pink-200 text-pink-700">
            营销
          </Badge>
        )
      case "product":
        return (
          <Badge variant="outline" className="border-blue-200 text-blue-700">
            产品
          </Badge>
        )
      default:
        return <Badge variant="outline">其他</Badge>
    }
  }

  const getTrendIcon = (trend: { direction: string; value: number }) => {
    if (trend.direction === "up") {
      return <TrendingUp className="h-4 w-4 text-red-600" />
    } else if (trend.direction === "down") {
      return <TrendingDown className="h-4 w-4 text-green-600" />
    } else {
      return <div className="h-4 w-4" />
    }
  }

  return (
    <div className="space-y-6">
      {/* 预警概览 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-gray-700 flex items-center gap-2">
              <Bell className="h-5 w-5" />
              总预警数
            </CardTitle>
            <CardDescription className="text-gray-600">{alertStats.total} 条</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between text-xs text-gray-600">
              <span>本周期内</span>
              <span className="flex items-center">{alertStats.trend[alertStats.trend.length - 1].count} 条今日</span>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-red-50">
          <CardHeader className="pb-2">
            <CardTitle className="text-red-700 flex items-center gap-2">
              <AlertCircle className="h-5 w-5" />
              紧急预警
            </CardTitle>
            <CardDescription className="text-red-600">{alertStats.bySeverity.high} 条</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between text-xs text-red-600">
              <span>需立即处理</span>
              <span className="flex items-center">{alertStats.active} 条活跃</span>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-orange-50">
          <CardHeader className="pb-2">
            <CardTitle className="text-orange-700 flex items-center gap-2">
              <Bug className="h-5 w-5" />
              技术问题
            </CardTitle>
            <CardDescription className="text-orange-600">{alertStats.byCategory.technical} 条</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between text-xs text-orange-600">
              <span>需开发关注</span>
              <span className="flex items-center">{alertStats.byCategory.technical - 2} 条已解决</span>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-pink-50">
          <CardHeader className="pb-2">
            <CardTitle className="text-pink-700 flex items-center gap-2">
              <Heart className="h-5 w-5" />
              营销机会
            </CardTitle>
            <CardDescription className="text-pink-600">{alertStats.byCategory.marketing} 条</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between text-xs text-pink-600">
              <span>可利用热点</span>
              <span className="flex items-center">{alertStats.byCategory.marketing - 1} 条已处理</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 预警趋势图 */}
      <Card>
        <CardHeader>
          <CardTitle>预警趋势</CardTitle>
          <CardDescription>过去7天的预警触发情况</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[300px] flex items-center justify-center">
            <canvas ref={alertTrendChartRef} className="w-full h-full" />
          </div>
        </CardContent>
      </Card>

      {/* 主要内容区域 */}
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <div>
              <CardTitle>场景化预警中心</CardTitle>
              <CardDescription>基于业务场景的智能预警和处理建议</CardDescription>
            </div>
            <Select value={timeRange} onValueChange={setTimeRange}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="时间范围" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1d">今日</SelectItem>
                <SelectItem value="7d">近7天</SelectItem>
                <SelectItem value="30d">近30天</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="active">
            <TabsList className="mb-4">
              <TabsTrigger value="active">活跃预警</TabsTrigger>
              <TabsTrigger value="resolved">已解决</TabsTrigger>
              <TabsTrigger value="rules">预警设置</TabsTrigger>
              <TabsTrigger value="history">预警记录</TabsTrigger>
            </TabsList>

            <TabsContent value="active">
              <div className="space-y-4">
                {scenarioAlerts
                  .filter((alert) => alert.status === "active")
                  .map((alert) => {
                    const IconComponent = alert.icon
                    return (
                      <div key={alert.id} className={`p-4 rounded-lg border ${alert.bgColor}`}>
                        <div className="flex items-start justify-between">
                          <div className="flex items-start gap-3">
                            <div
                              className={`w-8 h-8 rounded-full bg-white flex items-center justify-center ${alert.color}`}
                            >
                              <IconComponent className="h-5 w-5" />
                            </div>
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <h4 className="font-medium">{alert.title}</h4>
                                {getSeverityBadge(alert.severity)}
                                {getCategoryBadge(alert.category)}
                                <span className="text-xs text-muted-foreground">{alert.time}</span>
                              </div>
                              <p className="text-sm text-muted-foreground mb-2">{alert.description}</p>
                              <div className="flex items-center gap-4 mb-2">
                                <div className="flex items-center gap-1 text-sm">
                                  {getTrendIcon(alert.trend)}
                                  <span className={alert.trend.direction === "up" ? "text-red-600" : "text-green-600"}>
                                    {alert.trend.direction === "up" ? "+" : ""}
                                    {alert.trend.value}%
                                  </span>
                                </div>
                                <span className="text-sm text-muted-foreground">
                                  {alert.relatedComments} 条相关评论
                                </span>
                              </div>
                              <div className="flex gap-2">
                                <Button size="sm" variant="outline">
                                  查看详情
                                </Button>
                                <Button size="sm" className="bg-orange-500 hover:bg-orange-600">
                                  {alert.action}
                                </Button>
                                <Button size="sm" variant="outline">
                                  标记为已解决
                                </Button>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    )
                  })}
              </div>
            </TabsContent>

            <TabsContent value="resolved">
              <div className="space-y-4">
                {scenarioAlerts
                  .filter((alert) => alert.status === "resolved")
                  .map((alert) => {
                    const IconComponent = alert.icon
                    return (
                      <div key={alert.id} className="p-4 rounded-lg border bg-gray-50">
                        <div className="flex items-start justify-between">
                          <div className="flex items-start gap-3">
                            <div className="w-8 h-8 rounded-full bg-white flex items-center justify-center text-gray-600">
                              <CheckCircle className="h-5 w-5" />
                            </div>
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <h4 className="font-medium">{alert.title}</h4>
                                <Badge variant="outline">已解决</Badge>
                                {getCategoryBadge(alert.category)}
                                <span className="text-xs text-muted-foreground">{alert.time}</span>
                              </div>
                              <p className="text-sm text-muted-foreground mb-2">{alert.description}</p>
                              <div className="flex items-center gap-4 mb-2">
                                <div className="flex items-center gap-1 text-sm">
                                  {getTrendIcon(alert.trend)}
                                  <span className={alert.trend.direction === "up" ? "text-red-600" : "text-green-600"}>
                                    {alert.trend.direction === "up" ? "+" : ""}
                                    {alert.trend.value}%
                                  </span>
                                </div>
                                <span className="text-sm text-muted-foreground">
                                  {alert.relatedComments} 条相关评论
                                </span>
                              </div>
                              <div className="flex gap-2">
                                <Button size="sm" variant="outline">
                                  查看详情
                                </Button>
                                <Button size="sm" variant="outline">
                                  重新激活
                                </Button>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    )
                  })}
              </div>
            </TabsContent>

            <TabsContent value="rules">
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <h3 className="font-medium">预警规则配置</h3>
                  <Button>
                    <Plus className="mr-2 h-4 w-4" />
                    添加规则
                  </Button>
                </div>

                {alertRules.map((rule) => (
                  <Card key={rule.id}>
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <h4 className="font-medium">{rule.name}</h4>
                            {getSeverityBadge(rule.severity)}
                            {getCategoryBadge(rule.category)}
                          </div>
                          <p className="text-sm text-muted-foreground">{rule.description}</p>
                        </div>
                        <div className="flex items-center gap-4">
                          <div className="flex items-center gap-2">
                            <Switch id={`rule-${rule.id}`} checked={rule.enabled} />
                            <Label htmlFor={`rule-${rule.id}`}>{rule.enabled ? "已启用" : "已禁用"}</Label>
                          </div>
                          <Button variant="ghost" size="icon">
                            <Settings className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </TabsContent>

            <TabsContent value="history">
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <h3 className="font-medium">预警历史记录</h3>
                  <div className="flex gap-2">
                    <Select defaultValue="all">
                      <SelectTrigger className="w-[120px]">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">全部</SelectItem>
                        <SelectItem value="high">紧急</SelectItem>
                        <SelectItem value="medium">重要</SelectItem>
                        <SelectItem value="low">关注</SelectItem>
                      </SelectContent>
                    </Select>
                    <Button variant="outline" size="sm">
                      导出记录
                    </Button>
                  </div>
                </div>

                <Card>
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
                            <div className="flex items-center gap-2 mt-1">
                              <Badge className="bg-red-500">紧急</Badge>
                              <Badge variant="outline" className="border-red-200 text-red-700">
                                公关
                              </Badge>
                            </div>
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
                            <div className="flex items-center gap-2 mt-1">
                              <Badge className="bg-orange-500">重要</Badge>
                              <Badge variant="outline" className="border-orange-200 text-orange-700">
                                技术
                              </Badge>
                            </div>
                          </div>
                        </div>
                        <Button variant="ghost" size="sm" className="gap-1">
                          查看详情
                          <ArrowUpRight className="h-4 w-4" />
                        </Button>
                      </div>

                      <div className="p-4 flex items-center justify-between">
                        <div className="flex items-start gap-3">
                          <div className="w-2 h-2 rounded-full bg-pink-500 mt-2"></div>
                          <div>
                            <h4 className="font-medium">热点话题爆发</h4>
                            <p className="text-sm text-muted-foreground">
                              2025-04-10 16:20 - "巴辛姆表情包"话题讨论量激增300%
                            </p>
                            <div className="flex items-center gap-2 mt-1">
                              <Badge className="bg-blue-500">关注</Badge>
                              <Badge variant="outline" className="border-pink-200 text-pink-700">
                                营销
                              </Badge>
                            </div>
                          </div>
                        </div>
                        <Button variant="ghost" size="sm" className="gap-1">
                          查看详情
                          <ArrowUpRight className="h-4 w-4" />
                        </Button>
                      </div>

                      <div className="p-4 flex items-center justify-between">
                        <div className="flex items-start gap-3">
                          <div className="w-2 h-2 rounded-full bg-blue-500 mt-2"></div>
                          <div>
                            <h4 className="font-medium">功能建议聚合</h4>
                            <p className="text-sm text-muted-foreground">
                              2025-04-08 11:45 - 多位玩家建议增加快速旅行功能
                            </p>
                            <div className="flex items-center gap-2 mt-1">
                              <Badge className="bg-blue-500">关注</Badge>
                              <Badge variant="outline" className="border-blue-200 text-blue-700">
                                产品
                              </Badge>
                            </div>
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
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  )
}
