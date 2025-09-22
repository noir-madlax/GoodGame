/* eslint-disable @typescript-eslint/no-explicit-any */
/*
中文说明（重要）：
本文件提供“项目管理”相关的数据模型与 API（仅逻辑，不包含样式）。
被以下页面/组件使用：
- `polymet/components/project/project-management-panel.tsx`：项目列表/切换/删除
- `polymet/components/project/project-edit.tsx`：新建/编辑项目
- `polymet/components/modern-sidebar.tsx`：侧边栏标题展示当前项目名，并打开项目管理面板

数据库约定（来自需求）：
- 表 `project_settings`：记录项目名字与项目状态，status 取值："active" | "delete" | ""（正常）
  - 只允许一个 active；删除为软删除（置为 delete），列表中不展示。
- 表 `prompt_variables`：维护项目的具体信息：品牌、行业、别名。
  - 采用按键存储：key ∈ {"brand_name","sector","brand_aliases"}；
  - value 为文本；brand_aliases 使用 JSON 字符串存储字符串数组。

实现要点：
- 尽量最小改动满足当前两个页面的调用需求；
- 返回的 Project 模型整合自两张表，便于页面直接使用。
*/

import { supabase } from "@/lib/supabase";

export type Project = {
  id: string;
  project_name: string;
  brand_name: string;
  sector: string;
  brand_aliases: string[];
  created_at: string;
  is_current: boolean;
};

// project_settings 的活动项目配置
export type ProjectSettings = {
  id: string;
  project_name: string;
  status?: string | null;
  nav_overview_enabled: boolean;
  nav_mark_process_enabled: boolean;
  nav_search_settings_enabled: boolean;
  nav_analysis_rules_enabled: boolean;
  nav_alert_push_enabled: boolean;
};

export type ProjectFormData = {
  project_name?: string;
  brand_name: string;
  sector: string;
  brand_aliases: string[];
};

// 行业：餐饮细分（按需求截图）
export const SECTOR_OPTIONS = [
  { value: "火锅", label: "火锅" },
  { value: "轻食", label: "轻食" },
  { value: "咖啡", label: "咖啡" },
  { value: "烧烤", label: "烧烤" },
  { value: "快餐", label: "快餐" },
  { value: "中餐", label: "中餐" },
  { value: "西餐", label: "西餐" },
  { value: "日料", label: "日料" },
  { value: "韩料", label: "韩料" },
  { value: "甜品", label: "甜品" },
  { value: "奶茶", label: "奶茶" },
  { value: "酒店", label: "酒店" },
  { value: "零售", label: "零售" },
  { value: "其他", label: "其他" },
];

