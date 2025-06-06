"use client"

import { useEffect, useRef } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export function TrendCharts() {
  const sentimentChartRef = useRef<HTMLCanvasElement>(null)
  const platformChartRef = useRef<HTMLCanvasElement>(null)
  const timelineChartRef = useRef<HTMLCanvasElement>(null)
  const topicChartRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    // 绘制情感趋势图
    const drawSentimentTrend = () => {
      const canvas = sentimentChartRef.current
      if (!canvas) return

      const ctx = canvas.getContext("2d")
      if (!ctx) return

      canvas.width = 600
      canvas.height = 300

      ctx.clearRect(0, 0, canvas.width, canvas.height)

      // 模拟数据
      const data = [
        { date: "04-13", positive: 60, negative: 25, neutral: 15 },
        { date: "04-14", positive: 65, negative: 20, neutral: 15 },
        { date: "04-15", positive: 55, negative: 30, neutral: 15 },
        { date: "04-16", positive: 70, negative: 15, neutral: 15 },
        { date: "04-17", positive: 65, negative: 20, neutral: 15 },
        { date: "04-18", positive: 75, negative: 15, neutral: 10 },
        { date: "04-19", positive: 80, negative: 10, neutral: 10 },
      ]

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
      ctx.lineWidth = 3
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
      ctx.lineWidth = 3
      ctx.stroke()

      // 绘制中性情感折线
      ctx.beginPath()
      data.forEach((point, index) => {
        const x = padding + (index / (data.length - 1)) * chartWidth
        const y = canvas.height - padding - (point.neutral / 100) * chartHeight

        if (index === 0) {
          ctx.moveTo(x, y)
        } else {
          ctx.lineTo(x, y)
        }
      })
      ctx.strokeStyle = "#6b7280"
      ctx.lineWidth = 3
      ctx.stroke()

      // 添加数据点
      data.forEach((point, index) => {
        const x = padding + (index / (data.length - 1)) * chartWidth

        // 正面情感点
        const positiveY = canvas.height - padding - (point.positive / 100) * chartHeight
        ctx.beginPath()
        ctx.arc(x, positiveY, 4, 0, 2 * Math.PI)
        ctx.fillStyle = "#22c55e"
        ctx.fill()

        // 负面情感点
        const negativeY = canvas.height - padding - (point.negative / 100) * chartHeight
        ctx.beginPath()
        ctx.arc(x, negativeY, 4, 0, 2 * Math.PI)
        ctx.fillStyle = "#ef4444"
        ctx.fill()

        // 中性情感点
        const neutralY = canvas.height - padding - (point.neutral / 100) * chartHeight
        ctx.beginPath()
        ctx.arc(x, neutralY, 4, 0, 2 * Math.PI)
        ctx.fillStyle = "#6b7280"
        ctx.fill()
      })

      // 添加日期标签
      ctx.fillStyle = "#6b7280"
      ctx.font = "12px Arial"
      ctx.textAlign = "center"
      ctx.textBaseline = "top"

      data.forEach((point, index) => {
        const x = padding + (index / (data.length - 1)) * chartWidth
        ctx.fillText(point.date, x, canvas.height - padding + 10)
      })

      // 添加Y轴标签
      ctx.textAlign = "right"
      ctx.textBaseline = "middle"
      for (let i = 0; i <= 5; i++) {
        const y = canvas.height - padding - (i * chartHeight) / 5
        const value = (i * 20).toString() + "%"
        ctx.fillText(value, padding - 10, y)
      }

      // 添加图例
      const legendY = 20
      ctx.textAlign = "left"
      ctx.textBaseline = "middle"

      // 正面图例
      ctx.beginPath()
      ctx.moveTo(padding, legendY)
      ctx.lineTo(padding + 20, legendY)
      ctx.strokeStyle = "#22c55e"
      ctx.lineWidth = 3
      ctx.stroke()
      ctx.fillStyle = "#22c55e"
      ctx.fillText("正面", padding + 25, legendY)

      // 负面图例
      ctx.beginPath()
      ctx.moveTo(padding + 80, legendY)
      ctx.lineTo(padding + 100, legendY)
      ctx.strokeStyle = "#ef4444"
      ctx.lineWidth = 3
      ctx.stroke()
      ctx.fillStyle = "#ef4444"
      ctx.fillText("负面", padding + 105, legendY)

      // 中性图例
      ctx.beginPath()
      ctx.moveTo(padding + 160, legendY)
      ctx.lineTo(padding + 180, legendY)
      ctx.strokeStyle = "#6b7280"
      ctx.lineWidth = 3
      ctx.stroke()
      ctx.fillStyle = "#6b7280"
      ctx.fillText("中性", padding + 185, legendY)
    }

    // 绘制平台分布图
    const drawPlatformDistribution = () => {
      const canvas = platformChartRef.current
      if (!canvas) return

      const ctx = canvas.getContext("2d")
      if (!ctx) return

      canvas.width = 400
      canvas.height = 300

      ctx.clearRect(0, 0, canvas.width, canvas.height)

      const data = [
        { platform: "哔哩哔哩", value: 45, color: "#f97316" },
        { platform: "百度贴吧", value: 30, color: "#3b82f6" },
        { platform: "微博", value: 15, color: "#ec4899" },
        { platform: "小红书", value: 7, color: "#ef4444" },
        { platform: "抖音", value: 3, color: "#8b5cf6" },
      ]

      const centerX = canvas.width / 2
      const centerY = canvas.height / 2
      const radius = Math.min(centerX, centerY) - 40

      let startAngle = 0

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
      let legendY = 20
      data.forEach((segment) => {
        ctx.fillStyle = segment.color
        ctx.fillRect(20, legendY, 15, 15)

        ctx.fillStyle = "#000000"
        ctx.font = "12px Arial"
        ctx.textAlign = "left"
        ctx.textBaseline = "middle"
        ctx.fillText(`${segment.platform} (${segment.value}%)`, 45, legendY + 7.5)

        legendY += 25
      })
    }

    // 绘制时间线图
    const drawTimeline = () => {
      const canvas = timelineChartRef.current
      if (!canvas) return

      const ctx = canvas.getContext("2d")
      if (!ctx) return

      canvas.width = 800
      canvas.height = 300

      ctx.clearRect(0, 0, canvas.width, canvas.height)

      const data = [
        { time: "00:00", mentions: 45 },
        { time: "04:00", mentions: 23 },
        { time: "08:00", mentions: 78 },
        { time: "12:00", mentions: 156 },
        { time: "16:00", mentions: 234 },
        { time: "20:00", mentions: 189 },
        { time: "24:00", mentions: 67 },
      ]

      const padding = 40
      const chartWidth = canvas.width - padding * 2
      const chartHeight = canvas.height - padding * 2
      const maxMentions = Math.max(...data.map((d) => d.mentions))

      // 绘制坐标轴
      ctx.beginPath()
      ctx.moveTo(padding, padding)
      ctx.lineTo(padding, canvas.height - padding)
      ctx.lineTo(canvas.width - padding, canvas.height - padding)
      ctx.strokeStyle = "#e5e7eb"
      ctx.lineWidth = 1
      ctx.stroke()

      // 绘制柱状图
      const barWidth = (chartWidth / data.length) * 0.6
      data.forEach((point, index) => {
        const x = padding + (index + 0.5) * (chartWidth / data.length) - barWidth / 2
        const barHeight = (point.mentions / maxMentions) * chartHeight
        const y = canvas.height - padding - barHeight

        ctx.fillStyle = "#3b82f6"
        ctx.fillRect(x, y, barWidth, barHeight)

        // 添加数值标签
        ctx.fillStyle = "#374151"
        ctx.font = "12px Arial"
        ctx.textAlign = "center"
        ctx.textBaseline = "bottom"
        ctx.fillText(point.mentions.toString(), x + barWidth / 2, y - 5)

        // 添加时间标签
        ctx.textBaseline = "top"
        ctx.fillText(point.time, x + barWidth / 2, canvas.height - padding + 10)
      })

      // 添加Y轴标签
      ctx.textAlign = "right"
      ctx.textBaseline = "middle"
      for (let i = 0; i <= 5; i++) {
        const y = canvas.height - padding - (i * chartHeight) / 5
        const value = Math.round((i * maxMentions) / 5).toString()
        ctx.fillText(value, padding - 10, y)
      }
    }

    // 绘制话题热度图
    const drawTopicHeat = () => {
      const canvas = topicChartRef.current
      if (!canvas) return

      const ctx = canvas.getContext("2d")
      if (!ctx) return

      canvas.width = 600
      canvas.height = 400

      ctx.clearRect(0, 0, canvas.width, canvas.height)

      const topics = [
        { name: "画面质量", heat: 95, x: 150, y: 100 },
        { name: "游戏优化", heat: 85, x: 300, y: 150 },
        { name: "巴辛姆", heat: 75, x: 450, y: 120 },
        { name: "剧情设计", heat: 65, x: 200, y: 250 },
        { name: "战斗系统", heat: 70, x: 400, y: 280 },
        { name: "开放世界", heat: 80, x: 350, y: 200 },
        { name: "任务设计", heat: 55, x: 250, y: 180 },
        { name: "音效", heat: 60, x: 500, y: 250 },
      ]

      topics.forEach((topic) => {
        const radius = (topic.heat / 100) * 30 + 10
        const alpha = topic.heat / 100

        // 绘制热度圆圈
        ctx.beginPath()
        ctx.arc(topic.x, topic.y, radius, 0, 2 * Math.PI)
        ctx.fillStyle = `rgba(239, 68, 68, ${alpha * 0.6})`
        ctx.fill()

        // 绘制边框
        ctx.beginPath()
        ctx.arc(topic.x, topic.y, radius, 0, 2 * Math.PI)
        ctx.strokeStyle = `rgba(239, 68, 68, ${alpha})`
        ctx.lineWidth = 2
        ctx.stroke()

        // 添加话题名称
        ctx.fillStyle = "#374151"
        ctx.font = "12px Arial"
        ctx.textAlign = "center"
        ctx.textBaseline = "middle"
        ctx.fillText(topic.name, topic.x, topic.y)

        // 添加热度值
        ctx.font = "10px Arial"
        ctx.fillText(topic.heat.toString(), topic.x, topic.y + 15)
      })

      // 添加标题
      ctx.fillStyle = "#374151"
      ctx.font = "16px Arial"
      ctx.textAlign = "center"
      ctx.textBaseline = "top"
      ctx.fillText("话题热度分布图", canvas.width / 2, 20)
    }

    drawSentimentTrend()
    drawPlatformDistribution()
    drawTimeline()
    drawTopicHeat()
  }, [])

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <Card>
        <CardHeader>
          <CardTitle>情感趋势分析</CardTitle>
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

      <Card>
        <CardHeader>
          <CardTitle>24小时提及量</CardTitle>
        </CardHeader>
        <CardContent>
          <canvas ref={timelineChartRef} className="w-full h-auto" />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>话题热度图</CardTitle>
        </CardHeader>
        <CardContent>
          <canvas ref={topicChartRef} className="w-full h-auto" />
        </CardContent>
      </Card>
    </div>
  )
}
