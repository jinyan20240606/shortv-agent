# Content Safety Guide — MiniMax image-01

Reference for image generation API content audit rules.

## Banned Keywords (Trigger Rejection)

| Keyword | Note |
|---------|------|
| bikini / swimsuit / swimwear | Direct rejection |
| lingerie / underwear / bra | Direct rejection |
| naked / nude / topless | Direct rejection |
| sexy body / busty / voluptuous | Combination trigger |

## Outfit Safety Levels

### 🟢 SAFE — High Pass Rate
| Outfit | Style | Experience |
|--------|-------|-----------|
| White floral dress | Cute | ✅ 100% |
| Straw hat + sun dress | Casual | ✅ 100% |
| Linen shirt + shorts | Casual | ✅ 100% |
| Navy blue suit | Professional | ✅ 100% |
| White off-shoulder gown + side slit | Elegant | ✅ Passed |
| Red V-back evening gown | Glamorous | ✅ Passed |
| Silk robe | Intimate | ✅ Passed |

### 🟡 CAUTION — Needs Careful Wording
| Outfit | Note |
|--------|------|
| Off-shoulder dress | Avoid emphasizing body curves |
| Deep V design | Modify with "elegant" "couture" |
| Wet effect | Add "artistic" "tasteful" keywords |

### 🔴 REJECTED — Confirmed Failures
| Outfit | Reason |
|--------|--------|
| Any bikini variant | Sexy content |
| One-piece swimsuit | Sexy content |
| Any swimwear | Sexy content |

## Prompt Technique: "Describe Clothing, Not Body"

### Safe Modifier Keywords
- `artistic` / `tasteful` — converts sensual to artistic
- `cinematic` — filmic composition
- `elegant` / `sophisticated` — high-end feel
- `editorial` — fashion photography style

### Atmosphere Words (Shift Focus)
- `moonlight` / `golden hour` / `bokeh`
- `atmospheric lighting` / `lens flare`

## Body Description Safety

| Want | ✅ Safe | ❌ Dangerous |
|------|--------|------------|
| Curves | form-fitting dress that hugs her curves | curvy body |
| Neckline | V-neck dress with elegant draping | showing bust |
| Legs | showing shapely legs | long sexy legs |
| Collarbone | delicate collarbone showing | Direct OK |
