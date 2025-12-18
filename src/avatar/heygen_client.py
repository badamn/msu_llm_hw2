import os
import time
from typing import Dict, Optional

import requests


class HeygenClient:
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.heygen.com"):
        self.api_key = api_key or os.getenv("HEYGEN_API_KEY")
        if not self.api_key:
            raise ValueError("HEYGEN_API_KEY is not set")
        self.base_url = base_url.rstrip("/")
        self.headers = {"X-Api-Key": self.api_key, "accept": "application/json", "Content-Type": "application/json"}

    def list_avatars(self) -> Dict:
        url = f"{self.base_url}/v2/avatars"
        resp = requests.get(url, headers=self.headers, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def list_voices(self) -> Dict:
        url = f"{self.base_url}/v1/voice.list"
        resp = requests.get(url, headers=self.headers, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def generate_video_from_text(
        self,
        avatar_id: str,
        voice_id: str,
        text: str,
        aspect_ratio: str = "16:9",
        test: bool = False,
        width: int = 1280,
        height: int = 720,
    ) -> str:
        """
        HeyGen v2 endpoint. Payload aligns with docs:
        https://docs.heygen.com/reference/create-an-avatar-video-v2
        """
        url = f"{self.base_url}/v2/video/generate"
        payload = {
            "caption": False,
            "video_inputs": [
                {
                    "character": {
                        "type": "avatar",
                        "avatar_id": avatar_id,
                        "scale": 1,
                        "avatar_style": "normal",
                        "talking_style": "stable",
                    },
                    "voice": {
                        "type": "text",
                        "voice_id": voice_id,
                        "speed": "1",
                        "pitch": "0",
                        "duration": "1",
                        "input_text": text,
                    },
                }
            ],
            "dimension": {"width": width, "height": height},
        }
        if test:
            payload["test"] = True

        resp = requests.post(url, json=payload, headers=self.headers, timeout=60)
        if resp.status_code >= 400:
            raise RuntimeError(f"HeyGen generate failed {resp.status_code}: {resp.text}")
        data = resp.json()
        return data["data"]["video_id"]

    def poll_video(self, video_id: str, wait_seconds: int = 5, timeout: int = 300) -> Dict:
        # HeyGen v2 status endpoint
        url = f"{self.base_url}/v2/video/status"
        start = time.time()
        while True:
            resp = requests.get(url, params={"video_id": video_id}, headers=self.headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            status = data.get("data", {}).get("status")
            if status == "completed":
                return data["data"]
            if status == "failed":
                raise RuntimeError(f"HeyGen video failed: {data}")
            if time.time() - start > timeout:
                raise TimeoutError(f"HeyGen video timeout after {timeout}s")
            time.sleep(wait_seconds)

    def download_video(self, video_url: str, output_path: str) -> str:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with requests.get(video_url, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        return output_path
