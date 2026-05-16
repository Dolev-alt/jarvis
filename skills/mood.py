import os


def _analyze_voice_tone(audio_features=None):
    """Analyze voice characteristics for mood detection."""
    if not audio_features:
        return {"mood": "neutral", "confidence": 0.3, "source": "no_audio"}
    return {"mood": "neutral", "confidence": 0.5, "source": "basic_audio"}


def _analyze_face_emotion(image_path=None, chat=None):
    """Analyze facial expression for mood detection using AI vision."""
    if not image_path or not os.path.exists(image_path):
        return None

    if chat:
        try:
            from PIL import Image
            img = Image.open(image_path)
            prompt = (
                "Analyze the facial expression and body language in this photo. "
                "What is the person's likely emotional state? "
                "Respond with ONLY a JSON object: "
                '{"mood": "happy|sad|neutral|stressed|excited|tired|focused|angry", '
                '"confidence": 0.0-1.0, "details": "brief observation"}'
            )
            response = chat.send_message([prompt, img])
            if response and hasattr(response, "text"):
                import json
                text = response.text.strip()
                if '```json' in text:
                    text = text.split('```json')[1].split('```')[0].strip()
                elif '```' in text:
                    text = text.split('```')[1].split('```')[0].strip()
                return json.loads(text)
        except Exception as e:
            print(f"[mood] Face emotion analysis failed: {e}")
    return None


def execute(params):
    action = params.get("action", "detect").lower()
    chat = params.get("_chat")
    image_path = params.get("image", "") or params.get("_photo_path", "")

    if action == "detect":
        results = []

        voice_result = _analyze_voice_tone(params.get("audio_features"))
        results.append(f"Voice: {voice_result['mood']} (confidence: {voice_result['confidence']:.0%})")

        if image_path and chat:
            face_result = _analyze_face_emotion(image_path, chat)
            if face_result:
                results.append(
                    f"Face: {face_result.get('mood', 'unknown')} "
                    f"(confidence: {face_result.get('confidence', 0):.0%})"
                )
                if face_result.get("details"):
                    results.append(f"Details: {face_result['details']}")

        return "Mood analysis:\n" + "\n".join(results)

    if action == "face":
        if not image_path:
            return "No image for facial analysis. Take a photo first."
        if not chat:
            return "AI connection required for facial mood detection."
        result = _analyze_face_emotion(image_path, chat)
        if result:
            return f"Facial mood: {result.get('mood', 'unknown')} ({result.get('confidence', 0):.0%}). {result.get('details', '')}"
        return "Could not analyze facial expression."

    if action == "suggest":
        mood = params.get("mood", "neutral").lower()
        if chat:
            try:
                prompt = (
                    f"The user's detected mood is: {mood}. "
                    f"As JARVIS, suggest ONE thing to help. "
                    f"If happy: reinforce it. If stressed/tired: suggest a break, music, or joke. "
                    f"If focused: don't interrupt. Keep it to 1 sentence."
                )
                response = chat.send_message(prompt)
                if response and hasattr(response, "text"):
                    return response.text.strip()
            except Exception:
                pass
        mood_suggestions = {
            "stressed": "Perhaps some calming music would help.",
            "tired": "Might be a good time for a coffee break.",
            "happy": "Good mood noted. Carry on.",
            "sad": "How about I play something uplifting?",
            "angry": "Deep breath. Want me to pull up something relaxing?",
        }
        return mood_suggestions.get(mood, "No specific suggestion for this mood.")

    return f"Unknown mood action: {action}. Use: detect, face, suggest."
