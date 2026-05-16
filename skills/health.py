import json
import os
from datetime import datetime, timedelta

_HEALTH_FILE = os.path.join(os.path.dirname(__file__), "..", "health_data.json")


def _load():
    if os.path.exists(_HEALTH_FILE):
        try:
            with open(_HEALTH_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"water": [], "steps": [], "nutrition": [], "sleep": []}


def _save(data):
    try:
        with open(_HEALTH_FILE, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _today():
    return datetime.now().strftime("%Y-%m-%d")


def _get_today_entries(data, category):
    today = _today()
    return [e for e in data.get(category, []) if e.get("date") == today]


def execute(params):
    action = params.get("action", "status").lower()
    category = params.get("category", "").lower()

    if action == "water" or (action == "log" and category == "water"):
        amount = float(params.get("amount", 1))
        unit = params.get("unit", "glasses")
        data = _load()
        entry = {"date": _today(), "amount": amount, "unit": unit, "time": datetime.now().strftime("%H:%M")}
        data.setdefault("water", []).append(entry)
        _save(data)
        today_total = sum(e["amount"] for e in _get_today_entries(data, "water"))
        goal = float(params.get("goal", 8))
        remaining = max(0, goal - today_total)
        return f"Logged {amount} {unit} of water. Today's total: {today_total:.0f}/{goal:.0f} {unit}. {f'{remaining:.0f} more to go.' if remaining > 0 else 'Goal reached!'}"

    if action == "steps" or (action == "log" and category == "steps"):
        steps = int(params.get("steps", params.get("amount", 0)))
        if steps <= 0:
            data = _load()
            today_steps = sum(e["amount"] for e in _get_today_entries(data, "steps"))
            return f"Steps today: {today_steps:,}"
        data = _load()
        entry = {"date": _today(), "amount": steps, "time": datetime.now().strftime("%H:%M")}
        data.setdefault("steps", []).append(entry)
        _save(data)
        today_total = sum(e["amount"] for e in _get_today_entries(data, "steps"))
        return f"Logged {steps:,} steps. Today's total: {today_total:,}"

    if action == "nutrition" or (action == "log" and category in ["food", "nutrition", "meal"]):
        meal = params.get("meal", params.get("text", "")).strip()
        calories = params.get("calories", "")
        if not meal:
            return "No meal/food specified."
        data = _load()
        entry = {"date": _today(), "meal": meal, "calories": calories, "time": datetime.now().strftime("%H:%M")}
        data.setdefault("nutrition", []).append(entry)
        _save(data)
        today_meals = _get_today_entries(data, "nutrition")
        return f"Logged: {meal}{f' ({calories} cal)' if calories else ''}. Meals today: {len(today_meals)}"

    if action == "sleep":
        hours = params.get("hours", "")
        quality = params.get("quality", "").lower()
        if not hours:
            data = _load()
            recent = [e for e in data.get("sleep", []) if "hours" in e][-7:]
            if recent:
                avg = sum(float(e["hours"]) for e in recent) / len(recent)
                return f"Average sleep (last {len(recent)} days): {avg:.1f} hours"
            return "No sleep data recorded."
        data = _load()
        entry = {"date": _today(), "hours": float(hours), "quality": quality or "normal", "time": datetime.now().strftime("%H:%M")}
        data.setdefault("sleep", []).append(entry)
        _save(data)
        return f"Logged {hours}h sleep ({quality or 'normal'} quality)."

    if action == "status":
        data = _load()
        lines = []
        water_today = sum(e["amount"] for e in _get_today_entries(data, "water"))
        steps_today = sum(e["amount"] for e in _get_today_entries(data, "steps"))
        meals_today = len(_get_today_entries(data, "nutrition"))
        lines.append(f"Water: {water_today:.0f} glasses")
        lines.append(f"Steps: {steps_today:,}")
        lines.append(f"Meals logged: {meals_today}")
        recent_sleep = [e for e in data.get("sleep", []) if "hours" in e]
        if recent_sleep:
            lines.append(f"Last sleep: {recent_sleep[-1]['hours']}h ({recent_sleep[-1].get('quality', 'normal')})")
        return f"Health status for {_today()}:\n" + "\n".join(lines)

    if action == "history":
        days = int(params.get("days", 7))
        cat = category or "water"
        data = _load()
        entries = data.get(cat, [])
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        recent = [e for e in entries if e.get("date", "") >= cutoff]
        if not recent:
            return f"No {cat} data in the last {days} days."
        by_day = {}
        for e in recent:
            d = e.get("date", "unknown")
            by_day.setdefault(d, []).append(e)
        lines = []
        for day, day_entries in sorted(by_day.items()):
            if cat == "water":
                total = sum(e.get("amount", 0) for e in day_entries)
                lines.append(f"- {day}: {total:.0f} glasses")
            elif cat == "steps":
                total = sum(e.get("amount", 0) for e in day_entries)
                lines.append(f"- {day}: {total:,} steps")
            else:
                lines.append(f"- {day}: {len(day_entries)} entries")
        return f"{cat.title()} history ({days} days):\n" + "\n".join(lines)

    return f"Unknown health action: {action}. Use: water, steps, nutrition, sleep, status, history."
