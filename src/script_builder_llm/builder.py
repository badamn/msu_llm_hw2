import json
import os
from typing import Dict, List

from openai import OpenAI


def build_script(news_items: List[Dict], config: Dict, log_path: str) -> Dict:
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    prompt = _format_prompt(news_items, config)
    llm_cfg = config["llm"]
    base_url = llm_cfg.get("base_url")
    api_key = (
        os.getenv("OPENROUTER_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or llm_cfg.get("api_key")
    )
    client = OpenAI(base_url=base_url, api_key=api_key) if base_url else OpenAI(api_key=api_key)
    model = config["llm"]["model"]
    temperature = config["llm"].get("temperature", 0.3)

    completion = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[
            {
                "role": "system",
                "content": (
                    "Ты новостной редактор. Сделай короткий сценарий выпуска: вступление, 3-5 сюжетов, финал. "
                    "Стиль деловой, краткий, без эмоций. Язык — русский. Этот текст пойдёт сразу на генерацию новостного видеоролика, так что дай готовый сценарий для произношения на видео без разметки"
                ),
            },
            {"role": "user", "content": prompt},
        ],
    )

    script_text = completion.choices[0].message.content.strip()
    bullets = _extract_bullets(script_text, config)
    segments = _build_segments(bullets, config)

    log_payload = {
        "prompt": prompt,
        "response": script_text,
        "model": model,
        "temperature": temperature,
    }
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log_payload, f, ensure_ascii=False, indent=2)

    return {
        "script_text": script_text,
        "bullets": bullets,
        "segments": segments,
    }


def _format_prompt(news_items: List[Dict], config: Dict) -> str:
    anchor = config["style"]["anchor_name"]
    theme = config["theme"]
    lines = [f"Тема выпуска: {theme}. Ведущий: {anchor}. Сводка новостей:"]
    for i, item in enumerate(news_items, 1):
        lines.append(f"{i}) {item['title']}. {item['body']}")
    lines.append(
        "Сформируй связный текст ведущего (3-5 сюжетов), выдели короткие тезисы для титров, без воды и домыслов."
    )
    return "\n".join(lines)


def _extract_bullets(script_text: str, config: Dict) -> List[str]:
    lines = [line.strip("-• ") for line in script_text.splitlines() if line.strip()]
    bullets = []
    for line in lines:
        if len(bullets) >= config["style"].get("bullet_count", 4):
            break
        if len(line) > 12:
            bullets.append(line)
    if not bullets:
        bullets = lines[:3]
    return bullets


def _build_segments(bullets: List[str], config: Dict) -> List[Dict]:
    duration = config["video"]["duration_seconds"]
    per = max(duration / max(len(bullets), 1), 5)
    segments = []
    start = 0.0
    for b in bullets:
        end = min(start + per, duration)
        segments.append({"start": round(start, 2), "end": round(end, 2), "caption": b})
        start = end
    return segments
