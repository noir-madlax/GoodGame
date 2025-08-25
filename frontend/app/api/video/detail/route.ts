import { NextResponse } from "next/server"
import fs from "fs/promises"

// Read detail data from backend JSON and map to frontend detail shape
export async function GET() {
  try {
    const filePath = "/Users/rigel/project/goodgame/backend/test/output/douyin/output/prd/#⼩狗已经沉浸在海底捞⽆法⾃拔了/detail.json"
    const raw = await fs.readFile(filePath, "utf-8")
    const json = JSON.parse(raw)
    const result = json.result || {}

    // collect unique risk types for header badges
    const riskTypes: string[] = []
    const riskSet = new Set<string>()
    ;(result.timeline || []).forEach((t: any) => {
      ;(t.risk_type || []).forEach((r: string) => {
        if (!riskSet.has(r)) {
          riskSet.add(r)
          riskTypes.push(r)
        }
      })
    })

    const mapped = {
      id: 1,
      analysis: {
        summary: result.summary || "",
        sentiment: result.sentiment || "neutral",
        brand: result.brand || "",
        timeline: (result.timeline || []).map((t: any) => ({
          timestamp: t.timestamp || "",
          scene_description: t.scene_description || "",
          audio_transcript: t.audio_transcript || "",
          issue: t.issue || "",
          risk_type: t.risk_type || [],
          severity: 3,
          evidence: (t.evidence && t.evidence[0] && t.evidence[0].details) || "",
        })),
        key_points: result.key_points || [],
        risks: [],
      },
      risk_types: riskTypes,
    }

    return NextResponse.json(mapped)
  } catch (error: any) {
    return NextResponse.json({ error: error?.message || "Failed to load" }, { status: 500 })
  }
}


