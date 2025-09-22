import React, { useEffect, useRef } from "react";
import ModernSidebar from "@/polymet/components/modern-sidebar";
import { cn } from "@/lib/utils";
import { useLocation } from "react-router-dom";
import { ProjectProvider, useProject } from "@/polymet/lib/project-context";

interface ModernDashboardLayoutProps {
  children: React.ReactNode;
  className?: string;
}

function LayoutInner({
  children,
  className,
}: ModernDashboardLayoutProps) {
  // 中文说明：
  // 1) 该布局的 <main> 是整个应用的滚动容器（overflow-auto）。
  // 2) 使用 HashRouter 切换路由时布局不会卸载，导致滚动位置被继承。
  // 3) 方案B：进入详情/建议页强制置顶；返回列表页恢复之前的滚动位置。
  const location = useLocation();
  const mainRef = useRef<HTMLDivElement | null>(null);
  // 路由 -> 滚动位置 的缓存（仅存我们关心的页面，如 /dashboard）
  const scrollStoreRef = useRef<Map<string, number>>(new Map());
  // 记录上一个路径，用于在路径变化时保存旧页滚动位置
  const prevPathRef = useRef<string>(location.pathname);

  useEffect(() => {
    const mainEl = mainRef.current;
    if (!mainEl) {
      prevPathRef.current = location.pathname;
      return;
    }

    const prevPath = prevPathRef.current;
    const nextPath = location.pathname;

    // 在切换到新路径后，先保存旧路径（如 /dashboard）的滚动位置
    if (prevPath) {
      // 仅保存我们需要恢复的位置：列表页 /dashboard
      if (prevPath === "/dashboard") {
        scrollStoreRef.current.set(prevPath, mainEl.scrollTop);
      }
    }

    // 决定新页面的滚动定位
    const isDetail = /^\/detail\//.test(nextPath);
    const isSuggestion = /^\/suggestions\//.test(nextPath);
    const isDashboard = nextPath === "/dashboard";

    if (isDetail || isSuggestion) {
      // 进入详情/建议页：强制置顶
      mainEl.scrollTo({ top: 0, left: 0, behavior: "auto" });
    } else if (isDashboard) {
      // 返回列表页：恢复之前缓存的滚动位置（若没有则保持默认）
      const saved = scrollStoreRef.current.get("/dashboard");
      if (typeof saved === "number" && saved >= 0) {
        mainEl.scrollTo({ top: saved, left: 0, behavior: "auto" });
      }
    }

    // 更新 prevPath 供下一次切换使用
    prevPathRef.current = nextPath;
  }, [location.pathname]);
  return (
    <div
      className={cn(
        "min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50",
        "dark:from-gray-900 dark:via-blue-900 dark:to-purple-900",
        "relative overflow-hidden",
        className
      )}
    >
      {/* Background Pattern */}
      <div className="absolute inset-0 opacity-30">
        <div className="absolute top-0 left-0 w-72 h-72 bg-blue-400/20 rounded-full mix-blend-multiply filter blur-xl animate-pulse" />

        <div className="absolute top-0 right-0 w-72 h-72 bg-purple-400/20 rounded-full mix-blend-multiply filter blur-xl animate-pulse animation-delay-2000" />

        <div className="absolute bottom-0 left-1/2 w-72 h-72 bg-pink-400/20 rounded-full mix-blend-multiply filter blur-xl animate-pulse animation-delay-4000" />
      </div>

      <div className="relative flex h-screen">
        {/* Sidebar */}
        <ModernSidebar />

        {/* Main Content */}
        <main ref={mainRef} className="flex-1 overflow-auto">
          <div className="p-8">{children}</div>
        </main>
      </div>
    </div>
  );
}

export default function ModernDashboardLayout({ children, className }: ModernDashboardLayoutProps) {
  return (
    <ProjectProvider>
      <LayoutInner className={className}>{children}</LayoutInner>
    </ProjectProvider>
  );
}
