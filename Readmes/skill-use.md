# 项目内置 Skills 速查
> 位置：`.claude/skills/`，共 23 个。按生产流程「起号定位 → 找方向 → 标题钩子 → 出剧本 → AI视频 → 形象声音封面 → 剪辑合规评估 → 运营变现」分组。
## 项目级常用技能
### ⓪ 起号 / 定位 / 人设（前置策略）
| Skill | 一句话作用 |
|---|---|
| **duanshipin** 薛辉短视频运营技巧 | 账号定位+流量获取+IP人设+变现+避坑实战方法论（无需API，适合0起号） |
| **audience-mapper** 目标受众画像 | 受众/人群画像、细分社群与亚文化调研，锁定「都市女性逆袭」人群 |

### ① 找方向 / 选题
| Skill | 一句话作用 |
|---|---|
| **hotspot-radar** 全网热榜雷达 | 聚合微博/知乎/抖音/B站/小红书热搜，找选题与情绪爆点 |
| **shortdrama-weekly-ranking** 短剧每周热榜 | 抓公众号周榜，看当下什么短剧题材在火 |
| **content-idea-generator** 选题生成器 | 基于热点出抖音/小红书/B站选题建议 |

### ② 标题 / 钩子（决定完播）
| Skill | 一句话作用 |
|---|---|
| **viral-title-generator** 爆款标题生成器 | 多平台高点击率标题、标题改写 |
| **shortvideo-hook** 黄金3秒钩子 | 生成开头钩子，拉完播率 |

### ③ 脚本创作
| Skill | 一句话作用 |
|---|---|
| **short-video-script** 短视频脚本创作 | 口播脚本+标题+封面建议（前期短视频主力） |
| **short-drama-scriptwriter** 短剧剧本架构师 | 主题→5个爆款标题+梗概+人物小传+前10集大纲 |
| **xyq-short-drama** 短剧剧本创作助手 | 一句话创意→完整分集剧本（场景/对话/尾帧） |

### ④ AI 视频 / 分镜（后续 AI 短剧）
| Skill | 一句话作用 |
|---|---|
| **video-prompt-expert** 视频提示词（Seedance2.0） | 写专业级视频提示词，直接生成 MP4 |
| **storyboard-sketch-narrative** 分镜故事板 | 多宫格分镜+视频生成提示词 |
| **ark-novel-to-tuiwen** 小说转推文分镜 | 小说原文→标题+人物卡+场景卡+逐段分镜 |

### ⑤ 形象 / 声音 / 封面（资产标准化，0阶段地基）
| Skill | 一句话作用 |
|---|---|
| **agent-identity-skill** 数字人形象养成 | 定义一次女主身份→跨场景形象永久一致（IP 地基，先做形象初始化再出场景） |
| **dlazy-elevenlabs-voice-clone** 音色克隆 | 上传人声样本→复刻专属统一音色 |
| **audio-cog** AI音频/配音 | 用克隆音色出旁白/对话/音效（OpenAI/ElevenLabs/MiniMax） |
| **douyin-cover-builder** 抖音封面 | 输入主题+人物气质→出封面生图提示词 |

### ⑥ 剪辑 / 合规 / 评估
| Skill | 一句话作用 |
|---|---|
| **video-clip-assistant** 自动剪辑 | FFmpeg 自动提取片段+烧字幕+导出短视频 |
| **douyin-sensitive-check** 违禁词检测 | 本地词库，发布前扫文案合规（免 API） |
| **hit-preview** 短剧爆款预演器 | 钩子/悬念评分、爆款潜力预测、弹幕模拟、情绪热力图 |
| **lingyi-wx-video-decomposer-exp** 视频号爆款拆解 | 本地上传视频→拆结构/爆款归因/六维评分 |

### ⑦ 运营 / 变现
| Skill | 一句话作用 |
|---|---|
| **solo-media-matrix** 自媒体矩阵管理器 | 内容日历+多平台分发+数据复盘+涨粉诊断+变现路径+商单，覆盖 1-10 阶段运营 |

**一条龙**：起号定位/人设(duanshipin/audience-mapper/ip-persona-video-sop) → 形象/音色初始化(agent-identity-skill/voice-clone) → 选题(hotspot-radar/weekly-ranking/content-idea) → 标题钩子(viral-title/shortvideo-hook) → 脚本(short-video-script / short-drama-scriptwriter → xyq-short-drama) → AI视频(video-prompt-expert/storyboard) → 配音出图封面(audio-cog/douyin-cover-builder) → 剪辑(video-clip-assistant) → 合规(douyin-sensitive-check) → 评估拆解(hit-preview/lingyi) → 运营变现(solo-media-matrix)。

> ⚠️ 仍缺「执行层出图工具」：video-prompt-expert 只出提示词、agent-identity-skill 定形象，但真正批量生成分镜画面还需要 `nano-banana-cut`（AI生图+自动切九宫格）或 `image-cog`（角色一致性生图）。需要再装。

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