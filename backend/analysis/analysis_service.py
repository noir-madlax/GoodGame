from __future__ import annotations
from typing import Any, Dict, Optional, List, Tuple
import requests

from jobs.logger import get_logger
from jobs.config import Settings


from .gemini_client import GeminiClient
from .analysis_prompt_builder import get_system_prompt

from tikhub_api.orm.post_repository import PostRepository
from tikhub_api.orm.models import PlatformPost
from tikhub_api.orm.video_analysis_repository import VideoAnalysisRepository
from tikhub_api.orm.comment_repository import CommentRepository
from tikhub_api.video_downloader import VideoDownloader
from tikhub_api.fetchers import create_fetcher


try:
    from google.genai import types  # type: ignore
except Exception:  # pragma: no cover
    types = None  # type: ignore

log = get_logger(__name__)


class AnalysisService:
    """
    串联：Post -> 下载字节流 -> Gemini 上传 -> 生成内容 -> 保存分析结果

    支持的内容类型：
    - 视频（VIDEO）：下载视频并上传到 Gemini
    - 图文（PICTURE）：下载多张图片并上传到 Gemini
    - 评论：获取帖子评论并以 JSON 格式添加到分析内容中
    """

    def __init__(self, gemini_client: Optional[GeminiClient] = None) -> None:
        self.gemini = gemini_client or GeminiClient(api_key=Settings.from_env().GEMINI_API_KEY_ANALYZE)
        self.downloader = VideoDownloader()

    def analyze_post(self, post_id: int) -> Dict[str, Any]:
        from tikhub_api.orm.enums import AnalysisStatus, PostType, PromptName
        log.info(f"开始处理帖子 post_id={post_id}：准备读取帖子信息")
        try:
            post = self._get_post(post_id)

            # 1) 创建平台 fetcher 并按类型准备 contents（视频/图文）
            try:
                fetcher = create_fetcher(str(post.platform))
            except Exception as e:
                log.error(
                    f"创建 fetcher 失败：post_id={post_id}, platform={getattr(post, 'platform', None)}, err={e}"
                )
                raise

            # 1) 构建完整的 contents（包含文本和媒体）
            full_parts, source_key = self._build_full_contents(post, fetcher)

            if types is None:
                raise RuntimeError("google-genai SDK 未正确安装")

            # 2) 构建 prompt 与调用 generate_content（公共逻辑）
            log.info(f"开始调用 Gemini 生成内容：post_id={post_id}")
            prompt_name = PromptName.ANALYZE_VIDEO if post.post_type == PostType.VIDEO else PromptName.ANALYZE_PICTURE
            system_prompt = get_system_prompt(prompt_name,post.project_id)
            config = types.GenerateContentConfig(
                temperature=0.3,
                response_mime_type="application/json",
                system_instruction=system_prompt,
            )

            resp = self.gemini.client.models.generate_content(
                model=self.gemini.analysis_model,
                contents=full_parts,
                config=config,
            )
            # 打印大模型的原始返回，便于排查
            try:
                text_raw = getattr(resp, "text", None) or getattr(resp, "output_text", None)
                log.info(f"Gemini 返回文本：{text_raw}")
                cands = getattr(resp, "candidates", None)
                if cands is not None:
                    log.info(f"Gemini 返回候选数：{len(cands)}")
            except Exception as _e:
                log.info(f"打印模型返回文本失败：{_e}")

            log.info(
                f"生成完成：post_id={post_id}，model={getattr(resp, 'model_version', self.gemini.analysis_model)}"
            )

            text = getattr(resp, "text", None) or getattr(resp, "output_text", None)
            result: Dict[str, Any]
            if text:
                try:
                    import json
                    result = json.loads(text)
                except Exception:
                    result = {"raw_text": text}
            else:
                # 兜底：尽量序列化 resp
                def _to_jsonable(obj):
                    if obj is None or isinstance(obj, (str, int, float, bool)):
                        return obj
                    try:
                        import json
                        json.dumps(obj)
                        return obj
                    except Exception:
                        pass
                    try:
                        return obj.__dict__
                    except Exception:
                        return str(obj)
                result = {"raw_response": _to_jsonable(resp)}

            # 3) 字段映射并保存（source_path 使用上传完成后的文件/图片集合 URI 串）
            source_path = source_key or f"post:{post.id}"
            payload = self._map_result_to_video_analysis(post, result, source_path=source_path, system_prompt=system_prompt)
            saved = VideoAnalysisRepository.upsert(payload)

            # 标记分析完成
            try:
                PostRepository.update_analysis_status(post_id, AnalysisStatus.ANALYZED.value)
                log.info(f"分析成功，已更新状态为 ANALYZED：post_id={post_id}")
            except Exception as ue:
                log.exception("更新 ANALYZED 状态失败：post_id=%s, err=%s", post_id, ue)

            # 返回可 JSON 序列化的结果（避免 datetime 等导致 json.dumps 失败）
            try:
                if hasattr(saved, "model_dump"):
                    return saved.model_dump(mode="json", exclude_none=True)  # pydantic v2
            except Exception:
                pass
            return payload
        except Exception as e:
            try:
                PostRepository.update_analysis_status(post_id, AnalysisStatus.ANALYSIS_FAILED.value)
                log.error(
                    f"分析失败，已更新状态为 ANALYSIS_FAILED：post_id={post_id}, err={e}"
                )
            except Exception as ue:
                log.exception("更新 ANALYSIS_FAILED 状态失败：post_id=%s, err=%s", post_id, ue)
            raise

    def _build_full_contents(self, post: PlatformPost, fetcher, include_comments: bool = True, max_comments: int = 100) -> Tuple[List[Any], str]:
        """
        构建完整的 contents，包含：
        1. 帖子标题（如果有）
        2. 帖子内容（如果有）
        3. 媒体类型标注
        4. 媒体 Parts（视频或图片）
        5. 评论数据（如果 include_comments=True）

        参数:
            post: 帖子对象
            fetcher: 平台 fetcher
            include_comments: 是否包含评论，默认 True
            max_comments: 最大评论数量，默认 100

        返回:
            (full_parts, source_key)
        """
        from tikhub_api.orm.enums import PostType

        if types is None:
            raise RuntimeError("google-genai SDK 未正确安装")

        # 根据帖子类型准备媒体 Parts
        if post.post_type == PostType.VIDEO:
            media_parts, source_key = self._prepare_video_parts(post, fetcher)
        else:
            # 默认按图文处理
            media_parts, source_key = self._prepare_image_parts(post, fetcher)

        # 构建最终 contents 顺序：Title -> Content -> Media 标注 -> 媒体 Parts
        full_parts: List[Any] = []

        # 添加标题
        title_text = getattr(post, "title", None)
        if title_text:
            full_parts.append(types.Part(text=f"[Post Title]\n{str(title_text)}"))

        # 添加内容
        content_text = getattr(post, "content", None)
        if content_text:
            full_parts.append(types.Part(text=f"[Post Content]\n{str(content_text)}"))

        # 添加媒体类型标注
        if post.post_type == PostType.VIDEO:
            full_parts.append(types.Part(text="[Media] Video file attached below."))
        else:
            try:
                full_parts.append(types.Part(text=f"[Media] Images attached below. Count={len(media_parts)}"))
            except Exception:
                full_parts.append(types.Part(text="[Media] Images attached below."))

        # 添加媒体 Parts
        full_parts.extend(media_parts)

        # 添加评论（如果启用）
        if include_comments:
            try:
                comment_parts = self._prepare_comment_parts(post.id, max_comments=max_comments)
                if comment_parts:
                    # 添加评论引导文本
                    full_parts.append(types.Part(
                        text="以下是与该视频对应的评论数据，请一并纳入分析，并在 events 中标注来源 source=video 或 source=comment。"
                    ))
                    # 添加评论 Parts
                    full_parts.extend(comment_parts)
                    log.info(f"已添加评论到 contents：post_id={post.id}，评论 Parts 数={len(comment_parts)}")
                else:
                    log.info(f"没有评论需要添加：post_id={post.id}")
            except Exception as e:
                log.warning(f"获取评论失败，跳过评论分析：post_id={post.id}，err={e}")

        return full_parts, source_key

    def _prepare_comment_parts(self, post_id: int, max_comments: int = 100) -> List[Any]:
        """
        获取评论并构建评论 Parts

        参数:
            post_id: 帖子ID
            max_comments: 最大评论数量，默认100

        返回:
            List[types.Part]: 包含评论文本的 Parts 列表
        """
        if types is None:
            raise RuntimeError("google-genai SDK 未正确安装")

        # 1. 从 CommentRepository 获取评论
        try:
            comments = CommentRepository.list_by_post(post_id, limit=max_comments)
            log.info(f"获取评论成功：post_id={post_id}，评论数={len(comments)}")
        except Exception as e:
            log.error(f"获取评论失败：post_id={post_id}，err={e}")
            return []

        if not comments:
            log.info(f"该帖子没有评论：post_id={post_id}")
            return []

        # 2. 规范化评论数据格式
        normalized_comments = []
        for comment in comments:
            try:
                normalized = {
                    "id": str(comment.platform_comment_id),
                    "text": str(comment.content),
                }
                # 可选字段
                if comment.author_name:
                    normalized["author"] = str(comment.author_name)
                if comment.like_count is not None:
                    normalized["like_count"] = int(comment.like_count)
                if comment.published_at:
                    normalized["published_at"] = comment.published_at.isoformat()

                normalized_comments.append(normalized)
            except Exception as e:
                log.warning(f"规范化评论失败，跳过该评论：post_id={post_id}，comment_id={getattr(comment, 'id', None)}，err={e}")
                continue

        if not normalized_comments:
            log.warning(f"所有评论规范化失败：post_id={post_id}")
            return []

        # 3. 构建 JSON 格式的评论数据
        import json
        comments_payload = {
            "schema": {
                "id": "string",
                "text": "string",
                "author": "string (optional)",
                "like_count": "int (optional)",
                "published_at": "datetime (optional)"
            },
            "items": normalized_comments
        }

        # 4. 返回 types.Part 列表
        parts: List[Any] = [
            types.Part(text="[COMMENTS_JSON_START]"),
            types.Part(text=json.dumps(comments_payload, ensure_ascii=False)),
            types.Part(text="[COMMENTS_JSON_END]")
        ]

        log.info(f"评论 Parts 构建完成：post_id={post_id}，有效评论数={len(normalized_comments)}")
        return parts

    def _prepare_video_parts(self, post: PlatformPost, fetcher) -> Tuple[List[Any], str]:
        """下载→上传→构建视频 Part，返回 (parts, source_key)。"""
        post_id = int(post.id or 0)
        # 获取下载地址（一定是 URL 列表）
        video_urls: List[str]
        try:
            video_urls = fetcher.get_download_url_by_post_id(post_id) or []
            log.info(f"获取视频下载地址成功：post_id={post_id}，count={len(video_urls)}")
        except Exception as e:
            video_urls = []
            log.error(
                f"获取视频下载地址失败：post_id={post_id}, platform={getattr(post, 'platform', None)}, err={e}"
            )

        if not video_urls:
            raise ValueError(f"post {post_id} 获取下载地址失败")

        # 按顺序尝试下载，每个 URL 至多重试一次
        data: Optional[bytes] = None
        chosen_url: Optional[str] = None
        for idx, u in enumerate(video_urls):
            log.info(f"尝试下载视频：post_id={post_id}，idx={idx}，url={u}")
            data = self.downloader.download_video_as_bytes_with_retry(str(u), max_retries=1)
            if data is not None:
                chosen_url = str(u)
                break
            log.warning(f"下载失败，继续尝试下一个 URL：post_id={post_id}，idx={idx}，url={u}")

        if data is None:
            raise RuntimeError(f"下载视频失败：所有候选 URL 均不可用，count={len(video_urls)}")

        log.info(f"下载完成：post_id={post_id}，选用 URL={chosen_url}，大小={len(data)} 字节")

        # 推断 mime 与 display name
        mime_type = "video/mp4"
        display_name = f"post_{post.id or 'unknown'}.mp4"

        # 上传到 Gemini Files
        log.info(f"开始上传到 Gemini：post_id={post_id}，文件名={display_name}")
        upload = self.gemini.upload_file(data, display_name=display_name, mime_type=mime_type)
        file_uri = upload.get("uri")
        log.info(
            f"上传完成：post_id={post_id}，name={upload.get('name')}，uri={file_uri}"
        )
        if not file_uri:
            raise RuntimeError("Gemini 文件上传未返回 uri")

        if types is None:
            raise RuntimeError("google-genai SDK 未正确安装")
        video_part = types.Part(
            file_data=types.FileData(file_uri=file_uri, mime_type=mime_type),
            video_metadata=types.VideoMetadata(fps=1),
        )
        return [video_part], str(file_uri)

    def _prepare_image_parts(self, post: PlatformPost, fetcher) -> Tuple[List[Any], str]:
        """下载→上传多张图片→构建图片 Parts（可包含文案 Part）。返回 (parts, source_key)。"""
        post_id = int(post.id or 0)
        try:
            image_urls = fetcher.get_image_urls_by_post_id(post_id) or []
        except Exception as e:
            image_urls = []
            log.error(
                f"获取图片 URL 列表失败：post_id={post_id}, platform={getattr(post, 'platform', None)}, err={e}"
            )
        if not image_urls:
            raise ValueError(f"post {post_id} 未获取到图片 URL 列表")

        uploaded: List[Tuple[str, str]] = []  # (uri, mime)
        for idx, url in enumerate(image_urls):
            try:
                r = requests.get(str(url), timeout=30)
                if getattr(r, "status_code", 0) != 200:
                    log.warning(f"下载图片失败：post_id={post_id}，status={getattr(r, 'status_code', None)}，url={url}")
                    continue
                data = r.content
                ctype = r.headers.get("Content-Type") or ""
                mime: str
                url_l = str(url).lower()
                if ctype.startswith("image/"):
                    mime = ctype.split(";")[0].strip()
                elif url_l.endswith(".png"):
                    mime = "image/png"
                elif url_l.endswith(".webp"):
                    mime = "image/webp"
                elif url_l.endswith(".gif"):
                    mime = "image/gif"
                else:
                    mime = "image/jpeg"

                display_name = f"post_{post.id or 'unknown'}_{idx}"
                log.info(
                    f"上传图片到 Gemini：post_id={post_id}，idx={idx}，mime={mime}，url={url}"
                )
                upload = self.gemini.upload_file(data, display_name=display_name, mime_type=mime)
                uri = upload.get("uri")
                if uri:
                    uploaded.append((str(uri), mime))
                    log.info(f"图片上传完成：post_id={post_id}，idx={idx}，uri={uri}")
                else:
                    log.warning(f"图片上传未返回 uri：post_id={post_id}，idx={idx}，url={url}")
            except Exception as ue:
                log.warning(f"图片处理失败：post_id={post_id}，idx={idx}，url={url}，err={ue}")
                continue

        if not uploaded:
            raise RuntimeError("无可用图片可供分析（上传均失败）")

        if types is None:
            raise RuntimeError("google-genai SDK 未正确安装")

        parts: List[Any] = []

        for uri, mime in uploaded:
            parts.append(
                types.Part(
                    file_data=types.FileData(file_uri=str(uri), mime_type=str(mime))
                )
            )

        # Source key：按需求拼接 uri 字符串
        source_key = ",".join([u for (u, _) in uploaded])
        return parts, source_key


    def _get_post(self, post_id: int) -> PlatformPost:
        post = PostRepository.get_by_id(post_id)
        if not post:
            raise ValueError(f"post 不存在: {post_id}")
        return post

    def _map_result_to_video_analysis(self, post: PlatformPost, result: Dict[str, Any], *, source_path: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        将 prompt 的返回结构映射到 gg_video_analysis 的字段。
        根据 suggestion+video+comment-prompt.txt 的输出定义：
        - summary / sentiment / brand / risk_type_total / key_points / events
        - brand_relevance / relevance_evidence
        - handling_suggestions
        其余作为 analysis_detail 存档。

        source_path: 使用已上传文件的 URI（例如 https://.../files/<id>）作为唯一键。
        """
        platform = str(getattr(post, "platform", "douyin") or "douyin")
        platform_item_id = getattr(post, "platform_item_id", None)

        # 基本字段取值
        summary = result.get("summary")
        sentiment = result.get("sentiment")
        brand = result.get("brand")
        timeline = result.get("events")  # events 作为 timeline 存储
        key_points = result.get("key_points")
        risk_types = result.get("risk_type_total")
        brand_relevance = result.get("brand_relevance")
        relevance_evidence = result.get("relevance_evidence")
        handling_suggestions = result.get("handling_suggestions")
        total_risk = result.get("total_risk")
        total_risk_reason = result.get("total_risk_reason")
        transcript_json = result.get("transcript")

        payload: Dict[str, Any] = {
            "source_path": source_path,
            "source_platform": platform,
            "platform_item_id": platform_item_id,
            "post_id": post.id,
            "analysis_detail": result,
            "project_id": post.project_id,
        }
        if system_prompt is not None:
            payload["system_prompt"] = system_prompt

        # 仅在存在时写入，避免覆盖为空
        if summary is not None:
            payload["summary"] = summary
        if sentiment is not None:
            payload["sentiment"] = sentiment
        if brand is not None:
            payload["brand"] = brand
        if timeline is not None:
            payload["timeline"] = timeline
        if key_points is not None:
            payload["key_points"] = key_points
        if risk_types is not None:
            payload["risk_types"] = risk_types
        if brand_relevance is not None:
            payload["brand_relevance"] = brand_relevance
        if relevance_evidence is not None:
            payload["relevance_evidence"] = relevance_evidence
        if handling_suggestions is not None:
            payload["handling_suggestions"] = handling_suggestions
        if total_risk is not None:
            payload["total_risk"] = total_risk
        if total_risk_reason is not None:
            payload["total_risk_reason"] = total_risk_reason
        if transcript_json is not None:
            payload["transcript_json"] = transcript_json

        # 若缺少 summary/sentiment 等必填，保持最小插入由仓库兜底
        return payload

