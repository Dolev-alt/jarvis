import os


def _extract_pdf(filepath):
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(filepath)
        text = ""
        for page in reader.pages[:30]:
            text += page.extract_text() or ""
        return text.strip()
    except ImportError:
        try:
            import subprocess
            import tempfile
            script = "import sys, fitz\ndoc = fitz.open(sys.argv[1])\nprint(''.join(p.get_text() for p in doc))"
            result = subprocess.run(
                ["python3", "-c", script, filepath],
                capture_output=True, text=True, timeout=15
            )
            return result.stdout.strip()
        except Exception:
            pass
    except Exception as e:
        return f"PDF extraction error: {e}"
    return None


def _extract_docx(filepath):
    try:
        from docx import Document
        doc = Document(filepath)
        text = "\n".join([p.text for p in doc.paragraphs])
        return text.strip()
    except ImportError:
        pass
    except Exception as e:
        return f"DOCX extraction error: {e}"
    return None


def _extract_txt(filepath):
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().strip()
    except Exception as e:
        return f"Text extraction error: {e}"


def execute(params):
    filepath = params.get("file", "").strip()
    action = params.get("action", "read").lower()

    if not filepath:
        return "No file path provided."

    filepath = os.path.expanduser(filepath)
    if not os.path.exists(filepath):
        return f"File not found: {filepath}"

    from safety_manager import safety_manager
    if not safety_manager.validate_path(filepath):
        return "error: Access to that file path is not allowed by safety policy."

    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".pdf":
        text = _extract_pdf(filepath)
    elif ext in [".docx", ".doc"]:
        text = _extract_docx(filepath)
    elif ext in [".txt", ".md", ".csv", ".json", ".log", ".py", ".js", ".html", ".css"]:
        text = _extract_txt(filepath)
    else:
        return f"Unsupported file type: {ext}. Supported: .pdf, .docx, .txt, .md, .csv, .json, .py, .js, .html"

    if not text:
        return f"Could not extract text from {os.path.basename(filepath)}. Required library may be missing (pip install PyPDF2 python-docx)."

    word_count = len(text.split())
    preview = text[:500]

    if action == "read":
        if word_count > 500:
            return f"Document: {os.path.basename(filepath)} ({word_count} words)\nPreview:\n{preview}...\n\n(Use action='summarize' for a summary)"
        return f"Document: {os.path.basename(filepath)} ({word_count} words)\n{text}"

    if action == "summarize":
        chat = params.get("_chat")
        if chat:
            try:
                prompt = (
                    f"Summarize this document in 1-2 paragraphs. Focus on key information, decisions, and action items.\n\n"
                    f"Document ({os.path.basename(filepath)}, {word_count} words):\n{text[:4000]}"
                )
                response = chat.send_message(prompt)
                if response and hasattr(response, "text"):
                    return f"Summary of {os.path.basename(filepath)}:\n{response.text.strip()}"
            except Exception as e:
                print(f"[doc_reader] AI summary failed: {e}")
        return f"Document preview ({word_count} words):\n{preview}..."

    if action == "search":
        keyword = params.get("keyword", "").strip().lower()
        if not keyword:
            return "No search keyword provided."
        lines = text.split("\n")
        matches = [l.strip() for l in lines if keyword in l.lower()]
        if not matches:
            return f"'{keyword}' not found in {os.path.basename(filepath)}."
        return f"Found {len(matches)} matches for '{keyword}':\n" + "\n".join(f"- {m[:150]}" for m in matches[:10])

    return f"Unknown doc_reader action: {action}. Use: read, summarize, search."
