"""
ConsumerShield — Vision Parser
Uses Grok Vision (xAI) via instructor to analyse product/defect photos
and return structured VisionExtractionOutput.
"""
from __future__ import annotations

import base64
import mimetypes
import os

from evidence.schemas import VisionExtractionOutput
from backend.config import get_instructor_client, VISION_MODEL


VISION_SYSTEM_PROMPT = (
    "You are a product damage assessment system. "
    "Describe ONLY what is visually observable. "
    "Do NOT speculate on cause or timing of damage. "
    "Report: visible damage, severity (minor/moderate/severe), "
    "brand/model if visible, serial numbers if visible."
)


def _image_to_data_url(image_path: str) -> str:
    """Read an image file, base64-encode it, and return a data-URL string."""
    mime_type, _ = mimetypes.guess_type(image_path)
    if mime_type is None:
        mime_type = "image/jpeg"

    with open(image_path, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode("utf-8")

    return f"data:{mime_type};base64,{b64}"


def analyze_product_image(image_path: str) -> VisionExtractionOutput:
    """Analyse a product / defect photo using Grok Vision.

    Args:
        image_path: Absolute or relative path to the image file.

    Returns:
        VisionExtractionOutput with damage description, severity, identifiers.

    Raises:
        FileNotFoundError: If the image file does not exist.
        RuntimeError: On API or parsing errors.
    """
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    data_url = _image_to_data_url(image_path)

    try:
        client = get_instructor_client()

        result = client.chat.completions.create(
            model=VISION_MODEL,
            response_model=VisionExtractionOutput,
            messages=[
                {"role": "system", "content": VISION_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": data_url},
                        },
                        {
                            "type": "text",
                            "text": (
                                "Analyse this product image. "
                                "Describe any visible damage, its severity, "
                                "and any brand/model/serial identifiers you can read."
                            ),
                        },
                    ],
                },
            ],
            temperature=0.0,
        )
    except Exception as exc:
        raise RuntimeError(
            f"Vision analysis failed for '{image_path}': {exc}"
        ) from exc

    return result
