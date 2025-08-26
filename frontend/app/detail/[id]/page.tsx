"use client"
import { use, useEffect, useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import {
  ArrowLeft,
  Play,
  Clock,
  AlertTriangle,
  CheckCircle,
  XCircle,
  TrendingUp,
  Eye,
  MessageCircle,
  Share2,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

// 模拟详情数据
const mockDetailData = {
  1: {
    id: 1,
    title: "",
    description: "",
    thumbnail: "",
    platform: "抖音",
    author: "",
    likes: 0,
    comments: 0,
    shares: 0,
    views: 0,
    duration: "0:00",
    publishTime: "",
    contentType: "视频",
    analysis: {
      summary: "",
      sentiment: "negative",
      brand: "海底捞",
      timeline: [],
      key_points: [],
      risks: [],
    },
  },
  2: {
    id: 2,
    title: "海底捞排队太久了",
    description: "等了2个小时才吃上，虽然味道不错但是等待时间真的太长了",
    thumbnail: "/people-waiting-in-restaurant-queue.png",
    platform: "抖音",
    author: "吃货小李",
    likes: 567,
    comments: 123,
    shares: 23,
    views: 5670,
    duration: "1:45",
    publishTime: "4小时前",
    contentType: "视频",
    analysis: {
      summary:
        "视频反映海底捞排队时间过长的问题，虽然顾客认可食物品质，但等待体验影响整体满意度，需要关注客流管理优化。",
      sentiment: "negative",
      brand: "海底捞",
      timeline: [
        {
          timestamp: "00:00:30",
          scene_description: "大厅内顾客排队等待，队伍较长",
          audio_transcript: "已经等了快2个小时了，队伍还是很长",
          issue: "等待时间过长，影响顾客体验",
          risk_type: ["员工服务不当"],
          severity: 3,
          evidence: "视频显示排队时间超过2小时，队伍仍然很长",
        },
        {
          timestamp: "00:01:15",
          scene_description: "顾客表现出不耐烦情绪",
          audio_transcript: "等待时间真的太长了，有点受不了",
          issue: "长时间等待导致顾客不满",
          risk_type: ["员工服务不当"],
          severity: 3,
          evidence: "顾客明确表达对等待时间的不满",
        },
      ],
      key_points: [
        "排队等待时间超过2小时，严重影响顾客体验",
        "虽然认可食物品质，但等待体验成为主要痛点",
        "需要优化客流管理和排队机制",
      ],
      risks: [
        {
          timestamp: "00:00:30",
          risk_type: "员工服务不当",
          evidence: "排队时间过长，客流管理不当",
          recommendation: "优化排队系统，增加预约机制；加强高峰期人员配置和客流引导",
        },
      ],
    },
  },
}

export default function DetailPage({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter()
  const { id } = use(params)
  const videoId = Number.parseInt(id)
  const [data, setData] = useState(mockDetailData[videoId as keyof typeof mockDetailData])

  useEffect(() => {
    async function hydrate() {
      if (videoId !== 1) return
      try {
        const [cardRes, detailRes] = await Promise.all([
          fetch("/api/video/card", { cache: "no-store" }),
          fetch("/api/video/detail", { cache: "no-store" }),
        ])
        let card: any | null = null
        if (cardRes.ok) card = await cardRes.json()
        if (!card || !card.title) {
          try {
            const raw = await fetch("/data/douyin/card.json", { cache: "no-store" })
            const json = await raw.json()
            const data = json.data || {}
            const stats = data.statistics || {}
            const durationMs: number = Number(data.duration || 0)
            const durationSec = Math.floor(durationMs / 1000)
            const minutes = Math.floor(durationSec / 60)
            const seconds = String(durationSec % 60).padStart(2, "0")
            const createTime: number | undefined = data.create_time
            const publishTime = createTime ? new Date(createTime * 1000).toLocaleString("zh-CN") : ""
            card = {
              id: 1,
              title: data.preview_title || data.desc || "",
              description: data.desc || "",
              thumbnail: (data.url_list && data.url_list[0]) || "",
              platform: "抖音",
              author: data.nickname || "",
              likes: Number(stats.digg_count || 0),
              comments: Number(stats.comment_count || 0),
              shares: Number(stats.share_count || 0),
              sentiment: "negative",
              duration: `${minutes}:${seconds}`,
              publishTime,
              contentType: "视频",
              views: Number(stats.play_count || 0),
              riskLevel: "中风险",
              original_url: json.aweme_id ? `https://www.douyin.com/video/${json.aweme_id}` : "",
            }
          } catch {}
        }
        let detail: any | null = null
        if (detailRes.ok) detail = await detailRes.json()
        if (!detail || !detail.analysis) {
          try {
            const raw = await fetch("/data/douyin/detail.json", { cache: "no-store" })
            const json = await raw.json()
            const result = json.result || {}
            const riskSet = new Set<string>()
            ;(result.timeline || []).forEach((t: any) => (t.risk_type || []).forEach((r: string) => riskSet.add(r)))
            detail = {
              analysis: {
                summary: result.summary || "",
                sentiment: result.sentiment || "neutral",
                brand: result.brand || "",
                timeline:
                  (result.timeline || []).map((t: any) => ({
                    timestamp: t.timestamp || "",
                    scene_description: t.scene_description || "",
                    audio_transcript: t.audio_transcript || "",
                    issue: t.issue || "",
                    risk_type: t.risk_type || [],
                    severity: 3,
                    evidence: (t.evidence && t.evidence[0] && t.evidence[0].details) || "",
                  })) || [],
                key_points: result.key_points || [],
                risks: [],
              },
              risk_types: Array.from(riskSet),
            }
          } catch {}
        }
        if (card && detail)
          setData({ ...card, analysis: detail.analysis, risk_types: detail.risk_types, original_url: card.original_url })
      } catch (e) {}
    }
    hydrate()
  }, [videoId])

  const summaryRiskTypes: string[] = useMemo(() => {
    // prefer risk_types from API, or gather from timeline
    const fromApi = (data as any)?.risk_types as string[] | undefined
    if (fromApi && fromApi.length > 0) return fromApi
    const set = new Set<string>()
    data.analysis.timeline.forEach((t: any) => (t.risk_type || []).forEach((r: string) => set.add(r)))
    return Array.from(set)
  }, [data])

  if (!data) {
    return <div>内容不存在</div>
  }

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case "positive":
        return "bg-green-100 text-green-800"
      case "negative":
        return "bg-red-100 text-red-800"
      default:
        return "bg-yellow-100 text-yellow-800"
    }
  }

  const getSentimentText = (sentiment: string) => {
    switch (sentiment) {
      case "positive":
        return "正面"
      case "negative":
        return "负面"
      default:
        return "中性"
    }
  }

  const getSentimentIcon = (sentiment: string) => {
    switch (sentiment) {
      case "positive":
        return <CheckCircle className="w-4 h-4" />
      case "negative":
        return <XCircle className="w-4 h-4" />
      default:
        return <AlertTriangle className="w-4 h-4" />
    }
  }

  const getSeverityColor = (severity: number) => {
    if (severity >= 4) return "bg-red-100 text-red-800"
    if (severity >= 3) return "bg-yellow-100 text-yellow-800"
    return "bg-green-100 text-green-800"
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 顶部导航 */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => router.back()}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            返回
          </Button>
          <div>
            <h1 className="text-xl font-semibold text-gray-900">舆情详情分析</h1>
            <p className="text-sm text-gray-500">基于AI的深度舆情风险分析</p>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto p-6 space-y-6">
        {/* 视频基本信息 */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1">
            <Card>
              <CardContent className="p-0">
                <div className="relative">
                  <img
                    src={data.thumbnail || "/placeholder.svg"}
                    alt={data.title}
                    className="w-full h-64 object-cover rounded-t-lg"
                  />
                  <div className="absolute inset-0 bg-black/20 rounded-t-lg" />
                  <div className="absolute top-4 left-4">
                    <Badge variant="secondary" className="bg-black/50 text-white">
                      {data.platform}
                    </Badge>
                  </div>
                  <div className="absolute bottom-4 right-4 bg-black/70 text-white px-2 py-1 rounded text-sm">
                    {data.duration}
                  </div>
                  <div className="absolute inset-0 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity">
                    <Button
                      size="sm"
                      className="h-9 px-3 bg-white/90 hover:bg-white text-gray-700 hover:text-gray-900 text-sm rounded-md shadow"
                      onClick={() => {
                        const url = (data as any).original_url || `https://${data.platform.toLowerCase()}.com/video/${data.id}`
                        window.open(url, "_blank")
                      }}
                    >
                      查看原内容
                    </Button>
                  </div>
                </div>
                <div className="p-4 space-y-3">
                  <h2 className="font-semibold text-lg">{data.title}</h2>
                  <p className="text-sm text-gray-600">{data.description}</p>
                  <div className="flex items-center justify-between text-sm text-gray-500">
                    <span>@{data.author}</span>
                    <span>{data.publishTime}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-4">
                      <div className="flex items-center gap-1">
                        <Eye className="w-4 h-4" />
                        <span>{data.views.toLocaleString()}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <MessageCircle className="w-4 h-4" />
                        <span>{data.comments}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Share2 className="w-4 h-4" />
                        <span>{data.shares}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="lg:col-span-2 space-y-6">
            {/* 舆情总结 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="w-5 h-5" />
                  舆情分析总结
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge className={getSentimentColor(data.analysis.sentiment)}>
                    {getSentimentIcon(data.analysis.sentiment)}
                    <span className="ml-1">{getSentimentText(data.analysis.sentiment)}</span>
                  </Badge>
                  <Badge variant="outline">品牌: {data.analysis.brand}</Badge>
                  {summaryRiskTypes.map((r) => (
                    <Badge key={r} variant="secondary" className="bg-amber-50 text-amber-800 border border-amber-200">
                      {r}
                    </Badge>
                  ))}
                </div>
                <p className="text-gray-700 leading-relaxed">{data.analysis.summary}</p>
              </CardContent>
            </Card>

            {/* 关键观察点 */}
            <Card>
              <CardHeader>
                <CardTitle>关键观察点</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {data.analysis.timeline.map((t, index) => {
                    const r = (t.risk_type && t.risk_type[0]) || undefined
                    const textParts = [t.issue || t.scene_description]
                    const text = textParts.filter(Boolean).join(" - ")
                    return (
                    <li key={index} className="flex items-start gap-2">
                        {r ? (
                          <Badge className="mt-0.5 bg-amber-50 text-amber-800 border border-amber-200">{r}</Badge>
                        ) : (
                      <div className="w-2 h-2 bg-emerald-500 rounded-full mt-2 flex-shrink-0" />
                        )}
                        <span className="text-gray-700">
                          {r ? <span className="font-medium mr-1">：</span> : null}
                          {text}
                        </span>
                    </li>
                    )
                  })}
                </ul>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* 时间轴分析：仅在有数据时展示，压缩留白 */}
        {data.analysis.timeline.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="w-5 h-5" />
              时间轴分析
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {data.analysis.timeline.map((item, index) => (
                <div key={index} className="flex gap-4">
                  <div className="flex flex-col items-center">
                    <div className="w-3 h-3 bg-emerald-500 rounded-full" />
                      {index < data.analysis.timeline.length - 1 && <div className="w-px h-12 bg-gray-200 mt-2" />}
                  </div>
                    <div className="flex-1 pb-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Badge variant="outline" className="font-mono text-xs">
                        {item.timestamp}
                      </Badge>
                      {item.severity > 1 && (
                        <Badge className={getSeverityColor(item.severity)}>风险等级: {item.severity}</Badge>
                      )}
                        {(item.risk_type || []).map((r: string) => (
                          <Badge key={r} variant="secondary" className="bg-amber-50 text-amber-800 border border-amber-200">
                            {r}
                          </Badge>
                        ))}
                      </div>
                      <div className="bg-gray-50 rounded-lg p-4 space-y-2">
                        {item.scene_description && (
                          <p className="text-sm text-gray-700">{item.scene_description}</p>
                        )}
                        {item.audio_transcript && (
                          <p className="text-sm text-gray-500 italic">"{item.audio_transcript}"</p>
                        )}
                        {item.issue && <p className="text-sm text-gray-700">{item.issue}</p>}
                        {item.evidence && <p className="text-xs text-gray-500">{item.evidence}</p>}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
        )}

        {/* 风险清单与建议 */}
        {data.analysis.risks.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-red-500" />
                风险清单与改进建议
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {data.analysis.risks.map((risk, index) => (
                  <div key={index} className="border border-red-200 rounded-lg p-4 bg-red-50">
                    <div className="flex items-center gap-2 mb-2">
                      <Badge variant="outline" className="font-mono text-xs">
                        {risk.timestamp}
                      </Badge>
                      <Badge className="bg-red-100 text-red-800">{risk.risk_type}</Badge>
                    </div>
                    <div className="space-y-2">
                      <div>
                        <h4 className="font-medium text-sm text-gray-900">证据摘要</h4>
                        <p className="text-sm text-gray-600">{risk.evidence}</p>
                      </div>
                      <div>
                        <h4 className="font-medium text-sm text-gray-900">改进建议</h4>
                        <p className="text-sm text-gray-600">{risk.recommendation}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
