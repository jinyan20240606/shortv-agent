#!/usr/bin/env python3
"""
Agent Identity Studio — gen.py
AI character image generation engine with Character Sheet + Scene Card architecture.

Maintains visual consistency across unlimited scenes by separating
"who the character is" (fixed) from "what's happening" (variable).

Usage:
    # CLI — Generate character proof images
    python gen.py proofs -o ./output_dir

    # CLI — Generate from a single scene JSON
    python gen.py scene -s '{"name":"cafe","location":"cozy cafe","garment":"white sweater","expression":"warm smile","composition":"medium shot"}' -o ./output.png

    # CLI — Generate a complete session
    python gen.py session -s scenes.json -o ./session_dir

    # Python module
    from gen import CharacterSheet, SceneCard, Engine, generate, generate_session
"""

import os
import sys
import json
import time
import base64
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List

# ── Paths ──────────────────────────────────────────────
# Data root: ~/.workbuddy/identity-studio/
DATA_ROOT = Path.home() / ".workbuddy" / "identity-studio"
CHARACTER_SHEET_PATH = DATA_ROOT / "character-sheet.yaml"

# Reference images for subject_reference (dual-ref strategy)
# Local paths (preferred — uses data:image URI, no public URL needed)
DEFAULT_REF_LOCAL_FRONT = DATA_ROOT / "reference" / "ref-front.png"
DEFAULT_REF_LOCAL_SIDE = DATA_ROOT / "reference" / "ref-side.png"
# Fallback URLs (if local files not found, set per-character)
DEFAULT_REF_URL_FRONT = ""
DEFAULT_REF_URL_SIDE = ""

# ── API Config ─────────────────────────────────────────
# Dual engine: MiniMax (default) + Hunyuan (腾讯混元)
# Set IDENTITY_STUDIO_ENGINE env var to switch: "minimax" (default) or "hunyuan"
ENGINE_CHOICE = os.environ.get("IDENTITY_STUDIO_ENGINE", "minimax").lower()

# MiniMax config
MINIMAX_API_URL = "https://api.minimaxi.com/v1/image_generation"
MINIMAX_MODEL = "image-01"
MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY", "")
MINIMAX_COST = 0.025  # CNY per image

# Hunyuan config (腾讯混元生图 3.0, via Tencent Cloud SDK)
# Uses SecretId + SecretKey (CAM credentials), NOT the sk- API key
HUNYUAN_SECRET_ID = os.environ.get("TENCENT_SECRET_ID", "")
HUNYUAN_SECRET_KEY = os.environ.get("TENCENT_SECRET_KEY", "")
HUNYUAN_REGION = "ap-guangzhou"
HUNYUAN_COST = 0.20  # CNY per image
HUNYUAN_POLL_INTERVAL = 2  # seconds between status checks
HUNYUAN_MAX_POLL = 60  # max poll attempts (~120s timeout)


# =====================================================
# Layer 0 — Engine (API / Audit / Retry)
# =====================================================

BANNED_KEYWORDS = [
    "bikini", "swimsuit", "swimwear", "lingerie", "underwear", "bra",
    "backless", "spaghetti strap", "naked", "nude", "topless",
    "sexy body", "showing body", "busty", "voluptuous",
    "bust", "chest", "hips", "hourglass",
]


@dataclass
class GenerationResult:
    """Result of a single image generation."""
    success: bool
    image_path: Optional[Path] = None
    prompt_used: str = ""
    error: str = ""
    retry_count: int = 0
    elapsed_seconds: float = 0.0


