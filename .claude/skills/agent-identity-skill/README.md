# 🎨 Agent Identity Studio — 数字人形象养成工作室

> **[English version →](README_EN.md)**

AI 驱动的数字人形象生成技能，定义一次角色身份，跨场景无限生成，形象永远一致。

## 这是什么

一个运行在 AI Agent 平台上的 Skill。兼容任何支持 Skill 加载的 Agent 框架（如 [OpenClaw](https://github.com/anthropics/claw)、[WorkBuddy](https://www.codebuddy.cn/docs/workbuddy/Overview) 等）。

你告诉它"我的角色长什么样"，它会自动完成：

- **形象初始化**（描述角色 → 生成3张验证照 → 确认锁定身份）
- **场景写真生成**（说一句话就出图：「帮我拍一张咖啡馆的场景照」）
- **角色一致性保障**（不管换什么场景、穿搭、光影，TA 永远是 TA）
- **审核自动处理**（内置安全词库 + 被拒后自动降级重试，不用你操心）
- **Cosplay模式**（换装不换人，角色特征永远保留）

## 设计亮点

### 🧬 两层分离架构：身份和场景彻底解耦

这是整个 Skill 最核心的设计：

| 层级 | 管什么 | 谁控制 |
|------|--------|--------|
| Character Sheet（身份层）| 五官、发色、瞳色、发饰、身材、气质 | 固定不变，所有场景共享 |
| Scene Card（场景层）| 地点、穿搭、光影、表情、构图 | 每次生成都不同 |

为什么这样设计？传统方式每次生成都要在 Prompt 里重复角色描述，容易写漏、写错、每次微妙不一致。这个 Skill 把角色定义固化在 YAML 文件里，场景层绝对不允许触碰身份特征——发色、眼色、五官等字段只在身份层渲染，场景层碰都碰不到。

### 📐 身材分级系统：不同构图自动适配

| 构图 | 身体描述 | 原因 |
|------|----------|------|
| 特写/头像 | 不加身材描述 | 画面只有脸，加了反而干扰 |
| 半身照 | 基础体型 + 衣服勾勒 | 够用，不过度 |
| 全身照 | 完整体型 + 腿部 + 姿态 | 全身需要完整比例信息 |
| 宽松衣服 | 自动追加补偿词 | 防止宽松衣服"吃掉"身材描述 |

不需要手动调，gen.py 根据 Scene Card 的 `composition` 字段自动选择对应级别。

### 🛡️ 审核安全：不说身体说衣服

MiniMax 的内容审核对身体描述敏感。Skill 内置了一套安全话术体系：

| 你想要的效果 | ✅ 安全写法 | ❌ 会被拦截 |
|-------------|-----------|-----------|
| 展现身材曲线 | `form-fitting dress that hugs her curves` | `curvy body` |
| 好看的腿 | `showing shapely legs` | `long sexy legs` |
| 领口设计 | `V-neck dress with elegant draping` | `showing bust` |

原则：**描述衣服怎么穿，不描述身体长什么样。** 被拦截后自动降级 prompt 重试，最多 2 次。

### 🎯 参考图双策略：按需锁脸 / 锁身材

| 构图 | 用哪张参考图 | 锁什么 |
|------|-------------|--------|
| 半身 / 特写 | 正面参考图 | 锁定面部特征 |
| 全身 | 3/4侧面参考图 | 锁定身体比例 |

参考图可选不强制——对于原生画风角色，纯 Prompt 的一致性反而更好。参考图更适合"非原生"角色（如用户上传自己画的角色）的锚定。

支持两种传参方式：
- **本地 data:URI**（`data:image/png;base64,...`）— 不依赖外部 URL
- **公开 URL** — 适合已部署到 CDN 的参考图

⚠️ **注意**：MiniMax 的 `image_base64` 字段完全不可用，必须通过 `image_file` 字段传递（URL 或 data:URI 均可）。

## 效果展示

同一个角色，22+ 种不同场景，角色特征全自动保持：

| 场景 | 穿搭 | 构图 |
|------|------|------|
| ☕ 咖啡馆约会 | 白色高领毛衣 | 半身 |
| 🌧️ 雨夜街头 | 米色风衣+透明伞 | 全身 |
| 🌸 樱花公园 | 蓝裙+白开衫+草帽 | 全身 |
| 📚 图书馆 | 圆框眼镜+奶白毛衣 | 半身 |
| 🎪 夜市 | 牛仔外套+条纹T | 半身 |
| 💼 办公室 | 深灰西装+白衬衫 | 半身 |
| 🏖️ 海边夕阳 | 白色亚麻裙 | 全身 |
| 🎄 圣诞壁炉 | 红色oversized毛衣 | 半身 |
| 🎭 Cosplay | 校服/舞台装（保持角色发色瞳色） | 全身 |
| 🏋️ 瑜伽 | 运动背心+leggings | 半身 |

**在线Demo**: https://amayazhao.github.io/nami-gallery/showcase/nami.html

## 配置与安装

### 第一步：安装技能

将 `agent-identity-studio/` 文件夹放到你的 Agent 平台的 Skills 目录下即可。

不同平台的路径示例：
```
# WorkBuddy / CodeBuddy
~/.workbuddy/skills/agent-identity-studio/

# OpenClaw
~/.claw/skills/agent-identity-studio/

# 其他平台：参考对应文档的 Skill 安装目录
```

安装成功后，Agent 会自动识别 **agent-identity-studio** 技能。

### 第二步：获取 API Key（二选一即可）

**方式 A：MiniMax（默认引擎）**
1. 前往 [MiniMax开放平台](https://www.minimaxi.com/) 注册
2. 创建应用，获取 API Key
3. 设为环境变量：`MINIMAX_API_KEY`

**方式 B：腾讯混元生图 3.0**（via 腾讯云 SDK）
1. 前往 [腾讯云控制台](https://console.cloud.tencent.com/) 开通混元生图服务
2. 在 [API密钥管理](https://console.cloud.tencent.com/cam/capi) 获取 SecretId + SecretKey
3. 设为环境变量：`TENCENT_SECRET_ID` + `TENCENT_SECRET_KEY`
4. 安装 SDK：`pip install tencentcloud-sdk-python-aiart`
5. 切换引擎：`IDENTITY_STUDIO_ENGINE=hunyuan`

```bash
# Windows PowerShell — 以 MiniMax 为例
[Environment]::SetEnvironmentVariable('MINIMAX_API_KEY', '你的key', 'User')

# 如果用混元
[Environment]::SetEnvironmentVariable('TENCENT_SECRET_ID', '你的SecretId', 'User')
[Environment]::SetEnvironmentVariable('TENCENT_SECRET_KEY', '你的SecretKey', 'User')
[Environment]::SetEnvironmentVariable('IDENTITY_STUDIO_ENGINE', 'hunyuan', 'User')
pip install tencentcloud-sdk-python-aiart
```

| 引擎 | 模型 | 单张成本 | 速度 | 参考图 | 外部依赖 |
|------|------|---------|------|--------|---------|
| MiniMax | image-01 | ~¥0.025 | 15-30s | 1张（data:URI / URL）| 无 |
| 腾讯混元 | HY-Image-V3.0 | ~¥0.20 | 4-7s | 最多3张 | `tencentcloud-sdk-python-aiart` |

### 第三步：开始使用

在 Agent 中发：

> 帮我创建一个数字人形象：银色短发、琥珀色眼睛、活泼开朗的少女

Skill 会自动完成形象初始化 → 生成验证照 → 等你确认。

确认后，发任意场景描述即可生成：

> 帮我拍一张雨中撑伞的场景照，要有电影感

## 使用方式

| 你说的话 | Skill 做什么 |
|---------|------------|
| 「创建一个角色：红色长发、绿眼睛的魔法少女」 | 初始化 Character Sheet → 生成3张验证照 |
| 「帮我拍一张咖啡馆的照片」 | 设计 Scene Card → 拼装 Prompt → 调用 API → 返回图片 |
| 「来一组周末居家写真集，4张」 | 批量生成多场景 Session |
| 「头发颜色再深一点」 | 修改 Character Sheet → 重新验证 |
| 「Cosplay成樱岛麻衣」 | 换装不换人模式 |

## 技术数据

| 指标 | MiniMax | 腾讯混元 |
|------|---------|---------|
| 模型 | image-01 | HY-Image-V3.0 |
| 单张成本 | ~¥0.025 | ~¥0.20 |
| 生成速度 | 15-30s | 4-7s |
| 参考图上限 | 1张 | 3张 |
| 调用模式 | 同步 | 异步（SDK，提交+轮询）|
| 外部依赖 | 无 | `tencentcloud-sdk-python-aiart` |
| 认证方式 | `MINIMAX_API_KEY` | `TENCENT_SECRET_ID` + `TENCENT_SECRET_KEY` |
| 引擎切换 | 默认 | `IDENTITY_STUDIO_ENGINE=hunyuan` |

## 常见问题

| 问题 | 排查 |
|------|------|
| `MINIMAX_API_KEY not set` | 检查环境变量，新终端需重启才能读到 |
| `TENCENT_SECRET_ID / SECRET_KEY not set` | 检查环境变量；确认已 `pip install tencentcloud-sdk-python-aiart` |
| 图片被审核拦截 (1033) | Prompt 含敏感词，自动降级重试；如持续失败，调整穿搭描述 |
| MiniMax 参考图报 `unknown error` | image_base64 不可用，需用 image_file + data:URI 或 URL |
| 混元生成超时 | 异步轮询最多等 120s；网络或并发问题可重试 |
| 角色每次长得不一样 | 确认 character-sheet.yaml 已创建且 meta.confirmed=true |
| 全身照比例奇怪 | 避免使用 `tall` / `model-like` / `slender` |
| 怎么切换引擎 | 设环境变量 `IDENTITY_STUDIO_ENGINE=hunyuan` 或 `minimax` |
