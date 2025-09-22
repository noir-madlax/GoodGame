import React, { createContext, useContext, useEffect, useState } from "react";
import { projectAPI, type ProjectSettings } from "@/polymet/data/project-data";

// 全局项目上下文：保存当前项目ID与导航可见性设置
export type ProjectContextState = {
  activeProjectId: string | null;
  settings: ProjectSettings | null;
  refresh: () => Promise<void>;
};

const ProjectContext = createContext<ProjectContextState | undefined>(undefined);

export const useProject = () => {
  const ctx = useContext(ProjectContext);
  if (!ctx) throw new Error("useProject 必须在 ProjectProvider 内使用");
  return ctx;
};

export const ProjectProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [settings, setSettings] = useState<ProjectSettings | null>(null);

  const refresh = async () => {
    const s = await projectAPI.getActiveSettings();
    setSettings(s);
  };

  useEffect(() => {
    refresh();
  }, []);

  return (
    <ProjectContext.Provider
      value={{ activeProjectId: settings?.id || null, settings, refresh }}
    >
      {children}
    </ProjectContext.Provider>
  );
};
