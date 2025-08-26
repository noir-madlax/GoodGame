## 使用说明概览
本说明介绍如何使用 backend/tikhub_api/workflow.py 执行“下载视频 + 同步落库（详情/评论/弹幕）”操作，并根据需要选择性开启各步骤。

默认行为：一次性执行“同步详情并入库 → 同步评论 → 同步弹幕 → 下载视频”。

默认下载根目录常量如下（可按需修改）：
````python path=backend/tikhub_api/workflow.py mode=EXCERPT
DEFAULT_BASE_DOWNLOAD_DIR = "downloads"
````

---

## 前置准备
- 进入 backend 目录并激活虚拟环境
  - macOS/Linux:
    - cd backend
    - source .venv/bin/activate
- 确保数据库/服务相关环境变量已正确配置（用于 PostRepository/CommentRepository 等落库操作）
- 当前已支持平台列表可在运行时打印或查看 get_supported_platforms()

---

## 方式一：直接运行示例脚本
适合快速验证全流程

- 激活虚拟环境后运行：
  - python ./tikhub_api/workflow.py
- 说明：
  - 脚本会执行 main 中的示例，使用写死的 aweme_id 跑完整工作流（详情+评论+弹幕+下载）
  - 想换成你自己的视频 ID，可编辑 workflow.py 的 main 函数里对应的 video_id

---

## 方式二：在命令行一行式调用（指定视频 ID）
无需编辑文件，直接传入你的 ID，执行全流程

- Douyin 全流程（默认四步全开）
  - python -c "from tikhub_api.workflow import run_video_workflow; r=run_video_workflow('douyin','你的视频ID'); print(r.file_path, r.post_id, r.steps)"

返回说明：
- r.file_path：下载成功的视频文件路径（若未开启下载或下载失败则为 None）
- r.post_id：视频详情入库后的主键 ID（用于评论落库）
- r.steps：每一步的执行结果字典，含 ok/skipped/error/output 等字段

---

## 方式三：在你的 Python 代码中调用（可选择性开启步骤）
通过 WorkflowOptions 控制要执行的步骤

- 导入
  - from tikhub_api.workflow import run_video_workflow, WorkflowOptions

- 全流程（默认行为）
  - report = run_video_workflow('douyin', '你的视频ID')

- 只下载视频（不落库详情/评论/弹幕）
  - report = run_video_workflow('douyin', '你的视频ID', options=WorkflowOptions(
      sync_details=False,
      sync_comments=False,
      sync_danmaku=False,
      download_video=True,
    ))

- 只同步详情并入库（不评论、不弹幕、不下载）
  - report = run_video_workflow('douyin', '你的视频ID', options=WorkflowOptions(
      sync_details=True,
      sync_comments=False,
      sync_danmaku=False,
      download_video=False,
    ))

- 同步详情+评论，且不下载、不弹幕
  - report = run_video_workflow('douyin', '你的视频ID', options=WorkflowOptions(
      sync_details=True,
      sync_comments=True,
      sync_danmaku=False,
      download_video=False,
    ))

- 只同步弹幕（平台需支持弹幕能力）
  - report = run_video_workflow('douyin', '你的视频ID', options=WorkflowOptions(
      sync_details=False,
      sync_comments=False,
      sync_danmaku=True,
      download_video=False,
    ))

备注：
- 评论同步依赖 post_id（即先完成“详情入库”），因此在只评论的场景建议保持 sync_details=True。
- WorkflowOptions 还包含 page_size、force_refresh（已预留但当前默认不做存在即跳过逻辑，保持原始行为）。

---

## 下载产物与目录结构
- 默认保存位置：downloads/{platform}/{video_id}/
  - {video_id}.mp4（下载的视频）
  - danmaku.json（弹幕；仅在支持且开启弹幕步骤时保存）
- 如需修改根目录，请调整 DEFAULT_BASE_DOWNLOAD_DIR 常量

---

## 便捷函数（可选）
如果你只需要“抖音全流程”的默认调用，可以用：
- from tikhub_api.workflow import run_douyin_full_workflow
- report = run_douyin_full_workflow('你的视频ID')

（如不需要此便捷函数，可以忽略）

---

## 常见排查
- ImportError 或运行报错：确认已 cd 到 backend 且已 source .venv/bin/activate
- 评论或弹幕为空：可能是平台接口限制或该视频本身无数据；不影响其它步骤
- 落库失败：检查数据库连接配置是否正确

如需我把默认下载目录从 downloads 改成你指定的目录，或补充环境变量配置说明，告诉我你的偏好即可。
