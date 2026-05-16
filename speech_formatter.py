import re
import json


def format_for_speech(text: str, max_len: int = 1200) -> str:
    """
    Text normalization for TTS.
    - Extracts spoken text from JSON skill responses
    - Trims whitespace, collapses repeated whitespace/newlines
    - Strips characters that can cause TTS failures
    """
    if text is None:
        return ""

    s = str(text).strip()
    if not s:
        return ""

    # If the text looks like JSON, try to extract the "text" param from speak skills
    if s.startswith("[") or s.startswith("{"):
        try:
            parsed = json.loads(s)
            if isinstance(parsed, dict) and "params" in parsed:
                return format_for_speech(parsed["params"].get("text", ""))
            if isinstance(parsed, list):
                spoken_parts = []
                for item in parsed:
                    if isinstance(item, dict) and item.get("skill") == "speak":
                        t = item.get("params", {}).get("text", "")
                        if t:
                            spoken_parts.append(t)
                if spoken_parts:
                    return format_for_speech(" ".join(spoken_parts))
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    # Strip any remaining JSON fragments
    s = re.sub(r'\{"skill".*?\}', '', s)
    s = re.sub(r'\[?\s*\{[^}]*"skill"[^}]*\}\s*\]?', '', s)

    s = re.sub(r"\s+", " ", s).strip()
    s = s.replace("\u200b", "")

    if len(s) > max_len:
        s = s[:max_len].rstrip()

    return s

