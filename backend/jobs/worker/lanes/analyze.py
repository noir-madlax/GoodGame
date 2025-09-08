from jobs.worker.lanes.base import BaseLane


class AnalyzeLane(BaseLane):
    name = "analyze"

    def claim_and_submit_batch(self) -> int:
        # TODO: 从 posts 中占坑 analysis_status='ready_to_analyze' 的记录为 'running_analyze'，提交线程池
        return super().claim_and_submit_batch()

    def _run_one(self, item) -> None:
        # TODO: 执行视频+评论分析，写入 analysis_results；成功置为 'analyzed'
        super()._run_one(item)

