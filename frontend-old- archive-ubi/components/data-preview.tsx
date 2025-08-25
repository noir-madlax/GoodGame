"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { Download, Filter } from "lucide-react"
import { DataTable } from "@/components/data-table"
import { DataVisualizations } from "@/components/data-visualizations"

export function DataPreview() {
  const [activeTab, setActiveTab] = useState("table")

  return (
    <Card className="mt-6">
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle>数据预览</CardTitle>
          <CardDescription>共收集到 1,248 条数据</CardDescription>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm">
            <Filter className="mr-2 h-4 w-4" />
            筛选
          </Button>
          <Button variant="outline" size="sm">
            <Download className="mr-2 h-4 w-4" />
            导出Excel
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="table" value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="mb-4">
            <TabsTrigger value="table">数据表格</TabsTrigger>
            <TabsTrigger value="visualizations">数据可视化</TabsTrigger>
          </TabsList>
          <TabsContent value="table">
            <DataTable />
          </TabsContent>
          <TabsContent value="visualizations">
            <DataVisualizations />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}
