import json
import sqlite3
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

DB_PATH = (
    ROOT
    / "data"
    / "farmflow.db"
)

_model = TextModel()


with open(
    SMS_SCRIPT_PATH,
    encoding="utf-8",
) as f:
    _sms = json.load(f)


def _get_connection():
    conn = sqlite3.connect(
        DB_PATH,
        timeout=10,
    )

    conn.row_factory = sqlite3.Row

    return conn


def _message(
    key: str,
    lang: str = "en",
    **values,
):
    print(
        "[SMS DEBUG] Building message:",
        {
            "key": key,
            "lang": lang,
            "values": values,
        },
    )

    messages = _sms["messages"][key]

    print(
        "[SMS DEBUG] Available languages:",
        list(messages.keys()),
    )

    template = (
        messages.get(lang)
        or messages.get("en")
    )

    print(
        "[SMS DEBUG] Selected template:",
        template,
    )

    response = template.format(
        **values
    )

    print(
        "[SMS DEBUG] Final response:",
        response,
    )

    return response


def _diagnosis_name(
    diagnosis: str,
    lang: str = "en",
):
    names = (
        _sms["diagnosis_names"]
        .get(diagnosis, {})
    )

    print(
        "[SMS DEBUG] Diagnosis name lookup:",
        {
            "diagnosis": diagnosis,
            "requested_lang": lang,
            "available_names": names,
        },
    )

    diagnosis_name = (
        names.get(lang)
        or names.get("en")
        or DIAGNOSES.get(
            diagnosis,
            diagnosis,
        )
    )

    print(
        "[SMS DEBUG] Diagnosis display name:",
        diagnosis_name,
    )

    return diagnosis_name


def _save_diagnosis(
    farmer_id: str,
    diagnosis: str,
):
    row = {
        "farmer_id": farmer_id,
        "date": date.today().isoformat(),
        "diagnosis": diagnosis,
    }

    print(
        "[SMS DEBUG] Saving diagnosis to SQLite:",
        row,
    )

    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO diagnoses (
                farmer_id,
                date,
                diagnosis
            )
            VALUES (?, ?, ?)
            """,
            (
                row["farmer_id"],
                row["date"],
                row["diagnosis"],
            ),
        )

    print(
        "[SMS DEBUG] Diagnosis saved successfully"
    )


def handle_farmer_message(
    phone: str,
    text: str,
) -> str:

    print("\n" + "=" * 60)
    print("[SMS DEBUG] Incoming farmer SMS")
    print("[SMS DEBUG] Phone:", repr(phone))
    print("[SMS DEBUG] Text:", repr(text))

    farmer = find_farmer_by_phone(
        phone
    )

    print(
        "[SMS DEBUG] Farmer lookup result:",
        farmer,
    )

    if farmer:
        print(
            "[SMS DEBUG] Farmer ID:",
            farmer.get("farmer_id"),
        )

        print(
            "[SMS DEBUG] Farmer language field:",
            repr(
                farmer.get("language")
            ),
        )

    else:
        print(
            "[SMS DEBUG] No farmer matched this phone number"
        )

    # Default to Kinyarwanda for the demo.
    if farmer:
        lang = farmer.get("language") or "rw"
    else:
        lang = "rw"

    print(
        "[SMS DEBUG] Selected response language:",
        repr(lang),
    )

    result = _model.classify(
        text
    )

    print(
        "[SMS DEBUG] Classification result:",
        result,
    )

    if not result["sure"]:
        print(
            "[SMS DEBUG] Model is unsure"
        )

        centre = (
            "ikigo cyawe cyo gukusanyirizaho ikawa"
            if lang == "rw"
            else "your washing station"
        )

        return _message(
            "noor_unsure",
            lang=lang,
            centre=centre,
        )

    diagnosis = result["diagnosis"]

    print(
        "[SMS DEBUG] Diagnosis:",
        diagnosis,
    )

    print(
        "[SMS DEBUG] Needs confirmation:",
        diagnosis in NEEDS_CONFIRMATION,
    )

    diagnosis_name = _diagnosis_name(
        diagnosis,
        lang,
    )

    # Do not persist diagnoses that still require
    # a photo / co-op confirmation.
    if diagnosis in NEEDS_CONFIRMATION:
        print(
            "[SMS DEBUG] Not saving yet - "
            "vision confirmation required"
        )

        centre = (
            "ikigo cyawe cyo gukusanyirizaho ikawa"
            if lang == "rw"
            else "your washing station"
        )

        return _message(
            "noor_likely_bring_leaves",
            lang=lang,
            diagnosis=diagnosis_name,
            centre=centre,
        )

    # Save only confident diagnoses that do not
    # require further confirmation.
    if (
        farmer
        and diagnosis
        and diagnosis != "unknown"
    ):
        print(
            "[SMS DEBUG] Diagnosis qualifies for SQLite save"
        )

        _save_diagnosis(
            farmer_id=farmer["farmer_id"],
            diagnosis=diagnosis,
        )

    else:
        print(
            "[SMS DEBUG] Diagnosis NOT saved:",
            {
                "farmer_found": bool(farmer),
                "diagnosis": diagnosis,
            },
        )

    print(
        "[SMS DEBUG] Using no-photo response"
    )

    return _message(
        "noor_likely_no_photo",
        lang=lang,
        diagnosis=diagnosis_name,
        ussd="*384*22426#",
    )