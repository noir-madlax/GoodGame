from __future__ import annotations
from typing import Any, Dict, Optional, List, Tuple
import os
import requests

from jobs.logger import get_logger

from .gemini_client import GeminiClient
from .analysis_prompt_builder import get_system_prompt

from tikhub_api.orm.post_repository import PostRepository
from tikhub_api.orm.models import PlatformPost
from tikhub_api.orm.video_analysis_repository import VideoAnalysisRepository
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
    注意：目前 contents 仅包含视频，未来可在此处追加更多 Part。
    """

    def __init__(self, gemini_client: Optional[GeminiClient] = None) -> None:
        self.gemini = gemini_client or GeminiClient()
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

            if post.post_type == PostType.VIDEO:
                parts, source_key = self._prepare_video_parts(post, fetcher)
            else:
                # 默认按图文处理
                parts, source_key = self._prepare_image_parts(post, fetcher)

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

            # 构建最终 contents 顺序：Title -> Content -> Media 标注 -> 媒体 Parts
            full_parts: List[Any] = []
            title_text = getattr(post, "title", None)
            if title_text:
                full_parts.append(types.Part(text=f"[Post Title]\n{str(title_text)}"))
            content_text = getattr(post, "content", None)
            if content_text:
                full_parts.append(types.Part(text=f"[Post Content]\n{str(content_text)}"))
            if post.post_type == PostType.VIDEO:
                full_parts.append(types.Part(text="[Media] Video file attached below."))
            else:
                try:
                    full_parts.append(types.Part(text=f"[Media] Images attached below. Count={len(parts)}"))
                except Exception:
                    full_parts.append(types.Part(text="[Media] Images attached below."))
            full_parts.extend(parts)

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

    def _prepare_video_parts(self, post: PlatformPost, fetcher) -> Tuple[List[Any], str]:
        """下载→上传→构建视频 Part，返回 (parts, source_key)。"""
        post_id = int(post.id or 0)
        # 获取下载地址
        try:
            video_url = fetcher.get_download_url_by_post_id(post_id)
        except Exception as e:
            video_url = None
            log.error(
                f"获取视频下载地址失败：post_id={post_id}, platform={getattr(post, 'platform', None)}, err={e}"
            )
        if not video_url:
            raise ValueError(f"post {post_id} 获取下载地址失败")

        # 下载视频为字节流
        log.info(f"开始下载视频：post_id={post_id}，url={video_url}")
        data = self.downloader.download_video_as_bytes_with_retry(str(video_url))
        if data is None:
            raise RuntimeError(f"下载视频失败：{video_url}")
        log.info(f"下载完成：post_id={post_id}，大小={len(data)} 字节")

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
            video_metadata=types.VideoMetadata(fps=5),
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

