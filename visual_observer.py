import time
import threading
import os
import platform
import pyautogui
from PIL import Image
from datetime import datetime


def _get_active_window_info():
    """Cross-platform active window info: returns dict with left, top, width, height, title or None."""
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
                    bounds = win.get("kCGWindowBounds", {})
                    return {
                        "left": int(bounds.get("X", 0)),
                        "top": int(bounds.get("Y", 0)),
                        "width": int(bounds.get("Width", 0)),
                        "height": int(bounds.get("Height", 0)),
                        "title": win.get("kCGWindowOwnerName", "Unknown"),
                    }
        else:
            import pygetwindow as gw
            window = gw.getActiveWindow()
            if window and window.width > 0:
                return {
                    "left": window.left,
                    "top": window.top,
                    "width": window.width,
                    "height": window.height,
                    "title": window.title,
                }
    except Exception:
        pass
    return None

class VisualObserver:
    def __init__(self, chat_obj, socketio_obj=None, scan_interval=600, memory_obj=None):
        self.chat = chat_obj
        self.socketio = socketio_obj
        self.scan_interval = scan_interval
        self.memory = memory_obj
        self.active = False
        self.visual_context = "System starting... No visual data yet."
        self.last_screenshot_path = None
        
        if not os.path.exists("screenshots"):
            os.makedirs("screenshots")

    def _emit_update(self, context, screenshot_path):
        if self.socketio:
            self.socketio.emit('visual_awareness', {
                'context': context,
                'image_path': screenshot_path,
                'timestamp': datetime.now().strftime("%H:%M:%S")
            })

    def scan_now(self, prompt_context=""):
        """Event-Driven On-Demand Capture of Active Window."""
        print(f"[VISUAL_OBSERVER] Taking on-demand vision scan...")
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.abspath(f"screenshots/observer_{timestamp}.png")
            
            window_info = _get_active_window_info()
            if window_info and window_info["width"] > 0 and window_info["height"] > 0:
                region = (window_info["left"], window_info["top"], window_info["width"], window_info["height"])
                screenshot = pyautogui.screenshot(region=region)
                w_title = window_info["title"]
            else:
                screenshot = pyautogui.screenshot()
                w_title = "Desktop"
                
            screenshot.thumbnail((1280, 720))
            screenshot.save(filepath)
            self.last_screenshot_path = filepath
            
            img = Image.open(filepath)
            prompt = f"""You are the Visual Cortex of JARVIS.
User Context: {prompt_context}
Active Window Title: {w_title}

Analyze this screen and provide a CONCISE description of what is happening.

Focus on:
1. Visible progress (downloads, errors, code, loading states).
2. Content the user is currently focused on.
3. Any errors, warnings, or issues that need attention.

PRIVACY: NEVER include passwords, credit card numbers, private messages, email content, or personal credentials in your response. If you see sensitive data, note "sensitive content visible" without details.

Respond in this format:
AWARENESS: <what the user is doing, 1-2 sentences>
EVENTS: <notable items that JARVIS should know about>"""
            
            response = self.chat.send_message([prompt, img])
            self.visual_context = response.text.strip()
            
            self._emit_update(self.visual_context, f"/screenshots/{os.path.basename(filepath)}")
            
            if self.memory:
                self.memory.store_semantic(f"Visual Scan: {self.visual_context}", {"type": "vision_awareness", "window": w_title})
            
            self._cleanup_screenshots()
            
            return self.visual_context
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                err = "[VISUAL_OBSERVER] Brain Overloaded (429)."
            else:
                err = f"[VISUAL_OBSERVER] Vision Error: {e}"
            print(err)
            return err

    def _cleanup_screenshots(self):
        files = sorted([os.path.join("screenshots", f) for f in os.listdir("screenshots") if f.startswith("observer_")], 
                       key=os.path.getmtime)
        if len(files) > 5:
            for f in files[:-5]:
                try: os.remove(f)
                except: pass

    def start(self):
        print("[VISUAL_OBSERVER] Neural Optics loaded. Periodic scan every 5 minutes.")
        self.active = True
        self._scan_thread = threading.Thread(target=self._periodic_scan_loop, daemon=True)
        self._scan_thread.start()

    def _periodic_scan_loop(self):
        time.sleep(30)
        while self.active:
            try:
                self.scan_now()
            except Exception as e:
                print(f"[VISUAL_OBSERVER] Periodic scan error: {e}")
            time.sleep(max(self.scan_interval, 300))

    def stop(self):
        self.active = False

    def get_context(self):
        return self.visual_context