class Engine:
    """Layer 0: API calling, audit handling, retry logic.

    Supports two backends:
    - MiniMax image-01 (default): synchronous, returns URL
    - Hunyuan 3.0 (腾讯混元): async submit+poll, supports up to 3 reference images

    Uses urllib (stdlib only) — no external dependencies required.
    """

    def __init__(self, backend: str = None, api_key: str = None,
                 ref_url_front: str = None, ref_url_side: str = None,
                 ref_local_front: Path = None, ref_local_side: Path = None):
        self.backend = (backend or ENGINE_CHOICE).lower()
        self.ref_url_front = ref_url_front or DEFAULT_REF_URL_FRONT
        self.ref_url_side = ref_url_side or DEFAULT_REF_URL_SIDE
        self.ref_local_front = ref_local_front or DEFAULT_REF_LOCAL_FRONT
        self.ref_local_side = ref_local_side or DEFAULT_REF_LOCAL_SIDE

        if self.backend == "hunyuan":
            if not HUNYUAN_SECRET_ID or not HUNYUAN_SECRET_KEY:
                raise ValueError("TENCENT_SECRET_ID / TENCENT_SECRET_KEY not set. "
                                 "Get them from: https://console.cloud.tencent.com/cam/capi")
            try:
                from tencentcloud.common import credential
                from tencentcloud.common.profile.client_profile import ClientProfile
                from tencentcloud.common.profile.http_profile import HttpProfile
                from tencentcloud.aiart.v20221229 import aiart_client
                cred = credential.Credential(HUNYUAN_SECRET_ID, HUNYUAN_SECRET_KEY)
                hp = HttpProfile()
                hp.endpoint = "aiart.tencentcloudapi.com"
                hp.reqTimeout = 120
                cp = ClientProfile()
                cp.httpProfile = hp
                self._hunyuan_client = aiart_client.AiartClient(cred, HUNYUAN_REGION, cp)
                print(f"  [ENGINE] Hunyuan 3.0 (Tencent Cloud SDK)")
            except ImportError:
                raise ImportError("tencentcloud-sdk-python-aiart not installed. "
                                  "Run: pip install tencentcloud-sdk-python-aiart")
        else:
            self.backend = "minimax"
            self.api_key = api_key or MINIMAX_API_KEY
            if not self.api_key:
                raise ValueError("MINIMAX_API_KEY not set. Set it as environment variable.")
            print(f"  [ENGINE] MiniMax ({MINIMAX_MODEL})")

    @staticmethod
    def _to_data_uri(image_path: Path) -> Optional[str]:
        """Convert local image to data:image URI for subject_reference image_file field.
        MiniMax accepts data: URIs in the image_file field (NOT image_base64)."""
        if not image_path or not image_path.exists():
            return None
        raw = image_path.read_bytes()
        b64 = base64.b64encode(raw).decode("utf-8")
        ext = image_path.suffix.lower()
        mime = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"
        return f"data:{mime};base64,{b64}"

    def check_prompt_safety(self, prompt: str) -> list:
        """Check prompt for banned keywords using word-boundary matching."""
        import re
        prompt_lower = prompt.lower()
        return [kw for kw in BANNED_KEYWORDS if re.search(r'\b' + re.escape(kw) + r'\b', prompt_lower)]

    def _api_call(self, payload: dict) -> dict:
        """Make API call — dispatches to correct backend."""
        if self.backend == "hunyuan":
            return self._hunyuan_call(payload)
        return self._minimax_call(payload)

    def _minimax_call(self, payload: dict) -> dict:
        """MiniMax: synchronous call, returns image URLs directly."""
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            MINIMAX_API_URL,
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read())

    def _hunyuan_call(self, payload: dict) -> dict:
        """Hunyuan 3.0: async submit + poll via Tencent Cloud SDK.

        Uses SubmitTextToImageJob → QueryTextToImageJob.
        Translates result to MiniMax-compatible format for uniform handling.
        """
        from tencentcloud.aiart.v20221229 import models as aiart_models

        # Build submit request
        submit_req = aiart_models.SubmitTextToImageJobRequest()
        submit_params = {
            "Prompt": payload.get("prompt", ""),
            "LogoAdd": 0,
            "Revise": 0,
        }
        # Map aspect_ratio to Resolution
        ar = payload.get("aspect_ratio", "3:4")
        res_map = {
            "1:1": "1024:1024", "3:4": "768:1024", "4:3": "1024:768",
            "9:16": "576:1024", "16:9": "1024:576",
        }
        submit_params["Resolution"] = res_map.get(ar, "1024:1024")

        # Add reference images if available (Hunyuan supports up to 3)
        ref_images = payload.get("_hunyuan_images", [])
        if ref_images:
            submit_params["Images"] = ref_images

        submit_req.from_json_string(json.dumps(submit_params))

        # Submit
        resp = self._hunyuan_client.SubmitTextToImageJob(submit_req)
        result = json.loads(resp.to_json_string())
        job_id = result.get("JobId")
        if not job_id:
            return {"base_resp": {"status_code": -1, "status_msg": f"No JobId: {result}"}}

        print(f"  [HUNYUAN] Job submitted: {job_id[:30]}...")

        # Poll for result
        for poll in range(HUNYUAN_MAX_POLL):
            time.sleep(HUNYUAN_POLL_INTERVAL)
            query_req = aiart_models.QueryTextToImageJobRequest()
            query_req.from_json_string(json.dumps({"JobId": job_id}))
            qresp = self._hunyuan_client.QueryTextToImageJob(query_req)
            qresult = json.loads(qresp.to_json_string())

            status = str(qresult.get("JobStatusCode", "0"))
            elapsed_poll = (poll + 1) * HUNYUAN_POLL_INTERVAL
            if status == "5":  # Success
                img = qresult.get("ResultImage", "")
                urls = [img] if isinstance(img, str) and img else img if isinstance(img, list) else []
                print(f"  [HUNYUAN] Done after ~{elapsed_poll}s")
                return {
                    "base_resp": {"status_code": 0},
                    "data": {"image_urls": urls},
                }
            elif status in ("3", "4"):  # Failed / Audit rejected
                msg = qresult.get("JobStatusMsg", "Generation failed")
                code = 1033 if "audit" in msg.lower() or "sensitive" in msg.lower() else -1
                return {"base_resp": {"status_code": code, "status_msg": msg}}

        return {"base_resp": {"status_code": -1, "status_msg": "Hunyuan timeout after polling"}}

    def _download_image(self, url: str, path: Path):
        """Download image from URL to local path."""
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=60) as resp:
            path.write_bytes(resp.read())

    def _resolve_ref(self, composition_type: str) -> Optional[tuple]:
        """Resolve the best available reference image for the given composition.

        Returns (image_file_value, label) or None if no ref available.
        Priority: local data URI > remote URL.
        """
        if composition_type == "full_body":
            # Side ref for body lock
            data_uri = self._to_data_uri(self.ref_local_side)
            if data_uri:
                return data_uri, "side local (body lock)"
            if self.ref_url_side:
                return self.ref_url_side, "side URL (body lock)"
        # Default: front ref for face lock
        data_uri = self._to_data_uri(self.ref_local_front)
        if data_uri:
            return data_uri, "front local (face lock)"
        if self.ref_url_front:
            return self.ref_url_front, "front URL (face lock)"
        return None

    def generate(
        self,
        prompt: str,
        output_path: Path,
        aspect_ratio: str = "3:4",
        use_ref: bool = True,
        composition_type: str = "medium",
        max_retries: int = 2,
    ) -> GenerationResult:
        """Generate a single image. Dispatches to MiniMax or Hunyuan backend.

        Both backends share the same payload structure; backend-specific fields
        are injected here. Response format is normalized by _api_call().
        """
        # Pre-check for banned words
        banned = self.check_prompt_safety(prompt)
        if banned:
            print(f"  [WARN] Removing banned keywords: {banned}")
            for kw in banned:
                prompt = prompt.replace(kw, "")

        payload = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
        }

        # Backend-specific payload setup
        if self.backend == "minimax":
            payload["model"] = MINIMAX_MODEL
            payload["response_format"] = "url"
            payload["n"] = 1

        # Add reference images
        if use_ref:
            ref_resolved = self._resolve_ref(composition_type)
            if ref_resolved:
                ref_value, ref_label = ref_resolved
                if self.backend == "minimax":
                    # MiniMax: subject_reference with image_file (URL or data:URI)
                    payload["subject_reference"] = [{
                        "type": "character",
                        "image_file": ref_value,
                    }]
                elif self.backend == "hunyuan":
                    # Hunyuan: Images array (supports URL or base64, up to 3)
                    payload["_hunyuan_images"] = [ref_value]
                is_data_uri = ref_value.startswith("data:")
                print(f"  [REF] {ref_label} ({'data URI' if is_data_uri else 'URL'})")
            else:
                print(f"  [REF] No reference image available, generating without ref")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        start = time.time()
        last_error = ""
        tried_without_ref = False

        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    print(f"  [RETRY {attempt}/{max_retries}] Toning down prompt...")
                    payload["prompt"] = self._tone_down(payload["prompt"])

                print(f"  [API] Calling MiniMax (attempt {attempt + 1})...")
                result = self._api_call(payload)

                base_resp = result.get("base_resp") or {}
                data_resp = result.get("data") or {}
                status = base_resp.get("status_code", -1)

                if status == 0:
                    urls = data_resp.get("image_urls", [])
                    if urls:
                        self._download_image(urls[0], output_path)
                        elapsed = time.time() - start
                        meta = result.get("metadata", {})
                        print(f"  [OK] {output_path.name} ({elapsed:.1f}s) audit_fail={meta.get('failed_count', '0')}")
                        return GenerationResult(
                            success=True,
                            image_path=output_path,
                            prompt_used=payload["prompt"],
                            retry_count=attempt,
                            elapsed_seconds=elapsed,
                        )
                    else:
                        last_error = "API returned success but no image_urls"
                        print(f"  [ERROR] {last_error}")
                        break

                elif status in (1033, 1026):
                    last_error = f"Content audit rejection ({status}): {base_resp.get('status_msg', '')}"
                    print(f"  [AUDIT] {last_error}")
                    continue

                elif status == 1000 and not tried_without_ref and "subject_reference" in payload:
                    print(f"  [WARN] Unknown error with ref, retrying without subject_reference...")
                    del payload["subject_reference"]
                    tried_without_ref = True
                    continue

                elif status == 1008:
                    last_error = "Insufficient balance (1008)"
                    print(f"  [ERROR] {last_error}")
                    break

                else:
                    last_error = f"API error {status}: {base_resp.get('status_msg', '')}"
                    print(f"  [ERROR] {last_error}")
                    if status == 1000:
                        continue
                    break

            except urllib.error.URLError as e:
                last_error = f"Network error: {e}"
                print(f"  [NETWORK] {last_error}")
                continue
            except Exception as e:
                last_error = str(e)
                print(f"  [EXCEPTION] {last_error}")
                break

        elapsed = time.time() - start
        return GenerationResult(
            success=False,
            prompt_used=payload.get("prompt", prompt),
            error=last_error,
            retry_count=max_retries,
            elapsed_seconds=elapsed,
        )

    def _tone_down(self, prompt: str) -> str:
        """Tone down a prompt after audit rejection."""
        risky_extras = [
            "seductive", "alluring", "provocative", "sultry",
            "revealing", "exposed", "bare", "skin-tight",
            "deep V-neck", "plunging", "low-cut",
        ]
        for word in risky_extras:
            prompt = prompt.replace(word, "elegant")
        if "cinematic" not in prompt.lower():
            prompt += ", cinematic artistic style"
        if "tasteful" not in prompt.lower():
            prompt += ", tasteful"
        return prompt


