import os
import re
import importlib.util

SKILLS_DIR = os.path.abspath("./skills")
_SAFE_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,40}$")


def execute(params):
    skill_name = params.get("skill_name")
    test_params = params.get("test_params", {})
    
    if not skill_name:
        return "JARVIS: Please specify which skill to test."

    if not _SAFE_NAME_RE.match(skill_name):
        return f"error: Invalid skill name '{skill_name}'. Must be lowercase letters, digits, underscores only."

    skill_path = os.path.join(SKILLS_DIR, f"{skill_name}.py")
    resolved = os.path.realpath(skill_path)
    if not resolved.startswith(os.path.realpath(SKILLS_DIR)):
        return "error: Skill path resolves outside the skills directory."

    if not os.path.exists(skill_path):
        return f"JARVIS: Skill '{skill_name}' not found for testing."

    try:
        spec = importlib.util.spec_from_file_location(skill_name, skill_path)
        if spec is None or spec.loader is None:
            return f"Sir, I'm unable to load '{skill_name}' for testing. The module structure appears invalid."
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        result = module.execute(test_params)
        
        log_path = os.path.join(SKILLS_DIR, "test_run.log")
        with open(log_path, "a") as log:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log.write(f"[{timestamp}] Test: {skill_name} | Params: {test_params} | Result: {result}\n")
            
        return f"Sir, the test run for '{skill_name}' is complete. The result was: {result}"
    except Exception as e:
        log_path = os.path.join(SKILLS_DIR, "test_run.log")
        with open(log_path, "a") as log:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log.write(f"[{timestamp}] Test FAILED: {skill_name} | Error: {e}\n")
        return f"Sir, the test run for '{skill_name}' failed. Error encountered: {e}"
