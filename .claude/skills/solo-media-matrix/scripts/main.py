#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Solo Media Matrix V2.0
一人公司自媒体增长与变现作战台

Run:
  python scripts/main.py
  python scripts/main.py --json
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional


try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass


VERSION = "2.0.0"


class Platform(Enum):
    DOUYIN = "抖音"
    XIAOHONGSHU = "小红书"
    BILIBILI = "B站"
    SHIPINHAO = "视频号"
    WECHAT = "公众号"
    ZHIHU = "知乎"
    WEIBO = "微博"


PLATFORM_KNOWLEDGE: Dict[Platform, Dict[str, Any]] = {
    Platform.BILIBILI: {
        "form": "中长视频",
        "positioning": "系统教程、案例实操、长期搜索资产",
        "prime_time": "周末、12:00-14:00、18:00-22:00",
        "solo_score": 4,
        "coldstart": 3,
        "metrics": {"completion_rate": 0.45, "interaction_rate": 0.05},
        "monetization": "创作激励、花火商单、课程引流",
        "ad_threshold": 10000,
    },
    Platform.ZHIHU: {
        "form": "长图文/问答",
        "positioning": "专业回答、搜索流量、信任背书",
        "prime_time": "全天，优先抢新问题",
        "solo_score": 5,
        "coldstart": 3,
        "metrics": {"completion_rate": 0.60, "interaction_rate": 0.04},
        "monetization": "好物推荐、付费咨询、私域引流",
        "ad_threshold": 0,
    },
    Platform.WECHAT: {
        "form": "长图文",
        "positioning": "私域沉淀、产品说明、长期复购",
        "prime_time": "工作日 07:00-09:00、12:00-14:00",
        "solo_score": 4,
        "coldstart": 4,
        "metrics": {"open_rate": 0.05, "interaction_rate": 0.03},
        "monetization": "流量主、课程、小册、社群",
        "ad_threshold": 500,
    },
    Platform.XIAOHONGSHU: {
        "form": "图文/短视频",
        "positioning": "攻略卡片、真实体验、收藏型内容",
        "prime_time": "20:00-23:00、07:00-09:00",
        "solo_score": 4,
        "coldstart": 3,
        "metrics": {"completion_rate": 0.35, "interaction_rate": 0.05},
        "monetization": "蒲公英商单、资料包引流、低价产品",
        "ad_threshold": 1000,
    },
    Platform.SHIPINHAO: {
        "form": "短视频",
        "positioning": "1分钟可转发资产，承接微信生态",
        "prime_time": "12:00-14:00、20:00-22:00",
        "solo_score": 5,
        "coldstart": 2,
        "metrics": {"completion_rate": 0.40, "interaction_rate": 0.04},
        "monetization": "微信私域、直播、带货、服务咨询",
        "ad_threshold": 100,
    },
    Platform.DOUYIN: {
        "form": "短视频",
        "positioning": "强钩子、强节奏、强场景演示",
        "prime_time": "18:00-22:00",
        "solo_score": 2,
        "coldstart": 4,
        "metrics": {"completion_rate": 0.30, "interaction_rate": 0.04},
        "monetization": "星图商单、团购/带货、直播",
        "ad_threshold": 1000,
    },
    Platform.WEIBO: {
        "form": "短图文/热点",
        "positioning": "热点借势、观点扩散、事件评论",
        "prime_time": "热点发生时即时",
        "solo_score": 3,
        "coldstart": 2,
        "metrics": {"interaction_rate": 0.03},
        "monetization": "微任务、品牌曝光",
        "ad_threshold": 1000,
    },
}


