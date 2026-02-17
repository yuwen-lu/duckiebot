import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
API_BASE = f"https://api.telegram.org/bot{TOKEN}"


def api_call(method, params=None):
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
    # Telegram limits messages to 4096 chars
    max_len = 4096
    for i in range(0, len(text), max_len):
        chunk = text[i : i + max_len]
        api_call("sendMessage", {"chat_id": chat_id, "text": chunk})


def run_claude(prompt):
    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=120,
            cwd="/bot",
        )
        output = result.stdout.strip()
        if not output:
            output = result.stderr.strip() or "No response from Claude."
        return output
    except subprocess.TimeoutExpired:
        return "Claude timed out after 120 seconds."
    except Exception as e:
        return f"Error running Claude: {e}"


def main():
    if not TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN is not set.", file=sys.stderr)
        sys.exit(1)

    print("Bot started. Polling for updates...")
    offset = 0

    while True:
        try:
            params = {"timeout": 30, "allowed_updates": ["message"]}
            if offset:
                params["offset"] = offset

            response = api_call("getUpdates", params)

            if not response.get("ok"):
                print(f"API error: {response}", file=sys.stderr)
                continue

            for update in response.get("result", []):
                offset = update["update_id"] + 1
                message = update.get("message", {})
                text = message.get("text", "")
                chat_id = message.get("chat", {}).get("id")

                if not text or not chat_id:
                    continue

                print(f"Received from {chat_id}: {text}")

                reply = run_claude(text)
                send_message(chat_id, reply)
                print(f"Replied to {chat_id}")

        except urllib.error.URLError as e:
            print(f"Network error: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Unexpected error: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
