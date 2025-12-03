/**
 * 用户偏好页面 - Liquid Glass 风格
 * 
 * 路由: /zara/user-profile
 * 功能: 展示用户历史对话、偏好标签和个性化画像
 * 
 * 四维度偏好：属性(A) · 性能(P) · 场景(U) · 风格(S)
 */

'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { cn } from '@/lib/utils';
import {
  User,
  MessageSquare,
  Tag,
  TrendingUp,
  MapPin,
  Heart,
  Clock,
  ChevronRight,
  RefreshCw,
  Search,
  Sparkles,
  ShoppingBag,
  Eye,
  Thermometer,
  UserCircle,
} from 'lucide-react';

// ============================================================================
// 类型定义
// ============================================================================

interface UserProfile {
  id: number;
  user_id: string;
  inferred_gender: string | null;
  inferred_age_group: string | null;
  style_preferences: string[];
  category_preferences: string[];
  attribute_preferences: string[];
  performance_preferences: string[];
  use_preferences: string[];
  region_preference: string | null;
  total_searches: number;
  total_clicks: number;
  tag_cloud: Record<string, number>;
  last_active_at: string;
}

interface ChatHistory {
  id: number;
  user_id: string;
  query: string;
  search_text: string | null;
  extracted_tags: string[] | null;
  intent_attribute: string[] | null;
  intent_performance: string[] | null;
  intent_use: string[] | null;
  result_count: number | null;
  session_id: string | null;
  created_at: string;
}

// ============================================================================
// 组件
// ============================================================================

/** 标签云组件 */
const TagCloud: React.FC<{ tags: Record<string, number>; color: string }> = ({ tags, color }) => {
  const sortedTags = Object.entries(tags)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 15);

  const maxCount = Math.max(...Object.values(tags), 1);

  return (
    <div className="flex flex-wrap gap-2">
      {sortedTags.map(([tag, count]) => {
        const size = 0.7 + (count / maxCount) * 0.6;
        const opacity = 0.5 + (count / maxCount) * 0.5;
        return (
          <span
            key={tag}
            className="px-3 py-1 rounded-full transition-all hover:scale-105"
            style={{
              fontSize: `${size}rem`,
              background: `${color}${Math.round(opacity * 40).toString(16).padStart(2, '0')}`,
              color: color,
              border: `1px solid ${color}40`,
            }}
          >
            {tag}
            <span className="ml-1 opacity-60 text-xs">×{count}</span>
          </span>
        );
      })}
    </div>
  );
};

/** 用户卡片 */
const UserCard: React.FC<{
  profile: UserProfile;
  isSelected: boolean;
  onClick: () => void;
}> = ({ profile, isSelected, onClick }) => {
  const regionText = profile.region_preference === 'south' ? '南方' : 
                     profile.region_preference === 'north' ? '北方' : '未知';
  const genderIcon = profile.inferred_gender === 'female' ? '👩' : 
                     profile.inferred_gender === 'male' ? '👨' : '👤';

  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full p-4 rounded-xl text-left transition-all",
        "hover:bg-slate-700/50",
        isSelected && "ring-2 ring-purple-500"
      )}
      style={{
        background: isSelected 
          ? 'linear-gradient(135deg, rgba(139, 92, 246, 0.15), rgba(59, 130, 246, 0.1))'
          : 'rgba(30, 41, 59, 0.5)',
      }}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{genderIcon}</span>
          <p className="text-white font-medium">{profile.user_id}</p>
        </div>
        <ChevronRight className={cn("w-5 h-5 text-gray-400 transition-transform", isSelected && "rotate-90")} />
      </div>
      
      <div className="flex items-center gap-4 text-xs text-gray-400">
        <span className="flex items-center gap-1">
          <Search className="w-3 h-3" />
          {profile.total_searches} 次搜索
        </span>
        <span className="flex items-center gap-1">
          <MapPin className="w-3 h-3" />
          {regionText}
        </span>
      </div>

      {/* 主要偏好标签 */}
      <div className="mt-2 flex flex-wrap gap-1">
        {(profile.style_preferences || []).slice(0, 3).map((tag) => (
          <span key={tag} className="px-2 py-0.5 text-xs rounded-full bg-purple-500/20 text-purple-300">
            {tag}
          </span>
        ))}
      </div>
    </button>
  );
};

