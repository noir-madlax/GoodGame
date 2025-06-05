"use client"

import { useEffect, useRef } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export function DataVisualizations() {
  const sentimentChartRef = useRef<HTMLCanvasElement>(null)
  const platformChartRef = useRef<HTMLCanvasElement>(null)
  const trendChartRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    // 模拟图表渲染，实际项目中应使用Chart.js或其他图表库
    const drawSentimentChart = () => {
      const canvas = sentimentChartRef.current
      if (!canvas) return

      const ctx = canvas.getContext("2d")
      if (!ctx) return

      // 设置canvas尺寸
      canvas.width = 300
      canvas.height = 200

      // 清除画布
      ctx.clearRect(0, 0, canvas.width, canvas.height)

      // 绘制饼图
      const data = [
        { value: 65, color: "#22c55e", label: "正面" },
        { value: 20, color: "#ef4444", label: "负面" },
        { value: 15, color: "#6b7280", label: "中性" },
      ]

      let startAngle = 0
      const centerX = canvas.width / 2
      const centerY = canvas.height / 2
      const radius = Math.min(centerX, centerY) - 10

      data.forEach((segment) => {
        const segmentAngle = (segment.value / 100) * 2 * Math.PI

        ctx.beginPath()
        ctx.moveTo(centerX, centerY)
        ctx.arc(centerX, centerY, radius, startAngle, startAngle + segmentAngle)
        ctx.closePath()

        ctx.fillStyle = segment.color
        ctx.fill()

        // 添加标签
        const labelAngle = startAngle + segmentAngle / 2
        const labelX = centerX + Math.cos(labelAngle) * (radius * 0.7)
        const labelY = centerY + Math.sin(labelAngle) * (radius * 0.7)

        ctx.fillStyle = "#ffffff"
        ctx.font = "12px Arial"
        ctx.textAlign = "center"
        ctx.textBaseline = "middle"
        ctx.fillText(`${segment.value}%`, labelX, labelY)

        startAngle += segmentAngle
      })

      // 添加图例
      let legendY = canvas.height - 60
      data.forEach((segment) => {
        ctx.fillStyle = segment.color
        ctx.fillRect(20, legendY, 15, 15)

        ctx.fillStyle = "#000000"
        ctx.font = "12px Arial"
        ctx.textAlign = "left"
        ctx.textBaseline = "middle"
        ctx.fillText(segment.label, 45, legendY + 7.5)

        legendY += 20
      })
    }

    const drawPlatformChart = () => {
      const canvas = platformChartRef.current
      if (!canvas) return

      const ctx = canvas.getContext("2d")
      if (!ctx) return

      // 设置canvas尺寸
      canvas.width = 300
      canvas.height = 200

      // 清除画布
      ctx.clearRect(0, 0, canvas.width, canvas.height)

      // 绘制水平条形图
      const data = [
        { label: "哔哩哔哩", value: 45, color: "#f97316" },
        { label: "百度贴吧", value: 30, color: "#3b82f6" },
        { label: "微博", value: 15, color: "#ec4899" },
        { label: "小红书", value: 7, color: "#ef4444" },
        { label: "抖音", value: 3, color: "#8b5cf6" },
      ]

      const barHeight = 30
      const barGap = 15
      const maxBarWidth = canvas.width - 150

      data.forEach((item, index) => {
        const y = index * (barHeight + barGap) + 20
        const barWidth = (item.value / 100) * maxBarWidth

        // 绘制条形
        ctx.fillStyle = item.color
        ctx.fillRect(100, y, barWidth, barHeight)

        // 添加标签
        ctx.fillStyle = "#000000"
        ctx.font = "12px Arial"
        ctx.textAlign = "right"
        ctx.textBaseline = "middle"
        ctx.fillText(item.label, 90, y + barHeight / 2)

        // 添加数值
        ctx.fillStyle = "#000000"
        ctx.textAlign = "left"
        ctx.fillText(`${item.value}%`, barWidth + 110, y + barHeight / 2)
      })
    }

    const drawTrendChart = () => {
      const canvas = trendChartRef.current
      if (!canvas) return

      const ctx = canvas.getContext("2d")
      if (!ctx) return

      // 设置canvas尺寸
      canvas.width = 600
      canvas.height = 200

      // 清除画布
      ctx.clearRect(0, 0, canvas.width, canvas.height)

      // 绘制折线图
      const data = [
        { date: "03-20", positive: 60, negative: 20 },
        { date: "03-25", positive: 65, negative: 15 },
        { date: "03-30", positive: 55, negative: 25 },
        { date: "04-05", positive: 70, negative: 10 },
        { date: "04-10", positive: 65, negative: 20 },
        { date: "04-15", positive: 75, negative: 15 },
        { date: "04-19", positive: 80, negative: 10 },
      ]

      const padding = 40
      const chartWidth = canvas.width - padding * 2
      const chartHeight = canvas.height - padding * 2

      // 绘制坐标轴
      ctx.beginPath()
      ctx.moveTo(padding, padding)
      ctx.lineTo(padding, canvas.height - padding)
      ctx.lineTo(canvas.width - padding, canvas.height - padding)
      ctx.strokeStyle = "#cccccc"
      ctx.stroke()

      // 绘制正面情感折线
      ctx.beginPath()
      data.forEach((point, index) => {
        const x = padding + (index / (data.length - 1)) * chartWidth
        const y = canvas.height - padding - (point.positive / 100) * chartHeight

        if (index === 0) {
          ctx.moveTo(x, y)
        } else {
          ctx.lineTo(x, y)
        }
      })
      ctx.strokeStyle = "#22c55e"
      ctx.lineWidth = 2
      ctx.stroke()

      // 绘制负面情感折线
      ctx.beginPath()
      data.forEach((point, index) => {
        const x = padding + (index / (data.length - 1)) * chartWidth
        const y = canvas.height - padding - (point.negative / 100) * chartHeight

        if (index === 0) {
          ctx.moveTo(x, y)
        } else {
          ctx.lineTo(x, y)
        }
      })
      ctx.strokeStyle = "#ef4444"
      ctx.lineWidth = 2
      ctx.stroke()

      // 添加日期标签
      ctx.fillStyle = "#000000"
      ctx.font = "10px Arial"
      ctx.textAlign = "center"
      ctx.textBaseline = "top"

      data.forEach((point, index) => {
        const x = padding + (index / (data.length - 1)) * chartWidth
        ctx.fillText(point.date, x, canvas.height - padding + 10)
      })

      // 添加图例
      ctx.fillStyle = "#000000"
      ctx.textAlign = "left"
      ctx.textBaseline = "middle"

      ctx.beginPath()
      ctx.moveTo(padding, padding - 15)
      ctx.lineTo(padding + 20, padding - 15)
      ctx.strokeStyle = "#22c55e"
      ctx.stroke()
      ctx.fillText("正面", padding + 25, padding - 15)

      ctx.beginPath()
      ctx.moveTo(padding + 70, padding - 15)
      ctx.lineTo(padding + 90, padding - 15)
      ctx.strokeStyle = "#ef4444"
      ctx.stroke()
      ctx.fillText("负面", padding + 95, padding - 15)
    }

    drawSentimentChart()
    drawPlatformChart()
    drawTrendChart()
  }, [])

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <Card>
        <CardHeader>
          <CardTitle>情感分析</CardTitle>
        </CardHeader>
        <CardContent>
          <canvas ref={sentimentChartRef} className="w-full h-auto" />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>平台分布</CardTitle>
        </CardHeader>
        <CardContent>
          <canvas ref={platformChartRef} className="w-full h-auto" />
        </CardContent>
      </Card>

      <Card className="md:col-span-2">
        <CardHeader>
          <CardTitle>情感趋势</CardTitle>
        </CardHeader>
        <CardContent>
          <canvas ref={trendChartRef} className="w-full h-auto" />
        </CardContent>
      </Card>
    </div>
  )
}
