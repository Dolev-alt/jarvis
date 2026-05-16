import subprocess
import os

from safety_manager import safety_manager


def execute(params):
    action_type = params.get("type", "shell").strip().lower()
    command = params.get("command", "").strip()

    if not command:
        return "error: no command provided"

    check = safety_manager.validate_command(command, action_type)
    if not check["allowed"]:
        safety_manager.audit_log("smart_action", "smart_action", params, "DENIED",
                                 metadata=check["reason"])
        return f"error: {check['reason']}"

    safety_manager.audit_log("smart_action", "smart_action", params, "EXECUTED",
                             metadata=f"type={action_type}")
    print(f"[smart_action] {action_type}: {command}")

    timeout = 15

    try:
        if action_type == "osascript":
            r = subprocess.run(
                ["osascript", "-e", command],
                capture_output=True, text=True, timeout=timeout
            )
        elif action_type == "open":
            parts = command.split()
            cmd = ["open"] + parts
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        else:
            r = subprocess.run(
                command, shell=True,
                capture_output=True, text=True, timeout=timeout,
                env={**os.environ, "PATH": "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:" + os.environ.get("PATH", "")}
            )

        stdout = r.stdout.strip()
        stderr = r.stderr.strip()

        if r.returncode == 0:
            result = stdout if stdout else "ok (no output)"
            print(f"[smart_action] success: {result[:200]}")
            return f"success: {result[:500]}"
        else:
            err = stderr or stdout or f"exit code {r.returncode}"
            print(f"[smart_action] error: {err[:200]}")
            return f"error: {err[:500]}"

    except subprocess.TimeoutExpired:
        return "error: command timed out after 15 seconds"
    except Exception as e:
        return f"error: {e}"
