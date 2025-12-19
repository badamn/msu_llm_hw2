# Генерация новостного видео (RU)

Пайплайн: RSS → LLM (Openrouter) → TTS (gTTS, при необходимости) → аватар HeyGen → фон/титры → экспорт .mp4. Запуск одной командой `run_pipeline.py`, все артефакты сохраняются в `outputs/`.

## Параметры выпуска
- Тема: технологии и рынки (ИТ/финтех/телеком/hardware).
- Период: последние 24–48 часов (задаётся датой/интервалом).
- Формат: 16:9, 1280x720, 30 fps.
- Длительность: ~40 с (3–5 сюжетов).
- Источники: RSS (см. `configs/sources.yaml`).

## Структура
- `configs/` — источники, базовые параметры, TTS, шаблон, экспорт.
- `data/` — примеры новостей/ассеты (фон, фото ведущего).
- `src/ingest_news/` — загрузка/очистка RSS.
- `src/script_builder_llm/` — сценарий через OpenAI.
- `src/tts/` — озвучка (gTTS).
- `src/avatar/` — провайдеры аватара (HeyGen).
- `src/visual_template/` — фон, титры, стили.
- `src/video_composer/` — сборка дорожек в .mp4.
- `outputs/` — логи, сценарии, аудио, итоговые видео.
- `run_pipeline.py` — единая точка запуска.

## Зависимости
- Python 3.10+, `ffmpeg` в PATH.
- pip: `feedparser`, `PyYAML`, `openai`, `gtts`, `pydub`, `moviepy`, `Pillow`, `requests`.

Установка:
```bash
python -m venv .venv
./.venv/Scripts/activate  # Windows
pip install -r requirements.txt
```

## Переменные окружения
- `OPENROUTER_API_KEY` — ключ OpenRouter (LLM). При отсутствии используется `OPENAI_API_KEY`.
- `OPENAI_API_KEY` — запасной ключ OpenAI (если не указан OpenRouter).
- `HEYGEN_API_KEY` — ключ HeyGen (встроенный голос + аватар).
- `FREE_TTS_PROVIDER` — опционально, по умолчанию gTTS.

## Быстрый запуск
```bash
python run_pipeline.py --date 2024-05-20 --sources configs/sources.yaml --out outputs/video/video_example.mp4
```
Опции: `--use-sample` (новости из `data/sample_news.json`), `--dry-run` (без TTS/рендера), `--heygen-test` (флаг test для HeyGen API).

## Пайплайн шаги
1) `ingest_news`: RSS → очистка html/emoji → фильтр/дедуп → `outputs/logs/news_<date>.json`.
2) `script_builder_llm`: промпт к OpenAI → текст ведущего + тезисы/сегменты → `outputs/scripts/script_<date>.json`.
3) `avatar (HeyGen)`: при `avatar.provider=heygen` генерирует видео говорящей головы из текста через `https://api.heygen.com/v2/video/generate`, сохраняет `outputs/video/avatar_heygen_<date>.mp4`. Если `use_heygen_audio=true`, внешний TTS не накладывается.
4) `tts`: если нужно озвучить локально — gTTS → `outputs/audio/voice_<date>.wav`.
5) `visual_template`: фон/позиции/стили титров.
6) `video_composer`: фон + аватар-видео/фото + титры (по таймкодам) + аудио → `outputs/video/video_<date>.mp4`.

## Формат артефактов
- Новости: JSON `[{title, body, ts, source, url}]`.
- Сценарий: `{script_text, bullets, segments (start, end, caption)}`.
- Аудио: WAV 22.05 kHz (по умолчанию).
- Видео: mp4 H.264, 1280x720, 25 fps.

## Примечания
- Дообучение моделей не требуется; используем промпты (в модуле `script_builder_llm`).
- Все промежуточные артефакты лежат в `outputs/`.
- При недоступности HeyGen сработает TTS + статичное фото (если есть). Чтобы отключить TTS, оставьте `use_heygen_audio=true` и задайте `avatar.video_path` (или дайте сгенерировать автоматом).
