"""
openrouter_client.py

Thin client wrapper around the OpenRouter chat completions API for
vision-capable prompting (image + text -> text).
"""

import base64
import mimetypes
from pathlib import Path

import requests

import ocr.config as config


def _encode_image(image_path: Path) -> str:
    """Return a base64 data URI for the given image file."""
    mime_type, _ = mimetypes.guess_type(str(image_path))
    if mime_type is None:
        mime_type = "image/jpeg"
    data = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    return f"data:{mime_type};base64,{data}"


def transcribe_page(image_path: Path, prompt_text: str) -> str:
    if not config.OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. Export it or add it to your .env file."
        )

    image_data_uri = _encode_image(image_path)

    payload = {
        "model": config.MODEL,
        "temperature": config.TEMPERATURE,
        "max_tokens": config.MAX_TOKENS,
        "reasoning": {
        "effort": "low" 
        },
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_text},
                    {"type": "image_url", "image_url": {"url": image_data_uri}},
                ],
            }
        ],
    }

    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        f"{config.OPENROUTER_BASE_URL}/chat/completions",
        json=payload,
        headers=headers,
        timeout=180,
    )
    response.raise_for_status()

    data = response.json()

    choice = data["choices"][0]
    finish_reason = choice.get("finish_reason", "unknown")
    usage = data.get("usage", {})
    print(f"  finish_reason={finish_reason}  usage={usage}")
    if finish_reason == "length":
        print("  [WARN] Response was cut off by max_tokens — increase config.MAX_TOKENS")

    return choice["message"]["content"]