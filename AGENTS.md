# GoodGame 项目 AI Agent 指南

本文档为 AI 编程助手提供项目上下文和开发指导，帮助 AI Agent 更好地理解和协作开发 GoodGame 项目。

## 项目概述

GoodGame 是一个社交媒体内容分析平台，用于从抖音、小红书等平台抓取、分析和管理内容。

### 技术栈
- **前端**: React + TypeScript + Vite, TailwindCSS, shadcn/ui, React Router
- **后端**: Python 3.10+, FastAPI, 多线程任务系统
- **数据库**: Supabase Postgres (项目: GoodGame, ID: kctuxiejpwykosghunib)
- **外部 API**: TikHub API, OpenRouter, Gemini
- **包管理**: 前端使用 pnpm, 后端使用 uv (虚拟环境)

### 项目结构
```
GoodGame/
├── frontend/          # React + Vite 前端应用
│   ├── src/
│   │   ├── polymet/   # 主要业务组件和页面
│   │   ├── components/ # 通用 UI 组件
│   │   └── lib/       # 工具函数和客户端
│   └── public/
├── backend/           # Python 后端服务
│   ├── api/           # FastAPI 路由和服务器
│   ├── jobs/          # 定时任务和工作队列
│   ├── analysis/      # 内容分析和初筛逻辑
│   ├── tikhub_api/    # 数据抓取和 ORM
│   └── test/          # 测试工具和沙盒
├── tikhub/            # TikHub API 脚本工具
└── whisper/           # 语音转文字工具

```

## 开发环境设置

### 前端开发

**前置条件**: Node.js (LTS) + pnpm

```bash
# 进入前端目录
cd frontend

# 安装依赖
pnpm install

# 启动开发服务器 (支持 HMR)
pnpm dev

# 构建生产版本
pnpm build

# 运行 linter
pnpm lint
```

**重要提示**:
- 始终使用 `pnpm dev` 进行开发，**不要**在开发过程中运行 `pnpm build`
- 生产构建会禁用热重载，应在开发流程之外执行
- 前端使用 React Router 的 HashRouter 模式

### 后端开发

**前置条件**: Python 3.10+

```bash
# 进入后端目录
cd backend

# 激活 uv 虚拟环境 (必须先执行)
source .venv/bin/activate

# 安装依赖 (如需要)
pip install -r requirements.txt

# 运行主服务 (包含 API、调度器、工作队列)
python start.py

# 运行特定模块 (示例)
python -m analysis.cli run --limit 5
python -m jobs.worker.lanes.comments --id 108
```

**重要提示**:
- 所有 Python 命令必须在激活虚拟环境后执行
- 使用 `-m` 模块方式运行，而非直接执行脚本
- 后端采用多线程架构，可通过环境变量控制启用的组件

### 环境变量配置

在 `backend/.env` 文件中配置以下变量：

```bash
# Supabase
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# API Keys
OPENROUTER_API_KEY=your_openrouter_key
GEMINI_API_KEY_ANALYZE=your_gemini_key
tikhub_API_KEY=your_tikhub_key

# 可选配置
OPENROUTER_MODEL=openai/gpt-4o-mini
ENABLE_SCHEDULER=true
ENABLE_WORKER=true
ENABLE_API=true
```

## 核心功能模块

### 1. 内容抓取 (backend/tikhub_api)
- 从抖音、小红书等平台抓取视频和评论数据
- 使用 TikHub API 进行数据获取
- 支持批量下载和增量更新

### 2. 内容分析 (backend/analysis)
- 使用启发式规则和 LLM 进行内容价值初筛
- 支持批量处理和单条处理模式
- 分析状态: `init` → `no_value` / `pending` → `analyzed`

### 3. 任务系统 (backend/jobs)
- **调度器**: 定时搜索和数据更新任务
- **工作队列**: 多 lane 并发处理 (评估、评论、分析、作者)
- **API 服务**: FastAPI REST 接口

### 4. 前端界面 (frontend/src/polymet)
- **内容仪表板**: 展示和筛选平台内容
- **标记与处理**: 内容标记和批量操作
- **详情页**: 视频分析详情和评论展示
- **搜索设置**: 内容检索和过滤配置

## 测试指南

### 前端测试
```bash
cd frontend

# 运行测试 (使用 Vitest)
pnpm test

# 运行测试并生成覆盖率报告
pnpm test --coverage
```

**测试约定**:
- 测试文件使用 `.test.ts(x)` 后缀
- 使用 React Testing Library 进行组件测试
- Mock 网络请求，避免调用真实外部服务
- 验证可访问性属性和键盘交互

### 后端测试
```bash
cd backend
source .venv/bin/activate

# 运行测试 (使用 pytest)
pytest -q

# 运行测试并生成覆盖率报告
pytest --cov
```

**测试约定**:
- 测试文件使用 `.test.py` 后缀或放在 `tests/` 目录
- 使用 fixtures 进行通用设置
- 优先使用 JSON fixtures，避免网络调用
- 单元测试使用 stubbed repositories，集成测试才使用真实数据库

