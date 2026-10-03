"""Check the wording files: backend/ussd_script.json and hub/sms_script.json.

Valid JSON, every 'rw' filled, placeholders identical to English, and every
screen/SMS short enough once placeholders are filled with long sample values.

Usage: python3 backend/check_ussd.py
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
USSD_MAX, SMS_MAX = 160, 160
SAMPLE = {
    "name": "Immaculee", "limit": "150,000", "season": "2027", "as_of": "3 Oct 14:05",
    "bundle": "3x Fungicide 1kg, Sprayer hire", "total": "149,000", "cheapest": "5,000",
    "centre": "Ondera washing station", "diagnosis": "coffee berry disease", "ussd": "*384*123#",
    "conf": "87", "problem": "too blurry", "kg": "25.5", "total_kg": "1,373", "farmer_id": "F0001",
    "p10": "1,038", "code": "4821", "village": "Kanjongo", "phone": "+250700000001",
    "message": "amababi afite amabara y'umuhondo",
}
PH = re.compile(r"\{(\w+)\}")


def load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"{path.name}: JSON error: {e}. Usually a missing comma or an unescaped quote.")
        sys.exit(1)


def check(label, key, entry, limit, prefix=""):
    problems = 0
    en_ph = set(PH.findall(entry["en"]))
    for lang in ("en", "rw"):
        text = entry.get(lang, "")
        if not text:
            print(f"[todo]  {label}.{key}.{lang} is empty")
            problems += 1
            continue
        ph = set(PH.findall(text))
        if ph != en_ph:
            print(f"[error] {label}.{key}.{lang} placeholders {sorted(ph)} differ from en {sorted(en_ph)}")
            problems += 1
        unknown = ph - SAMPLE.keys()
        if unknown:
            print(f"[error] {label}.{key}.{lang} unknown placeholder(s) {sorted(unknown)}")
            problems += 1
            continue
        n = len(prefix + text.format(**SAMPLE))
        tag = "[long] " if n > limit else "[ok]   "
        problems += n > limit
        print(f"{tag} {label}.{key}.{lang}: {n} chars")
    return problems


def main():
    ussd = load(ROOT / "backend" / "ussd_script.json")
    sms = load(ROOT / "hub" / "sms_script.json")
    problems = 0
    for key, s in ussd["screens"].items():
        problems += check("ussd", key, s, USSD_MAX, s.get("_prefix", ""))
    for key, names in sms["diagnosis_names"].items():
        if not names.get("rw"):
            print(f"[todo]  sms.diagnosis_names.{key}.rw is empty")
            problems += 1
    for key, m in sms["messages"].items():
        problems += check("sms", key, m, SMS_MAX)
    print("\nAll good." if not problems else f"\n{problems} thing(s) to fix.")


if __name__ == "__main__":
    main()
