import subprocess
import os
import sys

from safety_manager import safety_manager


def execute(params):
    file_path = params.get("path")
    
    if not file_path or not os.path.exists(file_path):
        return f"error: I cannot find the file at {file_path}."

    if not safety_manager.validate_path(file_path):
        safety_manager.audit_log("SKILL", "run_script", {"path": file_path}, "DENIED", "Path not allowed")
        return "error: Running scripts from that location is not allowed by safety policy."

    if not file_path.endswith(".py"):
        return "error: Only Python (.py) scripts are allowed."

    print(f"JARVIS: Executing {os.path.basename(file_path)}...")
    try:
        result = subprocess.run([sys.executable, file_path], capture_output=True, text=True, timeout=30)
        print("-" * 30)
        print(result.stdout)
        if result.stderr:
            print(f"Errors:\n{result.stderr}")
        print("-" * 30)
    except subprocess.TimeoutExpired:
        return "error: Script timed out after 30 seconds."
    except Exception as e:
        return f"error: Failed to run the script: {e}"