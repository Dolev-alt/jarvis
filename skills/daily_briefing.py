from datetime import datetime


def execute(params):
    """Compile a comprehensive daily briefing from multiple sources."""
    chat = params.get("_chat")
    socketio = params.get("_socketio")
    sections = []

    # 1. Weather
    try:
        from skills.weather import execute as weather_exec
        weather = weather_exec({"city": params.get("city", ""), "_socketio": None})
        if weather and "error" not in weather.lower():
            sections.append(f"WEATHER:\n{weather}")
    except Exception:
        pass

    # 2. Calendar
    try:
        from skills.calendar import execute as cal_exec
        events = cal_exec({"action": "today"})
        if events and "no events" not in events.lower():
            sections.append(f"TODAY'S EVENTS:\n{events}")
        else:
            sections.append("CALENDAR: No events scheduled today.")
    except Exception:
        pass

    # 3. Reminders
    try:
        from skills.reminders import execute as remind_exec
        reminders = remind_exec({"action": "check_due"})
        pending = remind_exec({"action": "list"})
        if reminders and "no reminders" not in reminders.lower():
            sections.append(f"DUE REMINDERS:\n{reminders}")
        elif pending and "no pending" not in pending.lower():
            sections.append(f"PENDING TODOS:\n{pending}")
    except Exception:
        pass

    # 4. News
    try:
        from skills.news import _fetch_news
        articles = _fetch_news("general", count=3)
        if articles:
            headlines = "\n".join([f"- {a['title']}" for a in articles[:3]])
            sections.append(f"TOP NEWS:\n{headlines}")
    except Exception:
        pass

    # 5. System health
    try:
        import subprocess
        batt = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True, timeout=5)
        if batt.stdout:
            sections.append(f"SYSTEM: {batt.stdout.strip().split(chr(10))[-1].strip()}")
    except Exception:
        pass

    if not sections:
        return "Could not compile briefing. Some data sources may be unavailable."

    raw_briefing = "\n\n".join(sections)
    now = datetime.now()
    greeting = "Good morning" if now.hour < 12 else "Good afternoon" if now.hour < 17 else "Good evening"

    if chat:
        try:
            prompt = (
                f"You are JARVIS delivering the {greeting.lower().split()[1]} briefing. "
                f"Time: {now.strftime('%A, %B %d, %I:%M %p')}\n\n"
                f"Raw data:\n{raw_briefing}\n\n"
                f"Deliver this as a natural spoken briefing in 4-6 sentences. "
                f"Start with '{greeting}, Sir.' Cover weather, schedule, reminders, and one interesting headline. "
                f"Be conversational and prioritize what matters most."
            )
            response = chat.send_message(prompt)
            if response and hasattr(response, "text"):
                spoken = response.text.strip()
                if socketio:
                    socketio.emit("new_message", {"sender": "jarvis", "text": f"[Daily Briefing]\n{raw_briefing}"})
                from skills.speak import execute as speak_exec
                speak_exec({"text": spoken, "_socketio": socketio})
                return spoken
        except Exception as e:
            print(f"[daily_briefing] AI briefing failed: {e}")

    return f"{greeting}, Sir. Here's your briefing:\n{raw_briefing}"
