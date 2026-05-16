import json
import os
import time

_CLIPBOARD_FILE = os.path.join(os.path.dirname(__file__), "..", "clipboard_history.json")
_MAX_ITEMS = 100


def _load_history():
    if os.path.exists(_CLIPBOARD_FILE):
        try:
            with open(_CLIPBOARD_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_history(history):
    try:
        with open(_CLIPBOARD_FILE, "w", encoding="utf-8") as f:
            json.dump(history[-_MAX_ITEMS:], f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _get_clipboard():
    try:
        import subprocess
        result = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=5)
        return result.stdout.strip()
    except Exception:
        return ""


def _set_clipboard(text):
    try:
        import subprocess
        proc = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        proc.communicate(text.encode("utf-8"))
    except Exception:
        pass


def execute(params):
    action = params.get("action", "save").lower()

    if action == "save":
        content = _get_clipboard()
        if not content:
            return "Clipboard is empty."
        history = _load_history()
        entry = {"text": content[:2000], "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}
        history.append(entry)
        _save_history(history)
        return f"Saved to clipboard history ({len(history)} items total). Content: {content[:100]}..."

    if action == "history":
        history = _load_history()
        if not history:
            return "Clipboard history is empty."
        count = min(int(params.get("count", 5)), 20)
        recent = history[-count:]
        lines = [f"{i+1}. [{e['timestamp']}] {e['text'][:80]}..." for i, e in enumerate(reversed(recent))]
        return f"Last {len(lines)} clipboard items:\n" + "\n".join(lines)

    if action == "paste":
        index = int(params.get("index", 1)) - 1
        history = _load_history()
        if not history:
            return "Clipboard history is empty."
        if index < 0 or index >= len(history):
            return f"Invalid index. You have {len(history)} items."
        item = history[-(index + 1)]
        _set_clipboard(item["text"])
        return f"Pasted item {index + 1} to clipboard: {item['text'][:100]}..."

    if action == "search":
        keyword = params.get("keyword", "").lower()
        if not keyword:
            return "No search keyword provided."
        history = _load_history()
        matches = [e for e in history if keyword in e["text"].lower()]
        if not matches:
            return f"No clipboard items matching '{keyword}'."
        lines = [f"- [{e['timestamp']}] {e['text'][:80]}..." for e in matches[-5:]]
        return f"Found {len(matches)} matching items:\n" + "\n".join(lines)

    if action == "clear":
        _save_history([])
        return "Clipboard history cleared."

    return f"Unknown clipboard action: {action}"
