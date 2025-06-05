import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { DataCollection } from "@/components/data-collection"
import { SentimentAnalysis } from "@/components/sentiment-analysis"
import { ReportGeneration } from "@/components/report-generation"
import { DashboardHeader } from "@/components/dashboard-header"

export default function Home() {
  return (
    <div className="container mx-auto py-6">
      <DashboardHeader />

      <Tabs defaultValue="collection" className="mt-6">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="collection">全网监测</TabsTrigger>
          <TabsTrigger value="analysis">智能分析</TabsTrigger>
          <TabsTrigger value="reports">处理建议</TabsTrigger>
        </TabsList>
        <TabsContent value="collection" className="mt-6">
          <DataCollection />
        </TabsContent>
        <TabsContent value="analysis" className="mt-6">
          <SentimentAnalysis />
        </TabsContent>
        <TabsContent value="reports" className="mt-6">
          <ReportGeneration />
        </TabsContent>
      </Tabs>
    </div>
  )
}
