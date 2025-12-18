import argparse
import json
import os
from datetime import datetime

import yaml

from src.ingest_news import rss_ingest
from src.script_builder_llm import builder as script_builder
from src.tts import synthesizer
from src.avatar.heygen_client import HeygenClient
from src.visual_template import template as visual_template
from src.video_composer import composer


def load_yaml(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    args = parse_args()
    base_cfg = load_yaml("configs/base.yaml")
    sources_cfg = load_yaml(args.sources)
    tts_cfg = load_yaml("configs/tts.yaml")
    template_cfg = load_yaml("configs/template.yaml")
    export_cfg = load_yaml("configs/export.yaml")
    export_cfg["duration_seconds"] = base_cfg["video"]["duration_seconds"]

    date_tag = args.date or datetime.utcnow().strftime("%Y-%m-%d")
    outputs_root = base_cfg["paths"]["outputs_root"]

    # Step 1: ingest RSS
    news_log = os.path.join(outputs_root, "logs", f"news_{date_tag}.json")
    news_items = rss_ingest.fetch_and_normalize(
        sources_cfg["sources"],
        include_keywords=sources_cfg["filters"]["keywords_include"],
        exclude_keywords=sources_cfg["filters"]["keywords_exclude"],
        log_path=news_log,
    )
    if args.use_sample or not news_items:
        with open("data/sample_news.json", "r", encoding="utf-8") as f:
            news_items = json.load(f)
    print(f"[ingest] collected {len(news_items)} items -> {news_log}")

    # Step 2: script via LLM
    script_log = os.path.join(outputs_root, "logs", f"script_llm_{date_tag}.json")
    script_payload = script_builder.build_script(news_items, base_cfg, script_log)
    script_path = os.path.join(outputs_root, "scripts", f"script_{date_tag}.json")
    os.makedirs(os.path.dirname(script_path), exist_ok=True)
    with open(script_path, "w", encoding="utf-8") as f:
        json.dump(script_payload, f, ensure_ascii=False, indent=2)
    print(f"[script] saved script to {script_path}")

    # Step 3: HeyGen avatar video (with built-in voice) OR local TTS
    avatar_cfg = template_cfg.get("avatar", {})
    provider = avatar_cfg.get("provider", "static")
    audio_path = os.path.join(outputs_root, "audio", f"voice_{date_tag}.mp3")
    avatar_video_path = avatar_cfg.get("video_path", "")

    if provider == "heygen" and not args.dry_run:
        try:
            client = HeygenClient()
            aspect = export_cfg.get("format", "16:9") if "format" in export_cfg else "16:9"
            video_id = client.generate_video_from_text(
                avatar_cfg["avatar_id"],
                avatar_cfg["voice_id"],
                script_payload["script_text"],
                aspect_ratio=aspect,
                test=args.heygen_test,
            )
            task = client.poll_video(video_id)
            avatar_video_path = os.path.join(outputs_root, "video", f"avatar_heygen_{date_tag}.mp4")
            client.download_video(task["video_url"], avatar_video_path)
            template_cfg["avatar"]["video_path"] = avatar_video_path
            print(f"[heygen] video ready -> {avatar_video_path}")
            if avatar_cfg.get("use_heygen_audio", True):
                audio_path = ""
        except Exception as e:
            print(f"[heygen] failed, fallback to TTS: {e}")

    # Step 4: TTS (skip if HeyGen audio is used)
    tts_log = os.path.join(outputs_root, "logs", f"tts_{date_tag}.json")
    if audio_path and not args.dry_run:
        synthesizer.synthesize(script_payload["script_text"], tts_cfg, audio_path, tts_log)
        print(f"[tts] audio -> {audio_path}")

    # Step 5: visuals
    visuals = visual_template.prepare_visuals(template_cfg, outputs_root)
    print(f"[visuals] background: {visuals['background_path']}")

    # Step 6: compose video
    video_out = args.out or os.path.join(outputs_root, "video", f"video_{date_tag}.mp4")
    if not args.dry_run:
        composer.compose_video(
            visuals["background_path"],
            visuals.get("avatar_video", template_cfg["avatar"].get("video_path", "")),
            visuals.get("avatar_photo", ""),
            script_payload["segments"],
            audio_path,
            export_cfg,
            template_cfg,
            video_out,
        )
    print(f"[video] saved to {video_out}")


def parse_args():
    parser = argparse.ArgumentParser(description="Generate Russian news video.")
    parser.add_argument("--date", type=str, help="Дата выпуска YYYY-MM-DD")
    parser.add_argument("--sources", type=str, default="configs/sources.yaml", help="Путь к источникам RSS")
    parser.add_argument("--out", type=str, help="Итоговый путь к mp4")
    parser.add_argument("--dry-run", action="store_true", help="Не вызывать TTS и композит")
    parser.add_argument("--use-sample", action="store_true", help="Использовать sample_news.json вместо RSS")
    parser.add_argument("--heygen-test", action="store_true", help="HeyGen test mode flag")
    return parser.parse_args()


if __name__ == "__main__":
    main()
