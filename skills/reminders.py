import json
import os
import time
import uuid
from datetime import datetime, timedelta

_REMINDERS_FILE = os.path.join(os.path.dirname(__file__), "..", "reminders.json")


def _load():
    if os.path.exists(_REMINDERS_FILE):
        try:
            with open(_REMINDERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save(items):
    try:
        with open(_REMINDERS_FILE, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _parse_due(due_str):
    """Parse natural-ish date strings into ISO format."""
    if not due_str:
        return None
    due_lower = due_str.lower().strip()
    now = datetime.now()

    if due_lower == "today":
        return now.strftime("%Y-%m-%d 23:59")
    if due_lower == "tomorrow":
        return (now + timedelta(days=1)).strftime("%Y-%m-%d 09:00")

    for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%d", "%H:%M", "%I:%M %p"]:
        try:
            parsed = datetime.strptime(due_str.strip(), fmt)
            if fmt in ["%H:%M", "%I:%M %p"]:
                parsed = parsed.replace(year=now.year, month=now.month, day=now.day)
                if parsed < now:
                    parsed += timedelta(days=1)
            return parsed.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            continue

    return due_str


def execute(params):
    action = params.get("action", "list").lower()

    if action == "add":
        text = params.get("text", "").strip()
        if not text:
            return "No reminder text provided."
        due = _parse_due(params.get("due", ""))
        priority = params.get("priority", "medium").lower()
        items = _load()
        reminder = {
            "id": str(uuid.uuid4())[:8],
            "text": text,
            "due": due,
            "priority": priority,
            "status": "pending",
            "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        items.append(reminder)
        _save(items)
        due_str = f" (due: {due})" if due else ""
        return f"Reminder added: \"{text}\"{due_str} [{priority}]"

    if action == "list":
        items = _load()
        pending = [r for r in items if r.get("status") == "pending"]
        if not pending:
            return "No pending reminders."
        lines = []
        for r in pending:
            due = f" | due: {r['due']}" if r.get("due") else ""
            lines.append(f"- [{r['id']}] {r['text']}{due} ({r.get('priority', 'medium')})")
        return f"{len(pending)} pending reminders:\n" + "\n".join(lines)

    if action == "complete":
        rid = params.get("id", "").strip()
        text_match = params.get("text", "").strip().lower()
        items = _load()
        for r in items:
            if (rid and r["id"] == rid) or (text_match and text_match in r["text"].lower()):
                r["status"] = "done"
                r["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                _save(items)
                return f"Marked as done: \"{r['text']}\""
        return f"Reminder not found."

    if action == "delete":
        rid = params.get("id", "").strip()
        items = _load()
        new_items = [r for r in items if r["id"] != rid]
        if len(new_items) == len(items):
            return "Reminder not found."
        _save(new_items)
        return "Reminder deleted."

    if action == "check_due":
        items = _load()
        now = datetime.now()
        due_soon = []
        for r in items:
            if r.get("status") != "pending" or not r.get("due"):
                continue
            try:
                due_dt = datetime.strptime(r["due"], "%Y-%m-%d %H:%M")
                if due_dt <= now + timedelta(minutes=30) and due_dt >= now - timedelta(minutes=5):
                    due_soon.append(r)
            except ValueError:
                continue
        if not due_soon:
            return "No reminders due soon."
        lines = [f"- {r['text']} (due: {r['due']})" for r in due_soon]
        return f"{len(due_soon)} reminders due soon:\n" + "\n".join(lines)

    return f"Unknown reminder action: {action}"
