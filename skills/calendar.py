import os
import json
from datetime import datetime, timedelta

CALENDAR_FILE = "jarvis_calendar.json"


def _load_events():
    if not os.path.exists(CALENDAR_FILE):
        return []
    try:
        with open(CALENDAR_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def _save_events(events):
    with open(CALENDAR_FILE, "w") as f:
        json.dump(events, f, indent=2)


def execute(params):
    action = (params.get("action") or "list").lower().strip()

    if action == "add":
        title = params.get("title")
        date_str = params.get("date")  # YYYY-MM-DD
        time_str = params.get("time", "09:00")  # HH:MM

        if not title or not date_str:
            return "Sir, I need at least a title and a date (YYYY-MM-DD) to schedule an event."

        events = _load_events()
        event = {
            "title": title,
            "date": date_str,
            "time": time_str,
            "created": datetime.now().isoformat(),
        }
        events.append(event)
        _save_events(events)
        return f"Sir, I've added '{title}' to your schedule for {date_str} at {time_str}."

    elif action == "list":
        events = _load_events()
        if not events:
            return "Sir, your calendar is currently clear."

        today = datetime.now().strftime("%Y-%m-%d")
        upcoming = [e for e in events if e["date"] >= today]
        upcoming.sort(key=lambda e: (e["date"], e["time"]))

        if not upcoming:
            return "Sir, you have no upcoming events."

        lines = [f"  - {e['date']} {e['time']}: {e['title']}" for e in upcoming[:10]]
        return f"Sir, here are your upcoming events:\n" + "\n".join(lines)

    elif action == "today":
        events = _load_events()
        today = datetime.now().strftime("%Y-%m-%d")
        todays = [e for e in events if e["date"] == today]
        todays.sort(key=lambda e: e["time"])

        if not todays:
            return "Sir, you have nothing scheduled for today."

        lines = [f"  - {e['time']}: {e['title']}" for e in todays]
        return f"Sir, today's agenda:\n" + "\n".join(lines)

    elif action == "remove":
        title = params.get("title", "").lower()
        if not title:
            return "Sir, which event shall I remove? Please provide the title."

        events = _load_events()
        filtered = [e for e in events if title not in e["title"].lower()]
        removed = len(events) - len(filtered)
        if removed == 0:
            return f"Sir, I couldn't find any event matching '{title}'."
        _save_events(filtered)
        return f"Sir, I've removed {removed} event(s) matching '{title}'."

    return f"Sir, I don't recognise the calendar action '{action}'. Try: add, list, today, or remove."
