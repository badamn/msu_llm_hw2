import os
from typing import Dict, List

from moviepy.editor import (
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
    VideoFileClip,
)


def compose_video(
    background_path: str,
    avatar_path: str,
    avatar_photo: str,
    captions: List[Dict],
    audio_path: str,
    export_cfg: Dict,
    template_cfg: Dict,
    output_path: str,
) -> str:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    width, height = export_cfg.get("resolution", [1280, 720])
    fps = export_cfg.get("fps", 30)

    bg = ImageClip(background_path).set_duration(export_cfg.get("duration_seconds"))
    bg = bg.resize((width, height))

    avatar_clip = None
    avatar_conf = template_cfg.get("avatar", {})
    pos_rel = avatar_conf.get("position", [0.6, 0.1])
    size_rel = avatar_conf.get("size", [0.35, 0.7])

    if avatar_path and os.path.exists(avatar_path):
        avatar_clip = VideoFileClip(avatar_path).resize((int(width * size_rel[0]), int(height * size_rel[1])))
    elif avatar_photo and os.path.exists(avatar_photo):
        avatar_clip = ImageClip(avatar_photo).set_duration(bg.duration).resize(
            (int(width * size_rel[0]), int(height * size_rel[1]))
        )

    layers = [bg]
    if avatar_clip:
        avatar_clip = avatar_clip.set_position((int(width * pos_rel[0]), int(height * pos_rel[1])))
        layers.append(avatar_clip)

    caption_style = template_cfg.get("captions", {})
    for cap in captions:
        txt = TextClip(
            cap["caption"],
            fontsize=caption_style.get("font_size", 36),
            font=caption_style.get("font", "Arial"),
            color=caption_style.get("color", "white"),
            stroke_color=caption_style.get("stroke_color", "black"),
            stroke_width=caption_style.get("stroke_width", 2),
            method="caption",
            size=(int(width * caption_style.get("area", [0, 0, 1, 1])[2]),
                  int(height * caption_style.get("area", [0, 0, 1, 1])[3])),
        )
        txt = txt.set_start(cap["start"]).set_duration(cap["end"] - cap["start"])
        txt = txt.set_position(
            (int(width * caption_style.get("area", [0, 0, 1, 1])[0]),
             int(height * caption_style.get("area", [0, 0, 1, 1])[1]))
        )
        layers.append(txt)

    video = CompositeVideoClip(layers)

    if audio_path and os.path.exists(audio_path):
        audio = AudioFileClip(audio_path)
        video = video.set_audio(CompositeAudioClip([audio]))
        video = video.set_duration(min(video.duration, audio.duration))
    elif avatar_clip and avatar_clip.audio is not None:
        video = video.set_audio(CompositeAudioClip([avatar_clip.audio]))

    video.write_videofile(
        output_path,
        codec=export_cfg.get("video_codec", "libx264"),
        audio_codec=export_cfg.get("audio_codec", "aac"),
        bitrate=export_cfg.get("bitrate", "3M"),
        audio_bitrate=export_cfg.get("audio_bitrate", "192k"),
        fps=fps,
    )
    return output_path
