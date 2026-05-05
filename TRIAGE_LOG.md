# Triage Log

A record of deployment and integration issues encountered during development, along with their root causes and resolutions.

---

| # | Problem | What Happened | How It Was Solved |
|---|---------|---------------|-------------------|
| 1 | **Database Unreachable** | `OSError: [Errno 101] Network is unreachable` — Railway could not establish a connection to Supabase. The bot failed to start because the database was inaccessible. | Switched from the direct Supabase connection URL (port 5432) to the **Session Pooler URL** (`pooler.supabase.com:6543`). Railway's networking requires the pooler endpoint rather than a direct PostgreSQL connection. |
| 2 | **Telegram Conflict Error** | `telegram.error.Conflict: Conflict: terminated by other getUpdates request` — two instances of the bot were running simultaneously, both polling the Telegram API for updates, causing them to conflict. | Restarted the Railway service to terminate all running instances, ensuring only a single bot process was active and polling. |
| 3 | **Anthropic API Connection Error** | `APIConnectionError` — all calls to the LLM were failing at runtime despite the code being correct. The bot could not generate any responses. | Diagnosed the issue as a missing environment variable. Added `ANTHROPIC_API_KEY` to the Railway service's environment variables, which resolved the connection failure immediately. |
