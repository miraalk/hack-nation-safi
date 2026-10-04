from flask import Blueprint, request

from backend.services.coop_sms import handle_coop_sms
from backend.services.farmer_messages import handle_farmer_message
from backend.services.farmers import find_farmer_by_id
from backend.transports.africas_talking import (
    AT_COOP_SENDER_ID,
    AT_SENDER_ID,
    send_sms,
)


sms_bp = Blueprint("sms", __name__)


@sms_bp.post("/webhooks/sms")
def sms_webhook():
    phone = request.form.get("from", "").strip()
    shortcode = request.form.get("to", "").strip()
    text = request.form.get("text", "").strip()
    message_id = request.form.get("id", "").strip()

    print({
        "phone": phone,
        "shortcode": shortcode,
        "text": text,
        "message_id": message_id,
    })

    try:
        # -------------------------------------------------
        # CO-OP SMS
        # -------------------------------------------------

        if shortcode == AT_COOP_SENDER_ID:
            result = handle_coop_sms(text)

            # Reply to cooperative staff.
            send_sms(
                phone=phone,
                message=result["reply"],
                sender_id=AT_COOP_SENDER_ID,
            )

            print("Coop SMS reply:", result["reply"])

            # Notify farmer if their credit increased.
            if result["notify_farmer"]:
                farmer = find_farmer_by_id(
                    result["farmer_id"]
                )

                if farmer and farmer.get("phone"):
                    farmer_message = (
                        "FarmFlow: your available input credit "
                        f"increased from RWF "
                        f"{result['credit_before']:,} to RWF "
                        f"{result['credit_after']:,} after your "
                        "latest delivery."
                    )

                    # Sandbox override.
                    farmer_phone = "+254700000000"

                    farmer_result = send_sms(
                        phone=farmer_phone,
                        message=farmer_message,
                        sender_id=AT_SENDER_ID,
                    )

                    print(
                        "Farmer credit notification:",
                        farmer_message,
                    )

                    print(
                        "Africa's Talking farmer response:",
                        farmer_result,
                    )

            return "OK", 200

        # -------------------------------------------------
        # FARMER SMS
        # -------------------------------------------------

        if shortcode == AT_SENDER_ID:
            reply = handle_farmer_message(
                phone=phone,
                text=text,
            )

            result = send_sms(
                phone=phone,
                message=reply,
                sender_id=AT_SENDER_ID,
            )

            print("Farmer SMS reply:", reply)
            print("Africa's Talking response:", result)

            return "OK", 200

        # -------------------------------------------------
        # UNKNOWN SHORTCODE
        # -------------------------------------------------

        print("Unknown SMS shortcode:", shortcode)
        return "OK", 200

    except Exception as exc:
        print("SMS processing failed:", repr(exc))
        return "OK", 200