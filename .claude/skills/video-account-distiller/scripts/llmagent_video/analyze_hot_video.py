# coding=utf-8
import argparse
import json
import os
import re
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dy_apis.douyin_api import DouyinAPI
from fetch_single_work import handle_work_info, save_json, save_raw_json, timestamp_to_str
from url_util import normalize_douyin_url
from utils.common_util import init


def parse_args():
    parser = argparse.ArgumentParser(description="Analyze a hot Douyin video and write a new script.")
    parser.add_argument("url", help="Douyin work URL.")
    parser.add_argument(
        "--requirement",
        "-r",
        default="",
        help="Your writing requirement, such as target audience, product, topic, tone, or CTA.",
    )
    parser.add_argument(
        "--topic",
        "-t",
        default="",
        help="New script topic. If omitted, the original video's topic is reused.",
    )
    parser.add_argument(
        "--output-dir",
        default=os.path.join(os.path.dirname(__file__), "outputs", "hot_video_analysis"),
        help="Directory used to save analysis and script. Default: llmagent_video/outputs/hot_video_analysis",
    )
    parser.add_argument(
        "--transcript",
        default="",
        help="Optional transcript txt path. If omitted, the script tries outputs/transcripts/{work_id}.transcript.txt.",
    )
    return parser.parse_args()


def keyword_list(work_info):
    values = []
    values.extend(work_info.get("topics") or [])
    for text in [work_info.get("item_title", ""), work_info.get("desc", ""), work_info.get("script_summary", "")]:
        values.extend(re.findall(r"[\u4e00-\u9fff]{2,8}", text))
    seen = set()
    result = []
    for value in values:
        value = value.strip("# ，。,.")
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result[:12]


def infer_hook(work_info):
    title = work_info.get("item_title") or work_info.get("title") or ""
    if any(word in title for word in ["学会", "轻松", "识别", "看懂"]):
        return "结果承诺型开头：先告诉用户看完能获得什么能力。"
    if any(word in title for word in ["不要", "别再", "千万"]):
        return "避坑警示型开头：用风险提醒制造停留。"
    if any(word in title for word in ["为什么", "怎么", "如何"]):
        return "问题驱动型开头：用一个具体疑问拉住目标用户。"
    return "利益点开头：直接抛出一个用户关心的结果。"


def infer_structure(work_info):
    summary = work_info.get("script_summary") or ""
    chapters = work_info.get("script_chapters") or []
    if chapters:
        middle = [f"{item.get('desc', '')}: {item.get('detail', '')}" for item in chapters]
    elif summary:
        middle = [summary]
    else:
        middle = ["标题/文案提出明确收益", "中段给出概念解释或判断标准", "结尾用行动建议或关注理由收束"]

    return {
        "hook": infer_hook(work_info),
        "opening": work_info.get("item_title") or work_info.get("title", ""),
        "middle": middle,
        "ending": "以明确收益或可执行动作结尾，降低用户理解成本。",
    }


def load_transcript(work_id, transcript_path):
    if not transcript_path:
        transcript_path = os.path.join(
            os.path.dirname(__file__), "outputs", "transcripts", f"{work_id}.transcript.txt"
        )
    if not os.path.exists(transcript_path):
        return "", ""
    with open(transcript_path, "r", encoding="utf-8") as f:
        return f.read().strip(), os.path.abspath(transcript_path)


def analyze_video(work_info, transcript_text=""):
    stats = {
        "digg_count": work_info.get("digg_count", 0),
        "comment_count": work_info.get("comment_count", 0),
        "collect_count": work_info.get("collect_count", 0),
        "share_count": work_info.get("share_count", 0),
    }
    return {
        "source": {
            "work_id": work_info.get("work_id"),
            "work_url": work_info.get("work_url"),
            "author": work_info.get("nickname"),
            "created_at": work_info.get("create_time_text"),
            "title": work_info.get("item_title") or work_info.get("title"),
            "desc": work_info.get("desc"),
            "summary": work_info.get("script_summary"),
            "transcript": transcript_text,
            "topics": work_info.get("topics"),
            "stats": stats,
        },
        "viral_breakdown": {
            "target_user": "对这个话题已经有兴趣、但缺少判断方法的新手用户。",
            "core_promise": work_info.get("item_title") or work_info.get("script_summary") or work_info.get("title"),
            "hook_type": infer_hook(work_info),
            "keywords": keyword_list(work_info),
            "content_structure": infer_structure(work_info),
            "why_it_works": [
                "开头给出明确收益，用户能快速判断值不值得看。",
                "主题聚焦一个具体问题，减少泛泛而谈。",
                "文案里有垂直标签，利于平台识别内容人群。",
                "收藏数相对不低，说明内容带有方法论或复看价值。",
            ],
            "transcript_based_notes": build_transcript_notes(transcript_text),
        },
    }