# =====================================================
# Layer 1 — Character Sheet (Fixed identity: "who is she/he")
# =====================================================

@dataclass
class CharacterSheet:
    """
    Character identity definition.
    Loaded from character-sheet.yaml or uses built-in defaults.
    Renders to a fixed prompt segment that never changes across scenes.

    Default values are a demo character. Replace with your own via YAML.
    """

    # Core identity
    name: str = "Default"
    age_impression: str = "young woman, early 20s"

    # Face
    eyes: str = "bright expressive eyes"
    skin: str = "fair skin with a healthy glow"

    # Hair
    hair_color: str = "long flowing hair"
    hair_style: str = "naturally flowing"
    signature_accessory: str = ""

    # Body — tiered system
    half_body_type: str = "healthy well-proportioned feminine figure"
    half_body_curve: str = "form-fitting {garment} that flatters her frame"
    full_body_type: str = "healthy well-proportioned feminine figure"
    full_body_curve: str = "form-fitting {garment} that flatters her frame"
    full_body_legs: str = "natural legs"
    full_body_stance: str = "natural graceful posture"
    loose_outfit_boost: str = "figure visible beneath clothing"

    # Personality
    core_vibe: str = "confident"
    default_expression: str = "a gentle smile looking at the viewer"

    # Art style
    art_base: str = "anime art style"
    quality: str = "high quality, detailed, beautiful lighting"
    maturity_suffix: str = "elegant style"

    @classmethod
    def load(cls, path: Path = None) -> "CharacterSheet":
        """Load from YAML file. Falls back to defaults if file missing or parse error."""
        path = path or CHARACTER_SHEET_PATH
        if not path.exists():
            print(f"  [INFO] No character sheet at {path}, using defaults")
            return cls()
        try:
            return cls._parse_yaml(path)
        except Exception as e:
            print(f"  [WARN] Failed to parse {path}: {e}")
            print(f"  [WARN] Using built-in defaults instead")
            return cls()

    @classmethod
    def _parse_yaml(cls, path: Path) -> "CharacterSheet":
        """Robust YAML parser — handles nested key:value without pyyaml dependency.

        Strategy: build flat key map from indentation-based nesting.
        Supports up to 3 levels (e.g. body.full_body.base_type).
        """
        text = path.read_text(encoding="utf-8")
        data = {}
        section_stack = []

        for line in text.split("\n"):
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("---"):
                continue

            indent = len(line) - len(line.lstrip())

            while section_stack and section_stack[-1][0] >= indent:
                section_stack.pop()

            if ":" in stripped:
                key_part, _, val_part = stripped.partition(":")
                key_part = key_part.strip()
                val_part = val_part.strip()

                if not val_part:
                    section_stack.append((indent, key_part))
                    continue

                val_clean = val_part.strip('"').strip("'")
                if val_clean.startswith("{") or val_clean.startswith("["):
                    continue

                parents = ".".join(s[1] for s in section_stack)
                full_key = f"{parents}.{key_part}" if parents else key_part
                data[full_key] = val_clean

        sheet = cls()
        field_map = {
            "identity.name": "name",
            "identity.age_impression": "age_impression",
            "face.eyes": "eyes",
            "face.skin": "skin",
            "hair.color": "hair_color",
            "hair.style": "hair_style",
            "hair.signature_accessory": "signature_accessory",
            "body.half_body.base_type": "half_body_type",
            "body.half_body.curve_template": "half_body_curve",
            "body.full_body.base_type": "full_body_type",
            "body.full_body.curve_template": "full_body_curve",
            "body.full_body.legs_template": "full_body_legs",
            "body.full_body.stance_template": "full_body_stance",
            "body.loose_outfit_boost": "loose_outfit_boost",
            "personality.core_vibe": "core_vibe",
            "personality.default_expression": "default_expression",
            "art_style.base": "art_base",
            "art_style.quality": "quality",
            "art_style.maturity_suffix": "maturity_suffix",
        }

        matched = 0
        for yaml_key, attr_name in field_map.items():
            if yaml_key in data:
                setattr(sheet, attr_name, data[yaml_key])
                matched += 1

        print(f"  [INFO] Loaded character sheet: {matched}/{len(field_map)} fields matched from {path.name}")
        return sheet

    LOOSE_KEYWORDS = [
        "oversized", "loose", "wide", "baggy", "oversize",
        "boyfriend", "relaxed fit", "flowy", "boxy",
    ]

    def _is_loose_outfit(self, garment: str) -> bool:
        if not garment:
            return False
        return any(kw in garment.lower() for kw in self.LOOSE_KEYWORDS)

    def render(self, composition: str = "portrait", garment: str = None) -> str:
        """Render character identity into a prompt segment.

        Uses tiered body description:
        - portrait/close-up: no body description
        - medium shot: half_body basic
        - full body: full_body enhanced + legs + stance
        - loose outfit: auto-inject boost
        """
        parts = [
            "beautiful mature anime girl",
            f"with {self.hair_color}",
            self.eyes,
            self.signature_accessory,
            self.skin,
        ]

        is_loose = self._is_loose_outfit(garment) if garment else False

        if composition == "full_body":
            parts.append(self.full_body_type)
            if garment:
                parts.append(self.full_body_curve.format(garment=garment))
            parts.append(self.full_body_legs)
            parts.append(self.full_body_stance)
            if is_loose:
                parts.append(self.loose_outfit_boost)
        elif composition == "medium":
            parts.append(self.half_body_type)
            if garment:
                parts.append(self.half_body_curve.format(garment=garment))
            if is_loose:
                parts.append(self.loose_outfit_boost)

        parts.extend([self.art_base, self.quality, self.maturity_suffix])
        return ", ".join(parts)


