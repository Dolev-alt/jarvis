import subprocess
import re
import time

from safety_manager import safety_manager

_UNSAFE_SELECTOR_CHARS = re.compile(r"['\";\\`\n\r{}()$]")


def _sanitize_selector(selector: str) -> str:
    """Strip characters that could escape out of a JS string literal."""
    return _UNSAFE_SELECTOR_CHARS.sub("", selector)


def _run_applescript(script):
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=15
        )
        return result.stdout.strip() or result.stderr.strip() or "ok"
    except subprocess.TimeoutExpired:
        return "error: AppleScript timed out"
    except Exception as e:
        return f"error: {e}"


def _open_url(url, browser="Safari"):
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    script = f'tell application "{browser}" to open location "{url}"'
    return _run_applescript(script)


def _get_current_url(browser="Safari"):
    if browser == "Safari":
        script = 'tell application "Safari" to return URL of current tab of front window'
    else:
        script = f'tell application "Google Chrome" to return URL of active tab of front window'
    return _run_applescript(script)


def _get_page_title(browser="Safari"):
    if browser == "Safari":
        script = 'tell application "Safari" to return name of current tab of front window'
    else:
        script = f'tell application "Google Chrome" to return title of active tab of front window'
    return _run_applescript(script)


def _get_page_text(browser="Safari"):
    if browser == "Safari":
        script = '''
        tell application "Safari"
            set pageText to do JavaScript "document.body.innerText.substring(0, 3000)" in current tab of front window
            return pageText
        end tell
        '''
    else:
        script = '''
        tell application "Google Chrome"
            set pageText to execute active tab of front window javascript "document.body.innerText.substring(0, 3000)"
            return pageText
        end tell
        '''
    return _run_applescript(script)


def _click_element(selector, browser="Safari"):
    if browser == "Safari":
        script = f'''
        tell application "Safari"
            do JavaScript "document.querySelector('{selector}').click()" in current tab of front window
        end tell
        '''
    else:
        script = f'''
        tell application "Google Chrome"
            execute active tab of front window javascript "document.querySelector('{selector}').click()"
        end tell
        '''
    return _run_applescript(script)


def _fill_field(selector, value, browser="Safari"):
    escaped_value = value.replace("'", "\\'")
    if browser == "Safari":
        script = f'''
        tell application "Safari"
            do JavaScript "document.querySelector('{selector}').value = '{escaped_value}'" in current tab of front window
        end tell
        '''
    else:
        script = f'''
        tell application "Google Chrome"
            execute active tab of front window javascript "document.querySelector('{selector}').value = '{escaped_value}'"
        end tell
        '''
    return _run_applescript(script)


def _run_js(code, browser="Safari"):
    escaped = code.replace('"', '\\"')
    if browser == "Safari":
        script = f'tell application "Safari" to do JavaScript "{escaped}" in current tab of front window'
    else:
        script = f'tell application "Google Chrome" to execute active tab of front window javascript "{escaped}"'
    return _run_applescript(script)


def execute(params):
    action = params.get("action", "open").lower()
    browser = params.get("browser", "Safari").strip()
    url = params.get("url", "").strip()
    selector = params.get("selector", "").strip()
    value = params.get("value", "").strip()
    js = params.get("js", "").strip()

    if action == "open":
        if not url:
            return "No URL provided."
        url_check = safety_manager.validate_url(url)
        if not url_check["allowed"]:
            return f"Blocked: {url_check['reason']}"
        result = _open_url(url, browser)
        return f"Opened {url} in {browser}." if "error" not in result else result

    if action == "current_url":
        return _get_current_url(browser)

    if action == "title":
        return _get_page_title(browser)

    if action == "read":
        text = _get_page_text(browser)
        if text and "error" not in text.lower():
            return f"Page content:\n{text[:2000]}"
        return "Could not read page content."

    if action == "click":
        if not selector:
            return "No CSS selector provided for click."
        return _click_element(_sanitize_selector(selector), browser)

    if action == "fill":
        if not selector or not value:
            return "Need both selector and value to fill a field."
        return _fill_field(_sanitize_selector(selector), value, browser)

    if action == "js":
        return "error: Arbitrary JavaScript execution is disabled for security."

    if action == "tabs":
        if browser == "Safari":
            script = '''
            tell application "Safari"
                set tabList to ""
                repeat with w in windows
                    repeat with t in tabs of w
                        set tabList to tabList & name of t & " | " & URL of t & linefeed
                    end repeat
                end repeat
                return tabList
            end tell
            '''
        else:
            script = '''
            tell application "Google Chrome"
                set tabList to ""
                repeat with w in windows
                    repeat with t in tabs of w
                        set tabList to tabList & title of t & " | " & URL of t & linefeed
                    end repeat
                end repeat
                return tabList
            end tell
            '''
        result = _run_applescript(script)
        return f"Open tabs:\n{result}" if "error" not in result else result

    return f"Unknown browser action: {action}. Use: open, current_url, title, read, click, fill, js, tabs."
