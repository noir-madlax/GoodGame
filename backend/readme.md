## 运行定时任务
在 backend 目录下，先激活虚拟环境，再用 -m 运行模块：
cd backend
source .venv/bin/activate
python -m jobs.scheduler.search_job

## 运行初筛
请在项目根目录或 backend 目录下按模块方式运行，并确保先激活 backend 的虚拟环境。

运行单条初筛（推荐）
cd backend
source .venv/bin/activate
python -m analysis.cli run-one --id 139

运行批处理（unknown 的候选）
cd backend
source .venv/bin/activate
python -m analysis.cli run --limit 5 --offset 0

## 运行评论爬取
- 在 backend 目录运行
  - cd backend
  - source .venv/bin/activate
  - python -m jobs.worker.lanes.comments --id 108

## 运行分析
cd backend
source .venv/bin/activate
python -m analysis.cli analyze --id 292