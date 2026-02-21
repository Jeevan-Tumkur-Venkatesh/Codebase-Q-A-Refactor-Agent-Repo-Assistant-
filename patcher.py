import difflib

def unified_diff(old: str, new: str, filename: str = "file") -> str:
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm=""
    )
    return "\n".join(diff)

def clamp_text(s: str, max_chars: int = 200_000) -> str:
    return s if len(s) <= max_chars else s[:max_chars] + "\n\n# [TRUNCATED]\n"