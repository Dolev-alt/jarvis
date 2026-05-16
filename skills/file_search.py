import subprocess
import os


def execute(params):
    query = params.get("query", "").strip()
    file_type = params.get("type", "").strip().lower()
    directory = params.get("directory", "").strip()
    max_results = min(int(params.get("max", 10)), 30)

    if not query:
        return "No search query provided."

    args = ["mdfind"]

    if directory:
        args.extend(["-onlyin", os.path.expanduser(directory)])

    mdfind_query = query
    if file_type:
        type_map = {
            "pdf": "kMDItemContentType == 'com.adobe.pdf'",
            "image": "kMDItemContentType == 'public.image'",
            "doc": "kMDItemContentType == 'org.openxmlformats.wordprocessingml.document' || kMDItemContentType == 'com.microsoft.word.doc'",
            "spreadsheet": "kMDItemContentType == 'org.openxmlformats.spreadsheetml.sheet'",
            "presentation": "kMDItemContentType == 'org.openxmlformats.presentationml.presentation'",
            "video": "kMDItemContentType == 'public.movie'",
            "audio": "kMDItemContentType == 'public.audio'",
            "text": "kMDItemContentType == 'public.plain-text'",
            "code": "kMDItemContentType == 'public.source-code'",
        }
        if file_type in type_map:
            mdfind_query = f"({type_map[file_type]}) && (kMDItemDisplayName == '*{query}*'wc || kMDItemTextContent == '*{query}*'wc)"
        else:
            mdfind_query = f"kMDItemDisplayName == '*{query}*'wc && kMDItemFSName == '*.{file_type}'"

    args.append(mdfind_query)

    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=15)
        paths = [p.strip() for p in result.stdout.strip().split("\n") if p.strip()]

        if not paths:
            if file_type:
                args_simple = ["mdfind", "-onlyin", os.path.expanduser(directory or "~"), f"kMDItemDisplayName == '*{query}*'wc"]
                result = subprocess.run(args_simple, capture_output=True, text=True, timeout=15)
                paths = [p.strip() for p in result.stdout.strip().split("\n") if p.strip()]

        if not paths:
            return f"No files found matching '{query}'."

        paths = paths[:max_results]
        lines = []
        for p in paths:
            name = os.path.basename(p)
            folder = os.path.dirname(p)
            size = ""
            try:
                size_bytes = os.path.getsize(p)
                if size_bytes > 1048576:
                    size = f" ({size_bytes/1048576:.1f} MB)"
                elif size_bytes > 1024:
                    size = f" ({size_bytes/1024:.1f} KB)"
            except Exception:
                pass
            lines.append(f"- {name}{size} — {folder}")

        return f"Found {len(paths)} files:\n" + "\n".join(lines)

    except subprocess.TimeoutExpired:
        return "File search timed out."
    except Exception as e:
        return f"File search failed: {e}"
