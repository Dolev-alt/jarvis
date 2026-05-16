import os
import json

from safety_manager import safety_manager

_FACES_DIR = os.path.join(os.path.dirname(__file__), "..", "known_faces")
_FACES_DB = os.path.join(_FACES_DIR, "faces.json")


def _ensure_dir():
    os.makedirs(_FACES_DIR, exist_ok=True)


def _load_db():
    _ensure_dir()
    if os.path.exists(_FACES_DB):
        try:
            with open(_FACES_DB, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_db(db):
    _ensure_dir()
    with open(_FACES_DB, "w") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def execute(params):
    action = params.get("action", "identify").lower()
    chat = params.get("_chat")

    if action == "learn":
        name = params.get("name", "").strip()
        image_path = params.get("image", "").strip()

        if not name:
            return "No name provided. Tell me who this is."

        if not image_path:
            photo_path = params.get("_photo_path", "")
            if photo_path and os.path.exists(photo_path):
                image_path = photo_path
            else:
                return "No image provided. Take a photo first using the camera skill."

        if not safety_manager.validate_path(image_path):
            safety_manager.audit_log("SKILL_TOOL", "face_rec", {"image": image_path}, "DENIED", "Path not allowed")
            return f"Access denied: image path is outside allowed directories."

        if not os.path.exists(image_path):
            return f"Image not found: {image_path}"

        try:
            import face_recognition
            image = face_recognition.load_image_file(image_path)
            encodings = face_recognition.face_encodings(image)
            if not encodings:
                return f"No face detected in the image."

            db = _load_db()
            db[name] = {
                "encoding": encodings[0].tolist(),
                "image": image_path,
                "learned_at": __import__("time").strftime("%Y-%m-%d %H:%M:%S"),
            }
            _save_db(db)
            return f"Learned {name}'s face. I'll recognize them next time."

        except ImportError:
            if chat:
                try:
                    from PIL import Image
                    img = Image.open(image_path)
                    prompt = f"Describe the person in this photo briefly so I can remember them as '{name}'. Focus on distinctive features."
                    response = chat.send_message([prompt, img])
                    if response and hasattr(response, "text"):
                        db = _load_db()
                        db[name] = {
                            "description": response.text.strip(),
                            "image": image_path,
                            "learned_at": __import__("time").strftime("%Y-%m-%d %H:%M:%S"),
                        }
                        _save_db(db)
                        return f"Learned {name} via AI description (face_recognition library not installed for precise matching)."
                except Exception as e:
                    return f"Face learning failed: {e}"
            return "face_recognition library not installed. Run: pip install face_recognition"

    if action == "identify":
        image_path = params.get("image", "") or params.get("_photo_path", "")
        if not image_path or not os.path.exists(image_path):
            return "No image to analyze. Take a photo first."

        if not safety_manager.validate_path(image_path):
            safety_manager.audit_log("SKILL_TOOL", "face_rec", {"image": image_path}, "DENIED", "Path not allowed")
            return "Access denied: image path is outside allowed directories."

        db = _load_db()
        if not db:
            return "No known faces in the database. Use action='learn' first."

        try:
            import face_recognition
            import numpy as np
            image = face_recognition.load_image_file(image_path)
            face_locations = face_recognition.face_locations(image)
            face_encodings = face_recognition.face_encodings(image, face_locations)

            if not face_encodings:
                return "No faces detected in the image."

            identified = []
            for encoding in face_encodings:
                best_match = None
                best_distance = 0.6
                for name, data in db.items():
                    if "encoding" in data:
                        known_encoding = np.array(data["encoding"])
                        distance = face_recognition.face_distance([known_encoding], encoding)[0]
                        if distance < best_distance:
                            best_distance = distance
                            best_match = name

                if best_match:
                    identified.append(f"{best_match} (confidence: {(1-best_distance)*100:.0f}%)")
                else:
                    identified.append("Unknown person")

            return f"Detected {len(face_encodings)} face(s): " + ", ".join(identified)

        except ImportError:
            if chat:
                try:
                    from PIL import Image
                    img = Image.open(image_path)
                    known_descriptions = "\n".join([f"- {name}: {data.get('description', 'no description')}" for name, data in db.items()])
                    prompt = (
                        f"Look at this photo. Do you see anyone matching these known people?\n"
                        f"{known_descriptions}\n\n"
                        f"If you can match someone, say who. If not, describe who you see."
                    )
                    response = chat.send_message([prompt, img])
                    if response and hasattr(response, "text"):
                        return response.text.strip()
                except Exception:
                    pass
            return "face_recognition library not installed. Run: pip install face_recognition"

    if action == "list":
        db = _load_db()
        if not db:
            return "No known faces."
        lines = [f"- {name} (learned: {data.get('learned_at', 'unknown')})" for name, data in db.items()]
        return f"Known faces ({len(db)}):\n" + "\n".join(lines)

    if action == "forget":
        name = params.get("name", "").strip()
        db = _load_db()
        if name in db:
            del db[name]
            _save_db(db)
            return f"Forgot {name}'s face."
        return f"{name} not found in face database."

    return f"Unknown face_rec action: {action}. Use: learn, identify, list, forget."
