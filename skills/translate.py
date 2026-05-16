def execute(params):
    text = params.get("text", "").strip()
    target = params.get("target", "en").strip().lower()
    source = params.get("source", "auto").strip().lower()

    if not text:
        return "No text to translate."

    chat = params.get("_chat")
    if chat:
        try:
            src_info = f" from {source}" if source != "auto" else ""
            prompt = (
                f"Translate the following text{src_info} to {target}. "
                f"Return ONLY the translated text, nothing else.\n\n"
                f"Text: {text}"
            )
            response = chat.send_message(prompt)
            if response and hasattr(response, "text"):
                translated = response.text.strip().strip('"')
                return f"Translation ({target}): {translated}"
        except Exception as e:
            print(f"[translate] AI translation failed: {e}")

    try:
        from googletrans import Translator
        translator = Translator()
        result = translator.translate(text, dest=target, src=source if source != "auto" else "auto")
        return f"Translation ({target}): {result.text}"
    except ImportError:
        pass
    except Exception as e:
        return f"Translation failed: {e}"

    return "Translation unavailable. Neither AI nor googletrans could process this."
