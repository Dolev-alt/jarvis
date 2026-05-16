import subprocess
import os


def _spotify_osascript(command):
    """Control Spotify via AppleScript."""
    try:
        result = subprocess.run(
            ["osascript", "-e", f'tell application "Spotify" to {command}'],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip() or "ok"
    except Exception as e:
        return f"error: {e}"


def _search_and_play(query):
    """Search for a track on Spotify and play it."""
    try:
        search_query = query.replace(" ", "%20")
        uri_script = f'''
        tell application "Spotify"
            activate
            delay 1
        end tell
        do shell script "open 'spotify:search:{search_query}'"
        delay 2
        tell application "Spotify" to play
        '''
        result = subprocess.run(
            ["osascript", "-e", uri_script],
            capture_output=True, text=True, timeout=15
        )
        return f"Searching Spotify for '{query}' and playing."
    except Exception as e:
        return f"error: {e}"


def _play_uri(uri):
    """Play a specific Spotify URI."""
    try:
        result = subprocess.run(
            ["osascript", "-e", f'tell application "Spotify" to play track "{uri}"'],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip() or "Playing."
    except Exception as e:
        return f"error: {e}"


def _get_current():
    """Get current playing track info."""
    try:
        script = '''
        tell application "Spotify"
            set trackName to name of current track
            set artistName to artist of current track
            set albumName to album of current track
            set trackDuration to duration of current track
            set playerPos to player position
            return trackName & " | " & artistName & " | " & albumName
        end tell
        '''
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=10
        )
        if result.stdout.strip():
            parts = result.stdout.strip().split(" | ")
            if len(parts) >= 3:
                return {"track": parts[0], "artist": parts[1], "album": parts[2]}
        return None
    except Exception:
        return None


def execute(params):
    action = params.get("action", "play").lower()
    query = params.get("query", "").strip()

    if action == "play":
        if query:
            return _search_and_play(query)
        return _spotify_osascript("play")

    if action == "pause":
        return _spotify_osascript("pause")

    if action == "next":
        return _spotify_osascript("next track")

    if action == "previous":
        return _spotify_osascript("previous track")

    if action in ["current", "now_playing"]:
        info = _get_current()
        if info:
            return f"Now playing: {info['track']} by {info['artist']} (Album: {info['album']})"
        return "Nothing is currently playing on Spotify."

    if action == "volume":
        level = params.get("level", "50")
        return _spotify_osascript(f"set sound volume to {level}")

    if action == "shuffle":
        return _spotify_osascript("set shuffling to true")

    if action == "repeat":
        return _spotify_osascript("set repeating to true")

    return f"Unknown Spotify action: {action}. Use: play, pause, next, previous, current, volume, shuffle."
