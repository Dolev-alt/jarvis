import os
import shutil

from safety_manager import safety_manager


def execute(params):
    action = params.get("action")
    path = params.get("path")
    target = params.get("target")
    content = params.get("content", "")

    if not action or not path:
        return "Sir, I need an action and a path to manage files."

    if not safety_manager.validate_path(path):
        safety_manager.audit_log("SKILL", "file_management", {"action": action, "path": path}, "DENIED", "Path not allowed")
        return f"error: Access to that path is not allowed by safety policy."

    if target and not safety_manager.validate_path(target):
        safety_manager.audit_log("SKILL", "file_management", {"action": action, "target": target}, "DENIED", "Target path not allowed")
        return f"error: Access to the target path is not allowed by safety policy."

    try:
        if action == "create_file":
            with open(path, 'w') as f:
                f.write(content)
            return f"Sir, I have successfully created the file at: {path}"
        elif action == "delete_file":
            if os.path.isfile(path):
                os.remove(path)
                return f"Sir, the file at {path} has been deleted."
            elif os.path.isdir(path):
                shutil.rmtree(path)
                return f"Sir, the directory at {path} has been completely removed."
            else:
                return f"Path {path} does not exist."
        elif action == "move_file":
            shutil.move(path, target)
            return f"Sir, I've moved the item from {path} to {target}."
        elif action == "rename_file":
            os.rename(path, target)
            return f"Sir, the file has been renamed to {target}."
        elif action == "create_dir":
            os.makedirs(path, exist_ok=True)
            return f"Sir, the new directory has been established at: {path}"
        else:
            return f"Unknown action: {action}"
    except Exception as e:
        return f"File management error: {e}"
