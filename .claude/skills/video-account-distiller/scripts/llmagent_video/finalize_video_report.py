# coding=utf-8
import argparse
import html
import json
import os
import re


SECTION_PATTERNS = [
    ("一、这个视频为什么能爆", re.compile(r"^\s*(?:#{1,6}\s*)?一[、.．]\s*这个视频为什么能爆.*$", re.M)),
    ("二、可拍脚本", re.compile(r"^\s*(?:#{1,6}\s*)?二[、.．]\s*可拍脚本.*$", re.M)),
    ("三、发布包装", re.compile(r"^\s*(?:#{1,6}\s*)?三[、.．]\s*发布包装.*$", re.M)),
]

STOP_WORDS = {
    "一个", "这个", "那个", "什么", "怎么", "为什么", "不是", "就是", "如果", "因为", "所以", "可以",
    "视频", "原视频", "内容", "脚本", "标题", "建议", "关注", "评论", "今天", "很多", "时候", "新手",
    "我们", "你们", "他们", "自己", "不要", "没有", "已经", "进行", "出来", "看到", "知道",
    "br", "风格", "老师风格", "毛驴老师风格", "最新说法", "发布包装", "可拍脚本", "拆解报告",
}


def parse_args():
    parser = argparse.ArgumentParser(description="Render final WorkBuddy breakdown/script output to HTML.")
    parser.add_argument("--material", required=True, help="Path to *.material.json from prepare_video_for_workbuddy.py")
    parser.add_argument("--result-file", required=True, help="Markdown/text file containing WorkBuddy final output")
    parser.add_argument("--output", default="", help="Output HTML path")
    return parser.parse_args()


def esc(value):
    return html.escape("" if value is None else str(value), quote=True)


def compact_number(value):
    try:
        number = int(value or 0)
    except (TypeError, ValueError):
        return value or 0
    if number >= 10000:
        return f"{number / 10000:.1f}w".replace(".0w", "w")
    return str(number)


def split_sections(text):
    matches = []
    for title, pattern in SECTION_PATTERNS:
        match = pattern.search(text)
        if match:
            matches.append((match.start(), match.end(), title))
    matches.sort()
    if not matches:
        return [("最终输出", text.strip())]

    sections = []
    for index, (_, end, title) in enumerate(matches):
        next_start = matches[index + 1][0] if index + 1 < len(matches) else len(text)
        sections.append((title, text[end:next_start].strip()))
    return sections


def extract_keywords_from_final(final_text):
    patterns = [
        r"内容关键词\s*[：:]\s*(.+)",
        r"关键词\s*[：:]\s*(.+)",
        r"核心关键词\s*[：:]\s*(.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, final_text)
        if not match:
            continue
        raw = match.group(1).strip()
        raw = re.split(r"\n|<br>|。", raw)[0]
        parts = re.split(r"[、,，/#\s]+", raw)
        keywords = [clean_keyword(part) for part in parts]
        keywords = [keyword for keyword in keywords if keyword]
        if keywords:
            return unique_keep_order(keywords)[:8]
    return []


def clean_keyword(value):
    value = re.sub(r"<br\s*/?>", "", str(value or ""), flags=re.I)
    value = re.sub(r"[*`#【】\[\]（）()《》\"'“”]", "", value).strip()
    value = value.strip("-_：:，,。、 ")
    if not value or value in STOP_WORDS:
        return ""
    if re.fullmatch(r"\d+\s*(?:s|秒)?", value, re.I):
        return ""
    if any(word in value for word in ["风格", "报告", "脚本", "标题", "封面文字建议", "标题建议"]):
        return ""
    if any(word in value for word in ["留下", "最新说法", "本轮分析", "改写核心"]):
        return ""
    if len(value) < 2 or len(value) > 12:
        return ""
    return value


def unique_keep_order(items):
    seen = set()
    output = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            output.append(item)
    return output


def extract_keywords_from_material(work, transcript, final_text):
    candidates = []
    for topic in work.get("topics") or []:
        keyword = clean_keyword(topic)
        if keyword:
            candidates.append(keyword)

    source_text = "\n".join(
        [
            str(work.get("item_title") or work.get("title") or ""),
            str(work.get("desc") or ""),
            str(work.get("script_summary") or ""),
            str(transcript.get("text") or "")[:3000],
            final_text[:2000],
        ]
    )
    term_patterns = [
        r"[A-Za-z]+通缩论",
        r"核心CPI",
        r"CPI",
        r"AI",
        r"加息概率",
        r"通胀",
        r"能源",
        r"美联储",
        r"期货市场",
        r"关税战",
        r"川普",
        r"川子",
        r"沃什",
    ]
    for pattern in term_patterns:
        candidates.extend(clean_keyword(item) for item in re.findall(pattern, source_text, re.I))
    candidates.extend(clean_keyword(item) for item in re.findall(r"#([\u4e00-\u9fffA-Za-z0-9]{2,12})", source_text))
    candidates.extend(clean_keyword(item) for item in re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,12}", source_text))

    scored = {}
    order = {}
    for index, keyword in enumerate(candidates):
        if not keyword:
            continue
        if keyword not in order:
            order[keyword] = index
        score = 1
        if keyword in str(work.get("item_title") or ""):
            score += 5
        if keyword in str(work.get("desc") or ""):
            score += 3
        if keyword in final_text[:2000]:
            score += 2
        scored[keyword] = scored.get(keyword, 0) + score
    ranked = sorted(scored, key=lambda item: (-scored[item], order[item]))
    return ranked[:8]


def get_keywords(work, transcript, final_text):
    return extract_keywords_from_final(final_text) or extract_keywords_from_material(work, transcript, final_text)


def inline_markdown(text):
    text = esc(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`([^`]+)`", r"<b>\1</b>", text)
    return text


def normalize_line(line):
    stripped = line.strip()
    stripped = re.sub(r"^#{1,6}\s*", "", stripped)
    stripped = re.sub(r"^>\s*", "", stripped)
    stripped = re.sub(r"^[-*]\s+", "", stripped)
    stripped = re.sub(r"^\d+[.、]\s*", "", stripped)
    stripped = stripped.strip()
    return stripped


def is_separator(line):
    stripped = line.strip()
    return not stripped or stripped in {"---", "***", "```"} or re.fullmatch(r"[-|:\s]+", stripped or "")


