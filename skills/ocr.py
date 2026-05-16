import subprocess
import os
import time
from PIL import Image

from safety_manager import safety_manager


def _capture_screen_region():
    """Capture full screen and return the path."""
    filepath = os.path.join(os.path.dirname(__file__), "..", "captures", f"ocr_{int(time.time())}.png")
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    try:
        subprocess.run(["screencapture", "-x", filepath], timeout=10)
        if os.path.exists(filepath):
            return filepath
    except Exception as e:
        print(f"[ocr] Screen capture failed: {e}")
    return None


def execute(params):
    image_path = params.get("image", "").strip()
    action = params.get("action", "extract").lower()

    if not image_path:
        image_path = _capture_screen_region()
        if not image_path:
            return "Could not capture screen for OCR."

    if not safety_manager.validate_path(image_path):
        safety_manager.audit_log("SKILL_TOOL", "ocr", {"image": image_path}, "DENIED", "Path not allowed")
        return "Access denied: image path is outside allowed directories."

    if not os.path.exists(image_path):
        return f"Image file not found: {image_path}"

    chat = params.get("_chat")
    if chat:
        try:
            img = Image.open(image_path)
            img.thumbnail((1920, 1080))

            if action == "extract":
                prompt = (
                    "Extract ALL readable text from this image. "
                    "Maintain the original layout as much as possible. "
                    "Return ONLY the extracted text, nothing else. "
                    "PRIVACY: Replace any visible passwords or credit card numbers with [REDACTED]."
                )
            elif action == "analyze":
                prompt = (
                    "Analyze this image for text content. "
                    "1. Extract all visible text.\n"
                    "2. Identify the type of content (code, document, UI, receipt, etc.).\n"
                    "3. Highlight any errors, warnings, or important information.\n"
                    "PRIVACY: Replace any visible passwords or credit card numbers with [REDACTED]."
                )
            else:
                prompt = f"Look at this image and: {action}"

            response = chat.send_message([prompt, img])
            if response and hasattr(response, "text"):
                return f"OCR Result:\n{response.text.strip()}"
        except Exception as e:
            print(f"[ocr] AI OCR failed: {e}")

    try:
        import pytesseract
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img)
        return f"OCR Result:\n{text.strip()}" if text.strip() else "No text detected in image."
    except ImportError:
        return "OCR requires either AI vision (Gemini) or pytesseract. Neither is available."
    except Exception as e:
        return f"OCR failed: {e}"
