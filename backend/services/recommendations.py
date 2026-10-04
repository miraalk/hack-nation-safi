from shared.data import load_diagnoses, load_farmers, load_inputs
from shared.recommend import recommend, bundle_text


def get_latest_diagnosis(farmer_id: str):
    diagnoses = load_diagnoses()
    history = diagnoses.get(farmer_id, [])

    if not history:
        return None

    latest_date, diagnosis = max(history, key=lambda row: row[0])

    return {
        "date": latest_date,
        "diagnosis": diagnosis,
    }


def get_recommended_inputs(
    farmer_id: str,
    credit_limit_rwf: int,
    lang: str = "en",
):
    farmers = load_farmers()
    farmer = farmers.get(farmer_id)

    if farmer is None:
        return None

    latest = get_latest_diagnosis(farmer_id)

    if latest is None:
        return {
            "status": "no_diagnosis",
            "diagnosis": None,
            "items": [],
            "total_rwf": 0,
            "remaining_rwf": credit_limit_rwf,
            "text": "",
        }

    catalogue = load_inputs()

    result = recommend(
        limit_rwf=credit_limit_rwf,
        diagnosis=latest["diagnosis"],
        trees=farmer["trees"],
        catalogue=catalogue,
        lang=lang,
    )

    return {
        **result,
        "diagnosis": latest["diagnosis"],
        "diagnosis_date": latest["date"],
        "text": bundle_text(result) if result["items"] else "",
    }