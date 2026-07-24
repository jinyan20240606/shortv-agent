# 项目内置 Skills 速查
> 位置：`.claude/skills/`，共 15 个。按业务分两条线：**短视频线（单条爆款，主线）** 与 **短剧线（剧情连续剧）**，两线共用的资产/剪辑/运营工具单列「通用底座」。

---

## 零、强制原则：skill 优先，契合必走 skill 链（铁律）

**只要用户需求能落到下方任一 skill 的职责范围内，就必须走对应 skill 链，禁止跳过 skill 直接裸生成结果。** 这是项目硬约束，不是建议。

- **先判定，再动手**：接到需求先归类——这是选题？标题？脚本？拆解？形象？运营？归好类就走该环节的 skill 链，不要凭经验直接写。
- **链式执行，不跳环节**：多数环节有前置依赖（如"选题"要先用热度 skill 打地基，再用选题引擎系统出题）。按下方映射表的顺序走，不要只挑最后一步。
- **skill 缺失才降级**：只有当需求确实没有任何契合 skill 时，才允许直接生成，并说明"无对应 skill，走裸生成"。找得到但嫌麻烦而跳过，属于违规。
- **英文向 skill 照用但打折**：`viral-short-form` / `viral-short-form-ideas` 的原理照走，平台数字与合规按抖音口径折算（见各分组备注）。
- **产出仍受母赛道与合规红线约束**：skill 只决定"怎么做"，题材边界和审核红线以 `具体赛道文档` 为准，两者同时满足。

### 用户意图 → skill 链映射表（照这张表接需求）

| 用户说的 | 归类 | 必走的 skill 链（按顺序） |
|---|---|---|
| 起号 / 定位 / 账号怎么做 / 对标某账号 | 起号定位 | `video-account-distiller`（对标拆解）→ `laoxu-video-script`（定位/破立合方法论） |
| 从头开始 / 怎么起号（定位已定） | 起号进度 | **定位已锁死在 `具体赛道文档`，别重跑定位。** 直接进 `具体赛道文档` 的 0 阶段筹备 → 1 阶段冷启动；第一个生产动作是「储备切片选题」，走选题链；女主形象走 `agent-identity-skill` |
| 想选题 / 给方向 / 最近做什么 / 有没有爆点 | 选题 | `hotspot-radar` + `shortdrama-weekly-ranking`（热度地基）→ `viral-short-form-ideas`（系统出题）→ `laoxu-video-script`（母题库补充） |
| 起标题 / 标题不行 / 换个标题 | 标题 | `viral-title-generator` |
| 写钩子 / 开头留不住人 / 完播低 / 脚本 | 钩子·脚本 |  `viral-short-form`（钩子原型+留存结构+掉粉诊断） |
| 拆解这条爆款 / 为什么它火 / 照着抄 | 拆解迭代 | `lingyi-wx-video-decomposer-exp` |
| 最近什么短剧火 / 短剧题材 | 短剧找题材 | `shortdrama-weekly-ranking` |
| 写短剧剧本 / 出大纲 / 人物小传 | 短剧出剧本 | `short-drama-scriptwriter` |
| 这剧本能不能爆 / 评估一下 | 短剧评估 | `hit-preview`（钩子/悬念评分+爆款预演） |
| 定主角形象 / 保持形象一致 / 数字人 | 形象 | `agent-identity-skill`（先形象初始化再出场景） |
| 配音 / 音色 / 统一声音 | 声音 | `dlazy-elevenlabs-voice-clone` |
| 做封面 / 封面文案 / 封面图 | 封面 | `douyin-cover-builder` |
| 剪视频 / 加字幕 / 导出短视频 | 剪辑 | `video-clip-assistant` |
| 内容日历 / 多平台分发 / 涨粉诊断 / 变现 / 商单 | 运营变现 | `solo-media-matrix` |

> 需求跨多个环节时，串联多条链（如"从选题到成片"= 选题链 → 标题 → 钩子脚本 → 剪辑）。

---

## 一、短视频线（单条爆款 · 主线）
> 流程：起号定位 → 选题 → 标题/钩子/脚本 → 拆解迭代。

### ⓪ 起号 / 定位 / 对标研究
| Skill | 一句话作用 |
|---|---|
| **laoxu-video-script** 自媒体起号方法论 | 老徐教学版：定位/选题/破立合成稿/五维诊断/去AI味/112条母题库，零基础起号 |
| **video-account-distiller** 账号拆解蒸馏 | 批量研究抖音/小红书账号，提炼定位/人设/爆款规律，沉淀 IP 风格档案 |