FIELD_MATRIX: Dict[str, Dict[str, Any]] = {
    "编程技术": {
        "primary": [Platform.BILIBILI, Platform.ZHIHU],
        "secondary": [Platform.WECHAT, Platform.XIAOHONGSHU, Platform.SHIPINHAO],
        "pause": [Platform.DOUYIN],
        "reason": "技术内容需要代码细节、搜索沉淀和信任背书，短视频只适合拆片辅助。",
    },
    "知识付费": {
        "primary": [Platform.BILIBILI, Platform.WECHAT],
        "secondary": [Platform.ZHIHU, Platform.SHIPINHAO],
        "pause": [Platform.WEIBO],
        "reason": "高转化来自长内容信任和私域承接，避免只追泛流量。",
    },
    "职场效率": {
        "primary": [Platform.XIAOHONGSHU, Platform.ZHIHU],
        "secondary": [Platform.WECHAT, Platform.SHIPINHAO],
        "pause": [],
        "reason": "方法论和工具清单适合收藏、搜索和私域沉淀。",
    },
    "美妆护肤": {
        "primary": [Platform.XIAOHONGSHU, Platform.DOUYIN],
        "secondary": [Platform.SHIPINHAO, Platform.BILIBILI],
        "pause": [Platform.ZHIHU],
        "reason": "视觉化内容需要强展示和真实体验，小红书/抖音更容易验证。",
    },
    "本地生活": {
        "primary": [Platform.DOUYIN, Platform.XIAOHONGSHU],
        "secondary": [Platform.SHIPINHAO, Platform.WEIBO],
        "pause": [Platform.BILIBILI],
        "reason": "本地生活依赖即时推荐、搜索种草和交易链路。",
    },
}


TOPIC_DATABASE: Dict[str, List[Dict[str, Any]]] = {
    "编程技术": [
        {"title": "Python自动化办公完全指南", "heat": 5, "potential": 5, "difficulty": 2},
        {"title": "零基础如何系统学习Python", "heat": 5, "potential": 4, "difficulty": 3},
        {"title": "用Python自动生成Excel周报", "heat": 4, "potential": 5, "difficulty": 2},
        {"title": "AI时代还要不要学编程", "heat": 5, "potential": 5, "difficulty": 3},
    ],
    "知识付费": [
        {"title": "如何把经验做成第一款付费小产品", "heat": 5, "potential": 5, "difficulty": 3},
        {"title": "一人公司如何设计9.9到999元产品梯度", "heat": 4, "potential": 5, "difficulty": 3},
        {"title": "低粉账号如何验证知识付费需求", "heat": 4, "potential": 4, "difficulty": 2},
    ],
    "职场效率": [
        {"title": "如何用AI每天省下1小时重复工作", "heat": 5, "potential": 5, "difficulty": 2},
        {"title": "普通人最值得搭建的个人效率系统", "heat": 4, "potential": 4, "difficulty": 3},
        {"title": "Excel、Notion、飞书到底怎么选", "heat": 4, "potential": 5, "difficulty": 2},
    ],
}


CSV_TEMPLATE = """日期,平台,内容标题,播放量,点赞数,评论数,收藏数,分享数,粉丝增长,完播率
2026-05-20,B站,Python自动化办公教程,45000,2800,450,1200,350,320,0.55
2026-05-20,知乎,Python自动化办公解析,12000,650,180,420,95,85,0.72
2026-05-20,小红书,Python办公攻略,3000,380,95,180,28,28,0.45
"""


@dataclass
class FounderProfile:
    field: str
    offer: str
    target_customer: str
    weekly_hours: int
    goal: str
    existing_platforms: Dict[str, int]


@dataclass
class CoreContent:
    title: str
    format: str
    summary: str


