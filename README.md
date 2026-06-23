# farcaster-cleaner

A safe, **local-first** web app to bulk-clean your Farcaster casts via the [Neynar](https://neynar.com) API.

> ⚠️ **WARNING: DELETION IS IRREVERSIBLE.**
> Casts deleted from Farcaster **cannot be restored** by this tool or by Neynar.

## Quick Start

```bash
# 1. Install
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Fill in: NEYNAR_API_KEY, NEYNAR_SIGNER_UUID, FARCASTER_FID

# 3. Run
uvicorn app.main:app --host 127.0.0.1 --port 8132

# 4. Open http://127.0.0.1:8132
```

## Features

- Fetch and preview 1–1000 casts
- Automatic JSON backup before deletion
- Two-step deletion confirmation
- Live progress via Server-Sent Events
- Telegram bot support (polling/webhook)

## Documentation

See `docs/` for detailed documentation.

## License

MIT
