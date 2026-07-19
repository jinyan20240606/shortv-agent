# coding=utf-8
import argparse
import json
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv

from auth_douyin import capture_douyin_cookie
from dy_apis.douyin_api import DouyinAPI
from fetch_single_work import handle_work_info, save_json, save_raw_json, timestamp_to_str
from fetch_wechat_channels import fetch_wechat_channels_work, is_wechat_channels_url
from transcribe_work import download_video, save_transcript, transcribe_video
from url_util import normalize_douyin_url
from utils.common_util import init


def parse_args():
    parser = argparse.ArgumentParser(description="Prepare Douyin video materials for WorkBuddy model writing.")
    parser.add_argument("url", help="Douyin video/work URL.")
    parser.add_argument(
        "--requirement",
        "-r",
        default="面向股票新手，60秒口播，财经博主风格，开头要抓人，结尾引导关注。",
        help="Writing requirement for WorkBuddy.",
    )
    parser.add_argument("--model", default="tiny", help="faster-whisper model. Default: tiny")
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda"], help="ASR device. Default: cpu")
    parser.add_argument("--profile", default="", help="Optional IP style profile name or JSON path.")
    parser.add_argument(
        "--output-dir",
        default=os.path.join(os.path.dirname(__file__), "outputs", "workbuddy_materials"),
        help="Directory used to save materials.",
    )
    return parser.parse_args()


def ensure_cookie():
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"), override=True)
    return bool(os.getenv("DY_COOKIES"))


def build_prompt(work_info, transcript, requirement):
    transcript_text = transcript.get("text", "")
    transcript_chars = len(transcript_text.strip())
    min_script_chars = max(450, int(transcript_chars * 0.8)) if transcript_chars else 450
    source = {
        "work_id": work_info.get("work_id"),
        "work_url": work_info.get("work_url"),
        "title": work_info.get("item_title") or work_info.get("title"),
        "desc": work_info.get("desc"),
        "author": work_info.get("nickname"),
        "created_at": work_info.get("create_time_text"),
        "stats": {
            "likes": work_info.get("digg_count", 0),
            "comments": work_info.get("comment_count", 0),
            "collects": work_info.get("collect_count", 0),
            "shares": work_info.get("share_count", 0),
        },
        "topics": work_info.get("topics", []),
        "script_summary": work_info.get("script_summary", ""),
    }
    return f"""你是财经短视频爆款编导。请基于下面素材完成拆解和新脚本生成。

用户要求：
{requirement}

原视频信息：
{json.dumps(source, ensure_ascii=False, indent=2)}

原视频逐字稿：
{transcript_text}

长度要求：
- 原视频逐字稿约 {transcript_chars} 字。
- 新脚本必须是完整口播稿，不是提纲，不是摘要。
- 新脚本正文不少于 {min_script_chars} 字；如果用户明确要求 60 秒，正文建议 450-650 字；如果原文更长，优先接近原文信息密度。
- 每个时间段都要写出能直接照读的完整句子，不能只写“痛点放大”“案例说明”这种提示词。

请严格输出：

格式要求：
- 不要使用 Markdown 表格。
- 不要使用引用块 `>`。
- 不要使用代码块。
- 不要在三大标题之外添加 `##`、`###` 小标题。
- 每一项都用「字段名：内容」输出，方便生成 HTML 报告。
- 在正文最前面先输出一行「内容关键词：关键词1、关键词2、关键词3、关键词4」，关键词必须基于原视频内容，只写实体/概念/主题词；不要写风格词、时间段、标题整句、HTML符号或泛词。

一、这个视频为什么能爆
- 核心爆点：用一句话说清楚
- 可复用结构：用“开头 → 中段 → 结尾”压缩说明
- 借鉴提醒：这条视频最值得改写时借鉴什么

二、可拍脚本
用可直接拍摄的分镜口播格式。每一段都要给足口播台词，保留原视频的信息密度，并按用户要求重写表达：
【0-3秒 开头钩子】
【3-10秒 痛点放大】
【10-40秒 方法/案例】
【40-55秒 总结升华】
【55-60秒 关注/私信/评论引导】

三、发布包装
- 标题3个
- 封面字3个
- 评论区置顶引导1条
"""


def load_profile(profile):
    profile_name = profile or "小白投教"
    path = profile_name
    if not os.path.exists(path):
        path = os.path.join(os.path.dirname(__file__), "profiles", f"{profile_name}.json")
    if not os.path.exists(path):
        if profile:
            raise RuntimeError(f"Profile not found: {profile}")
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["_profile_name"] = data.get("name") or profile_name
    data["_profile_display_name"] = data.get("display_name") or data.get("name") or profile_name
    data["_is_default_profile"] = not bool(profile)
    return data