def render_table(lines, start):
    rows = []
    index = start
    while index < len(lines):
        raw = normalize_line(lines[index])
        if not raw.startswith("|") or not raw.endswith("|"):
            break
        cells = [cell.strip() for cell in raw.strip("|").split("|")]
        if cells and not all(re.fullmatch(r"[-:\s]+", cell) for cell in cells):
            rows.append(cells)
        index += 1
    if not rows:
        return "", index
    html_rows = []
    for row_index, cells in enumerate(rows):
        tag = "th" if row_index == 0 else "td"
        html_rows.append("<tr>" + "".join(f"<{tag}>{inline_markdown(cell)}</{tag}>" for cell in cells) + "</tr>")
    return '<table class="md-table">' + "".join(html_rows) + "</table>", index


def render_lines(text):
    lines = [line.rstrip() for line in text.splitlines()]
    blocks = []
    index = 0
    in_code = False
    while index < len(lines):
        line = lines[index]
        if line.strip().startswith("```"):
            in_code = not in_code
            index += 1
            continue
        if in_code:
            stripped = normalize_line(line)
            if stripped:
                blocks.append(f'<p class="plain">{inline_markdown(stripped)}</p>')
            index += 1
            continue

        if is_separator(line):
            index += 1
            continue

        stripped = normalize_line(line)
        if not stripped:
            index += 1
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            table_html, next_index = render_table(lines, index)
            if table_html:
                blocks.append(table_html)
                index = next_index
                continue

        if re.match(r"^[一二三四五六七八九十][、.．]", stripped):
            index += 1
            continue

        bracket = re.match(r"^(?:【|\[)(.+?)(?:】|\])\s*(.*)$", stripped)
        if bracket:
            blocks.append(
                f'<div class="beat"><span class="time">{inline_markdown(bracket.group(1))}</span>'
                f'<p>{inline_markdown(bracket.group(2))}</p></div>'
            )
        elif "：" in stripped or ":" in stripped:
            key, value = re.split(r"：|:", stripped, maxsplit=1)
            blocks.append(
                f'<div class="note"><div class="k">{inline_markdown(key)}</div>'
                f'<div class="t">{inline_markdown(value.strip())}</div></div>'
            )
        else:
            blocks.append(f'<p class="plain">{inline_markdown(stripped)}</p>')
        index += 1
    return "\n".join(blocks) or '<p class="plain muted">暂无内容</p>'


def clean_text_line(line):
    line = normalize_line(line)
    line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
    line = re.sub(r"`([^`]+)`", r"\1", line)
    line = re.sub(r"^\|?[-:\s|]+\|?$", "", line)
    return line.strip()


