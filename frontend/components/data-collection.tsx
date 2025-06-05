"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { DatePickerWithRange } from "@/components/date-range-picker"
import { Checkbox } from "@/components/ui/checkbox"
import { Badge } from "@/components/ui/badge"
import { PlatformSelector } from "@/components/platform-selector"
import { KeywordSuggestions } from "@/components/keyword-suggestions"
import { DataPreview } from "@/components/data-preview"
import { GameSlangKnowledgeBase } from "@/components/game-slang-knowledge-base"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

export function DataCollection() {
  const [isLoading, setIsLoading] = useState(false)
  const [dataCollected, setDataCollected] = useState(false)
  const [suggestedKeywords, setSuggestedKeywords] = useState<string[]>([])
  const [activeTab, setActiveTab] = useState("data-collection")

  const handleCollectData = () => {
    setIsLoading(true)
    // 模拟数据收集过程
    setTimeout(() => {
      setIsLoading(false)
      setDataCollected(true)
      setSuggestedKeywords(["刺客信条", "育碧", "开放世界", "游戏性", "画面", "优化"])
    }, 2000)
  }

  return (
    <div className="grid gap-6">
      <Tabs defaultValue="data-collection" value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="mb-4">
          <TabsTrigger value="data-collection">数据采集</TabsTrigger>
          <TabsTrigger value="slang-knowledge">游戏黑话知识库</TabsTrigger>
        </TabsList>

        <TabsContent value="data-collection">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>数据源配置</CardTitle>
                <CardDescription>选择要监测的品牌和平台</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="brand">品牌</Label>
                  <Select defaultValue="assassins-creed">
                    <SelectTrigger id="brand">
                      <SelectValue placeholder="选择品牌" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="assassins-creed">刺客信条</SelectItem>
                      <SelectItem value="far-cry">孤岛惊魂</SelectItem>
                      <SelectItem value="rainbow-six">彩虹六号</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>日期范围</Label>
                  <DatePickerWithRange />
                </div>

                <div className="space-y-2">
                  <Label>平台选择</Label>
                  <PlatformSelector />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>关键词设置</CardTitle>
                <CardDescription>设置要监测的关键词</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="keywords">手动输入关键词</Label>
                  <div className="flex gap-2">
                    <Input id="keywords" placeholder="输入关键词，按回车添加" />
                    <Button variant="outline" size="icon">
                      +
                    </Button>
                  </div>

                  <div className="flex flex-wrap gap-2 mt-2">
                    <Badge>刺客信条</Badge>
                    <Badge>育碧</Badge>
                    <Badge className="flex gap-1 items-center">
                      幻影刺客
                      <button className="h-3 w-3 rounded-full">×</button>
                    </Badge>
                  </div>
                </div>

                {suggestedKeywords.length > 0 && <KeywordSuggestions keywords={suggestedKeywords} />}

                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <Checkbox id="ai-keywords" />
                    <span>使用AI智能推荐关键词</span>
                  </Label>
                  <p className="text-sm text-muted-foreground">基于历史数据和行业趋势，AI将推荐相关关键词</p>
                </div>

                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <Checkbox id="use-slang" defaultChecked />
                    <span>使用游戏黑话知识库</span>
                  </Label>
                  <p className="text-sm text-muted-foreground">
                    启用游戏黑话知识库，帮助AI更准确理解玩家使用的特殊术语和表达
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="flex justify-center mt-6">
            <Button
              size="lg"
              onClick={handleCollectData}
              disabled={isLoading}
              className="bg-orange-500 hover:bg-orange-600"
            >
              {isLoading ? "数据收集中..." : "开始全网监测"}
            </Button>
          </div>

          {dataCollected && <DataPreview />}
        </TabsContent>

        <TabsContent value="slang-knowledge">
          <GameSlangKnowledgeBase />
        </TabsContent>
      </Tabs>
    </div>
  )
}