/** 聊天记录卡片 */
const ChatCard: React.FC<{ chat: ChatHistory }> = ({ chat }) => {
  return (
    <div
      className="p-4 rounded-xl"
      style={{
        background: 'rgba(30, 41, 59, 0.6)',
        border: '1px solid rgba(100, 116, 139, 0.2)',
      }}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <MessageSquare className="w-4 h-4 text-blue-400" />
          <span className="text-white font-medium">"{chat.query}"</span>
        </div>
        <span className="text-xs text-gray-500">
          {new Date(chat.created_at).toLocaleString('zh-CN')}
        </span>
      </div>

      {chat.search_text && (
        <p className="text-sm text-gray-400 mb-2">
          → 搜索文本: {chat.search_text}
        </p>
      )}

      <div className="flex flex-wrap gap-2 mt-2">
        {/* 属性标签 */}
        {(chat.intent_attribute || []).map((tag) => (
          <span key={`attr-${tag}`} className="px-2 py-0.5 text-xs rounded-full bg-blue-500/20 text-blue-300">
            属性: {tag}
          </span>
        ))}
        {/* 性能标签 */}
        {(chat.intent_performance || []).map((tag) => (
          <span key={`perf-${tag}`} className="px-2 py-0.5 text-xs rounded-full bg-green-500/20 text-green-300">
            性能: {tag}
          </span>
        ))}
        {/* 场景标签 */}
        {(chat.intent_use || []).map((tag) => (
          <span key={`use-${tag}`} className="px-2 py-0.5 text-xs rounded-full bg-amber-500/20 text-amber-300">
            场景: {tag}
          </span>
        ))}
      </div>

      {chat.result_count !== null && (
        <p className="text-xs text-gray-500 mt-2">
          返回 {chat.result_count} 个结果
        </p>
      )}
    </div>
  );
};

// ============================================================================
// 主页面
// ============================================================================

