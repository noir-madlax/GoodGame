"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { AlertCircle, ArrowUpRight, BarChart3, Clock, Download, Filter, MessageSquare, TrendingUp } from "lucide-react"
import { Progress } from "@/components/ui/progress"
import { TrendCharts } from "@/components/trend-charts"

export function TrainingCenter() {
  const [activeTab, setActiveTab] = useState("trends")

  return (
    <div className="grid gap-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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

        <Card className="bg-blue-50">
          <CardHeader className="pb-2">
            <CardTitle className="text-blue-700 flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              热门话题
            </CardTitle>
            <CardDescription className="text-blue-600">画面质量</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between text-xs text-blue-600">
              <span>提及次数</span>
              <span className="flex items-center">342 次</span>
            </div>
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

      <Card>
        <CardHeader>
          <CardTitle>舆情趋势追踪</CardTitle>
          <CardDescription>实时监控舆情变化趋势</CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="trends" value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="mb-4">
              <TabsTrigger value="trends">趋势分析</TabsTrigger>
              <TabsTrigger value="topics">热点话题</TabsTrigger>
              <TabsTrigger value="alerts">预警监控</TabsTrigger>
            </TabsList>

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
                  <TrendChart />
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
                      <CardTitle className="text-base">平台分布</CardTitle>
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

            <TabsContent value="topics">
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <div className="space-x-2">
                    <Select defaultValue="week">
                      <SelectTrigger className="w-[180px]">
                        <SelectValue placeholder="选择时间范围" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="day">今日</SelectItem>
                        <SelectItem value="week">本周</SelectItem>
                        <SelectItem value="month">本月</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <Button variant="outline" size="sm">
                    <Filter className="mr-2 h-4 w-4" />
                    筛选
                  </Button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Card>
                    <CardHeader className="py-3">
                      <CardTitle className="text-base">热门话题</CardTitle>
                    </CardHeader>
                    <CardContent className="p-0">
                      <div className="divide-y">
                        {[
                          { topic: "画面质量", count: 342, trend: "+12%" },
                          { topic: "游戏优化", count: 256, trend: "+8%" },
                          { topic: "剧情设计", count: 187, trend: "-3%" },
                          { topic: "战斗系统", count: 145, trend: "+5%" },
                          { topic: "开放世界", count: 132, trend: "+2%" },
                        ].map((item, i) => (
                          <div key={i} className="flex items-center justify-between p-3">
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-sm">{i + 1}.</span>
                              <span>{item.topic}</span>
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
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader className="py-3">
                      <CardTitle className="text-base">关键词云</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="h-[250px] flex flex-wrap gap-2 items-center justify-center">
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
                          { word: "音效", size: "text-sm", weight: "font-normal", color: "text-purple-600" },
                          { word: "配置", size: "text-lg", weight: "font-medium", color: "text-red-500" },
                          { word: "体验", size: "text-xl", weight: "font-medium", color: "text-blue-500" },
                          { word: "创新", size: "text-base", weight: "font-normal", color: "text-green-500" },
                          { word: "价格", size: "text-sm", weight: "font-normal", color: "text-gray-500" },
                        ].map((item, i) => (
                          <span
                            key={i}
                            className={`${item.size} ${item.weight} ${item.color} px-2 py-1 cursor-pointer hover:opacity-80`}
                          >
                            {item.word}
                          </span>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </div>

                <Card>
                  <CardHeader className="py-3">
                    <CardTitle className="text-base">话题关联分析</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-[300px] flex items-center justify-center text-muted-foreground">
                      [话题关联图表 - 展示不同话题之间的关联关系]
                    </div>
                  </CardContent>
                </Card>
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

function TrendChart() {
  return <TrendCharts />
}
