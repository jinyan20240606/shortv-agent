# coding=utf-8
import argparse
import json
import os
import sys
import time

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dy_apis.douyin_api import DouyinAPI
from fetch_single_work import handle_work_info, timestamp_to_str
from url_util import normalize_douyin_url
from utils.common_util import init


def parse_args():
    parser = argparse.ArgumentParser(description="Track one public account profile and works.")
    parser.add_argument("user_url", help="Supported public account homepage URL.")
    parser.add_argument(
        "--max-works",
        type=int,
        default=50,
        help="Maximum works kept in the output. Default: 50; hard limit: 200",
    )
    parser.add_argument(
        "--output-dir",
        default=os.path.join(os.path.dirname(__file__), "outputs", "accounts"),
        help="Directory used to save account tracking snapshots.",
    )
    return parser.parse_args()


def safe_name(value):
    return "".join(ch for ch in str(value) if ch not in r'\/:*?"<>| ')[:60] or "account"


def compact_user_info(user_response):
    user = user_response.get("user") or user_response.get("user_info") or user_response
    if not isinstance(user, dict):
        user = {}
    avatar = user.get("avatar_thumb") or user.get("avatar_medium") or {}
    return {
        "uid": user.get("uid", ""),
        "sec_uid": user.get("sec_uid", ""),
        "unique_id": user.get("unique_id", ""),
        "short_id": user.get("short_id", ""),
        "nickname": user.get("nickname", ""),
        "signature": user.get("signature", ""),
        "follower_count": user.get("follower_count", 0),
        "following_count": user.get("following_count", 0),
        "aweme_count": user.get("aweme_count", 0),
        "total_favorited": user.get("total_favorited", 0),
        "favoriting_count": user.get("favoriting_count", 0),
        "avatar": (avatar.get("url_list") or [""])[0],
        "ip_location": user.get("ip_location", ""),
    }


def compact_work(raw_work):
    try:
        work = handle_work_info(raw_work)
    except Exception:
        stats = raw_work.get("statistics") or {}
        author = raw_work.get("author") or {}
        aweme_id = raw_work.get("aweme_id", "")
        work = {
            "work_id": aweme_id,
            "work_url": f"https://www.douyin.com/video/{aweme_id}",
            "title": raw_work.get("desc", ""),
            "desc": raw_work.get("desc", ""),
            "nickname": author.get("nickname", ""),
            "digg_count": stats.get("digg_count", 0),
            "comment_count": stats.get("comment_count", 0),
            "collect_count": stats.get("collect_count", 0),
            "share_count": stats.get("share_count", 0),
            "create_time": raw_work.get("create_time", 0),
            "topics": [],
        }
    work["create_time_text"] = timestamp_to_str(work.get("create_time", 0))
    return {
        "work_id": work.get("work_id", ""),
        "work_url": work.get("work_url", ""),
        "title": work.get("title", ""),
        "desc": work.get("desc", ""),
        "create_time": work.get("create_time", 0),
        "create_time_text": work.get("create_time_text", ""),
        "digg_count": work.get("digg_count", 0),
        "comment_count": work.get("comment_count", 0),
        "collect_count": work.get("collect_count", 0),
        "share_count": work.get("share_count", 0),
        "topics": work.get("topics", []),
    }


def build_snapshot(user_url, user_info, works):
    compact_works = [compact_work(item) for item in works]
    compact_works.sort(key=lambda item: item.get("create_time", 0), reverse=True)
    totals = {
        "work_count_returned": len(compact_works),
        "digg_count_sum": sum(item.get("digg_count", 0) for item in compact_works),
        "comment_count_sum": sum(item.get("comment_count", 0) for item in compact_works),
        "collect_count_sum": sum(item.get("collect_count", 0) for item in compact_works),
        "share_count_sum": sum(item.get("share_count", 0) for item in compact_works),
    }
    return {
        "tracked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "user_url": user_url,
        "profile": user_info,
        "totals": totals,
        "works": compact_works,
    }


def save_snapshot(snapshot, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    profile = snapshot.get("profile", {})
    account_key = profile.get("unique_id") or profile.get("short_id") or profile.get("sec_uid") or "account"
    path = os.path.abspath(os.path.join(output_dir, f"{safe_name(account_key)}.json"))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)
    return path


def print_summary(snapshot, path):
    profile = snapshot["profile"]
    totals = snapshot["totals"]
    safe_print("Track success")
    safe_print(f"nickname: {profile.get('nickname')}")
    safe_print(f"unique_id: {profile.get('unique_id')}")
    safe_print(f"signature: {profile.get('signature')}")
    safe_print(f"followers: {profile.get('follower_count')}")
    safe_print(f"following: {profile.get('following_count')}")
    safe_print(f"aweme_count: {profile.get('aweme_count')}")
    safe_print(f"total_favorited: {profile.get('total_favorited')}")
    safe_print(f"works_returned: {totals.get('work_count_returned')}")
    safe_print(f"json: {path}")
    safe_print("")
    for index, work in enumerate(snapshot["works"][:10], 1):
        safe_print(f"{index}. {work['title']}")
        safe_print(f"   {work['work_url']}")
        safe_print(
            f"   {work['create_time_text']} | likes={work['digg_count']} comments={work['comment_count']} "
            f"collects={work['collect_count']} shares={work['share_count']}"
        )


def safe_print(value):
    text = str(value)
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode(sys.stdout.encoding or "utf-8", errors="ignore").decode(sys.stdout.encoding or "utf-8"))


def main():
    args = parse_args()
    args.max_works = min(max(args.max_works, 1), 200)
    auth, _ = init()
    api = DouyinAPI()
    user_url = normalize_douyin_url(args.user_url)

    user_response = api.get_user_info(auth, user_url)
    user_info = compact_user_info(user_response)
    works = api.get_user_all_work_info(auth, user_url)
    if args.max_works > 0:
        works = works[: args.max_works]

    snapshot = build_snapshot(user_url, user_info, works)
    path = save_snapshot(snapshot, args.output_dir)
    print_summary(snapshot, path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
