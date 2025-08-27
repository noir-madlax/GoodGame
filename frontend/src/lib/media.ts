// Utilities for media URL normalization and fallbacks

export const normalizeCoverUrl = (url: string | null | undefined): string => {
  if (!url) return "/placeholder.jpg";
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
  if (el && el.src !== "/placeholder.jpg") {
    el.src = "/placeholder.jpg";
  }
};


