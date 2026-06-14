#!/usr/bin/env python3
"""Send an SMS via Twilio.

Usage:
    python sms.py "+15555550100" "Hello from Claude!"

Required environment variables:
    TWILIO_ACCOUNT_SID  - Your Twilio Account SID
    TWILIO_AUTH_TOKEN   - Your Twilio Auth Token
    TWILIO_FROM_NUMBER  - Your Twilio phone number (e.g. "+15550001234")
"""

import os
import sys


def send_sms(to: str, body: str) -> str:
    try:
        from twilio.rest import Client
    except ImportError:
        raise SystemExit("Install the Twilio SDK first:  pip install twilio")

    account_sid = os.environ["TWILIO_ACCOUNT_SID"]
    auth_token = os.environ["TWILIO_AUTH_TOKEN"]
    from_number = os.environ["TWILIO_FROM_NUMBER"]

    client = Client(account_sid, auth_token)
    message = client.messages.create(to=to, from_=from_number, body=body)
    return message.sid


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(f"Usage: {sys.argv[0]} <to_number> <message>")

    to_number, text = sys.argv[1], sys.argv[2]
    sid = send_sms(to_number, text)
    print(f"Sent! Message SID: {sid}")
