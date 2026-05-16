import json
import os
import time
from datetime import datetime

_NOTES_FILE = os.path.join(os.path.dirname(__file__), "..", "notes.json")


def _load():
    if os.path.exists(_NOTES_FILE):
        try:
            with open(_NOTES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save(notes):
    try:
        with open(_NOTES_FILE, "w", encoding="utf-8") as f:
            json.dump(notes, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def execute(params):
    action = params.get("action", "save").lower()

    if action == "save":
        text = params.get("text", "").strip()
        if not text:
            return "No note text provided."
        tag = params.get("tag", "").strip().lower()
        notes = _load()
        note = {
            "text": text,
            "tag": tag if tag else "general",
            "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        notes.append(note)
        _save(notes)
        tag_info = f" [#{tag}]" if tag else ""
        return f"Note saved{tag_info}: \"{text[:100]}\""

    if action == "search":
        keyword = params.get("keyword", "").strip().lower()
        if not keyword:
            return "No search keyword provided."
        notes = _load()
        matches = [n for n in notes if keyword in n["text"].lower() or keyword in n.get("tag", "").lower()]
        if not matches:
            return f"No notes matching '{keyword}'."
        lines = [f"- [{n['created']}] #{n.get('tag', 'general')}: {n['text'][:100]}" for n in matches[-5:]]
        return f"Found {len(matches)} notes:\n" + "\n".join(lines)

    if action == "list":
        notes = _load()
        count = min(int(params.get("count", 5)), 20)
        if not notes:
            return "No notes saved."
        recent = notes[-count:]
        lines = [f"- [{n['created']}] #{n.get('tag', 'general')}: {n['text'][:100]}" for n in reversed(recent)]
        return f"Last {len(lines)} notes:\n" + "\n".join(lines)

    if action == "read_last":
        notes = _load()
        if not notes:
            return "No notes saved."
        last = notes[-1]
        return f"Last note ({last['created']}, #{last.get('tag', 'general')}): {last['text']}"

    if action == "delete":
        keyword = params.get("keyword", "").strip().lower()
        notes = _load()
        new_notes = [n for n in notes if keyword not in n["text"].lower()]
        deleted = len(notes) - len(new_notes)
        if deleted == 0:
            return f"No notes matching '{keyword}' to delete."
        _save(new_notes)
        return f"Deleted {deleted} note(s) matching '{keyword}'."

    return f"Unknown notes action: {action}"
