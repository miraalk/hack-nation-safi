import os

import requests


AT_USERNAME = os.environ.get("AT_USERNAME", "sandbox")
AT_API_KEY = os.environ["AT_API_KEY"]
AT_SENDER_ID = os.environ.get("AT_SENDER_ID")

AT_BASE_URL = "https://api.sandbox.africastalking.com/version1/messaging"


def send_sms(phone: str, message: str) -> dict:
    phone = phone.strip()

    payload = {
        "username": AT_USERNAME,
        "to": phone,
        "message": message,
    }

    if AT_SENDER_ID:
        payload["from"] = AT_SENDER_ID

    response = requests.post(
        AT_BASE_URL,
        headers={
            "apiKey": AT_API_KEY,
            "Accept": "application/json",
        },
        data=payload,
        timeout=10,
    )

    response.raise_for_status()
    return response.json()