def split_key_values(text):
    items = []
    for line in text.splitlines():
        stripped = clean_text_line(line)
        if not stripped or stripped in {"---", "***"}:
            continue
        if "：" in stripped or ":" in stripped:
            key, value = re.split(r"：|:", stripped, maxsplit=1)
            key = clean_text_line(key)
            value = clean_text_line(value)
            if key and value:
                items.append((key, value))
    return items


def subsection_text(text, names):
    pattern = re.compile(r"^\s*(?:#{1,6}\s*)?(?:" + "|".join(re.escape(name) for name in names) + r").*$", re.M)
    match = pattern.search(text)
    if not match:
        return ""
    next_match = re.search(r"^\s*(?:#{1,6}\s*)?(?:核心爆点|核心卖点|可复用结构|复用结构|借鉴提醒|改写提醒|提醒).*$", text[match.end() :], re.M)
    end = match.end() + next_match.start() if next_match else len(text)
    return text[match.end() : end].strip()


def first_meaningful_line(text):
    for line in text.splitlines():
        line = clean_text_line(line)
        if not line or line in {"---", "***"}:
            continue
        if line.startswith("```") or line in {"↓", "->", "→"}:
            continue
        line = re.sub(r"^(一句话|提醒|结构)\s*[：:]\s*", "", line)
        return line
    return ""


def render_breakdown(body):
    aliases = {
        "核心爆点": ["核心爆点", "核心卖点"],
        "可复用结构": ["可复用结构", "复用结构", "结构"],
        "借鉴提醒": ["借鉴提醒", "改写提醒", "提醒"],
    }
    found = {}
    for key, value in split_key_values(body):
        for canonical, names in aliases.items():
            if canonical not in found and any(name in key for name in names):
                found[canonical] = value
    for canonical, names in aliases.items():
        if canonical not in found:
            sub = subsection_text(body, names)
            if canonical == "可复用结构" and sub:
                steps = [clean_text_line(line) for line in sub.splitlines()]
                steps = [line for line in steps if line and line not in {"```", "↓"} and not re.fullmatch(r"[→↓\\s]+", line)]
                found[canonical] = " → ".join(steps[:5])
            else:
                found[canonical] = first_meaningful_line(sub)
    if len(found) < 2:
        return render_lines(body)
    core = found.get("核心爆点", "")
    structure = found.get("可复用结构", "")
    reminder = found.get("借鉴提醒", "")
    steps = [step.strip(" 「」") for step in re.split(r"\s*(?:→|->|⇒|↓)\s*", structure) if step.strip()]
    step_html = "".join(f'<span class="flow-chip">{inline_markdown(step)}</span>' for step in steps[:7])
    return f"""
      <div class="boom-core">
        <span class="eyebrow">核心爆点</span>
        <div class="boom-text">{inline_markdown(core)}</div>
      </div>
      <div class="flow-box">
        <span class="eyebrow">可复用结构</span>
        <div class="flow">{step_html or inline_markdown(structure)}</div>
      </div>
      <div class="tip-box">
        <span class="eyebrow">借鉴提醒</span>
        <div>{inline_markdown(reminder)}</div>
      </div>
    """


def expand_inline_signals(lines):
    """Split lines like '记住三个信号：第一，... 第二，... 第三，...' into separate signal items."""
    out = []
    for item in lines:
        parts = re.split(r"第([一二三四五六七八九十])[，、,．.]\s*", item)
        if len(parts) >= 5:
            lead = parts[0].strip(" ：:")
            if lead:
                out.append(lead)
            for num, text in zip(parts[1::2], parts[2::2]):
                text = text.strip()
                if text:
                    out.append(f"{num}、{text}")
        else:
            out.append(item)
    return out


