"""Classify one coffee leaf photo on the hub, offline.

NOT RUN YET (no trained model). Needs: onnxruntime, numpy, pillow.
On Termux, check onnxruntime installs first; if not, use the native app route
(ONNX Runtime Mobile or TFLite) and keep this file as the reference logic.

Usage: python vision/predict.py path/to/leaf.jpg

Returns {"class", "confidence", "diagnosis", "sure", "quality"}:
- quality "too_dark" / "too_blurry" -> no prediction, ask for a new photo
- confidence below the threshold chosen in training -> "unknown", refer to a person
"""

import json
import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageFilter

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from shared.diagnoses import VISION_CLASS_TO_DIAGNOSIS

MIN_BRIGHTNESS = 40      # mean pixel value 0-255
MIN_SHARPNESS = 60.0     # variance of edge image; lower = blurry


class LeafModel:
    def __init__(self, model_path=HERE / "leaf_model.int8.onnx", labels_path=HERE / "leaf_labels.json"):
        meta = json.loads(Path(labels_path).read_text())
        self.classes, self.size = meta["classes"], meta["image_size"]
        self.mean = np.array(meta["mean"], dtype=np.float32).reshape(3, 1, 1)
        self.std = np.array(meta["std"], dtype=np.float32).reshape(3, 1, 1)
        self.threshold = meta["threshold"]
        self.session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])

    def quality(self, img):
        gray = img.convert("L")
        if np.asarray(gray).mean() < MIN_BRIGHTNESS:
            return "too_dark"
        edges = np.asarray(gray.filter(ImageFilter.FIND_EDGES), dtype=np.float32)
        if edges.var() < MIN_SHARPNESS:
            return "too_blurry"
        return "ok"

    def preprocess(self, img):
        img = img.convert("RGB")
        w, h = img.size
        s = 256 / min(w, h)
        img = img.resize((round(w * s), round(h * s)))
        w, h = img.size
        left, top = (w - self.size) // 2, (h - self.size) // 2
        img = img.crop((left, top, left + self.size, top + self.size))
        x = np.asarray(img, dtype=np.float32).transpose(2, 0, 1) / 255.0
        return ((x - self.mean) / self.std)[None]

    def classify(self, path):
        img = Image.open(path)
        q = self.quality(img)
        if q != "ok":
            return {"class": None, "confidence": 0.0, "diagnosis": "unknown", "sure": False, "quality": q}
        logits = self.session.run(None, {"image": self.preprocess(img)})[0][0]
        p = np.exp(logits - logits.max())
        p /= p.sum()
        i = int(p.argmax())
        cls, conf = self.classes[i], float(p[i])
        sure = conf >= self.threshold
        diag = VISION_CLASS_TO_DIAGNOSIS.get(cls.lower(), "unknown") if sure else "unknown"
        return {"class": cls, "confidence": round(conf, 3), "diagnosis": diag, "sure": sure, "quality": "ok"}


if __name__ == "__main__":
    print(LeafModel().classify(sys.argv[1]))
