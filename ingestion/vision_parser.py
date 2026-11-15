from __future__ import annotations

import base64
import mimetypes
import os
from typing import Optional

from evidence.schemas import VisionExtractionSchema, VisionClassification
from backend.config import get_instructor_client, VISION_MODEL

VISION_SYSTEM_PROMPT = (
    "You are a strict forensic image analyst. Analyze the pixels of this image objectively. "
    "Do NOT assume the image contains a defect just because you are asked to look for one. "
    "First, identify the primary object. If the image is a random unrelated object "
    "(like an umbrella, coffee mug, pet, or food), set is_relevant_to_case to False and return immediately. "
    "Only extract defect details if you visually confirm a relevant product."
)

_CLIP_PIPELINE = None


def _get_clip_classifier():
    global _CLIP_PIPELINE
    if _CLIP_PIPELINE is None:
        from transformers import pipeline
        _CLIP_PIPELINE = pipeline("zero-shot-image-classification", model="openai/clip-vit-base-patch32")
    return _CLIP_PIPELINE


def _image_to_data_url(image_path: str) -> str:
    mime_type, _ = mimetypes.guess_type(image_path)
    if mime_type is None:
        mime_type = "image/jpeg"

    with open(image_path, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode("utf-8")

    return f"data:{mime_type};base64,{b64}"


def _analyze_with_gemini(image_path: str) -> Optional[VisionExtractionSchema]:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        mime_type, _ = mimetypes.guess_type(image_path)
        mime_type = mime_type or "image/jpeg"

        with open(image_path, "rb") as fh:
            img_bytes = fh.read()

        prompt = (
            "Analyze the raw pixels of this photo objectively. Identify the primary object. "
            "Determine if it is a consumer electronic device or appliance (such as phone, laptop, TV, audio, earbud). "
            "Return structured output strictly."
        )

        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=[
                types.Part.from_bytes(data=img_bytes, mime_type=mime_type),
                prompt,
            ],
            config={
                "response_mime_type": "application/json",
                "response_schema": VisionClassification,
                "temperature": 0.0,
            },
        )
        parsed = VisionClassification.model_validate_json(response.text)
        return VisionExtractionSchema(
            is_relevant_to_case=parsed.is_consumer_electronic,
            detected_primary_object=parsed.detected_object_name,
            defect_description=parsed.defect_description,
            is_consumer_electronic=parsed.is_consumer_electronic,
        )
    except Exception:
        return None


def _analyze_with_vlm_instructor(image_path: str) -> Optional[VisionExtractionSchema]:
    try:
        data_url = _image_to_data_url(image_path)
        client = get_instructor_client()
        result = client.chat.completions.create(
            model=VISION_MODEL,
            response_model=VisionExtractionSchema,
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
                                "Analyze the pixels of this image objectively. "
                                "Identify the primary object, assess whether it depicts a relevant consumer "
                                "product/appliance or document, and extract defect details only if relevant."
                            ),
                        },
                    ],
                },
            ],
            temperature=0.0,
        )
        return result
    except Exception:
        return None


def _zero_shot_clip_classification(image_path: str) -> VisionExtractionSchema:
    try:
        from PIL import Image
        img = Image.open(image_path).convert("RGB")
        classifier = _get_clip_classifier()

        candidates = [
            ("a photo of a smartphone, mobile phone, or cell phone", "Smartphone", True),
            ("a photo of a laptop, desktop computer, or monitor", "Laptop Computer", True),
            ("a photo of a television or smart TV display", "Television", True),
            ("a photo of wireless earbuds, headphones, or earphones", "Wireless Earbuds", True),
            ("a photo of a consumer household appliance (refrigerator, washing machine, microwave, air conditioner)", "Home Appliance", True),
            ("a photo of an umbrella or parasol", "Umbrella", False),
            ("a photo of a mousetrap or rodent pest trap", "Mousetrap", False),
            ("a photo of a domestic animal, dog, cat, or pet", "Pet / Animal", False),
            ("a photo of food, meal, fruit, or beverage", "Food / Beverage", False),
            ("a photo of clothing, shoes, footwear, or apparel", "Footwear / Apparel", False),
            ("a photo of trees, flowers, nature, or outdoor scenery", "Nature / Landscape", False),
            ("a photo of an everyday non-electronic household item or hand tool", "Non-electronic Item", False),
            ("a photo of a printed paper document, tax invoice, or receipt", "Paper Document", True),
        ]

        labels = [c[0] for c in candidates]
        preds = classifier(img, candidate_labels=labels)
        top = preds[0]
        label_map = {c[0]: c for c in candidates}
        matched = label_map[top["label"]]

        is_electronic = matched[2]
        obj_name = matched[1]

        if not is_electronic:
            return VisionExtractionSchema(
                is_relevant_to_case=False,
                detected_primary_object=obj_name,
                defect_description=None,
                is_consumer_electronic=False,
            )

        return VisionExtractionSchema(
            is_relevant_to_case=True,
            detected_primary_object=obj_name,
            defect_description=f"{obj_name} hardware under forensic visual examination",
            is_consumer_electronic=True,
        )
    except Exception:
        return VisionExtractionSchema(
            is_relevant_to_case=False,
            detected_primary_object="Unidentified Object",
            defect_description=None,
            is_consumer_electronic=False,
        )


def analyze_product_image(image_path: str, expected_product: Optional[str] = None) -> VisionExtractionSchema:
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    gemini_res = _analyze_with_gemini(image_path)
    if gemini_res is not None:
        return gemini_res

    vlm_res = _analyze_with_vlm_instructor(image_path)
    if vlm_res is not None:
        return vlm_res

    return _zero_shot_clip_classification(image_path)