# =====================================================
# Layer 2 — Scene Card
# =====================================================

@dataclass
class SceneCard:
    """Defines 'what is happening right now'. MUST NOT contain identity traits."""

    name: str = ""
    location: str = ""
    time_of_day: str = ""
    atmosphere: str = ""
    garment: str = ""
    accessories: str = ""
    pose: str = ""
    expression_override: str = ""
    lighting: str = "cinematic warm lighting"
    composition: str = "medium shot"
    aspect_ratio: str = "3:4"

    @classmethod
    def from_dict(cls, d: dict) -> "SceneCard":
        return cls(
            name=d.get("name", ""),
            location=d.get("location", ""),
            time_of_day=d.get("time_of_day", d.get("time", "")),
            atmosphere=d.get("atmosphere", ""),
            garment=d.get("garment", d.get("outfit", "")),
            accessories=d.get("accessories", ""),
            pose=d.get("pose", ""),
            expression_override=d.get("expression", d.get("expression_override", "")),
            lighting=d.get("lighting", "cinematic warm lighting"),
            composition=d.get("composition", "medium shot"),
            aspect_ratio=d.get("aspect_ratio", "3:4"),
        )

    @property
    def composition_type(self) -> str:
        comp = self.composition.lower()
        if "full body" in comp or "full-body" in comp:
            return "full_body"
        elif "close" in comp or "portrait" in comp or "head" in comp:
            return "portrait"
        return "medium"

    def render(self) -> str:
        parts = []
        if self.garment:
            parts.append(f"wearing {self.garment}")
        if self.accessories:
            parts.append(self.accessories)
        if self.pose:
            parts.append(self.pose)
        if self.location:
            parts.append(self.location)
        if self.time_of_day:
            parts.append(self.time_of_day)
        if self.atmosphere:
            parts.append(self.atmosphere)
        if self.lighting:
            parts.append(self.lighting)
        if self.composition:
            parts.append(self.composition)
        return ", ".join(parts)

    def get_expression(self, default: str) -> str:
        return self.expression_override or default


