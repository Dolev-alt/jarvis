import os
import subprocess
import platform
import json
import ssl
import urllib.request
import urllib.parse
import time

_ssl_ctx = ssl.create_default_context()


def _search_itunes(query):
    encoded = urllib.parse.quote(query)
    url = f"https://itunes.apple.com/search?term={encoded}&country=IL&media=music&entity=song&limit=5"
    try:
        with urllib.request.urlopen(url, timeout=6, context=_ssl_ctx) as resp:
            data = json.loads(resp.read().decode())
            return data.get("results", [])
    except Exception as e:
        print(f"[open_app] iTunes search failed: {e}")
        return []


def _play_specific_song(song_name):
    results = _search_itunes(song_name)
    if not results:
        return None

    track = results[0]
    track_url = track.get("trackViewUrl", "")
    track_name = track.get("trackName", song_name)
    artist_name = track.get("artistName", "")

    if not track_url:
        return None

    music_url = track_url.replace("https://", "music://")
    subprocess.run(["open", music_url], check=False)
    time.sleep(4)

    add_and_play = '''
    tell application "System Events"
        tell process "Music"
            set btns to every button of toolbar 1 of window 1
            repeat with b in btns
                if description of b is "Add to Library" then
                    click b
                    exit repeat
                end if
            end repeat
        end tell
    end tell
    delay 4
    tell application "Music"
        set searchResults to (search playlist "Library" for "''' + track_name.replace('"', '\\"') + '''")
        if (count of searchResults) > 0 then
            play item 1 of searchResults
            return "playing"
        else
            return "not_found"
        end if
    end tell'''

    label = f"{track_name} by {artist_name}" if artist_name else track_name

    r = subprocess.run(["osascript", "-e", add_and_play], capture_output=True, text=True, timeout=20)
    if "playing" in r.stdout:
        return f"Now playing: {label}"

    play_from_lib = f'''tell application "Music"
        set searchResults to (search playlist "Library" for "{track_name.replace('"', '\\"')}")
        if (count of searchResults) > 0 then
            play item 1 of searchResults
            return "playing"
        end if
    end tell'''
    r2 = subprocess.run(["osascript", "-e", play_from_lib], capture_output=True, text=True, timeout=10)
    if "playing" in r2.stdout:
        return f"Now playing: {label}"

    return None


def execute(params):
    """
    Skill: Open Application / Control Music
    Params: {'text': 'application name or music command'}
    """
    app_name = params.get("text", "").lower().strip()
    if not app_name:
        return "No application name provided."

    system = platform.system()

    try:
        if system == "Windows":
            if "email" in app_name or "mail" in app_name:
                subprocess.Popen(["cmd", "/c", "start", "mailto:"], shell=False)
                return "Opening your default email client."
            if "browser" in app_name or "internet" in app_name:
                subprocess.Popen(["cmd", "/c", "start", "https://www.google.com"], shell=False)
                return "Opening your web browser."
            subprocess.Popen(["cmd", "/c", "start", "", app_name], shell=False)
            return f"Opening {app_name}."

        elif system == "Darwin":
            if "email" in app_name or "mail" in app_name:
                subprocess.Popen(["open", "mailto:"])
                return "Opening your default email client."
            if "browser" in app_name or "internet" in app_name:
                subprocess.Popen(["open", "https://www.google.com"])
                return "Opening your web browser."

            music_cmds = {
                "pause": 'tell application "Music" to pause',
                "stop": 'tell application "Music" to pause',
                "next": 'tell application "Music" to next track',
                "skip": 'tell application "Music" to next track',
                "previous": 'tell application "Music" to previous track',
                "resume": 'tell application "Music" to play',
                "shuffle": 'tell application "Music" to set shuffle enabled to true',
            }

            is_music = ("music" in app_name or "song" in app_name or "play " in app_name
                        or "play the" in app_name or app_name in ("pause", "stop", "resume", "next", "skip", "previous", "shuffle")
                        or any(app_name.startswith(t) for t in ("pause", "stop", "resume", "next track", "skip track", "previous track")))

            if is_music:
                for trigger, cmd in music_cmds.items():
                    if trigger in app_name:
                        subprocess.run(["osascript", "-e", cmd])
                        return f"Music: {trigger}."

                song_query = app_name
                for word in ["play", "the song", "song", "music", "open", "start", "put on", "launch"]:
                    song_query = song_query.replace(word, "")
                song_query = song_query.strip()

                if song_query and len(song_query) > 1:
                    result = _play_specific_song(song_query)
                    if result:
                        return result

                play_script = '''tell application "Music"
                    activate
                    set shuffle enabled to true
                    if (count of tracks of playlist "Library") > 0 then
                        set totalTracks to count of tracks of playlist "Library"
                        set randomIndex to (random number from 1 to totalTracks)
                        play track randomIndex of playlist "Library"
                        delay 1
                        set trackName to name of current track
                        set artistName to artist of current track
                        return trackName & " by " & artistName
                    end if
                end tell'''
                r = subprocess.run(["osascript", "-e", play_script], capture_output=True, text=True)
                if r.returncode != 0:
                    print(f"[open_app] osascript error: {r.stderr}")
                    return "Playing music."
                now_playing = r.stdout.strip()
                if now_playing:
                    return f"Now playing: {now_playing}"
                return "Playing music."

            subprocess.Popen(["open", "-a", app_name])
            return f"Launching {app_name}."

        elif system == "Linux":
            subprocess.Popen([app_name], stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
            return f"Starting {app_name}."

    except Exception as e:
        return f"Error opening {app_name}: {str(e)}"

if __name__ == "__main__":
    print(execute({"text": "play wind of change"}))