class MatrixPlanner:
    @staticmethod
    def recommend_platforms(profile: FounderProfile) -> Dict[str, Any]:
        matrix = FIELD_MATRIX.get(profile.field, FIELD_MATRIX["知识付费"])
        max_platforms = 2 if profile.weekly_hours < 6 else 3 if profile.weekly_hours < 12 else 4
        primary = matrix["primary"][:2]
        secondary = matrix["secondary"][: max(0, max_platforms - len(primary))]

        return {
            "field": profile.field,
            "goal": profile.goal,
            "weekly_hours": profile.weekly_hours,
            "primary": [MatrixPlanner._platform_card(p, profile) for p in primary],
            "secondary": [MatrixPlanner._platform_card(p, profile) for p in secondary],
            "pause": [p.value for p in matrix["pause"]],
            "reason": matrix["reason"],
            "max_active_platforms": max_platforms,
            "time_budget": MatrixPlanner.calculate_energy_budget(profile.weekly_hours, len(primary), len(secondary)),
        }

    @staticmethod
    def _platform_card(platform: Platform, profile: FounderProfile) -> Dict[str, Any]:
        kb = PLATFORM_KNOWLEDGE[platform]
        followers = profile.existing_platforms.get(platform.value, 0)
        return {
            "platform": platform.value,
            "form": kb["form"],
            "positioning": kb["positioning"],
            "prime_time": kb["prime_time"],
            "followers": followers,
            "coldstart": kb["coldstart"],
            "ad_threshold": kb["ad_threshold"],
            "threshold_status": "已达参考门槛" if followers >= kb["ad_threshold"] else f"距参考门槛差 {kb['ad_threshold'] - followers} 粉",
        }

    @staticmethod
    def calculate_energy_budget(weekly_hours: int, primary_count: int, secondary_count: int) -> Dict[str, str]:
        return {
            "选题策划": f"{max(1, round(weekly_hours * 0.15, 1))}h",
            "核心内容生产": f"{round(weekly_hours * 0.45, 1)}h",
            "拆解改写": f"{round(weekly_hours * 0.20, 1)}h",
            "分发互动": f"{round(weekly_hours * 0.10, 1)}h",
            "数据复盘": f"{round(weekly_hours * 0.10, 1)}h",
            "active_mix": f"{primary_count}个主平台 + {secondary_count}个辅助平台",
        }


class TopicScheduler:
    @staticmethod
    def score_topic(search_heat: int, interaction_potential: int, creation_difficulty: int) -> Dict[str, Any]:
        for name, value in {
            "search_heat": search_heat,
            "interaction_potential": interaction_potential,
            "creation_difficulty": creation_difficulty,
        }.items():
            if value < 1 or value > 5:
                raise ValueError(f"{name} must be between 1 and 5")

        difficulty_bonus = 6 - creation_difficulty
        score = search_heat * interaction_potential * difficulty_bonus / 125 * 100
        if score >= 80:
            level = "优先创作"
        elif score >= 60:
            level = "本周备选"
        elif score >= 40:
            level = "放入题库"
        else:
            level = "暂不投入"
        return {
            "score": round(score, 1),
            "level": level,
            "formula": f"{search_heat} × {interaction_potential} × (6 - {creation_difficulty}) / 125 × 100",
            "breakdown": {
                "搜索热度": search_heat,
                "互动潜力": interaction_potential,
                "创作难度": creation_difficulty,
                "难度加成": difficulty_bonus,
            },
        }

    @staticmethod
    def mine_topics(field: str) -> List[Dict[str, Any]]:
        topics = TOPIC_DATABASE.get(field, TOPIC_DATABASE["知识付费"])
        scored = []
        for topic in topics:
            score = TopicScheduler.score_topic(topic["heat"], topic["potential"], topic["difficulty"])
            scored.append({**topic, **score})
        return sorted(scored, key=lambda item: item["score"], reverse=True)

    @staticmethod
    def generate_calendar(
        primary: Iterable[str],
        secondary: Iterable[str],
        core_title: str,
        weekly_hours: int,
    ) -> List[Dict[str, Any]]:
        primary_list = list(primary)
        secondary_list = list(secondary)
        tasks = [
            ("周一", "选题确认 + 素材整理", "全平台", f"确定《{core_title}》角度和资料包", 1.0, "选题评分>=60"),
            ("周二", "核心内容生产", primary_list[0] if primary_list else "主平台", "完成长文/长视频脚本初稿", round(weekly_hours * 0.25, 1), "脚本可发布"),
            ("周三", "主平台发布", primary_list[0] if primary_list else "主平台", "发布核心内容并置顶评论引导资料包", 1.0, "收藏率/完播率"),
            ("周四", "搜索平台改写", primary_list[1] if len(primary_list) > 1 else "知乎/公众号", "改写为问答或长图文", 1.5, "阅读完成率"),
            ("周五", "辅助平台拆片", secondary_list[0] if secondary_list else "辅助平台", "拆出2-3条短内容/图文卡片", 1.5, "互动率"),
            ("周六", "互动与私域承接", "全平台", "回复评论、收集问题、更新FAQ", 1.0, "私信/领取数"),
            ("周日", "数据复盘 + 下周实验", "全平台", "记录指标，决定加码/降频", 1.0, "下周动作清单"),
        ]
        return [
            {"day": day, "task": task, "platform": platform, "output": output, "hours": hours, "metric": metric}
            for day, task, platform, output, hours, metric in tasks
        ]


