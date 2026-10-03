"""Fine-tune a small image model on BRACOL coffee leaf images and export it for the hub.

NOT RUN YET: written without access to PyTorch or the dataset. Martin, expect
small fixes. Runs on a laptop CPU in an hour or two for a few thousand images;
faster on a Colab GPU.

Setup:
    pip install torch torchvision onnx onnxruntime pillow
    Put images in class folders, one folder per class, e.g.
        vision/data/healthy/*.jpg
        vision/data/rust/*.jpg
        vision/data/miner/*.jpg
        ...
    (BRACOL's own folder names are fine; map them in shared/diagnoses.py
     VISION_CLASS_TO_DIAGNOSIS.)

Usage:
    python vision/train_vision.py --data vision/data --epochs 8

Outputs (in vision/):
    leaf_model.onnx        float model
    leaf_model.int8.onnx   quantized model for the hub (a few MB)
    leaf_labels.json       class order, image size, normalisation, chosen threshold
    vision_report.json     accuracy, per-class results, size, threshold coverage

Split note: BRACOL has several crops/photos per leaf in some versions. If file
names share a leaf ID, split by that ID (--group-regex) so the same leaf never
appears in both train and validation; otherwise accuracy is inflated.
"""

import argparse
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, models, transforms

HERE = Path(__file__).resolve().parent
IMG = 224
MEAN, STD = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]


def group_split(dataset, val_share, group_regex, seed=0):
    """Split by leaf/group id if a regex is given, else by file."""
    groups = defaultdict(list)
    for idx, (path, _) in enumerate(dataset.samples):
        name = Path(path).stem
        m = re.search(group_regex, name) if group_regex else None
        groups[m.group(1) if m else name].append(idx)
    keys = sorted(groups)
    random.Random(seed).shuffle(keys)
    n_val = int(len(keys) * val_share)
    val_keys = set(keys[:n_val])
    tr = [i for k in keys if k not in val_keys for i in groups[k]]
    va = [i for k in val_keys for i in groups[k]]
    return tr, va


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(HERE / "data"))
    ap.add_argument("--epochs", type=int, default=8)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--val-share", type=float, default=0.2)
    ap.add_argument("--group-regex", default=None, help=r"e.g. '^(\d+)_' to group crops by leaf id")
    ap.add_argument("--target-precision", type=float, default=0.90,
                    help="threshold is chosen so answered predictions reach this accuracy")
    args = ap.parse_args()

    train_tf = transforms.Compose([
        # field photos differ from lab photos: augment light, angle, crop
        transforms.RandomResizedCrop(IMG, scale=(0.6, 1.0)),
        transforms.RandomHorizontalFlip(), transforms.RandomVerticalFlip(),
        transforms.RandomRotation(20),
        transforms.ColorJitter(0.4, 0.4, 0.3, 0.05),
        transforms.ToTensor(), transforms.Normalize(MEAN, STD),
    ])
    eval_tf = transforms.Compose([
        transforms.Resize(256), transforms.CenterCrop(IMG),
        transforms.ToTensor(), transforms.Normalize(MEAN, STD),
    ])
    base = datasets.ImageFolder(args.data)
    classes = base.classes
    print("classes:", classes, dict(Counter(classes[y] for _, y in base.samples)))
    tr_idx, va_idx = group_split(base, args.val_share, args.group_regex)
    train_ds = Subset(datasets.ImageFolder(args.data, transform=train_tf), tr_idx)
    val_ds = Subset(datasets.ImageFolder(args.data, transform=eval_tf), va_idx)
    tl = DataLoader(train_ds, batch_size=args.batch, shuffle=True, num_workers=2)
    vl = DataLoader(val_ds, batch_size=args.batch, num_workers=2)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT)
    model.classifier[-1] = nn.Linear(model.classifier[-1].in_features, len(classes))
    model.to(device)

    # balance classes in the loss
    counts = Counter(base.samples[i][1] for i in tr_idx)
    w = torch.tensor([len(tr_idx) / (len(classes) * counts.get(c, 1)) for c in range(len(classes))],
                     dtype=torch.float32, device=device)
    loss_fn = nn.CrossEntropyLoss(weight=w)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=args.epochs)

    for epoch in range(args.epochs):
        model.train()
        total = 0.0
        for x, y in tl:
            x, y = x.to(device), y.to(device)
            opt.zero_grad()
            loss = loss_fn(model(x), y)
            loss.backward()
            opt.step()
            total += loss.item() * len(y)
        sched.step()
        probs, ys = evaluate(model, vl, device)
        acc = (probs.argmax(1) == ys).mean()
        print(f"epoch {epoch + 1}: train loss {total / len(train_ds):.3f}  val acc {acc:.3f}")

    probs, ys = evaluate(model, vl, device)
    pred, conf = probs.argmax(1), probs.max(1)
    threshold = pick_threshold(pred, conf, ys, args.target_precision)
    answered = conf >= threshold
    per_class = {c: round(float((pred[ys == i] == i).mean()), 3) if (ys == i).any() else None
                 for i, c in enumerate(classes)}
    confusion = np.zeros((len(classes), len(classes)), dtype=int)
    for t, p in zip(ys, pred):
        confusion[t, p] += 1

    model.eval().cpu()
    onnx_path, q_path = HERE / "leaf_model.onnx", HERE / "leaf_model.int8.onnx"
    torch.onnx.export(model, torch.randn(1, 3, IMG, IMG), onnx_path,
                      input_names=["image"], output_names=["logits"],
                      dynamic_axes={"image": {0: "batch"}}, opset_version=17)
    from onnxruntime.quantization import QuantType, quantize_dynamic
    quantize_dynamic(str(onnx_path), str(q_path), weight_type=QuantType.QUInt8)

    (HERE / "leaf_labels.json").write_text(json.dumps({
        "classes": classes, "image_size": IMG, "mean": MEAN, "std": STD,
        "threshold": round(float(threshold), 3), "version": "vision-v1",
    }, indent=2))
    report = {
        "val_images": int(len(ys)),
        "accuracy_all": round(float((pred == ys).mean()), 3),
        "threshold": round(float(threshold), 3),
        "answered_share": round(float(answered.mean()), 3),
        "accuracy_when_answered": round(float((pred[answered] == ys[answered]).mean()), 3)
        if answered.any() else None,
        "per_class_accuracy": per_class,
        "confusion_rows_true_cols_pred": confusion.tolist(),
        "model_mb_float": round(onnx_path.stat().st_size / 1e6, 2),
        "model_mb_int8": round(q_path.stat().st_size / 1e6, 2),
        "note": "Validation images come from BRACOL, not East African field photos.",
    }
    (HERE / "vision_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


@torch.no_grad()
def evaluate(model, loader, device):
    model.eval()
    ps, ys = [], []
    for x, y in loader:
        ps.append(torch.softmax(model(x.to(device)), 1).cpu().numpy())
        ys.append(y.numpy())
    return np.concatenate(ps), np.concatenate(ys)


def pick_threshold(pred, conf, ys, target):
    """Lowest threshold at which answered predictions reach the target accuracy."""
    for t in np.arange(0.3, 0.99, 0.01):
        m = conf >= t
        if m.sum() >= 10 and (pred[m] == ys[m]).mean() >= target:
            return float(t)
    return 0.9


if __name__ == "__main__":
    main()
