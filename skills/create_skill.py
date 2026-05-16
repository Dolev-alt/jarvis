import os
import re
import ast

SKILLS_DIR = os.path.abspath("./skills")

_FORBIDDEN_CODE_PATTERNS = re.compile(
    r"(os\.system|subprocess\.(run|Popen|call)|__import__|eval\s*\(|exec\s*\(|"
    r"open\s*\(.*['\"]w['\"]|shutil\.rmtree|os\.remove)", re.IGNORECASE
)

_SAFE_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,40}$")


def execute(params):
    skill_name = params.get("skill_name")
    code = params.get("code")
    plan = params.get("plan", "No explicit plan provided.")
    
    if not skill_name or not code:
        return "Sir, I require both a skill name and the code payload to synthesize a new capability."

    from safety_manager import safety_manager

    if not _SAFE_NAME_RE.match(skill_name):
        safety_manager.audit_log("SKILL_TOOL", "create_skill", {"skill": skill_name}, "DENIED", "Invalid skill name")
        return f"error: Invalid skill name '{skill_name}'. Must be lowercase letters, digits, underscores only."

    if ".." in skill_name or "/" in skill_name or "\\" in skill_name:
        safety_manager.audit_log("SKILL_TOOL", "create_skill", {"skill": skill_name}, "DENIED", "Path traversal attempt")
        return "error: Skill name contains forbidden characters."

    try:
        ast.parse(code)
    except SyntaxError as e:
        return f"Sir, I've halted the synthesis. The provided code failed validation due to a syntax error: {e}"

    if _FORBIDDEN_CODE_PATTERNS.search(code):
        safety_manager.audit_log("SKILL_TOOL", "create_skill", {"skill": skill_name}, "DENIED", "Code contains forbidden patterns")
        return "error: The generated code contains forbidden operations (shell access, eval, exec, file deletion). Skill creation blocked."

    file_path = os.path.join(SKILLS_DIR, f"{skill_name}.py")

    resolved = os.path.realpath(file_path)
    if not resolved.startswith(os.path.realpath(SKILLS_DIR)):
        safety_manager.audit_log("SKILL_TOOL", "create_skill", {"skill": skill_name, "resolved": resolved}, "DENIED", "Path escape")
        return "error: Resolved path is outside the skills directory."

    try:
        with open(file_path, "w") as f:
            f.write(code)
        
        safety_manager.audit_log("SKILL_TOOL", "create_skill", {"skill": skill_name}, "SUCCESS", f"Manual creation via tool. Plan: {plan}")
            
        return f"Sir, the new skill '{skill_name}' has been successfully validated, logged, and integrated into my cognitive systems."
    except Exception as e:
        safety_manager.audit_log("SKILL_TOOL", "create_skill", {"skill": skill_name}, "FAILED", str(e))
        return f"Sir, I encountered a system error while integrating the new skill: {e}"