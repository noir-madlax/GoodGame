import threading
from jobs.worker.lanes.base import BaseLane
from jobs.logger import get_logger

from services.author_service import (
    list_posts_with_author_not_fetched,
    fetch_and_save_author_by_post_id,
)
from tikhub_api.orm.post_repository import PostRepository
from tikhub_api.orm import AuthorRepository, AuthorFetchStatus
from common.request_context import set_project_id, reset_project_id

log = get_logger(__name__)


class AuthorLane(BaseLane):
    name = "author"

    def __init__(self, settings, executor):
        super().__init__(settings, executor)
        self._busy = False
        self._lock = threading.Lock()

    def claim_and_submit_batch(self) -> int:
        with self._lock:
            if self._busy:
                log.debug("[AuthorLane] busy, skipping this round")
                return 0

            posts = list_posts_with_author_not_fetched(limit=1)
            if not posts:
                log.debug("[AuthorLane] no candidate (author_fetch_status=not_fetched)")
                return 0

            post = posts[0]
            post_id = post.id
            if not post_id:
                log.debug("[AuthorLane] candidate missing id, skip")
                return 0

            # 提交前：若作者已存在，则回写状态为 SUCCESS 并跳过提交
            platform_str = post.platform
            platform_author_id = post.author_id
            if platform_author_id:
                existing = AuthorRepository.get_by_platform_author(platform_str, str(platform_author_id))
                if existing:
                    PostRepository.update_author_fetch_status(int(post_id), AuthorFetchStatus.SUCCESS.value)
                    log.info(
                        "[AuthorLane] author already exists, mark success and skip: post_id=%s platform=%s author_id=%s",
                        post_id,
                        platform_str,
                        platform_author_id,
                    )
                    return 0
   
            self._busy = True
            self.executor.submit(self._run_one_wrapper, int(post_id))
            log.info("[AuthorLane] submitted 1 task, marked as busy: post_id=%s", post_id)
            return 1

    def _run_one_wrapper(self, post_id: int) -> None:
        try:
            self._run_one(post_id)
        finally:
            with self._lock:
                self._busy = False
                log.info("[AuthorLane] task completed, marked as not busy")

    def _run_one(self, post_id: int) -> None:
        token = None
        try:
            log.info("[AuthorLane] processing post_id: %s", post_id)
            # 注入项目上下文（若存在）
            post = PostRepository.get_by_id(int(post_id))
            pid = getattr(post, "project_id", None) if post else None
            if pid:
                token = set_project_id(str(pid))

            saved = fetch_and_save_author_by_post_id(int(post_id))
            if saved:
                log.info(
                    "[AuthorLane] author saved: post_id=%s platform_author_id=%s nickname=%s",
                    post_id,
                    getattr(saved, "platform_author_id", None),
                    getattr(saved, "nickname", None),
                )
            else:
                log.info("[AuthorLane] author save failed or skipped: post_id=%s", post_id)
        except Exception as e:
            log.exception("[AuthorLane] run_one failed: %s", e)
        finally:
            if token:
                reset_project_id(token)


def run_once_by_id(post_id: int) -> None:
    """单次执行：按 post_id 获取并保存作者信息（封装 service 方法）。"""
    saved = fetch_and_save_author_by_post_id(int(post_id))
    if saved:
        log.info("[AuthorLane] run_once_by_id ok: post_id=%s", post_id)
    else:
        log.info("[AuthorLane] run_once_by_id finished with failure: post_id=%s", post_id)

