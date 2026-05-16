import math
import re


_SAFE_NAMES = {
    "pi": math.pi, "e": math.e, "tau": math.tau,
    "sqrt": math.sqrt, "abs": abs, "round": round,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "log": math.log, "log10": math.log10, "log2": math.log2,
    "ceil": math.ceil, "floor": math.floor,
    "pow": pow, "min": min, "max": max,
    "factorial": math.factorial,
}


def _safe_eval(expression):
    """Evaluate math expression in a sandboxed environment."""
    cleaned = expression.replace("^", "**").replace("×", "*").replace("÷", "/")
    cleaned = re.sub(r'(\d+)%\s*of\s*(\d+)', r'(\1/100)*\2', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'(\d+)%', r'(\1/100)', cleaned)

    for char in cleaned:
        if char not in "0123456789+-*/.() ,eE" and not char.isalpha():
            raise ValueError(f"Invalid character: {char}")

    try:
        result = eval(cleaned, {"__builtins__": {}}, _SAFE_NAMES)
        return result
    except Exception as e:
        raise ValueError(f"Could not evaluate: {e}")


def execute(params):
    expression = params.get("expression", "").strip()
    if not expression:
        return "No math expression provided."

    chat = params.get("_chat")

    try:
        result = _safe_eval(expression)
        if isinstance(result, float):
            if result == int(result) and abs(result) < 1e15:
                result = int(result)
            else:
                result = round(result, 6)
        return f"{expression} = {result}"
    except ValueError:
        pass

    if chat:
        try:
            prompt = (
                f"Calculate: {expression}\n"
                "If this is a math problem, solve it step by step and return the final answer.\n"
                "Return ONLY the result in format: 'expression = result'. Nothing else."
            )
            response = chat.send_message(prompt)
            if response and hasattr(response, "text"):
                return response.text.strip()
        except Exception as e:
            print(f"[calculator] AI calculation failed: {e}")

    return f"Could not calculate: {expression}"
