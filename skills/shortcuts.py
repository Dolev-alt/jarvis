import subprocess
import json
import os

from safety_manager import safety_manager


def _run_shortcut(name):
    """Run a macOS Shortcut by name."""
    try:
        result = subprocess.run(
            ["shortcuts", "run", name],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            output = result.stdout.strip()
            return f"Shortcut '{name}' completed.{' Output: ' + output if output else ''}"
        return f"Shortcut '{name}' failed: {result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return f"Shortcut '{name}' timed out after 30 seconds."
    except Exception as e:
        return f"Failed to run shortcut: {e}"


def _list_shortcuts():
    """List available macOS Shortcuts."""
    try:
        result = subprocess.run(
            ["shortcuts", "list"],
            capture_output=True, text=True, timeout=10
        )
        shortcuts = [s.strip() for s in result.stdout.strip().split("\n") if s.strip()]
        return shortcuts
    except Exception as e:
        return []


def _schedule_task(command, schedule, label=None):
    """Create a launchd plist for scheduled task."""
    if not label:
        import hashlib
        label = f"com.jarvis.task.{hashlib.md5(command.encode()).hexdigest()[:8]}"

    plist_dir = os.path.expanduser("~/Library/LaunchAgents")
    os.makedirs(plist_dir, exist_ok=True)
    plist_path = os.path.join(plist_dir, f"{label}.plist")

    hour, minute = 9, 0
    if ":" in str(schedule):
        parts = str(schedule).split(":")
        hour, minute = int(parts[0]), int(parts[1])

    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-c</string>
        <string>{command}</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>{hour}</integer>
        <key>Minute</key>
        <integer>{minute}</integer>
    </dict>
</dict>
</plist>"""

    with open(plist_path, "w") as f:
        f.write(plist_content)

    subprocess.run(["launchctl", "load", plist_path], capture_output=True)
    return f"Scheduled task '{label}' at {hour:02d}:{minute:02d} daily. Plist: {plist_path}"


def execute(params):
    action = params.get("action", "run").lower()

    if action == "run":
        name = params.get("name", "").strip()
        if not name:
            return "No shortcut name provided."
        return _run_shortcut(name)

    if action == "list":
        shortcuts = _list_shortcuts()
        if not shortcuts:
            return "No macOS Shortcuts found (or 'shortcuts' CLI not available)."
        lines = [f"- {s}" for s in shortcuts[:20]]
        return f"Available Shortcuts ({len(shortcuts)} total):\n" + "\n".join(lines)

    if action == "schedule":
        command = params.get("command", "").strip()
        schedule = params.get("time", "09:00").strip()
        label = params.get("label", "").strip()
        if not command:
            return "No command provided for scheduling."

        check = safety_manager.validate_command(command, "shell")
        if not check["allowed"]:
            safety_manager.audit_log("SKILL", "shortcuts", {"action": "schedule", "command": command[:200]}, "DENIED", check["reason"])
            return f"error: Scheduled command blocked -- {check['reason']}"

        return _schedule_task(command, schedule, label or None)

    return f"Unknown shortcuts action: {action}. Use: run, list, schedule."
