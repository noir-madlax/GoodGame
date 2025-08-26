import { NextResponse } from "next/server"
import fs from "fs/promises"

// Read card data from backend JSON and map to frontend card shape
export async function GET() {
  try {
    let raw: string
    try {
      // preferred path on Vercel: read from public data
      raw = await fs.readFile(process.cwd() + "/public/data/douyin/card.json", "utf-8")
    } catch {
      // fallback to backend path for local dev
      const filePath = "/Users/rigel/project/goodgame/backend/test/output/douyin/output/prd/#⼩狗已经沉浸在海底捞⽆法⾃拔了/card.json"
      raw = await fs.readFile(filePath, "utf-8")
    }
    const json = JSON.parse(raw)
    const data = json.data || {}
    const stats = data.statistics || {}

    const durationMs: number = Number(data.duration || 0)
    const durationSec = Math.floor(durationMs / 1000)
    const minutes = Math.floor(durationSec / 60)
    const seconds = String(durationSec % 60).padStart(2, "0")

    const createTime: number | undefined = data.create_time
    const publishTime = createTime ? new Date(createTime * 1000).toLocaleString("zh-CN") : ""

    const awemeId: string = json.aweme_id || ""
    const mapped = {
      id: 1,
      title: data.preview_title || data.desc || "",
      description: data.desc || "",
      thumbnail: (data.url_list && data.url_list[0]) || "",
      platform: "抖音",
      author: data.nickname || "",
      likes: Number(stats.digg_count || 0),
      comments: Number(stats.comment_count || 0),
      shares: Number(stats.share_count || 0),
      sentiment: "negative", // will align with detail.json
      duration: `${minutes}:${seconds}`,
      publishTime,
      contentType: "视频",
      views: Number(stats.play_count || 0),
      riskLevel: "中风险",
      // provide empty risk_types to be merged from detail API on client
      risk_types: [],
      original_url: awemeId ? `https://www.douyin.com/video/${awemeId}` : "",
    }

    return NextResponse.json(mapped)
  } catch (error: any) {
    return NextResponse.json({ error: error?.message || "Failed to load" }, { status: 500 })
  }
}


