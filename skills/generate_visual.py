import os
import re
import json
import time
import base64
import threading
import xml.etree.ElementTree as ET


SVG_PROMPT_TEMPLATE = """Generate a precise SVG image based on this request:
{description}

{context_section}

CRITICAL RULES — follow ALL of them:
- Output ONLY valid SVG code. Start with <svg and end with </svg>. NO markdown, NO explanation, NO wrapping.
- Use viewBox="0 0 800 600" (or adjust to fit the design).
- Color scheme: cyan (#00e5ff) lines and text on dark (#0a0a2e) background. Use rgba(0,229,255,0.1) for subtle fills.
- Include dimension labels as <text> elements with actual measurements.
- Use clean lines (stroke-width 1-2), minimal fills on structural elements.
- Add a title at the top and a scale reference at the bottom.
- Make it look like a professional technical blueprint or engineering diagram.
"""

OVERLAY_SVG_PROMPT_TEMPLATE = """Generate an SVG wireframe overlay to be placed ON TOP of a photo of a room.
The overlay should show: {description}

Spatial context from the room photo: {context_section}

CRITICAL RULES — follow ALL of them:
- Output ONLY valid SVG code. Start with <svg and end with </svg>. NO markdown, NO explanation.
- Use viewBox="0 0 1280 720" to match a standard camera frame.
- Background MUST be completely transparent. Do NOT add any background rect.
- Draw the object as a 3D wireframe using cyan (#00e5ff) lines, stroke-width 2-3.
- Use semi-transparent fills: rgba(0,229,255,0.06) for surfaces, rgba(0,229,255,0.15) for edges.
- Add dimension labels as <text> elements. Use fill="#ffffff" font-size="16" with a dark text-shadow for readability on photo background.
- Position the furniture/object approximately where it would go in the room based on the spatial context.
- Include dashed guide lines from the object to nearby walls/floor to show depth and placement.
- Add a small label at the bottom: "AR OVERLAY — JARVIS".
- Think of this as an Iron Man HUD scan overlay — clean, technical, futuristic.
"""

MERMAID_PROMPT_TEMPLATE = """Generate a Mermaid.js diagram based on this request:
{description}

{context_section}

CRITICAL RULES:
- Output ONLY valid Mermaid syntax. NO markdown fences, NO explanation.
- Use flowchart, sequenceDiagram, or graph as appropriate.
- Keep it clean and readable.
"""

HTML_PROMPT_TEMPLATE = """Generate an interactive HTML visualization based on this request:
{description}

{context_section}

CRITICAL RULES:
- Output a single self-contained HTML snippet (no <html>/<head>/<body> wrappers).
- Use inline CSS. Color scheme: cyan (#00e5ff) on dark (#0a0a2e).
- Can include inline SVG, tables, or canvas.
- NO external resources or scripts. Keep it self-contained.
"""

ASSEMBLY_3D_PROMPT_TEMPLATE = """You are a 3D modeling engine. Decompose this object into geometric parts for a live assembly animation:
{description}

{context_section}

Output ONLY a valid JSON object (no markdown, no explanation). The JSON must have this exact structure:
{{
  "title": "Short name of the object",
  "summary": "Brief description with overall dimensions and material",
  "build_time": "Estimated real-world build time",
  "parts": [
    {{
      "name": "Part name (e.g. Base, Left Panel, Shelf 1)",
      "shape": "box",
      "w": 80, "h": 2, "d": 35,
      "x": 0, "y": 1, "z": 0,
      "color": "#a0845c"
    }}
  ]
}}

RULES:
- Dimensions (w, h, d) are in centimeters matching the user's specifications.
- Positions (x, y, z) place each part so the full object is correctly assembled. Y is UP. Origin is the center-bottom.
- Supported shapes: "box" (w/h/d), "cylinder" (w=diameter, h=height, d ignored), "sphere" (w=diameter, h/d ignored).
- Color should reflect the material: wood=#a0845c, metal=#8899aa, glass=#88ccee, white=#e0e0e0, black=#333333.
- Order parts in logical assembly sequence (base first, then structural supports, then shelves/surfaces, then back panel/details).
- Include ALL parts needed to build the complete object. Minimum 4 parts, maximum 25.
- Be precise with dimensions and positions so parts connect without gaps.
- Output RAW JSON only. No markdown fences. No explanation text before or after.
"""


def _sanitize_svg(raw):
    raw = re.sub(r'```(?:svg|xml|html)?\s*', '', raw)
    raw = raw.replace('```', '')
    svg_match = re.search(r'<svg[\s\S]*?</svg>', raw, re.IGNORECASE | re.DOTALL)
    if not svg_match:
        return None
    svg_str = svg_match.group(0)
    svg_str = re.sub(r'<script[\s\S]*?</script>', '', svg_str, flags=re.IGNORECASE)
    svg_str = re.sub(r'\bon\w+\s*=\s*"[^"]*"', '', svg_str)
    try:
        ET.fromstring(svg_str)
    except ET.ParseError:
        pass
    return svg_str


