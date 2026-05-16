import subprocess
import json
import urllib.request
import ssl
import os

_ssl_ctx = ssl.create_default_context()


def _homekit_command(device, action):
    """Control HomeKit devices via macOS Shortcuts or Siri."""
    try:
        shortcut_name = f"{action} {device}"
        result = subprocess.run(
            ["shortcuts", "run", shortcut_name],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            return f"{action.title()} {device}: done."
        siri_script = f'tell application "System Events" to do shell script "open \\"x-apple.systempreferences:com.apple.HomeKit\\""'
        pass
    except Exception:
        pass

    try:
        script = f'''
        tell application "Home"
            activate
        end tell
        delay 1
        tell application "System Events"
            tell process "Home"
                -- HomeKit doesn't have great AppleScript support
            end tell
        end tell
        '''
        return f"HomeKit direct control limited. Create a Shortcut named '{action} {device}' and use shortcuts skill."
    except Exception as e:
        return f"HomeKit error: {e}"


def _home_assistant(entity_id, action, ha_url=None, ha_token=None):
    """Control devices via Home Assistant REST API."""
    url = ha_url or os.getenv("HA_URL", "http://homeassistant.local:8123")
    token = ha_token or os.getenv("HA_TOKEN", "")

    if not token:
        return "Home Assistant token not configured. Set HA_TOKEN in .env"

    service_map = {
        "on": "turn_on",
        "off": "turn_off",
        "toggle": "toggle",
    }
    service = service_map.get(action.lower(), action.lower())
    domain = entity_id.split(".")[0] if "." in entity_id else "light"

    try:
        api_url = f"{url}/api/services/{domain}/{service}"
        data = json.dumps({"entity_id": entity_id}).encode("utf-8")
        req = urllib.request.Request(
            api_url,
            data=data,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
        )
        with urllib.request.urlopen(req, timeout=10, context=_ssl_ctx) as resp:
            if resp.status == 200:
                return f"{entity_id}: {service} executed."
        return f"Home Assistant returned unexpected status."
    except Exception as e:
        return f"Home Assistant error: {e}"


def _ha_get_states(ha_url=None, ha_token=None):
    """Get all device states from Home Assistant."""
    url = ha_url or os.getenv("HA_URL", "http://homeassistant.local:8123")
    token = ha_token or os.getenv("HA_TOKEN", "")

    if not token:
        return None

    try:
        req = urllib.request.Request(
            f"{url}/api/states",
            headers={"Authorization": f"Bearer {token}"}
        )
        with urllib.request.urlopen(req, timeout=10, context=_ssl_ctx) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def execute(params):
    action = params.get("action", "toggle").lower()
    device = params.get("device", "").strip()
    entity_id = params.get("entity_id", "").strip()
    value = params.get("value", "").strip()
    backend = params.get("backend", "auto").lower()

    if action == "list":
        states = _ha_get_states()
        if states:
            devices = [s for s in states if s["entity_id"].startswith(("light.", "switch.", "climate.", "cover.", "fan."))]
            lines = [f"- {s['entity_id']}: {s['state']} ({s['attributes'].get('friendly_name', '')})" for s in devices[:20]]
            return f"Smart home devices ({len(devices)}):\n" + "\n".join(lines)
        return "Home Assistant not configured or no devices found. Set HA_URL and HA_TOKEN in .env"

    if not device and not entity_id:
        return "No device specified. Provide device name or entity_id."

    if entity_id or backend == "ha":
        eid = entity_id or f"light.{device.lower().replace(' ', '_')}"
        return _home_assistant(eid, action)

    return _homekit_command(device, action)
