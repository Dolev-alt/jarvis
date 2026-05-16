import pyautogui
import os
import platform
from datetime import datetime
from PIL import Image


def _get_active_window_region():
    """Returns (left, top, width, height) of the active window, or None."""
    system = platform.system()
    try:
        if system == "Darwin":
            from Quartz import (
                CGWindowListCopyWindowInfo,
                kCGWindowListOptionOnScreenOnly,
                kCGNullWindowID,
                kCGWindowListExcludeDesktopElements,
            )
            windows = CGWindowListCopyWindowInfo(
                kCGWindowListOptionOnScreenOnly | kCGWindowListExcludeDesktopElements,
                kCGNullWindowID,
            )
            for win in windows:
                if win.get("kCGWindowLayer", 999) == 0 and win.get("kCGWindowOwnerName"):
                    b = win.get("kCGWindowBounds", {})
                    w, h = int(b.get("Width", 0)), int(b.get("Height", 0))
                    if w > 0 and h > 0:
                        return (int(b.get("X", 0)), int(b.get("Y", 0)), w, h)
        else:
            import pygetwindow as gw
            window = gw.getActiveWindow()
            if window and window.width > 0 and window.height > 0:
                return (window.left, window.top, window.width, window.height)
    except Exception:
        pass
    return None


def _capture_webcam():
    """Capture a photo from the webcam using the camera skill."""
    try:
        from skills.camera import execute as cam_execute
        result = cam_execute({})
        if isinstance(result, str) and result.startswith("CAMERA_CAPTURED:"):
            path = result.split(":", 1)[1].strip()
            return path
    except Exception as e:
        print(f"[vision] Webcam capture failed: {e}")
    return None


def execute(params):
    """
    Skill: Vision / Screen Capture or Webcam Capture
    Params: source = "screen" (default) or "camera" (webcam)
    """
    source = params.get("source", "screen").strip().lower()

    if source == "camera":
        cam_path = _capture_webcam()
        if cam_path and os.path.exists(cam_path):
            try:
                img = Image.open(cam_path)
                img.thumbnail((1280, 720))
                img.save(cam_path)
            except Exception:
                pass
            return f"CAMERA_CAPTURED: {cam_path}"
        return "VISION_ERROR: Webcam capture failed. Check camera permissions."

    os.makedirs("screenshots", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = f"screenshots/scr_{timestamp}.png"

    try:
        region = _get_active_window_region()
        if region:
            screenshot = pyautogui.screenshot(region=region)
        else:
            screenshot = pyautogui.screenshot()

        screenshot.thumbnail((1280, 720))
        screenshot.save(filepath)

        return f"SCREENSHOT_SAVED: {filepath}"
    except Exception as e:
        return f"VISION_ERROR: {str(e)}"