import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"

export function DataTable() {
  const data = [
    {
      id: 1,
      content: "刺客信条幻影刺客的画面真的太惊艳了，育碧这次做得很棒！",
      platform: "哔哩哔哩",
      date: "2025-04-15",
      sentiment: "positive",
      confidence: 0.92,
    },
    {
      id: 2,
      content: "游戏优化还是有问题，高配置电脑都有点卡顿",
      platform: "百度贴吧",
      date: "2025-04-12",
      sentiment: "negative",
      confidence: 0.85,
    },
    {
      id: 3,
      content: "剧情设计中规中矩，没有特别惊喜的地方",
      platform: "微博",
      date: "2025-04-10",
      sentiment: "neutral",
      confidence: 0.78,
    },
    {
      id: 4,
      content: "这代的战斗系统有了很大改进，但是任务设计还是有些重复",
      platform: "哔哩哔哩",
      date: "2025-04-08",
      sentiment: "mixed",
      confidence: 0.65,
    },
    {
      id: 5,
      content: "育碧这次的开放世界设计真的很用心，每个角落都有惊喜",
      platform: "百度贴吧",
      date: "2025-04-05",
      sentiment: "positive",
      confidence: 0.89,
    },
  ]

  const getSentimentBadge = (sentiment: string) => {
    switch (sentiment) {
      case "positive":
        return <Badge className="bg-green-500">正面</Badge>
      case "negative":
        return <Badge className="bg-red-500">负面</Badge>
      case "neutral":
        return <Badge className="bg-gray-500">中性</Badge>
      case "mixed":
        return <Badge className="bg-yellow-500">混合</Badge>
      default:
        return <Badge>未知</Badge>
    }
  }

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>内容</TableHead>
            <TableHead>平台</TableHead>
            <TableHead>日期</TableHead>
            <TableHead>情感倾向</TableHead>
            <TableHead>置信度</TableHead>
            <TableHead>操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.map((row) => (
            <TableRow key={row.id}>
              <TableCell className="max-w-md truncate">{row.content}</TableCell>
              <TableCell>{row.platform}</TableCell>
              <TableCell>{row.date}</TableCell>
              <TableCell>{getSentimentBadge(row.sentiment)}</TableCell>
              <TableCell>{(row.confidence * 100).toFixed(0)}%</TableCell>
              <TableCell>
                <Button variant="ghost" size="sm">
                  查看
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

import { Button } from "@/components/ui/button"