def _sanitize_mermaid(raw):
    raw = raw.strip()
    raw = re.sub(r'^```(?:mermaid)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    return raw.strip()


def _generate_ai_composite(photo_path, description, context, socketio):
    """Use Gemini image editing to place furniture in the room photo (runs in background)."""
    try:
        from google import genai
        from PIL import Image

        api_keys_str = os.getenv("GEMINI_API_KEYS", "").strip()
        if not api_keys_str:
            print("[generate_visual] No GEMINI_API_KEYS for composite generation")
            return

        api_key = api_keys_str.replace(',', ' ').split()[0].strip()
        client = genai.Client(api_key=api_key)

        img = Image.open(photo_path)
        img.thumbnail((1280, 720))

        position_hint = f"\nPlace it at this location: {context}" if context else ""
        prompt = (
            f"Edit this photo of a room. Add {description} to the room.{position_hint}\n"
            "Keep the rest of the photo EXACTLY as it is — same lighting, same angle, same objects.\n"
            "The added furniture should look realistic and naturally lit to match the scene.\n"
            "Make it look like a real photograph."
        )

        print(f"[generate_visual] Generating AI composite: {description[:80]}")

        IMAGE_MODELS = [
            "gemini-2.0-flash-exp-image-generation",
            "gemini-2.0-flash-exp",
            "gemini-2.5-flash-preview-04-17",
        ]

        response = None
        for model_name in IMAGE_MODELS:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[prompt, img],
                    config=genai.types.GenerateContentConfig(
                        response_modalities=["TEXT", "IMAGE"],
                    ),
                )
                if response and response.candidates:
                    print(f"[generate_visual] AI composite succeeded with model: {model_name}")
                    break
            except Exception as model_err:
                print(f"[generate_visual] Model {model_name} failed: {model_err}")
                continue

        if not response or not response.candidates:
            print("[generate_visual] AI composite: no model returned a valid response")
            return

        for part in response.candidates[0].content.parts:
            if hasattr(part, 'inline_data') and part.inline_data and part.inline_data.data:
                image_bytes = part.inline_data.data
                if isinstance(image_bytes, str):
                    image_bytes = base64.b64decode(image_bytes)

                os.makedirs("generated", exist_ok=True)
                filename = f"generated/composite_{int(time.time())}.jpg"
                with open(filename, "wb") as f:
                    f.write(image_bytes)

                image_b64 = base64.b64encode(image_bytes).decode('utf-8')
                if socketio:
                    socketio.emit("visual_panel", {
                        "type": "ai_composite",
                        "image_base64": image_b64,
                        "title": f"AR RENDER: {description[:50]}",
                    })
                print(f"[generate_visual] AI composite emitted to HUD ({len(image_bytes)} bytes)")
                return

        print("[generate_visual] AI composite: response had no image parts")

    except Exception as e:
        print(f"[generate_visual] AI composite failed: {e}")
        import traceback
        traceback.print_exc()


def _parse_assembly_json(raw):
    """Extract and validate assembly JSON from AI response."""
    raw = raw.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)

    json_match = re.search(r'\{[\s\S]*\}', raw)
    if not json_match:
        return None
    try:
        data = json.loads(json_match.group(0))
    except json.JSONDecodeError:
        return None

    if not isinstance(data.get("parts"), list) or len(data["parts"]) < 1:
        return None

    valid_parts = []
    for p in data["parts"]:
        if not isinstance(p, dict):
            continue
        if "shape" not in p or "w" not in p:
            continue
        part = {
            "name": str(p.get("name", f"Part {len(valid_parts)+1}")),
            "shape": p.get("shape", "box"),
            "w": float(p.get("w", 10)),
            "h": float(p.get("h", 10)),
            "d": float(p.get("d", 10)),
            "x": float(p.get("x", 0)),
            "y": float(p.get("y", 0)),
            "z": float(p.get("z", 0)),
            "color": str(p.get("color", "#a0845c")),
        }
        valid_parts.append(part)

    if not valid_parts:
        return None

    data["parts"] = valid_parts
    return data