class ContentKitchen:
    PRODUCTION_TIME = {
        Platform.BILIBILI: 240,
        Platform.ZHIHU: 90,
        Platform.WECHAT: 120,
        Platform.XIAOHONGSHU: 45,
        Platform.SHIPINHAO: 45,
        Platform.DOUYIN: 60,
        Platform.WEIBO: 15,
    }

    @staticmethod
    def dismantle_content(content: CoreContent, target_platforms: List[str]) -> List[Dict[str, Any]]:
        output = []
        for platform_name in target_platforms:
            platform = platform_from_name(platform_name)
            if platform is None:
                continue
            output.append(ContentKitchen._adapt(content, platform))
        return output

    @staticmethod
    def _adapt(content: CoreContent, platform: Platform) -> Dict[str, Any]:
        templates = {
            Platform.BILIBILI: {
                "title": f"{content.title}：从入门到实战",
                "hook": f"这期用一个真实场景讲清楚：{content.title}。",
                "deliverable": "8-12分钟教程视频 + 代码/资料包",
                "publish_goal": "收藏、投币、搜索沉淀",
            },
            Platform.ZHIHU: {
                "title": f"如何系统掌握{content.title}？",
                "hook": "先给结论，再拆步骤，最后给可复制模板。",
                "deliverable": "2000字问答 + 案例 + 资料包入口",
                "publish_goal": "赞同、收藏、搜索长尾",
            },
            Platform.WECHAT: {
                "title": f"{content.title}：一人公司实战手册",
                "hook": "把散点经验整理成可复用流程，适合私域沉淀。",
                "deliverable": "长文 + 产品说明 + 领取入口",
                "publish_goal": "打开率、转发、私域转化",
            },
            Platform.XIAOHONGSHU: {
                "title": f"{content.title}｜可直接照做",
                "hook": "封面突出结果：省时间、少踩坑、可复制。",
                "deliverable": "6-9页攻略卡片 + 清单式正文",
                "publish_goal": "收藏率、评论问题",
            },
            Platform.SHIPINHAO: {
                "title": f"1分钟看懂：{content.title}",
                "hook": "用一个前后对比展示价值。",
                "deliverable": "60秒短视频 + 评论区资料引导",
                "publish_goal": "转发、私信、社群流动",
            },
            Platform.DOUYIN: {
                "title": f"别再低效了，{content.title}这样做",
                "hook": "前三秒展示痛点和结果差异。",
                "deliverable": "30-60秒强节奏短视频",
                "publish_goal": "完播率、收藏",
            },
            Platform.WEIBO: {
                "title": f"{content.title}的3个关键点",
                "hook": "用观点摘要接热点或行业讨论。",
                "deliverable": "短图文 + 九宫格要点",
                "publish_goal": "转发、讨论",
            },
        }
        item = templates[platform]
        return {
            "platform": platform.value,
            "content_form": PLATFORM_KNOWLEDGE[platform]["form"],
            "title": item["title"],
            "hook": item["hook"],
            "deliverable": item["deliverable"],
            "production_minutes": ContentKitchen.PRODUCTION_TIME[platform],
            "publish_goal": item["publish_goal"],
            "prime_time": PLATFORM_KNOWLEDGE[platform]["prime_time"],
        }


