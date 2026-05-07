# JEE Mentorship Forum Bot

This repository contains the Telegram forum management bot in `bot/`.

## Deploy on Render

- Build command: `cd bot && pip install -r requirements.txt`
- Start command: `cd bot && python main.py`
- Set `TELEGRAM_BOT_TOKEN` in Render environment variables
- Set `DB_PATH` to `/data/jee_bot.db` and add a persistent disk for `/data`