def _handle_assembly_3d(description, context_section, chat, socketio):
    """Generate a 3D assembly JSON and emit to HUD."""
    prompt = ASSEMBLY_3D_PROMPT_TEMPLATE.format(description=description, context_section=context_section)
    print(f"[generate_visual] Generating assembly_3d for: {description[:100]}")

    try:
        response = chat.send_message(prompt)
        if not response or not hasattr(response, 'text'):
            return "error: AI returned empty response for assembly_3d"

        raw = response.text.strip()
        print(f"[generate_visual] assembly_3d AI returned {len(raw)} chars")

        data = _parse_assembly_json(raw)
        if not data:
            print(f"[generate_visual] assembly_3d parse failed. Raw: {raw[:300]}")
            return "error: AI output was not valid assembly JSON"

        os.makedirs("generated", exist_ok=True)
        filename = f"generated/assembly_{int(time.time())}.json"
        with open(filename, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        if socketio:
            socketio.emit("visual_panel", {
                "type": "assembly_3d",
                "data": data,
                "title": f"3D BUILD: {data.get('title', description[:40])}",
            })
            print(f"[generate_visual] Emitted assembly_3d to HUD ({len(data['parts'])} parts)")

        return f"success: 3D assembly model generated with {len(data['parts'])} parts. Displaying live assembly animation on HUD."

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"error: assembly_3d generation failed — {e}"


def execute(params):
    """
    Skill: Generate Visual
    Generates SVG/Mermaid/HTML visuals using AI and pushes to the HUD.
    Types: svg, overlay, composite, mermaid, html, assembly_3d
    """
    description = params.get("prompt", "").strip()
    context = params.get("context", "").strip()
    vis_type = params.get("type", "svg").strip().lower()
    chat = params.get("_chat")
    socketio = params.get("_socketio")
    photo_path = params.get("_photo_path", "").strip()

    if not description:
        return "error: no prompt/description provided"
    if not chat:
        return "error: no AI chat session available"

    context_section = f"Spatial context from camera analysis:\n{context}" if context else ""

    if vis_type == "assembly_3d":
        return _handle_assembly_3d(description, context_section, chat, socketio)
    elif vis_type == "overlay":
        prompt = OVERLAY_SVG_PROMPT_TEMPLATE.format(description=description, context_section=context_section)
    elif vis_type == "composite":
        if not photo_path or not os.path.exists(photo_path):
            return "error: composite mode requires a captured photo (_photo_path missing)"
        _generate_ai_composite(photo_path, description, context, socketio)
        return "success: AI composite generation initiated"
    elif vis_type == "mermaid":
        prompt = MERMAID_PROMPT_TEMPLATE.format(description=description, context_section=context_section)
    elif vis_type == "html":
        prompt = HTML_PROMPT_TEMPLATE.format(description=description, context_section=context_section)
    else:
        vis_type = "svg"
        prompt = SVG_PROMPT_TEMPLATE.format(description=description, context_section=context_section)

    print(f"[generate_visual] Generating {vis_type} for: {description[:100]}")

    try:
        response = chat.send_message(prompt)
        if not response or not hasattr(response, 'text'):
            print("[generate_visual] ERROR: AI returned empty response")
            return "error: AI returned empty response"

        raw_output = response.text.strip()
        print(f"[generate_visual] AI returned {len(raw_output)} chars")

        if vis_type in ("svg", "overlay"):
            svg_content = _sanitize_svg(raw_output)
            if not svg_content:
                print(f"[generate_visual] SVG sanitize failed. Raw start: {raw_output[:200]}")
                return "error: AI output did not contain valid SVG"

            os.makedirs("generated", exist_ok=True)
            filename = f"generated/visual_{int(time.time())}.svg"
            with open(filename, "w") as f:
                f.write(svg_content)

            if vis_type == "overlay" and photo_path and os.path.exists(photo_path):
                photo_url = f"/captures/{os.path.basename(photo_path)}"
                if socketio:
                    socketio.emit("visual_panel", {
                        "type": "photo_overlay",
                        "photo_url": photo_url,
                        "svg_overlay": svg_content,
                        "title": f"AR: {description[:50]}",
                    })
                    print(f"[generate_visual] Emitted photo_overlay to HUD")

                threading.Thread(
                    target=_generate_ai_composite,
                    args=(photo_path, description, context, socketio),
                    daemon=True
                ).start()

                return f"success: AR overlay displayed on HUD. AI composite generating in background. Saved to {filename}"
            else:
                if socketio:
                    socketio.emit("visual_panel", {
                        "type": "svg",
                        "content": svg_content,
                        "title": description[:60],
                    })
                    print(f"[generate_visual] Emitted to HUD: svg ({len(svg_content)} chars)")
                return f"success: svg visual generated and displayed on the HUD. Saved to {filename}"

        elif vis_type == "mermaid":
            content = _sanitize_mermaid(raw_output)
            if not content:
                return "error: AI output did not contain valid Mermaid syntax"

            os.makedirs("generated", exist_ok=True)
            filename = f"generated/visual_{int(time.time())}.html"
            with open(filename, "w") as f:
                f.write(content)

            if socketio:
                socketio.emit("visual_panel", {
                    "type": "mermaid",
                    "content": content,
                    "title": description[:60],
                })
            return f"success: mermaid diagram generated. Saved to {filename}"

        else:
            os.makedirs("generated", exist_ok=True)
            filename = f"generated/visual_{int(time.time())}.html"
            with open(filename, "w") as f:
                f.write(raw_output)

            if socketio:
                socketio.emit("visual_panel", {
                    "type": "html",
                    "content": raw_output,
                    "title": description[:60],
                })
            return f"success: html visual generated. Saved to {filename}"

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"error: visual generation failed — {e}"