# =====================================================
# Prompt Assembly
# =====================================================

def assemble_prompt(sheet: CharacterSheet, scene: SceneCard) -> str:
    """Assemble final prompt: character(fixed) + expression + scene(variable)."""
    char_prompt = sheet.render(composition=scene.composition_type, garment=scene.garment)
    expression = scene.get_expression(sheet.default_expression)
    scene_prompt = scene.render()
    return f"{char_prompt}. {expression}. {scene_prompt}"


# =====================================================
# High-Level Generation Functions
# =====================================================

def generate(
    scene: SceneCard,
    output_path: Path,
    sheet: CharacterSheet = None,
    engine: Engine = None,
) -> GenerationResult:
    """Generate a single photo from a scene card."""
    sheet = sheet or CharacterSheet.load()
    engine = engine or Engine()
    prompt = assemble_prompt(sheet, scene)

    print(f"\n{'='*60}")
    print(f"  Scene: {scene.name}")
    print(f"  Composition: {scene.composition} ({scene.composition_type})")
    print(f"  Prompt ({len(prompt)} chars): {prompt[:150]}...")
    print(f"{'='*60}")

    return engine.generate(
        prompt=prompt,
        output_path=output_path,
        aspect_ratio=scene.aspect_ratio,
        composition_type=scene.composition_type,
    )


