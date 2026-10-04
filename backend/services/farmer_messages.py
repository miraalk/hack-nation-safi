import json
from pathlib import Path

from shared.data import load_farmers
from shared.diagnoses import DIAGNOSES, NEEDS_CONFIRMATION
from shared.text_model import TextModel


ROOT = Path(__file__).resolve().parents[2]
SMS_SCRIPT_PATH = ROOT / "hub" / "sms_script.json"

_model = TextModel()
_farmers = load_farmers()

with open(SMS_SCRIPT_PATH, encoding="utf-8") as f:
    _sms = json.load(f)


def _farmer_by_phone(phone: str):
    normalized = phone.strip().replace(" ", "")

    for farmer in _farmers.values():
        farmer_phone = str(farmer.get("phone", "")).strip().replace(" ", "")

        if farmer_phone == normalized:
            return farmer

    return None


def _message(key: str, lang: str = "en", **values):
    template = _sms["messages"][key][lang]
    return template.format(**values)


def _diagnosis_name(diagnosis: str, lang: str = "en"):
    names = _sms["diagnosis_names"].get(diagnosis, {})
    return names.get(lang) or names.get("en") or DIAGNOSES.get(diagnosis, diagnosis)


def handle_farmer_message(phone: str, text: str) -> str:
    farmer = _farmer_by_phone(phone)

    # For sandbox testing, allow unknown numbers for now.
    lang = farmer.get("language", "en") if farmer else "en"

    result = _model.classify(text)

    print("Classification:", result)

    if not result["sure"]:
        return _message(
            "noor_unsure",
            lang=lang,
            centre="your washing station",
        )

    diagnosis = result["diagnosis"]
    diagnosis_name = _diagnosis_name(diagnosis, lang)

    if diagnosis in NEEDS_CONFIRMATION:
        return _message(
            "noor_likely_bring_leaves",
            lang=lang,
            diagnosis=diagnosis_name,
            centre="your washing station",
        )

    return _message(
        "noor_likely_no_photo",
        lang=lang,
        diagnosis=diagnosis_name,
        ussd="*384*22426#",
    )