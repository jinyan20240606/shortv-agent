---
name: agent-identity-studio
description: |
  A digital identity cultivation skill for AI Agent characters.
  Separates identity definition (Character Sheet) from scene generation (Scene Card),
  ensuring visual consistency across unlimited scenes while allowing full creative freedom.

  Supports: identity initialization, standard proof generation, identity locking,
  tuning, and continued scene output for the same character.

  Triggers: 数字人, 形象, 角色, identity, avatar, character, portrait, 写真,
  photoshoot, 头像, 形象照, cosplay, or any request to generate consistent character images.

  IMPORTANT: Character identity must be confirmed (形象初始化) before any scene shoots.
---

# Agent Identity Studio

> **Core principle**: Define "who they are" first, then generate "what they're doing".
> Character Sheet (fixed) + Scene Card (variable) = consistent visual output.

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│  Layer 0 — Engine (API / Audit / Retry)         │
│  MiniMax image-01, ~¥0.025/image, 15-30s/image  │
├─────────────────────────────────────────────────┤
│  Layer 1 — Character Sheet (Fixed)              │
│  Face + Body + Personality + Style + Reference  │
│  → render() → fixed prompt segment              │
├─────────────────────────────────────────────────┤
│  Layer 2 — Scene Card (Variable per shot)       │
│  Location + Outfit + Pose + Lighting + Comp     │
│  → render() → variable prompt segment           │
├─────────────────────────────────────────────────┤
│  Prompt Assembly                                 │
│  final = character_prompt + expression + scene   │
└─────────────────────────────────────────────────┘
```

## Image Generation Engine — MiniMax image-01

### API Configuration
- **API URL**: `https://api.minimaxi.com/v1/image_generation`
- **Model**: `image-01`
- **Auth**: Bearer Token from env `MINIMAX_API_KEY`
- **Cost**: ~¥0.025/image (~40 images per ¥1)
- **Speed**: 15-30s/image (first call may be slower)

### Gen Script
- **Path**: `scripts/gen.py`
- **Usage**: `from gen import CharacterSheet, SceneCard, Engine, generate, generate_session`
- **CLI**: `python gen.py proofs` / `python gen.py session --scenes '[...]' --output ./dir`
- **Dependencies**: None (pure Python stdlib)

### API Response Handling
- `status_code == 0` → success, download from `data.image_urls[0]`
- `status_code == 1033/1026` → content audit rejection → auto-retry with toned-down prompt
- `status_code == 1000` with subject_reference → fallback to no-ref generation
- `status_code == 1008` → insufficient balance
- Max 2 retries per image, then skip and report

### Subject Reference (Character Anchor)
- Use `image_file` field with `data:image/png;base64,...` URI (local files)
- Or `image_file` with public URL
- ⚠️ `image_base64` field is BROKEN on MiniMax — always use `image_file`
- Dual-ref strategy: front ref (face lock) + side ref (body lock)
- Reference images are optional — pure prompt works well for native MiniMax style characters

## Layer 1 — Character Sheet

### File
- **Path**: `~/.workbuddy/identity-studio/character-sheet.yaml`
- **Format**: YAML with structured identity fields
- **Status**: `meta.confirmed: true/false`

### Fields & Their Impact on Consistency

| Field | Impact | Notes |
|-------|--------|-------|
| reference_image | ★★★★★ | Visual anchor — critical for non-native characters |
| hair.color | ★★★★☆ | Most important text field in prompt |
| face.eyes | ★★★★☆ | Second most important text field |
| hair.signature_accessory | ★★★☆☆ | Unique identifier, disappears if omitted |
| personality.core_vibe | ★★★☆☆ | Controls maturity/age impression |
| body | ★★☆☆☆ | Only matters for full-body shots |
| art_style | ★☆☆☆☆ | MiniMax defaults to anime, minor effect |

### Prompt Rendering Rules

```python
# CharacterSheet.render(composition, garment) produces the fixed segment:
#
# Always: "beautiful mature anime girl, with {hair_color},
#          {eyes}, {signature_accessory}, {skin},
#          {art_base}, {quality}, {maturity_suffix}"
#
# + medium: adds half_body_type + curve_template(garment)
# + full_body: adds full_body_type + curve + legs + stance
# + loose outfit detected: adds loose_outfit_boost
```

**CRITICAL RULES**:
1. Character Sheet render output is identical across ALL scenes (body only varies by composition)
2. Maturity suffix is always appended automatically
3. Audit-safe body descriptions are built into curve/legs templates

## Layer 2 — Scene Card

### Structure

```python
SceneCard:
  name: str          # Scene name
  location: str      # Environment/setting
  time_of_day: str   # Time context
  atmosphere: str    # Mood/atmosphere
  garment: str       # Outfit (injected into curve_template)
  accessories: str   # Props/accessories
  pose: str          # Action/posture
  expression_override: str  # Expression (empty = use character default)
  lighting: str      # Lighting setup
  composition: str   # Shot type (close-up / medium / full body)
  aspect_ratio: str  # Image ratio
```

### ❌ Scene Card MUST NOT contain:

| Forbidden | Reason |
|-----------|--------|
| Hair color/style | Managed by Character Sheet |
| Eye color/shape | Managed by Character Sheet |
| Facial features | Managed by Character Sheet |
| Body type/figure | Auto-injected by Character Sheet |
| Age descriptors | Managed by Character Sheet |
| Art style | Managed by Character Sheet |
| Character name | Managed by Character Sheet |

