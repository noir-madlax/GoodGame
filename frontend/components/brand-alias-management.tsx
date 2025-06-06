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
import { Search, Edit, Trash2, Save, X, Plus } from "lucide-react"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

// 定义数据类型
interface BrandAlias {
  id: number
  alias: string
  officialName: string
  type: string
  description: string
  examples: string[]
  popularity: number
  verified: boolean
}

// 模拟的品牌别名数据
const initialAliasData: BrandAlias[] = [
  {
    id: 1,
    alias: "ACM",
    officialName: "刺客信条：幻影刺客",
    type: "游戏简称",
    description: "Assassin's Creed Mirage的英文缩写",
    examples: ["ACM的画面真不错", "ACM什么时候打折"],
    popularity: 85,
    verified: true,
  },
  {
    id: 2,
    alias: "幻影刺客",
    officialName: "刺客信条：幻影刺客",
    type: "游戏简称",
    description: "游戏副标题的简称",
    examples: ["幻影刺客优化怎么样", "幻影刺客值得买吗"],
    popularity: 92,
    verified: true,
  },
  {
    id: 3,
    alias: "巴辛姆",
    officialName: "刺客信条：幻影刺客",
    type: "主角名称",
    description: "游戏主角的名字",
    examples: ["巴辛姆的技能很酷", "巴辛姆的故事线不错"],
    popularity: 78,
    verified: true,
  },
  {
    id: 4,
    alias: "AC新作",
    officialName: "刺客信条：幻影刺客",
    type: "通用称呼",
    description: "作为刺客信条系列新作的通用称呼",
    examples: ["AC新作什么时候出", "AC新作回到了经典玩法"],
    popularity: 65,
    verified: false,
  },
  {
    id: 5,
    alias: "巴格达刺客",
    officialName: "刺客信条：幻影刺客",
    type: "地点相关",
    description: "基于游戏背景地巴格达的称呼",
    examples: ["巴格达刺客的场景很美", "巴格达刺客还原了历史"],
    popularity: 45,
    verified: false,
  },
  {
    id: 6,
    alias: "育碧新游",
    officialName: "刺客信条：幻影刺客",
    type: "厂商相关",
    description: "作为育碧新游戏的称呼",
    examples: ["育碧新游又优化不好", "育碧新游画面还是可以的"],
    popularity: 38,
    verified: false,
  },
]

