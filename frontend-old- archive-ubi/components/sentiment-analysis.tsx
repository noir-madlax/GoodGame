"use client"
import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { SentimentDashboard } from "@/components/sentiment-dashboard"
import { ScenarioAlertCenter } from "@/components/scenario-alert-center"

export function SentimentAnalysis() {
  const [activeTab, setActiveTab] = useState("dashboard")

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>智能分析中心</CardTitle>
          <CardDescription>AI情感分析、舆情追踪和预警监控</CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="dashboard" value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="mb-4">
              <TabsTrigger value="dashboard">舆情总览</TabsTrigger>
              <TabsTrigger value="scenario-alerts">场景化预警</TabsTrigger>
            </TabsList>

            <TabsContent value="dashboard">
              <SentimentDashboard />
            </TabsContent>

            <TabsContent value="scenario-alerts">
              <ScenarioAlertCenter />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  )
}
