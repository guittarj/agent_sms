#!/usr/bin/env python3
"""Two-way SMS/MMS bridge: Twilio <-> Claude AI.

Incoming texts and photos are forwarded to Claude, which replies via SMS.
Conversation history is kept per phone number so Claude remembers context.

Setup:
    pip install -r requirements.txt
    cp .env.example .env   # fill in credentials
    python server.py

Point your Twilio number's Messaging webhook to:
    https://<your-host>/sms   (HTTP POST)
"""

import base64
import json
import os
from pathlib import Path

import anthropic
import requests
from dotenv import load_dotenv
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

load_dotenv()

app = Flask(__name__)

HISTORY_FILE = Path("conversations.json")
MAX_TURNS = 10          # exchanges (user+assistant pairs) kept per number
MODEL = "claude-sonnet-4-6"
SYSTEM = (
    "You are Claude, a helpful AI assistant reachable via SMS. "
    "Keep replies concise — they're read on a phone. "
    "If you receive an image, describe what you see and answer any question about it."
)


# ── conversation history ──────────────────────────────────────────────────────

def _load() -> dict:
    return json.loads(HISTORY_FILE.read_text()) if HISTORY_FILE.exists() else {}


def _save(data: dict) -> None:
    HISTORY_FILE.write_text(json.dumps(data, indent=2))


def get_history(number: str) -> list:
    return _load().get(number, [])


def append_history(number: str, role: str, content) -> None:
    data = _load()
    turns = data.setdefault(number, [])
    turns.append({"role": role, "content": content})
    data[number] = turns[-(MAX_TURNS * 2):]   # trim oldest pairs
    _save(data)


# ── image fetching ────────────────────────────────────────────────────────────

def fetch_image(url: str) -> tuple[str, str]:
    """Download a Twilio media URL; return (base64_data, mime_type)."""
    auth = (os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
    r = requests.get(url, auth=auth, timeout=15)
    r.raise_for_status()
    mime = r.headers.get("Content-Type", "image/jpeg").split(";")[0]
    return base64.standard_b64encode(r.content).decode(), mime


# ── webhook ───────────────────────────────────────────────────────────────────

@app.route("/sms", methods=["POST"])
def sms_webhook():
    from_number = request.form["From"]
    body = request.form.get("Body", "").strip()
    num_media = int(request.form.get("NumMedia", 0))

    # Build rich content for Claude (includes actual image data)
    content = []
    image_count = 0
    for i in range(num_media):
        mime = request.form.get(f"MediaContentType{i}", "")
        if not mime.startswith("image/"):
            continue
        try:
            data, detected_mime = fetch_image(request.form[f"MediaUrl{i}"])
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": detected_mime, "data": data},
            })
            image_count += 1
        except Exception as e:
            app.logger.warning("Could not fetch media: %s", e)

    if body:
        content.append({"type": "text", "text": body})
    if not content:
        content = [{"type": "text", "text": "(empty message)"}]

    # Build a text-only version for history storage (base64 images are huge)
    stored = []
    if image_count:
        stored.append({"type": "text", "text": f"[{image_count} image(s) attached]"})
    if body:
        stored.append({"type": "text", "text": body})
    if not stored:
        stored = [{"type": "text", "text": "(empty message)"}]

    # Assemble full message list: stored history + current turn with real images
    messages = get_history(from_number) + [{"role": "user", "content": content}]

    ai = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = ai.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM,
        messages=messages,
    )
    reply = response.content[0].text

    append_history(from_number, "user", stored)
    append_history(from_number, "assistant", reply)

    resp = MessagingResponse()
    resp.message(reply)
    return str(resp), 200, {"Content-Type": "text/xml"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
