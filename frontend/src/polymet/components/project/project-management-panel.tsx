import React, { useState, useEffect } from "react";
import { Plus, Edit, Trash2, Building2 } from "lucide-react";
import { projectAPI, formatDateTime } from "@/polymet/data/project-data";
import type { Project } from "@/polymet/data/project-data";

interface ProjectManagementModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreateProject?: () => void;
  onEditProject?: (project: Project) => void;
  onDeleteProject?: (project: Project) => void;
  onSwitchProject?: (project: Project) => void;
  className?: string;
}

export default function ProjectManagementModal({
  isOpen,
  onClose,
  onCreateProject,
  onEditProject,
  onDeleteProject,
  onSwitchProject,
  className = "",
}: ProjectManagementModalProps) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10; // 仅用于内部分页（简单实现）

  // 加载项目列表
  const loadProjects = async (page = 1) => {
    setLoading(true);
    try {
      const response = await projectAPI.getProjects({ page, limit: pageSize });
      setProjects(response.projects);
      setCurrentPage(page);
    } catch (error) {
      console.error("加载项目列表失败:", error);
    } finally {
      setLoading(false);
    }
  };

  // 初始加载和搜索变化时重新加载
  useEffect(() => {
    if (isOpen) {
      loadProjects(1);
    }
  }, [isOpen]);

  // 监听编辑弹窗成功后的刷新事件
  useEffect(() => {
    const handler = () => loadProjects(currentPage);
    window.addEventListener("project:list:reload", handler);
    return () => window.removeEventListener("project:list:reload", handler);
  }, [currentPage]);

  // 简化：当前版本不包含搜索/筛选/批量选择 UI

  // 处理项目切换
  const handleSwitchProject = async (project: Project) => {
    try {
      await projectAPI.switchProject(project.id);
      onSwitchProject?.(project);
      // 重新加载列表以更新当前项目状态
      loadProjects(currentPage);
    } catch (error) {
      console.error("切换项目失败:", error);
    }
  };

  // 处理删除（软删除）
  const handleDeleteProject = async (project: Project) => {
    const confirmed = window.confirm(`确定删除项目“${project.brand_name}”？此操作可恢复（软删除）。`);
    if (!confirmed) return;
    try {
      await projectAPI.softDeleteProject(project.id);
      onDeleteProject?.(project);
      // 删除后刷新
      const nextPage = projects.length === 1 && currentPage > 1 ? currentPage - 1 : currentPage;
      await loadProjects(nextPage);
    } catch (error) {
      console.error("删除项目失败:", error);
    }
  };

  // 无筛选清理逻辑

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div
        className={`w-full max-w-6xl max-h-[90vh] bg-white dark:bg-gray-900 rounded-2xl shadow-2xl overflow-hidden ${className}`}
      >
        {/* 头部 */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-3">
            <div>
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                项目管理
              </h2>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={onCreateProject}
              className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white rounded-lg transition-all duration-200 shadow-lg hover:shadow-xl"
            >
              <Plus className="w-4 h-4" />

              <span>新建项目</span>
            </button>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg transition-colors"
            >
              <span>关闭</span>
            </button>
          </div>
        </div>

        {/* 项目列表 */}
        <div className="flex-1 overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                <p className="text-gray-500 dark:text-gray-400">加载中...</p>
              </div>
            </div>
          ) : projects.length === 0 ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <Building2 className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />

                <p className="text-gray-500 dark:text-gray-400 mb-2">暂无项目</p>
                <button
                  onClick={onCreateProject}
                  className="text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 text-sm"
                >
                  创建第一个项目
                </button>
              </div>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 dark:bg-gray-800">
                  <tr>
                    <th className="text-left px-6 py-4 font-semibold text-gray-700 dark:text-gray-300">
                      项目名称
                    </th>
                    <th className="text-left px-6 py-4 font-semibold text-gray-700 dark:text-gray-300">
                      品牌名
                    </th>
                    <th className="text-left px-6 py-4 font-semibold text-gray-700 dark:text-gray-300">
                      行业
                    </th>
                    <th className="text-left px-6 py-4 font-semibold text-gray-700 dark:text-gray-300">
                      别名
                    </th>
                    <th className="text-left px-6 py-4 font-semibold text-gray-700 dark:text-gray-300">
                      创建时间
                    </th>
                    <th className="text-right px-6 py-4 font-semibold text-gray-700 dark:text-gray-300">
                      操作
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {projects.map((project) => (
                    <tr
                      key={project.id}
                      className="group border-t border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                    >
                      <td className="px-6 py-4">
                        <div className="flex items-center space-x-3">
                          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center flex-shrink-0">
                            <span className="text-sm font-semibold text-white">
                              {project.brand_name.charAt(0)}
                            </span>
                          </div>
                          <div className="min-w-0">
                            <div className="flex items-center space-x-2">
                              <span className="font-medium text-gray-900 dark:text-white truncate">
                                {project.project_name || `${project.brand_name}舆情分析`}
                              </span>
                              {project.is_current && (
                                <span className="px-2 py-1 text-xs bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 rounded-full flex-shrink-0">
                                  当前
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className="font-medium text-gray-900 dark:text-white">
                          {project.brand_name}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="px-2 py-1 text-xs bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 rounded-full">
                          {project.sector}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-gray-600 dark:text-gray-400">
                          {project.brand_aliases.length} 个
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                        {formatDateTime(project.created_at)}
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center justify-end space-x-2">
                          <button
                            onClick={() => handleSwitchProject(project)}
                            disabled={project.is_current}
                            className={`px-3 py-1 text-sm rounded-lg transition-colors ${
                              project.is_current
                                ? "opacity-0 pointer-events-none"
                                : "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-200 hover:bg-blue-200 dark:hover:bg-blue-800"
                            }`}
                            title="切换到此项目"
                          >
                            切换
                          </button>
                          <button
                            onClick={() => onEditProject?.(project)}
                            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                            title="编辑"
                          >
                            <Edit className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                          </button>
                          <button
                            onClick={() => handleDeleteProject(project)}
                            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                            title="删除"
                          >
                            <Trash2 className="w-4 h-4 text-red-500 dark:text-red-400" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
