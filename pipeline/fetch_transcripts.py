from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound
)

import json
import random
import time
from pathlib import Path

# =========================
# BASE PATHS (Pi-safe)
# =========================

BASE_DIR = Path(__file__).parent

TRANSCRIPTS_DIR = BASE_DIR / "transcripts" / "hindi"
FAILURES_PATH = BASE_DIR / "transcripts" / "transcript_failures.json"

TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# HELPERS
# =========================

def get_page_name(video_id, declared_ekantik_number):
    if declared_ekantik_number is not None:
        return f"ekantik_{declared_ekantik_number}.json"
    return f"video_{video_id}.json"


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_hindi_transcript(video_id):
    return YouTubeTranscriptApi().fetch(video_id, languages=["hi"])


def build_page(video_id, declared_ekantik_number, snippets):
    return {
        "video_id": video_id,
        "declared_ekantik_number": declared_ekantik_number,
        "language": "hi",
        "snippets": [
            {
                "index": i + 1,
                "text": s.text,
                "start": s.start,
                "duration": s.duration,
            }
            for i, s in enumerate(snippets)
        ],
    }

# =========================
# CORE
# =========================

def process_video(entry, failures):
    video_id = entry["video_id"]
    ekantik_no = entry.get("declared_ekantik_number")

    page_name = get_page_name(video_id, ekantik_no)
    output_path = TRANSCRIPTS_DIR / page_name

    if output_path.exists():
        print(f"already processed {page_name}", flush=True)
        return

    try:
        snippets = fetch_hindi_transcript(video_id)
        page = build_page(video_id, ekantik_no, snippets)
        save_json(output_path, page)
        print(f"saved {page_name}", flush=True)
        # ⏳ Human-like delay: 30–50 minutes
        sleep_seconds = random.uniform(120, 360)
        sleep_minutes = sleep_seconds / 60
        print(f"sleeping for {sleep_minutes:.1f} minutes...\n", flush=True)
        time.sleep(sleep_seconds)

    except (TranscriptsDisabled, NoTranscriptFound):
        failures.append({
            "video_id": video_id,
            "declared_ekantik_number": ekantik_no,
            "reason": "Hindi transcript not available"
        })
        print(f"failed {page_name}", flush=True)

# =========================
# DRIVER
# =========================

def generate_transcripts(video_meta_data):
    failures = []

    for entry in video_meta_data:
        process_video(entry, failures)


    save_json(FAILURES_PATH, failures)
if __name__ == "__main__":
    print("[START] Phase-2 transcript fetcher", flush=True)

    with open(BASE_DIR / "ekantik_videos_v1.json", "r", encoding="utf-8") as f:
        video_meta_data = json.load(f)

    generate_transcripts(video_meta_data)

    print("[DONE] Phase-2 run complete", flush=True)
