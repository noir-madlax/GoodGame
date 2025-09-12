import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { supabase } from "@/lib/supabase";
import HandlingSuggestionsView, { HandlingSuggestionsData } from "@/polymet/components/handling-suggestions-view";
import { SectionSkeleton } from "@/polymet/components/loading-skeletons";
import { ArrowLeft, Bookmark, Download, BellRing } from "lucide-react";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

export default function HandlingSuggestionsPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState<boolean>(false);
  const [data, setData] = useState<HandlingSuggestionsData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [postTitle, setPostTitle] = useState<string>("");
  const [postPlatform, setPostPlatform] = useState<string>("");
  // 处理状态（用于图标显色与乐观更新）
  const [processStatus, setProcessStatus] = useState<string | null>(null);
  const [tip, setTip] = useState<string | null>(null);
  const [tipFading, setTipFading] = useState<boolean>(false);
  // 与详情页保持一致的轻提示，不提供额外定位参数

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        setLoading(true);
        setError(null);
        if (!id || !supabase) return;
        // 先按 post.id 查询，得到 platform_item_id / 标题 / 平台
        const { data: posts, error: pErr } = await supabase
          .from("gg_platform_post")
          .select("id, platform_item_id, title, platform, process_status")
          .eq("id", id)
          .limit(1);
        if (pErr) throw pErr;
        const p = posts && posts[0];
        let hs: HandlingSuggestionsData | null = null;
        if (p?.platform_item_id) {
          const { data: row, error: dbErr } = await supabase
            .from("gg_video_analysis")
            .select("handling_suggestions")
            .eq("platform_item_id", p.platform_item_id)
            .order("id", { ascending: false })
            .maybeSingle();
          if (dbErr) throw dbErr;
          hs = ((row as { handling_suggestions?: unknown } | null)?.handling_suggestions as HandlingSuggestionsData | undefined) || null;
        }
        if (!cancelled) setData(hs);
        // 最小元信息（用于展示）
        if (!cancelled && posts && posts[0]) {
          setPostTitle(String(posts[0].title || ""));
          setPostPlatform(String(posts[0].platform || ""));
          setProcessStatus((posts[0] as any).process_status || null);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "查询失败");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, [id]);

  // 已移除本地存储的保存逻辑
  // 顶部提示 2 秒自动消失
  useEffect(() => {
    if (!tip) return;
    setTipFading(false);
    const t1 = setTimeout(() => setTipFading(true), 1500);
    const t2 = setTimeout(() => setTip(null), 2000);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, [tip]);

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* 顶部返回 + 右侧操作按钮 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <button
            className="p-3 rounded-xl bg-white/10 backdrop-blur-xl border border-white/20 hover:bg-white/20 transition-all duration-300 shadow-lg hover:shadow-xl"
            onClick={() => navigate(-1)}
            aria-label="返回"
          >
            <ArrowLeft className="w-5 h-5 text-gray-700 dark:text-gray-300" />
          </button>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">处理建议</h1>
        </div>
        <TooltipProvider>
          <div className="flex items-center space-x-2">
            {/* 需处理：图标按钮，点击置 process_status=处理中 */}
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  className="p-3 rounded-xl bg-white/10 backdrop-blur-xl border border-white/20 hover:bg-white/20 transition-all duration-300 shadow-lg hover:shadow-xl"
                  aria-label="标记该视频为需处理"
                  onClick={async () => {
                    try {
                      if (!id || !supabase) return;
                      // 乐观更新：仅改变图标颜色；提示在成功后再显示
                      const prev = processStatus;
                      const next = prev === "处理中" ? null : "处理中";
                      setProcessStatus(next);
                      const { error: dbErr } = await supabase
                        .from("gg_platform_post")
                        .update({ process_status: next })
                        .eq("id", id);
                      if (dbErr) {
                        // 回滚
                        setProcessStatus(prev || null);
                        setTip("操作失败，请重试");
                      } else {
                        setTip(next === "处理中" ? "已标记为需处理" : "已取消需处理");
                      }
                    } catch {
                      setTip("操作失败，请重试");
                    }
                  }}
                >
                  <BellRing className={"w-5 h-5 " + (processStatus === "处理中" ? "text-red-600 dark:text-red-400" : "text-gray-700 dark:text-gray-300")} />
                </button>
              </TooltipTrigger>
              <TooltipContent>标记该视频为需处理</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <button className="p-3 rounded-xl bg-white/10 backdrop-blur-xl border border-white/20 hover:bg-white/20 transition-all duration-300 shadow-lg hover:shadow-xl" aria-label="导出报告">
                  <Download className="w-5 h-5 text-gray-700 dark:text-gray-300" />
                </button>
              </TooltipTrigger>
              <TooltipContent>导出</TooltipContent>
            </Tooltip>
          </div>
        </TooltipProvider>
      </div>
      {/* 右上角轻提示：完全复用详情页的视觉与定位 */}
      {tip && (
        <div
          className={
            "pointer-events-none absolute left-[92%] -translate-x-1/2 top-[56px] text-xs px-1 py-0.5 whitespace-nowrap text-gray-500/80 transition-opacity duration-500 " +
            (tipFading ? "opacity-0" : "opacity-100")
          }
        >
          {tip}
        </div>
      )}

      {loading ? (
        <SectionSkeleton rows={6} />
      ) : error ? (
        <div className="p-8 text-sm text-red-600">加载失败：{error}</div>
      ) : !data ? (
        <div className="p-8 text-sm text-gray-600">暂无处理建议数据</div>
      ) : (
        <HandlingSuggestionsView data={data} isOpen={true} onClose={() => navigate(-1)} showHeader={false} />
      )}
    </div>
  );
}
