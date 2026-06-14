# agent_sms — Personal SMS-to-Claude Assistant

A personal text-message bridge between [Twilio](https://www.twilio.com/) and the
[Claude API](https://docs.anthropic.com/). Text your Twilio number and Claude
texts you back — over SMS or MMS, with per-conversation memory and image
understanding.

## Features

- **Two-way SMS/MMS** — receive texts (and photos) and reply automatically via Twilio.
- **Image understanding** — incoming MMS photos are forwarded to Claude, which can describe them or answer questions about them.
- **Conversational memory** — history is kept per phone number (last 10 exchanges) so Claude remembers context across messages.
- **One-shot sender** — `sms.py` sends a single outbound text from the command line.

## Components

| File | Purpose |
|------|---------|
| `server.py` | Flask webhook (`POST /sms`) that bridges incoming Twilio messages to Claude and replies via TwiML. |
| `sms.py` | Standalone CLI script to send a single SMS. |
| `.env.example` | Template for required credentials. |

## Requirements

- Python 3.10+
- A Twilio account with an SMS-capable phone number
- An Anthropic API key

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env      # then fill in your credentials
```

Set the following in `.env`:

| Variable | Description |
|----------|-------------|
| `TWILIO_ACCOUNT_SID` | Your Twilio Account SID |
| `TWILIO_AUTH_TOKEN` | Your Twilio Auth Token |
| `TWILIO_FROM_NUMBER` | Your Twilio phone number, e.g. `+15550001234` |
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `PORT` | Port for the webhook server (default `5000`) |

## Usage

### Run the two-way bridge

```bash
python server.py
```

Then point your Twilio number's **Messaging** webhook to your server's public URL:

```
https://<your-host>/sms      (HTTP POST)
```

For local development, expose the port with a tunnel (e.g. `ngrok http 5000`)
and use the resulting HTTPS URL.

Now text your Twilio number — Claude will reply, remembering the conversation
and understanding any photos you send.

### Send a one-off text

```bash
python sms.py "+15555550100" "Hello from Claude!"
```

## Deployment

The webhook needs a public HTTPS URL. Two common options:

### Local (testing) — ngrok

```bash
python server.py            # runs on :5000
ngrok http 5000            # gives you an https://… URL
```

Point the Twilio number's Messaging webhook at `https://<ngrok-id>.ngrok.io/sms`.

### Hosted — Render / Railway / Heroku / Docker

A `Procfile` and `Dockerfile` are included; both start the app with gunicorn
(single worker, so the file-based conversation store stays consistent).

```bash
# Docker
docker build -t agent_sms .
docker run -p 5000:5000 --env-file .env agent_sms
```

On a PaaS, set the same environment variables (`TWILIO_*`, `ANTHROPIC_API_KEY`)
in the dashboard — `PORT` is supplied by the platform — then point the Twilio
webhook at `https://<your-app>/sms`.

> Note: `conversations.json` is local to the container. On platforms with
> ephemeral disks it resets on redeploy; attach a persistent volume if you want
> history to survive restarts.

## How it works

Incoming messages hit `POST /sms`. The server downloads any image attachments
from Twilio, assembles the new turn plus stored history into a Claude API call
(`claude-sonnet-4-6`), and returns the reply as TwiML so Twilio sends it back
as an SMS. Conversation history is stored locally in `conversations.json`
(git-ignored); base64 image data is never persisted — only a placeholder is
stored in history.

## Privacy & registration

This is a personal-use service. The privacy policy and terms required for
A2P 10DLC / SMS number registration live in [TERMS.md](TERMS.md).
