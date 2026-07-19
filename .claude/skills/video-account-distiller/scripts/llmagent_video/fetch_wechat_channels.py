# coding=utf-8
import hashlib
import re
from urllib.parse import urlparse

import requests


PARSER_API = "https://sph.litao.workers.dev/api/fetch_video_profile"


def is_wechat_channels_url(url):
    host = urlparse(url).netloc.lower()
    return host in {"weixin.qq.com", "channels.weixin.qq.com"} and ("/sph/" in url or "finder-preview" in url)


def _number(value):
    match = re.search(r"[\d.]+", str(value or ""))
    if not match:
        return 0
    number = float(match.group())
    text = str(value)
    if "万" in text:
        number *= 10000
    return int(number)


def fetch_wechat_channels_work(url, timeout=45):
    response = requests.post(PARSER_API, json={"url": url}, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    if payload.get("errCode") not in (None, 0):
        raise RuntimeError(payload.get("errMsg") or "视频号解析失败")
    data = payload.get("data") or {}
    author = data.get("authorInfo") or {}
    feed = data.get("feedInfo") or {}
    video_url = feed.get("videoUrl") or (feed.get("h264VideoInfo") or {}).get("videoUrl")
    if not video_url:
        raise RuntimeError("视频号解析结果没有视频地址")
    description = feed.get("description") or ""
    topics = re.findall(r"#([^#\s]+)", description)
    work_id = "wx_" + hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
    return {
        "work_id": work_id,
        "work_url": url,
        "platform": "wechat_channels",
        "work_type": "video",
        "title": description.splitlines()[0].strip() if description else "视频号视频",
        "item_title": "",
        "desc": description,
        "caption": description,
        "script_summary": "",
        "script_chapters": [],
        "video_text": [],
        "admire_count": _number(feed.get("favCountFmt")),
        "digg_count": _number(feed.get("likeCountFmt")),
        "comment_count": _number(feed.get("commentCountFmt")),
        "collect_count": _number(feed.get("favCountFmt")),
        "share_count": _number(feed.get("forwardCountFmt")),
        "video_addr": video_url,
        "images": [],
        "topics": topics,
        "create_time": feed.get("createtime", 0),
        "video_cover": feed.get("coverUrl", ""),
        "user_url": "",
        "user_id": "",
        "nickname": author.get("nickname", ""),
        "author_avatar": author.get("headImgUrl", ""),
        "user_desc": "",
        "following_count": "unknown",
        "follower_count": "unknown",
        "total_favorited": "unknown",
        "aweme_count": "unknown",
        "user_age": "unknown",
        "gender": "unknown",
        "ip_location": "unknown",
    }, payload
