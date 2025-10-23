"""
Author 获取与保存服务

功能：传入 post_id，从 ORM 获取 PlatformPost，读取其 author_id，
调用对应平台的 fetcher.get_author() 获取 Author 对象，并通过 AuthorRepository 保存到数据库。

注意：失败或成功都会更新 PlatformPost.author_fetch_status 字段（AuthorFetchStatus）。
"""
from typing import Optional

from jobs.logger import get_logger

from tikhub_api.orm import PostRepository, AuthorRepository, AuthorFetchStatus, Author, RelevantStatus
from tikhub_api.fetchers import FetcherFactory

log = get_logger(__name__)


def fetch_and_save_author_by_post_id(post_id: int) -> Optional["Author"]:
    """
    传入 post_id：
    1) 从 ORM 读取 PlatformPost
    2) 读取 post.author_id，选择平台对应的 fetcher
    3) 调用 fetcher.get_author(author_id) 获取 Author
    4) 使用 AuthorRepository.upsert_author 保存并返回保存后的 Author
    5) 成功则将 author_fetch_status 更新为 SUCCESS，失败则更新为 FAILED

    返回：Author 或 None
    """
    try:
        if not isinstance(post_id, int) or post_id <= 0:
            raise ValueError("post_id 必须为正整数")

        post = PostRepository.get_by_id(post_id)
        if not post:
            log.warning("未找到帖子：post_id=%s", post_id)
            return None

        platform = getattr(post, "platform", None)
        author_id = getattr(post, "author_id", None)

        if not author_id:
            log.warning("帖子无 author_id：post_id=%s, platform=%s", post_id, platform)
            # 标记失败
            PostRepository.update_author_fetch_status(post_id, AuthorFetchStatus.FAILED.value)
            return None

        # 使用工厂创建 fetcher（platform 可能是字符串或枚举，统一取其 value 或 str）
        try:
            plat_str = getattr(platform, "value", str(platform))
            fetcher = FetcherFactory.create_fetcher(plat_str)
        except Exception as _e:
            log.warning("创建 fetcher 失败：platform=%s, err=%s", platform, _e)
            PostRepository.update_author_fetch_status(post_id, AuthorFetchStatus.FAILED.value)
            return None

        author = fetcher.get_author(str(author_id))
        if not author:
            log.warning("get_author 返回空：post_id=%s, platform=%s, author_id=%s", post_id, platform, author_id)
            PostRepository.update_author_fetch_status(post_id, AuthorFetchStatus.FAILED.value)
            return None

        saved = AuthorRepository.upsert_author(author)
        # 标记成功
        PostRepository.update_author_fetch_status(post_id, AuthorFetchStatus.SUCCESS.value)
        log.info("作者信息已保存：post_id=%s, platform=%s, author_id=%s", post_id, platform, author_id)
        return saved
    except Exception as e:
        log.error("fetch_and_save_author_by_post_id 失败：%s", e)
        # 标记失败
        try:
            PostRepository.update_author_fetch_status(post_id, AuthorFetchStatus.FAILED.value)
        except Exception:
            pass
        return None




def list_posts_with_author_not_fetched(limit: int = 50) -> list["PlatformPost"]:
    """
    按作者获取状态=未获取(not_fetched) 且相关性状态为 YES 或 MAYBE 查询帖子列表。
    Args:
        limit: 需要的条数
    Returns:
        PlatformPost 列表
    """
    try:
        if not isinstance(limit, int) or limit <= 0:
            limit = 50
        return PostRepository.list_by_author_fetch_status(
            status=AuthorFetchStatus.NOT_FETCHED.value,
            limit=limit,
            offset=0,
            relevant_status=[RelevantStatus.YES.value, RelevantStatus.MAYBE.value],
        )
    except Exception as e:
        log.error("list_posts_with_author_not_fetched 失败：%s", e)
        return []