**覆盖率目标**: 前端和后端核心模块均应达到 70%+ 的语句/分支覆盖率

## 常用命令速查

### 后端常用操作

```bash
# 激活虚拟环境 (所有操作的前提)
cd backend && source .venv/bin/activate

# 运行定时任务
python -m jobs.scheduler.search_job

# 运行内容初筛 (单条)
python -m analysis.cli run-one --id 139

# 运行内容初筛 (批量)
python -m analysis.cli run --limit 5 --offset 0

# 运行评论爬取
python -m jobs.worker.lanes.comments --id 108

# 运行内容分析
python -m analysis.cli analyze --id 292

# 获取作者信息
python -c "from jobs.worker.lanes.author import run_once_by_id; run_once_by_id(4389)"

# 启动完整后端服务
python start.py
```

### 前端常用操作

```bash
cd frontend

# 开发模式 (推荐)
pnpm dev

# 类型检查
pnpm tsc

# Linting
pnpm lint

# 构建 (仅在需要时)
pnpm build
```

## 代码规范

### 通用原则
- 测试是产品质量的一部分，不是可选项
- 优先编写快速、确定性、隔离的测试
- 测试行为和契约，而非实现细节
- 在风险最高的地方追求有意义的覆盖率

### 前端规范
- 使用 TypeScript 严格模式
- 组件使用函数式组件和 Hooks
- 遵循 shadcn/ui 组件库的设计模式
- 使用 TailwindCSS 进行样式管理
- API 调用统一通过 `lib/supabase.ts` 客户端

### 后端规范
- 所有数据库操作通过 ORM 层 (`backend/tikhub_api/orm`)
- 使用类型提示 (type hints)
- 模块化设计，避免循环依赖
- 日志使用标准 logging 模块
- 异步任务使用队列系统，避免阻塞

## 数据库访问规则

### MCP 和 Supabase
- **读取**: 允许通过 MCP 进行验证性读取
- **写入**: AI 对 Supabase 的任何修改操作需要明确的人工指令
- **测试**: 单元测试优先使用 stubbed repositories，仅在批准的集成测试中使用真实数据库

### 主要数据表
- `gg_platform_post`: 平台内容帖子
- `gg_platform_comment`: 评论数据
- `gg_platform_author`: 作者信息
- `gg_search_task`: 搜索任务
- `gg_job_queue`: 任务队列

## Pull Request 规范

### 提交前检查清单
- [ ] 前端: 运行 `pnpm lint` 和 `pnpm build` 成功
- [ ] 后端: 运行 `pytest` 通过
- [ ] 新功能包含测试或有明确的不需要测试的理由
- [ ] Bug 修复包含回归测试
- [ ] 代码遵循项目规范
- [ ] 更新相关文档 (如有必要)

### PR 标题格式
- `[frontend] 功能描述` - 前端相关
- `[backend] 功能描述` - 后端相关
- `[tikhub] 功能描述` - TikHub 工具相关
- `[docs] 文档更新` - 文档相关

## 故障排查

### 前端问题

**问题**: HMR 不工作
- **解决**: 确保使用 `pnpm dev` 而非 `pnpm build`，重启开发服务器

**问题**: 依赖安装失败
- **解决**: 删除 `node_modules` 和 `pnpm-lock.yaml`，重新运行 `pnpm install`

### 后端问题

**问题**: 找不到模块
- **解决**: 确保已激活虚拟环境 `source .venv/bin/activate`，使用 `-m` 模块方式运行

**问题**: OPENROUTER_API_KEY 未找到
- **解决**: 检查 `backend/.env` 文件是否存在且包含正确的 API key

**问题**: Supabase 认证失败
- **解决**: 确保 `.env` 中的 `SUPABASE_URL` 和 `SUPABASE_KEY` 正确

**问题**: 数据库连接超时
- **解决**: 检查网络连接，验证 Supabase 项目状态

## 部署

### 后端部署 (Docker)
```bash
cd backend

# 构建镜像
docker build -t goodgame-backend -f Dockerfile ..

# 使用 docker-compose 运行
docker-compose up -d
```

**环境变量**: 生产环境通过 Portainer 注入，参见 `backend/docker-compose.yml`

### 前端部署
- 构建: `pnpm build`
- 输出目录: `dist/`
- 可部署到 Vercel、Netlify 等静态托管服务

## 参考资源

- [项目架构文档](.cursor/rules/@rules/project-arch.md)
- [开发指南](.cursor/rules/@rules/dev-guide.md)
- [测试规范](.cursor/rules/@rules/test-rules.md)
- [后端 README](backend/readme.md)
- [前端 README](frontend/README.md)
- [分析模块文档](backend/analysis/README.md)
- [TikHub 工具文档](tikhub/README.md)

---

**最后更新**: 2025-10-28  
**维护者**: GoodGame 开发团队

遵循这些指南将帮助 AI Agent 更高效地协助开发，保持代码质量和项目一致性。