def compact_comment(comment):
    user = comment.get("user") or {}
    return {
        "cid": comment.get("cid", ""),
        "text": comment.get("text", ""),
        "digg_count": comment.get("digg_count", 0),
        "reply_comment_total": comment.get("reply_comment_total", 0),
        "nickname": user.get("nickname", ""),
    }


def fetch_top_comments(auth, url, max_pages=10, top_n=5):
    comments = []
    cursor = "0"
    for _ in range(max_pages):
        try:
            response = DouyinAPI.get_work_out_comment(auth, url, cursor)
        except Exception as exc:
            print(f"Comment fetch skipped: {exc}")
            break
        batch = response.get("comments") or []
        comments.extend(compact_comment(item) for item in batch if item.get("text"))
        if response.get("has_more") != 1:
            break
        cursor = str(response.get("cursor", "0"))
    comments.sort(key=lambda item: (item.get("digg_count", 0), item.get("reply_comment_total", 0)), reverse=True)
    return comments[:top_n]


def inject_profile(prompt, profile):
    if not profile:
        return prompt
    profile_text = json.dumps(profile, ensure_ascii=False, indent=2)
    return prompt.replace(
        "请严格输出：",
        f"""请优先按下面这个IP风格档案改写，不要只模仿原视频：
{profile_text}

请严格输出：""",
    )


def save_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    args = parse_args()
    is_channels = is_wechat_channels_url(args.url)
    if not is_channels and not ensure_cookie():
        print("DY_COOKIES is not set. Opening Douyin login window...")
        try:
            os.environ["DY_COOKIES"] = capture_douyin_cookie(auto=True)
        except RuntimeError as exc:
            print(str(exc))
            return 1

    auth = None
    if is_channels:
        print("Detected platform: WeChat Channels")
        work_info, response = fetch_wechat_channels_work(args.url)
    else:
        auth, _ = init()
        normalized_url = normalize_douyin_url(args.url)
        if normalized_url != args.url:
            print(f"Resolved Douyin URL: {normalized_url}")
        response = DouyinAPI().get_work_info(auth, normalized_url)
        if "aweme_detail" not in response or not response["aweme_detail"]:
            print("Fetch failed: response has no aweme_detail.")
            print(json.dumps(response, ensure_ascii=False, indent=2))
            return 1
        work_info = handle_work_info(response["aweme_detail"])
        work_info["platform"] = "douyin"
    work_info["create_time_text"] = timestamp_to_str(work_info["create_time"])
    work_id = work_info["work_id"]

    os.makedirs(args.output_dir, exist_ok=True)
    work_path = save_json(work_info, args.output_dir)
    raw_path = save_raw_json(response, args.output_dir, work_id)

    video_path = os.path.abspath(os.path.join(args.output_dir, f"{work_id}.mp4"))
    transcript_json = os.path.abspath(os.path.join(args.output_dir, f"{work_id}.transcript.json"))
    transcript_txt = os.path.abspath(os.path.join(args.output_dir, f"{work_id}.transcript.txt"))

    if not os.path.exists(video_path):
        print(f"Downloading video: {video_path}")
        download_video(work_info["video_addr"], video_path, auth, work_info["work_url"])

    if os.path.exists(transcript_json):
        with open(transcript_json, "r", encoding="utf-8") as f:
            transcript = json.load(f)
    else:
        print(f"Transcribing with faster-whisper model={args.model}, device={args.device}")
        transcript = transcribe_video(video_path, args.model, args.device)
        save_transcript(args.output_dir, work_id, transcript)

    profile = load_profile(args.profile)
    top_comments = [] if is_channels else fetch_top_comments(auth, work_info["work_url"])
    prompt = inject_profile(build_prompt(work_info, transcript, args.requirement), profile)
    prompt_path = os.path.abspath(os.path.join(args.output_dir, f"{work_id}.workbuddy_prompt.md"))
    material_path = os.path.abspath(os.path.join(args.output_dir, f"{work_id}.material.json"))
    save_text(prompt_path, prompt)
    with open(material_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "work_info": work_info,
                "transcript": transcript,
                "requirement": args.requirement,
                "profile": profile,
                "profile_display_name": profile.get("_profile_display_name") if profile else "",
                "profile_is_default": bool(profile and profile.get("_is_default_profile")),
                "top_comments": top_comments,
                "prompt_path": prompt_path,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print("Material prepared for WorkBuddy")
    print(f"work_json: {work_path}")
    print(f"raw_json: {raw_path}")
    print(f"video: {video_path}")
    print(f"transcript_txt: {transcript_txt}")
    print(f"transcript_json: {transcript_json}")
    print(f"prompt: {prompt_path}")
    print(f"material: {material_path}")
    print(f"profile: {profile.get('_profile_display_name') if profile else 'none'}")
    print(f"top_comments: {len(top_comments)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
