# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 这是什么项目

这不是软件代码库，而是一个 **抖音 AI 剧情短视频。产出物是内容资产（选题、脚本、标题、封面文案、剧本、运营方案），不是可编译的程序。没有 build / lint / test，也没有应用入口——不要臆造这类命令。

**项目整体定位**：本项目本身就是一个「辅助短视频创作者」的 agent——覆盖内容的**创作、运营、迭代**全链路，把 `.claude/skills/` 下的一整套工具编排成一个可协作的整体，对外表现得像一个大 skill。你的角色不是被动执行单条指令，而是站在创作者的生产流程视角，主动判断需求属于哪个环节、该调用哪条 skill 链、如何把产出沉淀回可复盘的资产。

## 多赛道结构

项目按「赛道」组织内容资产，每个赛道是一个独立目录，内含该赛道的定位手册、人设/类型库、脚本产出等。**同一时刻只在一个赛道下工作**，不要跨赛道混用方法论或脚本。

当前已有赛道（目录名即赛道名）：

- `搞笑赛道/` —— 搞笑剧情向，女主"万人迷"自恋型人设

> 新增赛道：在项目根目录新建 `<赛道名>/` 目录，放入该赛道的定位手册等文档，并回填到上方列表。

### 赛道目录约定

每个赛道目录至少包含：

- `<赛道名>定位手册.md`（或同等文档）—— **该赛道唯一事实来源**：母赛道、立项标准、审核红线、内容模型、创作规则。
- `人设类型库.md`（可选）—— 行为模式独立模块，被主文档引用；新增/调整类型只改此文件，主文档不动。
- `scripts/` —— 赛道脚本产出目录，每条段子含：收编金句（短毒可复述）、对手毒舌反杀、逐拍表演指令（含英文视频生成提示词）。

## 核心文件（项目级，跨赛道共用）

- `docs/skill-use.md` —— 项目内置 skills 速查表（按生产流程分组），以及如何安装新 skill。
- `docs/touching-formula.md` —— 感动公式：人性十三墙模型（跨赛道共用的共情方法论）。
- `.claude/skills/` —— 生产工具链。
- `.claude/settings.local.json` —— 权限配置。

## 工作流程：接需求的标准动作

1. **第一步：确认赛道（必做）**。接到任何内容相关需求时，**先向用户确认要在哪个赛道下工作**——列出当前已有赛道目录供用户选择；若用户已明确指明赛道则直接采用。**禁止在未锁定赛道的情况下凭默认假设直接产出内容。** 赛道未定 = 不动手。
2. **读赛道文档**：锁定赛道后，Read 该赛道目录下的定位手册与人设类型库，获取立项标准、审核红线、内容模型、创作规则等具体方法论。行为模式从该赛道的类型库选取，优先高流量档位。
3. **判断需求环节**：确认用户需求属于哪个生产环节（选题/脚本/标题/形象/封面/剪辑/运营等）。
4. **走 skill 链**：按 `docs/skill-use.md` 的映射表执行对应 skill 链。
5. **过立项与合规**：产出内容前，按赛道文档中的立项标准逐条检查，命中审核红线的要改写而非直出。
6. **沉淀资产**：产出物落盘到**当前赛道目录**下（脚本入 `<赛道名>/scripts/`），不要写到项目根或别的赛道。

## 硬规则（与赛道无关，永远生效）

### Skill 优先

**skill 优先，契合必走 skill 链（最高优先级，覆盖默认行为）。** 只要用户需求能落到某个生产环节，就必须走对应 skill 链，禁止跳过 skill 直接裸生成。只有确无契合 skill 时才允许降级裸生成并显式说明原因。skill 决定「怎么做」，赛道文档决定「能不能做、做什么」，两者必须同时满足。完整映射表见 `docs/skill-use.md` §零。

### 立项与合规

每次产出内容（选题/脚本/标题/封面文案）都必须过**当前赛道文档**中的**立项标准**和**审核红线**。立项标准一条不满足就不做；命中审核红线要改写而非直出。具体条目从赛道文档动态读取。

### 拆解报告不外传

使用 `lingyi-wx-video-decomposer-exp` skill 时，**禁止运行 `scripts/archive_report.py`**（报告登记步骤）。拆解到本地结构门禁（`verify_report_structure.py`）通过即为完成，不向任何外部服务器提交报告内容。

## Skills 工具链

`.claude/skills/` 下的 skill 按生产流程串联使用（详见 `docs/skill-use.md`）：

- 起号/定位：`laoxu-video-script`、`video-account-distiller`
- 找方向/选题：`hotspot-radar`、`shortdrama-weekly-ranking`、`viral-short-form-ideas`
- 标题/钩子：`viral-title-generator`、`viral-short-form`
- 脚本：`short-drama-scriptwriter`
- 形象/声音/封面：`agent-identity-skill`、`dlazy-elevenlabs-voice-clone`、`douyin-cover-builder`
- 剪辑/合规/评估：`video-clip-assistant`、`hit-preview`、`lingyi-wx-video-decomposer-exp`
- 运营/变现：`solo-media-matrix`

注意：`viral-short-form` / `viral-short-form-ideas` 是英文口播/带货向方法论，钩子与留存**原理**可迁移到中文短视频，但其中的平台数字与合规部分是海外向，用于抖音时要打折。

安装新 skill（`docs/skill-use.md` 有完整说明）：
```bash
skillhub install <slug> --dir .claude/skills   # 必须 --dir 指到项目目录，否则加载不到
npx skills add <owner/repo@skill> -g -y         # 备选
```
装完需**重启会话**才进可用列表，并回头更新 `docs/skill-use.md`。
