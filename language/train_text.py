"""Train the symptom text classifier and export it to JSON for the hub.

Usage: python language/train_text.py
Needs: scikit-learn (training only).

Reads language/examples.csv (columns: text, label, lang, author, split).
- split=train rows are used for training and cross-validation.
- split=test rows (ideally written by someone else) are held out and only scored.
Reports accuracy, per-label results, accuracy by language, and how often the
model is "sure" at the chosen threshold.
"""

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shared import config
from shared.diagnoses import TEXT_LABEL_TO_DIAGNOSIS
from shared.text_model import TextModel, preprocess

NGRAMS = (2, 4)


def load():
    with open(ROOT / "language" / "examples.csv", newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["text"].strip()]
    bad = {r["label"] for r in rows} - set(TEXT_LABEL_TO_DIAGNOSIS)
    if bad:
        sys.exit(f"Unknown label(s) in examples.csv: {sorted(bad)}. "
                 f"Use one of: {sorted(TEXT_LABEL_TO_DIAGNOSIS)}")
    return rows


def make_model():
    return make_pipeline(
        TfidfVectorizer(analyzer="char_wb", ngram_range=NGRAMS, preprocessor=preprocess,
                        sublinear_tf=True, min_df=1),
        LogisticRegression(C=10, max_iter=2000),
    )


def report(name, y_true, probs, classes, langs):
    pred = [classes[i] for i in probs.argmax(1)]
    conf = probs.max(1)
    acc = np.mean([p == t for p, t in zip(pred, y_true)])
    sure = conf >= config.TEXT_THRESHOLD
    acc_sure = np.mean([p == t for p, t, s in zip(pred, y_true, sure) if s]) if sure.any() else float("nan")
    print(f"\n== {name}: {len(y_true)} messages")
    print(f"accuracy (all)                 {acc:.2f}")
    print(f"answered (conf >= {config.TEXT_THRESHOLD})         {sure.mean():.2f} of messages")
    print(f"accuracy when it answers       {acc_sure:.2f}")
    by_lang = defaultdict(list)
    for p, t, l in zip(pred, y_true, langs):
        by_lang[l].append(p == t)
    for l, v in sorted(by_lang.items()):
        print(f"  {l:6} accuracy {np.mean(v):.2f} (n={len(v)})")
    errors = Counter((t, p) for p, t in zip(pred, y_true) if p != t)
    if errors:
        print("most common mix-ups (true -> predicted):")
        for (t, p), n in errors.most_common(5):
            print(f"  {t} -> {p}: {n}")


def main():
    rows = load()
    train = [r for r in rows if r["split"] != "test"]
    test = [r for r in rows if r["split"] == "test"]
    counts = Counter(r["label"] for r in train)
    print("training examples per label:", dict(sorted(counts.items())))
    print("by language:", dict(Counter(r["lang"] for r in train)))

    X = [r["text"] for r in train]
    y = [r["label"] for r in train]
    k = min(5, min(counts.values()))
    if k >= 2:
        cv = StratifiedKFold(n_splits=k, shuffle=True, random_state=0)
        probs = cross_val_predict(make_model(), X, y, cv=cv, method="predict_proba")
        classes = sorted(set(y))
        report(f"{k}-fold cross-validation on training examples", y, probs, classes,
               [r["lang"] for r in train])

    model = make_model().fit(X, y)
    vec, clf = model.named_steps["tfidfvectorizer"], model.named_steps["logisticregression"]
    spec = {
        "version": "text-v1",
        "ngram_range": list(NGRAMS),
        "vocab": {g: int(i) for g, i in vec.vocabulary_.items()},
        "idf": [round(float(v), 6) for v in vec.idf_],
        "classes": clf.classes_.tolist(),
        "coef": [[round(float(v), 6) for v in row] for row in clf.coef_],
        "intercept": [round(float(v), 6) for v in clf.intercept_],
        "trained_on": len(train),
    }
    out = ROOT / "language" / "text_model.json"
    out.write_text(json.dumps(spec, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"\nexported {out.name}: {out.stat().st_size / 1024:.0f} KB, {len(spec['vocab'])} n-grams")

    # parity check: pure-Python model must match scikit-learn
    tm = TextModel(out)
    sk = model.predict_proba(X[:50])
    py = np.array([[tm.probabilities(t)[c] for c in clf.classes_] for t in X[:50]])
    print(f"parity max diff: {np.abs(sk - py).max():.2e}")

    if test:
        probs = model.predict_proba([r["text"] for r in test])
        # align columns to classes the model knows
        report("held-out test set", [r["label"] for r in test], probs, clf.classes_.tolist(),
               [r["lang"] for r in test])

    for t in ["coffee leaves with orange spots", "ndashaka kumenya igiciro", "my berries fall"]:
        print(f"try: {t!r:40} -> {tm.classify(t)}")


if __name__ == "__main__":
    main()
