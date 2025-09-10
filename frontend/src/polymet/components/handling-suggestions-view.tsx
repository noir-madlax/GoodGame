import React, { useState } from "react";
import { AlertTriangle, Shield, Scale, MessageSquare, CheckCircle, Users, FileText, Copy, Download, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

export interface LegalBasis {
  law_name: string;
  article: string;
  why_relevant: string;
}

export interface Strategy {
  tone: "good" | "strict";
  target: string;
  talk_track: string;
  incentives: string[];
  legal_basis: LegalBasis[];
  platform_policy_basis: string[];
  required_actions: string[];
  escalation_path: string;
}

export interface HandlingSuggestionsData {
  overview: string;
  severity: "low" | "medium" | "high";
  priority: "P1" | "P2" | "P3";
  legal_risk_summary: string;
  strategies: Strategy[];
  outreach_channels: string[];
  follow_up_checklist: string[];
  redact_suggestions: string[];
}

export interface HandlingSuggestionsProps {
  data: HandlingSuggestionsData;
  isOpen: boolean;
  onClose: () => void;
  className?: string;
  showHeader?: boolean; // 新增：是否渲染内部头部（页面模式可关闭）
}


const getPriorityColor = (priority: string) => {
  switch (priority) {
    case "P1":
      return "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 border-red-200 dark:border-red-800";
    case "P2":
      return "bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400 border-orange-200 dark:border-orange-800";
    case "P3":
      return "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 border-blue-200 dark:border-blue-800";
    default:
      return "bg-gray-100 dark:bg-gray-900/30 text-gray-700 dark:text-gray-400 border-gray-200 dark:border-gray-800";
  }
};

export default function HandlingSuggestionsView({ data, isOpen, onClose, className = "", showHeader = true }: HandlingSuggestionsProps) {
  const [activeStrategy, setActiveStrategy] = useState(0);
  if (!isOpen) return null;
  const copyToClipboard = (text: string) => navigator.clipboard.writeText(text);
  return (
    <div className={`w-full max-w-6xl mx-auto rounded-3xl bg-white/10 backdrop-blur-xl border border-white/20 shadow-2xl ${className}`}>
      {showHeader && (
        <div className="flex items-center justify-between p-6 border-b border-white/20">
          <div className="flex items-center space-x-4">
            <div className="p-3 rounded-xl bg-blue-100 dark:bg-blue-900/30">
              <Shield className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white">处理建议</h2>
            </div>
          </div>
          <TooltipProvider>
            <div className="flex items-center space-x-2">
              <Tooltip>
                <TooltipTrigger asChild>
                  <button className="p-3 rounded-xl bg-white/10 backdrop-blur-xl border border-white/20 hover:bg-white/20 transition-all duration-300 shadow-lg hover:shadow-xl" aria-label="导出报告">
                    <Download className="w-5 h-5 text-gray-700 dark:text-gray-300" />
                  </button>
                </TooltipTrigger>
                <TooltipContent>导出报告</TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button className="p-3 rounded-xl bg-white/10 backdrop-blur-xl border border-white/20 hover:bg-white/20 transition-all duration-300 shadow-lg hover:shadow-xl" aria-label="关闭" onClick={onClose}>
                    <X className="w-5 h-5 text-gray-700 dark:text-gray-300" />
                  </button>
                </TooltipTrigger>
                <TooltipContent>关闭</TooltipContent>
              </Tooltip>
            </div>
          </TooltipProvider>
        </div>
      )}

      <div className="p-6">
        <div className="space-y-6">
          {/* 概览 */}
          <Card className="bg-white/10 backdrop-blur-xl border-white/20">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center space-x-2">
                  <AlertTriangle className="w-5 h-5 text-orange-500" />
                  <span>情况概览</span>
                </CardTitle>
                <div className="flex items-center space-x-2">
                  <Badge className={`px-3 py-1 text-xs font-medium border rounded-full bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 border-red-200 dark:border-red-800 ${data.severity === "high" ? "" : data.severity === "medium" ? "!bg-orange-100 dark:!bg-orange-900/30 !text-orange-700 dark:!text-orange-400 !border-orange-200 dark:!border-orange-800" : "!bg-green-100 dark:!bg-green-900/30 !text-green-700 dark:!text-green-400 !border-green-200 dark:!border-green-800"}`}>{data.severity === "high" ? "高风险" : data.severity === "medium" ? "中等风险" : "低风险"}</Badge>
                  <Badge className={`px-3 py-1 text-xs font-medium border rounded-full ${getPriorityColor(data.priority)}`}>{data.priority}优先级</Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-gray-700 dark:text-gray-300 leading-relaxed">{data.overview}</p>
            </CardContent>
          </Card>

          {/* 法律风险 */}
          <Card className="bg-white/10 backdrop-blur-xl border-white/20">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Scale className="w-5 h-5 text-purple-500" />
                <span>法律风险评估</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-700 dark:text-gray-300 leading-relaxed">{data.legal_risk_summary}</p>
            </CardContent>
          </Card>

          {/* 整改建议：上移到应对策略前 */}
          {data.redact_suggestions.length > 0 && (
            <Card className="bg-white/10 backdrop-blur-xl border-white/20">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <FileText className="w-5 h-5 text-red-500" />
                  <span>整改建议</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {data.redact_suggestions.map((suggestion, index) => (
                    <div key={index} className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
                      <p className="text-red-700 dark:text-red-400">{suggestion}</p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* 应对策略 */}
          <Card className="bg-white/10 backdrop-blur-xl border-white/20">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <MessageSquare className="w-5 h-5 text-blue-500" />
                <span>应对策略</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Tabs value={activeStrategy.toString()} onValueChange={(v) => setActiveStrategy(parseInt(v))}>
                <TabsList className="grid w-full grid-cols-2 bg-white/10 backdrop-blur-xl border border-white/20">
                  {data.strategies.map((strategy, index) => (
                    <TabsTrigger key={index} value={index.toString()} className="flex items-center space-x-2 data-[state=active]:bg-white/20">
                      {strategy.tone === "good" ? (
                        <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400" />
                      ) : (
                        <AlertTriangle className="w-4 h-4 text-orange-600 dark:text-orange-400" />
                      )}
                      <span>{strategy.tone === "good" ? "友好沟通" : "严肃处理"}</span>
                    </TabsTrigger>
                  ))}
                </TabsList>

                {data.strategies.map((strategy, index) => (
                  <TabsContent key={index} value={index.toString()} className="mt-6">
                    <div className="space-y-6">
                      <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                        <div className="flex items-center justify-between mb-3">
                          <h4 className="font-semibold text-gray-900 dark:text-white">沟通话术</h4>
                          <Button variant="ghost" size="sm" onClick={() => copyToClipboard(strategy.talk_track)} className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300">
                            <Copy className="w-4 h-4" />
                          </Button>
                        </div>
                        <p className="text-gray-700 dark:text-gray-300 leading-relaxed">{strategy.talk_track}</p>
                      </div>

                      {strategy.incentives.length > 0 && (
                        <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                          <h4 className="font-semibold text-gray-900 dark:text-white mb-3">激励措施</h4>
                          <ul className="space-y-2">
                            {strategy.incentives.map((incentive, idx) => (
                              <li key={idx} className="flex items-start space-x-2">
                                <CheckCircle className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                                <span className="text-gray-700 dark:text-gray-300">{incentive}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                        <h4 className="font-semibold text-gray-900 dark:text-white mb-3">要求行动</h4>
                        <ul className="space-y-2">
                          {strategy.required_actions.map((action, idx) => (
                            <li key={idx} className="flex items-start space-x-2">
                              <AlertTriangle className="w-4 h-4 text-orange-500 mt-0.5 flex-shrink-0" />
                              <span className="text-gray-700 dark:text-gray-300">{action}</span>
                            </li>
                          ))}
                        </ul>
                      </div>

                      {strategy.legal_basis.length > 0 && (
                        <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                          <h4 className="font-semibold text-gray-900 dark:text-white mb-3">法律依据</h4>
                          <div className="space-y-3">
                            {strategy.legal_basis.map((legal, idx) => (
                              <div key={idx} className="p-3 rounded-lg bg-white/5 border border-white/5">
                                <div className="flex items-center space-x-2 mb-2">
                                  <Scale className="w-4 h-4 text-purple-500" />
                                  <span className="font-medium text-gray-900 dark:text-white">{legal.law_name} {legal.article}</span>
                                </div>
                                <p className="text-sm text-gray-600 dark:text-gray-400">{legal.why_relevant}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                        <h4 className="font-semibold text-gray-900 dark:text-white mb-3">升级路径</h4>
                        <p className="text-gray-700 dark:text-gray-300 leading-relaxed">{strategy.escalation_path}</p>
                      </div>
                    </div>
                  </TabsContent>
                ))}
              </Tabs>
            </CardContent>
          </Card>

          {/* 联系渠道 */}
          <Card className="bg-white/10 backdrop-blur-xl border-white/20">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Users className="w-5 h-5 text-green-500" />
                <span>联系渠道</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {data.outreach_channels.map((channel, index) => (
                  <div key={index} className="p-3 rounded-lg bg-white/5 border border-white/10 flex items-center space-x-2">
                    <span className="text-gray-700 dark:text-gray-300">{channel}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* 跟进清单 */}
          {data.follow_up_checklist.length > 0 && (
            <Card className="bg-white/10 backdrop-blur-xl border-white/20">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <CheckCircle className="w-5 h-5 text-blue-500" />
                  <span>跟进检查清单</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {data.follow_up_checklist.map((item, index) => (
                    <div key={index} className="flex items-start space-x-3 p-3 rounded-lg bg-white/5 border border-white/10">
                      <input type="checkbox" className="mt-1 rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
                      <span className="text-gray-700 dark:text-gray-300">{item}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
