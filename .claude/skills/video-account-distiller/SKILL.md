---
name: video-account-distiller
description: 采集和分析站外公开账号及内容，批量研究历史作品，提炼账号定位、内容方法、表达习惯与 IP 风格，并保存为可复用的创作档案；同时支持抖音和微信视频号单条视频的下载、转写、爆点拆解、脚本复刻与 HTML 报告。适用于站外账号研究、IP 风格蒸馏、内容复刻和短视频创作。
---

# 站外账号与内容蒸馏

本技能包含三项相互独立的能力：

1. **生成内容报告**：分析一条抖音、微信视频号或小红书视频/笔记，输出完整 HTML 报告。
2. **分析站外账号**：批量采集抖音或小红书账号作品，分析选题、表现和内容风格。
3. **创建 IP 风格**：根据站外账号或用户上传的语料，保存可复用的创作风格。

除非用户明确要求，不要把创建风格和单条视频分析混为一个任务。不要让用户手动复制 Cookie；抖音授权缺失时，由脚本自动打开浏览器完成登录和授权。

## 用户入口

向用户展示以下三个入口：

- **生成内容报告**：提供抖音、微信视频号或小红书内容链接，可附加创作要求或指定已有风格。
- **账号分析**：提供抖音或小红书账号主页，分析历史作品、爆款规律和账号定位。
- **创建 IP 风格**：提供站外账号主页，或上传 `.docx`、`.txt` 语料，沉淀长期可复用的表达风格。

首次使用且未指定风格时，自动使用默认风格“小白投教”，不要停下来追问。

## 环境安装

在技能目录执行：

```powershell
cd scripts
python install_minimal.py
```

技能已包含抖音签名所需的最小 Node 依赖，不要运行 `npm install`。

## 流程一：生成单条视频 HTML 报告

当用户提供抖音或微信视频号的视频链接，并要求分析、拆解、改写或生成报告时，执行本流程。脚本会自动识别平台；微信视频号不需要 `DY_COOKIES`。

如用户指定已有风格，先查看风格列表：

```powershell
python scripts\llmagent_video\list_ip_profiles.py
```

每份报告只能使用一个风格档案：

- 用户未指定时，使用默认风格“小白投教”。
- 用户指定风格时，只传入该风格，不要同时叠加默认风格。
- 用户的临时要求属于“本次要求”，不要把它解释成第二种风格。

准备视频材料：

```powershell
python scripts\llmagent_video\prepare_video_for_workbuddy.py "VIDEO_URL" --requirement "USER_REQUIREMENT"
```

指定风格：

```powershell
python scripts\llmagent_video\prepare_video_for_workbuddy.py "VIDEO_URL" --requirement "USER_REQUIREMENT" --profile "PROFILE_NAME"
```

脚本会采集视频信息、下载视频、完成语音转写，并在输出目录生成素材 JSON 和 `*.workbuddy_prompt.md`。读取提示文件后，使用 WorkBuddy 模型生成最终内容。

最终内容必须包含：

```text
内容关键词：关键词1、关键词2、关键词3、关键词4

一、这个视频为什么能爆
核心爆点：...
可复用结构：...
借鉴提醒：...

二、可拍脚本
【0-3秒 开头钩子】...
【3-10秒 痛点放大】...
【10-40秒 方法/案例】...
【40-55秒 总结升华】...
【55-60秒 关注/私信/评论引导】...

三、发布包装
标题：...
标题：...
标题：...
封面字：...
封面字：...
封面字：...
评论区置顶引导：...
```

生成要求：

- 关键词必须来自原视频的实体、概念和主题，不要使用“行动号召”等结构标签。
- 可拍脚本必须是能直接朗读拍摄的完整文稿，不要只写提纲。
- 默认 60 秒脚本建议为 450 至 650 个汉字，并尽量保留原视频的核心信息量。
- 不使用 Markdown 表格、引用块或代码块，不额外增加章节。
- 对转写中的人名、地名、公司名和数据进行上下文校正，无法确认时使用审慎表达，不编造事实。

渲染 HTML：

```powershell
python scripts\llmagent_video\finalize_video_report.py --material "MATERIAL_JSON" --result-file "FINAL_OUTPUT.md" --output "WORK_ID_final_report.html"
```