def render_script_timeline(body):
    lines = [line for line in body.splitlines()]
    beats = []
    current = None
    for line in lines:
        stripped = clean_text_line(line)
        if not stripped:
            continue
        match = re.match(r"^(?:【|\[)?\s*([0-9０-９]+)\s*[-~—到至]\s*([0-9０-９]+)\s*秒?\s*(?:】|\])?\s*(.*)$", stripped)
        if match:
            if current:
                beats.append(current)
            scene = clean_text_line(match.group(3)).strip("】]｜| ")
            current = {"time": f"{match.group(1)}–{match.group(2)}s", "title": scene or "口播段落", "lines": []}
            continue
        if current:
            current["lines"].append(stripped)
    if current:
        beats.append(current)

    if not beats:
        return render_lines(body)

    html_beats = []
    for beat in beats:
        title = esc(beat["title"].strip("｜| "))
        content_lines = []
        signals = []
        for item in expand_inline_signals(beat["lines"]):
            signal = re.match(r"^([123ABC一二三])\s*[、.．]?\s*(.+)$", item)
            if signal and len(item) < 80:
                signals.append((signal.group(1), signal.group(2)))
            else:
                content_lines.append(item)
        content = "".join(f'<p>{inline_markdown(line)}</p>' for line in content_lines)
        signal_html = ""
        if signals:
            numerals = {"一": "1", "二": "2", "三": "3", "四": "4", "五": "5"}
            signal_html = '<div class="sig">' + "".join(
                f'<div class="sigrow"><div class="n">{esc(numerals.get(num, num))}</div><div class="x">{inline_markdown(text)}</div></div>'
                for num, text in signals
            ) + "</div>"
        html_beats.append(
            f'<div class="beat"><span class="time">{esc(beat["time"])}</span>'
            f'<div class="scene">{title}</div>{content}{signal_html}</div>'
        )
    return "".join(html_beats)


def render_package(body):
    def section_after(title_pattern):
        match = re.search(title_pattern, body, re.M)
        if not match:
            return ""
        next_match = re.search(r"^\s*#{1,6}\s+", body[match.end() :], re.M)
        end = match.end() + next_match.start() if next_match else len(body)
        return body[match.end() : end].strip()

    def table_items(section, value_col=1):
        rows = []
        for line in section.splitlines():
            stripped = clean_text_line(line)
            if not stripped.startswith("|") or not stripped.endswith("|"):
                continue
            cells = [clean_text_line(cell) for cell in stripped.strip("|").split("|")]
            if not cells or all(re.fullmatch(r"[-:\s]+", cell) for cell in cells):
                continue
            if cells[0] in {"#", "序号"} or cells[value_col] in {"标题", "封面字", "封面文字"}:
                continue
            if len(cells) > value_col:
                value = cells[value_col].replace("<br>", " / ")
                rows.append(f"{cells[0]}  {value}")
        return rows

    title_section = section_after(r"^\s*#{1,6}\s*标题")
    cover_section = section_after(r"^\s*#{1,6}\s*封面")
    pin_section = section_after(r"^\s*#{1,6}\s*(?:评论区置顶引导|置顶评论|评论引导)")
    title_items = table_items(title_section, 1)
    cover_items = table_items(cover_section, 1)
    pin = first_meaningful_line(pin_section)

    if title_items or cover_items or pin:
        output = []
        if title_items:
            output.append('<div class="pack"><h3>标题 · 3 选</h3>')
            for item in title_items[:3]:
                marker, text = item.split("  ", 1)
                output.append(f'<div class="pick"><span class="m">{esc(marker)}</span><span>{inline_markdown(text)}</span></div>')
            output.append("</div>")
        if cover_items:
            output.append('<div class="pack"><h3>封面字 · 3 选</h3>')
            for item in cover_items[:3]:
                marker, text = item.split("  ", 1)
                output.append(f'<div class="pick"><span class="m">{esc(marker)}</span><span>{inline_markdown(text)}</span></div>')
            output.append("</div>")
        if pin:
            output.append(f'<div class="pin"><span class="label">评论区置顶引导</span><br>{inline_markdown(pin)}</div>')
        return "".join(output)

    lines = [clean_text_line(line) for line in body.splitlines()]
    lines = [line for line in lines if line and line not in {"---", "***"}]
    groups = []
    table_rows = []
    for line in body.splitlines():
        stripped = clean_text_line(line)
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [clean_text_line(cell) for cell in stripped.strip("|").split("|")]
            if cells and not all(re.fullmatch(r"[-:\s]+", cell) for cell in cells):
                table_rows.append(cells)
    title_items = []
    cover_items = []
    for row in table_rows:
        if not row or row[0] in {"#", "序号"}:
            continue
        if len(row) >= 3 and ("标题" in row[1] or len(row[1]) > 6):
            text = row[1]
            if "封面" in row[1] or "<br>" in row[1]:
                cover_items.append(f"{row[0]}  {text.replace('<br>', ' / ')}")
            elif "标题" not in row[0]:
                title_items.append(f"{row[0]}  {text}")
    if title_items:
        groups.append(("标题 · 3 选", title_items[:3]))
    if cover_items:
        groups.append(("封面字 · 3 选", cover_items[:3]))

    current_title = "发布建议"
    current_items = []
    pin = ""
    for line in lines:
        if line.startswith("|") and line.endswith("|"):
            continue
        heading = re.match(r"^(标题|封面字|评论区置顶|置顶评论|评论引导).*?(?:选|条)?\s*$", line)
        kv = re.match(r"^(标题|封面字|评论区置顶|置顶评论|评论引导)\s*[：:]\s*(.+)$", line)
        item = re.match(r"^([ABC123])\s*[、.．]?\s*(.+)$", line)
        if kv:
            if "评论" in kv.group(1):
                pin = kv.group(2)
            else:
                current_items.append(kv.group(2))
            continue
        if heading:
            if current_items:
                groups.append((current_title, current_items))
            current_title = heading.group(1)
            current_items = []
            continue
        if item:
            current_items.append(f"{item.group(1)}  {item.group(2)}")
        elif "评论" in current_title or "置顶" in current_title:
            pin = line
        else:
            current_items.append(line)
    if current_items:
        groups.append((current_title, current_items))

    output = []
    letters = "ABCDEF"
    for title, items in groups:
        items = items[:6]
        display_title = title if "·" in title else f"{title} · {len(items)} 选"
        output.append(f'<div class="pack"><h3>{esc(display_title)}</h3>')
        for position, item in enumerate(items):
            text = item
            match = re.match(r"^([ABC123])\s+(.+)$", item)
            if match:
                marker = match.group(1)
                text = match.group(2)
            else:
                marker = letters[position] if position < len(letters) else "·"
            output.append(f'<div class="pick"><span class="m">{esc(marker)}</span><span>{inline_markdown(text)}</span></div>')
        output.append("</div>")
    if pin:
        output.append(f'<div class="pin"><span class="label">评论区置顶引导</span><br>{inline_markdown(pin)}</div>')
    return "".join(output) or render_lines(body)


