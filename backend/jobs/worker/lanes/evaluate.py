from jobs.worker.lanes.base import BaseLane


class EvaluateLane(BaseLane):
    name = "evaluate"

    def claim_and_submit_batch(self) -> int:
        # TODO: 从 posts 中占坑 analysis_status='init' 的记录为 'running_eval'，提交线程池
        return super().claim_and_submit_batch()

    def _run_one(self, item) -> None:
        # TODO: 计算 value_score 与 value_reason；根据阈值回写 'pending' 或 'no_value'
        super()._run_one(item)