只向用户交付一个最终文件：`WORK_ID_final_report.html`。不要同时展示素材 JSON、中间 Markdown、任务文件或多个 HTML 版本。

完成后简洁回复：

```text
已生成报告：WORK_ID_final_report.html
本次使用风格：PROFILE_NAME
本次要求：USER_REQUIREMENT
```

## 流程二：分析站外账号

当用户提供抖音或小红书账号主页，并要求分析账号、作品表现、内容方向或爆款规律时执行。小红书使用内置 `xhs-apis` 采集公开主页、笔记列表、笔记详情和互动数据。

小红书必须直接调用技能内置入口，不要在任务目录临时编写 `extract_xhs.py` 或其他采集脚本：

```powershell
python -X utf8 scripts\llmagent_video\fetch_xhs.py "XHS_URL" --max-items 50 --output "xhs_account.json"
```

命令必须从技能根目录执行。入口会根据自身文件位置定位 `xhs-apis`，不要硬编码 `C:\Users\...` 路径。脚本自动将终端和 JSON 统一为 UTF-8。

如需登录后分页获取更多历史内容，在环境变量中配置 `XHS_COOKIES`，不要把 Cookie 写进命令、报告或回复：

```powershell
$env:XHS_COOKIES="..."
python -X utf8 scripts\llmagent_video\fetch_xhs.py "XHS_URL" --max-items 50 --output "xhs_account.json"
```

```powershell
python scripts\llmagent_video\track_account.py "USER_URL" --max-works 50
```

根据生成的账号快照，提炼以下内容：

- 账号基础数据与近期作品数量。
- 高赞、高评论、高收藏作品及共同特征。
- 核心内容方向、目标受众和账号定位。
- 常用标题、开头钩子、表达习惯和脚本结构。
- 可借鉴的选题方向与内容方法。
- 是否适合进一步沉淀为 IP 风格。

不要只罗列原始数据。要给出清晰、可执行的总结。

WorkBuddy 默认不导出 Excel。只有用户明确提出“导出 Excel”“生成表格”或“给领导展示数据表”时，才执行：

```powershell
python scripts\llmagent_video\export_account_excel.py "SNAPSHOT_JSON"
```

账号采集限制：

- 默认模式：50 篇，适合常规账号画像和风格蒸馏。
- 快速模式：20 篇，适合快速判断账号定位。
- 深度模式：100 篇，适合选题规律和长期风格研究。
- 硬上限：200 篇。即使用户输入更大数字，也只处理 200 篇。

抖音和小红书支持账号级批量分析。微信视频号目前支持单条视频分析，尚未打通账号历史作品的批量采集。

## 流程三：创建和管理 IP 风格

当用户希望保存某个人、某账号或某套语料的风格，用于后续持续创作时执行。

先列出现有风格：

```powershell
python scripts\llmagent_video\list_ip_profiles.py
```

从抖音或小红书账号创建：

```powershell
python scripts\llmagent_video\create_ip_profile.py --name "PROFILE_NAME" --account-url "USER_URL"
```

从文档语料创建：

```powershell
python scripts\llmagent_video\create_ip_profile.py --name "PROFILE_NAME" --docx-file "CORPUS.docx"
```

同时使用账号和文档：

```powershell
python scripts\llmagent_video\create_ip_profile.py --name "PROFILE_NAME" --account-url "USER_URL" --docx-file "CORPUS.docx"
```

风格档案保存在：

```text
scripts/llmagent_video/profiles
```

创建后向用户说明：

- 风格名称。
- 内容定位。
- 典型语气和说话习惯。
- 常用开头、内容结构与收尾方式。
- 后续生成报告时可以直接指定该风格。

## 安全与异常处理

- 不要在回答或交付文件中暴露 `.env`、Cookie、Token 或 API 密钥。
- 默认语音识别模型为 `tiny`，优先保证速度；用户要求更高精度时使用 `--model small`。
- 抖音出现 `verify_check` 时，提示用户在自动打开的浏览器中完成验证，再继续任务。
- 抓取和分析仅针对用户提供的公开内容，不绕过登录权限或平台访问控制。
