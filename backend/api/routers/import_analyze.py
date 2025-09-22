from __future__ import annotations

import json
from jobs.logger import get_logger
from fastapi import APIRouter

from ..schemas.import_analyze import ImportAnalyzeRequest, ImportAnalyzeResult
from ..schemas.base import BaseResponse
from services.import_analyze_service import analyze_and_import

logger = get_logger(__name__)
router = APIRouter()


@router.post("/api/import/analyze", response_model=BaseResponse[ImportAnalyzeResult])
async def import_analyze(body: ImportAnalyzeRequest) -> BaseResponse[ImportAnalyzeResult]:
    try:
        body_json = json.dumps(body.model_dump(exclude_none=True), ensure_ascii=False)
    except Exception:
        body_json = "<serialize error>"
    logger.info("【导入分析】接口请求 trace_id=%s 入参=%s", body.trace_id, body_json)

    result_dict = analyze_and_import(body.url, body.project_id, trace_id=body.trace_id)
    return BaseResponse.ok(ImportAnalyzeResult(**result_dict), trace_id=body.trace_id)