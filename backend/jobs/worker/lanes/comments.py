from jobs.worker.lanes.base import BaseLane


class CommentsLane(BaseLane):
    name = "comments"

    def claim_and_submit_batch(self) -> int:
        # TODO: 从 posts 中占坑 analysis_status='pending' 的记录为 'running_comments'，提交线程池
        return super().claim_and_submit_batch()

    def _run_one(self, item) -> None:
        # TODO: 复用 tikhub_api.workflow 的 _step_sync_comments / run_video_workflow 进行评论抓取
        # 成功则置为 'ready_to_analyze'，失败回滚并重试
        super()._run_one(item)

