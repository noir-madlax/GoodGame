/* eslint-disable @typescript-eslint/no-explicit-any */
// 过滤规则工具库（与页面/组件使用点对应）：
// - 被 ContentDashboard 用于构建白名单与相关性回填
// - 被 FilterBar 用于加载全量枚举（来自 gg_filter_enums）
// - 本文件不包含任何 React 代码，便于在 hooks/服务端/组件中复用

// 中文说明：相关性标签统一枚举；
// 使用位置：VideoGridCard 左上角角标文案与筛选值
export type RelevanceLabel = "相关" | "疑似相关" | "不相关";

// 功能：将初筛 relevant_status(y/n/maybe) 映射为品牌相关性风格标签
// 使用位置：ContentDashboard 在没有 brand_relevance 时回填最终相关性
export const mapRelevantStatus = (status?: string | null): RelevanceLabel | "" => {
  const raw = String(status || "").toLowerCase();
  if (raw === "yes") return "相关";
  if (raw === "maybe") return "疑似相关";
  if (raw === "no") return "不相关";
  return "";
};

// 功能：执行“细分覆盖初筛”的回填逻辑（有 brand_relevance 用之；否则用 relevant_status 映射回填）
// 使用位置：ContentDashboard 列表渲染前对可见帖子批量回填，供筛选与角标统一使用
export const backfillRelevance = (
  relevanceMap: Record<string, string>,
  posts: { platform_item_id: string; relevant_status?: string | null }[]
): Record<string, string> => {
  const next: Record<string, string> = { ...relevanceMap };
  posts.forEach((p) => {
    const key = p.platform_item_id;
    if (!key) return;
    if (!next[key]) {
      const mapped = mapRelevantStatus(p.relevant_status);
      if (mapped) next[key] = mapped;
    }
  });
  return next;
};

export interface AnalysisFilters {
  sentiment: string; // all | positive | neutral | negative
  relevance: string; // all | 相关 | 疑似相关 | 不相关
  riskScenario: string; // all | scenario text
}

// 功能：根据当前筛选构建 platform_item_id 白名单
// 规则：
//  - 优先使用分析表 brand_relevance 命中的 ids
//  - 若相关性筛选不为 all，则将初筛 relevant_status 命中的 ids 并入（保证“仅初筛命中”的内容不丢失）
// 使用位置：ContentDashboard 在筛选激活时用于帖子分页查询前置过滤
export const buildRelevanceWhitelist = async (
  sb: any,
  filters: AnalysisFilters
): Promise<string[]> => {
  const { sentiment, relevance, riskScenario } = filters;
  const idsSet = new Set<string>();

  // 1) from analysis table
  const { data: aRows } = await sb
    .from("gg_video_analysis")
    .select("platform_item_id, risk_types, sentiment, brand_relevance")
    .limit(20000);
  (aRows || []).forEach((r: { platform_item_id: string; risk_types?: any; sentiment?: string | null; brand_relevance?: string | null }) => {
    const okSent = sentiment === "all" || r.sentiment === sentiment;
    const okRel = relevance === "all" || r.brand_relevance === relevance;
    let okRisk = true;
    if (riskScenario !== "all") {
      const raw = r.risk_types as any;
      const names: string[] = Array.isArray(raw)
        ? (raw as any[])
            .map((x) => {
              if (typeof x === "string") return x;
              if (x && typeof x === "object") {
                const obj = x as { category?: unknown; scenario?: unknown };
                if (typeof obj.category === "string") return obj.category;
                if (typeof obj.scenario === "string") return obj.scenario;
              }
              return "";
            })
            .filter((s) => Boolean(s))
        : [];
      okRisk = names.includes(riskScenario);
    }
    if (okSent && okRel && okRisk && r.platform_item_id) idsSet.add(r.platform_item_id);
  });

  // 2) union from screening when relevance is explicitly chosen
  if (relevance !== "all") {
    const statusWanted = relevance === "相关" ? "yes" : relevance === "疑似相关" ? "maybe" : relevance === "不相关" ? "no" : null;
    if (statusWanted) {
      const { data: sRows } = await sb
        .from("gg_platform_post")
        .select("platform_item_id, relevant_status")
        .eq("relevant_status", statusWanted)
        .limit(20000);
      (sRows || []).forEach((r: { platform_item_id: string | null }) => {
        if (r.platform_item_id) idsSet.add(r.platform_item_id);
      });
    }
  }

  return Array.from(idsSet);
};

