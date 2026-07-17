# 🎨 Agent Identity Studio

> **[中文版 →](README.md)**

AI-powered digital character identity cultivation skill. Define a character once, generate consistently across unlimited scenes and engines.

## What Is This

A Skill that runs on any AI Agent platform supporting skill loading — such as [OpenClaw](https://github.com/anthropics/claw), [WorkBuddy](https://www.codebuddy.cn/docs/workbuddy/Overview), or similar frameworks.

You tell it "what my character looks like," and it automatically handles:

- **Identity Initialization** — Describe a character → generate 3 proof shots → confirm & lock identity
- **Scene Generation** — One sentence = one image: *"Take a photo of her at a cozy cafe"*
- **Character Consistency** — No matter how scenes, outfits, or lighting change, your character stays recognizable
- **Audit Auto-Handling** — Built-in safety vocabulary + automatic fallback retry on rejections
- **Cosplay Mode** — Change costume, keep identity — character features always preserved

## Design Highlights

### 🧬 Two-Layer Architecture: Identity × Scene Decoupling

The core design principle of this skill:

| Layer | Controls | Owned By |
|-------|----------|----------|
| Character Sheet (Identity) | Facial features, hair color, eye color, accessories, body type, personality | Fixed — shared across all scenes |
| Scene Card (Scene) | Location, outfit, lighting, expression, composition | Varies per generation |

Traditional approaches repeat character descriptions in every prompt, leading to inconsistencies. This skill locks identity traits in a YAML file — the scene layer **cannot** touch identity fields (hair color, eye color, etc.). They are rendered exclusively from the identity layer.

### 📐 Tiered Body Description System

| Composition | Body Description | Why |
|-------------|-----------------|-----|
| Close-up / Portrait | None | Only face visible — body info is noise |
| Medium Shot | Basic body type + garment silhouette | Just enough, not excessive |
| Full Body | Complete body type + legs + stance | Full proportions needed |
| Loose Outfit | Auto-appended compensation keywords | Prevents baggy clothes from "erasing" the figure |

No manual adjustment needed — `gen.py` auto-selects the tier based on the Scene Card's `composition` field.

### 🛡️ Audit Safety: Describe the Clothes, Not the Body

Image generation APIs are sensitive to body-related descriptions. The skill includes a safety phrasing system:

| Desired Effect | ✅ Safe Phrasing | ❌ Gets Blocked |
|----------------|-----------------|----------------|
| Show curves | `form-fitting dress that hugs her curves` | `curvy body` |
| Nice legs | `showing shapely legs` | `long sexy legs` |
| Neckline | `V-neck dress with elegant draping` | `showing bust` |

Principle: **Describe how the clothes fit, not what the body looks like.** Auto-fallback retry (up to 2x) on rejection.

### 🎯 Dual Reference Image Strategy

| Composition | Reference Used | Locks |
|-------------|---------------|-------|
| Medium / Portrait | Front-facing ref | Facial features |
| Full Body | 3/4 side ref | Body proportions |

Reference images are **optional** — for characters matching the engine's native art style, pure prompt consistency can actually be better. Refs are most valuable for anchoring "non-native" characters (e.g., user-uploaded custom designs).

Two delivery methods supported:
- **Local data:URI** (`data:image/png;base64,...`) — no external URL dependency
- **Public URL** — for CDN-hosted references

⚠️ **Note**: MiniMax's `image_base64` field is non-functional. Always use the `image_file` field (URL or data:URI both work).

## Live Demos

Same character, 22+ different scenes, identity features automatically maintained:

| Scene | Outfit | Composition |
|-------|--------|-------------|
| ☕ Cafe Date | White turtleneck sweater | Medium |
| 🌧️ Rainy Street | Beige trench coat + transparent umbrella | Full body |
| 🌸 Cherry Blossom Park | Blue sundress + white cardigan + straw hat | Full body |
| 📚 Library | Round glasses + cream sweater | Medium |
| 🎪 Night Market | Denim jacket + striped tee | Medium |
| 💼 Office | Charcoal suit + white blouse | Medium |
| 🏖️ Beach Sunset | White linen dress | Full body |
| 🎄 Christmas Fireplace | Red oversized sweater | Medium |
| 🎭 Cosplay | School uniform / stage outfit (character hair & eyes preserved) | Full body |
| 🏋️ Yoga | Sports tank + leggings | Medium |

**Live Demo (MiniMax Engine)**: https://amayazhao.github.io/nami-gallery/showcase/nami.html

**Live Demo (Hunyuan Engine)**: https://amayazhao.github.io/nami-gallery/showcase/hunyuan/

## Setup & Installation

### Step 1: Install the Skill

Place the `agent-identity-studio/` folder into your Agent platform's skills directory.

Example paths for different platforms:
```
# WorkBuddy / CodeBuddy
~/.workbuddy/skills/agent-identity-studio/

# OpenClaw
~/.claw/skills/agent-identity-studio/

# Other platforms: check your platform's skill installation docs
```

The agent will automatically detect **agent-identity-studio** after installation.

### Step 2: Get an API Key (pick one)

**Option A: MiniMax (default engine)**
1. Sign up at [MiniMax Platform](https://www.minimaxi.com/)
2. Create an app and get your API Key
3. Set as environment variable: `MINIMAX_API_KEY`

**Option B: Tencent Hunyuan 3.0** (via Tencent Cloud SDK)
1. Go to [Tencent Cloud Console](https://console.cloud.tencent.com/) and enable the Hunyuan Image service
2. Get SecretId + SecretKey from [API Key Management](https://console.cloud.tencent.com/cam/capi)
3. Set environment variables: `TENCENT_SECRET_ID` + `TENCENT_SECRET_KEY`
4. Install SDK: `pip install tencentcloud-sdk-python-aiart`
5. Switch engine: `IDENTITY_STUDIO_ENGINE=hunyuan`

```bash
# macOS / Linux — MiniMax example
export MINIMAX_API_KEY="your_key"

# For Hunyuan
export TENCENT_SECRET_ID="your_secret_id"
export TENCENT_SECRET_KEY="your_secret_key"
export IDENTITY_STUDIO_ENGINE="hunyuan"
pip install tencentcloud-sdk-python-aiart
```

| Engine | Model | Cost/Image | Speed | Ref Images | Dependencies |
|--------|-------|-----------|-------|------------|-------------|
| MiniMax | image-01 | ~¥0.025 (~$0.003) | 15-30s | 1 (data:URI / URL) | None |
| Tencent Hunyuan | HY-Image-V3.0 | ~¥0.20 (~$0.03) | 4-7s | Up to 3 | `tencentcloud-sdk-python-aiart` |

### Step 3: Start Using

Say to your agent:

> Create a digital character: silver short hair, amber eyes, cheerful energetic girl

The skill will auto-run identity initialization → generate proof shots → wait for your confirmation.

After confirming, just describe any scene:

> Take a photo of her walking in the rain with an umbrella, cinematic feel

## Usage Examples

| You Say | Skill Does |
|---------|-----------|
| "Create a character: red long hair, green-eyed magical girl" | Initialize Character Sheet → generate 3 proof shots |
| "Take a cafe photo" | Design Scene Card → assemble prompt → call API → return image |
| "A weekend home photoshoot series, 4 shots" | Batch generate multi-scene session |
| "Make the hair color a bit darker" | Modify Character Sheet → re-verify |
| "Cosplay as Mai Sakurajima" | Costume-swap mode (identity preserved) |

## Technical Specs

| Metric | MiniMax | Tencent Hunyuan |
|--------|---------|-----------------|
| Model | image-01 | HY-Image-V3.0 |
| Cost/Image | ~¥0.025 (~$0.003) | ~¥0.20 (~$0.03) |
| Speed | 15-30s | 4-7s |
| Max Ref Images | 1 | 3 |
| Call Mode | Synchronous | Async (SDK, submit + poll) |
| Dependencies | None (stdlib only) | `tencentcloud-sdk-python-aiart` |
| Auth | `MINIMAX_API_KEY` | `TENCENT_SECRET_ID` + `TENCENT_SECRET_KEY` |
| Engine Switch | Default | `IDENTITY_STUDIO_ENGINE=hunyuan` |

## FAQ

| Issue | Solution |
|-------|----------|
| `MINIMAX_API_KEY not set` | Check env vars; restart terminal after setting |
| `TENCENT_SECRET_ID / SECRET_KEY not set` | Check env vars; confirm `pip install tencentcloud-sdk-python-aiart` |
| Image rejected by audit (1033) | Prompt contains sensitive words; auto-fallback retry; adjust outfit descriptions if persistent |
| MiniMax ref image `unknown error` | `image_base64` is broken; use `image_file` with data:URI or URL |
| Hunyuan generation timeout | Async poll waits up to 120s; retry on network issues |
| Character looks different each time | Confirm `character-sheet.yaml` exists with `meta.confirmed: true` |
| Full body proportions look off | Avoid `tall` / `model-like` / `slender` in body descriptions |
| How to switch engines | Set `IDENTITY_STUDIO_ENGINE=hunyuan` or `minimax` |

## License

[MIT](LICENSE)
