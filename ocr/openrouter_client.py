# ocr/openrouter_client.py
import base64
import mimetypes
from pathlib import Path

from openai import OpenAI

import ocr.config as config
from ocr.models import OcrPage
from utils.llm import build_client, response_format


def _encode_image(image_path: Path) -> str:
    mime_type, _ = mimetypes.guess_type(str(image_path))
    if mime_type is None:
        mime_type = "image/jpeg"
    data = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    return f"data:{mime_type};base64,{data}"


def transcribe_page(image_path: Path, prompt_text: str) -> OcrPage:
    if not config.OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. Export it or add it to your .env file."
        )

    client = build_client(config.OPENROUTER_BASE_URL, timeout=180)

    response = client.chat.completions.create(
        model=config.MODEL,
        temperature=config.TEMPERATURE,
        max_tokens=config.MAX_TOKENS,
        response_format=response_format(OcrPage, "OcrPage"),
        extra_body={"reasoning": config.REASONING},
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_text},
                    {"type": "image_url", "image_url": {"url": _encode_image(image_path)}},
                ],
            }
        ],
    )

    finish_reason = response.choices[0].finish_reason
    usage = response.usage
    print(f"  finish_reason={finish_reason}  usage={usage}")
    if finish_reason == "length":
        print("  [WARN] Response was cut off by max_tokens — increase config.MAX_TOKENS")

    content = response.choices[0].message.content
    return OcrPage.model_validate_json(content)