// 功能：读取全量筛选枚举（平台/类型/情绪/相关性/风险场景）并做文案归一
// 使用位置：FilterBar 在挂载时加载筛选项，保持稳定且与分页无关
export const fetchGlobalFilterEnums = async (sb: any) => {
  const { data } = await sb.from("gg_filter_enums").select("kind, value, label").limit(2000);
  const rows = (data || []) as { kind: string; value: string; label: string | null }[];

  const normalizeLabel = (k: string, v: string, l?: string | null) => {
    if (k === "sentiment") {
      if (v === "positive") return "正向";
      if (v === "neutral") return "中立";
      if (v === "negative") return "负面";
    }
    if (k === "platform") {
      const map: Record<string, string> = { douyin: "抖音", xiaohongshu: "小红书", xhs: "小红书", weibo: "微博" };
      return map[v] || l || v;
    }
    if (k === "post_type") {
      const map: Record<string, string> = { video: "视频", image: "图文", note: "图文", text: "文本", unknown: "其他" };
      return map[v] || l || v;
    }
    return l || v;
  };

  const byKind = (kind: string) => rows.filter((r) => r.kind === kind);
  const channels = byKind("platform").map((r) => ({ id: r.value, label: normalizeLabel("platform", r.value, r.label) }));
  const types = byKind("post_type").map((r) => ({ id: r.value, label: normalizeLabel("post_type", r.value, r.label) }));
  const sentiments = byKind("sentiment").map((r) => ({ id: r.value, label: normalizeLabel("sentiment", r.value, r.label) }));
  const relevances = byKind("brand_relevance").map((r) => ({ id: r.value, label: normalizeLabel("brand_relevance", r.value, r.label) }));
  const risks = byKind("risk_scenario").map((r) => ({ id: r.value, label: r.label || r.value }));

  return {
    channels: [{ id: "all", label: "全部渠道" }, ...channels.sort((a, b) => a.label.localeCompare(b.label))],
    types: [{ id: "all", label: "全部类型" }, ...types.sort((a, b) => a.label.localeCompare(b.label))],
    sentiments: [{ id: "all", label: "全部情绪" }, ...sentiments],
    relevances: [{ id: "all", label: "全部相关性" }, ...relevances],
    risks: [{ id: "all", label: "全部场景", count: 0 }, ...risks.map((r) => ({ ...r, count: 0 }))],
  };
};



// 功能：将 "today/week/month" 转换为起始时间，all 返回 null。
// 使用位置：ContentDashboard -> 首屏与滚动加载后的客户端过滤。
export const resolveStartAt = (timeRange: "all" | "today" | "week" | "month") => {
  const now = new Date();
  if (timeRange === "today") return new Date(now.getFullYear(), now.getMonth(), now.getDate());
  if (timeRange === "week") {
    const d = new Date(now);
    d.setDate(d.getDate() - 7);
    return d;
  }
  if (timeRange === "month") {
    const d = new Date(now);
    d.setMonth(now.getMonth() - 1);
    return d;
  }
  return null;
};

// 功能：根据起始时间过滤列表（使用 published_at 优先，否则使用 created_at）。
// 使用位置：ContentDashboard -> 首屏与滚动加载后的客户端过滤。
export const filterByTime = <T extends { published_at?: string | null; created_at: string }>(rows: T[], startAt: Date | null) => {
  if (!startAt) return rows;
  return rows.filter((p) => new Date((p.published_at || p.created_at)) >= startAt);
};

// 功能：按发布时间（或创建时间）排序。
// 使用位置：ContentDashboard -> 排序按钮切换时重新排序。
export const sortByPublished = <T extends { published_at?: string | null; created_at: string }>(rows: T[], oldestFirst: boolean) => {
  return [...rows].sort((a, b) => {
    const ta = new Date((a.published_at || a.created_at)).getTime();
    const tb = new Date((b.published_at || b.created_at)).getTime();
    return oldestFirst ? ta - tb : tb - ta;
  });
};

export type AnalysisRow = { platform_item_id: string; risk_types?: any; sentiment?: string | null; brand_relevance?: string | null };

// 功能：把 gg_video_analysis 的行转换为便于消费的多个映射
// 使用位置：ContentDashboard -> 构建 risks/sentiments/relevance 三张映射表，支撑筛选与卡片标签。
export const buildAnalysisMaps = (rows: AnalysisRow[]) => {
  const risksMap: Record<string, string[]> = {};
  const sentimentsMap: Record<string, string> = {};
  const relevanceMap: Record<string, string> = {};
  const riskCountMap: Record<string, number> = {};
  const sentimentSet = new Set<string>();
  const relevanceSet = new Set<string>();

  rows.forEach((r) => {
    const raw = r.risk_types as any;
    const names: string[] = Array.isArray(raw)
      ? (raw as any[])
          .map((x) => (typeof x === "string" ? x : (x?.category || x?.scenario || "")))
          .filter(Boolean)
      : [];
    risksMap[r.platform_item_id] = names;
    names.forEach((n) => (riskCountMap[n] = (riskCountMap[n] || 0) + 1));
    if (r.sentiment) {
      sentimentsMap[r.platform_item_id] = String(r.sentiment);
      sentimentSet.add(String(r.sentiment));
    }
    if (r.brand_relevance) {
      const rel = String(r.brand_relevance);
      relevanceMap[r.platform_item_id] = rel;
      relevanceSet.add(rel);
    }
  });

  return { risksMap, sentimentsMap, relevanceMap, riskCountMap, sentimentSet, relevanceSet };
};

// 功能：根据风险计数字典生成 TopN 风险选项（供筛选器展示）
// 使用位置：ContentDashboard -> 作为 FilterBar 的 riskOptions 传入（可覆盖组件内部的全量风险枚举）
export const buildTopRiskOptions = (
  riskCountMap: Record<string, number>,
  limit: number = 8
) => {
  const top = Object.entries(riskCountMap)
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([k, v]) => ({ id: k, label: k, count: v }));
  const total = Object.values(riskCountMap).reduce((a, b) => a + b, 0);
  return [{ id: "all", label: "全部场景", count: total }, ...top];
};
