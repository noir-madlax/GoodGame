import React from "react";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

export interface AuthorTooltipData {
  authorName: string;
  followerCount?: number | null;
  avatarUrl?: string | null;
  shareUrl?: string | null;
  signature?: string | null;
  location?: string | null;
  accountCertInfo?: string | null;
  verificationType?: number | null;
  nickname?: string | null;
  isInfluencer?: boolean | null;
}

export interface AuthorTooltipProps {
  data: AuthorTooltipData;
  className?: string;
  children: React.ReactNode; // 触发器
}

const formatFollowersCn = (num?: number | null): string => {
  const n = Number(num || 0);
  if (!Number.isFinite(n) || n <= 0) return "0";
  if (n >= 10000) {
    const w = Math.round((n / 10000) * 10) / 10; // 1 位小数
    return `${w}万`;
  }
  return n.toLocaleString();
};

const parseCertLabel = (accountCertInfo?: string | null, verificationType?: number | null): string | null => {
  // account_cert_info 可能是 JSON 字符串，形如 {"label_text":"已认证"}
  try {
    if (accountCertInfo && typeof accountCertInfo === "string") {
      const obj = JSON.parse(accountCertInfo);
      const label = obj?.label_text || obj?.label || null;
      if (label) return String(label);
    }
  } catch (_) {
    // ignore parse error
  }
  if (verificationType && verificationType > 0) return "已认证";
  return null;
};

export default function AuthorTooltip({ data, className, children }: AuthorTooltipProps) {
  const {
    authorName,
    followerCount,
    avatarUrl,
    shareUrl,
    signature,
    location,
    accountCertInfo,
    verificationType,
    nickname,
  } = data || {};

  const displayName = (nickname || authorName || "作者").toString();
  const certText = parseCertLabel(accountCertInfo, verificationType);

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <span className={cn("inline-flex items-center gap-1", className)} tabIndex={0} aria-label="作者信息">
            {children}
          </span>
        </TooltipTrigger>
        <TooltipContent className="w-80 p-0 bg-transparent rounded-2xl shadow-none ring-0 text-inherit">
          <div className="p-3 rounded-2xl bg-white/95 dark:bg-gray-900/95 backdrop-blur-xl border border-white/20 shadow-2xl">
            <div className="flex items-start gap-3">
              {avatarUrl ? (
                <img src={String(avatarUrl)} alt="avatar" className="w-10 h-10 rounded-full object-cover" />
              ) : (
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 text-white flex items-center justify-center text-sm">{displayName.slice(0,1)}</div>
              )}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  {data?.isInfluencer ? <img src="/v-badge.svg" alt="达人" className="w-4 h-4" aria-hidden /> : null}
                  <span className="font-semibold text-gray-900 dark:text-white truncate">{displayName}</span>
                  {certText ? (
                    <span className="px-1.5 py-0.5 rounded-md bg-blue-500/10 text-blue-600 dark:text-blue-400 text-[10px] border border-blue-500/20">{certText}</span>
                  ) : null}
                </div>
                <div className="mt-1 text-xs text-gray-600 dark:text-gray-300 inline-flex items-center gap-1">
                  <img src="/follower.svg" alt="粉丝" className="w-3.5 h-3.5" aria-hidden />
                  <span>{formatFollowersCn(followerCount)} </span>
                </div>
              </div>
            </div>
            {(signature || location) && (
              <div className="mt-2 space-y-1 text-xs text-gray-700 dark:text-gray-300">
                {signature ? <p className="whitespace-pre-wrap leading-relaxed">{signature}</p> : null}
                {location ? <div className="text-gray-500">地区：{location}</div> : null}
              </div>
            )}
            {shareUrl && (
              <div className="mt-2">
                <button
                  className="px-2 py-1 rounded-md text-xs text-blue-600 dark:text-blue-400 hover:underline bg-transparent"
                  onClick={(e) => { e.stopPropagation(); window.open(String(shareUrl), "_blank"); }}
                >
                  访问主页
                </button>
              </div>
            )}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

export { formatFollowersCn };


