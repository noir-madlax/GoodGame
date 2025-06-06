"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { DatePickerWithRange } from "@/components/date-range-picker"
import { Checkbox } from "@/components/ui/checkbox"
import { PlatformSelector } from "@/components/platform-selector"
import { DataPreview } from "@/components/data-preview"
import { BrandAliasManagement } from "@/components/brand-alias-management"
import { GameSlangKnowledgeBase } from "@/components/game-slang-knowledge-base"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Video, MessageSquare, FileText, Radio, Hash } from "lucide-react"
import { Separator } from "@/components/ui/separator"

export function DataCollection() {
  const [isLoading, setIsLoading] = useState(false)
  const [dataCollected, setDataCollected] = useState(false)
  const [activeTab, setActiveTab] = useState("data-source")

  const handleCollectData = () => {
    setIsLoading(true)
    // 模拟数据收集过程
    setTimeout(() => {
      setIsLoading(false)
      setDataCollected(true)
    }, 2000)
  }

  return (
    <div className="grid gap-6">
      <Tabs defaultValue="data-source" value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="mb-4">
          <TabsTrigger value="data-source">数据源配置</TabsTrigger>
          <TabsTrigger value="brand-alias">品牌别名管理</TabsTrigger>
          <TabsTrigger value="slang-knowledge">游戏黑话知识库</TabsTrigger>
        </TabsList>

        <TabsContent value="data-source">
          <Card>
            <CardHeader>
              <CardTitle>监测配置</CardTitle>
              <CardDescription>选择要监测的品牌、平台和时间范围</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="brand">品牌产品</Label>
                  <Select defaultValue="assassins-creed-mirage">
                    <SelectTrigger id="brand">
                      <SelectValue placeholder="选择品牌" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="assassins-creed-mirage">刺客信条：幻影刺客</SelectItem>
                      <SelectItem value="far-cry-6">孤岛惊魂6</SelectItem>
                      <SelectItem value="rainbow-six-siege">彩虹六号：围攻</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>监测时间范围</Label>
                  <DatePickerWithRange />
                </div>

                <div className="space-y-2">
                  <Label>内容类型</Label>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="flex items-center space-x-2">
                      <Checkbox id="text-content" defaultChecked />
                      <Label htmlFor="text-content" className="flex items-center gap-2">
                        <FileText className="h-4 w-4" />
                        图文内容
                      </Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Checkbox id="video-content" defaultChecked />
                      <Label htmlFor="video-content" className="flex items-center gap-2">
                        <Video className="h-4 w-4" />
                        视频内容
                      </Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Checkbox id="live-content" defaultChecked />
                      <Label htmlFor="live-content" className="flex items-center gap-2">
                        <Radio className="h-4 w-4" />
                        直播内容
                      </Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Checkbox id="comment-content" defaultChecked />
                      <Label htmlFor="comment-content" className="flex items-center gap-2">
                        <MessageSquare className="h-4 w-4" />
                        评论
                      </Label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Checkbox id="barrage-content" defaultChecked />
                      <Label htmlFor="barrage-content" className="flex items-center gap-2">
                        <Hash className="h-4 w-4" />
                        弹幕
                      </Label>
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>监测平台</Label>
                  <PlatformSelector />
                </div>
              </div>

              <Separator />

              <div className="space-y-4">
                <h3 className="text-lg font-medium">高级设置</h3>

                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <Checkbox id="use-brand-alias" defaultChecked />
                    <span>使用品牌别名库</span>
                  </Label>
                  <p className="text-sm text-muted-foreground">启用品牌别名库，识别游戏的各种代称、主角名称等</p>
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
              </div>
            </CardContent>
          </Card>

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

        <TabsContent value="brand-alias">
          <BrandAliasManagement />
        </TabsContent>

        <TabsContent value="slang-knowledge">
          <GameSlangKnowledgeBase />
        </TabsContent>
      </Tabs>
    </div>
  )
}
