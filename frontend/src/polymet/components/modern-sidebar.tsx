import React from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { BarChart3, Settings, TrendingUp, Filter, Search, BellRing, Bookmark } from "lucide-react";
import { cn } from "@/lib/utils";

interface SidebarItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  active?: boolean;
  count?: number;
  disabled?: boolean;
}

interface ModernSidebarProps {
  className?: string;
}

export default function ModernSidebar({ className }: ModernSidebarProps) {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const menuItems: SidebarItem[] = [
    {
      id: "content",
      label: "全网舆情监控",
      icon: <BarChart3 className="w-5 h-5" />,
    },
    {
      id: "marks",
      label: "标记内容与处理",
      icon: <Bookmark className="w-5 h-5" />,
    },
    {
      id: "search-filter",
      label: "内容检索与过滤设置",
      icon: <Search className="w-5 h-5" />,
      disabled: true,
    },
    {
      id: "rules-settings",
      label: "舆情分析规则配置",
      icon: <Settings className="w-5 h-5" />,
      disabled: true,
    },
    {
      id: "alerts-push",
      label: "告警与推送配置",
      icon: <BellRing className="w-5 h-5" />,
      disabled: true,
    },
  ];

  return (
    <div
      className={cn(
        "w-64 h-full bg-white/10 backdrop-blur-xl border-r border-white/20",
        "shadow-2xl shadow-black/10",
        className
      )}
    >
      {/* Header */}
      <div className="p-6 border-b border-white/10">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-green-500 to-teal-600 flex items-center justify-center shadow-lg">
            <TrendingUp className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-gray-900 dark:text-white">
              海底捞舆情分析
            </h1>
        
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="p-4 space-y-2">
        {menuItems.map((item) => {
          const active =
            (item.id === "content" && (pathname.startsWith("/dashboard") || pathname === "/" || pathname.startsWith("/detail"))) ||
            (item.id === "marks" && (pathname.startsWith("/marks") || pathname.startsWith("/suggestions")));
          return (
          <button
            key={item.id}
            type="button"
            className={cn(
              "w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-300",
              !item.disabled && "hover:bg-white/10 hover:backdrop-blur-sm hover:shadow-lg",
              active
                ? "bg-gradient-to-r from-blue-500/20 to-purple-600/20 backdrop-blur-sm border border-white/20 shadow-lg"
                : !item.disabled && "hover:border hover:border-white/10",
              item.disabled && "opacity-50 cursor-not-allowed"
            )}
            disabled={item.disabled}
            aria-disabled={item.disabled}
            onClick={() => {
              if (item.disabled) return;
              if (item.id === "content") navigate("/dashboard");
              if (item.id === "marks") navigate("/marks");
            }}
          >
            <div
              className={cn(
                "flex items-center justify-center",
                active
                  ? "text-blue-600 dark:text-blue-400"
                  : "text-gray-600 dark:text-gray-400"
              )}
            >
              {item.icon}
            </div>
            <span
              className={cn(
                "font-medium",
                active
                  ? "text-blue-600 dark:text-blue-400"
                  : "text-gray-700 dark:text-gray-300"
              )}
            >
              {item.label}
            </span>
            {item.count && (
              <span className="ml-auto px-2 py-1 rounded-full bg-blue-500 text-white text-xs font-medium">
                {item.count}
              </span>
            )}
          </button>
          );
        })}
      </nav>

      {/* Bottom Section 这个先隐藏，hidden注释掉*/}
      <div className="hidden absolute bottom-0 left-0 right-0 p-4">
        <div className="p-4 rounded-xl bg-gradient-to-br from-blue-500/10 to-purple-600/10 backdrop-blur-sm border border-white/20">
          <div className="flex items-center space-x-3 mb-2">
            <Filter className="w-4 h-4 text-blue-600 dark:text-blue-400" />

            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              快速筛选
            </span>
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
            使用智能筛选快速找到相关内容
          </p>
        </div>
      </div>
    </div>
  );
}
