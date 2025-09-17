// Utilities for media URL normalization and fallbacks
// Use an inline SVG data URL as a safe, always-available placeholder to avoid 404s
const PLACEHOLDER_SVG = `<svg xmlns="http://www.w3.org/2000/svg" width="720" height="405" viewBox="0 0 720 405" role="img" aria-label="Placeholder image"><rect width="100%" height="100%" fill="#e5e7eb"/><g fill="#9ca3af" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif" font-size="20" text-anchor="middle"><text x="50%" y="50%" dy=".35em">No Image</text></g></svg>`;
const PLACEHOLDER_DATA_URL = `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(PLACEHOLDER_SVG)}`;

export const normalizeCoverUrl = (url: string | null | undefined): string => {
  if (!url) return PLACEHOLDER_DATA_URL;
  let u = url.trim();

  // 针对小红书 xhscdn：
  // 1) 统一升级为 https
  // 2) 不截断管道参数（| 后参数保留）
  // 3) 仅在 xhscdn 链接上，将 heif/heic 原位替换为 jpg，避免不可显示
  const isXhsCdn = /(^|\.)xhscdn\.com\//i.test(u);
  if (isXhsCdn) {
    u = u.replace(/^http:\/\//i, "https://");
    u = u.replace(/format\/(heif|heic)/gi, "format/jpg");
    return u;
  }

  // 其他域：保持原有保守处理
  u = u.replace(/format\/(heif|heic)/gi, "format/jpg");
  if (u.includes("|")) {
    u = u.split("|")[0];
  }
  const hasFormat = /format\/(jpg|jpeg|png|webp)/i.test(u);
  if (!hasFormat) {
    const joiner = u.includes("?") ? "&" : "?";
    u = `${u}${joiner}imageView2/2/w/720/format/jpg`;
  }
  return u;
};

export const onImageErrorSetPlaceholder = (
  e: React.SyntheticEvent<HTMLImageElement, Event>,
) => {
  const el = e.currentTarget;
  if (el && el.src !== PLACEHOLDER_DATA_URL) {
    el.src = PLACEHOLDER_DATA_URL;
  }
};


