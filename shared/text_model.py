"""Symptom text classifier, evaluated in pure Python on the hub.

Character n-grams (2-4, within word boundaries) + TF-IDF + multinomial logistic
regression, exported to JSON by language/train_text.py. Character fragments
make it robust to typos, missing apostrophes and Kinyarwanda-English mixing.

classify(text) -> {"label", "confidence", "diagnosis", "sure"}
Below TEXT_THRESHOLD the hub replies "not sure, ask a person".
"""

import json
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path

from . import config
from .diagnoses import TEXT_LABEL_TO_DIAGNOSIS

MODEL_PATH = Path(__file__).resolve().parent.parent / "language" / "text_model.json"
_WS = re.compile(r"\s\s+")


def preprocess(text):
    """Must match training: lowercase, strip accents, collapse whitespace."""
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return _WS.sub(" ", text)


def char_wb_ngrams(text, min_n, max_n):
    """Same as scikit-learn's analyzer='char_wb'."""
    grams = []
    for w in text.split():
        w = " " + w + " "
        w_len = len(w)
        for n in range(min_n, max_n + 1):
            offset = 0
            grams.append(w[offset:offset + n])
            while offset + n < w_len:
                offset += 1
                grams.append(w[offset:offset + n])
            if offset == 0:
                break
    return grams


class TextModel:
    def __init__(self, path=MODEL_PATH):
        spec = json.loads(Path(path).read_text(encoding="utf-8"))
        self.vocab = spec["vocab"]
        self.idf = spec["idf"]
        self.coef = spec["coef"]
        self.intercept = spec["intercept"]
        self.classes = spec["classes"]
        self.min_n, self.max_n = spec["ngram_range"]
        self.version = spec["version"]

    def probabilities(self, text):
        counts = Counter(g for g in char_wb_ngrams(preprocess(text), self.min_n, self.max_n)
                         if g in self.vocab)
        vec = {self.vocab[g]: (1 + math.log(c)) * self.idf[self.vocab[g]] for g, c in counts.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        scores = [b + sum(row[j] * v / norm for j, v in vec.items())
                  for row, b in zip(self.coef, self.intercept)]
        m = max(scores)
        exps = [math.exp(s - m) for s in scores]
        z = sum(exps)
        return {c: e / z for c, e in zip(self.classes, exps)}

    def classify(self, text, threshold=None):
        threshold = config.TEXT_THRESHOLD if threshold is None else threshold
        probs = self.probabilities(text)
        label = max(probs, key=probs.get)
        conf = probs[label]
        sure = conf >= threshold and label != "other"
        return {"label": label, "confidence": round(conf, 3),
                "diagnosis": TEXT_LABEL_TO_DIAGNOSIS[label] if sure else "unknown", "sure": sure}
