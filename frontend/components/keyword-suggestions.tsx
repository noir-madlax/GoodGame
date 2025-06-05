import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

interface KeywordSuggestionsProps {
  keywords: string[]
}

export function KeywordSuggestions({ keywords }: KeywordSuggestionsProps) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium">AI推荐关键词</h4>
        <Button variant="ghost" size="sm">
          全部添加
        </Button>
      </div>
      <div className="flex flex-wrap gap-2">
        {keywords.map((keyword, index) => (
          <Badge key={index} variant="outline" className="cursor-pointer hover:bg-secondary">
            {keyword} +
          </Badge>
        ))}
      </div>
    </div>
  )
}
