"""搜索出来后，为了要做视频初筛的分析，决定要不要进一步处理，得输出一个本次search结果的摘要文件"""
"""aweme_id": 和"desc":  "create_time":  "hashtags": 都得输出"""
"""输出到extraced.json"""

from typing import Dict, Any, Optional, List
import os
import json
from datetime import datetime
import glob
import time

# Use absolute imports to work from test directory
from tikhub_api.fetchers.base_fetcher import BaseFetcher
from tikhub_api.orm.models import PlatformPost
from tikhub_api.capabilities import (
    VideoPostProvider,
    VideoDurationProvider,
    DanmakuProvider,
    CommentsProvider,
)
from tikhub_api.orm.supabase_client import get_client

# ===== 抖音搜索（V3）默认配置常量（可由你后续修改） =====
# 接口路径占位：请根据实际文档更新
DOUYIN_SEARCH_API = "/douyin/search/fetch_general_search_v3"
BRAND_LIMIT = 50
#


##

# 默认请求体（仅占位示例）：首次请求 cursor=0, search_id=""
DOUYIN_SEARCH_DEFAULT_PAYLOAD: Dict[str, Any] = {
    "keyword": "火锅", #搜索关键词，如 "猫咪"
    "cursor": 0,  #翻页游标（首次请求传 0）
    "sort_type": "2", #排序方式：0: 综合排序，1: 最多点赞，2: 最新发布
    "publish_time": "180",#0: 不限，1: 最近一天，7: 最近一周，180: 最近半年
    "filter_duration": "0", #0: 不限，0-1: 1分钟以内，1-5: 1-5分钟，5-10000: 5分钟以上
    "content_type": "0",  # 0: 不限，1: 视频，2: 图片，3: 文章
    "search_id": "", #搜索ID（分页时使用）
}

# 本次任务最多获取的结果条数（达到该数将停止翻页）
DOUYIN_SEARCH_MAX_ITEMS: int = 30


