import os
import platform
import subprocess
import time


_cache = {}
_cache_time = 0
_CACHE_TTL = 300  # refresh every 5 minutes


def _run(cmd, timeout=5):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception:
        return ""


def discover_apps():
    apps = set()
    for folder in ["/Applications", "/System/Applications", os.path.expanduser("~/Applications")]:
        if not os.path.isdir(folder):
            continue
        for entry in os.listdir(folder):
            if entry.endswith(".app"):
                apps.add(entry.replace(".app", ""))
        for sub in os.listdir(folder):
            sub_path = os.path.join(folder, sub)
            if os.path.isdir(sub_path) and not sub.endswith(".app"):
                for entry in os.listdir(sub_path):
                    if entry.endswith(".app"):
                        apps.add(entry.replace(".app", ""))
    return sorted(apps)


def discover_system_info():
    info = {
        "os": platform.system(),
        "os_version": platform.mac_ver()[0] or platform.release(),
        "arch": platform.machine(),
        "user": os.environ.get("USER", "unknown"),
        "home": os.path.expanduser("~"),
        "hostname": platform.node(),
        "shell": os.environ.get("SHELL", "/bin/zsh"),
    }
    return info


def discover_running_apps():
    raw = _run(["osascript", "-e", 'tell application "System Events" to get name of every process whose background only is false'])
    if raw:
        return [a.strip() for a in raw.split(",") if a.strip()]
    return []


def get_system_context(force_refresh=False):
    global _cache, _cache_time

    if not force_refresh and _cache and (time.time() - _cache_time < _CACHE_TTL):
        return _cache

    sys_info = discover_system_info()
    apps = discover_apps()

    ctx = {
        "system": sys_info,
        "installed_apps": apps,
    }

    _cache = ctx
    _cache_time = time.time()
    return ctx


def format_for_prompt():
    ctx = get_system_context()
    sys = ctx["system"]
    apps = ctx["installed_apps"]

    apps_str = ", ".join(apps[:80])
    if len(apps) > 80:
        apps_str += f" ... and {len(apps) - 80} more"

    return f"""SYSTEM CONTEXT (auto-discovered at startup — use this to decide how to act):
- OS: macOS {sys['os_version']} ({sys['arch']})
- User: {sys['user']}, Home: {sys['home']}
- Shell: {sys['shell']}
- Installed Apps ({len(apps)}): {apps_str}
- Available macOS commands: osascript (AppleScript — control ANY app), open (launch apps/URLs/files), say (text-to-speech), pbcopy/pbpaste (clipboard), defaults (read/write preferences), networksetup, diskutil, screencapture"""
