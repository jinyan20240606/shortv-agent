# coding=utf-8
import argparse
import json
import os
import re
import sys
import time

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dy_apis.douyin_api import DouyinAPI
from url_util import normalize_douyin_url
from utils.common_util import init


def timestamp_to_str(timestamp):
    timestamp = int(timestamp or 0)
    if timestamp > 10_000_000_000:
        timestamp = timestamp / 1000
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))


def handle_work_info(data):
    author = data.get("author", {})
    statistics = data.get("statistics", {})
    video = data.get("video", {})
    text_extra = data.get("text_extra") or []
    images = data.get("images")
    if not isinstance(images, list):
        images = []

    sec_uid = author.get("sec_uid", "")
    gender = author.get("gender")
    if gender == 1:
        gender_text = "male"
    elif gender == 0:
        gender_text = "female"
    else:
        gender_text = "unknown"

    aweme_type = data.get("aweme_type")
    if aweme_type == 68:
        work_type = "image"
    elif aweme_type == 0:
        work_type = "video"
    else:
        work_type = "unknown"

    recommend_chapter_info = data.get("recommend_chapter_info") or {}
    chapter_bar = recommend_chapter_info.get("chapter_bar") or []
    chapter_items = []
    for item in chapter_bar:
        chapter_items.append(
            {
                "desc": item.get("desc", ""),
                "detail": item.get("detail", ""),
                "start_time": item.get("start_time"),
                "end_time": item.get("end_time"),
            }
        )

    return {
        "work_id": data.get("aweme_id", ""),
        "work_url": f"https://www.douyin.com/video/{data.get('aweme_id', '')}",
        "work_type": work_type,
        "title": data.get("desc", ""),
        "item_title": data.get("item_title", ""),
        "desc": data.get("desc", ""),
        "caption": data.get("caption", ""),
        "script_summary": recommend_chapter_info.get("chapter_abstract", ""),
        "script_chapters": chapter_items,
        "video_text": data.get("video_text") or [],
        "admire_count": statistics.get("admire_count", 0),
        "digg_count": statistics.get("digg_count", 0),
        "comment_count": statistics.get("comment_count", 0),
        "collect_count": statistics.get("collect_count", 0),
        "share_count": statistics.get("share_count", 0),
        "video_addr": ((video.get("play_addr") or {}).get("url_list") or [""])[0],
        "images": images,
        "topics": [item.get("hashtag_name", "") for item in text_extra if item.get("hashtag_name")],
        "create_time": data.get("create_time", 0),
        "video_cover": ((video.get("cover") or {}).get("url_list") or [""])[0],
        "user_url": f"https://www.douyin.com/user/{sec_uid}" if sec_uid else "",
        "user_id": author.get("unique_id", ""),
        "nickname": author.get("nickname", ""),
        "author_avatar": ((author.get("avatar_thumb") or {}).get("url_list") or [""])[0],
        "user_desc": author.get("signature", ""),
        "following_count": author.get("following_count", "unknown"),
        "follower_count": author.get("follower_count", "unknown"),
        "total_favorited": author.get("total_favorited", "unknown"),
        "aweme_count": author.get("aweme_count", "unknown"),
        "user_age": author.get("user_age", "unknown"),
        "gender": gender_text,
        "ip_location": data.get("ip_location", "unknown"),
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Fetch one Douyin work by URL.")
    parser.add_argument("url", help="Douyin work URL, for example https://www.douyin.com/video/...")
    parser.add_argument(
        "--output-dir",
        default=os.path.join(os.path.dirname(__file__), "outputs", "single_work"),
        help="Directory used to save JSON output. Default: llmagent_video/outputs/single_work",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download media files as well. By default only metadata is fetched.",
    )
    parser.add_argument(
        "--excel",
        action="store_true",
        help="Also save one xlsx file under datas/excel_datas.",
    )
    return parser.parse_args()


def save_json(work_info, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.abspath(os.path.join(output_dir, f"{work_info['work_id']}.json"))
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(work_info, f, ensure_ascii=False, indent=2)
    return output_path


def save_raw_json(response, output_dir, work_id):
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.abspath(os.path.join(output_dir, f"{work_id}.raw.json"))
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(response, f, ensure_ascii=False, indent=2)
    return output_path


def norm_filename(value):
    value = re.sub(r'[\\/:*?"<>| ]+', "", value or "")
    return value[:40] or "untitled"


def download_file(url, path):
    import requests

    with requests.get(url, stream=True, timeout=30) as response:
        response.raise_for_status()
        with open(path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


def download_media(work_info, output_root):
    save_dir = os.path.abspath(
        os.path.join(output_root, f"{norm_filename(work_info['nickname'])}_{work_info['work_id']}")
    )
    os.makedirs(save_dir, exist_ok=True)

    if work_info["video_cover"]:
        download_file(work_info["video_cover"], os.path.join(save_dir, "cover.jpg"))
    if work_info["work_type"] == "video" and work_info["video_addr"]:
        download_file(work_info["video_addr"], os.path.join(save_dir, "video.mp4"))
    if work_info["work_type"] == "image":
        for index, image in enumerate(work_info["images"]):
            url_list = image.get("url_list") if isinstance(image, dict) else None
            image_url = (url_list or [image])[0]
            if image_url:
                download_file(image_url, os.path.join(save_dir, f"image_{index}.jpg"))

    return save_dir


def print_summary(work_info, json_path):
    print("Fetch success")
    print(f"work_id: {work_info['work_id']}")
    print(f"work_url: {work_info['work_url']}")
    print(f"type: {work_info['work_type']}")
    print(f"title: {work_info['title']}")
    if work_info["item_title"]:
        print(f"item_title: {work_info['item_title']}")
    print(f"desc: {work_info['desc']}")
    if work_info["script_summary"]:
        print(f"script_summary: {work_info['script_summary']}")
    if work_info["script_chapters"]:
        print("script_chapters:")
        for chapter in work_info["script_chapters"]:
            print(f"  - {chapter['desc']}: {chapter['detail']}")
    print(f"author: {work_info['nickname']} ({work_info['user_id']})")
    print(f"created_at: {timestamp_to_str(work_info['create_time'])}")
    print(f"digg_count: {work_info['digg_count']}")
    print(f"comment_count: {work_info['comment_count']}")
    print(f"collect_count: {work_info['collect_count']}")
    print(f"share_count: {work_info['share_count']}")
    print(f"topics: {', '.join(work_info['topics'])}")
    print(f"video_cover: {work_info['video_cover']}")
    print(f"video_addr: {work_info['video_addr']}")
    print(f"json: {json_path}")


def main():
    args = parse_args()
    auth, base_path = init()

    response = DouyinAPI().get_work_info(auth, normalize_douyin_url(args.url))
    if "aweme_detail" not in response or not response["aweme_detail"]:
        print("Fetch failed: response has no aweme_detail.", file=sys.stderr)
        print(json.dumps(response, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    work_info = handle_work_info(response["aweme_detail"])
    work_info["create_time_text"] = timestamp_to_str(work_info["create_time"])

    json_path = save_json(work_info, args.output_dir)
    raw_json_path = save_raw_json(response, args.output_dir, work_info["work_id"])
    print_summary(work_info, json_path)
    print(f"raw_json: {raw_json_path}")

    if args.excel:
        from utils.data_util import save_to_xlsx

        excel_path = os.path.abspath(os.path.join(base_path["excel"], f"{work_info['work_id']}.xlsx"))
        save_to_xlsx([work_info], excel_path)
        print(f"excel: {excel_path}")

    if args.download:
        media_path = download_media(work_info, base_path["media"])
        print(f"media: {media_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