def generate_character_proofs(
    output_dir: Path,
    sheet: CharacterSheet = None,
    engine: Engine = None,
) -> list:
    """Generate 3 standard proof images for identity confirmation (Phase 1)."""
    sheet = sheet or CharacterSheet.load()
    engine = engine or Engine()

    proof_scenes = [
        SceneCard(
            name="Portrait - Front",
            location="simple clean light background",
            garment="white silk blouse",
            pose="facing the viewer directly, standing naturally",
            expression_override="a gentle confident smile, looking directly at the viewer",
            lighting="soft studio lighting, bright and clean",
            composition="portrait close-up",
            aspect_ratio="1:1",
        ),
        SceneCard(
            name="Portrait - 3/4 View",
            location="simple clean light background",
            garment="white silk blouse",
            pose="turned slightly to the side, 3/4 view, looking at the viewer",
            expression_override="a subtle knowing smile, eyes meeting the viewer",
            lighting="soft studio lighting with gentle shadows",
            composition="medium shot",
            aspect_ratio="3:4",
        ),
        SceneCard(
            name="Full Body - Standing",
            location="simple clean light background",
            garment="elegant white midi dress",
            pose="standing naturally, one hand lightly touching her hair",
            expression_override="composed confident expression, looking at the viewer",
            lighting="bright even studio lighting",
            composition="full body shot",
            aspect_ratio="3:4",
        ),
    ]

    filenames = ["portrait-front.png", "portrait-3quarter.png", "full-body.png"]
    results = []
    output_dir.mkdir(parents=True, exist_ok=True)

    for scene, filename in zip(proof_scenes, filenames):
        result = generate(scene=scene, output_path=output_dir / filename, sheet=sheet, engine=engine)
        results.append(result)
        print(f"  Result: {'OK' if result.success else 'FAIL'} {result.elapsed_seconds:.1f}s")

    return results


