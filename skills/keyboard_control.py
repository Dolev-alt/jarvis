import pyautogui
import re

from safety_manager import safety_manager

_BLOCKED_HOTKEYS = {"command+shift+delete", "cmd+shift+delete", "command+q", "cmd+q"}
_BLOCKED_TEXT_PATTERNS = re.compile(
    r"(sudo\s|rm\s+-rf|curl.*\|\s*bash|chmod\s+777)", re.IGNORECASE
)


def execute(params):
    action = params.get("action", "").lower()
    text = params.get("text", "")
    key = params.get("key", "")
    hotkey = params.get("hotkey", [])

    if action == "type" and text and _BLOCKED_TEXT_PATTERNS.search(text):
        safety_manager.audit_log("SKILL", "keyboard_control", {"action": "type", "text": text[:100]}, "DENIED", "Blocked text pattern")
        return "error: Typing that content is blocked by safety policy."

    if action == "hotkey" and hotkey:
        combo = "+".join(str(k).lower() for k in hotkey)
        if combo in _BLOCKED_HOTKEYS:
            safety_manager.audit_log("SKILL", "keyboard_control", {"hotkey": combo}, "DENIED", "Blocked hotkey")
            return "error: That hotkey combination is blocked by safety policy."

    try:
        if action == "type":
            pyautogui.write(text, interval=0.05)
            return f"Typed: {text}"
        elif action == "press":
            pyautogui.press(key)
            return f"Pressed {key}"
        elif action == "hotkey":
            pyautogui.hotkey(*hotkey)
            return f"Executed hotkey: {' + '.join(hotkey)}"
        else:
            return f"Sir, I have successfully executed the {action} action."
    except Exception as e:
        return f"Sir, I encountered an error during input control: {e}"