export const formatDateTime = (iso: string) => {
  if (!iso) return "";
  const d = new Date(iso);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${y}-${m}-${day} ${hh}:${mm}`;
};

const TABLE_PROJECT = "project_settings";
const TABLE_VARS = "prompt_variables";

type GetProjectsParams = {
  search?: string;
  sector?: string;
  page?: number;
  limit?: number;
};

// 读取变量集合并组装为 Map(project_id -> { brand_name, sector, brand_aliases })
type VarsSnapshot = { brand_name: string; sector: string; brand_aliases: string[] };
type VarRow = { project_id: string; variable_name: string; variable_value: string | null };
type ProjectRow = { id: string; status?: string | null; created_at: string };
type ProjectRowWithName = { id: string; status?: string | null; created_at: string; project_name?: string | null };

async function fetchProjectVariables(projectIds: string[]): Promise<Record<string, VarsSnapshot>> {
  if (projectIds.length === 0) return {};
  const sb = supabase as any;
  const { data, error } = await sb
    .from(TABLE_VARS)
    .select("project_id,variable_name,variable_value")
    .in("project_id", projectIds);
  if (error) throw error;
  const map: Record<string, VarsSnapshot> = {};
  (data as VarRow[] | null || []).forEach((row: VarRow) => {
    const pid = String(row.project_id);
    if (!map[pid]) map[pid] = { brand_name: "", sector: "", brand_aliases: [] };
    const key = String(row.variable_name);
    const val = row.variable_value as string | null;
    if (key === "brand_name") map[pid].brand_name = String(val || "");
    if (key === "sector") map[pid].sector = String(val || "");
    if (key === "brand_aliases") {
      try {
        map[pid].brand_aliases = val ? (JSON.parse(val) as string[]) : [];
      } catch {
        map[pid].brand_aliases = [];
      }
    }
  });
  return map;
}

// 写入/更新变量（幂等 upsert）
async function upsertVariables(projectId: string, form: ProjectFormData) {
  const sb = supabase as any;
  // 先删除旧值再插入，避免 upsert 依赖复合唯一键
  await sb
    .from(TABLE_VARS)
    .delete()
    .eq("project_id", projectId)
    .in("variable_name", ["brand_name", "sector", "brand_aliases"]);
  const rows = [
    { project_id: projectId, variable_name: "brand_name", variable_value: form.brand_name },
    { project_id: projectId, variable_name: "sector", variable_value: form.sector },
    { project_id: projectId, variable_name: "brand_aliases", variable_value: JSON.stringify(form.brand_aliases || []) },
  ];
  const { error } = await sb.from(TABLE_VARS).insert(rows);
  if (error) throw error;
}

// 校验品牌名唯一（针对未删除的项目）
export const validateBrandNameUnique = async (brandName: string, excludeProjectId?: string) => {
  const sb = supabase as any;
  const { data, error } = await sb
    .from(TABLE_VARS)
    .select("project_id, variable_name, variable_value")
    .eq("variable_name", "brand_name")
    .eq("variable_value", brandName)
    .limit(1000);
  if (error) return true; // 容错：出错时不阻塞
  const candidates = (data as { project_id: string; value: string }[] | null) || [];
  if (candidates.length === 0) return true;
  const pids = candidates.map((r) => r.project_id);
  const { data: ps } = await sb
    .from(TABLE_PROJECT)
    .select("id,status")
    .in("id", pids)
    .neq("status", "delete");
  const exists = ((ps as ProjectRow[] | null) || []).some((p: ProjectRow) => p.id !== excludeProjectId);
  return !exists;
};

export const projectAPI = {
  // 分页列表（过滤 soft delete）
  async getProjects(params: GetProjectsParams) {
    if (!supabase) return { projects: [], total: 0 };
    const page = Math.max(1, params.page || 1);
    const limit = Math.max(1, params.limit || 10);
    const from = (page - 1) * limit;
    const to = from + limit - 1;

    // 只加载未删除项目
    const sb = supabase as any;
    const { data: projRows, error, count } = await sb
      .from(TABLE_PROJECT)
      .select("id, status, created_at, project_name", { count: "exact" })
      .neq("status", "delete")
      .order("created_at", { ascending: false })
      .range(from, to);
    if (error) return { projects: [], total: 0 };
    const ids = ((projRows as ProjectRowWithName[] | null) || []).map((r: ProjectRowWithName) => String(r.id));
    const varMap = await fetchProjectVariables(ids);

    // 引号清洗逻辑已由数据库数据修正，前端不再处理；保留稳妥的 trim 即可
    const stripQuotes = (s: string) => String(s || "").trim();

    let projects: Project[] = ((projRows as ProjectRowWithName[] | null) || []).map((r: ProjectRowWithName) => {
      const v = varMap[r.id] || { brand_name: "", sector: "", brand_aliases: [] as string[] };
      const brand = stripQuotes(v.brand_name || "");
      const sector = stripQuotes(v.sector || "");
      const aliases = (v.brand_aliases || []).map((x) => stripQuotes(String(x)));
      return {
        id: String(r.id),
        project_name: stripQuotes(r.project_name || ""),
        brand_name: brand,
        sector,
        brand_aliases: aliases,
        created_at: r.created_at,
        is_current: String(r.status || "") === "active",
      } as Project;
    });

    // 过滤条件：搜索/行业
    if (params.search) {
      const s = params.search.trim();
      projects = projects.filter((p) => p.brand_name.includes(s));
    }
    if (params.sector) {
      projects = projects.filter((p) => p.sector === params.sector);
    }

    // active 排前
    projects = projects.sort((a, b) => (a.is_current === b.is_current ? 0 : a.is_current ? -1 : 1));
    return { projects, total: count || projects.length };
  },

  // 读取当前 active 项目（供侧边栏标题展示）
  async getCurrentProject(): Promise<Project | null> {
    if (!supabase) return null;
    const sb = supabase as any;
    const { data, error } = await sb
      .from(TABLE_PROJECT)
      .select("id, status, created_at, project_name")
      .eq("status", "active")
      .limit(1)
      .maybeSingle();
    if (error) return null;
    if (!data) return null;
    const varMap = await fetchProjectVariables([data.id]);
    const v = varMap[data.id] || { brand_name: "", sector: "", brand_aliases: [] as string[] };
    const stripQuotes = (s: string) => String(s || "").trim();
    return {
      id: String(data.id),
      project_name: stripQuotes(data.project_name || ""),
      brand_name: stripQuotes(v.brand_name || data.project_name || ""),
      sector: stripQuotes(v.sector || ""),
      brand_aliases: (v.brand_aliases || []).map((x) => stripQuotes(String(x))),
      created_at: data.created_at,
      is_current: true,
    };
  },

  // 读取当前 active 的 project_settings
  async getActiveSettings(): Promise<ProjectSettings | null> {
    if (!supabase) return null;
    const sb = supabase as any;
    const { data } = await sb
      .from(TABLE_PROJECT)
      .select(
        "id, project_name, status, nav_overview_enabled, nav_mark_process_enabled, nav_search_settings_enabled, nav_analysis_rules_enabled, nav_alert_push_enabled"
      )
      .eq("status", "active")
      .limit(1)
      .maybeSingle();
    if (!data) return null;
    return {
      id: String(data.id),
      project_name: String(data.project_name || ""),
      status: data.status,
      nav_overview_enabled: Boolean(data.nav_overview_enabled),
      nav_mark_process_enabled: Boolean(data.nav_mark_process_enabled),
      nav_search_settings_enabled: Boolean(data.nav_search_settings_enabled),
      nav_analysis_rules_enabled: Boolean(data.nav_analysis_rules_enabled),
      nav_alert_push_enabled: Boolean(data.nav_alert_push_enabled),
    } as ProjectSettings;
  },

  async createProject(form: ProjectFormData): Promise<Project> {
    if (!supabase) throw new Error("Supabase 未初始化");
    const stripQuotes = (s: string) => String(s || "").trim();
    const clean: ProjectFormData = {
      project_name: stripQuotes(form.project_name || ""),
      brand_name: stripQuotes(form.brand_name),
      sector: stripQuotes(form.sector),
      brand_aliases: (form.brand_aliases || []).map((x) => stripQuotes(String(x))),
    };
    const sb = supabase as any;
    const { data, error } = await sb
      .from(TABLE_PROJECT)
      .insert({
        status: "",
        project_name: clean.project_name,
        nav_overview_enabled: false,
        nav_mark_process_enabled: true,
        nav_search_settings_enabled: true,
        nav_analysis_rules_enabled: false,
        nav_alert_push_enabled: false,
      })
      .select("id, status, created_at, project_name")
      .single();
    if (error) throw error;
    await upsertVariables(data.id, clean);
    return {
      id: String(data.id),
      project_name: stripQuotes(data.project_name || ""),
      brand_name: clean.brand_name,
      sector: clean.sector,
      brand_aliases: clean.brand_aliases || [],
      created_at: data.created_at,
      is_current: String(data.status || "") === "active",
    };
  },

  async updateProject(projectId: string, form: ProjectFormData): Promise<Project> {
    if (!supabase) throw new Error("Supabase 未初始化");
    const stripQuotes = (s: string) => String(s || "").trim();
    const clean: ProjectFormData = {
      brand_name: stripQuotes(form.brand_name),
      sector: stripQuotes(form.sector),
      brand_aliases: (form.brand_aliases || []).map((x) => stripQuotes(String(x))),
    };
    await upsertVariables(projectId, clean);
    const sb = supabase as any;
    const { data } = await sb
      .from(TABLE_PROJECT)
      .select("id, status, created_at, project_name")
      .eq("id", projectId)
      .single();
    return {
      id: String(projectId),
      project_name: stripQuotes(data?.project_name || ""),
      brand_name: clean.brand_name,
      sector: clean.sector,
      brand_aliases: clean.brand_aliases || [],
      created_at: data?.created_at || new Date().toISOString(),
      is_current: String(data?.status || "") === "active",
    };
  },

  async softDeleteProject(projectId: string) {
    if (!supabase) return;
    // 若删除当前 active 项，先清空 active 状态
    const sb = supabase as any;
    await sb.from(TABLE_PROJECT).update({ status: "" }).eq("id", projectId).eq("status", "active");
    const { error } = await sb.from(TABLE_PROJECT).update({ status: "delete" }).eq("id", projectId);
    if (error) throw error;
  },

  async switchProject(projectId: string) {
    if (!supabase) return;
    // 仅允许一个 active
    const sb = supabase as any;
    await sb.from(TABLE_PROJECT).update({ status: "" }).neq("id", projectId).eq("status", "active");
    const { error } = await sb.from(TABLE_PROJECT).update({ status: "active" }).eq("id", projectId);
    if (error) throw error;
  },
};


