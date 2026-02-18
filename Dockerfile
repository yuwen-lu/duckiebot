FROM node:20-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends python3 python3-pip python3-venv curl git jq wget vim tree sudo && \
    rm -rf /var/lib/apt/lists/*

RUN npm install -g @anthropic-ai/claude-code

RUN useradd -m -s /bin/bash duckie && \
    echo "duckie ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/duckie

RUN mkdir -p /bot /app && chown duckie:duckie /bot /app

COPY entrypoint.sh /app/entrypoint.sh
COPY default_poll.py /app/default_poll.py
COPY poll.py /app/poll.py

RUN chmod +x /app/entrypoint.sh

USER duckie
WORKDIR /bot

CMD ["/app/entrypoint.sh"]
