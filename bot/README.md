# JEE Mentorship Forum Bot

A production-ready Telegram bot for JEE mentorship groups that use forum topics. It automatically tracks student activity across multiple groups and sends daily 3 AM inactivity alerts.

## Features

- Auto-detects forum topics by keyword matching
- Tracks 7 required categories per student per day
- Sends daily 3 AM alerts (IST) to announcement topics
- Supports multiple groups simultaneously
- SQLite database with WAL mode for reliability
- Admin commands: `/report`, `/user`, `/rule`

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

Topics with `announcement` or `announce` in the name are **ignored** for tracking (but used for sending alerts).

## Alert Levels (3 AM daily)

| Score | Alert |
|---|---|
| 0/7 | 🔴 HIGH ALERT |
| 1–3/7 | 🟠 MID ALERT |
| 4–6/7 | 🟡 LOW ALERT |
| 7/7 | ✅ No alert |

## Admin Commands

| Command | Where | Description |
|---|---|---|
| `/report` | Any topic | 7-day activity report for all members |
| `/user @username` | Any topic | Detailed stats for one student |
| `/rule` | Any topic | Show all rules and how alerts work |

## Setup

### 1. Create a bot via @BotFather
- Enable **Group Privacy OFF** (so the bot reads all messages)
- Enable **Allow Groups** ON

### 2. Add bot to your Telegram group
- Add the bot as an **admin** with "Post Messages" permission
- The group **must have Topics enabled** (Supergroup → Topics ON)

### 3. How topic detection works
- When someone sends a message in a topic, the bot reads `message_thread_id`
- The bot looks up or registers the topic name the first time it sees a message from it
- **Important:** Send at least one message in each topic after adding the bot so it can register the topic names
- The announcement topic must also receive a message so the bot registers it for sending alerts

## Local Development

```bash
cp .env.example .env
# Edit .env and set TELEGRAM_BOT_TOKEN
pip install -r requirements.txt
python main.py
```

## Deploy to Railway

### Step 1: Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

### Step 2: Create Railway project
1. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
2. Select your repo
3. Railway auto-detects Python via `railway.toml`

### Step 3: Set environment variables on Railway
In your Railway project → Variables tab:
```
TELEGRAM_BOT_TOKEN = your_token_here
DB_PATH = /data/jee_bot.db
```

### Step 4: Add a Volume for persistent SQLite storage
1. Railway project → Add → Volume
2. Mount path: `/data`
3. This ensures the database survives restarts

### Step 5: Deploy
Railway will build and start the bot automatically. The bot runs as a `worker` (no HTTP port needed).

## Important Notes

- The bot needs **admin rights** in the group to post alerts
- Topic detection is automatic — no manual config needed
- Each group's announcement topic is auto-registered when the bot first sees a message in it
- The bot handles multiple groups simultaneously with no extra config
- Database is reset-safe: all state is in SQLite so restarts are seamless
