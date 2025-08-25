"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Search, Edit, Trash2, Save, X, Download, Upload } from "lucide-react"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

// 定义数据类型
interface SlangItem {
  id: number
  term: string
  meaning: string
  example: string
  category: string
  sentiment: string
  games: string[]
}

// 模拟的游戏黑话数据
const initialSlangData: SlangItem[] = [
  {
    id: 1,
    term: "肝",
    meaning: "长时间投入游戏，不断重复某些内容以获取资源或成就",
    example: "这个周末我要肝一下这个新副本",
    category: "游戏行为",
    sentiment: "neutral",
    games: ["通用", "刺客信条"],
  },
  {
    id: 2,
    term: "氪金",
    meaning: "在游戏中花费真实货币购买游戏内物品或服务",
    example: "这个皮肤太好看了，我忍不住氪金了",
    category: "消费行为",
    sentiment: "negative",
    games: ["通用"],
  },
  {
    id: 3,
    term: "毒瘤",
    meaning: "形容某个游戏机制或角色非常不平衡，令人厌烦",
    example: "这个角色真是毒瘤，技能太强了",
    category: "游戏体验",
    sentiment: "negative",
    games: ["通用"],
  },
  {
    id: 4,
    term: "手残",
    meaning: "自嘲操作技术不好",
    example: "我太手残了，这个BOSS打了十次都没过",
    category: "玩家能力",
    sentiment: "negative",
    games: ["通用"],
  },
  {
    id: 5,
    term: "爽到飞起",
    meaning: "游戏体验非常好，令人兴奋",
    example: "新版本的战斗系统爽到飞起",
    category: "游戏体验",
    sentiment: "positive",
    games: ["通用", "刺客信条"],
  },
  {
    id: 6,
    term: "闪退",
    meaning: "游戏突然关闭或崩溃",
    example: "这个版本经常闪退，希望官方尽快修复",
    category: "技术问题",
    sentiment: "negative",
    games: ["通用"],
  },
  {
    id: 7,
    term: "鸽了",
    meaning: "开发者延期或取消了先前承诺的内容",
    example: "这个DLC又被鸽了，要等到下个月",
    category: "开发状态",
    sentiment: "negative",
    games: ["通用"],
  },
  {
    id: 8,
    term: "破防",
    meaning: "情绪被触动，通常是因为游戏中的感人剧情或令人沮丧的体验",
    example: "这个结局直接让我破防了",
    category: "情感反应",
    sentiment: "mixed",
    games: ["通用"],
  },
  {
    id: 9,
    term: "ACG",
    meaning: "刺客信条幻影刺客的缩写",
    example: "ACG的画面真的很惊艳",
    category: "游戏名称",
    sentiment: "neutral",
    games: ["刺客信条"],
  },
  {
    id: 10,
    term: "育碧式塔",
    meaning: "讽刺育碧游戏中常见的需要爬上去同步的高塔",
    example: "又是一堆育碧式塔，爬得我手酸",
    category: "游戏机制",
    sentiment: "negative",
    games: ["刺客信条", "孤岛惊魂"],
  },
]

