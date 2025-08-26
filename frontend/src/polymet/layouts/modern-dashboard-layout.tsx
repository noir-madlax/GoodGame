import React from "react";
import ModernSidebar from "@/polymet/components/modern-sidebar";
import { cn } from "@/lib/utils";

interface ModernDashboardLayoutProps {
  children: React.ReactNode;
  className?: string;
}

export default function ModernDashboardLayout({
  children,
  className,
}: ModernDashboardLayoutProps) {
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
        <main className="flex-1 overflow-auto">
          <div className="p-8">{children}</div>
        </main>
      </div>
    </div>
  );
}
