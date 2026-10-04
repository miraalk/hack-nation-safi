from backend.services.farmers import find_farmer_by_phone
from backend.services.credit import get_credit_summary
from backend.services.recommendations import get_recommended_inputs


def handle_ussd(
    session_id: str,
    service_code: str,
    phone: str,
    text: str,
) -> str:
    farmer = find_farmer_by_phone(phone)

    if farmer is None:
        return "END This phone number is not registered with FarmFlow."

    path = _normalize_path(text)

    # Main menu
    if path == []:
        return _main_menu(farmer)

    # Check credit
    if path == ["1"]:
        return _handle_credit(farmer)

    # Show recommended inputs
    if path == ["2"]:
        return _handle_recommendation(farmer)

    # Confirm recommended inputs
    if path == ["2", "1"]:
        return _handle_input_request(farmer)

    # Order status
    if path == ["3"]:
        return "END You do not have any active FarmFlow orders."

    return "END Invalid selection."


def _normalize_path(text: str) -> list:
    """
    Africa's Talking sends the full USSD history.

    Example:
        1       -> ["1"]
        1*0     -> []
        1*0*1   -> ["1"]
        2*0*2   -> ["2"]
        2*0*1   -> ["1"]

    We treat 0 as a Back button that removes the previous menu choice.
    """
    if not text:
        return []

    path = []

    for step in text.split("*"):
        step = step.strip()

        if not step:
            continue

        if step == "0":
            if path:
                path.pop()
            continue

        path.append(step)

    return path


def _main_menu(farmer: dict) -> str:
    name = farmer.get("name", "Farmer")

    return (
        f"CON Welcome {name}\n"
        "1. Check credit\n"
        "2. Order inputs\n"
        "3. Check order status"
    )


def _handle_credit(farmer: dict) -> str:
    credit = get_credit_summary(farmer["farmer_id"])

    if credit is None:
        return "END We could not calculate your credit limit."

    if credit["status"] == "insufficient_history":
        return (
            "END We do not have enough delivery history to calculate "
            "a credit limit yet. Please speak with cooperative staff."
        )

    return (
        f"CON Your estimated FarmFlow credit limit is "
        f"RWF {credit['limit_rwf']:,}.\n"
        "0. Back"
    )


def _handle_recommendation(farmer: dict) -> str:
    result = _get_farmer_recommendation(farmer)

    if isinstance(result, str):
        return result

    rec = result

    return (
        f"CON Recommended: {rec['text']}\n"
        f"Cost: RWF {rec['total_rwf']:,}\n"
        "1. Request these inputs\n"
        "0. Back"
    )


def _handle_input_request(farmer: dict) -> str:
    result = _get_farmer_recommendation(farmer)

    if isinstance(result, str):
        return result

    rec = result

    # For now this only confirms the USSD flow.
    # Next step: persist an actual pending order.
    return (
        f"END Request received for {rec['text']}.\n"
        f"Total: RWF {rec['total_rwf']:,}.\n"
        "Your cooperative will review the request."
    )


def _get_farmer_recommendation(farmer: dict):
    credit = get_credit_summary(farmer["farmer_id"])

    if credit is None:
        return "END We could not calculate your credit limit."

    if credit["status"] == "insufficient_history":
        return (
            "END We do not have enough delivery history "
            "to recommend inputs on credit yet."
        )

    rec = get_recommended_inputs(
        farmer_id=farmer["farmer_id"],
        credit_limit_rwf=credit["limit_rwf"],
    )

    if rec is None:
        return "END We could not generate an input recommendation."

    if rec["status"] == "no_diagnosis":
        return (
            "END We do not have a recent diagnosis for you. "
            "Please report symptoms by SMS first."
        )

    if rec["status"] == "refer":
        return (
            "END We are not confident enough in the diagnosis "
            "to recommend an input. Please visit the washing station."
        )

    if rec["status"] == "no_treatment":
        return "END Your latest diagnosis does not require treatment."

    if rec["status"] == "no_credit":
        return "END You currently have no available credit for inputs."

    if rec["status"] == "too_low":
        return (
            "END Your available credit is too low for the recommended input."
        )

    return rec