def build_transcript_notes(transcript_text):
    if not transcript_text:
        return ["未检测到逐字稿，当前仅基于标题、摘要和互动数据拆解。"]

    lines = [line.strip() for line in transcript_text.splitlines() if line.strip()]
    opening = " / ".join(lines[:4])
    ending = " / ".join(lines[-4:])
    method_markers = [line for line in lines if re.match(r"^[一二三四五六七八九十]", line)]
    return [
        f"前3-8秒开头：{opening}",
        f"中段方法点数量：约 {len(method_markers) or '多'} 个",
        f"结尾动作：{ending}",
        "结构特征：先解释概念，再连续给清单式判断标准，最后引导继续学习。",
    ]


def pick_topic(work_info, topic):
    if topic:
        return topic
    return work_info.get("item_title") or work_info.get("script_summary") or work_info.get("title", "")


def write_script(work_info, analysis, requirement, topic):
    topic = pick_topic(work_info, topic)
    keywords = analysis["viral_breakdown"]["keywords"][:5]
    keyword_text = "、".join(keywords) if keywords else "核心关键词"
    requirement_text = requirement or "面向普通新手，语气直接、口语化，输出一条60秒以内的短视频脚本。"
    transcript = analysis["source"].get("transcript") or ""
    transcript_hint = transcript[:500] if transcript else work_info.get("script_summary", "")

    return f"""# 爆款拆解后改写脚本

## 你的要求
{requirement_text}

## 选题
{topic}

## 拆解结论
- 开头类型：{analysis["viral_breakdown"]["hook_type"]}
- 核心承诺：{analysis["viral_breakdown"]["core_promise"]}
- 可借用关键词：{keyword_text}
- 逐字稿依据：{transcript_hint}

## 成片脚本
【开头 0-3秒】
很多人看{topic}，其实只盯着表面，真正有用的是背后的判断方法。

【痛点 3-10秒】
你以为自己看懂了，其实只是看到了结果。真正容易踩坑的地方，是不知道该看哪几个信号。

【方法 10-40秒】
记住三个步骤：
第一，先看最明显的变化，它代表用户第一眼能感受到的冲突。
第二，看这个变化有没有持续，如果只是一下子出现，参考价值就要打折。
第三，把它和你的目标结合起来，不要单独看一个指标就下结论。

【案例化表达 40-52秒】
比如原视频讲的是：{work_info.get("script_summary") or work_info.get("item_title") or work_info.get("desc")}
它的厉害之处不是信息多，而是把复杂判断压缩成了普通人能听懂的动作。

【结尾 52-60秒】
所以你下次再看{topic}，别急着下判断，先按这三个步骤过一遍。想要我继续拆类似案例，可以把链接发过来。

## 拍摄提示
- 语速：偏快，但每个步骤之间停顿半秒。
- 画面：开头直接放结论字幕，中段用三条列表字幕。
- 标题建议：别只看表面，真正有用的是这3个信号。
"""


def save_text(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    args = parse_args()
    auth, _ = init()
    response = DouyinAPI().get_work_info(auth, normalize_douyin_url(args.url))
    if "aweme_detail" not in response or not response["aweme_detail"]:
        print("Fetch failed: response has no aweme_detail.")
        print(json.dumps(response, ensure_ascii=False, indent=2))
        return 1

    work_info = handle_work_info(response["aweme_detail"])
    work_info["create_time_text"] = timestamp_to_str(work_info["create_time"])
    transcript_text, transcript_path = load_transcript(work_info["work_id"], args.transcript)
    analysis = analyze_video(work_info, transcript_text)
    script = write_script(work_info, analysis, args.requirement, args.topic)

    os.makedirs(args.output_dir, exist_ok=True)
    work_id = work_info["work_id"]
    work_path = save_json(work_info, args.output_dir)
    raw_path = save_raw_json(response, args.output_dir, work_id)
    analysis_path = os.path.abspath(os.path.join(args.output_dir, f"{work_id}.analysis.json"))
    script_path = os.path.abspath(os.path.join(args.output_dir, f"{work_id}.script.md"))

    with open(analysis_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    save_text(script_path, script)

    print("Analyze success")
    print(f"title: {analysis['source']['title']}")
    print(f"summary: {analysis['source']['summary']}")
    print(f"hook_type: {analysis['viral_breakdown']['hook_type']}")
    print("llm: local-template")
    print(f"analysis: {analysis_path}")
    print(f"script: {script_path}")
    if transcript_path:
        print(f"transcript: {transcript_path}")
    print(f"work_json: {work_path}")
    print(f"raw_json: {raw_path}")
    print("")
    print(script)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
