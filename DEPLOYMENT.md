# Deployment Guide

## Architecture

```
Railway Service 1: Bot      (python main.py)
Railway Service 2: API      (uvicorn api.main:app)
Vercel:            Frontend (frontend/index.html — static)
Supabase:          Database (shared by both Railway services)
```

---

## 1. Deploy the FastAPI service on Railway

1. In your Railway project, click **New Service → GitHub Repo** and select this repo again (same repo as the bot).
2. In the service settings, set the **Start Command** to:
   ```
   uvicorn api.main:app --host 0.0.0.0 --port $PORT
   ```
3. Add these environment variables (same as the bot, minus `BOT_TOKEN`):
   | Variable | Value |
   |----------|-------|
   | `DATABASE_URL` | Your Supabase Session Pooler URL (`postgresql+asyncpg://...@pooler.supabase.com:6543/postgres`) |
   | `WEB_BASE_URL` | `https://hypatia-web.vercel.app` (or your Vercel URL once deployed) |

4. Railway will assign a public URL like `https://hypatia-api.up.railway.app`. Copy it.

5. Update the `API_BASE` constant in `frontend/index.html` to match that URL:
   ```js
   const API_BASE = "https://hypatia-api.up.railway.app";
   ```

---

## 2. Deploy the frontend on Vercel

1. Go to [vercel.com](https://vercel.com) → **New Project** → import this repo.
2. In the project settings:
   - **Framework Preset:** Other
   - **Root Directory:** `frontend`
   - **Output Directory:** `.` (the directory itself — it's a static file)
3. Click **Deploy**. Vercel will give you a URL like `https://hypatia-web.vercel.app`.
4. Go back to Railway and set `WEB_BASE_URL` to that Vercel URL on the bot service.

---

## 3. Environment variables summary

### Bot service (Railway)
| Variable | Required |
|----------|----------|
| `BOT_TOKEN` | Yes |
| `ANTHROPIC_API_KEY` | Yes |
| `DATABASE_URL` | Yes |
| `WEB_BASE_URL` | Yes — set to your Vercel URL |

### API service (Railway)
| Variable | Required |
|----------|----------|
| `DATABASE_URL` | Yes — same Supabase pooler URL |

---

## 4. How the magic link flow works end-to-end

1. User sends `/myhistory` in Telegram.
2. Bot generates a random token, saves it to `magic_links` table with 24h expiry, replies with the link.
3. User opens the link in a browser → `frontend/index.html` loads.
4. The page reads the token from the URL and calls `GET /history?token=...` on the Railway API.
5. The API validates the token (checks it exists, is not expired, is not used), marks it as used, fetches the user's last 30 check-ins, and returns JSON.
6. The page renders the user's name, streak, and check-in history.