export function BrandAliasManagement() {
  const [aliasData, setAliasData] = useState<BrandAlias[]>(initialAliasData)
  const [searchTerm, setSearchTerm] = useState("")
  const [typeFilter, setTypeFilter] = useState("all")
  const [editingId, setEditingId] = useState<number | null>(null)
  const [isAdding, setIsAdding] = useState(false)

  // 新别名的表单状态
  const [newAlias, setNewAlias] = useState({
    alias: "",
    officialName: "刺客信条：幻影刺客",
    type: "游戏简称",
    description: "",
    examples: [""],
    popularity: 0,
    verified: false,
  })

  // 编辑中的别名状态
  const [editingAlias, setEditingAlias] = useState<BrandAlias>({
    id: 0,
    alias: "",
    officialName: "",
    type: "",
    description: "",
    examples: [""],
    popularity: 0,
    verified: false,
  })

  // 过滤数据
  const filteredData = aliasData.filter((item) => {
    const matchesSearch =
      item.alias.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.examples.some((example) => example.toLowerCase().includes(searchTerm.toLowerCase()))

    const matchesType = typeFilter === "all" || item.type === typeFilter

    return matchesSearch && matchesType
  })

  // 添加新别名
  const handleAddAlias = () => {
    const newId = Math.max(...aliasData.map((item) => item.id)) + 1
    setAliasData([...aliasData, { id: newId, ...newAlias }])
    setNewAlias({
      alias: "",
      officialName: "刺客信条：幻影刺客",
      type: "游戏简称",
      description: "",
      examples: [""],
      popularity: 0,
      verified: false,
    })
    setIsAdding(false)
  }

  // 开始编辑别名
  const startEditing = (item: BrandAlias) => {
    setEditingId(item.id)
    setEditingAlias({ ...item })
  }

  // 保存编辑的别名
  const saveEdit = () => {
    setAliasData(aliasData.map((item) => (item.id === editingId ? editingAlias : item)))
    setEditingId(null)
  }

  // 取消编辑
  const cancelEdit = () => {
    setEditingId(null)
  }

  // 删除别名
  const deleteAlias = (id: number) => {
    setAliasData(aliasData.filter((item) => item.id !== id))
  }

  // 验证别名
  const verifyAlias = (id: number) => {
    setAliasData(aliasData.map((item) => (item.id === id ? { ...item, verified: true } : item)))
  }

  // 获取热度标签
  const getPopularityBadge = (popularity: number) => {
    if (popularity >= 80) {
      return <Badge className="bg-red-500">热门</Badge>
    } else if (popularity >= 60) {
      return <Badge className="bg-orange-500">常用</Badge>
    } else if (popularity >= 40) {
      return <Badge className="bg-yellow-500">一般</Badge>
    } else {
      return <Badge className="bg-gray-500">冷门</Badge>
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>品牌别名管理</CardTitle>
        <CardDescription>管理游戏产品的各种别名、代称、主角名称等，帮助AI准确识别玩家讨论的游戏内容</CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="browse">
          <TabsList className="mb-4">
            <TabsTrigger value="browse">浏览别名库</TabsTrigger>
            <TabsTrigger value="add">添加新别名</TabsTrigger>
            <TabsTrigger value="analytics">使用分析</TabsTrigger>
          </TabsList>

          <TabsContent value="browse">
            <div className="space-y-4">
              <div className="flex flex-col md:flex-row gap-4">
                <div className="flex-1 relative">
                  <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="搜索别名、描述或使用示例..."
                    className="pl-8"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                  />
                </div>

                <Select value={typeFilter} onValueChange={setTypeFilter}>
                  <SelectTrigger className="w-[180px]">
                    <SelectValue placeholder="类型筛选" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">所有类型</SelectItem>
                    <SelectItem value="游戏简称">游戏简称</SelectItem>
                    <SelectItem value="主角名称">主角名称</SelectItem>
                    <SelectItem value="通用称呼">通用称呼</SelectItem>
                    <SelectItem value="地点相关">地点相关</SelectItem>
                    <SelectItem value="厂商相关">厂商相关</SelectItem>
                    <SelectItem value="玩家俚语">玩家俚语</SelectItem>
                  </SelectContent>
                </Select>

                <Button onClick={() => setIsAdding(true)}>
                  <Plus className="mr-2 h-4 w-4" />
                  添加别名
                </Button>
              </div>

              <div className="border rounded-md">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>别名/代称</TableHead>
                      <TableHead>官方名称</TableHead>
                      <TableHead>类型</TableHead>
                      <TableHead>描述</TableHead>
                      <TableHead>使用示例</TableHead>
                      <TableHead>热度</TableHead>
                      <TableHead>状态</TableHead>
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
                                value={editingAlias.alias}
                                onChange={(e) => setEditingAlias({ ...editingAlias, alias: e.target.value })}
                              />
                            </TableCell>
                            <TableCell>
                              <Select
                                value={editingAlias.officialName}
                                onValueChange={(value) => setEditingAlias({ ...editingAlias, officialName: value })}
                              >
                                <SelectTrigger>
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="刺客信条：幻影刺客">刺客信条：幻影刺客</SelectItem>
                                  <SelectItem value="孤岛惊魂6">孤岛惊魂6</SelectItem>
                                  <SelectItem value="彩虹六号：围攻">彩虹六号：围攻</SelectItem>
                                </SelectContent>
                              </Select>
                            </TableCell>
                            <TableCell>
                              <Select
                                value={editingAlias.type}
                                onValueChange={(value) => setEditingAlias({ ...editingAlias, type: value })}
                              >
                                <SelectTrigger>
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="游戏简称">游戏简称</SelectItem>
                                  <SelectItem value="主角名称">主角名称</SelectItem>
                                  <SelectItem value="通用称呼">通用称呼</SelectItem>
                                  <SelectItem value="地点相关">地点相关</SelectItem>
                                  <SelectItem value="厂商相关">厂商相关</SelectItem>
                                  <SelectItem value="玩家俚语">玩家俚语</SelectItem>
                                </SelectContent>
                              </Select>
                            </TableCell>
                            <TableCell>
                              <Textarea
                                value={editingAlias.description}
                                onChange={(e) => setEditingAlias({ ...editingAlias, description: e.target.value })}
                                rows={2}
                              />
                            </TableCell>
                            <TableCell>
                              <Textarea
                                value={editingAlias.examples.join("\n")}
                                onChange={(e) =>
                                  setEditingAlias({
                                    ...editingAlias,
                                    examples: e.target.value.split("\n").filter((ex) => ex.trim()),
                                  })
                                }
                                rows={2}
                                placeholder="每行一个示例"
                              />
                            </TableCell>
                            <TableCell>
                              <Input
                                type="number"
                                min="0"
                                max="100"
                                value={editingAlias.popularity}
                                onChange={(e) =>
                                  setEditingAlias({
                                    ...editingAlias,
                                    popularity: Number.parseInt(e.target.value) || 0,
                                  })
                                }
                              />
                            </TableCell>
                            <TableCell>
                              <Badge variant={editingAlias.verified ? "default" : "secondary"}>
                                {editingAlias.verified ? "已验证" : "待验证"}
                              </Badge>
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
                            <TableCell className="font-medium">{item.alias}</TableCell>
                            <TableCell>{item.officialName}</TableCell>
                            <TableCell>
                              <Badge variant="outline">{item.type}</Badge>
                            </TableCell>
                            <TableCell className="max-w-xs truncate">{item.description}</TableCell>
                            <TableCell>
                              <div className="space-y-1">
                                {item.examples.slice(0, 2).map((example, idx) => (
                                  <div key={idx} className="text-sm text-muted-foreground italic">
                                    "{example}"
                                  </div>
                                ))}
                                {item.examples.length > 2 && (
                                  <div className="text-xs text-muted-foreground">+{item.examples.length - 2} 更多</div>
                                )}
                              </div>
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center gap-2">
                                {getPopularityBadge(item.popularity)}
                                <span className="text-sm text-muted-foreground">{item.popularity}%</span>
                              </div>
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center gap-2">
                                {item.verified ? (
                                  <Badge className="bg-green-500">已验证</Badge>
                                ) : (
                                  <Badge variant="secondary">待验证</Badge>
                                )}
                              </div>
                            </TableCell>
                            <TableCell>
                              <div className="flex gap-2">
                                <Button size="sm" variant="ghost" onClick={() => startEditing(item)}>
                                  <Edit className="h-4 w-4" />
                                </Button>
                                {!item.verified && (
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    className="text-green-600"
                                    onClick={() => verifyAlias(item.id)}
                                  >
                                    验证
                                  </Button>
                                )}
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  className="text-red-500"
                                  onClick={() => deleteAlias(item.id)}
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
                共 {filteredData.length} 条记录 (总计 {aliasData.length} 条)
              </div>
            </div>
          </TabsContent>

          <TabsContent value="add">
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="new-alias">别名/代称</Label>
                  <Input
                    id="new-alias"
                    placeholder="输入游戏别名或代称"
                    value={newAlias.alias}
                    onChange={(e) => setNewAlias({ ...newAlias, alias: e.target.value })}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="new-official">官方名称</Label>
                  <Select
                    value={newAlias.officialName}
                    onValueChange={(value) => setNewAlias({ ...newAlias, officialName: value })}
                  >
                    <SelectTrigger id="new-official">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="刺客信条：幻影刺客">刺客信条：幻影刺客</SelectItem>
                      <SelectItem value="孤岛惊魂6">孤岛惊魂6</SelectItem>
                      <SelectItem value="彩虹六号：围攻">彩虹六号：围攻</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="new-type">类型</Label>
                  <Select value={newAlias.type} onValueChange={(value) => setNewAlias({ ...newAlias, type: value })}>
                    <SelectTrigger id="new-type">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="游戏简称">游戏简称</SelectItem>
                      <SelectItem value="主角名称">主角名称</SelectItem>
                      <SelectItem value="通用称呼">通用称呼</SelectItem>
                      <SelectItem value="地点相关">地点相关</SelectItem>
                      <SelectItem value="厂商相关">厂商相关</SelectItem>
                      <SelectItem value="玩家俚语">玩家俚语</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="new-popularity">预估热度 (0-100)</Label>
                  <Input
                    id="new-popularity"
                    type="number"
                    min="0"
                    max="100"
                    placeholder="0"
                    value={newAlias.popularity}
                    onChange={(e) => setNewAlias({ ...newAlias, popularity: Number.parseInt(e.target.value) || 0 })}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="new-description">描述</Label>
                <Textarea
                  id="new-description"
                  placeholder="详细描述该别名的来源和含义"
                  value={newAlias.description}
                  onChange={(e) => setNewAlias({ ...newAlias, description: e.target.value })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="new-examples">使用示例</Label>
                <Textarea
                  id="new-examples"
                  placeholder="提供一些使用该别名的例句，每行一个"
                  value={newAlias.examples.join("\n")}
                  onChange={(e) =>
                    setNewAlias({
                      ...newAlias,
                      examples: e.target.value.split("\n").filter((ex) => ex.trim()),
                    })
                  }
                  rows={3}
                />
              </div>

              <div className="flex justify-end gap-2 pt-4">
                <Button variant="outline" onClick={() => setIsAdding(false)}>
                  取消
                </Button>
                <Button onClick={handleAddAlias} disabled={!newAlias.alias || !newAlias.description}>
                  添加别名
                </Button>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="analytics">
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card>
                  <CardHeader className="py-3">
                    <CardTitle className="text-base">热门别名</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {aliasData
                        .sort((a, b) => b.popularity - a.popularity)
                        .slice(0, 5)
                        .map((item, i) => (
                          <div key={i} className="flex justify-between items-center">
                            <span className="text-sm">{item.alias}</span>
                            <span className="text-sm font-medium">{item.popularity}%</span>
                          </div>
                        ))}
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="py-3">
                    <CardTitle className="text-base">类型分布</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {Object.entries(
                        aliasData.reduce(
                          (acc, item) => {
                            acc[item.type] = (acc[item.type] || 0) + 1
                            return acc
                          },
                          {} as Record<string, number>,
                        ),
                      ).map(([type, count]) => (
                        <div key={type} className="flex justify-between items-center">
                          <span className="text-sm">{type}</span>
                          <span className="text-sm font-medium">{count}</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="py-3">
                    <CardTitle className="text-base">验证状态</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      <div className="flex justify-between items-center">
                        <span className="text-sm">已验证</span>
                        <span className="text-sm font-medium text-green-600">
                          {aliasData.filter((item) => item.verified).length}
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm">待验证</span>
                        <span className="text-sm font-medium text-orange-600">
                          {aliasData.filter((item) => !item.verified).length}
                        </span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              <Card>
                <CardHeader>
                  <CardTitle>使用趋势</CardTitle>
                  <CardDescription>各别名在舆情监测中的使用频率变化</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-[300px] flex items-center justify-center text-muted-foreground">
                    [别名使用趋势图表 - 展示不同别名在监测中的使用频率变化]
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}