class AnalyticsBoard:
    NUMERIC_FIELDS = ["播放量", "点赞数", "评论数", "收藏数", "分享数", "粉丝增长", "完播率"]

    @staticmethod
    def import_from_csv(csv_content: str) -> List[Dict[str, Any]]:
        rows = []
        reader = csv.DictReader(io.StringIO(csv_content.strip()))
        for row in reader:
            for field in AnalyticsBoard.NUMERIC_FIELDS:
                row[field] = safe_float(row.get(field, 0))
            plays = row.get("播放量", 0)
            if plays > 0:
                row["互动率"] = round((row["点赞数"] + row["评论数"] + row["收藏数"] + row["分享数"]) / plays, 4)
                row["涨粉率"] = round(row["粉丝增长"] / plays, 4)
            else:
                row["互动率"] = 0
                row["涨粉率"] = 0
            rows.append(row)
        return rows

    @staticmethod
    def cross_platform_compare(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not rows:
            return {"summary": "没有可分析的数据", "platforms": [], "insights": []}

        platforms = []
        for row in rows:
            platform = row.get("平台", "")
            kb = PLATFORM_KNOWLEDGE.get(platform_from_name(platform))
            avg_interaction = kb.get("metrics", {}).get("interaction_rate", 0.04) if kb else 0.04
            completion_line = kb.get("metrics", {}).get("completion_rate", 0.35) if kb else 0.35
            interaction = row.get("互动率", 0)
            completion = row.get("完播率", 0)
            if interaction >= avg_interaction * 1.5 or completion >= completion_line * 1.2:
                decision = "加码"
            elif interaction < avg_interaction * 0.7 or completion < completion_line * 0.7:
                decision = "优化/降频"
            else:
                decision = "保持测试"
            platforms.append({
                "平台": platform,
                "标题": row.get("内容标题", ""),
                "播放量": int(row.get("播放量", 0)),
                "互动率": interaction,
                "完播率": completion,
                "涨粉": int(row.get("粉丝增长", 0)),
                "判断": decision,
            })

        best = sorted(platforms, key=lambda item: (item["互动率"], item["涨粉"]), reverse=True)[0]
        insights = [
            f"最该加码：{best['平台']}，互动率 {best['互动率']:.1%}，涨粉 {best['涨粉']}。",
            "下周只做一个变量实验：标题钩子、封面、时长或结尾转化入口，不要同时改太多。",
        ]
        return {"summary": f"{best['平台']}表现最佳", "platforms": platforms, "insights": insights}

    @staticmethod
    def csv_template() -> str:
        return CSV_TEMPLATE


class MonetizationPlanner:
    @staticmethod
    def match_monetization_model(profile: FounderProfile) -> Dict[str, Any]:
        total_followers = sum(profile.existing_platforms.values())
        if total_followers < 1000:
            stage = "验证期"
            action = "先用免费资料包换取私信/社群线索，验证痛点和表达。"
        elif total_followers < 10000:
            stage = "小产品期"
            action = "上线9.9-99元模板/小册，测试付费意愿。"
        else:
            stage = "产品矩阵期"
            action = "搭建低价小产品 + 中价训练营 + 高价咨询/陪跑。"

        return {
            "stage": stage,
            "total_followers": total_followers,
            "this_week_action": action,
            "product_ladder": [
                {"level": "免费", "product": f"{profile.field}资料包/检查清单", "purpose": "私域引流"},
                {"level": "低价 9.9-99", "product": profile.offer, "purpose": "验证需求"},
                {"level": "中价 199-499", "product": f"{profile.field}训练营/系统课", "purpose": "规模化交付"},
                {"level": "高价 1000+", "product": "1对1咨询/陪跑/企业服务", "purpose": "利润和案例"},
            ],
            "risk_note": "平台门槛和合规要求变化快，正式接商单或投放前以官方后台为准。",
        }


class PlatformRadar:
    SENSITIVE_PATTERNS = ["最", "第一", "100%", "稳赚", "包过", "加微信", "私加", "绝对"]

    @staticmethod
    def detect_violation_risk(text: str) -> Dict[str, Any]:
        hits = [word for word in PlatformRadar.SENSITIVE_PATTERNS if word in text]
        return {
            "risk_level": "高" if len(hits) >= 3 else "中" if hits else "低",
            "hits": hits,
            "suggestion": "替换绝对化承诺，站外引流改为平台允许的表达。" if hits else "未发现明显高风险词，仍需按平台规则复核。",
        }


class OPCWeeklyOperator:
    @staticmethod
    def generate_weekly_plan(
        profile: FounderProfile,
        core_content: CoreContent,
        metrics_csv: Optional[str] = None,
    ) -> Dict[str, Any]:
        platform_plan = MatrixPlanner.recommend_platforms(profile)
        primary_names = [p["platform"] for p in platform_plan["primary"]]
        secondary_names = [p["platform"] for p in platform_plan["secondary"]]
        targets = primary_names + secondary_names
        content_versions = ContentKitchen.dismantle_content(core_content, targets)
        calendar = TopicScheduler.generate_calendar(primary_names, secondary_names, core_content.title, profile.weekly_hours)
        topics = TopicScheduler.mine_topics(profile.field)[:5]
        monetization = MonetizationPlanner.match_monetization_model(profile)
        metrics_review = AnalyticsBoard.cross_platform_compare(AnalyticsBoard.import_from_csv(metrics_csv)) if metrics_csv else None

        return {
            "version": VERSION,
            "profile": asdict(profile),
            "core_content": asdict(core_content),
            "operating_judgement": {
                "weekly_goal": profile.goal,
                "primary_platforms": primary_names,
                "secondary_platforms": secondary_names,
                "paused_platforms": platform_plan["pause"],
                "reason": platform_plan["reason"],
                "time_budget": platform_plan["time_budget"],
            },
            "topic_candidates": topics,
            "content_versions": content_versions,
            "calendar": calendar,
            "metrics_review": metrics_review,
            "monetization": monetization,
            "today_actions": [
                f"确认本周唯一核心选题：《{core_content.title}》。",
                f"用 {primary_names[0] if primary_names else '主平台'} 的长内容作为母内容，不为每个平台单独重写。",
                "准备一个免费资料包或清单，在评论/私信/公众号中承接需求。",
            ],
            "do_not_do": [
                "本周不新增超过计划外的平台。",
                "不做全平台日更。",
                "不同时测试标题、封面、时长、转化入口四个变量。",
            ],
        }

    @staticmethod
    def to_markdown(plan: Dict[str, Any]) -> str:
        judgement = plan["operating_judgement"]
        lines = [
            f"# Solo Media Matrix V{plan['version']} 一人公司自媒体作战计划",
            "",
            "## 经营判断",
            f"- 本周目标: {judgement['weekly_goal']}",
            f"- 主平台: {', '.join(judgement['primary_platforms'])}",
            f"- 辅助平台: {', '.join(judgement['secondary_platforms']) or '无'}",
            f"- 暂停平台: {', '.join(judgement['paused_platforms']) or '无'}",
            f"- 核心选题: {plan['core_content']['title']}",
            f"- 时间预算: {plan['profile']['weekly_hours']}小时/周",
            f"- 判断依据: {judgement['reason']}",
            "",
            "## 一鱼多吃拆解",
            "| 平台 | 内容形态 | 标题/Hook | 交付物 | 预计耗时 | 发布目标 |",
            "|---|---|---|---|---:|---|",
        ]
        for item in plan["content_versions"]:
            lines.append(
                f"| {item['platform']} | {item['content_form']} | {item['title']} / {item['hook']} | "
                f"{item['deliverable']} | {item['production_minutes']}分钟 | {item['publish_goal']} |"
            )

        lines.extend([
            "",
            "## 7天排期",
            "| 日期 | 任务 | 平台 | 产出 | 耗时 | 指标 |",
            "|---|---|---|---|---:|---|",
        ])
        for item in plan["calendar"]:
            lines.append(f"| {item['day']} | {item['task']} | {item['platform']} | {item['output']} | {item['hours']}h | {item['metric']} |")

        lines.extend([
            "",
            "## 选题候选",
            "| 选题 | 分数 | 判断 |",
            "|---|---:|---|",
        ])
        for item in plan["topic_candidates"]:
            lines.append(f"| {item['title']} | {item['score']} | {item['level']} |")

        if plan.get("metrics_review"):
            lines.extend([
                "",
                "## 数据复盘",
                f"- 结论: {plan['metrics_review']['summary']}",
                "| 平台 | 播放/阅读 | 互动率 | 完播率 | 涨粉 | 判断 |",
                "|---|---:|---:|---:|---:|---|",
            ])
            for item in plan["metrics_review"]["platforms"]:
                lines.append(
                    f"| {item['平台']} | {item['播放量']} | {item['互动率']:.1%} | "
                    f"{item['完播率']:.1%} | {item['涨粉']} | {item['判断']} |"
                )
            for insight in plan["metrics_review"]["insights"]:
                lines.append(f"- {insight}")

        monetization = plan["monetization"]
        lines.extend([
            "",
            "## 变现动作",
            f"- 阶段: {monetization['stage']}",
            f"- 本周验证: {monetization['this_week_action']}",
            "| 层级 | 产品 | 目的 |",
            "|---|---|---|",
        ])
        for item in monetization["product_ladder"]:
            lines.append(f"| {item['level']} | {item['product']} | {item['purpose']} |")

        lines.extend([
            "",
            "## 今日动作",
        ])
        for index, action in enumerate(plan["today_actions"], 1):
            lines.append(f"{index}. {action}")

        lines.extend([
            "",
            "## 不做清单",
        ])
        for action in plan["do_not_do"]:
            lines.append(f"- {action}")

        return "\n".join(lines)


def platform_from_name(name: str) -> Optional[Platform]:
    for platform in Platform:
        if platform.value == name:
            return platform
    return None


def safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def demo_profile() -> FounderProfile:
    return FounderProfile(
        field="编程技术",
        offer="Python自动化办公小册和模板包",
        target_customer="想用AI和Python提升办公效率的职场人",
        weekly_hours=10,
        goal="30天内涨粉并验证知识付费",
        existing_platforms={"B站": 3000, "知乎": 1200, "小红书": 500},
    )


def demo_content() -> CoreContent:
    return CoreContent(
        title="Python自动化办公完全指南",
        format="长文",
        summary="用Python处理Excel报表、自动生成PPT、批量处理邮件，让职场人减少重复劳动。",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Solo Media Matrix V2.0 demo")
    parser.add_argument("--json", action="store_true", help="print JSON instead of Markdown")
    parser.add_argument("--with-metrics", action="store_true", help="include sample CSV metrics review")
    args = parser.parse_args()

    metrics = CSV_TEMPLATE if args.with_metrics else None
    plan = OPCWeeklyOperator.generate_weekly_plan(demo_profile(), demo_content(), metrics)
    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    else:
        print(OPCWeeklyOperator.to_markdown(plan))


if __name__ == "__main__":
    main()
