import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { supabase } from "@/lib/supabase";
import HandlingSuggestionsView, { HandlingSuggestionsData } from "@/polymet/components/handling-suggestions-view";
import { SectionSkeleton } from "@/polymet/components/loading-skeletons";
import { ArrowLeft, Bookmark, Download } from "lucide-react";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

export default function HandlingSuggestionsPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState<boolean>(false);
  const [data, setData] = useState<HandlingSuggestionsData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [postTitle, setPostTitle] = useState<string>("");
  const [postPlatform, setPostPlatform] = useState<string>("");

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        setLoading(true);
        setError(null);
        if (!id || !supabase) return;
        // 建议数据
        const { data: row, error: dbErr } = await supabase
          .from("gg_video_analysis")
          .select("handling_suggestions")
          .eq("platform_item_id", id)
          .order("id", { ascending: false })
          .maybeSingle();
        if (dbErr) throw dbErr;
        const hs = (row as { handling_suggestions?: unknown } | null)?.handling_suggestions as HandlingSuggestionsData | undefined;
        if (!cancelled) setData((hs as HandlingSuggestionsData) || null);
        // 最小元信息（用于保存）
        const { data: posts } = await supabase
          .from("gg_platform_post")
          .select("title, platform")
          .eq("platform_item_id", id)
          .limit(1);
        if (!cancelled && posts && posts[0]) {
          setPostTitle(String(posts[0].title || ""));
          setPostPlatform(String(posts[0].platform || ""));
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

  const handleSaveAdvice = () => {
    if (!id) return;
    try {
      const payload = {
        id,
        platform_item_id: id,
        title: postTitle,
        platform: postPlatform,
        created_at: new Date().toISOString(),
      };
      const key = "gg_action_advices";
      const arr = JSON.parse(localStorage.getItem(key) || "[]");
      arr.unshift(payload);
      localStorage.setItem(key, JSON.stringify(arr.slice(0, 200)));
    } catch (e) {
      // no-op
    }
  };

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
