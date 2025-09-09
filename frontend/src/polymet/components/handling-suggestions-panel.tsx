import React, { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import { cn } from "@/lib/utils";
import { AlertTriangle, Loader2 } from "lucide-react";
import SampleHandlingSuggestions from "@/polymet/sample-code/sample";

/**
 * 处理建议展示抽屉组件
 * 作用：当用户点击“生成处理建议”时，调用该组件，通过 analysisId 或 postId 从表 `public.gg_video_analysis`
 * 加载 `handling_suggestions` 字段的 JSON，并渲染为设计稿样式。
 * 
 * 使用位置建议：详情页视频卡片按钮点击后弹出（父组件控制 open 与 onClose）。
 * 
 * props:
 * - open: 是否打开
 * - onClose: 关闭回调
 * - analysisId?: gg_video_analysis.id（二选一）
 * - postId?: gg_video_analysis.post_id（当未提供 analysisId 时作为查询条件）
 */

export interface HandlingSuggestionsPanelProps {
  open: boolean;
  onClose: () => void;
  analysisId?: number | string;
  postId?: number | string;
  className?: string;
}

type LegalBasis = { law_name: string; article: string; why_relevant: string };

type Strategy = {
  tone: "good" | "strict";
  target: string;
  talk_track: string;
  incentives: string[];
  legal_basis: LegalBasis[];
  platform_policy_basis: string[];
  required_actions: string[];
  escalation_path: string;
};

type DbSuggestions = {
  overview: string;
  severity: "low" | "medium" | "high";
  priority: "P1" | "P2" | "P3";
  legal_risk_summary: string;
  strategies: Strategy[];
  outreach_channels: string[];
  follow_up_checklist: string[];
  redact_suggestions: string[];
};

const isValidSuggestions = (val: unknown): val is DbSuggestions => {
  if (!val || typeof val !== "object") return false;
  const v = val as Record<string, unknown>;
  return (
    typeof v.overview === "string" &&
    typeof v.severity === "string" &&
    typeof v.priority === "string" &&
    typeof v.legal_risk_summary === "string" &&
    Array.isArray(v.strategies)
  );
};

const toStringSafe = (v: unknown, fallback = ""): string => (typeof v === "string" ? v : fallback);
const toStringArray = (v: unknown): string[] => (Array.isArray(v) ? v.map((x) => toStringSafe(x)) : []);

const toLegalBasisArray = (v: unknown): LegalBasis[] =>
  Array.isArray(v)
    ? v.map((x) => {
        const obj = (typeof x === "object" && x !== null ? (x as Record<string, unknown>) : {}) as Record<string, unknown>;
        return {
          law_name: toStringSafe(obj["law_name"]),
          article: toStringSafe(obj["article"]),
          why_relevant: toStringSafe(obj["why_relevant"]),
        } as LegalBasis;
      })
    : [];

// 兜底：将数据库 JSON 规整为组件需要的完整结构（填充缺省字段）
const normalizeSuggestions = (raw: unknown): DbSuggestions | null => {
  if (!isValidSuggestions(raw)) return null;
  const r = raw as Record<string, unknown>;
  const strategiesInput = Array.isArray(r.strategies) ? (r.strategies as unknown[]) : [];
  const strategies: Strategy[] = strategiesInput.map((sUnknown) => {
    const s = (typeof sUnknown === "object" && sUnknown !== null ? (sUnknown as Record<string, unknown>) : {}) as Record<string, unknown>;
    const toneRaw = toStringSafe(s["tone"], "good");
    const tone: "good" | "strict" = toneRaw === "strict" ? "strict" : "good";
    return {
      tone,
      target: toStringSafe(s["target"], "发布者"),
      talk_track: toStringSafe(s["talk_track"], ""),
      incentives: toStringArray(s["incentives"]),
      legal_basis: toLegalBasisArray(s["legal_basis"]),
      platform_policy_basis: toStringArray(s["platform_policy_basis"]),
      required_actions: toStringArray(s["required_actions"]),
      escalation_path: toStringSafe(s["escalation_path"], ""),
    };
  });
  const severityRaw = toStringSafe(r["severity"], "medium");
  const priorityRaw = toStringSafe(r["priority"], "P2");
  const severityVals = ["low", "medium", "high"] as const;
  const priorityVals = ["P1", "P2", "P3"] as const;
  const severity = (severityVals.includes(severityRaw as typeof severityVals[number]) ? (severityRaw as typeof severityVals[number]) : "medium");
  const priority = (priorityVals.includes(priorityRaw as typeof priorityVals[number]) ? (priorityRaw as typeof priorityVals[number]) : "P2");
  return {
    overview: toStringSafe(r["overview"], ""),
    severity,
    priority,
    legal_risk_summary: toStringSafe(r["legal_risk_summary"], ""),
    strategies,
    outreach_channels: toStringArray(r["outreach_channels"]),
    follow_up_checklist: toStringArray(r["follow_up_checklist"]),
    redact_suggestions: toStringArray(r["redact_suggestions"]),
  };
};

const EmptyBox: React.FC<{ message?: string; className?: string }> = ({ message = "暂无处理建议数据", className }) => (
  <div className={cn("p-8 rounded-2xl bg-white/10 backdrop-blur-xl border border-white/20 text-center", className)}>
    <div className="mx-auto mb-3 w-10 h-10 rounded-full bg-yellow-500/15 border border-yellow-500/30 flex items-center justify-center">
      <AlertTriangle className="w-5 h-5 text-yellow-600" />
    </div>
    <div className="text-sm text-gray-600 dark:text-gray-300">{message}</div>
  </div>
);

export default function HandlingSuggestionsPanel({ open, onClose, analysisId, postId, className }: HandlingSuggestionsPanelProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<DbSuggestions | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      if (!open) return;
      setLoading(true);
      setError(null);
      try {
        if (!supabase) throw new Error("Supabase 未初始化");
        type Row = { id: number; post_id: number | null; handling_suggestions: unknown } | null;
        let query = supabase
          .from("gg_video_analysis")
          .select("id, post_id, handling_suggestions")
          .limit(1);
        if (analysisId != null) query = query.eq("id", analysisId);
        else if (postId != null) query = query.eq("post_id", postId).order("id", { ascending: false });
        const { data: row, error: dbErr } = await query.maybeSingle<Row>();
        if (dbErr) throw dbErr;
        const hs = row?.handling_suggestions;
        if (!cancelled) {
          const normalized = normalizeSuggestions(hs);
          setData(normalized);
        }
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : "加载失败";
        if (!cancelled) setError(msg);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, [open, analysisId, postId]);

  if (!open) return null;

  // 加载态
  if (loading) {
    return (
      <div className={cn("w-full max-w-6xl mx-auto rounded-3xl bg-white/10 backdrop-blur-xl border border-white/20 shadow-2xl p-10 flex items-center justify-center", className)}>
        <Loader2 className="w-5 h-5 mr-2 animate-spin text-gray-500" />
        <span className="text-sm text-gray-600 dark:text-gray-300">正在加载处理建议…</span>
      </div>
    );
  }

  // 错误态
  if (error) {
    return <EmptyBox message={`加载失败：${error}`} className={className} />;
  }

  // 空态
  if (!data) {
    return <EmptyBox message="未查询到处理建议数据" className={className} />;
  }

  // 直接复用 sample 展示组件
  return <SampleHandlingSuggestions data={data} isOpen={true} onClose={onClose} className={className} />;
}
