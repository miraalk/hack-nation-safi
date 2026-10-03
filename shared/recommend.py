"""Rule-based input recommendations from a confirmed (or likely) diagnosis.

Picks catalogue items whose `diagnoses` include the diagnosis, most important
first (rank), quantity scaled by tree count (`per_trees`), staying within the
credit limit, at most MAX_ITEMS items so it fits one USSD screen.
No second model: the catalogue is agreed with the extension officer.
"""

import math

from . import config


def recommend(limit_rwf, diagnosis, trees, catalogue, lang="en"):
    if diagnosis in ("unknown", None):
        return {"status": "refer", "items": [], "total_rwf": 0, "remaining_rwf": limit_rwf}
    if diagnosis == "healthy":
        return {"status": "no_treatment", "items": [], "total_rwf": 0, "remaining_rwf": limit_rwf}
    if limit_rwf <= 0:
        return {"status": "no_credit", "items": [], "total_rwf": 0, "remaining_rwf": 0}

    matches = sorted((i for i in catalogue if diagnosis in i["diagnoses"]),
                     key=lambda i: (i["rank"], i["price_rwf"]))
    budget, bundle = limit_rwf, []
    for item in matches:
        if len(bundle) == config.MAX_ITEMS:
            break
        want = max(1, math.ceil(trees / item["per_trees"])) if item["per_trees"] else 1
        qty = min(want, budget // item["price_rwf"])
        if qty >= 1:
            bundle.append({
                "input_id": item["input_id"],
                "name": item.get("short_rw") if lang == "rw" and item.get("short_rw") else item["short_en"],
                "qty": int(qty),
                "unit_price_rwf": item["price_rwf"],
                "subtotal_rwf": int(qty * item["price_rwf"]),
                "note_en": item["note_en"],
            })
            budget -= qty * item["price_rwf"]

    if not bundle:
        cheapest = min((i["price_rwf"] for i in matches), default=0)
        return {"status": "too_low", "items": [], "total_rwf": 0, "remaining_rwf": limit_rwf,
                "cheapest_rwf": cheapest}
    total = sum(b["subtotal_rwf"] for b in bundle)
    return {"status": "ok", "items": bundle, "total_rwf": total, "remaining_rwf": limit_rwf - total}


def bundle_text(rec):
    """Compact text for a USSD screen, e.g. '3x Fungicide 1kg, Sprayer hire'."""
    return ", ".join((f"{b['qty']}x " if b["qty"] > 1 else "") + b["name"] for b in rec["items"])
