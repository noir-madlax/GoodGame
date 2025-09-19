import React, { useState } from "react";
import { Link as LinkIcon, Clock, Search, Settings } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";
import { useToast } from "@/hooks/use-toast";
import { useNavigate } from "react-router-dom";
import { buildApiUrl } from "@/lib/api";

/**
 * 页面：内容检索设置（一级页面）
 * 说明：将“页面壳 + 手动补充分析 + 系统自动化配置”三段设计代码合并为单文件；
 *      数据写死；平台图标统一使用站内 /douyin.svg 与 /xiaohongshu.svg；
 *      样式与 CSS 类名保持与设计一致。
 */
export default function ContentRetrievalSettings() {
  return (
    <div className="min-h-screen p-6 space-y-8">
      {/* 页面标题 */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">内容检索设置</h1>
      </div>

      {/* 手动补充分析区域 */}
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-2 h-8 bg-gradient-to-b from-blue-500 to-purple-600 rounded-full" />
          <div>
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">分析内容补充</h2>
           
          </div>
        </div>
        <LinkAnalysisSection />
      </div>

      {/* 分隔线 */}
      <div className="border-t border-white/20" />

      {/* 系统自动化配置区域 */}
      <BatchProcessingConfig />
    </div>
  );
}

/**
 * 子组件：手动补充分析输入区
 * 交互：模拟 2 秒“分析中”，结束后清空输入。样式保持不变。
 */
const LinkAnalysisSection: React.FC<{ className?: string }> = ({ className }) => {
  const [link, setLink] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [progress, setProgress] = useState(0);
  const { toast } = useToast();
  const navigate = useNavigate();

  // —— 与 ImportAnalyzeDialog 一致的提交流程（去弹窗化） ——
  const douyinRe = /(^https?:\/\/)?([\w.-]+\.)?(douyin|iesdouyin)\.com\/.+/i;
  const xhsRe = /(^https?:\/\/)?([\w.-]+\.)?(xiaohongshu|xhslink)\.(com|cn)\/.+/i;
  const stripUtm = (url: string) => {
    try {
      const u = new URL(url);
      ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"].forEach((k) => u.searchParams.delete(k));
      return u.toString();
    } catch {
      return url.trim();
    }
  };
  const extractFirstUrl = (text: string): string | null => {
    if (!text) return null;
    const t = String(text).trim();
    const protoRe = /(https?:\/\/[^\s"'<>)+\]]+)/i;
    const m1 = t.match(protoRe);
    if (m1 && m1[1]) return m1[1];
    const noProtoRe = /((?:www\.)?(?:v\.)?(?:douyin|iesdouyin|xiaohongshu|xhslink)\.(?:com|cn)\/[^\s"'<>)+\]]+)/i;
    const m2 = t.match(noProtoRe);
    if (m2 && m2[1]) return `https://${m2[1]}`;
    return null;
  };
  const handleAnalyze = async () => {
    const raw = link.trim();
    if (!raw) return;
    const picked = extractFirstUrl(raw);
    if (!picked) {
      toast({ title: "提交失败", description: "未识别到有效链接，请检查分享内容" });
      return;
    }
    const url = stripUtm(picked);
    if (!(douyinRe.test(url) || xhsRe.test(url))) {
      toast({ title: "仅支持抖音或小红书链接" });
      return;
    }
    setIsAnalyzing(true);
    // 启动本地 10s 进度条动画（100 步，每 100ms +1）
    setProgress(0);
    const start = Date.now();
    const interval = setInterval(() => {
      setProgress((p) => {
        const next = Math.min(99, p + 1); // 保持 99% 以内，待请求完成再补满
        return next;
      });
    }, 100);
    const maxTimer = setTimeout(() => {
      setProgress(99);
    }, 10000);
    try {
      const endpoint = buildApiUrl("/api/import/analyze");
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ trace_id: String(Date.now()), url }),
      });
      const data: Record<string, unknown> = await res.json().catch(() => ({} as Record<string, unknown>));
      const code = (data as { code?: number }).code;
      const success = (data as { success?: boolean }).success;
      if (res.ok && (code === 0 || success === true)) {
        toast({ title: "已受理", description: "任务已提交，稍后在“标记内容与处理”查看。" });
        setLink("");
        // 填充进度至 100%，稍作停顿再跳转
        setProgress(100);
        const remaining = Math.max(0, 400 - (Date.now() - start));
        setTimeout(() => navigate("/marks"), remaining);
        return;
      }
      const message = String((data as { message?: unknown }).message ?? "请稍后重试");
      toast({ title: "提交失败", description: message });
    } catch (e: unknown) {
      toast({ title: "提交失败", description: e instanceof Error ? e.message : "网络异常" });
    } finally {
      clearInterval(interval);
      clearTimeout(maxTimer);
      setIsAnalyzing(false);
    }
  };

  return (
    <Card className={cn("bg-white/10 backdrop-blur-xl border-white/20", className)}>
      <CardContent className="p-6">
        <div className="flex items-center gap-4">
          {/* 左侧：平台 + 链接符号，不要文字 */}
          <div className="flex items-center gap-2 text-gray-900 dark:text-white">
            <img src="/douyin.svg" alt="抖音" className="w-6 h-6" />
            <img src="/xiaohongshu.svg" alt="小红书" className="w-6 h-6" />
            <LinkIcon className="w-6 h-6 text-blue-400" />
          </div>
          <div className="flex-1 flex gap-3">
            <Input
              placeholder="例如：https://www.douyin.com/video/xxxx 或 https://www.xiaohongshu.com/xxxx"
              value={link}
              onChange={(e) => setLink(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") handleAnalyze(); }}
              className="bg-white/5 border-white/20 text-gray-900 dark:text-white placeholder:text-gray-500 dark:placeholder:text-gray-400"
              disabled={isAnalyzing}
              aria-label="粘贴需要分析的链接"
            />
            <Button
              onClick={handleAnalyze}
              disabled={!link.trim() || isAnalyzing}
              className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white border-0 px-6"
              aria-label="开始分析"
            >
              {isAnalyzing ? "分析中..." : "分析"}
            </Button>
          </div>
          {/* 进度条 */}
          {isAnalyzing && (
            <div className="w-full mt-3">
              <div className="h-1.5 w-full bg-white/10 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-blue-500 to-purple-600 transition-all duration-100"
                  style={{ width: `${progress}%` }}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={progress}
                  role="progressbar"
                />
              </div>
              <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">正在提交与排队分析，请稍候...</div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

/**
 * 子组件：系统自动化配置（只读展示，数据写死）
 * 平台图标：统一为 /douyin.svg 与 /xiaohongshu.svg
 */
const BatchProcessingConfig: React.FC<{ className?: string }> = ({ className }) => {
  const batchConfig = {
    schedule: {
      time: "10:00",
      description: "系统自动内容爬取",
      timezone: "UTC+8 北京时间",
    },
    keywords: {
      list: ["海底捞", "火锅", "餐饮服务"],
    },
    platforms: {
      active: [
        { name: "抖音", key: "douyin", limit: "2000" },
        { name: "小红书", key: "xiaohongshu", limit: "1500" },
      ],
    },
    analysisSettings: {
      authorAnalysis: true,
      commentAnalysis: true,
      subtitleGeneration: true,
      suggestionGeneration: true,
      suspiciousAnalysis: true,
    },
  } as const;

  const renderPlatformImg = (key: string) => {
    if (key === "douyin") return <img src="/douyin.svg" alt="抖音" className="w-8 h-8" />;
    if (key === "xiaohongshu") return <img src="/xiaohongshu.svg" alt="小红书" className="w-8 h-8" />;
    return null;
  };

  const getColorClass = (key: string) => (key === "douyin" ? "from-black to-red-600" : key === "xiaohongshu" ? "from-red-500 to-pink-600" : "from-gray-400 to-gray-600");

  return (
    <div className={`space-y-6 ${className || ""}`}>
      {/* 系统自动内容爬取设置区域标识 */}
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 rounded-lg bg-gradient-to-r from-blue-500/20 to-purple-500/20">
          <Settings className="w-5 h-5 text-blue-600 dark:text-blue-400" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">系统自动内容爬取设置</h3>
        </div>
      </div>

      {/* 处理时间安排（优化：直接展示简洁文案） */}
      <Card className="bg-white/10 backdrop-blur-xl border-white/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-3 text-gray-900 dark:text-white">
            <div className="p-2 rounded-lg bg-blue-500/20">
              <Clock className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            </div>
            自动处理时间
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="p-4 rounded-xl bg-white/5 border border-white/10 text-gray-900 dark:text-white">
          
            <div className="mt-1 font-semibold">每日 10:00 自动处理任务</div>
            <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">北京时间（UTC+8）</div>
          </div>
        </CardContent>
      </Card>

      {/* 监控关键词配置 */}
      <Card className="bg-white/10 backdrop-blur-xl border-white/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-3 text-gray-900 dark:text-white">
            <div className="p-2 rounded-lg bg-green-500/20">
              <Search className="w-5 h-5 text-green-600 dark:text-green-400" />
            </div>
            监控关键词配置
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {batchConfig.keywords.list.map((keyword, index) => (
              <Badge key={index} variant="outline" className="bg-blue-50 border-blue-200 text-blue-800">
                {keyword}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 监控平台 + 每日数据限制（合并展示） */}
      <Card className="bg-white/10 backdrop-blur-xl border-white/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-3 text-gray-900 dark:text-white">
            <div className="p-2 rounded-lg bg-purple-500/20">
              <Search className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            </div>
            监控平台与每日限制
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {batchConfig.platforms.active.map((platform, index) => (
              <div key={index} className="p-4 rounded-xl bg-white/5 border border-white/10">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center`}>
                      {renderPlatformImg(platform.key)}
                    </div>
                    <span className="font-medium text-gray-900 dark:text-white">{platform.name}</span>
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-bold text-gray-900 dark:text-white">{platform.limit}</div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">条/天</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 分析配置选项 */}
      <Card className="bg-white/10 backdrop-blur-xl border-white/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-3 text-gray-900 dark:text-white">
            <div className="p-2 rounded-lg bg-green-500/20">
              <Settings className="w-5 h-5 text-green-600 dark:text-green-400" />
            </div>
            分析配置选项
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex items-center justify-between p-3 rounded-lg bg-white/5 border border-white/10">
              <span className="text-gray-900 dark:text-white font-medium">作者信息分析</span>
              <Switch checked={batchConfig.analysisSettings.authorAnalysis} disabled className="data-[state=checked]:bg-green-500" />
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg bg-white/5 border border-white/10">
              <span className="text-gray-900 dark:text-white font-medium">评论内容分析</span>
              <Switch checked={batchConfig.analysisSettings.commentAnalysis} disabled className="data-[state=checked]:bg-green-500" />
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg bg-white/5 border border-white/10">
              <span className="text-gray-900 dark:text-white font-medium">视频字幕生成</span>
              <Switch checked={batchConfig.analysisSettings.subtitleGeneration} disabled className="data-[state=checked]:bg-green-500" />
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg bg-white/5 border border-white/10">
              <span className="text-gray-900 dark:text-white font-medium">处理建议生成</span>
              <Switch checked={batchConfig.analysisSettings.suggestionGeneration} disabled className="data-[state=checked]:bg-green-500" />
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg bg-white/5 border border-white/10 ">
              <span className="text-gray-900 dark:text-white font-medium">疑似内容深度分析</span>
              <Switch checked={batchConfig.analysisSettings.suspiciousAnalysis} disabled className="data-[state=checked]:bg-green-500 w-10 h-6" />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};


