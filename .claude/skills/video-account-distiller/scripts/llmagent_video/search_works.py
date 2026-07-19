# coding=utf-8
import argparse
import json
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dy_apis.douyin_api import DouyinAPI
from fetch_single_work import handle_work_info, save_json, timestamp_to_str
from utils.common_util import init


def parse_args():
    parser = argparse.ArgumentParser(description="Search Douyin works by keyword.")
    parser.add_argument("keyword", help="Search keyword.")
    parser.add_argument("--num", type=int, default=10, help="How many works to fetch. Default: 10")
    parser.add_argument(
        "--sort-type",
        default="0",
        choices=["0", "1", "2"],
        help="0 comprehensive, 1 most liked, 2 latest. Default: 0",
    )
    parser.add_argument(
        "--publish-time",
        default="0",
        choices=["0", "1", "7", "180"],
        help="0 unlimited, 1 one day, 7 one week, 180 half year. Default: 0",
    )
    parser.add_argument(
        "--filter-duration",
        default="",
        help="Video duration filter: empty unlimited, 0-1, 1-5, 5-10000.",
    )
    parser.add_argument(
        "--search-range",
        default="0",
        help="0 unlimited, 1 recently watched, 2 unwatched, 3 followed users. Default: 0",
    )
    parser.add_argument(
        "--content-type",
        default="0",
        help="0 unlimited, 1 video, 2 image/text. Default: 0",
    )
    parser.add_argument(
        "--output-dir",
        default=os.path.join(os.path.dirname(__file__), "outputs", "search_results"),
        help="Directory used to save search results.",
    )
    return parser.parse_args()


def extract_aweme(item):
    if isinstance(item, dict):
        if isinstance(item.get("aweme_info"), dict):
            return item["aweme_info"]
        if isinstance(item.get("aweme_detail"), dict):
            return item["aweme_detail"]
    return item


def normalize_work(item):
    aweme = extract_aweme(item)
    if not isinstance(aweme, dict):
        return None
    try:
        return handle_work_info(aweme)
    except Exception:
        return {
            "work_id": aweme.get("aweme_id", ""),
            "work_url": f"https://www.douyin.com/video/{aweme.get('aweme_id', '')}",
            "title": aweme.get("desc", ""),
            "desc": aweme.get("desc", ""),
            "nickname": (aweme.get("author") or {}).get("nickname", ""),
            "digg_count": (aweme.get("statistics") or {}).get("digg_count", 0),
            "comment_count": (aweme.get("statistics") or {}).get("comment_count", 0),
            "collect_count": (aweme.get("statistics") or {}).get("collect_count", 0),
            "share_count": (aweme.get("statistics") or {}).get("share_count", 0),
            "create_time": aweme.get("create_time", 0),
        }


def save_results(keyword, results, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    safe_keyword = "".join(ch for ch in keyword if ch not in r'\/:*?"<>| ')[:40] or "keyword"
    path = os.path.abspath(os.path.join(output_dir, f"{safe_keyword}.json"))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    return path


def save_raw(keyword, payload, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    safe_keyword = "".join(ch for ch in keyword if ch not in r'\/:*?"<>| ')[:40] or "keyword"
    path = os.path.abspath(os.path.join(output_dir, f"{safe_keyword}.raw.json"))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


def print_result(index, work):
    created_at = timestamp_to_str(work.get("create_time", 0)) if work.get("create_time") else ""
    print(f"{index}. {work.get('title') or work.get('desc')}")
    print(f"   id: {work.get('work_id')}")
    print(f"   url: {work.get('work_url')}")
    print(f"   author: {work.get('nickname')}")
    print(
        f"   stats: likes={work.get('digg_count', 0)} comments={work.get('comment_count', 0)} "
        f"collects={work.get('collect_count', 0)} shares={work.get('share_count', 0)}"
    )
    if created_at:
        print(f"   created_at: {created_at}")


def main():
    args = parse_args()
    auth, _ = init()
    api = DouyinAPI()

    first_page = api.search_general_work(
        auth,
        args.keyword,
        sort_type=args.sort_type,
        publish_time=args.publish_time,
        offset="0",
        count=str(args.num),
        filter_duration=args.filter_duration,
        search_range=args.search_range,
        content_type=args.content_type,
    )
    if "data" not in first_page:
        raw_path = save_raw(args.keyword, first_page, args.output_dir)
        print(f"Search failed: {first_page.get('status_msg') or 'response has no data'}")
        print(f"status_code: {first_page.get('status_code')}")
        print(f"raw: {raw_path}")
        print("")
        print("Tip: refresh DY_COOKIES from a logged-in www.douyin.com browser session, then retry.")
        return 1

    raw_items = first_page.get("data", [])[: args.num]

    works = []
    for item in raw_items:
        work = normalize_work(item)
        if work:
            works.append(work)

    output_path = save_results(args.keyword, works, args.output_dir)
    print(f"Search success: {args.keyword}")
    print(f"count: {len(works)}")
    print(f"json: {output_path}")
    print("")
    for index, work in enumerate(works, 1):
        print_result(index, work)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
