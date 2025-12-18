import json
import os
from typing import Dict

from gtts import gTTS


def synthesize(text: str, config: Dict, output_path: str, log_path: str) -> str:
    # сохраняем в mp3, чтобы избежать зависимости от audioop/pyaudioop
    if not output_path.lower().endswith(".mp3"):
        root, _ = os.path.splitext(output_path)
        output_path = root + ".mp3"

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    language = config.get("language", "ru")

    # gTTS справляется с умеренным текстом; при больших сценариях можно резать вручную
    tts_obj = gTTS(text, lang=language, slow=False)
    tts_obj.save(output_path)

    meta = {
        "provider": config.get("provider"),
        "language": language,
        "text_char_len": len(text),
    }
    if log_path and config.get("log_params", True):
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    return output_path
