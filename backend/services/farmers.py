from shared.data import load_farmers


_FARMERS = load_farmers()


def normalize_phone(phone: str) -> str:
    return (
        phone.strip()
        .replace(" ", "")
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
    )


def find_farmer_by_phone(phone: str):
    target = normalize_phone(phone)

    # Africa's Talking sandbox simulator
    #temp mapper
    if target == "+254700000000":
        target = "+250700000001"

    for farmer_id, farmer in _FARMERS.items():
        farmer_phone = normalize_phone(str(farmer.get("phone", "")))

        if farmer_phone == target:
            return {
                "farmer_id": farmer_id,
                **farmer,
            }

    return None

def find_farmer_by_id(farmer_id: str):
    farmer = _FARMERS.get(farmer_id)

    if farmer is None:
        return None

    return {
        "farmer_id": farmer_id,
        **farmer,
    }