def render_section(index, title, body):
    title = re.sub(r"^[一二三四五六七八九十]+[、.．]\s*", "", title).strip()
    if index == 1:
        body_html = render_breakdown(body)
    elif index == 2:
        body_html = render_script_timeline(body)
    elif index == 3:
        body_html = render_package(body)
    else:
        body_html = render_lines(body)
    return f"""
      <section class="card" id="section-{index}">
        <div class="card-head">
          <div class="idx">{index:02d}</div>
          <h2>{esc(title)}</h2>
          <div class="spacer"></div>
          {'<button class="copy-btn" data-copy="section-2">复制脚本</button>' if index == 2 else ''}
        </div>
        <div class="card-body">{body_html}</div>
      </section>
    """


def render_stat(label, value):
    return f"""
      <div class="stat">
        <div class="v">{esc(compact_number(value))}</div>
        <div class="l">{esc(label)}</div>
      </div>
    """


def render_top_comments(comments):
    if not comments:
        return ""
    rows = []
    for index, comment in enumerate(comments[:5], 1):
        text = comment.get("text", "")
        nickname = comment.get("nickname", "") or "匿名用户"
        digg = compact_number(comment.get("digg_count", 0))
        rows.append(
            f'<div class="comment-row"><div class="comment-rank">{index}</div>'
            f'<div><div class="comment-meta">{esc(nickname)} · {esc(digg)}赞</div>'
            f'<div class="comment-text">{esc(text)}</div></div></div>'
        )
    return f"""
      <section class="card">
        <div class="card-head"><div class="idx">C</div><h2>高赞评论 TOP 5</h2></div>
        <div class="card-body comments-box">{''.join(rows)}</div>
      </section>
    """


def render_html(material, final_text, output_path):
    work = material.get("work_info", {})
    transcript = material.get("transcript", {})
    top_comments = material.get("top_comments") or []
    title = work.get("item_title") or work.get("title") or "短视频拆解报告"
    cover = work.get("video_cover") or ""
    work_url = work.get("work_url") or ""
    topics = unique_keep_order([clean_keyword(topic) for topic in (work.get("topics") or [])])
    keywords = unique_keep_order(topics + get_keywords(work, transcript, final_text))[:8]
    sections = split_sections(final_text)
    rendered_sections = [render_section(i + 1, title, body) for i, (title, body) in enumerate(sections)]
    left_sections = "\n".join(rendered_sections[:2])
    right_sections = "\n".join(rendered_sections[2:])
    stats = [
        ("点赞", work.get("digg_count", 0)),
        ("评论", work.get("comment_count", 0)),
        ("收藏", work.get("collect_count", 0)),
        ("分享", work.get("share_count", 0)),
    ]

    html_text = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · WorkBuddy 拆解报告</title>
