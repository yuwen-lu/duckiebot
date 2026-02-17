# Telegram Claude Bot

A Telegram bot that uses Claude Code in single-shot mode to process messages, running as a Docker container.

## Setup

### 1. Create a Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the prompts to name your bot
3. Copy the bot token BotFather gives you

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and fill in:
- `TELEGRAM_BOT_TOKEN` - the token from BotFather
- `ANTHROPIC_API_KEY` - your Anthropic API key

### 3. Build and Run

```bash
docker compose up --build
```

Run in the background:

```bash
docker compose up --build -d
```

### 4. View Logs

```bash
docker compose logs -f
```

### 5. Stop

```bash
docker compose down
```

## Custom Startup

To use a custom startup script instead of the default polling bot, create `bot-data/startup.sh`. The container will run it instead of the default script on next restart.

## Persistent Storage

The `bot-data/` directory is mounted to `/bot` inside the container. Any files the bot creates (memory, skills, etc.) persist across container restarts.