### Expression System

```
Scene has expression_override → use override
Scene has no expression_override → use CharacterSheet.default_expression
```

**Expression levels (shallow → deep):**
```
# Level 1 — Casual/Cute
giving the viewer a gentle warm smile
looking over her shoulder at the viewer with a playful wink

# Level 2 — Intimate/Romantic
gazing at the viewer with a mysterious confident smile
looking warmly at the viewer with tender loving eyes

# Level 3 — Emotional/Deep
gazing at the viewer with warm tender eyes
eyes slightly moist with emotion, lips parted

# Level 4 — Alluring/Bold
looks over her shoulder with a confident half-smile
leaning forward with a happy surprised smile and flushed cheeks
```

## Workflow — Three Phases

### Phase 1: Identity Initialization (Required)

> ❌ No confirmed identity = no scene generation

```
1. Load or create character-sheet.yaml
2. Generate 3 standard proof images (gen.py proofs):
   - portrait-front.png — Front close-up
   - portrait-3quarter.png — 3/4 medium shot
   - full-body.png — Full body standing
   → White background, focus on character identity
3. User review:
   - ✅ Approved → meta.confirmed = true, lock sheet
   - ❌ Rejected → adjust fields, regenerate
   - 🔄 Tweak → modify specific fields
4. Output: character-sheet.yaml + reference/ directory
```

### Phase 2: Scene Generation (Requires confirmed identity)

```
Prerequisites: character-sheet.yaml meta.confirmed == true

1. Design scene → create SceneCard (DO NOT touch identity traits)
2. Auto-assemble prompt:
   char_prompt = sheet.render(composition, garment)
   expression  = scene.expression_override or sheet.default_expression
   scene_prompt = scene.render()
   final = f"{char_prompt}. {expression}. {scene_prompt}"
3. Call Engine → if audit fails, only downgrade SceneCard (NEVER touch CharacterSheet)
4. Save to sessions/YYYY-MM-DD-theme/
```

### Phase 3: Identity Tuning (Optional)

```
When user wants adjustments:
- "Not mature enough" → adjust personality.core_vibe + maturity_suffix
- "Proportions wrong" → adjust body fields
- "Expression too stiff" → adjust default_expression
→ Re-run proofs → user confirms → update reference images
```

## Content Safety — Audit Rules

### ❌ BANNED keywords (trigger rejection)
bikini, swimsuit, swimwear, lingerie, underwear, bra, backless,
spaghetti strap, naked, nude, topless, sexy body, busty, voluptuous,
bust, chest, hips, hourglass

### ✅ Safe body description: "describe the clothing, not the body"
| Want | Safe Phrasing | Dangerous Phrasing |
|------|--------------|-------------------|
| Curves | form-fitting dress that hugs her curves | curvy body |
| Neckline | V-neck dress with elegant draping | showing bust |
| Legs | showing shapely legs | long sexy legs |
| Collarbone | delicate collarbone showing | OK to write directly |

### Audit-failure Handling
1. Engine auto-retries up to 2 times with toned-down prompt
2. Only Scene Card gets modified (outfit/pose toned down)
3. Character Sheet NEVER changes due to audit
4. If 2 retries fail, skip and report

## Cosplay Mode

When generating cosplay images, the result must be **"[Character] cosplaying as [Target]"**.

### Core Rules
- **ALWAYS keep**: All Character Sheet identity traits (hair color, eye color, accessory)
- **CAN change**: Outfit, props, expression, scene, hairstyle (NOT color)
- **NEVER change**: Hair color, eye color, facial features

## File Structure

```
skills/agent-identity-studio/
├── SKILL.md                     ← This file (AI reads this)
├── README.md                    ← User-facing documentation
├── scripts/
│   └── gen.py                   ← Generation engine (zero dependencies)
├── references/
│   ├── audit-guide.md           ← Content safety rules
│   └── prompt-templates.md      ← Scene & expression templates
└── assets/

~/.workbuddy/identity-studio/    ← Runtime data (per-user)
├── character-sheet.yaml         ← Identity definition
├── reference/                   ← Proof images (Phase 1 output)
│   ├── ref-front.png            ← Front reference (face lock)
│   ├── ref-side.png             ← Side reference (body lock)
│   ├── portrait-front.png
│   ├── portrait-3quarter.png
│   └── full-body.png
└── sessions/                    ← Generated image sessions
    └── YYYY-MM-DD-theme/
```

## Quick Reference

### Generate Identity Proofs
```python
from gen import CharacterSheet, generate_character_proofs
from pathlib import Path

sheet = CharacterSheet.load()
results = generate_character_proofs(Path.home() / ".workbuddy/identity-studio/reference")
```

### Generate Photo Session
```python
from gen import generate_session
from pathlib import Path

scenes = [
    {"name": "cafe", "location": "cozy cafe by window", "garment": "cream knit cardigan",
     "pose": "resting chin on hand", "expression": "warm smile at viewer",
     "lighting": "golden afternoon light", "composition": "medium shot"},
]
results = generate_session(scenes, Path.home() / ".workbuddy/identity-studio/sessions/2026-04-07-cafe")
```
