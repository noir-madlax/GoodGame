from __future__ import annotations
from typing import Any, Dict, Optional
import os

from jobs.logger import get_logger

from .gemini_client import GeminiClient
from .analysis_prompt_builder import get_system_prompt

from tikhub_api.orm.post_repository import PostRepository
from tikhub_api.orm.models import PlatformPost
from tikhub_api.orm.video_analysis_repository import VideoAnalysisRepository
from tikhub_api.video_downloader import VideoDownloader

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
        log.info(f"开始处理帖子 post_id={post_id}：准备读取帖子信息")
        post = self._get_post(post_id)
        log.info(f"读取帖子完成：post_id={post_id}，video_url={post.video_url}")
        if not post.video_url:
            raise ValueError(f"post {post_id} 缺少 video_url")

        # 2) 下载视频为字节流
        log.info(f"开始下载视频：post_id={post_id}，url={post.video_url}")
        data = self.downloader.download_video_as_bytes_with_retry(str(post.video_url))
        if data is None:
            raise RuntimeError(f"下载视频失败：{post.video_url}")
        log.info(f"下载完成：post_id={post_id}，大小={len(data)} 字节")

        # 推断 mime 与 display name
        mime_type = "video/mp4"  # 默认
        display_name = f"post_{post.id or 'unknown'}.mp4"

        # 3) 上传字节流至 Gemini Files
        log.info(f"开始上传到 Gemini：post_id={post_id}，文件名={display_name}")
        upload = self.gemini.upload_file(data, display_name=display_name, mime_type=mime_type)
        file_uri = upload.get("uri")
        log.info(f"上传完成：post_id={post_id}，name={upload.get('name')}，uri={file_uri}")
        if not file_uri:
            raise RuntimeError("Gemini 文件上传未返回 uri")

        # 4) 构建视频 Part（目前仅视频，未来可追加更多内容）
        if types is None:
            raise RuntimeError("google-genai SDK 未正确安装")
        video_part = types.Part(
            file_data=types.FileData(file_uri=file_uri, mime_type=mime_type),
            video_metadata=types.VideoMetadata(fps=5),
        )

        # 5) 构建 prompt 与调用 generate_content
        log.info(f"开始调用 Gemini 生成内容：post_id={post_id}")
        system_prompt = get_system_prompt()
        config = types.GenerateContentConfig(
            temperature=0.3,
            response_mime_type="application/json",
            system_instruction=system_prompt,
        )
        resp = self.gemini.client.models.generate_content(
            model=self.gemini.model,
            contents=[video_part],
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

        log.info(f"生成完成：post_id={post_id}，model={getattr(resp, 'model_version', self.gemini.model)}")

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

        # 6) 字段映射并保存（source_path 使用上传完成后的文件 URI）
        payload = self._map_result_to_video_analysis(post, result, source_path=file_uri or f"post:{post.id}")
        saved = VideoAnalysisRepository.upsert(payload)
        # 返回可 JSON 序列化的结果（避免 datetime 等导致 json.dumps 失败）
        try:
            if hasattr(saved, "model_dump"):
                return saved.model_dump(mode="json", exclude_none=True)  # pydantic v2
        except Exception:
            pass
        return payload

    def _get_post(self, post_id: int) -> PlatformPost:
        post = PostRepository.get_by_id(post_id)
        if not post:
            raise ValueError(f"post 不存在: {post_id}")
        return post

    def _map_result_to_video_analysis(self, post: PlatformPost, result: Dict[str, Any], *, source_path: str) -> Dict[str, Any]:
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

        payload: Dict[str, Any] = {
            "source_path": source_path,
            "source_platform": platform,
            "platform_item_id": platform_item_id,
            "post_id": post.id,
            "analysis_detail": result,
        }
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

        # 若缺少 summary/sentiment 等必填，保持最小插入由仓库兜底
        return payload

