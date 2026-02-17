#!/usr/bin/env bash
set -e

if [ -f /bot/startup.sh ]; then
    echo "Found /bot/startup.sh, running it..."
    exec bash /bot/startup.sh
else
    echo "No startup.sh found, running default polling script..."
    exec python3 /app/default_poll.py
fi
