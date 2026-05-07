# JEE Mentorship Forum Bot

A production-ready Telegram bot for JEE mentorship groups that use forum topics. Automatically tracks student activity across multiple groups and sends daily 3 AM inactivity alerts.

---

## Features

- Auto-detects forum topics by keyword matching (no hardcoded IDs)
- Tracks 7 required categories per student per day
- Sends daily 3 AM IST alerts to announcement topics
- Supports unlimited groups simultaneously — zero config per group
- SQLite database with WAL mode for reliability
- Admin commands: `/report`, `/user @username`, `/rule`

---

## Topic Categories Detected

| Category | Keyword in topic name |
|---|---|
| TARGET | `target` |
| SCREEN_TIME | `screen` |
| STUDY_HOURS | `study` |
| TOTAL_TIME_WASTE | `waste` |
| REVISION | `revision` |
| QUESTIONS_SOLVED | `question` |
| TARGET_COMPLETION | `completion` |

Topics containing `announcement` or `announce` are **ignored for tracking** but used to **send alerts**.

---

## Alert Levels (3 AM daily, last 24 hours)

| Score | Alert |
|---|---|
| 0/7 | 🔴 HIGH ALERT — has not updated any required topic today. |
| 1–3/7 | 🟠 MID ALERT — has low activity today. |
| 4–6/7 | 🟡 LOW ALERT — missed some updates today. |
| 7/7 | ✅ No alert sent |

---

## Admin Commands

| Command | Description |
|---|---|
| `/report` | 7-day activity report for all members |
| `/user @username` | Detailed 7-day stats for one student |
| `/rule` | Show all rules and how alerts work |

Run these from **any topic** inside the group (admins only).

---

## How Topic Detection Works

1. The bot listens for `message_thread_id` on every message
2. When a topic is first seen, it registers the topic name in the database
3. Topic name is matched against keywords (case-insensitive)
4. **Important:** Send at least one message in each topic after adding the bot so it can register the topic names
5. The announcement topic is auto-registered when someone sends a message there

---

## Deploy to Railway (Step-by-Step)

### Step 1 — Create a GitHub repository

Go to [github.com/new](https://github.com/new), create a **private** repo (e.g. `jee-mentor-bot`).

### Step 2 — Push the bot folder to GitHub

```bash
cd bot                          # this folder only, not the whole workspace
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/jee-mentor-bot.git
git push -u origin main
```

### Step 3 — Create a Railway project

1. Go to [railway.app](https://railway.app) → **New Project**
2. Choose **Deploy from GitHub repo**
3. Authorise Railway to access your GitHub account
4. Select `jee-mentor-bot`
5. Railway auto-detects Python via `nixpacks.toml`

### Step 4 — Add environment variables on Railway

In your Railway project → **Variables** tab, add:

| Key | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | your bot token from @BotFather |
| `DB_PATH` | `/data/jee_bot.db` |

### Step 5 — Add a Volume for persistent SQLite storage

1. Railway project → **+ New** → **Volume**
2. Attach it to your service
3. Set mount path: `/data`

This ensures the database survives redeploys and restarts.

### Step 6 — Deploy

Click **Deploy**. Railway builds and starts the bot automatically.
The bot runs as a background worker — no HTTP port needed.

---

## Bot Setup on Telegram

### 1. Configure the bot via @BotFather
- `/setprivacy` → **Disable** (so the bot can read all group messages)
- `/setjoingroups` → **Enable**

### 2. Make the group a Supergroup with Topics
- Group Settings → **Topics** → Enable

### 3. Add the bot to your group
- Add as **Admin** with these permissions:
  - Read Messages ✅
  - Post Messages ✅ (to send alerts)
  - Delete Messages ❌ (not needed)

### 4. Send one message in each topic
After adding the bot, send a message in each topic (including the announcement topic) so the bot can register them. After that, tracking is fully automatic.

---

## File Structure

```
bot/
├── main.py          # Entry point, bot setup, handlers registration
├── config.py        # All configurable constants
├── database.py      # SQLite schema + all DB operations
├── handlers.py      # Message handlers + command handlers
├── scheduler.py     # APScheduler — 3 AM daily alert job
├── requirements.txt # Python dependencies
├── nixpacks.toml    # Railway build config
├── railway.toml     # Railway deploy config
├── Procfile         # Fallback process definition
├── runtime.txt      # Python version hint
├── .env.example     # Local dev template
└── .gitignore
```
