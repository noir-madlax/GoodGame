// Utilities for media URL normalization and fallbacks
// Use an inline SVG data URL as a safe, always-available placeholder to avoid 404s
const PLACEHOLDER_SVG = `<svg xmlns="http://www.w3.org/2000/svg" width="720" height="405" viewBox="0 0 720 405" role="img" aria-label="Placeholder image"><rect width="100%" height="100%" fill="#e5e7eb"/><g fill="#9ca3af" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif" font-size="20" text-anchor="middle"><text x="50%" y="50%" dy=".35em">No Image</text></g></svg>`;
const PLACEHOLDER_DATA_URL = `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(PLACEHOLDER_SVG)}`;

export const normalizeCoverUrl = (url: string | null | undefined): string => {
  if (!url) return PLACEHOLDER_DATA_URL;
  let u = url.trim();
  // XHS often returns HEIF/HEIC thumbnails which browsers can't display widely; force jpg
  // common patterns: imageView2/2/.../format/heif or imageMogr2/format/heif
  u = u.replace(/format\/(heif|heic)/gi, "format/jpg");
  // Remove any redImage/frame params that may break cross-origin processing after pipe
  // and keep the first segment before a pipe if present
  if (u.includes("|")) {
    u = u.split("|")[0];
  }
  // If url lacks a known format directive, append a safe query to request jpg
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


