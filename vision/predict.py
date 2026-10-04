"""Detect coffee leaf disease from one photo, offline.

Uses:
    vision/models/decafia/decafia_clean_best.pt

DECAFIA classes:
    0 roya     -> coffee leaf rust
    1 coco     -> weevil / coco damage
    2 minador  -> leaf miner

A photo with no detection above the confidence threshold is treated as
"inconclusive" rather than automatically healthy.

Usage:
    python vision/predict.py path/to/leaf.jpg
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from ultralytics import YOLO

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

sys.path.insert(0, str(ROOT))

from shared.diagnoses import VISION_CLASS_TO_DIAGNOSIS


MODEL_PATH = (
    HERE
    / "models"
    / "decafia"
    / "decafia_clean_best.pt"
)

CONFIDENCE_THRESHOLD = 0.50

MIN_BRIGHTNESS = 40
MIN_SHARPNESS = 60.0


CLASS_TO_FARMFLOW = {
    "roya": "leaf_rust",
    "minador": "leaf_miner",

    # Keep this separate unless your downstream recommendation
    # logic has a specific treatment for it.
    "coco": "unknown",
}


class LeafModel:
    def __init__(self, model_path=MODEL_PATH):
        self.model = YOLO(str(model_path))

        print("Vision model:", model_path.name)
        print("Vision classes:", self.model.names)

    def quality(self, img):
        gray = img.convert("L")

        brightness = np.asarray(
            gray,
            dtype=np.float32,
        ).mean()

        if brightness < MIN_BRIGHTNESS:
            return "too_dark"

        edges = np.asarray(
            gray.filter(ImageFilter.FIND_EDGES),
            dtype=np.float32,
        )

        if edges.var() < MIN_SHARPNESS:
            return "too_blurry"

        return "ok"

    def classify(self, path):
        img = Image.open(path).convert("RGB")

        quality = self.quality(img)

        if quality != "ok":
            return {
                "class": None,
                "confidence": 0.0,
                "diagnosis": "unknown",
                "sure": False,
                "quality": quality,
                "detections": [],
            }

        results = self.model.predict(
            source=str(path),
            conf=CONFIDENCE_THRESHOLD,
            verbose=False,
        )

        result = results[0]
        detections = []

        if result.boxes is not None:
            for box in result.boxes:
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])

                class_name = result.names[class_id]

                xyxy = box.xyxy[0].tolist()

                detections.append({
                    "class_id": class_id,
                    "class": class_name,
                    "confidence": round(
                        confidence,
                        3,
                    ),
                    "box": [
                        round(float(x), 1)
                        for x in xyxy
                    ],
                })

        detections.sort(
            key=lambda d: d["confidence"],
            reverse=True,
        )

        if detections:
            print(
                f"Detected {len(detections)} regions. "
                f"Best: {detections[0]['class']} "
                f"({detections[0]['confidence']:.3f})"
            )
        else:
            print("No confident detections.")

        if not detections:
            return {
                "class": None,
                "confidence": 0.0,
                "diagnosis": "unknown",
                "sure": False,
                "quality": "ok",
                "detections": [],
            }

        best = detections[0]

        cls = best["class"]
        confidence = best["confidence"]

        diagnosis = CLASS_TO_FARMFLOW.get(
            cls.lower(),
            VISION_CLASS_TO_DIAGNOSIS.get(
                cls.lower(),
                "unknown",
            ),
        )

        return {
            "class": cls,
            "confidence": confidence,
            "diagnosis": diagnosis,
            "sure": diagnosis != "unknown",
            "quality": "ok",
        }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(
            "Usage: python vision/predict.py "
            "path/to/leaf.jpg"
        )
        raise SystemExit(1)

    model = LeafModel()

    result = model.classify(
        sys.argv[1]
    )

    print(result)