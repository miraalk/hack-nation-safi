import csv
import json
from datetime import date
from pathlib import Path

from backend.services.farmers import find_farmer_by_phone
from shared.diagnoses import DIAGNOSES, NEEDS_CONFIRMATION
from shared.text_model import TextModel


ROOT = Path(__file__).resolve().parents[2]

SMS_SCRIPT_PATH = (
    ROOT
    / "hub"
    / "sms_script.json"
)

DIAGNOSES_PATH = (
    ROOT
    / "data"
    / "diagnoses.csv"
)

_model = TextModel()


with open(
    SMS_SCRIPT_PATH,
    encoding="utf-8",
) as f:
    _sms = json.load(f)


def _message(
    key: str,
    lang: str = "en",
    **values,
):
    template = _sms["messages"][key][lang]

    return template.format(
        **values
    )


def _diagnosis_name(
    diagnosis: str,
    lang: str = "en",
):
    names = (
        _sms["diagnosis_names"]
        .get(diagnosis, {})
    )

    return (
        names.get(lang)
        or names.get("en")
        or DIAGNOSES.get(
            diagnosis,
            diagnosis,
        )
    )


def _save_diagnosis(
    farmer_id: str,
    diagnosis: str,
):
    row = {
        "farmer_id": farmer_id,
        "date": date.today().isoformat(),
        "diagnosis": diagnosis,
    }

    file_exists = (
        DIAGNOSES_PATH.exists()
    )

    with open(
        DIAGNOSES_PATH,
        "a",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "farmer_id",
                "date",
                "diagnosis",
            ],
        )

        if not file_exists:
            writer.writeheader()

        writer.writerow(row)

    print(
        "SMS diagnosis saved:",
        row,
    )


def handle_farmer_message(
    phone: str,
    text: str,
) -> str:

    farmer = find_farmer_by_phone(
        phone
    )

    # For sandbox testing, unknown numbers
    # can still receive a response.
    lang = (
        farmer.get("language", "en")
        if farmer
        else "en"
    )

    result = _model.classify(
        text
    )

    print(
        "Classification:",
        result,
    )

    if not result["sure"]:
        return _message(
            "noor_unsure",
            lang=lang,
            centre="your washing station",
        )

    diagnosis = result["diagnosis"]

    diagnosis_name = _diagnosis_name(
        diagnosis,
        lang,
    )

    # Save confident SMS diagnosis for a
    # registered farmer.
    if (
        farmer
        and diagnosis
        and diagnosis != "unknown"
    ):
        _save_diagnosis(
            farmer_id=farmer["farmer_id"],
            diagnosis=diagnosis,
        )

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