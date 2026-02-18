import json
import os
import subprocess
import sys
import threading
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
API_BASE = f"https://api.telegram.org/bot{TOKEN}"
STATE_FILE = "/bot/state.json"
MEMORY_FILE = "/bot/memory.md"
SESSION_TIMEOUT = 300  # 5 minutes

# Per-chat session tracking: {chat_id: {"session_id": str, "last_active": float}}
sessions = {}


def telegram_api(method, params=None):
    url = f"{API_BASE}/{method}"
    if params:
        data = json.dumps(params).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}
        )
    else:
        req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def send_message(chat_id, text):
    max_len = 4096
    if not text:
        text = "(empty response)"
    for i in range(0, len(text), max_len):
        chunk = text[i : i + max_len]
        telegram_api("sendMessage", {"chat_id": chat_id, "text": chunk})


def load_state():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"offset": 0}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def get_or_create_session(chat_id):
    """Get existing session or create a new one. Returns (session_id, is_new)."""
    now = time.time()
    if chat_id in sessions:
        info = sessions[chat_id]
        elapsed = now - info["last_active"]
        if elapsed < SESSION_TIMEOUT:
            info["last_active"] = now
            return info["session_id"], False
        else:
            # Session expired — summarize before starting new one
            expire_session(chat_id, info["session_id"])

    session_id = str(uuid.uuid4())
    sessions[chat_id] = {"session_id": session_id, "last_active": now}
    return session_id, True


def expire_session(chat_id, session_id):
    """Ask Claude to summarize the expired session and append to memory (in background)."""
    def _summarize():
        print(f"Session {session_id[:8]} expired for chat {chat_id}, summarizing...", flush=True)
        try:
            result = subprocess.run(
                [
                    "claude", "-p",
                    "Summarize our conversation so far in 2-3 concise bullet points. "
                    "Focus on key decisions, facts learned, and any pending tasks. "
                    "Output ONLY the bullet points, nothing else.",
                    "--model", "claude-sonnet-4-6",
                    "--resume", session_id,
                ],
                capture_output=True,
                text=True,
                timeout=120,
                cwd="/bot",
            )
            summary = result.stdout.strip()
            if summary:
                timestamp = time.strftime("%Y-%m-%d %H:%M")
                entry = f"\n\n## Session {timestamp}\n{summary}\n"
                with open(MEMORY_FILE, "a") as f:
                    f.write(entry)
                print(f"Saved session summary to memory.md", flush=True)
        except Exception as e:
            print(f"Failed to summarize session: {e}", file=sys.stderr, flush=True)

    threading.Thread(target=_summarize, daemon=True).start()


def check_expired_sessions():
    """Check all sessions for expiry."""
    now = time.time()
    expired = []
    for chat_id, info in sessions.items():
        if now - info["last_active"] >= SESSION_TIMEOUT:
            expired.append((chat_id, info["session_id"]))
    for chat_id, session_id in expired:
        expire_session(chat_id, session_id)
        del sessions[chat_id]


def run_claude(prompt, session_id, is_new_session):
    """Run claude with session continuity."""
    cmd = [
        "claude", "-p", prompt,
        "--model", "claude-sonnet-4-6",
        "--dangerously-skip-permissions",
    ]

    if is_new_session:
        cmd.extend(["--session-id", session_id])
    else:
        cmd.extend(["--resume", session_id])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd="/bot",
        )
        output = result.stdout.strip()
        if not output:
            output = result.stderr.strip() or "No response from Claude."
        return output
    except subprocess.TimeoutExpired:
        return None
    except Exception:
        return None


def main():
    if not TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN is not set.", file=sys.stderr)
        sys.exit(1)

    print("Bot started. Polling for updates...", flush=True)
    state = load_state()

    while True:
        try:
            # Check for expired sessions on each poll cycle
            check_expired_sessions()

            params = {"timeout": 30, "allowed_updates": ["message"]}
            if state["offset"]:
                params["offset"] = state["offset"]

            response = telegram_api("getUpdates", params)

            if not response.get("ok"):
                print(f"API error: {response}", file=sys.stderr, flush=True)
                time.sleep(10)
                continue

            for update in response.get("result", []):
                state["offset"] = update["update_id"] + 1
                save_state(state)

                message = update.get("message", {})
                text = message.get("text", "")
                chat_id = message.get("chat", {}).get("id")

                if not text or not chat_id:
                    continue

                print(f"Received from {chat_id}: {text}", flush=True)

                session_id, is_new = get_or_create_session(chat_id)
                if is_new:
                    print(f"New session {session_id[:8]} for chat {chat_id}", flush=True)

                reply = run_claude(text, session_id, is_new)

                if reply is None:
                    send_message(chat_id, "Something went wrong, try again.")
                else:
                    send_message(chat_id, reply)

                print(f"Replied to {chat_id}", flush=True)

        except (urllib.error.URLError, OSError) as e:
            print(f"Network error: {e}", file=sys.stderr, flush=True)
            time.sleep(10)
        except Exception as e:
            print(f"Unexpected error: {e}", file=sys.stderr, flush=True)
            time.sleep(10)


if __name__ == "__main__":
    main()