<style>
:root{{
  --bg:#0e1116; --panel:#161b22; --panel-2:#1c232d; --line:#28323f;
  --ink:#e6edf3; --muted:#8b97a6; --gold:#e0a826; --accent:#4cc4b0; --soft:#12211f;
}}
*{{box-sizing:border-box;}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:"Microsoft YaHei","PingFang SC",-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;line-height:1.7;}}
.mono{{font-family:ui-monospace,"SF Mono","Roboto Mono",Menlo,Consolas,monospace;}}
.page{{max-width:1140px;margin:0 auto;padding:32px 24px 64px;}}
.ribbon{{display:flex;align-items:center;gap:12px;flex-wrap:wrap;font-size:12px;letter-spacing:.16em;color:var(--muted);text-transform:uppercase;margin-bottom:18px;}}
.dot{{width:7px;height:7px;border-radius:50%;background:var(--accent);box-shadow:0 0 0 4px rgba(76,196,176,.12);}}
.pipe{{color:var(--line);}}
.hero{{border:1px solid var(--line);border-radius:14px;overflow:hidden;background:linear-gradient(180deg,var(--panel-2),var(--panel));margin-bottom:26px;}}
.hero-grid{{display:grid;grid-template-columns:300px 1fr;}}
.cover{{position:relative;min-height:340px;background:#0a0d12 center/cover no-repeat;border-right:1px solid var(--line);}}
.cover::after{{content:"";position:absolute;inset:0;background:linear-gradient(105deg,transparent 60%,rgba(22,27,34,.85));}}
.badge{{position:absolute;left:14px;top:14px;z-index:2;font-size:11px;letter-spacing:.12em;padding:5px 10px;border-radius:6px;background:rgba(14,17,22,.78);border:1px solid var(--line);color:var(--accent);backdrop-filter:blur(4px);}}
.hero-body{{padding:30px 32px;}}
h1{{margin:0 0 16px;font-size:30px;line-height:1.28;font-weight:800;letter-spacing:0;}}
.byline{{display:flex;gap:16px;flex-wrap:wrap;align-items:center;font-size:13px;color:var(--muted);margin-bottom:18px;}}
.byline strong{{color:var(--ink);font-weight:600;}}
a{{color:var(--accent);text-decoration:none;border-bottom:1px solid transparent;}}
a:hover{{border-bottom-color:var(--accent);}}
.desc{{margin:0 0 18px;color:#c9d3de;font-size:15px;}}
.tags{{display:flex;flex-wrap:wrap;gap:8px;}}
.tag{{font-size:12.5px;padding:4px 11px;border-radius:999px;color:var(--accent);background:var(--soft);border:1px solid #1e3b36;}}
.stats{{display:grid;grid-template-columns:repeat(4,1fr);border-top:1px solid var(--line);}}
.stat{{padding:18px 20px;border-right:1px solid var(--line);display:flex;flex-direction:column;gap:2px;}}
.stat:last-child{{border-right:none;}}
.stat .v{{font-size:26px;font-weight:800;color:var(--gold);line-height:1;}}
.stat .l{{font-size:12px;color:var(--muted);letter-spacing:.08em;}}
.main{{display:grid;grid-template-columns:1.18fr .82fr;gap:22px;margin-top:26px;}}
.col-r{{display:flex;flex-direction:column;gap:22px;}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:14px;overflow:hidden;margin-bottom:22px;}}
.card-head{{display:flex;align-items:center;gap:12px;padding:16px 22px;border-bottom:1px solid var(--line);background:linear-gradient(180deg,var(--panel-2),transparent);}}
.idx{{font-family:ui-monospace,monospace;font-size:13px;font-weight:800;width:36px;height:36px;flex:none;border-radius:10px;display:grid;place-items:center;color:var(--bg);background:var(--accent);}}
.card-head h2{{margin:0;font-size:21px;font-weight:800;letter-spacing:0;}}
.spacer{{flex:1;}}
.copy-btn{{cursor:pointer;font-family:inherit;font-size:12.5px;font-weight:600;color:var(--accent);background:var(--soft);border:1px solid #1e3b36;border-radius:8px;padding:6px 12px;}}
.copy-btn.done{{color:var(--gold);border-color:#4a3a14;background:#231c0d;}}
.card-body{{padding:28px 26px;font-size:16px;color:#cdd7e2;}}
.insight-row{{display:grid;grid-template-columns:90px 1fr;gap:20px;padding:16px 0;border-bottom:1px dashed var(--line);}}
.insight-row:last-child{{border-bottom:none;}}
.insight-k{{font-size:13px;font-weight:800;color:var(--accent);letter-spacing:.02em;}}
.insight-v{{color:#e6edf3;font-size:16px;line-height:1.9;}}
.insight-v b{{color:#fff;}}
.eyebrow{{display:inline-block;font-size:12px;font-weight:800;letter-spacing:.08em;color:var(--accent);margin-bottom:8px;}}
.boom-core{{padding:18px 20px;border:1px solid #25433e;border-radius:12px;background:linear-gradient(180deg,rgba(76,196,176,.12),rgba(18,33,31,.55));margin-bottom:16px;}}
.boom-text{{font-size:19px;line-height:1.85;color:#fff;font-weight:700;}}
.flow-box{{padding:16px 0 18px;border-bottom:1px dashed var(--line);margin-bottom:16px;}}
.flow{{display:flex;flex-wrap:wrap;gap:10px;align-items:center;}}
.flow-chip{{position:relative;display:inline-flex;align-items:center;min-height:34px;padding:6px 12px;border-radius:9px;border:1px solid var(--line);background:var(--panel-2);color:#e6edf3;font-size:14px;font-weight:700;}}
.flow-chip:not(:last-child)::after{{content:"→";position:absolute;right:-17px;color:var(--gold);font-weight:800;}}
.tip-box{{padding:15px 18px;border-radius:12px;background:#211b0e;border:1px solid #4a3a14;color:#f3d998;font-size:15.5px;line-height:1.85;}}
.tip-box b{{color:#fff;}}
.note{{display:flex;gap:12px;padding:12px 0;border-bottom:1px dashed var(--line);}}
.note:last-child{{border-bottom:none;}}
.note .k{{flex:none;font-size:12px;font-weight:700;color:var(--accent);letter-spacing:.05em;width:86px;padding-top:2px;}}
.note .t{{color:#d4dde7;}}
.note .t b,.plain b{{color:#fff;}}
.beat{{position:relative;padding:0 0 28px 34px;margin-left:7px;}}
.beat::before{{content:"";position:absolute;left:0;top:7px;width:9px;height:9px;border-radius:50%;background:var(--gold);box-shadow:0 0 0 3px rgba(224,168,38,.18);}}
.beat::after{{content:"";position:absolute;left:4px;top:18px;bottom:-2px;width:1px;background:var(--line);}}
.beat:last-child::after{{display:none;}}
.beat .time{{font-family:ui-monospace,monospace;font-size:12px;color:var(--gold);letter-spacing:.04em;display:block;margin-bottom:8px;}}
.beat .scene{{font-weight:800;color:#fff;font-size:17px;margin-bottom:10px;}}
.beat p{{margin:8px 0 0;color:#e1e8f0;font-size:16px;line-height:1.85;}}
.sig{{display:grid;gap:12px;margin-top:14px;}}
.sigrow{{display:grid;grid-template-columns:auto 1fr;gap:14px;align-items:start;padding:12px 16px;border:1px solid var(--line);border-radius:10px;background:var(--panel-2);}}
.sigrow .n{{font-family:ui-monospace,monospace;font-weight:800;font-size:14px;color:var(--bg);background:var(--gold);border-radius:7px;padding:3px 10px;}}
.sigrow .x{{font-size:15px;color:#dbe5ef;}}
.plain{{margin:9px 0;color:#c4ceda;}}
.pack h3{{font-size:13px;letter-spacing:.1em;color:var(--muted);margin:18px 0 10px;text-transform:uppercase;font-weight:800;}}
.pack h3:first-child{{margin-top:0;}}
.pick{{display:flex;gap:12px;padding:11px 0;border-bottom:1px solid var(--line);font-size:15px;color:#e1e8f0;}}
.pick .m{{color:var(--accent);font-family:ui-monospace,monospace;font-weight:800;flex:none;min-width:16px;}}
.pin{{margin-top:18px;padding:15px 17px;border-radius:10px;background:var(--soft);border:1px solid #1e3b36;color:#bfe6dd;font-size:15px;line-height:1.8;}}
.pin .label{{display:inline-block;font-size:12px;letter-spacing:.1em;color:var(--accent);border:1px solid #1e3b36;border-radius:6px;padding:2px 8px;margin-bottom:8px;}}
.comments-box{{display:grid;gap:12px;}}
.comment-row{{display:grid;grid-template-columns:auto 1fr;gap:12px;padding:12px 0;border-bottom:1px solid var(--line);}}
.comment-row:last-child{{border-bottom:none;}}
.comment-rank{{width:26px;height:26px;border-radius:8px;display:grid;place-items:center;background:var(--gold);color:var(--bg);font-family:ui-monospace,monospace;font-weight:800;font-size:13px;}}
.comment-meta{{font-size:12px;color:var(--muted);margin-bottom:5px;}}
.comment-text{{font-size:14px;color:#dbe5ef;line-height:1.75;}}
.muted{{color:var(--muted);}}
.md-table{{width:100%;border-collapse:collapse;margin:12px 0 16px;font-size:13.5px;color:#cdd7e2;}}
.md-table th,.md-table td{{border:1px solid var(--line);padding:9px 10px;vertical-align:top;}}
.md-table th{{color:var(--accent);background:var(--panel-2);font-weight:700;}}
.md-table td{{background:rgba(28,35,45,.45);}}
.transcript{{white-space:pre-wrap;max-height:560px;overflow:auto;font-size:13px;line-height:1.85;color:#9aa6b3;padding:4px 8px 4px 0;}}
.transcript::-webkit-scrollbar{{width:8px;}}
.transcript::-webkit-scrollbar-thumb{{background:var(--line);border-radius:8px;}}
footer{{margin-top:40px;padding-top:18px;border-top:1px solid var(--line);font-size:12px;color:var(--muted);display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;}}
@media (max-width:880px){{
  .page{{padding:20px 14px 48px;}}
  .hero-grid,.main{{grid-template-columns:1fr;}}
  .cover{{min-height:220px;border-right:none;border-bottom:1px solid var(--line);}}
  .cover::after{{background:linear-gradient(180deg,transparent 55%,rgba(22,27,34,.9));}}
  .stats{{grid-template-columns:repeat(2,1fr);}}
  .stat:nth-child(2){{border-right:none;}}
  h1{{font-size:24px;}}
}}
</style>
</head>
<body>
<main class="page">
  <div class="ribbon">
    <span class="dot"></span><span>WorkBuddy 拆解报告</span><span class="pipe">/</span>
    <span>抖音短视频</span><span class="pipe">/</span><span class="mono">{esc(work.get("work_id", ""))}</span>
  </div>
  <section class="hero">
    <div class="hero-grid">
      <div class="cover" style="background-image:url('{esc(cover)}')"><span class="badge">原视频封面</span></div>
      <div class="hero-body">
        <h1>{esc(title)}</h1>
        <div class="byline">
          <span>作者 <strong>{esc(work.get("nickname", ""))}</strong></span>
          <span class="mono">{esc(work.get("create_time_text", ""))}</span>
          <a href="{esc(work_url)}" target="_blank" rel="noopener">打开原视频</a>
        </div>
        <p class="desc">{esc(work.get("desc", ""))}</p>
        <div class="tags">{''.join(f'<span class="tag">#{esc(keyword)}</span>' for keyword in keywords)}</div>
      </div>
    </div>
    <div class="stats">{''.join(render_stat(label, value) for label, value in stats)}</div>
  </section>
  <div class="main">
    <div>{left_sections}</div>
    <aside class="col-r">
      {right_sections}
      {render_top_comments(top_comments)}
      <section class="card">
        <div class="card-head"><div class="idx">T</div><h2>原视频逐字稿</h2></div>
        <div class="card-body"><div class="transcript">{esc(transcript.get("text", "")) or "暂无逐字稿"}</div></div>
      </section>
    </aside>
  </div>
  <footer><span>由 WorkBuddy 生成</span><span class="mono">{esc(os.path.basename(output_path))}</span></footer>
</main>
<script>
document.querySelectorAll('.copy-btn').forEach(function(btn) {{
  btn.addEventListener('click', async function() {{
    var target = document.getElementById(btn.dataset.copy);
    if (!target) return;
    await navigator.clipboard.writeText(target.innerText.trim());
    btn.classList.add('done');
    btn.textContent = '已复制';
    setTimeout(function() {{ btn.classList.remove('done'); btn.textContent = '复制'; }}, 1400);
  }});
}});
</script>
</body>
</html>
"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_text)
    return output_path


def main():
    args = parse_args()
    with open(args.material, "r", encoding="utf-8") as f:
        material = json.load(f)
    with open(args.result_file, "r", encoding="utf-8") as f:
        final_text = f.read()
    output = args.output or os.path.splitext(args.material)[0] + ".final_report.html"
    output = os.path.abspath(output)
    render_html(material, final_text, output)
    print(f"Final HTML report: {output}")
    print(f"html_artifact: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
