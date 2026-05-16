import subprocess

from safety_manager import safety_manager


def execute(params):
    command = params.get("command", "")
    if not command:
        return "Sir, please provide a command to execute."

    check = safety_manager.validate_command(command, "shell")
    if not check["allowed"]:
        safety_manager.audit_log("SKILL", "shell_execution", {"command": command[:200]}, "DENIED", check["reason"])
        return f"error: Command blocked -- {check['reason']}"

    import platform
    if platform.system() == "Windows":
        if command.startswith("top") or "ps" in command:
            command = "tasklist"
        elif "ls " in command or command == "ls":
            command = command.replace("ls", "dir")
        elif "grep" in command:
            command = command.replace("grep", "findstr")

    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        
        output = result.stdout.strip()
        error = result.stderr.strip()

        if len(output) > 1000:
            output = output[:1000] + "\n...(truncated for brevity)..."
        if len(error) > 1000:
            error = error[:1000] + "\n...(truncated for brevity)..."
        
        if result.returncode == 0:
            if not output:
                return "Command executed successfully, Sir. However, there was no output to report."
            return f"Execution successful, Sir. Here is the output:\n\n{output}"
        else:
            return f"Command failed with return code {result.returncode}.\nError Output:\n{error}"
    except subprocess.TimeoutExpired:
        return "Command timed out after 30 seconds."
    except Exception as e:
        return f"Shell execution error: {e}"
