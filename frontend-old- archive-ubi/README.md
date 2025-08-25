# UBI 舆情分析平台

基于 Next.js 和 AI 技术的游戏舆情监测与分析平台，专为游戏行业设计的智能舆情分析工具。

## 功能特性

- 🌐 **全网监测**: 支持哔哩哔哩、百度贴吧、微博等主流平台
- 🤖 **AI 智能分析**: 基于深度学习的情感分析和话题识别
- 📊 **可视化报表**: 丰富的图表和数据可视化展示
- 🎮 **游戏黑话识别**: 内置游戏术语知识库，准确理解玩家表达
- ⚡ **实时预警**: 智能预警系统，及时发现舆情风险
- 📋 **智能报告**: 自动生成专业的舆情分析报告

## 技术栈

- **前端框架**: Next.js 14 (App Router)
- **UI 组件**: shadcn/ui + Tailwind CSS
- **图标库**: Lucide React
- **类型检查**: TypeScript
- **部署平台**: Vercel

## 快速开始

### 环境要求

- Node.js 18.0 或更高版本
- npm 或 yarn 包管理器

### 安装依赖

\`\`\`bash
npm install
# 或
yarn install
\`\`\`

### 开发环境运行

\`\`\`bash
npm run dev
# 或
yarn dev
\`\`\`

打开 [http://localhost:3000](http://localhost:3000) 查看应用。

### 构建生产版本

\`\`\`bash
npm run build
# 或
yarn build
\`\`\`

## 部署到 Vercel

### 方法一：通过 Vercel CLI

1. 安装 Vercel CLI:
\`\`\`bash
npm i -g vercel
\`\`\`

2. 在项目根目录运行:
\`\`\`bash
vercel
\`\`\`

3. 按照提示完成部署配置

### 方法二：通过 Git 集成

1. 将代码推送到 GitHub/GitLab/Bitbucket
2. 在 [Vercel Dashboard](https://vercel.com/dashboard) 中导入项目
3. Vercel 会自动检测 Next.js 项目并配置构建设置
4. 点击 "Deploy" 完成部署

### 方法三：一键部署

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/your-username/ubi-sentiment-analysis)

## 项目结构

\`\`\`
├── app/                    # Next.js App Router 目录
│   ├── globals.css        # 全局样式
│   ├── layout.tsx         # 根布局组件
│   └── page.tsx           # 首页组件
├── components/            # React 组件
│   ├── ui/               # shadcn/ui 基础组件
│   ├── dashboard-header.tsx
│   ├── data-collection.tsx
│   ├── sentiment-analysis.tsx
│   ├── report-generation.tsx
│   └── ...
├── lib/                  # 工具函数
│   └── utils.ts
├── public/               # 静态资源
├── next.config.mjs       # Next.js 配置
├── tailwind.config.ts    # Tailwind CSS 配置
├── tsconfig.json         # TypeScript 配置
└── package.json          # 项目依赖
\`\`\`

## 主要功能模块

### 1. 全网监测
- 多平台数据采集配置
- 关键词智能推荐
- 游戏黑话知识库管理
- 实时数据预览

### 2. 智能分析
- AI 情感分析
- 多维度数据分类
- 趋势追踪分析
- 预警监控系统

### 3. 处理建议
- 智能报告生成
- 数据可视化图表
- 改进建议输出
- 多格式报告导出

## 环境变量

创建 `.env.local` 文件并添加以下环境变量（如需要）:

\`\`\`env
# API 配置
NEXT_PUBLIC_API_URL=your_api_url
API_SECRET_KEY=your_secret_key

# 数据库配置（如使用）
DATABASE_URL=your_database_url

# 第三方服务配置
OPENAI_API_KEY=your_openai_key
\`\`\`

## 自定义配置

### 修改主题色彩

编辑 `app/globals.css` 中的 CSS 变量:

\`\`\`css
:root {
  --primary: 222.2 47.4% 11.2%;
  --primary-foreground: 210 40% 98%;
  /* 其他颜色变量 */
}
\`\`\`

### 添加新的数据源

在 `components/platform-selector.tsx` 中添加新的平台选项。

### 扩展游戏黑话库

在 `components/game-slang-knowledge-base.tsx` 中添加新的术语分类和数据。

## 性能优化

- 使用 Next.js 14 App Router 实现服务端渲染
- 组件级别的代码分割
- 图片优化和懒加载
- Tailwind CSS 的 JIT 编译

## 浏览器支持

- Chrome (推荐)
- Firefox
- Safari
- Edge

## 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 联系方式

如有问题或建议，请通过以下方式联系:

- 项目 Issues: [GitHub Issues](https://github.com/your-username/ubi-sentiment-analysis/issues)
- 邮箱: your-email@example.com

## 更新日志

### v1.0.0 (2025-01-06)
- 🎉 初始版本发布
- ✨ 完整的舆情分析功能
- 🎮 游戏黑话知识库
- 📊 数据可视化图表
- 📋 智能报告生成
\`\`\`

现在这个项目已经完全配置好，可以直接在 Vercel 上部署了。主要改进包括：

1. **完整的 Next.js 配置**: 添加了所有必要的配置文件
2. **类型安全**: 修复了所有 TypeScript 类型错误
3. **Vercel 优化**: 配置了 `vercel.json` 和正确的构建设置
4. **依赖管理**: 完整的 `package.json` 包含所有必要依赖
5. **样式系统**: 完整的 Tailwind CSS 配置
6. **项目文档**: 详细的 README 文件

您可以通过以下方式部署：

1. **GitHub + Vercel**: 将代码推送到 GitHub，然后在 Vercel 中导入项目
2. **Vercel CLI**: 使用 `vercel` 命令直接部署
3. **一键部署**: 使用 Vercel 的一键部署按钮

所有组件都已经优化为生产就绪状态，包括响应式设计、无障碍支持和性能优化。