export function GameSlangKnowledgeBase() {
  const [slangData, setSlangData] = useState<SlangItem[]>(initialSlangData)
  const [searchTerm, setSearchTerm] = useState("")
  const [categoryFilter, setCategoryFilter] = useState("all")
  const [sentimentFilter, setSentimentFilter] = useState("all")
  const [gameFilter, setGameFilter] = useState("all")
  const [editingId, setEditingId] = useState<number | null>(null)
  const [isAdding, setIsAdding] = useState(false)

  // 新词条的表单状态
  const [newTerm, setNewTerm] = useState({
    term: "",
    meaning: "",
    example: "",
    category: "游戏行为",
    sentiment: "neutral",
    games: ["通用"],
  })

  // 编辑中的词条状态
  const [editingTerm, setEditingTerm] = useState<SlangItem>({
    id: 0,
    term: "",
    meaning: "",
    example: "",
    category: "",
    sentiment: "",
    games: [""],
  })

  // 过滤数据
  const filteredData = slangData.filter((item) => {
    const matchesSearch =
      item.term.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.meaning.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.example.toLowerCase().includes(searchTerm.toLowerCase())

    const matchesCategory = categoryFilter === "all" || item.category === categoryFilter
    const matchesSentiment = sentimentFilter === "all" || item.sentiment === sentimentFilter
    const matchesGame = gameFilter === "all" || item.games.includes(gameFilter)

    return matchesSearch && matchesCategory && matchesSentiment && matchesGame
  })

  // 添加新词条
  const handleAddTerm = () => {
    const newId = Math.max(...slangData.map((item) => item.id)) + 1
    setSlangData([...slangData, { id: newId, ...newTerm }])
    setNewTerm({
      term: "",
      meaning: "",
      example: "",
      category: "游戏行为",
      sentiment: "neutral",
      games: ["通用"],
    })
    setIsAdding(false)
  }

  // 开始编辑词条
  const startEditing = (item: SlangItem) => {
    setEditingId(item.id)
    setEditingTerm({ ...item })
  }

  // 保存编辑的词条
  const saveEdit = () => {
    setSlangData(slangData.map((item) => (item.id === editingId ? editingTerm : item)))
    setEditingId(null)
  }

  // 取消编辑
  const cancelEdit = () => {
    setEditingId(null)
  }

  // 删除词条
  const deleteTerm = (id: number) => {
    setSlangData(slangData.filter((item) => item.id !== id))
  }

  // 获取情感标签样式
  const getSentimentBadge = (sentiment: string) => {
    switch (sentiment) {
      case "positive":
        return <Badge className="bg-green-500">正面</Badge>
      case "negative":
        return <Badge className="bg-red-500">负面</Badge>
      case "mixed":
        return <Badge className="bg-yellow-500">混合</Badge>
      default:
        return <Badge className="bg-gray-500">中性</Badge>
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>游戏黑话知识库</CardTitle>
        <CardDescription>维护游戏玩家常用的黑话、术语和热词，帮助AI更准确理解玩家评论</CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="browse">
          <TabsList className="mb-4">
            <TabsTrigger value="browse">浏览知识库</TabsTrigger>
            <TabsTrigger value="add">添加新词条</TabsTrigger>
            <TabsTrigger value="import">导入/导出</TabsTrigger>
          </TabsList>

          <TabsContent value="browse">
            <div className="space-y-4">
              <div className="flex flex-col md:flex-row gap-4">
                <div className="flex-1 relative">
                  <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="搜索黑话、含义或示例..."
                    className="pl-8"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                  />
                </div>

                <Select value={categoryFilter} onValueChange={setCategoryFilter}>
                  <SelectTrigger className="w-[180px]">
                    <SelectValue placeholder="分类筛选" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">所有分类</SelectItem>
                    <SelectItem value="游戏行为">游戏行为</SelectItem>
                    <SelectItem value="消费行为">消费行为</SelectItem>
                    <SelectItem value="游戏体验">游戏体验</SelectItem>
                    <SelectItem value="玩家能力">玩家能力</SelectItem>
                    <SelectItem value="技术问题">技术问题</SelectItem>
                    <SelectItem value="开发状态">开发状态</SelectItem>
                    <SelectItem value="情感反应">情感反应</SelectItem>
                    <SelectItem value="游戏名称">游戏名称</SelectItem>
                    <SelectItem value="游戏机制">游戏机制</SelectItem>
                  </SelectContent>
                </Select>

                <Select value={sentimentFilter} onValueChange={setSentimentFilter}>
                  <SelectTrigger className="w-[180px]">
                    <SelectValue placeholder="情感筛选" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">所有情感</SelectItem>
                    <SelectItem value="positive">正面</SelectItem>
                    <SelectItem value="negative">负面</SelectItem>
                    <SelectItem value="neutral">中性</SelectItem>
                    <SelectItem value="mixed">混合</SelectItem>
                  </SelectContent>
                </Select>

                <Select value={gameFilter} onValueChange={setGameFilter}>
                  <SelectTrigger className="w-[180px]">
                    <SelectValue placeholder="游戏筛选" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">所有游戏</SelectItem>
                    <SelectItem value="通用">通用</SelectItem>
                    <SelectItem value="刺客信条">刺客信条</SelectItem>
                    <SelectItem value="孤岛惊魂">孤岛惊魂</SelectItem>
                    <SelectItem value="彩虹六号">彩虹六号</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="border rounded-md">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>黑话/术语</TableHead>
                      <TableHead>含义</TableHead>
                      <TableHead>示例</TableHead>
                      <TableHead>分类</TableHead>
                      <TableHead>情感倾向</TableHead>
                      <TableHead>适用游戏</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredData.map((item) => (
                      <TableRow key={item.id}>
                        {editingId === item.id ? (
                          // 编辑模式
                          <>
                            <TableCell>
                              <Input
                                value={editingTerm.term}
                                onChange={(e) => setEditingTerm({ ...editingTerm, term: e.target.value })}
                              />
                            </TableCell>
                            <TableCell>
                              <Textarea
                                value={editingTerm.meaning}
                                onChange={(e) => setEditingTerm({ ...editingTerm, meaning: e.target.value })}
                                rows={2}
                              />
                            </TableCell>
                            <TableCell>
                              <Input
                                value={editingTerm.example}
                                onChange={(e) => setEditingTerm({ ...editingTerm, example: e.target.value })}
                              />
                            </TableCell>
                            <TableCell>
                              <Select
                                value={editingTerm.category}
                                onValueChange={(value) => setEditingTerm({ ...editingTerm, category: value })}
                              >
                                <SelectTrigger>
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="游戏行为">游戏行为</SelectItem>
                                  <SelectItem value="消费行为">消费行为</SelectItem>
                                  <SelectItem value="游戏体验">游戏体验</SelectItem>
                                  <SelectItem value="玩家能力">玩家能力</SelectItem>
                                  <SelectItem value="技术问题">技术问题</SelectItem>
                                  <SelectItem value="开发状态">开发状态</SelectItem>
                                  <SelectItem value="情感反应">情感反应</SelectItem>
                                  <SelectItem value="游戏名称">游戏名称</SelectItem>
                                  <SelectItem value="游戏机制">游戏机制</SelectItem>
                                </SelectContent>
                              </Select>
                            </TableCell>
                            <TableCell>
                              <Select
                                value={editingTerm.sentiment}
                                onValueChange={(value) => setEditingTerm({ ...editingTerm, sentiment: value })}
                              >
                                <SelectTrigger>
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="positive">正面</SelectItem>
                                  <SelectItem value="negative">负面</SelectItem>
                                  <SelectItem value="neutral">中性</SelectItem>
                                  <SelectItem value="mixed">混合</SelectItem>
                                </SelectContent>
                              </Select>
                            </TableCell>
                            <TableCell>
                              <Input
                                value={editingTerm.games.join(", ")}
                                onChange={(e) =>
                                  setEditingTerm({
                                    ...editingTerm,
                                    games: e.target.value.split(",").map((g) => g.trim()),
                                  })
                                }
                              />
                            </TableCell>
                            <TableCell>
                              <div className="flex gap-2">
                                <Button size="sm" variant="ghost" onClick={saveEdit}>
                                  <Save className="h-4 w-4" />
                                </Button>
                                <Button size="sm" variant="ghost" onClick={cancelEdit}>
                                  <X className="h-4 w-4" />
                                </Button>
                              </div>
                            </TableCell>
                          </>
                        ) : (
                          // 查看模式
                          <>
                            <TableCell className="font-medium">{item.term}</TableCell>
                            <TableCell>{item.meaning}</TableCell>
                            <TableCell className="text-muted-foreground italic">{item.example}</TableCell>
                            <TableCell>{item.category}</TableCell>
                            <TableCell>{getSentimentBadge(item.sentiment)}</TableCell>
                            <TableCell>{item.games.join(", ")}</TableCell>
                            <TableCell>
                              <div className="flex gap-2">
                                <Button size="sm" variant="ghost" onClick={() => startEditing(item)}>
                                  <Edit className="h-4 w-4" />
                                </Button>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  className="text-red-500"
                                  onClick={() => deleteTerm(item.id)}
                                >
                                  <Trash2 className="h-4 w-4" />
                                </Button>
                              </div>
                            </TableCell>
                          </>
                        )}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              <div className="text-sm text-muted-foreground text-right">
                共 {filteredData.length} 条记录 (总计 {slangData.length} 条)
              </div>
            </div>
          </TabsContent>

          <TabsContent value="add">
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="new-term">黑话/术语</Label>
                  <Input
                    id="new-term"
                    placeholder="输入游戏黑话或术语"
                    value={newTerm.term}
                    onChange={(e) => setNewTerm({ ...newTerm, term: e.target.value })}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="new-category">分类</Label>
                  <Select
                    value={newTerm.category}
                    onValueChange={(value) => setNewTerm({ ...newTerm, category: value })}
                  >
                    <SelectTrigger id="new-category">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="游戏行为">游戏行为</SelectItem>
                      <SelectItem value="消费行为">消费行为</SelectItem>
                      <SelectItem value="游戏体验">游戏体验</SelectItem>
                      <SelectItem value="玩家能力">玩家能力</SelectItem>
                      <SelectItem value="技术问题">技术问题</SelectItem>
                      <SelectItem value="开发状态">开发状态</SelectItem>
                      <SelectItem value="情感反应">情感反应</SelectItem>
                      <SelectItem value="游戏名称">游戏名称</SelectItem>
                      <SelectItem value="游戏机制">游戏机制</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="new-meaning">含义</Label>
                <Textarea
                  id="new-meaning"
                  placeholder="详细解释该术语的含义"
                  value={newTerm.meaning}
                  onChange={(e) => setNewTerm({ ...newTerm, meaning: e.target.value })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="new-example">使用示例</Label>
                <Input
                  id="new-example"
                  placeholder="提供一个使用该术语的例句"
                  value={newTerm.example}
                  onChange={(e) => setNewTerm({ ...newTerm, example: e.target.value })}
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="new-sentiment">情感倾向</Label>
                  <Select
                    value={newTerm.sentiment}
                    onValueChange={(value) => setNewTerm({ ...newTerm, sentiment: value })}
                  >
                    <SelectTrigger id="new-sentiment">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="positive">正面</SelectItem>
                      <SelectItem value="negative">负面</SelectItem>
                      <SelectItem value="neutral">中性</SelectItem>
                      <SelectItem value="mixed">混合</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="new-games">适用游戏</Label>
                  <Input
                    id="new-games"
                    placeholder="输入适用游戏，用逗号分隔"
                    value={newTerm.games.join(", ")}
                    onChange={(e) =>
                      setNewTerm({
                        ...newTerm,
                        games: e.target.value.split(",").map((g) => g.trim()),
                      })
                    }
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-4">
                <Button variant="outline" onClick={() => setIsAdding(false)}>
                  取消
                </Button>
                <Button onClick={handleAddTerm} disabled={!newTerm.term || !newTerm.meaning}>
                  添加词条
                </Button>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="import">
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold mb-2">导出知识库</h3>
                <p className="text-muted-foreground mb-4">导出当前的游戏黑话知识库，可用于备份或在其他系统中使用</p>
                <div className="flex gap-2">
                  <Button variant="outline">
                    <Download className="mr-2 h-4 w-4" />
                    导出为CSV
                  </Button>
                  <Button variant="outline">
                    <Download className="mr-2 h-4 w-4" />
                    导出为JSON
                  </Button>
                </div>
              </div>

              <div className="border-t pt-6">
                <h3 className="text-lg font-semibold mb-2">导入知识库</h3>
                <p className="text-muted-foreground mb-4">从CSV或JSON文件导入游戏黑话知识库，将与现有数据合并</p>
                <div className="flex flex-col gap-4">
                  <div className="flex items-center justify-center w-full">
                    <label
                      htmlFor="dropzone-file"
                      className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed rounded-lg cursor-pointer bg-gray-50 hover:bg-gray-100"
                    >
                      <div className="flex flex-col items-center justify-center pt-5 pb-6">
                        <Upload className="w-8 h-8 mb-3 text-gray-400" />
                        <p className="mb-2 text-sm text-gray-500">
                          <span className="font-semibold">点击上传</span> 或拖放文件
                        </p>
                        <p className="text-xs text-gray-500">支持 CSV 或 JSON 格式</p>
                      </div>
                      <input id="dropzone-file" type="file" className="hidden" />
                    </label>
                  </div>

                  <div className="flex justify-end">
                    <Button>
                      <Upload className="mr-2 h-4 w-4" />
                      导入文件
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}