class DouyinVideoFetcher(BaseFetcher, VideoPostProvider, VideoDurationProvider, DanmakuProvider, CommentsProvider):
    """抖音视频获取器，用于调用 TikHub API 获取抖音视频信息"""

    @property
    def platform_name(self) -> str:
        """平台名称"""
        return "抖音"


    def get_adapter(self):
        from tikhub_api.adapters import DouyinVideoAdapter
        return DouyinVideoAdapter()

    @property
    def api_endpoint(self) -> str:
        """API 端点路径"""
        return "/douyin/web/fetch_one_video"

    def fetch_video_info(self, aweme_id: str) -> Dict[str, Any]:
        """
        根据视频 ID 获取抖音视频信息

        Args:
            aweme_id (str): 抖音视频 ID

        Returns:
            Dict[str, Any]: API 返回的视频信息

        Raises:
            requests.RequestException: 请求异常
            ValueError: 参数错误
        """
        self._validate_video_id(aweme_id)

        url = f"{self.base_url}{self.api_endpoint}"
        params = {'aweme_id': aweme_id}

        return self._make_request(url, params)

    def get_video_details(self, aweme_id: str) -> Optional[Dict[str, Any]]:
        """
        获取视频详细信息的便捷方法

        Args:
            aweme_id (str): 抖音视频 ID

        Returns:
            Optional[Dict[str, Any]]: 视频详细信息，如果获取失败返回 None
        """
        try:
            result = self.fetch_video_info(aweme_id)

            # 检查 API 返回状态
            if self._check_api_response(result):
                return result.get('data')
            else:
                print(f"API 返回信息: {result}")
                return None

        except Exception as e:
            print(f"获取视频信息失败: {str(e)}")
            return None

    def get_download_urls(self, aweme_id: str) -> Optional[List[str]]:
        """
        获取视频下载链接列表

        Args:
            aweme_id (str): 抖音视频 ID

        Returns:
            Optional[List[str]]: 下载链接列表，如果获取失败返回 None
        """
        try:
            video_details = self.get_video_details(aweme_id)
            if video_details and 'aweme_detail' in video_details:
                download_addr = video_details['aweme_detail']['video']['download_addr']
                return download_addr.get('url_list', [])
            return None
        except Exception as e:
            print(f"获取下载链接失败: {str(e)}")
            return None

    # ===== 抖音搜索能力 =====
    def fetch_search_posts(self) -> List[PlatformPost]:
        """
        内置分页：基于 DOUYIN_SEARCH_DEFAULT_PAYLOAD 和 DOUYIN_SEARCH_MAX_ITEMS，
        自动按 cursor/search_id 翻页，最终返回 PlatformPost 列表。
        """
        try:
            from tikhub_api.adapters import to_posts_from_douyin_search
        except Exception:
            from tikhub_api.adapters import to_posts_from_douyin_search

        gathered: List[PlatformPost] = []
        cursor = 0
        search_id = ""
        has_more = 1
        total_needed = int(DOUYIN_SEARCH_MAX_ITEMS)

        while has_more == 1 and len(gathered) < total_needed:
            payload = dict(DOUYIN_SEARCH_DEFAULT_PAYLOAD)
            payload["cursor"] = cursor
            payload["search_id"] = search_id

            url = f"{self.base_url}{DOUYIN_SEARCH_API}"
            # 该接口要求 POST，因此这里用 POST 方式调用
            result = self._make_request(url, payload, method="POST")
            if not self._check_api_response(result):
                print(f"搜索接口返回异常: {result}")
                break

            data = result.get("data") or {}
            posts = to_posts_from_douyin_search(data)
            for p in posts:
                if len(gathered) >= total_needed:
                    break
                gathered.append(p)

            # 翻页字段（参考示例文件，可按实际返回字段名调整）
            inner = data if isinstance(data, dict) else {}
            cursor = int(inner.get("cursor") or cursor)
            search_id = str(inner.get("search_id") or search_id)
            has_more = int(inner.get("has_more") or (1 if len(posts) > 0 else 0))
            if cursor == payload["cursor"] and has_more == 1:
                has_more = 0  # 防止死循环

        return gathered

    # 兼容命名：对外也提供 fetch_search_page，返回 PlatformPost 列表
    def fetch_search_page(self) -> List[PlatformPost]:
        return self.fetch_search_posts()


    def fetch_video_danmaku(self, item_id: str, duration: int, start_time: int = 0, end_time: Optional[int] = None) -> Dict[str, Any]:
        """
        获取抖音视频弹幕信息

        Args:
            item_id (str): 抖音视频 ID
            duration (int): 视频时长（毫秒）
            start_time (int): 开始时间（毫秒），默认为 0
            end_time (Optional[int]): 结束时间（毫秒），如果为 None 则使用 duration-1

        Returns:
            Dict[str, Any]: API 返回的弹幕信息

        Raises:
            requests.RequestException: 请求异常
            ValueError: 参数错误
        """
        self._validate_video_id(item_id)

        if duration <= 0:
            raise ValueError("视频时长必须大于 0")

        if start_time < 0:
            raise ValueError("开始时间不能小于 0")

        if end_time is None:
            end_time = duration - 1

        if end_time > duration:
            raise ValueError("结束时间不能大于视频时长")

        if start_time >= end_time:
            raise ValueError("开始时间必须小于结束时间")

        url = f"{self.base_url}/douyin/web/fetch_one_video_danmaku"
        params = {
            'item_id': item_id,
            'duration': duration,
            'start_time': start_time,
            'end_time': end_time
        }

        return self._make_request(url, params)

    def get_video_danmaku(self, item_id: str, duration: int, start_time: int = 0, end_time: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        获取视频弹幕信息的便捷方法

        Args:
            item_id (str): 抖音视频 ID
            duration (int): 视频时长（毫秒）
            start_time (int): 开始时间（毫秒），默认为 0
            end_time (Optional[int]): 结束时间（毫秒），如果为 None 则使用 duration-1

        Returns:
            Optional[Dict[str, Any]]: 弹幕信息，如果获取失败返回 None
        """
        try:
            result = self.fetch_video_danmaku(item_id, duration, start_time, end_time)

            # 检查 API 返回状态
            if self._check_api_response(result):
                return result.get('data')
            else:
                print(f"获取弹幕失败: {result.get('message', '未知错误')}")
                return None

        except Exception as e:
            print(f"获取弹幕信息失败: {str(e)}")
            return None

    # ===== 评论能力 =====
    def fetch_video_comments_page(self, aweme_id: str, cursor: int = 0, count: int = 20) -> Dict[str, Any]:
        self._validate_video_id(aweme_id)
        if cursor < 0:
            raise ValueError("cursor 不能小于 0")
        if count <= 0 or count > 50:
            raise ValueError("count 必须在 1~50 之间")
        url = f"{self.base_url}/douyin/web/fetch_video_comments"
        params = {
            'aweme_id': aweme_id,
            'cursor': cursor,
            'count': count,
        }
        return self._make_request(url, params)

    def get_video_comments(self, aweme_id: str, cursor: int = 0, count: int = 20) -> Optional[Dict[str, Any]]:
        try:
            result = self.fetch_video_comments_page(aweme_id, cursor, count)
            if self._check_api_response(result):
                return result.get('data')
            else:
                print(f"获取评论失败，response: {result}")
                return None
        except Exception as e:
            print(f"获取评论信息失败: {str(e)}")
            return None

    # ===== 评论回复能力 =====
    def fetch_video_comment_replies_page(self, item_id: str, comment_id: str, cursor: int = 0, count: int = 20) -> Dict[str, Any]:
        self._validate_video_id(item_id)
        if not comment_id:
            raise ValueError("comment_id 不能为空")
        if cursor < 0:
            raise ValueError("cursor 不能小于 0")
        if count <= 0 or count > 50:
            raise ValueError("count 必须在 1~50 之间")
        url = f"{self.base_url}/douyin/web/fetch_video_comment_replies"
        params = {
            'item_id': item_id,
            'comment_id': comment_id,
            'cursor': cursor,
            'count': count,
        }
        return self._make_request(url, params)

    def get_video_comment_replies(self, item_id: str, comment_id: str, cursor: int = 0, count: int = 20) -> Optional[Dict[str, Any]]:
        try:
            result = self.fetch_video_comment_replies_page(item_id, comment_id, cursor, count)
            if self._check_api_response(result):
                return result.get('data')
            else:
                print(f"获取评论回复失败: {result.get('message', '未知错误')}")
                return None
        except Exception as e:
            print(f"获取评论回复信息失败: {str(e)}")
            return None


# 便捷函数
def fetch_douyin_video(aweme_id: str) -> Optional[Dict[str, Any]]:
    """
    便捷函数：获取抖音视频信息

    Args:
        aweme_id (str): 抖音视频 ID

    Returns:
        Optional[Dict[str, Any]]: 视频信息，失败返回 None
    """
    fetcher = DouyinVideoFetcher()
    return fetcher.get_video_details(aweme_id)


def save_search_result_like_reference(
    fetcher: DouyinVideoFetcher,
    payload: Dict[str, Any],
    brand_name: Optional[str] = None,
    base_keyword: Optional[str] = None,
) -> str:
    """
    Call Douyin search v3 and save JSON to output directory with filename using MMDD-HHMM.
    The JSON structure mirrors the reference result.json (top-level code/router/params/data fields).
    Returns the absolute file path written.
    """
    url = f"{fetcher.base_url}{DOUYIN_SEARCH_API}"
    response = fetcher._make_request(url, payload, method="POST")  # preserve structure

    # ---------- extract key info and summary ----------
    def to_yyMMdd_hhmm(ts: int) -> str:
        try:
            return datetime.fromtimestamp(ts).strftime("%y%m%d-%H%M")
        except Exception:
            return ""

    items = []  # flat list of aweme items
    data_obj = response.get("data") or {}
    raw_list = data_obj.get("data") or []
    for entry in raw_list:
        if not isinstance(entry, dict):
            continue
        if entry.get("type") != 1:
            continue
        aw = entry.get("aweme_info") or {}
        items.append(aw)

    extracted: List[Dict[str, Any]] = []
    per_day_count: Dict[str, int] = {}
    for aw in items:
        aweme_id = aw.get("aweme_id")
        desc = aw.get("desc")
        create_time = int(aw.get("create_time") or 0)
        create_ymdhm = to_yyMMdd_hhmm(create_time)
        # video first url
        first_video_url = None
        video = aw.get("video") or {}
        url_list = None
        # try common paths
        if isinstance(video, dict):
            dl = video.get("download_addr") or {}
            url_list = (dl.get("url_list") if isinstance(dl, dict) else None) or []
            if not url_list and video.get("play_addr"):
                pla = video.get("play_addr") or {}
                url_list = (pla.get("url_list") if isinstance(pla, dict) else None) or []
        if isinstance(url_list, list) and len(url_list) > 0:
            first_video_url = url_list[0]

        # interaction sum from statistics
        stats = aw.get("statistics") or {}
        try:
            share_count = int(stats.get("share_count") or 0)
            comment_count = int(stats.get("comment_count") or 0)
            digg_count = int(stats.get("digg_count") or 0)
            collect_count = int(stats.get("collect_count") or 0)
        except Exception:
            share_count = comment_count = digg_count = collect_count = 0
        engagement_sum = share_count + comment_count + digg_count + collect_count

        # hashtags
        hashtags: List[str] = []
        for t in (aw.get("text_extra") or []):
            if not isinstance(t, dict):
                continue
            name = t.get("hashtag_name")
            if name:
                hashtags.append(name)

        extracted.append({
            "aweme_id": aweme_id,
            "desc": desc,
            "create_time": create_ymdhm,
            "video_first_url": first_video_url,
            "engagement_sum": engagement_sum,
            "hashtags": hashtags,
        })

        if create_ymdhm:
            day_key = create_ymdhm.split("-")[0]  # yyMMdd
            per_day_count[day_key] = per_day_count.get(day_key, 0) + 1

    # summary
    date_keys = sorted(per_day_count.keys())
    date_span = None
    if date_keys:
        date_span = {
            "from": date_keys[0],
            "to": date_keys[-1],
        }
    summary = {
        "total_videos": len(extracted),
        "date_span": date_span,
        "per_day_counts": per_day_count,
    }

    # inject at top-level
    response = {
        "summary": summary,
        "extracted": extracted,
        "__separator__": "----- raw below -----",
        **response,
    }

    # output directory and filename: month-day-hour-minute (no year, no seconds)
    timestamp = datetime.now().strftime("%m%d-%H%M")
    # include base keyword in filename for clarity (allow unicode)
    kw_part = (base_keyword or "").strip()
    if kw_part:
        filename = f"douyin_search_v3_{timestamp}__{kw_part}.json"
    else:
        filename = f"douyin_search_v3_{timestamp}.json"
    # brand sub-directory
    safe_brand = None
    if brand_name:
        safe_brand = "".join(ch if ch.isalnum() else "_" for ch in brand_name).strip("_") or "brand"
    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "output", "seachlist", safe_brand or "_"))
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, filename)
    # avoid overwrite when multiple queries run within the same minute
    if os.path.exists(out_path):
        suffix = 1
        base, ext = os.path.splitext(out_path)
        while os.path.exists(f"{base}_{suffix}{ext}"):
            suffix += 1
        out_path = f"{base}_{suffix}{ext}"

    # Write pretty JSON, ensure UTF-8 and non-ASCII preserved
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(response, f, ensure_ascii=False, indent=2)

    # also write/update a simple brand summary txt with request params and file path
    try:
        if brand_name:
            txt_path = os.path.join(out_dir, "brand_summary.txt")
            with open(txt_path, "a", encoding="utf-8") as tf:
                tf.write(f"time={datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
                tf.write(f"payload={json.dumps(payload, ensure_ascii=False)}\n")
                tf.write(f"written={out_path}\n")
                tf.write(f"total_videos={summary['total_videos']} date_span={summary['date_span']}\n")
                tf.write("---\n")
    except Exception:
        pass

    return out_path


if __name__ == "__main__":
    # 执行：从 Supabase 读取品牌与关键词，按“品牌 + 空格 + 关键词”组合批量搜索
    # 环境变量 BRAND_LIMIT 控制最多查询多少个品牌（默认 1）
    try:
        brand_limit = int(os.getenv("BRAND_LIMIT", str(BRAND_LIMIT)))
    except Exception:
        brand_limit = 1

    try:
        sb = get_client()
        # 读取品牌（merchant_brands.name）
        bres = sb.table("merchant_brands").select("name").order("id").limit(brand_limit).execute()
        brands: List[str] = [r.get("name") for r in (bres.data or []) if r.get("name")]
        if not brands:
            print("No brands found; stop.")
            raise SystemExit(0)

        # 读取关键词（search_keywords.keyword）
        kres = sb.table("search_keywords").select("keyword").order("id").execute()
        keywords: List[str] = [r.get("keyword") for r in (kres.data or []) if r.get("keyword")]
        if not keywords:
            print("No keywords found; stop.")
            raise SystemExit(0)

        fetcher = DouyinVideoFetcher()
        for brand in brands:
            # per-brand subdir and existing file detection for resume
            brand_dir = os.path.abspath(os.path.join(
                os.path.dirname(__file__), "output", "seachlist",
                ("".join(ch if ch.isalnum() else "_" for ch in brand).strip("_") or "brand")
            ))
            os.makedirs(brand_dir, exist_ok=True)

            for kw in keywords:
                # skip if any file for this keyword already exists in brand dir
                pattern = os.path.join(brand_dir, f"douyin_search_v3_*__{kw}.json")
                existed = glob.glob(pattern)
                if existed:
                    print(f"Skip (exists): {brand} {kw}")
                    continue

                payload = dict(DOUYIN_SEARCH_DEFAULT_PAYLOAD)
                payload["keyword"] = f"{brand} {kw}"

                # retry transient errors up to 3 times
                last_err: Optional[Exception] = None
                for attempt in range(1, 4):
                    try:
                        written = save_search_result_like_reference(
                            fetcher,
                            payload,
                            brand_name=brand,
                            base_keyword=kw,
                        )
                        print(f"Saved search result to: {written}")
                        last_err = None
                        break
                    except Exception as e:
                        last_err = e
                        print(f"Error attempt {attempt} for {brand} {kw}: {e}")
                        time.sleep(2 * attempt)
                if last_err is not None:
                    # log to brand_summary.txt for visibility
                    try:
                        with open(os.path.join(brand_dir, "brand_summary.txt"), "a", encoding="utf-8") as tf:
                            tf.write(f"failed {datetime.now().strftime('%Y-%m-%d %H:%M')} {brand} {kw}: {last_err}\n")
                    except Exception:
                        pass
    except Exception as e:
        print(f"错误: {str(e)}")
