"use client"
import { useEffect, useMemo, useState } from "react"
import { useParams, useRouter } from "next/navigation"
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
import { supabase } from "@/lib/supabase"

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

export default function DetailPage() {
  const router = useRouter()
  const params = useParams()
  const idParam = (params?.id as string) || "0"
  const videoId = Number.parseInt(idParam)
  const [data, setData] = useState(mockDetailData[videoId as keyof typeof mockDetailData])

  useEffect(() => {
    async function hydrate() {
      try {
        // id=1 读取 Supabase 的 id=4；其他 id 使用 public JSON
        if (videoId === 1 && supabase) {
          const { data: rows, error } = await supabase
            .from("gg_video_analysis")
            .select("*")
            .eq("id", 4)
            .limit(1)
          if (!error && rows && rows[0]) {
            const row: any = rows[0]
            // 同步读取 gg_platform_post 填充左侧卡片
            let post: any | null = null
            if (row.platform_item_id) {
              const { data: posts } = await supabase
                .from("gg_platform_post")
                .select("*")
                .eq("platform_item_id", row.platform_item_id)
                .eq("platform", row.source_platform || "douyin")
                .limit(1)
              post = posts && posts[0]
            }
            const timeline = (row.timeline?.events || []).map((e: any) => ({
              timestamp: e.timestamp || "",
              scene_description: e.scene_description || "",
              audio_transcript: e.audio_transcript || "",
              issue: e.issue || "",
              risk_type: e.risk_type || [],
              severity: 3,
              evidence: (e.evidence && e.evidence[0] && e.evidence[0].details) || "",
            }))
            const merged = {
              id: 1,
              title: post?.title || row.summary || "xxx字段数据缺失",
              description: post?.desc || row.summary || "xxx字段数据缺失",
              thumbnail: post?.cover_url || "",
              platform: post?.platform || row.source_platform || "抖音",
              author: post?.author || "xxx字段数据缺失",
              likes: Number(post?.digg_count ?? 0),
              comments: Number(post?.comment_count ?? 0),
              shares: Number(post?.share_count ?? 0),
              views: Number(post?.play_count ?? 0),
              duration: post?.duration || "0:27",
              publishTime: post?.created_at ? new Date(post.created_at).toLocaleString("zh-CN") : "",
              contentType: "视频",
              analysis: {
                summary: row.summary || "",
                sentiment: row.sentiment || "neutral",
                brand: row.brand || "",
                timeline,
                key_points: row.key_points || [],
                risks: [],
              },
              risk_types: row.risk_types || [],
              original_url: row.platform_item_id
                ? `https://www.douyin.com/video/${row.platform_item_id}`
                : (data as any).original_url,
            }
            setData(merged as any)
            return
          }
        }

        if (videoId !== 1 || !supabase) {
          const [cardRaw, detailRaw] = await Promise.all([
            fetch("/data/douyin/card.json", { cache: "no-store" }),
            fetch("/data/douyin/detail.json", { cache: "no-store" }),
          ])
          const cardJson = await cardRaw.json()
          const djson = await detailRaw.json()
          const base = cardJson.data || {}
          const stats = base.statistics || {}
          const durationMs: number = Number(base.duration || 0)
          const durationSec = Math.floor(durationMs / 1000)
          const minutes = Math.floor(durationSec / 60)
          const seconds = String(durationSec % 60).padStart(2, "0")
          const createTime: number | undefined = base.create_time
          const publishTime = createTime ? new Date(createTime * 1000).toLocaleString("zh-CN") : ""
          const result = djson.result || {}
          const riskSet = new Set<string>()
          ;(result.timeline || []).forEach((t: any) => (t.risk_type || []).forEach((r: string) => riskSet.add(r)))
          const mapped = {
            id: videoId,
            title: base.preview_title || base.desc || "",
            description: base.desc || "",
            thumbnail: (base.url_list && base.url_list[0]) || "",
            platform: "抖音",
            author: base.nickname || "",
            likes: Number(stats.digg_count || 0),
            comments: Number(stats.comment_count || 0),
            shares: Number(stats.share_count || 0),
            sentiment: result.sentiment || "neutral",
            duration: `${minutes}:${seconds}`,
            publishTime,
            contentType: "视频",
            views: Number(stats.play_count || 0),
            riskLevel: "中风险",
            original_url: cardJson.aweme_id ? `https://www.douyin.com/video/${cardJson.aweme_id}` : "",
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
          setData(mapped as any)
        }
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
    <div className="min-h-screen bg-[#f7f7f8]">
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
   {/* 视频基本信息介绍区域 */}
      <div className="max-w-6xl mx-auto p-6 space-y-6">
        {/* 区域1：左图右信息（横向） */}
        <Card className="border border-gray-200 shadow-sm rounded-2xl overflow-hidden">
          {/* 使用11列：左5列封面，右6列信息；固定视觉高度，右侧垂直居中 */}
          <div className="grid grid-cols-1 lg:grid-cols-11">
            {/* 左侧封面 */}
            <div className="lg:col-span-5 bg-white">
              <CardContent className="p-0">
                <div className="relative h-56 sm:h-60 lg:h-[320px]">
                  <img
                    src={data.thumbnail || "/placeholder.svg"}
                    alt={data.title}
                    className="absolute inset-0 w-full h-full object-cover"
                  />
                  <div className="absolute top-4 left-4">
                    <Badge variant="secondary" className="bg-black/60 text-white backdrop-blur px-2.5 py-1 rounded-full">
                      {data.platform}
                    </Badge>
                  </div>
                  <div className="absolute bottom-4 right-4 bg-black/75 text-white px-2 py-1 rounded text-xs">
                    {data.duration}
                  </div>
                </div>
              </CardContent>
            </div>
            {/* 右侧视频信息 */}
            <div className="lg:col-span-6 bg-white">
              <CardContent className="h-full flex flex-col justify-center p-6 lg:p-8 gap-3">
                <h2 className="text-xl lg:text-2xl font-semibold text-gray-900 leading-snug">{data.title}</h2>
                <p className="text-sm text-gray-600 leading-relaxed line-clamp-3">{data.description}</p>
                <div className="flex items-center justify-between text-xs text-gray-500 pt-1">
                  <span>@{data.author}</span>
                  <span>{data.publishTime}</span>
                </div>
                <div className="flex items-center gap-4 text-sm text-gray-700 pt-1">
                  <div className="flex items-center gap-1"><Eye className="w-4 h-4" /><span>{data.views.toLocaleString()}</span></div>
                  <div className="flex items-center gap-1"><MessageCircle className="w-4 h-4" /><span>{data.comments}</span></div>
                  <div className="flex items-center gap-1"><Share2 className="w-4 h-4" /><span>{data.shares}</span></div>
                  <Button
                    size="sm"
                    className="ml-auto h-9 px-3 bg-rose-100 text-rose-700 hover:bg-rose-200 rounded-full"
                    onClick={() => {
                      const url = (data as any).original_url || `https://${data.platform.toLowerCase()}.com/video/${data.id}`
                      window.open(url, "_blank")
                    }}
                  >
                    查看原内容
                  </Button>
                </div>
              </CardContent>
            </div>
          </div>
        </Card>

        {/* 区域2：舆情分析总结（横向分栏） */}
        <Card className="border border-gray-200 shadow-sm rounded-2xl">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className="lg:col-span-3 border-b lg:border-b-0 lg:border-r border-gray-100">
              <CardHeader className="py-6">
                <CardTitle className="flex items-center gap-2 text-gray-900">
                  <TrendingUp className="w-5 h-5" />
                  舆情分析总结
                </CardTitle>
              </CardHeader>
            </div>
            <div className="lg:col-span-9">
              <CardContent className="py-6 space-y-4">
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
                <p className="text-gray-700 leading-7">{data.analysis.summary}</p>
              </CardContent>
            </div>
          </div>
        </Card>

        {/* 区域3：关键观察点（横向分栏） */}
        <Card className="border border-gray-200 shadow-sm rounded-2xl">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className="lg:col-span-3 border-b lg:border-b-0 lg:border-r border-gray-100">
              <CardHeader className="py-6">
                <CardTitle>关键观察点</CardTitle>
              </CardHeader>
            </div>
            <div className="lg:col-span-9">
              <CardContent className="py-6">
                <ul className="space-y-2">
                  {data.analysis.key_points.map((kp, idx) => {
                    const str = String(kp)
                    const parts = str.split(/[:：]/)
                    const badge = parts[0] || "要点"
                    const desc = parts.slice(1).join(":").trim()
                    return (
                      <li key={idx} className="flex items-start gap-2">
                        <Badge className="mt-0.5 bg-amber-50 text-amber-800 border border-amber-200">{badge}</Badge>
                        <span className="text-gray-700">{desc}</span>
                      </li>
                    )
                  })}
                </ul>
              </CardContent>
            </div>
          </div>
        </Card>

        {/* 时间轴分析：仅在有数据时展示，压缩留白 */}
        {data.analysis.timeline.length > 0 && (
        <Card className="border border-gray-200 shadow-sm rounded-2xl">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className="lg:col-span-3 border-b lg:border-b-0 lg:border-r border-gray-100">
              <CardHeader className="py-6">
                <CardTitle className="flex items-center gap-2">
                  <Clock className="w-5 h-5" />
                  时间轴分析
                </CardTitle>
              </CardHeader>
            </div>
            <div className="lg:col-span-9">
              <CardContent className="py-6">
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
                      <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                        {item.scene_description && (
                          <div>
                            <p className="text-xs text-gray-400 mb-1">场景描述</p>
                            <p className="text-sm text-gray-700">{item.scene_description}</p>
                          </div>
                        )}
                        {item.audio_transcript && (
                          <div>
                            <p className="text-xs text-gray-400 mb-1">配音内容</p>
                            <p className="text-sm text-gray-500 italic">"{item.audio_transcript}"</p>
                          </div>
                        )}
                        {item.issue && (
                          <div>
                            <p className="text-xs text-gray-400 mb-1">风险问题</p>
                            <p className="text-sm text-gray-700">{item.issue}</p>
                          </div>
                        )}
                        {item.evidence && (
                          <div>
                            <p className="text-xs text-gray-400 mb-1">详细说明</p>
                            <p className="text-xs text-gray-500">{item.evidence}</p>
                          </div>
                        )}
                    </div>
                  </div>
                </div>
              ))}
                </div>
              </CardContent>
            </div>
          </div>
        </Card>
        )}

        {/* 风险清单与建议 */}
        {data.analysis.risks.length > 0 && (
          <Card className="border border-gray-200 shadow-sm rounded-2xl">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              <div className="lg:col-span-3 border-b lg:border-b-0 lg:border-r border-gray-100">
                <CardHeader className="py-6">
                  <CardTitle className="flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5 text-red-500" />
                    风险清单与改进建议
                  </CardTitle>
                </CardHeader>
              </div>
              <div className="lg:col-span-9">
                <CardContent className="py-6">
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
              </div>
            </div>
          </Card>
        )}
      </div>
    </div>
  )
}