def generate_session(
    scenes: list,
    session_dir: Path,
    sheet: CharacterSheet = None,
    engine: Engine = None,
) -> list:
    """Generate a complete photo session from a list of scene dicts."""
    sheet = sheet or CharacterSheet.load()
    engine = engine or Engine()
    session_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for i, scene_dict in enumerate(scenes, 1):
        scene = SceneCard.from_dict(scene_dict)
        if not scene.name:
            scene.name = f"scene-{i:02d}"
        safe_name = scene.name.lower().replace(" ", "-").replace("/", "-")
        filename = f"{i:02d}-{safe_name}.png"

        print(f"\n[{i}/{len(scenes)}] Generating: {scene.name}")
        result = generate(scene=scene, output_path=session_dir / filename, sheet=sheet, engine=engine)
        results.append(result)

        ok = sum(1 for r in results if r.success)
        print(f"  Progress: {i}/{len(scenes)} | OK: {ok} | FAIL: {i - ok}")

    return results


# =====================================================
# CLI
# =====================================================

def main():
    parser = argparse.ArgumentParser(description="Agent Identity Studio — Character Image Generator")
    sub = parser.add_subparsers(dest="command")

    p1 = sub.add_parser("proofs", help="Generate character proof images")
    p1.add_argument("--output", "-o", type=str, default=str(DATA_ROOT / "reference"))

    p2 = sub.add_parser("scene", help="Generate from a single scene")
    p2.add_argument("--scene", "-s", type=str, required=True, help="Scene JSON string")
    p2.add_argument("--output", "-o", type=str, required=True, help="Output file path")

    p3 = sub.add_parser("session", help="Generate a complete session")
    p3.add_argument("--scenes", "-s", type=str, required=True, help="Scenes JSON array or file path")
    p3.add_argument("--output", "-o", type=str, required=True, help="Output directory")

    args = parser.parse_args()

    if args.command == "proofs":
        print("=== Generating Character Proof Images ===")
        results = generate_character_proofs(Path(args.output))
        ok = sum(1 for r in results if r.success)
        print(f"\nDone: {ok}/{len(results)} successful")

    elif args.command == "scene":
        print("=== Generating Single Scene ===")
        scene = SceneCard.from_dict(json.loads(args.scene))
        result = generate(scene=scene, output_path=Path(args.output))
        print(f"\nResult: {'OK' if result.success else 'FAIL'}")

    elif args.command == "session":
        print("=== Generating Photo Session ===")
        s = args.scenes
        scenes = json.loads(Path(s).read_text() if Path(s).is_file() else s)
        results = generate_session(scenes, Path(args.output))
        ok = sum(1 for r in results if r.success)
        print(f"\nDone: {ok}/{len(results)} successful")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
