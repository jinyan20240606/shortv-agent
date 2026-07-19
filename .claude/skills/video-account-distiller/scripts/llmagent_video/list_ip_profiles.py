# coding=utf-8
import argparse
import json
import os


def parse_args():
    parser = argparse.ArgumentParser(description="List saved IP style profiles.")
    parser.add_argument(
        "--profiles-dir",
        default=os.path.join(os.path.dirname(__file__), "profiles"),
        help="Directory containing profile JSON files.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    return parser.parse_args()


def clean_text(value):
    return str(value or "").strip()


def infer_description(profile):
    if clean_text(profile.get("name")) == "小白投教":
        return "技术分析 / 新手教学"
    if clean_text(profile.get("name")) == "default_finance_teacher":
        return "急救财经 / 新手解释"
    account = profile.get("account") or {}
    tone = [clean_text(item) for item in profile.get("tone", []) if clean_text(item)]
    text = " ".join(
        [
            clean_text(profile.get("positioning")),
            " ".join(tone),
            clean_text(profile.get("structure_preference")),
            clean_text(profile.get("corpus_excerpt")),
            " ".join(clean_text(work.get("title")) for work in profile.get("top_account_works", [])[:5]),
        ]
    )
    tags = []
    if any(word in text for word in ["技术", "盘口", "主力", "CPI", "加息", "财经", "股票", "资金", "趋势"]):
        tags.append("技术分析")
    if any(word in text for word in ["新手", "小白", "教学", "方法", "步骤", "信号"]):
        tags.append("新手教学")
    if any(word in text for word in ["犀利", "吐槽", "直接", "提醒"]):
        tags.append("直接犀利")
    if any(word in text for word in ["情绪", "观点", "宏观", "政策"]):
        tags.append("观点解读")
    if not tags and account.get("nickname"):
        tags.append("账号风格")
    if not tags:
        tags.append("自定义风格")
    return " / ".join(tags[:2])


def display_name(profile, filename):
    account = profile.get("account") or {}
    raw = clean_text(profile.get("display_name")) or clean_text(profile.get("name")) or os.path.splitext(filename)[0]
    nickname = clean_text(account.get("nickname"))
    if nickname and raw.lower() in {"profile", "style", "test_style"}:
        raw = nickname
    return raw


def load_profiles(profiles_dir):
    if not os.path.isdir(profiles_dir):
        return []

    profiles = []
    for filename in sorted(os.listdir(profiles_dir)):
        if not filename.lower().endswith(".json"):
            continue
        path = os.path.abspath(os.path.join(profiles_dir, filename))
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue

        account = data.get("account") or {}
        name = clean_text(data.get("name")) or os.path.splitext(filename)[0]
        label = display_name(data, filename)
        profiles.append(
            {
                "name": name,
                "label": label,
                "description": infer_description(data),
                "is_default": name == "小白投教",
                "created_at": data.get("created_at", ""),
                "tone": data.get("tone", []),
                "source": "账号主页+语料" if account and data.get("corpus_excerpt") else "账号主页" if account else "语料/文档",
                "account_nickname": account.get("nickname", ""),
                "path": path,
            }
        )
    return sorted(profiles, key=lambda item: (not item.get("is_default"), item["label"]))


def print_human(profiles):
    if not profiles:
        print("暂无已保存风格。")
        print("新建方式：发送“创建IP风格 + 风格名称 + 抖音账号主页/语料文档”。")
        print("例：创建IP风格 毛驴老师 https://www.douyin.com/user/xxx")
        return

    print("可选风格：")
    for index, profile in enumerate(profiles, 1):
        suffix = " · 默认" if profile.get("is_default") else ""
        print(f"{index}. {profile['label']}（{profile['description']}）{suffix}")
    print("")
    print("新建风格：发送“创建IP风格 + 风格名称 + 抖音账号主页/语料文档”。")
    print("例：创建IP风格 毛驴老师 https://www.douyin.com/user/xxx")


def main():
    args = parse_args()
    profiles = load_profiles(args.profiles_dir)
    if args.json:
        print(json.dumps(profiles, ensure_ascii=False, indent=2))
    else:
        print_human(profiles)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
