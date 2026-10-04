from backend.services.credit import get_credit_summary
from backend.services.deliveries import record_delivery


def handle_coop_sms(text: str) -> dict:
    text = text.strip()

    if not text:
        return _result(_help_message())

    parts = text.split()
    command = parts[0].upper()

    if command == "HELP":
        return _result(_help_message())

    if command == "DELIVERY":
        return _handle_delivery(parts)

    return _result(
        "Unknown command.\n"
        "Send HELP for available commands."
    )


def _handle_delivery(parts: list) -> dict:
    """
    Supported formats:

    DELIVERY F0001 10.6

    DELIVERY F0001 10.6 0.5 350
    """

    if len(parts) not in (3, 5):
        return _result(
            "Invalid format.\n"
            "Use: DELIVERY F0001 10.6\n"
            "Or: DELIVERY F0001 10.6 0.5 350"
        )

    farmer_id = parts[1].upper()

    try:
        cherry_kg = float(parts[2])

        if len(parts) == 5:
            rejected_kg = float(parts[3])
            price_rwf_per_kg = int(parts[4])
        else:
            rejected_kg = 0.0
            price_rwf_per_kg = 350

        # Calculate credit before recording delivery.
        before = get_credit_summary(farmer_id)

        delivery = record_delivery(
            farmer_id=farmer_id,
            cherry_kg=cherry_kg,
            rejected_kg=rejected_kg,
            price_rwf_per_kg=price_rwf_per_kg,
        )

        # Recalculate after the new delivery.
        after = get_credit_summary(farmer_id)

    except ValueError as exc:
        return _result(f"Could not record delivery: {exc}")

    reply = (
        f"Recorded {delivery['cherry_kg']} kg for {farmer_id}.\n"
        f"Rejected: {delivery['rejected_kg']} kg.\n"
        f"Price: RWF {delivery['price_rwf_per_kg']}/kg."
    )

    before_limit = None
    after_limit = None
    notify_farmer = False

    if (
        before
        and after
        and before["status"] != "insufficient_history"
        and after["status"] != "insufficient_history"
    ):
        before_limit = before["limit_rwf"]
        after_limit = after["limit_rwf"]

        change = after_limit - before_limit

        if change > 0:
            reply += (
                f"\nCredit: RWF {before_limit:,} -> "
                f"RWF {after_limit:,} (+{change:,})."
            )

            notify_farmer = True

        elif change < 0:
            reply += (
                f"\nCredit: RWF {before_limit:,} -> "
                f"RWF {after_limit:,} ({change:,})."
            )

            # Don't notify farmer automatically about decreases for now.
            notify_farmer = False

        else:
            reply += f"\nCredit remains RWF {after_limit:,}."

    return {
        "reply": reply,
        "farmer_id": farmer_id,
        "credit_before": before_limit,
        "credit_after": after_limit,
        "notify_farmer": notify_farmer,
    }


def _result(reply: str) -> dict:
    return {
        "reply": reply,
        "farmer_id": None,
        "credit_before": None,
        "credit_after": None,
        "notify_farmer": False,
    }


def _help_message() -> str:
    return (
        "FarmFlow coop commands:\n"
        "DELIVERY <farmer> <kg>\n"
        "Example: DELIVERY F0001 10.6\n\n"
        "Full format:\n"
        "DELIVERY <farmer> <kg> <rejected_kg> <price>\n"
        "Example: DELIVERY F0001 10.6 0.5 350"
    )