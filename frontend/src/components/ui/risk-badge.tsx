import React from "react";
import { AlertTriangle, Shield } from "lucide-react";
import { cn } from "@/lib/utils";

type RiskSeverity = "low" | "medium" | "high";
type RiskBadgeSize = "sm" | "md" | "lg";

interface RiskBadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  label: string;
  severity?: RiskSeverity;
  size?: RiskBadgeSize;
  withIcon?: boolean;
}

const getSeverityClasses = (severity: RiskSeverity) => {
  if (severity === "high") {
    return "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 border border-red-200 dark:border-red-800";
  }
  if (severity === "low") {
    return "bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400 border border-yellow-200 dark:border-yellow-800";
  }
  return "bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400 border border-orange-200 dark:border-orange-800";
};

const getSizeClasses = (size: RiskBadgeSize) => {
  switch (size) {
    case "lg":
      return { container: "px-3 py-1.5 text-sm", icon: "w-4 h-4" };
    case "md":
      return { container: "px-2.5 py-1 text-xs", icon: "w-3.5 h-3.5" };
    default:
      return { container: "px-2 py-0.5 text-xs", icon: "w-3 h-3" };
  }
};

const RiskBadge: React.FC<RiskBadgeProps> = ({
  label,
  severity = "medium",
  size = "md",
  withIcon = true,
  className,
  ...props
}) => {
  const sizeClasses = getSizeClasses(size);
  const severityClasses = getSeverityClasses(severity);
  const Icon = severity === "high" ? AlertTriangle : Shield;

  return (
    <div
      role="status"
      aria-label={label}
      tabIndex={0}
      className={cn(
        "inline-flex items-center rounded-full font-medium select-none gap-1 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
        sizeClasses.container,
        severityClasses,
        className
      )}
      {...props}
    >
      {withIcon && <Icon className={sizeClasses.icon} aria-hidden />}
      <span>{label}</span>
    </div>
  );
};

export { RiskBadge };


