import os
from typing import Dict

from PIL import Image, ImageDraw


def prepare_visuals(template_cfg: Dict, outputs_root: str) -> Dict:
    os.makedirs(outputs_root, exist_ok=True)
    background_path = template_cfg["background"].get("path")
    if not background_path or not os.path.exists(background_path):
        background_path = _make_placeholder_bg(
            os.path.join(outputs_root, "bg_placeholder.png"),
            template_cfg["background"].get("color_fallback", "#0f172a"),
        )

    avatar_video = template_cfg["avatar"].get("video_path", "")
    avatar_photo = template_cfg["avatar"].get("photo_path", "")

    return {
        "background_path": background_path,
        "avatar_video": avatar_video,
        "avatar_photo": avatar_photo,
        "captions_style": template_cfg.get("captions", {}),
    }


def _make_placeholder_bg(path: str, color: str) -> str:
    img = Image.new("RGB", (1280, 720), color)
    draw = ImageDraw.Draw(img)
    draw.text((40, 40), "Tech/Markets Briefing", fill="#94a3b8")
    img.save(path)
    return path
