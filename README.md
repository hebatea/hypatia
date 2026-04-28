# Hypatia

A daily AI companion for 12-step recovery. Telegram bot that checks in every evening, asks three questions, and responds with a personal AI reflection.

---

## Project structure

```
hypatia/
├── main.py                   # Entrypoint — starts bot + scheduler
├── requirements.txt
├── .env.example
└── app/
    ├── config.py             # All env vars loaded once
    ├── bot.py                # Handler registration
    ├── handlers/
    │   ├── states.py         # State constants (IDLE, IN_CHECKIN_1, etc.)
    │   ├── keyboards.py      # All inline keyboards
    │   ├── onboarding.py     # /start flow
    │   ├── checkin.py        # Core check-in state machine
    │   └── settings.py       # /streak /history /remind /pause /resume
    ├── services/
    │   ├── llm.py            # Anthropic API calls
    │   └── scheduler.py      # APScheduler reminder job
    └── db/
        ├── models.py         # SQLAlchemy ORM models
        ├── engine.py         # Async engine + session factory
        └── repository.py     # All DB queries
```

---

## Local setup

### 1. Prerequisites

- Python 3.11+
- A PostgreSQL database (Supabase free tier recommended)
- A Telegram bot token (from @BotFather)
- An Anthropic API key

### 2. Clone and install

```bash
git clone https://github.com/yourname/hypatia.git
cd hypatia
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```
BOT_TOKEN=your_telegram_bot_token
ANTHROPIC_API_KEY=your_anthropic_key
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname
```

For Supabase, your DATABASE_URL looks like:
```
postgresql+asyncpg://postgres.xxxx:password@aws-0-eu-central-1.pooler.supabase.com:5432/postgres
```

### 4. Run

```bash
python main.py
```

Tables are created automatically on first run. Open Telegram and send `/start` to your bot.

---

## Deploy to Railway

1. Push your code to GitHub (make sure `.env` is in `.gitignore`)
2. Create a new Railway project → Deploy from GitHub repo
3. Add environment variables in Railway dashboard:
   - `BOT_TOKEN`
   - `ANTHROPIC_API_KEY`
   - `DATABASE_URL` (from Supabase)
4. Railway will run `python main.py` automatically

Cost: ~$5/month for the Railway hobby plan.

---

## Bot commands

| Command | Description |
|---|---|
| `/start` | Onboarding — set timezone and reminder time |
| `/checkin` | Start today's check-in |
| `/streak` | View current streak |
| `/history` | Last 5 check-ins |
| `/remind` | Change reminder time |
| `/pause` | Pause daily reminders |
| `/resume` | Re-enable reminders |

---

## Architecture

```
Telegram ──webhook──> Bot process (python-telegram-bot)
                          │
                    State machine
                    (IDLE → IN_CHECKIN_1 → 2 → 3 → AWAITING_LLM → IDLE)
                          │
              ┌───────────┴────────────┐
         LLM service              DB service
      (Anthropic Haiku)       (SQLAlchemy async)
                                       │
                              PostgreSQL (Supabase)

Scheduler (APScheduler, every 5 min)
    └──> find due users ──> LLM ──> send reminder ──> log
```

---

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `BOT_TOKEN` | ✓ | From @BotFather on Telegram |
| `ANTHROPIC_API_KEY` | ✓ | From console.anthropic.com |
| `DATABASE_URL` | ✓ | `postgresql+asyncpg://...` format |
