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
from track_account import build_snapshot, compact_user_info
from url_util import normalize_douyin_url
from utils.common_util import init


def parse_args():
    parser = argparse.ArgumentParser(description="Create an IP style profile from text corpus and/or Douyin account.")
    parser.add_argument("--name", required=True, help="Profile name, for example panjie.")
    parser.add_argument("--text-file", default="", help="UTF-8 text file containing scripts/corpus.")
    parser.add_argument("--docx-file", default="", help="DOCX file containing scripts/corpus.")
    parser.add_argument("--text", default="", help="Inline corpus text.")
    parser.add_argument("--account-url", default="", help="Optional Douyin user homepage URL.")
    parser.add_argument("--max-works", type=int, default=50, help="Works to inspect. Default: 50; hard limit: 200")
    parser.add_argument(
        "--output-dir",
        default=os.path.join(os.path.dirname(__file__), "profiles"),
        help="Directory used to save profiles.",
    )
    return parser.parse_args()


def safe_name(value):
    return "".join(ch for ch in str(value) if ch not in r'\/:*?"<>| ')[:60] or "profile"


def read_corpus(args):
    parts = []
    if args.text_file:
        with open(args.text_file, "r", encoding="utf-8") as f:
            parts.append(f.read())
    if args.docx_file:
        parts.append(read_docx(args.docx_file))
    if args.text:
        parts.append(args.text)
    return "\n\n".join(part.strip() for part in parts if part.strip())


def read_docx(path):
    try:
        from docx import Document
    except ModuleNotFoundError as exc:
        raise RuntimeError("Missing dependency: python-docx. Install with: python -m pip install python-docx") from exc
    document = Document(path)
    paragraphs = [p.text.strip() for p in document.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def top_phrases(text, limit=20):
    phrases = re.findall(r"[\u4e00-\u9fff]{2,12}", text or "")
    stop = {"这个", "就是", "我们", "他们", "然后", "因为", "所以", "如果", "不是", "一个", "什么", "可以"}
    counts = {}
    for phrase in phrases:
        if phrase in stop:
            continue
        counts[phrase] = counts.get(phrase, 0) + 1
    return [item[0] for item in sorted(counts.items(), key=lambda x: x[1], reverse=True)[:limit]]


def opening_samples(text, limit=8):
    lines = [line.strip() for line in re.split(r"[\n。！？!?]", text or "") if line.strip()]
    return lines[:limit]


def infer_tone(text):
    tone = []
    if any(word in text for word in ["一定", "千万", "记住", "别"]):
        tone.append("直接、有提醒感")
    if any(word in text for word in ["新手", "散户", "小白"]):
        tone.append("面向新手")
    if any(word in text for word in ["方法", "步骤", "信号", "判断"]):
        tone.append("教学感")
    if any(word in text for word in ["主力", "盘口", "资金", "趋势"]):
        tone.append("财经实战感")
    return tone or ["口语化", "实用导向"]


def fetch_account_snapshot(account_url, max_works):
    if not account_url:
        return None
    account_url = normalize_douyin_url(account_url)
    auth, _ = init()
    api = DouyinAPI()
    user_response = api.get_user_info(auth, account_url)
    user_info = compact_user_info(user_response)
    works = api.get_user_all_work_info(auth, account_url)[:max_works]
    return build_snapshot(account_url, user_info, works)


def build_profile(name, corpus, account_snapshot):
    work_titles = []
    top_works = []
    if account_snapshot:
        works = account_snapshot.get("works", [])
        ranked = sorted(
            works,
            key=lambda item: item.get("digg_count", 0) + item.get("collect_count", 0) * 2 + item.get("share_count", 0) * 3,
            reverse=True,
        )
        top_works = ranked[:5]
        work_titles = [item.get("title", "") for item in ranked[:12] if item.get("title")]

    combined_text = "\n".join([corpus, "\n".join(work_titles)])
    return {
        "name": name,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "positioning": "短视频IP风格档案",
        "tone": infer_tone(combined_text),
        "opening_samples": opening_samples(corpus, 8),
        "common_phrases": top_phrases(combined_text, 20),
        "structure_preference": "痛点开头 → 方法拆解 → 案例/判断标准 → 风险提醒 → 行动引导",
        "avoid": ["不承诺收益", "不荐股", "不夸大结果", "少用空泛鸡汤"],
        "cta_preference": "引导关注、评论或私信领取资料",
        "corpus_excerpt": corpus[:3000],
        "account": account_snapshot.get("profile") if account_snapshot else None,
        "top_account_works": top_works,
    }


def save_profile(profile, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.abspath(os.path.join(output_dir, f"{safe_name(profile['name'])}.json"))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)
    return path


def main():
    args = parse_args()
    args.max_works = min(max(args.max_works, 1), 200)
    corpus = read_corpus(args)
    account_snapshot = fetch_account_snapshot(args.account_url, args.max_works)
    profile = build_profile(args.name, corpus, account_snapshot)
    path = save_profile(profile, args.output_dir)
    print(f"Profile saved: {path}")
    print(f"name: {profile['name']}")
    print(f"tone: {', '.join(profile['tone'])}")
    print(f"common_phrases: {', '.join(profile['common_phrases'][:8])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
