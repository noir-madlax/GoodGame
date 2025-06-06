"use client"

import { useState } from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { DashboardHeader } from "@/components/dashboard-header"
import { DataCollection } from "@/components/data-collection"
import { SentimentAnalysis } from "@/components/sentiment-analysis"
import { ContentExplorer } from "@/components/content-explorer"
import { ReportGeneration } from "@/components/report-generation"

export default function Home() {
  const [activeTab, setActiveTab] = useState("data-collection")

  return (
    <div className="min-h-screen bg-gray-50">
      <DashboardHeader />

      <main className="container mx-auto px-4 py-6">
        <Tabs defaultValue="data-collection" value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-4 mb-6">
            <TabsTrigger value="data-collection">全网监测</TabsTrigger>
            <TabsTrigger value="sentiment-analysis">智能分析</TabsTrigger>
            <TabsTrigger value="content-explorer">内容查询</TabsTrigger>
            <TabsTrigger value="report-generation">处理建议</TabsTrigger>
          </TabsList>

          <TabsContent value="data-collection">
            <DataCollection />
          </TabsContent>

          <TabsContent value="sentiment-analysis">
            <SentimentAnalysis />
          </TabsContent>

          <TabsContent value="content-explorer">
            <ContentExplorer />
          </TabsContent>

          <TabsContent value="report-generation">
            <ReportGeneration />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  )
}
