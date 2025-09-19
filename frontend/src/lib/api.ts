// 中文说明：
// 功能：集中管理后端 API 基地址，供全站请求复用。
// 使用位置：导入链接分析弹窗等发起后端请求的场景。

/**
 * 读取并规范化后端 API 基地址。
 * - 来源：环境变量 `NEXT_PUBLIC_API_URL`（必须带协议，如 http://34.217.176.84:8000）。
 * - 处理：移除结尾的斜杠，保证后续拼接路径不重复斜杠。
 */
export const getApiBase = (): string => {
  const raw = (process.env.NEXT_PUBLIC_API_URL || "").trim();
  if (!raw) return "";
  return raw.endsWith("/") ? raw.slice(0, -1) : raw;
};

/**
 * 拼接完整请求地址。
 * @param path 形如 "/api/..." 的路径
 */
export const buildApiUrl = (path: string): string => {
  const base = getApiBase();
  if (!base) return path;
  return `${base}${path.startsWith("/") ? path : `/${path}`}`;
};


