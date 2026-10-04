from flask import Blueprint, request

from backend.services.farmer_messages import handle_farmer_message
from backend.transports.africas_talking import send_sms


sms_bp = Blueprint("sms", __name__)


@sms_bp.post("/webhooks/sms")
def sms_webhook():
    phone = request.form.get("from", "").strip()
    text = request.form.get("text", "").strip()
    message_id = request.form.get("id", "").strip()

    print({
        "phone": phone,
        "text": text,
        "message_id": message_id,
    })

    try:
        reply = handle_farmer_message(
            phone=phone,
            text=text,
        )

        print("FarmFlow reply:", reply)

        result = send_sms(
            phone=phone,
            message=reply,
        )

        print("Africa's Talking response:", result)

    except Exception as exc:
        print("SMS processing failed:", repr(exc))

    return "OK", 200