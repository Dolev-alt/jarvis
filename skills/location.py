import json
import urllib.request
import ssl
import subprocess
import os

_ssl_ctx = ssl.create_default_context()

_LOCATION_CACHE_FILE = os.path.join(os.path.dirname(__file__), "..", "location_cache.json")


def _get_ip_location():
    try:
        req = urllib.request.Request("https://ipinfo.io/json", headers={"User-Agent": "JARVIS/1.0"})
        with urllib.request.urlopen(req, timeout=8, context=_ssl_ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return {
            "ip": data.get("ip", ""),
            "city": data.get("city", ""),
            "region": data.get("region", ""),
            "country": data.get("country", ""),
            "loc": data.get("loc", ""),
            "org": data.get("org", ""),
            "timezone": data.get("timezone", ""),
        }
    except Exception as e:
        print(f"[location] IP location failed: {e}")
        return None


def _get_wifi_name():
    try:
        result = subprocess.run(
            ["/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport", "-I"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.split("\n"):
            if "SSID:" in line and "BSSID" not in line:
                return line.split("SSID:")[1].strip()
    except Exception:
        pass
    try:
        result = subprocess.run(
            ["networksetup", "-getairportnetwork", "en0"],
            capture_output=True, text=True, timeout=5
        )
        if "Current Wi-Fi Network:" in result.stdout:
            return result.stdout.split("Current Wi-Fi Network:")[1].strip()
    except Exception:
        pass
    return None


def _load_cache():
    if os.path.exists(_LOCATION_CACHE_FILE):
        try:
            with open(_LOCATION_CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_cache(data):
    try:
        with open(_LOCATION_CACHE_FILE, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def execute(params):
    action = params.get("action", "where").lower()

    if action in ["where", "current", "location"]:
        location = _get_ip_location()
        wifi = _get_wifi_name()

        if not location:
            return "Could not determine location."

        cache = _load_cache()
        wifi_context = ""
        if wifi:
            known = cache.get("wifi_locations", {})
            if wifi in known:
                wifi_context = f" Context: {known[wifi]}"
            else:
                wifi_context = f" (Wi-Fi: {wifi})"

        result = f"Location: {location['city']}, {location['region']}, {location['country']}"
        if location.get("timezone"):
            result += f" | Timezone: {location['timezone']}"
        if wifi_context:
            result += wifi_context

        return result

    if action == "label":
        label = params.get("label", "").strip()
        wifi = _get_wifi_name()
        if not wifi:
            return "Not connected to Wi-Fi."
        if not label:
            return "No label provided. Example: label='home' or label='office'."

        cache = _load_cache()
        if "wifi_locations" not in cache:
            cache["wifi_locations"] = {}
        cache["wifi_locations"][wifi] = label
        _save_cache(cache)
        return f"Wi-Fi '{wifi}' labeled as '{label}'. I'll know this location next time."

    if action == "context":
        wifi = _get_wifi_name()
        cache = _load_cache()
        known = cache.get("wifi_locations", {})
        if wifi and wifi in known:
            return f"You're at: {known[wifi]} (Wi-Fi: {wifi})"
        location = _get_ip_location()
        if location:
            return f"Location: {location['city']}, {location['country']} (Wi-Fi: {wifi or 'unknown'})"
        return "Location unknown."

    return f"Unknown location action: {action}. Use: where, label, context."
