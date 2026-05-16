import os


SKILL_REGISTRY = {
    "speak": {
        "desc": "Speak out loud to the user.",
        "params": {"text": "string"},
        "required": ["text"],
        "risk": 0
    },
    "web_search": {
        "desc": "Search the internet for live information using DuckDuckGo. Returns snippets and speaks a summary.",
        "params": {"query": "string"},
        "required": ["query"],
        "risk": 0
    },
    "smart_action": {
        "desc": "Run ANY command on macOS dynamically. Use type='osascript' for AppleScript (control apps), type='shell' for terminal commands, type='open' for launching apps/URLs. This is your most flexible tool — use it when no specific skill exists.",
        "params": {"type": "string (osascript|shell|open)", "command": "string"},
        "required": ["command"],
        "risk": 0
    },
    "open_app": {
        "desc": "Open a local application or file.",
        "params": {"text": "string (app name or alias)"},
        "risk": 0
    },
    "email_sender": {
        "desc": "Send an email in the background without opening the UI. Highly preferred for sending messages.",
        "params": {"to": "string", "subject": "string", "body": "string"},
        "risk": 0
    },
    "vision": {
        "desc": "Look at the screen or open live camera preview. Use source='camera' to show live webcam feed on HUD (user clicks Capture), default is screen.",
        "params": {},
        "risk": 0
    },
    "camera": {
        "desc": "Capture a photo from the Mac's built-in webcam.",
        "params": {},
        "risk": 0
    },
    "generate_visual": {
        "desc": "Generate a visual and display it on the HUD. Types: 'svg' for standalone blueprint, 'overlay' to show wireframe ON the room photo (AR-style, also auto-generates realistic composite), 'composite' for AI realistic rendering only, 'mermaid' for diagrams, 'html' for other visuals, 'assembly_3d' for live 3D assembly animation (parts fly in and build the object Iron Man style — best for furniture, structures, machines, robots). Use 'overlay' when the user wants to see how something looks IN their room. Optional 'context' for spatial placement info.",
        "params": {"prompt": "string (what to generate — include exact dimensions)", "type": "string (svg|overlay|composite|mermaid|html|assembly_3d)"},
        "risk": 0
    },
    "shell_execution": {
        "desc": "Execute a terminal command. Use for system diagnostics or file operations.",
        "params": {"command": "string"},
        "risk": 1
    },
    "learn": {
        "desc": "Store a new personal fact or preference about the user into long-term memory.",
        "params": {"key": "string", "fact": "string"},
        "risk": 0
    },
    "recall_memory": {
        "desc": "Retrieve previously learned facts by key or topic.",
        "params": {"query": "string"},
        "risk": 0
    },
    "system_monitor": {
        "desc": "Check current CPU, RAM, and Battery status.",
        "params": {},
        "risk": 0
    },
    "timer": {
        "desc": "Set a countdown timer.",
        "params": {"minutes": "integer", "label": "string"},
        "risk": 0
    },
    "volume": {
        "desc": "Control system audio volume.",
        "params": {"action": "string ('up', 'down', 'mute')"},
        "risk": 0
    },
    "list_files": {
        "desc": "List the contents of a directory.",
        "params": {"path": "string"},
        "risk": 0
    },
    "file_management": {
        "desc": "Create, delete, or rename files and directories.",
        "params": {"action": "string", "path": "string", "target": "string", "content": "string"},
        "risk": 1
    },
    "research": {
        "desc": "Deep research into a topic using a recursive autonomous agent.",
        "params": {"topic": "string"},
        "risk": 0
    },
    "synthesize_skill": {
        "desc": "Automatically create a new code-based skill to expand JARVIS's functionality.",
        "params": {"skill_name": "string", "description": "string", "requirements": "string"},
        "risk": 1
    },
    "mouse_control": {
        "desc": "Control the mouse cursor.",
        "params": {"action": "string", "x": "integer", "y": "integer"},
        "risk": 0
    },
    "keyboard_control": {
        "desc": "Simulate keyboard input.",
        "params": {"action": "string", "text": "string", "key": "string"},
        "risk": 0
    },
    "send_whatsapp_message": {
        "desc": "Send a WhatsApp message via Twilio API or browser fallback. Highly reliable for messaging.",
        "params": {"phone": "string", "message": "string"},
        "risk": 0
    },
    "weather": {
        "desc": "Get current weather for a city. Defaults to JARVIS_CITY env var.",
        "params": {"city": "string"},
        "risk": 0
    },
    "calendar": {
        "desc": "Manage the user's calendar: add/list/today/remove events.",
        "params": {"action": "string", "title": "string", "date": "string", "time": "string"},
        "risk": 0
    },
    "notifications": {
        "desc": "Start or stop monitoring macOS system notifications.",
        "params": {"action": "string"},
        "risk": 0
    },
    # --- Tier 1: Quick Win Skills ---
    "clipboard": {
        "desc": "Manage clipboard history. Actions: save (current clipboard), history (show recent), paste (restore item by index), search (find by keyword), clear.",
        "params": {"action": "string (save|history|paste|search|clear)", "index": "integer", "keyword": "string", "count": "integer"},
        "risk": 0
    },
    "reminders": {
        "desc": "To-do list with due dates. Actions: add, list, complete, delete, check_due. Supports priority levels.",
        "params": {"action": "string (add|list|complete|delete|check_due)", "text": "string", "due": "string (time/date)", "priority": "string (low|medium|high)", "id": "string"},
        "risk": 0
    },
    "notes": {
        "desc": "Quick save and retrieve text notes. Actions: save, search (by keyword), list (recent), read_last, delete.",
        "params": {"action": "string (save|search|list|read_last|delete)", "text": "string", "tag": "string", "keyword": "string", "count": "integer"},
        "risk": 0
    },
    "translate": {
        "desc": "Translate text between languages using AI or Google Translate. Use 2-letter language codes.",
        "params": {"text": "string", "target": "string (language code, e.g. he/en/es/fr)", "source": "string (auto or code)"},
        "risk": 0
    },
    "summarize": {
        "desc": "Summarize text, URLs, or clipboard content. Specify source='clipboard' to read from clipboard.",
        "params": {"text": "string", "url": "string", "source": "string (clipboard)", "length": "string (short|medium|long)"},
        "risk": 0
    },
    "convert": {
        "desc": "Convert units or currencies. Supports km/miles, kg/lbs, C/F, currency codes (USD/ILS/EUR), etc. Use expression for natural language.",
        "params": {"expression": "string (e.g. '100 USD to ILS')", "value": "number", "from": "string", "to": "string"},
        "risk": 0
    },
    "calculator": {
        "desc": "Calculate math expressions. Supports natural language math, percentages, trigonometry, logarithms.",
        "params": {"expression": "string (e.g. '15% of 340' or 'sqrt(144)')"},
        "risk": 0
    },
    # --- Tier 2: Power Features ---
    "news": {
        "desc": "Get news headlines by category. Categories: general, technology, business, science, health, sports, entertainment.",
        "params": {"category": "string", "count": "integer"},
        "risk": 0
    },
    "ocr": {
        "desc": "Extract text from screen or image using AI vision or OCR. Actions: extract (text only), analyze (text + context).",
        "params": {"action": "string (extract|analyze)", "image": "string (file path, optional - captures screen if empty)"},
        "risk": 0
    },
    "file_search": {
        "desc": "Search for files on Mac using Spotlight (mdfind). Supports type filters: pdf, image, doc, video, audio, code.",
        "params": {"query": "string", "type": "string (pdf|image|doc|video|audio|code)", "directory": "string", "max": "integer"},
        "risk": 0
    },
    "shortcuts": {
        "desc": "Run macOS Shortcuts or schedule tasks. Actions: run (execute shortcut), list (show available), schedule (create daily task).",
        "params": {"action": "string (run|list|schedule)", "name": "string", "command": "string", "time": "string (HH:MM)", "label": "string"},
        "risk": 0
    },
    "code_assistant": {
        "desc": "Write, explain, debug, review, or refactor code using AI. Supports any language.",
        "params": {"action": "string (write|explain|debug|review|refactor)", "description": "string", "code": "string", "language": "string", "file": "string", "error": "string"},
        "risk": 0
    },
    "doc_reader": {
        "desc": "Read and summarize PDF, Word, and text documents. Actions: read, summarize, search (by keyword).",
        "params": {"file": "string (path to document)", "action": "string (read|summarize|search)", "keyword": "string"},
        "risk": 0
    },
    "spotify": {
        "desc": "Control Spotify playback via AppleScript. Actions: play (with optional search query), pause, next, previous, current, volume, shuffle.",
        "params": {"action": "string (play|pause|next|previous|current|volume|shuffle)", "query": "string", "level": "integer"},
        "risk": 0
    },
    # --- Tier 3: Advanced Capabilities ---
    "knowledge_base": {
        "desc": "Personal knowledge base / RAG. Actions: ingest (store text/file), search (find by query), list (show docs), ask (answer question from stored knowledge).",
        "params": {"action": "string (ingest|search|list|ask)", "text": "string", "file": "string", "title": "string", "query": "string"},
        "risk": 0
    },
    "browser": {
        "desc": "Control Safari/Chrome. Actions: open (URL), read (page text), click (CSS selector), fill (form field), tabs (list open tabs), js (run JavaScript), current_url, title.",
        "params": {"action": "string (open|read|click|fill|tabs|js|current_url|title)", "url": "string", "selector": "string", "value": "string", "js": "string", "browser": "string"},
        "risk": 0
    },
    "face_rec": {
        "desc": "Face recognition. Actions: learn (save face with name), identify (who is in photo), list (known faces), forget (remove).",
        "params": {"action": "string (learn|identify|list|forget)", "name": "string", "image": "string"},
        "risk": 0
    },
    "location": {
        "desc": "Get current location via IP/Wi-Fi. Actions: where (current location), label (tag current Wi-Fi as home/office), context (location + context).",
        "params": {"action": "string (where|label|context)", "label": "string"},
        "risk": 0
    },
    "messenger": {
        "desc": "Send messages via iMessage, Telegram, or Discord. Actions: send, read.",
        "params": {"platform": "string (imessage|telegram|discord)", "action": "string (send|read)", "recipient": "string", "message": "string", "chat_id": "string"},
        "risk": 0
    },
    "smart_home": {
        "desc": "Control smart home devices via HomeKit Shortcuts or Home Assistant. Actions: on, off, toggle, list.",
        "params": {"action": "string (on|off|toggle|list)", "device": "string", "entity_id": "string", "backend": "string (auto|ha|homekit)"},
        "risk": 0
    },
    # --- Tier 4: Experimental + Advanced ---
    "daily_briefing": {
        "desc": "Compile morning/evening briefing: weather + calendar + reminders + news + system health. Delivers as natural spoken summary.",
        "params": {"city": "string"},
        "risk": 0
    },
    "mood": {
        "desc": "Detect user mood from voice tone and/or facial expression. Actions: detect (both), face (camera only), suggest (recommendation based on mood).",
        "params": {"action": "string (detect|face|suggest)", "mood": "string", "image": "string"},
        "risk": 0
    },
    "health": {
        "desc": "Track health/fitness: water intake, steps, nutrition, sleep. Actions: water, steps, nutrition, sleep, status, history.",
        "params": {"action": "string (water|steps|nutrition|sleep|status|history)", "amount": "number", "meal": "string", "hours": "number", "quality": "string", "days": "integer"},
        "risk": 0
    },
    "vault": {
        "desc": "Encrypted secret storage (passwords, keys). Actions: init, save, get, list, delete. Requires master_password or JARVIS_VAULT_MASTER env var.",
        "params": {"action": "string (init|save|get|list|delete)", "key": "string", "value": "string", "master_password": "string"},
        "risk": 1
    },
    # --- Newly registered (previously orphaned files) ---
    "run_script": {
        "desc": "Run a Python script file from an allowed path.",
        "params": {"path": "string"},
        "required": ["path"],
        "risk": 1
    },
    "screen_capture": {
        "desc": "Capture a screenshot of the current screen or a specific window.",
        "params": {"region": "string"},
        "risk": 0
    },
    "file_watcher": {
        "desc": "Watch a directory for file changes and report events.",
        "params": {"path": "string", "action": "string (start|stop|status)"},
        "risk": 0
    },
    "scheduler": {
        "desc": "Schedule a task to run at a specific time.",
        "params": {"action": "string (add|list|remove)", "time": "string", "task": "string"},
        "risk": 0
    },
    "screen_analysis": {
        "desc": "Analyze current screen content using vision AI.",
        "params": {"prompt": "string"},
        "risk": 0
    },
}

def get_skill_list_prompt():
    """Generates a human-readable skill list for AI system prompts.
    Escapes braces to avoid KeyError during string formatting."""
    lines = []
    for name, data in SKILL_REGISTRY.items():
        params_str = str(data['params']).replace("{", "{{").replace("}", "}}")
        lines.append(f"- {name}: {data['desc']} | Params: {params_str}")
    return "\n".join(lines)

def get_param_contract():
    """Generates the parameter contract for ExecutorAgent validation.
    Only the first param is truly required; the rest are optional.
    Skills use .get() with defaults, so missing params don't crash."""
    contract = {}
    for name, data in SKILL_REGISTRY.items():
        all_params = {}
        for pk, pt in data['params'].items():
            if "string" in pt: all_params[pk] = str
            elif "integer" in pt: all_params[pk] = int
            else: all_params[pk] = str
        required_keys = data.get("required", [])
        if required_keys:
            req = {k: all_params[k] for k in required_keys if k in all_params}
        else:
            req = {}
        contract[name] = {"required": req, "optional": all_params}
    return contract