### ① 选题 / 找方向
| Skill | 一句话作用 |
|---|---|
| **hotspot-radar** 全网热榜雷达 | 聚合微博/知乎/抖音/B站/小红书热搜，找选题与情绪爆点（热点输入） |
| **viral-short-form-ideas** 选题引擎 | 内容支柱+内容矩阵+评论/竞品挖掘+90天想法管线，系统化批量出选题 · 英文向，框架通用、平台数字打折 |

### ② 标题 / 钩子 / 脚本（决定完播）
| Skill | 一句话作用 |
|---|---|
| **viral-title-generator** 爆款标题生成器 | 多平台高点击率标题、标题改写（管标题文字） |
| **viral-short-form** 短视频爆款总控 | 10种钩子原型 + Hook→升级→payoff→CTA 留存结构 + 掉粉诊断改稿（管视听钩子+脚本）· 英文向，原理通用 |

### ③ 拆解 / 迭代
| Skill | 一句话作用 |
|---|---|
| **lingyi-wx-video-decomposer-exp** 视频号爆款拆解 | 本地上传视频→拆结构/爆款归因/六维评分，照着学照着抄 |

---

## 二、短剧线（剧情连续剧）
> 流程：找题材 → 出剧本 → 爆款预演评估。

| 环节 | Skill | 一句话作用 |
|---|---|---|
| 找题材 | **shortdrama-weekly-ranking** 短剧每周热榜 | 抓公众号周榜，看当下什么短剧题材在火 |
| 出剧本 | **short-drama-scriptwriter** 短剧剧本架构师 | 主题→5个爆款标题+梗概+人物小传+前10集大纲 |
| 评估 | **hit-preview** 短剧爆款预演器 | 钩子/悬念评分、爆款潜力预测、弹幕模拟、情绪热力图 |

---

## 三、通用底座（两条线共用）

### 形象 / 声音 / 封面（资产标准化，0阶段地基）
| Skill | 一句话作用 |
|---|---|
| **agent-identity-skill** 数字人形象养成 | 定义一次主角身份→跨场景形象永久一致（IP 地基，先做形象初始化再出场景；短剧女主尤其需要） |
| **dlazy-elevenlabs-voice-clone** 音色克隆 | 上传人声样本→复刻专属统一音色 |
| **douyin-cover-builder** 抖音封面 | 输入主题+人物气质→出封面生图提示词 |

### 剪辑 / 运营 / 变现
| Skill | 一句话作用 |
|---|---|
| **video-clip-assistant** 自动剪辑 | FFmpeg 自动提取片段+烧字幕+导出短视频 |
| **solo-media-matrix** 自媒体矩阵管理器 | 内容日历+多平台分发+数据复盘+涨粉诊断+变现路径+商单，覆盖 1-10 阶段运营 |

---

## 如何查找 / 安装新 Skill
> 后续想找新 skill，用 **skillhub**（中文短剧/自媒体生态最全，首选）或 **skills**（skills.sh，英文/通用开发类为主）。

### skillhub（首选，中文垂类多）
```bash
# 搜索（多关键词就分别搜，噪音多时再用 grep 过滤）
skillhub search 短剧
skillhub search 账号定位

# 安装到本项目（关键：--dir 指到项目 skills 目录，否则默认装去 openclaw 路径加载不到）
skillhub install <skill-slug> --dir .claude/skills

# 其他
skillhub --version          # 查看版本
```
- CLI 位置：`~/.local/bin/skillhub`（若 `skillhub` 命令找不到，用全路径 `~/.local/bin/skillhub`）。
- 下载源为第三方腾讯云 COS + `api.skillhub.cn`，装前可留意 skill 是否标注【付费】/需 API Key。

### skills（skills.sh，备选）
```bash
npx skills find <关键词>                    # 搜索
npx skills add <owner/repo@skill> -g -y     # 安装（-g 全局，-y 免确认）
```
- 认准安装量与来源（`anthropics`/`vercel-labs` 等官方源更可靠，1K+ installs 优先）。

### 安装后
- 新 skill 需**重启会话**才进可用列表。
- 装完记得回来更新本速查表（归到对应流程分组）。