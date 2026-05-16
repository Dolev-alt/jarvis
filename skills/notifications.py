import os
import platform
import subprocess
import threading
import time


_listener_active = False
_listener_thread = None


def _macos_notification_loop(socketio=None):
    """Polls macOS notification center via osascript for new notifications."""
    global _listener_active
    seen = set()

    while _listener_active:
        try:
            script = '''
            tell application "System Events"
                set _output to ""
                try
                    set _notifs to every notification
                    repeat with n in _notifs
                        set _output to _output & (title of n) & " | " & (subtitle of n) & linefeed
                    end repeat
                end try
                return _output
            end tell
            '''
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=5
            )
            raw = result.stdout.strip()
            if raw:
                for line in raw.splitlines():
                    line = line.strip()
                    if line and line not in seen:
                        seen.add(line)
                        msg = f"Sir, you have a notification: {line}"
                        print(f"[NOTIFICATIONS] {msg}")
                        if socketio:
                            try:
                                socketio.emit("new_message", {"sender": "jarvis", "text": msg})
                            except Exception:
                                pass

            if len(seen) > 200:
                seen = set(list(seen)[-50:])

        except Exception:
            pass

        time.sleep(10)


def execute(params):
    global _listener_active, _listener_thread

    action = (params.get("action") or "start").lower().strip()
    socketio = params.get("_socketio")

    if platform.system() != "Darwin":
        return "Sir, the notification listener is currently only supported on macOS."

    if action == "start":
        if _listener_active:
            return "Sir, I'm already monitoring your notifications."

        _listener_active = True
        _listener_thread = threading.Thread(
            target=_macos_notification_loop,
            args=(socketio,),
            daemon=True,
        )
        _listener_thread.start()
        return "Sir, I'm now monitoring your system notifications."

    elif action == "stop":
        _listener_active = False
        return "Sir, notification monitoring has been suspended."

    return f"Sir, unrecognised notification action '{action}'. Use 'start' or 'stop'."
