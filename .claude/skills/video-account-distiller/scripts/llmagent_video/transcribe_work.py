# coding=utf-8
import argparse
import json
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dy_apis.douyin_api import DouyinAPI
from builder.header import HeaderBuilder
from fetch_single_work import handle_work_info, save_json, save_raw_json
from url_util import normalize_douyin_url
from utils.common_util import init


def parse_args():
    parser = argparse.ArgumentParser(description="Download one Douyin work and transcribe its speech.")
    parser.add_argument("url", help="Douyin work URL.")
    parser.add_argument(
        "--model",
        default="small",
        help="faster-whisper model size or local model path. Default: small",
    )
    parser.add_argument(
        "--device",
        default="cpu",
        choices=["cpu", "cuda"],
        help="Run device. Default: cpu",
    )
    parser.add_argument(
        "--output-dir",
        default=os.path.join(os.path.dirname(__file__), "outputs", "transcripts"),
        help="Directory used to save video and transcript.",
    )
    return parser.parse_args()


def load_whisper_model(model_name, device):
    try:
        from faster_whisper import WhisperModel
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Missing dependency: faster-whisper. Install it with: python -m pip install faster-whisper"
        ) from exc

    compute_type = "int8" if device == "cpu" else "float16"
    return WhisperModel(model_name, device=device, compute_type=compute_type)


def transcribe_video(video_path, model_name, device):
    model = load_whisper_model(model_name, device)
    segments, info = model.transcribe(
        video_path,
        language="zh",
        vad_filter=True,
        beam_size=5,
    )

    result_segments = []
    texts = []
    for segment in segments:
        item = {
            "start": round(segment.start, 2),
            "end": round(segment.end, 2),
            "text": segment.text.strip(),
        }
        if item["text"]:
            result_segments.append(item)
            texts.append(item["text"])

    return {
        "language": info.language,
        "language_probability": info.language_probability,
        "text": "\n".join(texts),
        "segments": result_segments,
    }


def save_transcript(output_dir, work_id, transcript):
    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.abspath(os.path.join(output_dir, f"{work_id}.transcript.json"))
    txt_path = os.path.abspath(os.path.join(output_dir, f"{work_id}.transcript.txt"))

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(transcript, f, ensure_ascii=False, indent=2)
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(transcript["text"])

    return json_path, txt_path


def download_video(url, path, auth, referer):
    import requests

    headers = {
        "User-Agent": HeaderBuilder.ua,
        "Referer": referer or "https://www.douyin.com/",
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Range": "bytes=0-",
    }
    cookies = auth.cookie if auth is not None else None
    with requests.get(url, headers=headers, cookies=cookies, stream=True, timeout=60) as response:
        response.raise_for_status()
        with open(path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


def main():
    args = parse_args()
    auth, _ = init()

    response = DouyinAPI().get_work_info(auth, normalize_douyin_url(args.url))
    if "aweme_detail" not in response or not response["aweme_detail"]:
        print("Fetch failed: response has no aweme_detail.")
        print(json.dumps(response, ensure_ascii=False, indent=2))
        return 1

    work_info = handle_work_info(response["aweme_detail"])
    if work_info["work_type"] != "video" or not work_info["video_addr"]:
        print("This work has no downloadable video address.")
        return 1

    os.makedirs(args.output_dir, exist_ok=True)
    work_id = work_info["work_id"]
    video_path = os.path.abspath(os.path.join(args.output_dir, f"{work_id}.mp4"))

    save_json(work_info, args.output_dir)
    save_raw_json(response, args.output_dir, work_id)
    print(f"Downloading video: {video_path}")
    download_video(work_info["video_addr"], video_path, auth, work_info["work_url"])

    print(f"Transcribing with faster-whisper model={args.model}, device={args.device}")
    try:
        transcript = transcribe_video(video_path, args.model, args.device)
    except RuntimeError as exc:
        print(str(exc))
        return 1

    json_path, txt_path = save_transcript(args.output_dir, work_id, transcript)
    print("Transcribe success")
    print(f"text: {txt_path}")
    print(f"json: {json_path}")
    print("")
    print(transcript["text"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
