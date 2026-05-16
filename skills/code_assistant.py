import os

from safety_manager import safety_manager


def execute(params):
    action = params.get("action", "write").lower()
    code = params.get("code", "").strip()
    language = params.get("language", "python").strip()
    description = params.get("description", "").strip()
    filepath = params.get("file", "").strip()

    chat = params.get("_chat")
    if not chat:
        return "Code assistant requires AI connection."

    if filepath:
        if not safety_manager.validate_path(filepath):
            safety_manager.audit_log("SKILL_TOOL", "code_assistant", {"file": filepath, "action": action}, "DENIED", "Path not allowed")
            return f"Access denied: '{filepath}' is outside allowed directories."

    if filepath and os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                code = f.read()
            if not language:
                ext_map = {".py": "python", ".js": "javascript", ".ts": "typescript", ".sh": "bash", ".swift": "swift", ".java": "java", ".go": "go", ".rs": "rust"}
                ext = os.path.splitext(filepath)[1]
                language = ext_map.get(ext, "unknown")
        except Exception as e:
            return f"Could not read file: {e}"

    try:
        if action == "write":
            if not description:
                return "No description provided. Tell me what to write."
            prompt = (
                f"Write {language} code for: {description}\n\n"
                f"Return ONLY the code, no explanations. Include necessary imports. "
                f"Add brief inline comments only for non-obvious logic."
            )

        elif action == "explain":
            if not code:
                return "No code to explain. Provide code or a file path."
            prompt = (
                f"Explain this {language} code in plain English. Be concise but thorough:\n\n"
                f"```{language}\n{code[:3000]}\n```\n\n"
                f"Structure: 1) What it does (1-2 sentences), 2) Key components, 3) Any issues or improvements."
            )

        elif action == "debug":
            error = params.get("error", "").strip()
            if not code and not error:
                return "Provide code and/or an error message to debug."
            prompt = (
                f"Debug this {language} code:\n\n"
                f"```{language}\n{code[:3000]}\n```\n\n"
                f"{'Error: ' + error if error else ''}\n\n"
                f"1. Identify the bug.\n2. Explain the fix.\n3. Show the corrected code."
            )

        elif action == "review":
            if not code:
                return "No code to review."
            prompt = (
                f"Code review for this {language} code:\n\n"
                f"```{language}\n{code[:3000]}\n```\n\n"
                f"Rate 1-10. List: bugs, performance issues, security concerns, style improvements. Be specific."
            )

        elif action == "refactor":
            if not code:
                return "No code to refactor."
            prompt = (
                f"Refactor this {language} code for better readability, performance, and maintainability:\n\n"
                f"```{language}\n{code[:3000]}\n```\n\n"
                f"Return the improved code with brief comments explaining changes."
            )

        else:
            prompt = f"{action}: {description or code[:1000]}"

        response = chat.send_message(prompt)
        if response and hasattr(response, "text"):
            result = response.text.strip()
            if filepath and action in ["write", "refactor"] and params.get("save", False):
                with open(filepath, "w", encoding="utf-8") as f:
                    clean_code = result
                    if "```" in clean_code:
                        clean_code = clean_code.split("```")[1]
                        if clean_code.startswith(language):
                            clean_code = clean_code[len(language):]
                        clean_code = clean_code.split("```")[0].strip()
                    f.write(clean_code)
                return f"Code saved to {filepath}.\n\n{result}"
            return result

    except Exception as e:
        return f"Code assistant error: {e}"

    return "Code assistant could not process the request."
