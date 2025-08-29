# analysis 目录使用指南

本目录实现了“对 gg_platform_post 帖子进行分析价值初筛”的逻辑：
- 先用本地启发式规则做快速筛除（明显无价值 → 直接 no_value）
- 再调用 OpenRouter 上的轻量模型做二分类（有价值 → pending；无价值 → no_value）
- 不占坑：不会把 init 改为处理中状态，仅在判定后写回 pending/no_value
- 所有数据库交互均通过 orm 层（backend/tikhub_api/orm）完成

## 目录结构

- openrouter_client.py：OpenRouter API 调用封装，统一返回 JSON
- text_builder.py：将帖子信息构造成 LLM 输入的结构化文本与提示词
- heuristics.py：启发式预筛规则（阈值、关键词）
- screening_service.py：主服务，整合筛选与状态回写
- cli.py：命令行入口

## 前置条件

1) 激活后端虚拟环境（uv 虚拟环境）

```bash
cd backend
source .venv/bin/activate
```

2) 环境变量

- Supabase（orm/supabase_client.py 会自动加载最近的 .env）
  - SUPABASE_URL
  - SUPABASE_KEY
- OpenRouter（openrouter_client.py 会先 find_dotenv()，再尝试加载 backend/.env）
  - OPENROUTER_API_KEY
  - 可选：OPENROUTER_MODEL（默认 openai/gpt-4o-mini）

建议将上述变量写入 backend/.env。

3) 数据库列要求

- gg_platform_post.analysis_status 列（TEXT，默认 'init'，CHECK 限制取值：'init','no_value','pending','analyzed'）

## 快速开始

在虚拟环境中执行（默认每次处理 5 条 init 帖子）：

```bash
python -m backend.analysis.cli run --limit 5
```

可选参数：
- --offset：偏移量，默认 0
- --model：OpenRouter 模型名，默认读取 OPENROUTER_MODEL 或使用 openai/gpt-4o-mini

## 工作流程

1) 从 DB 读取 analysis_status='init' 的帖子（PostRepository.list_by_status）
2) 启发式预筛（heuristics.obviously_no_value）：
   - 低互动且命中低价值关键词 → 直接判定 no_value
3) 若未被预筛，构造结构化文本（text_builder.build_user_msg），调用 LLM（openrouter_client.OpenRouterClient.classify_value）
4) 解析 LLM 的 JSON 返回，读取 suggested_status：
   - 'pending' → 写回 pending
   - 'no_value' → 写回 no_value
5) 每条处理后打印日志（含 LLM 原样返回结果、最终写回状态）

## 日志与结果解释

- LLM 响应中要求包含：
  - has_value: boolean
  - reason: 简短理由（<=80字）
  - explanation: 1-3 句中文说明（命中了哪些线索，如品牌、情绪、风险、互动阈值等）
  - signals: string[]（理由标签）
  - confidence: 0-1
  - suggested_status: 'pending' | 'no_value'
- screening_service.py 会将 result 原样打印，便于人工审阅；也会打印每条的 updated_status。

## 配置与调整

- 启发式阈值（heuristics.py）：
  - MIN_PLAY / MIN_LIKE / MIN_COMMENT，及 LOW_VALUE_KEYWORDS
- 模型选择：
  - 通过环境变量 OPENROUTER_MODEL 或 CLI 的 --model 指定
- 批大小：
  - 通过 CLI 的 --limit 控制

## 常见问题（FAQ）

1) 提示找不到 OPENROUTER_API_KEY？
   - 确保 backend/.env 中已设置 OPENROUTER_API_KEY，并已激活 backend/.venv 环境。
   - openrouter_client.py 会通过 find_dotenv() 与 backend/.env 两条路径加载。

2) Supabase 认证失败？
   - 确保 SUPABASE_URL、SUPABASE_KEY 在 .env 中，且 orm/supabase_client.py 能读取（其使用 find_dotenv 自动加载）。

3) 想看到更详细日志或落库？
   - 目前使用 print 输出。若需落文件或建审计表，可扩展 logging 或新增 gg_post_screening_log 表。

## 约束与注意事项

- 本流程仅做“是否进入深度分析”的初筛，不做详细内容抽取。
- 请合理控制 --limit 以避免调用成本失控；建议从小批量开始。
- 状态流转：init →（预筛/LLM）→ pending/no_value；深度分析完成后由后续流程将 pending → analyzed。

## 示例

```bash
# 处理 10 条
python -m backend.analysis.cli run --limit 10

# 指定模型
OPENROUTER_MODEL=anthropic/claude-3.5-haiku python -m backend.analysis.cli run --limit 5
```

