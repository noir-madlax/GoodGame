import React, { useState, useEffect, useRef } from "react";
import { Save, Loader2, AlertCircle, Plus, Trash2, Tag, Sparkles } from "lucide-react";
import {
  projectAPI,
  validateBrandNameUnique,
  SECTOR_OPTIONS,
} from "@/polymet/data/project-data";
import type { Project, ProjectFormData } from "@/polymet/data/project-data";

interface ProjectFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  project?: Project | null; // null表示新建，有值表示编辑
  onSuccess?: (project: Project, isNew: boolean) => void;
  className?: string;
}

interface FormErrors {
  project_name?: string;
  brand_name?: string;
  sector?: string;
  brand_aliases?: string;
}

export default function ProjectFormModal({
  isOpen,
  onClose,
  project,
  onSuccess,
  className = "",
}: ProjectFormModalProps) {
  const [formData, setFormData] = useState<ProjectFormData & { project_name: string }>({
    project_name: "",
    brand_name: "",
    sector: "",
    brand_aliases: [],
  });
  const [errors, setErrors] = useState<FormErrors>({});
  const [loading, setLoading] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [aliasInput, setAliasInput] = useState("");
  const [setAsCurrentProject, setSetAsCurrentProject] = useState(false);
  // 备注：AI 引导占位，当前版本未启用

  const brandNameInputRef = useRef<HTMLInputElement>(null);
  const aliasInputRef = useRef<HTMLInputElement>(null);

  const isEditing = !!project;
  const modalTitle = isEditing ? "编辑项目" : "新建项目";

  // 初始化表单数据
  useEffect(() => {
    if (isOpen) {
      if (project) {
        setFormData({
          project_name: project.project_name || "",
          brand_name: project.brand_name,
          sector: project.sector,
          brand_aliases: [...project.brand_aliases],
        });
        setSetAsCurrentProject(false);
      } else {
        setFormData({
          project_name: "",
          brand_name: "",
          sector: "",
          brand_aliases: [],
        });
        setSetAsCurrentProject(true); // 新建项目默认设为当前项目
      }
      setErrors({});
      setHasChanges(false);
      setAliasInput("");

      // 聚焦到品牌名输入框
      setTimeout(() => {
        brandNameInputRef.current?.focus();
      }, 100);
    }
  }, [isOpen, project]);

  // 监听表单变化
  useEffect(() => {
    if (project) {
      const hasChanged =
        formData.brand_name !== project.brand_name ||
        formData.sector !== project.sector ||
        JSON.stringify(formData.brand_aliases) !==
          JSON.stringify(project.brand_aliases);
      setHasChanges(hasChanged);
    } else {
      setHasChanges(
        formData.brand_name.trim() !== "" ||
          formData.sector !== "" ||
          formData.brand_aliases.length > 0
      );
    }
  }, [formData, project]);

  // 键盘事件处理
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      if (e.key === "Escape") {
        handleClose();
      } else if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
        handleSubmit();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, hasChanges]);

  // 验证表单
  const validateForm = async (): Promise<boolean> => {
    const newErrors: FormErrors = {};

    // 品牌名验证
    if (!formData.project_name || !formData.project_name.trim()) {
      newErrors.project_name = "项目名称不能为空";
    }
    // 品牌名验证
    if (!formData.brand_name.trim()) {
      newErrors.brand_name = "品牌名称不能为空";
    } else if (formData.brand_name.trim().length < 2) {
      newErrors.brand_name = "品牌名称至少需要2个字符";
    } else if (formData.brand_name.trim().length > 50) {
      newErrors.brand_name = "品牌名称不能超过50个字符";
    } else if (
      !(await validateBrandNameUnique(formData.brand_name.trim(), project?.id))
    ) {
      newErrors.brand_name = "品牌名称已存在";
    }

    // 行业验证
    if (!formData.sector) {
      newErrors.sector = "请选择行业";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // 处理输入变化
  const handleInputChange = (
    field: keyof ProjectFormData,
    value: ProjectFormData[keyof ProjectFormData]
  ) => {
    setFormData((prev) => ({ ...prev, [field]: value }));

    // 清除对应字段的错误
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: undefined }));
    }
  };

  // 添加别名
  const handleAddAlias = () => {
    const alias = aliasInput.trim();
    if (alias && !formData.brand_aliases.includes(alias)) {
      handleInputChange("brand_aliases", [...formData.brand_aliases, alias]);
      setAliasInput("");
    }
  };

  // 删除别名
  const handleRemoveAlias = (index: number) => {
    const newAliases = formData.brand_aliases.filter((_, i) => i !== index);
    handleInputChange("brand_aliases", newAliases);
  };

  // 处理别名输入框回车
  const handleAliasKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAddAlias();
    }
  };

  // 批量粘贴别名
  const handleAliasPaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const pastedText = e.clipboardData.getData("text");
    const aliases = pastedText
      .split(/[,，\n\t]/)
      .map((alias) => alias.trim())
      .filter((alias) => alias && !formData.brand_aliases.includes(alias));

    if (aliases.length > 0) {
      handleInputChange("brand_aliases", [
        ...formData.brand_aliases,
        ...aliases,
      ]);
    }
  };

  // 提交表单
  const handleSubmit = async () => {
    if (loading) return;

    const isValid = await validateForm();
    if (!isValid) return;

    setLoading(true);
    try {
      const submitData: ProjectFormData = {
        project_name: formData.project_name.trim(),
        brand_name: formData.brand_name.trim(),
        sector: formData.sector,
        brand_aliases: formData.brand_aliases.filter(
          (alias) => alias.trim() !== ""
        ),
      };

      let resultProject: Project;
      if (isEditing) {
        resultProject = await projectAPI.updateProject(project!.id, submitData);
      } else {
        resultProject = await projectAPI.createProject(submitData);
      }

      // 如果需要设为当前项目
      if (setAsCurrentProject && !isEditing) {
        await projectAPI.switchProject(resultProject.id);
        resultProject.is_current = true;
      }

      onSuccess?.(resultProject, !isEditing);
      // 保存成功后，提示外层面板刷新
      const ev = new CustomEvent("project:list:reload");
      window.dispatchEvent(ev);
      onClose();
    } catch (error) {
      console.error("保存项目失败:", error);
      if (error instanceof Error) {
        setErrors({ brand_name: error.message });
      }
    } finally {
      setLoading(false);
    }
  };

  // 关闭处理
  const handleClose = () => {
    if (hasChanges) {
      const confirmed = window.confirm("您有未保存的更改，确定要关闭吗？");
      if (!confirmed) return;
    }
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div
        className={`w-full max-w-2xl bg-white dark:bg-gray-900 rounded-2xl shadow-2xl overflow-hidden ${className}`}
      >
        {/* 头部 */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-3">
            <div>
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                {modalTitle}
              </h2>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="px-4 py-1 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg transition-colors"
          >
            <span>关闭</span>
          </button>
        </div>

        {/* 表单内容 */}
        <div className="p-6 space-y-3">
         
          {/* 项目名称 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              项目名称 <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={(formData.project_name as string) || ""}
              onChange={(e) => handleInputChange("project_name", e.target.value)}
              placeholder="请输入项目名称（必填）"
              className={`w-full px-4 py-3 bg-gray-50 dark:bg-gray-800 border rounded-xl text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-colors ${
                errors.project_name
                  ? "border-red-500"
                  : "border-gray-200 dark:border-gray-700"
              }`}
            />
          </div>

          {/* 品牌名称 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              品牌名称 <span className="text-red-500">*</span>
            </label>
            <input
              ref={brandNameInputRef}
              type="text"
              value={formData.brand_name}
              onChange={(e) => handleInputChange("brand_name", e.target.value)}
              placeholder="请输入品牌名称"
              className={`w-full px-4 py-3 bg-gray-50 dark:bg-gray-800 border rounded-xl text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-colors ${
                errors.brand_name
                  ? "border-red-500"
                  : "border-gray-200 dark:border-gray-700"
              }`}
            />

            {errors.brand_name && (
              <div className="flex items-center space-x-2 mt-2 text-red-500 text-sm">
                <AlertCircle className="w-4 h-4" />

                <span>{errors.brand_name}</span>
              </div>
            )}
          </div>

          {/* 行业选择 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              行业分类 <span className="text-red-500">*</span>
            </label>
            <select
              value={formData.sector}
              onChange={(e) => handleInputChange("sector", e.target.value)}
              className={`w-full px-4 py-3 bg-gray-50 dark:bg-gray-800 border rounded-xl text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-colors ${
                errors.sector
                  ? "border-red-500"
                  : "border-gray-200 dark:border-gray-700"
              }`}
            >
              <option value="">请选择行业</option>
              {SECTOR_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            {errors.sector && (
              <div className="flex items-center space-x-2 mt-2 text-red-500 text-sm">
                <AlertCircle className="w-4 h-4" />

                <span>{errors.sector}</span>
              </div>
            )}
          </div>

          {/* 品牌别名 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              品牌别名{" "}
              <span className="text-gray-500 dark:text-gray-400">(可选)</span>
            </label>
            <div className="space-y-3">
              {/* 别名输入 */}
              <div className="flex space-x-2">
                <input
                  ref={aliasInputRef}
                  type="text"
                  value={aliasInput}
                  onChange={(e) => setAliasInput(e.target.value)}
                  onKeyDown={handleAliasKeyDown}
                  onPaste={handleAliasPaste}
                  placeholder="输入别名后按回车添加，支持批量粘贴"
                  className="flex-1 px-4 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                />

                <button
                  type="button"
                  onClick={handleAddAlias}
                  disabled={!aliasInput.trim()}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/50 text-white rounded-lg transition-colors"
                >
                  <Plus className="w-4 h-4" />
                </button>
              </div>

              {/* 别名列表 */}
              {formData.brand_aliases.length > 0 && (
                <div className="space-y-2 max-h-28 overflow-auto pr-1">
                  <div className="text-sm text-gray-600 dark:text-gray-400">
                    已添加 {formData.brand_aliases.length} 个别名：
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {formData.brand_aliases.map((alias, index) => (
                      <div
                        key={index}
                        className="flex items-center space-x-2 px-3 py-1 bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg"
                      >
                        <Tag className="w-3 h-3 text-gray-500 dark:text-gray-400" />

                        <span className="text-sm text-gray-900 dark:text-white">
                          {alias}
                        </span>
                        <button
                          type="button"
                          onClick={() => handleRemoveAlias(index)}
                          className="p-0.5 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                        >
                          <Trash2 className="w-3 h-3 text-red-500" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="text-xs text-gray-500 dark:text-gray-400 -mt-1">
                提示：别名用于提高搜索匹配准确度
              </div>
            </div>
          </div>

          {/* 新建项目选项 */}
          {!isEditing && (
            <div className="flex items-center space-x-2 p-0 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <input
                type="checkbox"
                id="setAsCurrent"
                checked={setAsCurrentProject}
                onChange={(e) => setSetAsCurrentProject(e.target.checked)}
                className="rounded border-gray-300 dark:border-gray-600 text-blue-600 focus:ring-blue-500/50"
              />
              <label htmlFor="setAsCurrent" className="text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
                创建后设为当前项目
              </label>
            </div>
          )}
        </div>

        {/* 底部操作 */}
        <div className="flex items-center justify-between p-6 border-t border-gray-200 dark:border-gray-700">
          <div className="text-sm text-gray-500 dark:text-gray-400">
            {hasChanges && "• 有未保存的更改"}
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={handleClose}
              className="px-4 py-2 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg transition-colors"
            >
              取消
            </button>
            <button
              onClick={handleSubmit}
              disabled={loading || !hasChanges}
              className="flex items-center space-x-2 px-6 py-2 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 disabled:opacity-50 text-white rounded-lg transition-all duration-200 shadow-lg hover:shadow-xl"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Save className="w-4 h-4" />
              )}
              <span>
                {loading ? "保存中..." : isEditing ? "保存更改" : "创建项目"}
              </span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
