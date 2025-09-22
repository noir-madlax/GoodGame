import React, { useMemo, useState } from "react";
import { useProject } from "@/polymet/lib/project-context";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";
import { useNavigate } from "react-router-dom";
import { buildApiUrl } from "@/lib/api";

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

// 从整段文本中提取第一个可用链接（支持缺少协议的短链）
const extractFirstUrl = (text: string): string | null => {
  if (!text) return null;
  const t = String(text).trim();
  // 1) 先找带协议的链接
  const protoRe = /(https?:\/\/[^\s"'<>)+\]]+)/i;
  const m1 = t.match(protoRe);
  if (m1 && m1[1]) return m1[1];
  // 2) 再找常见平台的无协议链接
  const noProtoRe = /((?:www\.)?(?:v\.)?(?:douyin|iesdouyin|xiaohongshu|xhslink)\.(?:com|cn)\/[^\s"'<>)+\]]+)/i;
  const m2 = t.match(noProtoRe);
  if (m2 && m2[1]) return `https://${m2[1]}`;
  return null;
};

export default function ImportAnalyzeDialog({ isOpen, onOpenChange }: Props) {
  const [value, setValue] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();
  const navigate = useNavigate();
  const { activeProjectId } = useProject();

  const platform: "douyin" | "xiaohongshu" | null = useMemo(() => {
    const v = value.trim();
    const extracted = extractFirstUrl(v) || v;
    if (!v) return null;
    if (douyinRe.test(extracted)) return "douyin";
    if (xhsRe.test(extracted)) return "xiaohongshu";
    return null;
  }, [value]);

  const isValidUrl = useMemo(() => {
    const v = value.trim();
    if (!v) return false;
    const extracted = extractFirstUrl(v);
    if (!extracted) return false;
    return douyinRe.test(extracted) || xhsRe.test(extracted);
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
      const picked = extractFirstUrl(raw);
      if (!picked) {
        setError("未识别到有效链接，请检查分享内容");
        setSubmitting(false);
        return;
      }
      const url = stripUtm(picked);
      const endpoint = buildApiUrl("/api/import/analyze");
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ trace_id: String(Date.now()), url, project_id: activeProjectId || undefined }),
      });
      const data = await res.json().catch(() => ({} as any));
      if (res.ok && data && (data.code === 0 || data.success === true)) {
        toast({ title: "已受理", description: "任务已提交，稍后在“标记内容与处理”查看。" });
        setValue("");
        onOpenChange(false);
        // 成功后跳转至标记页，便于用户查看最新标记内容
        navigate("/marks");
        return;
      }
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