export default function UserProfilePage() {
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [selectedUser, setSelectedUser] = useState<UserProfile | null>(null);
  const [chatHistory, setChatHistory] = useState<ChatHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);

  /**
   * 加载用户列表
   */
  const loadUsers = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/zara/user-profile');
      const data = await response.json();
      if (data.success) {
        setUsers(data.data || []);
        // 默认选中第一个用户
        if (data.data?.length > 0) {
          loadUserDetail(data.data[0]);
        }
      }
    } catch (error) {
      console.error('加载用户列表失败:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * 加载用户详情
   */
  const loadUserDetail = async (user: UserProfile) => {
    setSelectedUser(user);
    setLoadingDetail(true);
    try {
      const response = await fetch(`/api/zara/user-profile?userId=${user.user_id}&includeHistory=true`);
      const data = await response.json();
      if (data.success) {
        setChatHistory(data.data.chatHistory || []);
      }
    } catch (error) {
      console.error('加载用户详情失败:', error);
    } finally {
      setLoadingDetail(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  return (
    <div className="min-h-screen">
      {/* 页面标题 */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center"
              style={{
                background: 'linear-gradient(135deg, #8b5cf6, #ec4899)',
                boxShadow: '0 4px 20px rgba(139, 92, 246, 0.4)',
              }}
            >
              <User className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1
                className="text-2xl font-bold"
                style={{
                  background: 'linear-gradient(90deg, #a78bfa, #f472b6)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                }}
              >
                用户偏好
              </h1>
              <p className="text-sm text-gray-400">
                基于历史对话的用户偏好分析
              </p>
            </div>
          </div>
          <button
            onClick={loadUsers}
            disabled={loading}
            className="p-2 rounded-lg transition-colors hover:bg-slate-700/50"
          >
            <RefreshCw className={cn("w-5 h-5 text-gray-400", loading && "animate-spin")} />
          </button>
        </div>
      </div>

      {/* 价值说明 */}
      <div
        className="p-4 rounded-xl mb-6 flex items-start gap-3"
        style={{
          background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(236, 72, 153, 0.1))',
          border: '1px solid rgba(139, 92, 246, 0.2)',
        }}
      >
        <Sparkles className="w-5 h-5 text-purple-400 shrink-0 mt-0.5" />
        <div className="text-sm text-gray-300">
          <p className="font-medium text-purple-300 mb-1">千人千面个性化推荐</p>
          <p>
            系统自动分析用户历史对话，提取偏好标签（如风格、场景、区域），构建动态用户档案。
            这些标签可用于个性化推荐（如南方用户优先展示薄款），也可对外输出用于其他运营场景。
          </p>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <RefreshCw className="w-8 h-8 text-purple-400 animate-spin" />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* 左侧：用户列表（窄） */}
          <div
            className="lg:col-span-1 rounded-xl p-4"
            style={{
              background: 'rgba(30, 41, 59, 0.6)',
              backdropFilter: 'blur(10px)',
              border: '1px solid rgba(100, 116, 139, 0.2)',
            }}
          >
            <h3 className="text-white font-medium mb-4 flex items-center gap-2 text-sm">
              <User className="w-4 h-4 text-purple-400" />
              用户列表 ({users.length})
            </h3>
            <div className="space-y-2 max-h-[700px] overflow-y-auto">
              {users.map((user) => (
                <UserCard
                  key={user.user_id}
                  profile={user}
                  isSelected={selectedUser?.user_id === user.user_id}
                  onClick={() => loadUserDetail(user)}
                />
              ))}
            </div>
          </div>

          {/* 右侧：用户详情（宽） */}
          <div className="lg:col-span-3 space-y-4">
            {selectedUser ? (
              <>
                {/* 偏好画像总结 */}
                <div
                  className="rounded-xl p-6"
                  style={{
                    background: 'rgba(30, 41, 59, 0.6)',
                    backdropFilter: 'blur(10px)',
                    border: '1px solid rgba(100, 116, 139, 0.2)',
                  }}
                >
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-white font-medium flex items-center gap-2">
                      <Heart className="w-4 h-4 text-pink-400" />
                      偏好画像总结
                    </h3>
                    <div className="flex items-center gap-2 text-sm">
                      <span className="px-2 py-1 rounded-lg bg-purple-500/20 text-purple-300">
                        {selectedUser.inferred_gender === 'female' ? '女性' : 
                         selectedUser.inferred_gender === 'male' ? '男性' : '未知性别'}
                      </span>
                      <span className="px-2 py-1 rounded-lg bg-amber-500/20 text-amber-300">
                        {selectedUser.region_preference === 'south' ? '南方用户' :
                         selectedUser.region_preference === 'north' ? '北方用户' : '区域未知'}
                      </span>
                    </div>
                  </div>

                  {/* 偏好分类 */}
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
                    <div>
                      <p className="text-xs text-gray-400 mb-2">风格偏好</p>
                      <div className="flex flex-wrap gap-1">
                        {(selectedUser.style_preferences || []).map((tag) => (
                          <span key={tag} className="px-2 py-0.5 text-xs rounded-full bg-purple-500/20 text-purple-300">
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400 mb-2">品类偏好</p>
                      <div className="flex flex-wrap gap-1">
                        {(selectedUser.category_preferences || []).map((tag) => (
                          <span key={tag} className="px-2 py-0.5 text-xs rounded-full bg-blue-500/20 text-blue-300">
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400 mb-2">性能偏好</p>
                      <div className="flex flex-wrap gap-1">
                        {(selectedUser.performance_preferences || []).map((tag) => (
                          <span key={tag} className="px-2 py-0.5 text-xs rounded-full bg-green-500/20 text-green-300">
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400 mb-2">场景偏好</p>
                      <div className="flex flex-wrap gap-1">
                        {(selectedUser.use_preferences || []).map((tag) => (
                          <span key={tag} className="px-2 py-0.5 text-xs rounded-full bg-amber-500/20 text-amber-300">
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* 标签云 */}
                  <div>
                    <p className="text-xs text-gray-400 mb-2 flex items-center gap-1">
                      <TrendingUp className="w-3 h-3" />
                      标签词频云
                    </p>
                    <TagCloud tags={selectedUser.tag_cloud || {}} color="#a78bfa" />
                  </div>
                </div>

                {/* 用户画像数据来源 - 四大维度 */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* 基础属性 */}
                  <div
                    className="rounded-xl p-4"
                    style={{
                      background: 'rgba(30, 41, 59, 0.6)',
                      backdropFilter: 'blur(10px)',
                      border: '1px solid rgba(139, 92, 246, 0.2)',
                    }}
                  >
                    <h4 className="text-white font-medium mb-3 flex items-center gap-2 text-sm">
                      <UserCircle className="w-4 h-4 text-purple-400" />
                      基础属性
                      <span className="text-xs text-gray-500 font-normal">（会员注册信息）</span>
                    </h4>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div className="p-2 rounded-lg bg-slate-800/50">
                        <span className="text-gray-400">性别：</span>
                        <span className="text-purple-300">
                          {selectedUser.inferred_gender === 'female' ? '女' : 
                           selectedUser.inferred_gender === 'male' ? '男' : '-'}
                        </span>
                      </div>
                      <div className="p-2 rounded-lg bg-slate-800/50">
                        <span className="text-gray-400">身高：</span>
                        <span className="text-purple-300">165cm</span>
                      </div>
                      <div className="p-2 rounded-lg bg-slate-800/50">
                        <span className="text-gray-400">体重：</span>
                        <span className="text-purple-300">52kg</span>
                      </div>
                      <div className="p-2 rounded-lg bg-slate-800/50">
                        <span className="text-gray-400">生日：</span>
                        <span className="text-purple-300">1995-06</span>
                      </div>
                    </div>
                  </div>

                  {/* 地理位置 */}
                  <div
                    className="rounded-xl p-4"
                    style={{
                      background: 'rgba(30, 41, 59, 0.6)',
                      backdropFilter: 'blur(10px)',
                      border: '1px solid rgba(34, 197, 94, 0.2)',
                    }}
                  >
                    <h4 className="text-white font-medium mb-3 flex items-center gap-2 text-sm">
                      <Thermometer className="w-4 h-4 text-green-400" />
                      地理位置
                      <span className="text-xs text-gray-500 font-normal">（环境因素）</span>
                    </h4>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div className="p-2 rounded-lg bg-slate-800/50">
                        <span className="text-gray-400">区域：</span>
                        <span className="text-green-300">
                          {selectedUser.region_preference === 'south' ? '南方' :
                           selectedUser.region_preference === 'north' ? '北方' : '未知'}
                        </span>
                      </div>
                      <div className="p-2 rounded-lg bg-slate-800/50">
                        <span className="text-gray-400">城市：</span>
                        <span className="text-green-300">上海</span>
                      </div>
                      <div className="p-2 rounded-lg bg-slate-800/50">
                        <span className="text-gray-400">气温：</span>
                        <span className="text-green-300">22°C</span>
                      </div>
                      <div className="p-2 rounded-lg bg-slate-800/50">
                        <span className="text-gray-400">湿度：</span>
                        <span className="text-green-300">65%</span>
                      </div>
                    </div>
                  </div>

                  {/* 历史订单 */}
                  <div
                    className="rounded-xl p-4"
                    style={{
                      background: 'rgba(30, 41, 59, 0.6)',
                      backdropFilter: 'blur(10px)',
                      border: '1px solid rgba(245, 158, 11, 0.2)',
                    }}
                  >
                    <h4 className="text-white font-medium mb-3 flex items-center gap-2 text-sm">
                      <ShoppingBag className="w-4 h-4 text-amber-400" />
                      历史订单 (12)
                      <span className="text-xs text-gray-500 font-normal">（消费习惯）</span>
                    </h4>
                    <div className="space-y-2 text-xs">
                      <div className="flex items-center justify-between p-2 rounded-lg bg-slate-800/50">
                        <span className="text-gray-400">常购品类</span>
                        <span className="text-amber-300">T恤、连衣裙、短裤</span>
                      </div>
                      <div className="flex items-center justify-between p-2 rounded-lg bg-slate-800/50">
                        <span className="text-gray-400">价格偏好</span>
                        <span className="text-amber-300">¥100-300</span>
                      </div>
                      <div className="flex items-center justify-between p-2 rounded-lg bg-slate-800/50">
                        <span className="text-gray-400">常购尺码</span>
                        <span className="text-amber-300">S / M</span>
                      </div>
                    </div>
                  </div>

                  {/* 历史浏览 */}
                  <div
                    className="rounded-xl p-4"
                    style={{
                      background: 'rgba(30, 41, 59, 0.6)',
                      backdropFilter: 'blur(10px)',
                      border: '1px solid rgba(59, 130, 246, 0.2)',
                    }}
                  >
                    <h4 className="text-white font-medium mb-3 flex items-center gap-2 text-sm">
                      <Eye className="w-4 h-4 text-blue-400" />
                      历史浏览 (56)
                      <span className="text-xs text-gray-500 font-normal">（行为数据）</span>
                    </h4>
                    <div className="space-y-2 text-xs">
                      <div className="flex items-center justify-between p-2 rounded-lg bg-slate-800/50">
                        <span className="text-gray-400">搜索次数</span>
                        <span className="text-blue-300">{selectedUser.total_searches} 次</span>
                      </div>
                      <div className="flex items-center justify-between p-2 rounded-lg bg-slate-800/50">
                        <span className="text-gray-400">点击次数</span>
                        <span className="text-blue-300">{selectedUser.total_clicks} 次</span>
                      </div>
                      <div className="flex items-center justify-between p-2 rounded-lg bg-slate-800/50">
                        <span className="text-gray-400">平均停留</span>
                        <span className="text-blue-300">45 秒</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* 历史搜索对话 */}
                <div
                  className="rounded-xl p-6"
                  style={{
                    background: 'rgba(30, 41, 59, 0.6)',
                    backdropFilter: 'blur(10px)',
                    border: '1px solid rgba(100, 116, 139, 0.2)',
                  }}
                >
                  <h3 className="text-white font-medium mb-4 flex items-center gap-2">
                    <Clock className="w-4 h-4 text-cyan-400" />
                    历史搜索对话 ({chatHistory.length})
                  </h3>
                  
                  {loadingDetail ? (
                    <div className="flex items-center justify-center py-8">
                      <RefreshCw className="w-6 h-6 text-cyan-400 animate-spin" />
                    </div>
                  ) : (
                    <div className="space-y-3 max-h-[400px] overflow-y-auto">
                      {chatHistory.map((chat) => (
                        <ChatCard key={chat.id} chat={chat} />
                      ))}
                      {chatHistory.length === 0 && (
                        <p className="text-center text-gray-500 py-8">暂无搜索记录</p>
                      )}
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div
                className="rounded-xl p-12 text-center"
                style={{
                  background: 'rgba(30, 41, 59, 0.6)',
                  border: '1px solid rgba(100, 116, 139, 0.2)',
                }}
              >
                <User className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                <p className="text-gray-500">选择一个用户查看详情</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

