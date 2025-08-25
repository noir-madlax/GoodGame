"use client"

import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"

export function PlatformSelector() {
  return (
    <div className="space-y-3">
      <div className="flex items-center space-x-2">
        <Checkbox id="bilibili" defaultChecked />
        <Label htmlFor="bilibili">哔哩哔哩</Label>
      </div>
      <div className="flex items-center space-x-2">
        <Checkbox id="tieba" defaultChecked />
        <Label htmlFor="tieba">百度贴吧</Label>
      </div>
      <div className="flex items-center space-x-2">
        <Checkbox id="weibo" defaultChecked />
        <Label htmlFor="weibo">微博</Label>
      </div>
      <div className="flex items-center space-x-2">
        <Checkbox id="xiaohongshu" />
        <Label htmlFor="xiaohongshu">小红书</Label>
      </div>
      <div className="flex items-center space-x-2">
        <Checkbox id="douyin" />
        <Label htmlFor="douyin">抖音</Label>
      </div>
      <div className="flex items-center space-x-2">
        <Checkbox id="zhihu" />
        <Label htmlFor="zhihu">知乎</Label>
      </div>
    </div>
  )
}
