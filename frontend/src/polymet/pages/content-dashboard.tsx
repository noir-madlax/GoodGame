 
import FilterBar from "@/polymet/components/filter-bar";
import VideoGridCard from "@/polymet/components/video-grid-card";
import { Grid, List, SortAsc, MoreHorizontal } from "lucide-react";
import { cn } from "@/lib/utils";
import { useNavigate } from "react-router-dom";

export default function ContentDashboard() {
  const navigate = useNavigate();

  const sampleVideos = [
    {
      title:
        "大晚上去海底捞吃饭看到的小可爱 😍 #当你有只喵馋小狗 #养狗当然就是用来玩的 #被小狗治愈的一万个瞬间",
      thumbnail:
        "https://images.unsplash.com/photo-1574158622682-e40e69881006?w=400&h=225&fit=crop",
      duration: "0:27",
      views: 508,
      likes: 55,
      comments: 428,
      author: "CC记录",
      category: "抖音",
      tags: ["宠物进店", "用餐卫生"],
      publishTime: "6小时前",
    },
    {
      title: "海底捞排队太久了",
      thumbnail:
        "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=400&h=225&fit=crop",
      duration: "1:45",
      views: 567,
      likes: 123,
      comments: 23,
      author: "吃货小分队",
      category: "内容",
      tags: ["服务体验", "排队"],
      publishTime: "8小时前",
    },
    {
      title: "海底捞新品试吃",
      thumbnail:
        "https://images.unsplash.com/photo-1565299624946-b28f40a0ca4b?w=400&h=225&fit=crop",
      duration: "3:12",
      views: 2341,
      likes: 234,
      comments: 156,
      author: "美食探店",
      category: "小红书",
      tags: ["食品安全", "新品", "试吃"],
      publishTime: "6小时前",
    },
    {
      title: "海底捞价格分析",
      thumbnail:
        "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=400&h=225&fit=crop",
      duration: "4:23",
      views: 890,
      likes: 167,
      comments: 78,
      author: "价格分析师",
      category: "正面",
      tags: ["价格", "分析"],
      publishTime: "8小时前",
    },
    {
      title: "海底捞员工服务态度",
      thumbnail:
        "https://images.unsplash.com/photo-1559329007-40df8a9345d8?w=400&h=225&fit=crop",
      duration: "2:56",
      views: 1567,
      likes: 98,
      comments: 67,
      author: "服务体验官",
      category: "小红书",
      tags: ["服务", "员工"],
      publishTime: "12小时前",
    },
    {
      title: "海底捞食材新鲜度",
      thumbnail:
        "https://images.unsplash.com/photo-1606787366850-de6330128bfc?w=400&h=225&fit=crop",
      duration: "1:23",
      views: 234,
      likes: 56,
      comments: 12,
      author: "健康生活",
      category: "科普",
      tags: ["食品安全", "健康", "图文"],
      publishTime: "1天前",
    },
    {
      title: "海底捞环境卫生检查",
      thumbnail:
        "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=400&h=225&fit=crop",
      duration: "5:45",
      views: 3456,
      likes: 234,
      comments: 189,
      author: "卫生监督",
      category: "中风险",
      tags: ["环境卫生", "检查"],
      publishTime: "2天前",
    },
    {
      title: "海底捞新店开业",
      thumbnail:
        "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=400&h=225&fit=crop",
      duration: "3:30",
      views: 1890,
      likes: 145,
      comments: 89,
      author: "商业观察",
      category: "内容",
      tags: ["开业", "新店", "扩张"],
      publishTime: "3天前",
    },
  ];

  return (
    <div className="space-y-8">
      {/* Filter Bar */}
      <FilterBar />

      {/* Content Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            内容监控结果
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            共找到 {sampleVideos.length.toLocaleString()} 条相关内容
          </p>
        </div>

        {/* View Controls */}
        <div className="flex items-center space-x-4">
          {/* Sort Button */}
          <button
            className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-gray-100/40 dark:bg-gray-800/30 backdrop-blur-xl border border-white/20 text-gray-400 cursor-not-allowed transition-all duration-300"
            disabled
            aria-disabled
            title="Not implemented yet"
          >
            <SortAsc className="w-4 h-4 text-gray-600 dark:text-gray-300" />

            <span className="text-sm font-medium text-gray-400">
              按时间排序
            </span>
          </button>

          {/* View Mode Toggle */}
          <div className="flex items-center rounded-xl bg-white/10 backdrop-blur-xl border border-white/20 p-1">
            <button className="p-2 rounded-lg text-gray-400 bg-transparent cursor-not-allowed" disabled aria-disabled>
              <Grid className="w-4 h-4" />
            </button>
            <button className="p-2 rounded-lg text-gray-400 bg-transparent cursor-not-allowed" disabled aria-disabled>
              <List className="w-4 h-4" />
            </button>
          </div>

          {/* More Options */}
          <button
            className="p-2 rounded-xl bg-gray-100/40 dark:bg-gray-800/30 backdrop-blur-xl border border-white/20 text-gray-400 cursor-not-allowed"
            disabled
            aria-disabled
            title="Not implemented yet"
          >
            <MoreHorizontal className="w-5 h-5 text-gray-600 dark:text-gray-300" />
          </button>
        </div>
      </div>

      {/* Content Grid */}
      <div className={cn("grid gap-6 transition-all duration-500 grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4")}
      >
        {sampleVideos.map((video, index) => (
          <VideoGridCard
            key={index}
            {...video}
            onClick={() => navigate(`/detail/${index + 1}`)}
          />
        ))}
      </div>

      {/* Load More */}
      <div className="flex justify-center pt-8">
        <button className="px-8 py-3 rounded-xl bg-gradient-to-r from-blue-500 to-purple-600 text-white font-medium hover:from-blue-600 hover:to-purple-700 transition-all duration-300 hover:scale-105 shadow-lg hover:shadow-xl">
          加载更多内容
        </button>
      </div>
    </div>
  );
}
