"""
ConsumerShield — Vision Parser
Uses Grok Vision (xAI) via instructor to analyse product/defect photos
and return structured VisionExtractionOutput.
"""
from __future__ import annotations

import base64
import mimetypes
import os

from evidence.schemas import VisionExtractionOutput, VisionExtractionSchema
from backend.config import get_instructor_client, VISION_MODEL


VISION_SYSTEM_PROMPT = (
    "You are a strict forensic image analyst. Analyze the pixels of this image objectively. "
    "Do NOT assume the image contains a defect just because you are asked to look for one. "
    "First, identify the primary object. If the image is a random unrelated object "
    "(like an umbrella, coffee mug, or pet), set is_relevant_to_case to False and return immediately. "
    "Only extract defect details if you visually confirm a relevant product."
)


def _image_to_data_url(image_path: str) -> str:
    """Read an image file, base64-encode it, and return a data-URL string without any filename metadata."""
    mime_type, _ = mimetypes.guess_type(image_path)
    if mime_type is None:
        mime_type = "image/jpeg"

    with open(image_path, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode("utf-8")

    return f"data:{mime_type};base64,{b64}"


def _fallback_pixel_classification(image_path: str) -> VisionExtractionSchema:
    """Classify raw image pixels locally using vision classifier without filename metadata."""
    try:
        from PIL import Image
        import torch
        from torchvision.models import mobilenet_v3_small, MobileNet_V3_Small_Weights
        weights = MobileNet_V3_Small_Weights.DEFAULT
        model = mobilenet_v3_small(weights=weights).eval()
        preprocess = weights.transforms()
        img = Image.open(image_path).convert("RGB")
        batch = preprocess(img).unsqueeze(0)
        with torch.no_grad():
            preds = model(batch).squeeze(0).softmax(0)
        top5_prob, top5_catid = torch.topk(preds, 5)
        categories = weights.meta["categories"]
        top_preds = [(categories[top5_catid[i]], float(top5_prob[i].item())) for i in range(5)]

        unrelated_classes = {
            "mousetrap", "umbrella", "parasol", "mountain tent", "tent", "bathing cap", "crash helmet",
            "football helmet", "bicycle helmet", "helmet", "knee pad", "sunglass", "sunglasses",
            "wok", "frying pan", "pot", "pan", "cup", "mug", "plate", "cat", "dog", "bird",
            "pizza", "cheeseburger", "hotdog", "ice cream", "espresso", "alp", "cliff",
            "valley", "seashore", "flower", "daisy", "sports car", "convertible", "volcano",
            "coral reef", "jellyfish", "balloon", "teddy", "comic book", "monarch", "mushroom",
            "sock", "shoe", "sandal", "loafer", "boot", "backpack", "handbag", "purse", "wallet"
        }
        for label, prob in top_preds[:3]:
            if prob > 0.05 and any(u in label.lower() for u in unrelated_classes):
                return VisionExtractionSchema(
                    is_relevant_to_case=False,
                    detected_primary_object=label.title(),
                    defect_description=None
                )

        ELECTRONIC_CLASSES = {
            "cellular telephone", "telephone", "computer", "laptop", "desktop computer",
            "monitor", "screen", "television", "tv", "loudspeaker", "speaker", "microphone",
            "modem", "keyboard", "computer mouse", "radio", "ipod", "cassette", "cd player", "disc",
            "tape", "fan", "heater", "refrigerator", "washer", "microwave", "toaster",
            "vacuum", "drier", "iron", "dishwasher", "switch", "plug", "socket", "drill", "remote"
        }
        has_electronic = any(any(e in label.lower() for e in ELECTRONIC_CLASSES) for label, _ in top_preds)
        primary_label = top_preds[0][0].title()

        if any(u in primary_label.lower() for u in unrelated_classes):
            return VisionExtractionSchema(
                is_relevant_to_case=False,
                detected_primary_object=primary_label,
                defect_description=None
            )

        if has_electronic:
            return VisionExtractionSchema(
                is_relevant_to_case=True,
                detected_primary_object=primary_label,
                defect_description="Hardware component or display surface under visual inspection"
            )

        if not has_electronic and top_preds[0][1] > 0.10:
            return VisionExtractionSchema(
                is_relevant_to_case=False,
                detected_primary_object=primary_label,
                defect_description=None
            )

        return VisionExtractionSchema(
            is_relevant_to_case=True,
            detected_primary_object=primary_label,
            defect_description=None
        )
    except Exception:
        return VisionExtractionSchema(
            is_relevant_to_case=False,
            detected_primary_object="Unidentified Object",
            defect_description=None
        )


def analyze_product_image(image_path: str) -> VisionExtractionSchema:
    """Analyse a product / defect photo blindly using pure pixels and strict guardrails.

    Filename is strictly blinded from the LLM/VLM prompt.
    """
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    data_url = _image_to_data_url(image_path)

    try:
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
        return _fallback_pixel_classification(image_path)
