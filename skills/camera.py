import subprocess
import os
import time
import shutil
import base64


def save_browser_capture(data_url):
    """Save a base64 data URL from the browser to captures/. Returns file path or None."""
    try:
        if "," in data_url:
            data_url = data_url.split(",", 1)[1]
        image_bytes = base64.b64decode(data_url)
        os.makedirs("captures", exist_ok=True)
        output_path = f"captures/cam_{int(time.time())}.jpg"
        with open(output_path, "wb") as f:
            f.write(image_bytes)
        print(f"[camera] Browser capture saved: {output_path}")
        return output_path
    except Exception as e:
        print(f"[camera] Failed to save browser capture: {e}")
        return None


def _capture_imagesnap(output_path, warmup=1.5):
    if not shutil.which("imagesnap"):
        return None
    try:
        r = subprocess.run(
            ["imagesnap", "-w", str(warmup), output_path],
            capture_output=True, text=True, timeout=15
        )
        if r.returncode == 0 and os.path.exists(output_path):
            return output_path
    except Exception as e:
        print(f"[camera] imagesnap failed: {e}")
    return None


def _capture_ffmpeg(output_path):
    if not shutil.which("ffmpeg"):
        return None
    try:
        r = subprocess.run(
            ["ffmpeg", "-f", "avfoundation", "-framerate", "30",
             "-i", "0", "-frames:v", "1", "-y", "-q:v", "2", output_path],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode == 0 and os.path.exists(output_path):
            return output_path
    except Exception as e:
        print(f"[camera] ffmpeg failed: {e}")
    return None


def _capture_opencv(output_path):
    try:
        import cv2
        os.environ["OPENCV_AVFOUNDATION_SKIP_AUTH"] = "1"
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return None
        for _ in range(8):
            cap.read()
        ok, frame = cap.read()
        cap.release()
        if ok:
            cv2.imwrite(output_path, frame)
            return output_path
    except ImportError:
        pass
    except Exception as e:
        print(f"[camera] opencv failed: {e}")
    return None


def execute(params):
    """
    Skill: Webcam Camera Capture
    Captures a photo from the Mac's built-in webcam.
    Cascade: imagesnap -> ffmpeg -> OpenCV
    """
    os.makedirs("captures", exist_ok=True)
    output_path = f"captures/cam_{int(time.time())}.jpg"

    for method in [_capture_imagesnap, _capture_ffmpeg, _capture_opencv]:
        result = method(output_path)
        if result:
            print(f"[camera] Captured: {result}")
            return f"CAMERA_CAPTURED: {result}"

    return "error: Could not capture from webcam. Check camera permissions in System Settings > Privacy > Camera."
