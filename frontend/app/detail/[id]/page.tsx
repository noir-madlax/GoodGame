"use client"
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
    title: "海底捞服务体验分享",
    description: "今天去海底捞吃火锅，服务员小姐姐超级贴心，还帮我们拍照！",
    thumbnail: "/hotpot-restaurant-interior.png",
    platform: "小红书",
    author: "美食达人小王",
    likes: 1234,
    comments: 89,
    shares: 45,
    views: 12340,
    duration: "2:34",
    publishTime: "2小时前",
    contentType: "视频",
    analysis: {
      summary: "视频展示了海底捞优质的服务体验，顾客对服务员的贴心服务表示满意，整体舆情积极正面，有助于品牌形象提升。",
      sentiment: "positive",
      brand: "海底捞",
      timeline: [
        {
          timestamp: "00:00:15",
          scene_description: "服务员主动为顾客拍照，面带微笑",
          audio_transcript: "服务员小姐姐超级贴心，还帮我们拍照",
          issue: "无明显问题，展现良好服务态度",
          risk_type: [],
          severity: 1,
          evidence: "服务员主动提供拍照服务，体现贴心服务",
        },
        {
          timestamp: "00:01:30",
          scene_description: "餐厅环境整洁，顾客用餐愉快",
          audio_transcript: "环境真的很不错，很干净",
          issue: "无问题，正面评价",
          risk_type: [],
          severity: 1,
          evidence: "顾客对环境卫生给予正面评价",
        },
      ],
      key_points: [
        "服务员主动提供拍照服务，体现贴心服务理念",
        "餐厅环境卫生状况良好，获得顾客认可",
        "整体用餐体验积极正面，有利于品牌口碑传播",
      ],
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

export default function DetailPage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const videoId = Number.parseInt(params.id)
  const data = mockDetailData[videoId as keyof typeof mockDetailData]

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
                  <div className="absolute inset-0 flex items-center justify-center">
                    <Button size="lg" className="rounded-full w-16 h-16">
                      <Play className="w-6 h-6" />
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
                <div className="flex items-center gap-2">
                  <Badge className={getSentimentColor(data.analysis.sentiment)}>
                    {getSentimentIcon(data.analysis.sentiment)}
                    <span className="ml-1">{getSentimentText(data.analysis.sentiment)}</span>
                  </Badge>
                  <Badge variant="outline">品牌: {data.analysis.brand}</Badge>
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
                  {data.analysis.key_points.map((point, index) => (
                    <li key={index} className="flex items-start gap-2">
                      <div className="w-2 h-2 bg-emerald-500 rounded-full mt-2 flex-shrink-0" />
                      <span className="text-gray-700">{point}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* 时间轴分析 */}
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
                    {index < data.analysis.timeline.length - 1 && <div className="w-px h-16 bg-gray-200 mt-2" />}
                  </div>
                  <div className="flex-1 pb-6">
                    <div className="flex items-center gap-2 mb-2">
                      <Badge variant="outline" className="font-mono text-xs">
                        {item.timestamp}
                      </Badge>
                      {item.severity > 1 && (
                        <Badge className={getSeverityColor(item.severity)}>风险等级: {item.severity}</Badge>
                      )}
                    </div>
                    <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                      <div>
                        <h4 className="font-medium text-sm text-gray-900 mb-1">画面描述</h4>
                        <p className="text-sm text-gray-600">{item.scene_description}</p>
                      </div>
                      <div>
                        <h4 className="font-medium text-sm text-gray-900 mb-1">音频转写</h4>
                        <p className="text-sm text-gray-600 italic">"{item.audio_transcript}"</p>
                      </div>
                      <div>
                        <h4 className="font-medium text-sm text-gray-900 mb-1">问题分析</h4>
                        <p className="text-sm text-gray-600">{item.issue}</p>
                      </div>
                      {item.evidence && (
                        <div>
                          <h4 className="font-medium text-sm text-gray-900 mb-1">证据要点</h4>
                          <p className="text-sm text-gray-600">{item.evidence}</p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

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
