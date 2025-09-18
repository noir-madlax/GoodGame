import React, { useMemo, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";
import { useNavigate } from "react-router-dom";

interface Props {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
}

// 前端平台匹配正则（最小可用）
const douyinRe = /(^https?:\/\/)?([\w.-]+\.)?(douyin|iesdouyin)\.com\/.+/i;
const xhsRe = /(^https?:\/\/)?([\w.-]+\.)?(xiaohongshu|xhslink)\.(com|cn)\/.+/i;

// 基础去噪：移除常见追踪参数
const stripUtm = (url: string) => {
  try {
    const u = new URL(url);
    ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"].forEach((k) => u.searchParams.delete(k));
    return u.toString();
  } catch {
    return url.trim();
  }
};

export default function ImportAnalyzeDialog({ isOpen, onOpenChange }: Props) {
  const [value, setValue] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();
  const navigate = useNavigate();

  const platform: "douyin" | "xiaohongshu" | null = useMemo(() => {
    const v = value.trim();
    if (!v) return null;
    if (douyinRe.test(v)) return "douyin";
    if (xhsRe.test(v)) return "xiaohongshu";
    return null;
  }, [value]);

  const isValidUrl = useMemo(() => {
    const v = value.trim();
    if (!v) return false;
    if (!/^https?:\/\//i.test(v)) return false;
    return douyinRe.test(v) || xhsRe.test(v);
  }, [value]);

  const handleSubmit = async () => {
    const raw = value.trim();
    if (!raw) {
      setError("请粘贴链接");
      return;
    }
    if (!isValidUrl) {
      setError("仅支持抖音或小红书链接");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      const url = stripUtm(raw);
      const res = await fetch("/api/import/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      const data = await res.json().catch(() => ({}));
      // 去重命中：直接跳详情
      if (data && data.status === "exists" && data.analysisId) {
        onOpenChange(false);
        navigate(`/detail/${data.analysisId}`);
        return;
      }
      if (res.ok && data && (data.status === "queued" || data.taskId)) {
        onOpenChange(false);
        toast({
          title: "已受理",
          description:
            "该链接的分析任务已提交。为便于集中查看，我们会自动为该内容打上“标记”，几分钟后可在“标记内容与处理”页面统一查看，避免与列表内容混在一起。",
        });
        setValue("");
        return;
      }
      // 其他情况简单提示
      toast({ title: "提交失败", description: String(data?.message || "请稍后重试") });
    } catch (e: unknown) {
      toast({ title: "提交失败", description: e instanceof Error ? e.message : "网络异常" });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[520px]">
        <DialogHeader>
          <DialogTitle>导入链接分析</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <label className="text-sm text-gray-600 dark:text-gray-300">粘贴抖音或小红书链接</label>
          <Input
            placeholder="例如：https://www.douyin.com/video/xxxx 或 https://www.xiaohongshu.com/explore/xxxx"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleSubmit(); }}
            aria-invalid={!isValidUrl && !!value}
          />
          {error && (
            <div className="text-xs text-red-600">{error}</div>
          )}
          <div className="flex items-center justify-between">
            <div className={cn("text-xs", platform ? "text-gray-500" : "text-gray-400")}>识别平台：{platform ? (platform === "douyin" ? "抖音" : "小红书") : "未识别"}</div>
            <Button disabled={!isValidUrl || submitting} onClick={handleSubmit}>
              {submitting ? "提交中..." : "提交分析"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}


