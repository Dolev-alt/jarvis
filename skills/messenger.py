import subprocess
import os


def _send_imessage(recipient, message):
    escaped_msg = message.replace('"', '\\"')
    script = f'''
    tell application "Messages"
        set targetService to 1st account whose service type = iMessage
        set targetBuddy to participant "{recipient}" of targetService
        send "{escaped_msg}" to targetBuddy
    end tell
    '''
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            return f"iMessage sent to {recipient}."
        return f"iMessage failed: {result.stderr.strip()}"
    except Exception as e:
        return f"iMessage error: {e}"


def _send_telegram(chat_id, message, bot_token=None):
    token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        return "Telegram bot token not configured. Set TELEGRAM_BOT_TOKEN in .env"

    try:
        import urllib.request
        import ssl
        import json
        ctx = ssl.create_default_context()

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = json.dumps({"chat_id": chat_id, "text": message}).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        if result.get("ok"):
            return f"Telegram message sent to {chat_id}."
        return f"Telegram error: {result.get('description', 'unknown')}"
    except Exception as e:
        return f"Telegram failed: {e}"


def _send_discord(webhook_url, message):
    if not webhook_url:
        webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "")
    if not webhook_url:
        return "Discord webhook URL not configured. Set DISCORD_WEBHOOK_URL in .env"

    try:
        import urllib.request
        import ssl
        import json
        ctx = ssl.create_default_context()

        data = json.dumps({"content": message}).encode("utf-8")
        req = urllib.request.Request(webhook_url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            if resp.status in [200, 204]:
                return "Discord message sent."
        return "Discord message may not have sent."
    except Exception as e:
        return f"Discord failed: {e}"


def _read_imessages(contact=None, count=5):
    script = '''
    tell application "Messages"
        set recentChats to {}
        repeat with c in chats
            set chatName to name of c
            set msgs to messages of c
            if (count of msgs) > 0 then
                set lastMsg to item 1 of msgs
                set msgText to text of lastMsg
                set msgSender to sender of lastMsg
                copy (chatName & ": " & msgText) to end of recentChats
            end if
            if (count of recentChats) >= ''' + str(count) + ''' then exit repeat
        end repeat
        set output to ""
        repeat with r in recentChats
            set output to output & r & linefeed
        end repeat
        return output
    end tell
    '''
    try:
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=15)
        if result.stdout.strip():
            return f"Recent messages:\n{result.stdout.strip()}"
        return "No recent messages found."
    except Exception as e:
        return f"Could not read messages: {e}"


def execute(params):
    platform = params.get("platform", "imessage").lower()
    action = params.get("action", "send").lower()
    recipient = params.get("recipient", "").strip()
    message = params.get("message", "").strip()

    if action == "send":
        if not message:
            return "No message to send."

        if platform == "imessage":
            if not recipient:
                return "No recipient specified for iMessage."
            return _send_imessage(recipient, message)

        if platform == "telegram":
            chat_id = params.get("chat_id", recipient).strip()
            if not chat_id:
                return "No chat_id specified for Telegram."
            return _send_telegram(chat_id, message)

        if platform == "discord":
            webhook = params.get("webhook", "").strip()
            return _send_discord(webhook, message)

        return f"Unknown platform: {platform}. Supported: imessage, telegram, discord."

    if action == "read":
        if platform == "imessage":
            count = int(params.get("count", 5))
            return _read_imessages(recipient, count)
        return f"Reading messages not yet supported for {platform}."

    return f"Unknown messenger action: {action}. Use: send, read."
