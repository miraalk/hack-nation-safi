from flask import Blueprint, request

from backend.services.farmer_ussd import handle_ussd


ussd_bp = Blueprint("ussd", __name__)


@ussd_bp.post("/webhooks/ussd")
def ussd_webhook():
    session_id = request.form.get("sessionId", "").strip()
    service_code = request.form.get("serviceCode", "").strip()
    phone = request.form.get("phoneNumber", "").strip()
    text = request.form.get("text", "").strip()

    print({
        "session_id": session_id,
        "service_code": service_code,
        "phone": phone,
        "text": text,
    })

    response = handle_ussd(
        session_id=session_id,
        service_code=service_code,
        phone=phone,
        text=text,
    )

    print("USSD response:", response)

    return response