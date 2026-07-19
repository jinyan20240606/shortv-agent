# coding=utf-8
import argparse
import html
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests


MOBILE_UA = (
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 "
    "Chrome/124.0 Mobile Safari/537.36"
)
MAX_ITEMS = 200


def configure_utf8():
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def parse_args():
    parser = argparse.ArgumentParser(description="采集小红书公开主页或单篇内容。")
    parser.add_argument("url", help="小红书短链、用户主页或笔记链接")
    parser.add_argument("--max-items", type=int, default=50, help="最多采集内容数，默认 50，硬上限 200")
    parser.add_argument("--cookies", default=os.getenv("XHS_COOKIES", ""), help="可选的小红书登录 Cookie")
    parser.add_argument("--output", default="", help="输出 JSON 路径")
    return parser.parse_args()


def resolve_url(url):
    response = requests.get(url, headers={"User-Agent": MOBILE_UA}, allow_redirects=True, timeout=30)
    response.raise_for_status()
    return response.url, response.text


def extract_initial_state(page):
    match = re.search(r"window\.__INITIAL_STATE__=(\{.*?\})</script>", page, re.S)
    if not match:
        raise RuntimeError("页面中未找到公开结构化数据，可能需要登录或链接已失效。")
    raw = html.unescape(match.group(1))
    raw = re.sub(r"\bundefined\b", "null", raw)
    return json.loads(raw)


def normalize_count(value):
    if isinstance(value, (int, float)):
        return value
    text = str(value or "0").replace(",", "").strip().upper()
    try:
        if text.endswith("K+"):
            return int(float(text[:-2]) * 1000)
        if text.endswith("K"):
            return int(float(text[:-1]) * 1000)
        if text.endswith("W+"):
            return int(float(text[:-2]) * 10000)
        if text.endswith("W"):
            return int(float(text[:-1]) * 10000)
        return int(float(text))
    except ValueError:
        return 0


def compact_profile(state, resolved_url):
    profile = state.get("profile") or {}
    user = profile.get("userInfo") or {}
    notes = profile.get("noteData") or []
    works = []
    for item in notes:
        note_id = item.get("id", "")
        works.append({
            "work_id": note_id,
            "work_url": f"https://www.xiaohongshu.com/explore/{note_id}" if note_id else "",
            "title": item.get("title", ""),
            "desc": item.get("title", ""),
            "type": item.get("type", ""),
            "digg_count": normalize_count(item.get("likes")),
            "collect_count": normalize_count(item.get("collects")),
            "comment_count": normalize_count(item.get("comments")),
            "share_count": 0,
            "cover": (item.get("cover") or {}).get("url", ""),
            "platform": "xiaohongshu",
        })
    return {
        "platform": "xiaohongshu",
        "user_url": resolved_url,
        "profile": {
            "uid": (user.get("userPageWidgetsInfo") or {}).get("userId", "") or urlparse(resolved_url).path.rstrip("/").split("/")[-1],
            "unique_id": user.get("redId", ""),
            "nickname": user.get("nickname", ""),
            "signature": user.get("desc", ""),
            "follower_count": user.get("fans", ""),
            "following_count": user.get("follows", ""),
            "total_favorited": user.get("likeAndCollect", ""),
            "avatar": user.get("images", ""),
            "ip_location": user.get("ipLocation", ""),
            "verification": (user.get("redOfficialVerifyInfo") or {}).get("redOfficialVerifyContent", ""),
        },
        "works": works,
    }


def load_pc_api():
    root = Path(__file__).resolve().parents[1] / "xhs-apis" / "scripts" / "runtime" / "spider_xhs_core"
    os.chdir(root)
    sys.path.insert(0, str(root))
    from apis.xhs_pc_apis import XHS_Apis
    return XHS_Apis()


def enrich_account(result, cookies, max_items):
    if not cookies or len(result["works"]) >= max_items:
        return result
    success, message, notes = load_pc_api().get_user_all_notes(result["user_url"], cookies)
    if not success:
        result["pagination_warning"] = message
        return result
    seen = {item["work_id"] for item in result["works"]}
    for item in notes:
        note_id = item.get("note_id") or item.get("id") or ""
        if not note_id or note_id in seen:
            continue
        card = item.get("note_card") or item
        interact = card.get("interact_info") or {}
        result["works"].append({
            "work_id": note_id,
            "work_url": f"https://www.xiaohongshu.com/explore/{note_id}",
            "title": card.get("display_title") or card.get("title") or "",
            "desc": card.get("desc", ""),
            "type": card.get("type", ""),
            "digg_count": normalize_count(interact.get("liked_count")),
            "collect_count": normalize_count(interact.get("collected_count")),
            "comment_count": normalize_count(interact.get("comment_count")),
            "share_count": normalize_count(interact.get("share_count")),
            "platform": "xiaohongshu",
        })
        seen.add(note_id)
        if len(result["works"]) >= max_items:
            break
    return result


def main():
    configure_utf8()
    args = parse_args()
    max_items = min(max(args.max_items, 1), MAX_ITEMS)
    resolved_url, page = resolve_url(args.url)
    state = extract_initial_state(page)
    if "/user/profile/" in resolved_url:
        result = compact_profile(state, resolved_url)
        result = enrich_account(result, args.cookies, max_items)
        result["works"] = result["works"][:max_items]
        result["max_items"] = max_items
    else:
        result = {"platform": "xiaohongshu", "url": resolved_url, "initial_state": state}

    output = Path(args.output) if args.output else Path.cwd() / "xhs_data.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("小红书采集完成")
    print(f"真实链接：{resolved_url}")
    print(f"输出文件：{output.resolve()}")
    if "works" in result:
        print(f"账号：{result['profile'].get('nickname', '')}")
        print(f"本次内容数：{len(result['works'])}")
        if not args.cookies:
            print("当前未提供登录 Cookie，仅使用公开网页数据；需要更多历史内容时配置 XHS_COOKIES。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
