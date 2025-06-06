"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Checkbox } from "@/components/ui/checkbox"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Download, FileText, MessageSquare, ThumbsDown, ThumbsUp } from "lucide-react"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"

export function ReportGeneration() {
  const [isGenerating, setIsGenerating] = useState(false)
  const [reportGenerated, setReportGenerated] = useState(false)
  const [activeReportTab, setActiveReportTab] = useState("summary")

  const handleGenerateReport = () => {
    setIsGenerating(true)
    // 模拟报告生成过程
    setTimeout(() => {
      setIsGenerating(false)
      setReportGenerated(true)
    }, 2000)
  }

  return (
    <div className="grid gap-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle>报告配置</CardTitle>
              <CardDescription>配置要生成的舆情分析报告</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="report-title">报告标题</Label>
                <Input id="report-title" defaultValue="刺客信条幻影刺客舆情分析报告" />
              </div>

              <div className="space-y-2">
                <Label htmlFor="report-date">报告日期</Label>
                <Input id="report-date" type="date" defaultValue="2025-04-20" />
              </div>

              <div className="space-y-2">
                <Label>报告内容</Label>
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <Checkbox id="include-summary" defaultChecked />
                    <Label htmlFor="include-summary">舆情概述</Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Checkbox id="include-sentiment" defaultChecked />
                    <Label htmlFor="include-sentiment">情感分析</Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Checkbox id="include-platforms" defaultChecked />
                    <Label htmlFor="include-platforms">平台分布</Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Checkbox id="include-trends" defaultChecked />
                    <Label htmlFor="include-trends">趋势分析</Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Checkbox id="include-topics" defaultChecked />
                    <Label htmlFor="include-topics">热点话题</Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Checkbox id="include-recommendations" defaultChecked />
                    <Label htmlFor="include-recommendations">改进建议</Label>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="report-format">报告格式</Label>
                <Select defaultValue="pdf">
                  <SelectTrigger id="report-format">
                    <SelectValue placeholder="选择报告格式" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="pdf">PDF</SelectItem>
                    <SelectItem value="docx">Word (DOCX)</SelectItem>
                    <SelectItem value="pptx">PowerPoint (PPTX)</SelectItem>
                    <SelectItem value="html">HTML</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
            <CardFooter>
              <Button
                onClick={handleGenerateReport}
                disabled={isGenerating}
                className="w-full bg-orange-500 hover:bg-orange-600"
              >
                {isGenerating ? "生成中..." : "生成报告"}
              </Button>
            </CardFooter>
          </Card>
        </div>

        <div className="md:col-span-2">
          {!reportGenerated ? (
            <Card className="h-full">
              <CardHeader>
                <CardTitle>报告预览</CardTitle>
                <CardDescription>生成的报告预览</CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col items-center justify-center h-[400px] text-center">
                <FileText className="h-16 w-16 text-muted-foreground mb-4" />
                <p className="text-muted-foreground mb-2">尚未生成报告</p>
                <p className="text-sm text-muted-foreground">配置报告参数后点击"生成报告"按钮</p>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardHeader className="border-b">
                <div className="flex justify-between items-center">
                  <div>
                    <CardTitle>刺客信条幻影刺客舆情分析报告</CardTitle>
                    <CardDescription>2025年3月20日 - 2025年4月19日</CardDescription>
                  </div>
                  <Button variant="outline" size="sm">
                    <Download className="mr-2 h-4 w-4" />
                    下载报告
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                <Tabs defaultValue="summary" value={activeReportTab} onValueChange={setActiveReportTab} className="w-full">
                  <TabsList className="w-full justify-start rounded-none border-b bg-transparent p-0">
                    <TabsTrigger
                      value="summary"
                      className="rounded-none border-b-2 border-transparent px-4 py-3 data-[state=active]:border-primary data-[state=active]:bg-transparent"
                    >
                      舆情概述
                    </TabsTrigger>
                    <TabsTrigger
                      value="sentiment"
                      className="rounded-none border-b-2 border-transparent px-4 py-3 data-[state=active]:border-primary data-[state=active]:bg-transparent"
                    >
                      情感分析
                    </TabsTrigger>
                    <TabsTrigger
                      value="topics"
                      className="rounded-none border-b-2 border-transparent px-4 py-3 data-[state=active]:border-primary data-[state=active]:bg-transparent"
                    >
                      热点话题
                    </TabsTrigger>
                    <TabsTrigger
                      value="recommendations"
                      className="rounded-none border-b-2 border-transparent px-4 py-3 data-[state=active]:border-primary data-[state=active]:bg-transparent"
                    >
                      改进建议
                    </TabsTrigger>
                  </TabsList>
                  
                  <TabsContent value="summary" className="p-6">
                    <div className="space-y-6">
                      <div>
                        <h3 className="text-lg font-semibold mb-2">舆情概述</h3>
                        <p className="text-muted-foreground">
                          本报告分析了2025年3月20日至2025年4月19日期间刺客信条幻影刺客的舆情数据，共收集到1,248条相关评论。
                          总体来看，游戏获得了较为积极的评价，正面评论占比65%，负面评论占比20%，中性评论占比15%。
                          用户对游戏的画面质量和开放世界设计给予了高度评价，但对游戏优化和剧情创新方面存在一定的不满。
                        </p>
                      </div>
                      
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <Card>
                          <CardHeader className="py-3">
                            <div className="flex items-center justify-between">
                              <CardTitle className="text-base">情感分布</CardTitle>
                              <ThumbsUp className="h-4 w-4 text-green-500" />
                            </div>
                          </CardHeader>
                          <CardContent className="py-2">
                            <div className="space-y-2">
                              <div className="flex justify-between text-sm">
                                <span>正面评论</span>
                                <span className="font-medium">65%</span>
                              </div>
                              <Progress value={65} className="h-2 bg-green-100" indicatorClassName="bg-green-500" />
                              
                              <div className="flex justify-between text-sm">
                                <span>负面评论</span>
                                <span className="font-medium">20%</span>
                              </div>
                              <Progress value={20} className="h-2 bg-red-100" indicatorClassName="bg-red-500" />
                              
                              <div className="flex justify-between text-sm">
                                <span>中性评论</span>
                                <span className="font-medium">15%</span>
                              </div>
                              <Progress value={15} className="h-2 bg-gray-100" indicatorClassName="bg-gray-500" />
                            </div>
                          </CardContent>
                        </Card>
                        
                        <Card>
                          <CardHeader className="py-3">
                            <div className="flex items-center justify-between">
                              <CardTitle className="text-base">平台分布</CardTitle>
                              <MessageSquare className="h-4 w-4 text-blue-500" />
                            </div>
                          </CardHeader>
                          <CardContent className="py-2">
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
                            <div className="flex items-center justify-between">
                              <CardTitle className="text-base">热点话题</CardTitle>
                              <ThumbsDown className="h-4 w-4 text-red-500" />
                            </div>
                          </CardHeader>
                          <CardContent className="py-2">
                            <div className="space-y-2">
                              <div className="flex justify-between text-sm">
                                <span>画面质量</span>
                                <span className="font-medium">342次</span>
                              </div>
                              <Progress value={85} className="h-2" />
                              
                              <div className="flex justify-between text-sm">
                                <span>游戏优化</span>
                                <span className="font-medium">256次</span>
                              </div>
                              <Progress value={64} className="h-2" />
                              
                              <div className="flex justify-between text-sm">
                                <span>剧情设计</span>
                                <span className="font-medium">187次</span>
                              </div>
                              <Progress value={47} className="h-2" />
                            </div>
                          </CardContent>
                        </Card>
                      </div>
                      
                      <div>
                        <h3 className="text-lg font-semibold mb-2">主要发现</h3>
                        <ul className="list-disc list-inside space-y-1 text-muted-foreground">
                          <li>游戏画面质量获得广泛好评，是最受玩家认可的方面</li>
                          <li>开放世界设计的细节和丰富度受到玩家赞赏</li>
                          <li>游戏优化问题是负面评论的主要来源，特别是在高配置PC上仍存在卡顿现象</li>
                          <li>剧情设计被认为缺乏创新，部分玩家认为过于老套</li>
                          <li>战斗系统相比前作有所改进，但任务设计被认为重复性较高</li>
                        </ul>
                      </div>
                    </div>
                  </TabsContent>
                  
                  <TabsContent value="sentiment" className="p-6">
                    <div className="space-y-6">
                      <div>
                        <h3 className="text-lg font-semibold mb-2">情感分析详情</h3>
                        <p className="text-muted-foreground">
                          通过AI分析，我们对收集到的1,248条评论进行了情感分类，并提取了关键观点和用户态度。
                          总体情感倾向为积极，正面评论占比65%，负面评论占比20%，中性评论占比15%。
                        </p>
                      </div>
                      
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                          <h4 className="font-semibold text-green-700 mb-3">正面评论分析</h4>
                          <div className="space-y-4">
                            <Card>
                              <CardContent className="p-4">
                                <div className="flex justify-between items-start mb-2">
                                  <Badge className="bg-green-500">正面评论</Badge>
                                  <span className="text-xs text-muted-foreground">哔哩哔哩 · 2025-04-15</span>
                                </div>
                                <p className="mb-2">刺客信条幻影刺客的画面真的太惊艳了，育碧这次做得很棒！每个场景都精致到令人窒息，尤其是光影效果。</p>
                                <div className="flex flex-wrap gap-2">
                                  <Badge variant="outline" className="bg-green-50 text-green-700">画面</Badge>
                                  <Badge variant="outline" className="bg-green-50 text-green-700">光影</Badge>
                                </div>
                              </CardContent>
                            </Card>
                            
                            <Card>
                              <CardContent className="p-4">
                                <div className="flex justify-between items-start mb-2">
                                  <Badge className="bg-green-500">正面评论</Badge>
                                  <span className="text-xs text-muted-foreground">百度贴吧 · 2025-04-05</span>
                                </div>
                                <p className="mb-2">育碧这次的开放世界设计真的很用心，每个角落都有惊喜，探索起来非常有趣，比前几作有很大进步。</p>
                                <div className="flex flex-wrap gap-2">
                                  <Badge variant="outline" className="bg-green-50 text-green-700">开放世界</Badge>
                                  <Badge variant="outline" className="bg-green-50 text-green-700">探索</Badge>
                                </div>
                              </CardContent>
                            </Card>
                          </div>
                        </div>
                        
                        <div>
                          <h4 className="font-semibold text-red-700 mb-3">负面评论分析</h4>
                          <div className="space-y-4">
                            <Card>
                              <CardContent className="p-4">
                                <div className="flex justify-between items-start mb-2">
                                  <Badge className="bg-red-500">负面评论</Badge>
                                  <span className="text-xs text-muted-foreground">百度贴吧 · 2025-04-12</span>
                                </div>
                                <p className="mb-2">游戏优化还是有问题，我的3080显卡在高画质下都有点卡顿，特别是在城市区域，帧数明显下降，希望官方尽快修复。</p>
                                <div className="flex flex-wrap gap-2">
                                  <Badge variant="outline" className="bg-red-50 text-red-700">优化</Badge>
                                  <Badge variant="outline" className="bg-red-50 text-red-700">卡顿</Badge>
                                </div>
                              </CardContent>
                            </Card>
                            
                            <Card>
                              <CardContent className="p-4">
                                <div className="flex justify-between items-start mb-2">
                                  <Badge className="bg-red-500">负面评论</Badge>
                                  <span className="text-xs text-muted-foreground">哔哩哔哩 · 2025-04-08</span>
                                </div>
                                <p className="mb-2">剧情设计太过于老套，没有新意，感觉就是换了皮的老刺客信条，希望育碧能在剧情上有更多创新。</p>
                                <div className="flex flex-wrap gap-2">
                                  <Badge variant="outline" className="bg-red-50 text-red-700">剧情</Badge>
                                  <Badge variant="outline" className="bg-red-50 text-red-700">创新</Badge>
                                </div>
                              </CardContent>
                            </Card>
                          </div>
                        </div>
                      </div>
                      
                      <div>
                        <h4 className="font-semibold mb-3">情感趋势分析</h4>
                        <Card>
                          <CardContent className="p-4">
                            <div className="h-[300px] flex items-center justify-center text-muted-foreground">
                              [情感趋势图表 - 展示正面、负面、中性评论随时间的变化趋势]
                            </div>
                          </CardContent>
                        </Card>
                      </div>
                    </div>
                  </TabsContent>
                  
                  <TabsContent value="topics" className="p-6">
                    <div className="space-y-6">
                      <div>
                        <h3 className="text-lg font-semibold mb-2">热点话题分析</h3>
                        <p className="text-muted-foreground">
                          通过对用户评论的文本分析，我们识别出了以下主要讨论话题及其情感倾向。
                          这些话题代表了用户最关注的游戏方面，可以作为产品改进的重要参考。
                        </p>
                      </div>
                      
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <Card>
                          <CardHeader className="py-3">
                            <CardTitle className="text-base">热门话题排名</CardTitle>
                          </CardHeader>
                          <CardContent className="p-0">
                            <div className="divide-y">
                              {[
                                { topic: "画面质量", count: 342, sentiment: "正面", percent: "92%" },
                                { topic: "游戏优化", count: 256, sentiment: "负面", percent: "78%" },
                                { topic: "剧情设计", count: 187, sentiment: "中性", percent: "55%" },
                                { topic: "战斗系统", count: 145, sentiment: "正面", percent: "68%" },
                                { topic: "开放世界", count: 132, sentiment: "正面", percent: "85%" },
                                { topic: "任务设计", count: 98, sentiment: "负面", percent: "62%" },
                                { topic: "角色塑造", count: 87, sentiment: "正面", percent: "71%" },
                                { topic: "音效音乐", count: 76, sentiment: "正面", percent: "89%" },
                              ].map((item, i) => (
                                <div key={i} className="flex items-center justify-between p-3">
                                  <div className="flex items-center gap-2">
                                    <span className="font-medium text-sm">{i + 1}.</span>
                                    <span>{item.topic}</span>
                                  </div>
                                  <div className="flex items-center gap-4">
                                    <span className="text-sm text-muted-foreground">{item.count}次提及</span>
                                    <Badge 
                                      className={
                                        item.sentiment === "正面" ? "bg-green-500" : 
                                        item.sentiment === "负面" ? "bg-red-500" : "bg-gray-500"
                                      }
                                    >
                                      {item.sentiment} {item.percent}
                                    </Badge>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </CardContent>
                        </Card>
                        
                        <Card>
                          <CardHeader className="py-3">
                            <CardTitle className="text-base">话题情感分布</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="h-[350px] flex items-center justify-center text-muted-foreground">
                              [话题情感分布图表 - 展示各主要话题的正面/负面/中性评论比例]
                            </div>
                          </CardContent>
                        </Card>
                      </div>
                      
                      <div>
                        <h4 className="font-semibold mb-3">话题详细分析</h4>
                        <div className="space-y-4">
                          <Card>
                            <CardHeader className="py-3">
                              <div className="flex justify-between items-center">
                                <CardTitle className="text-base">画面质量</CardTitle>
                                <Badge className="bg-green-500">92% 正面</Badge>
                              </div>
                            </CardHeader>
                            <CardContent className="py-2">
                              <p className="text-muted-foreground mb-3">
                                画面质量是用户评论中提及最多的话题，也是获得最高正面评价的方面。
                                用户普遍认为游戏画面精美，光影效果出色，环境细节丰富。
                                特别是城市场景和自然风光的渲染获得了极高评价。
                              </p>
                              <div className="space-y-2">
                                <div className="flex justify-between text-sm">
                                  <span>正面评价</span>
                                  <span className="font-medium">92%</span>
                                </div>
                                <Progress value={92} className="h-2 bg-green-100" indicatorClassName="bg-green-500" />
                                
                                <div className="flex justify-between text-sm">
                                  <span>负面评价</span>
                                  <span className="font-medium">3%</span>
                                </div>
                                <Progress value={3} className="h-2 bg-red-100" indicatorClassName="bg-red-500" />
                                
                                <div className="flex justify-between text-sm">
                                  <span>中性评价</span>
                                  <span className="font-medium">5%</span>
                                </div>
                                <Progress value={5} className="h-2 bg-gray-100" indicatorClassName="bg-gray-500" />
                              </div>
                            </CardContent>
                          </Card>
                          
                          <Card>
                            <CardHeader className="py-3">
                              <div className="flex justify-between items-center">
                                <CardTitle className="text-base">游戏优化</CardTitle>
                                <Badge className="bg-red-500">78% 负面</Badge>
                              </div>
                            </CardHeader>
                            <CardContent className="py-2">
                              <p className="text-muted-foreground mb-3">
                                游戏优化是用户负面评价最集中的话题。
                                即使在高配置PC上，用户仍然报告了帧率下降、卡顿和偶尔的崩溃问题。
                                特别是在城市区域和大规模战斗场景中，性能问题更为明显。
                              </p>
                              <div className="space-y-2">
                                <div className="flex justify-between text-sm">
                                  <span>正面评价</span>
                                  <span className="font-medium">12%</span>
                                </div>
                                <Progress value={12} className="h-2 bg-green-100" indicatorClassName="bg-green-500" />
                                
                                <div className="flex justify-between text-sm">
                                  <span>负面评价</span>
                                  <span className="font-medium">78%</span>
                                </div>
                                <Progress value={78} className="h-2 bg-red-100" indicatorClassName="bg-red-500" />
                                
                                <div className="flex justify-between text-sm">
                                  <span>中性评价</span>
                                  <span className="font-medium">10%</span>
                                </div>
                                <Progress value={10} className="h-2 bg-gray-100" indicatorClassName="bg-gray-500" />
                              </div>
                            </CardContent>
                          </Card>
                        </div>
                      </div>
                    </div>
                  </TabsContent>
                  
                  <TabsContent value="recommendations" className="p-6">
                    <div className="space-y-6">
                      <div>
                        <h3 className="text-lg font-semibold mb-2">改进建议</h3>
                        <p className="text-muted-foreground">
                          基于舆情分析结果，我们提出以下改进建议，以提升用户体验和产品口碑。
                          这些建议按照优先级排序，可作为产品迭代和市场策略的参考。
                        </p>
                      </div>
                      
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                          <h4 className="font-semibold text-green-700 mb-3">优势保持</h4>
                          <div className="space-y-4">
                            <Card>
                              <CardContent className="p-4">
                                <div className="flex items-start gap-3">
                                  <div className="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center text-green-600">
                                    <ThumbsUp className="h-4 w-4" />
                                  </div>
                                  <div>
                                    <h5 className="font-medium mb-1">继续保持高质量的视觉效果</h5>
                                    <p className="text-sm text-muted-foreground">
                                      画面质量是用户最认可的优势，建议在后续更新和DLC中保持这一水准，
                                      并在营销宣传中突出展示游戏的视觉效果。
                                    </p>
                                  </div>
                                </div>
                              </CardContent>
                            </Card>
                            
                            <Card>
                              <CardContent className="p-4">
                                <div className="flex items-start gap-3">
                                  <div className="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center text-green-600">
                                    <ThumbsUp className="h-4 w-4" />
                                  </div>
                                  <div>
                                    <h5 className="font-medium mb-1">强化开放世界探索体验</h5>
                                    <p className="text-sm text-muted-foreground">
                                      用户对世界设计的细节和丰富度给予高度评价，建议在后续内容中
                                      增加更多有趣的探索点和隐藏内容，进一步提升探索乐趣。
                                    </p>
                                  </div>
                                </div>
                              </CardContent>
                            </Card>
                            
                            <Card>
                              <CardContent className="p-4">
                                <div className="flex items-start gap-3">
                                  <div className="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center text-green-600">
                                    <ThumbsUp className="h-4 w-4" />
                                  </div>
                                  <div>
                                    <h5 className="font-medium mb-1">延续战斗系统的改进</h5>
                                    <p className="text-sm text-muted-foreground">
                                      战斗系统的改进获得了积极反馈，建议继续优化并增加更多战斗技巧和
                                      敌人类型，提供更丰富的战斗体验。
                                    </p>
                                  </div>
                                </div>
                              </CardContent>
                            </Card>
                          </div>
                        </div>
                        
                        <div>
                          <h4 className="font-semibold text-red-700 mb-3">问题改进</h4>
                          <div className="space-y-4">
                            <Card>
                              <CardContent className="p-4">
                                <div className="flex items-start gap-3">
                                  <div className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center text-red-600">
                                    <ThumbsDown className="h-4 w-4" />
                                  </div>
                                  <div>
                                    <h5 className="font-medium mb-1">优先解决性能优化问题</h5>
                                    <p className="text-sm text-muted-foreground">
                                      游戏优化是负面评论的主要来源，建议尽快发布性能补丁，
                                      重点优化城市区域和大规模战斗场景的性能表现，减少卡顿和崩溃问题。
                                    </p>
                                  </div>
                                </div>
                              </CardContent>
                            </Card>
                            
                            <Card>
                              <CardContent className="p-4">
                                <div className="flex items-start gap-3">
                                  <div className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center text-red-600">
                                    <ThumbsDown className="h-4 w-4" />
                                  </div>
                                  <div>
                                    <h5 className="font-medium mb-1">增强剧情创新</h5>
                                    <p className="text-sm text-muted-foreground">
                                      剧情被认为缺乏创新，建议在后续DLC和更新中引入更有创意的
                                      剧情元素和任务设计，避免重复感，提升游戏的叙事深度。
                                    </p>
                                  </div>
                                </div>
                              </CardContent>
                            </Card>
                            
                            <Card>
                              <CardContent className="p-4">
                                <div className="flex items-start gap-3">
                                  <div className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center text-red-600">
                                    <ThumbsDown className="h-4 w-4" />
                                  </div>
                                  <div>
                                    <h5 className="font-medium mb-1">改进任务设计</h5>
                                    <p className="text-sm text-muted-foreground">
                                      任务设计被认为重复性较高，建议增加更多样化的任务类型和
                                      目标，减少重复性任务，提升游戏的长期可玩性。
                                    </p>
                                  </div>
                                </div>
                              </CardContent>
                            </Card>
                          </div>
                        </div>
                      </div>
                      
                      <div>
                        <h4 className="font-semibold mb-3">市场策略建议</h4>
                        <Card>
                          <CardContent className="p-4">
                            <ul className="space-y-3 list-disc list-inside text-muted-foreground">
                              <li>
                                <span className="font-medium text-foreground">优化补丁沟通</span>：
                                尽快公布优化补丁计划，向玩家传达团队正在积极解决性能问题的信息，
                                减轻负面情绪。
                              </li>
                              <li>
                                <span className="font-medium text-foreground">强化视觉营销</span>：
                                在营销材料中突出展示游戏的视觉效果和开放世界设计，这是最受好评的方面。
                              </li>
                              <li>
                                <span className="font-medium text-foreground">DLC内容规划</span>：
                                规划DLC内容时，重点关注剧情创新和任务多样性，以弥补这些方面的不足。
                              </li>
                              <li>
                                <span className="font-medium text-foreground">社区互动</span>：
                                加强与社区的互动，收集玩家对游戏优化和内容的反馈，展示团队对玩家意见的重视。
                              </li>
                              <li>
                                <span className="font-medium text-foreground">竞品分析</span>：
                                分析同类型游戏中剧情和任务设计的成功案例，借鉴其创新点。
                              </li>
                            </ul>
                          </CardContent>
                        </Card>
                      </div>
                    </div>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {reportGenerated && (
        <Card>
          <CardHeader>
            <CardTitle>处理建议</CardTitle>
            <CardDescription>基于舆情分析结果的改进建议</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h4 className="font-semibold text-green-700 mb-3">优势保持</h4>
                <ul className="space-y-2">
                  <li className="flex items-start gap-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full mt-2"></div>
                    <div>
                      <p className="font-medium">画面质量</p>
                      <p className="text-sm text-muted-foreground">继续保持高质量的视觉效果，这是用户最认可的优势</p>
                    </div>
                  </li>
                  <li className="flex items-start gap-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full mt-2"></div>
                    <div>
                      <p className="font-medium">开放世界设计</p>
                      <p className="text-sm text-muted-foreground">用户对世界设计的细节和丰富度给予高度评价</p>
                    </div>
                  </li>
                  <li className="flex items-start gap-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full mt-2"></div>
                    <div>
                      <p className="font-medium">战斗系统</p>
                      <p className="text-sm text-muted-foreground">战斗系统的改进获得了积极反馈，继续优化并增加更多战斗技巧</p>
                    </div>
                  </li>
                </ul>
              </div>
              
              <div>
                <h4 className="font-semibold text-red-700 mb-3">问题改进</h4>
                <ul className="space-y-2">
                  <li className="flex items-start gap-2">
                    <div className="w-2 h-2 bg-red-500 rounded-full mt-2"></div>
                    <div>
                      <p className="font-medium">性能优化</p>
                      <p className="text-sm text-muted-foreground">游戏优化是负面评论的主要来源，需要尽快解决</p>
                    </div>
                  </li>
                  <li className="flex items-start gap-2">
                    <div className="w-2 h-2 bg-red-500 rounded-full mt-2"></div>
                    <div>
                      <p className="font-medium">剧情创新</p>
                      <p className="text-sm text-muted-foreground">剧情被认为缺乏创新，需要在后续内容中改进</p>
                    </div>
                  </li>
                  <li className="flex items-start gap-2">
                    <div className="w-2 h-2 bg-red-500 rounded-full mt-2"></div>
                    <div>
                      <p className="font-medium">任务设计</p>
                      <p className="text-sm text-muted-foreground">任务设计重复性较高，需要增加多样性</p>
                    </div>
                  </li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
