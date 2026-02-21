import os
import re
from dataclasses import dataclass
from typing import List, Tuple, Optional

TEXT_EXTS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".kt", ".go", ".rs",
    ".c", ".cpp", ".h", ".hpp", ".cs", ".php", ".rb", ".swift",
    ".md", ".txt", ".yaml", ".yml", ".json", ".toml", ".ini",
    ".html", ".css", ".scss", ".sql", ".sh", ".bat", ".ps1"
}

@dataclass
class SearchHit:
    path: str
    line_no: int
    line: str

def _safe_join(root: str, rel: str) -> str:
    root_abs = os.path.abspath(root)
    target = os.path.abspath(os.path.join(root_abs, rel))
    if not target.startswith(root_abs):
        raise ValueError("Unsafe path traversal detected.")
    return target

def is_text_file(path: str) -> bool:
    _, ext = os.path.splitext(path.lower())
    return ext in TEXT_EXTS

def list_repo_tree(repo_root: str, max_files: int = 5000) -> List[str]:
    """Return a flat list of relative paths."""
    repo_root = os.path.abspath(repo_root)
    out = []
    for base, dirs, files in os.walk(repo_root):
        # skip common heavy folders
        dirs[:] = [d for d in dirs if d not in {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}]
        for fn in files:
            rel = os.path.relpath(os.path.join(base, fn), repo_root)
            out.append(rel)
            if len(out) >= max_files:
                return sorted(out)
    return sorted(out)

def read_file(repo_root: str, rel_path: str, max_chars: int = 200_000) -> str:
    path = _safe_join(repo_root, rel_path)
    with open(path, "rb") as f:
        raw = f.read()
    # decode best-effort
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1", errors="ignore")
    return text[:max_chars]

def write_file(repo_root: str, rel_path: str, new_text: str) -> None:
    path = _safe_join(repo_root, rel_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_text)

def search_code(repo_root: str, query: str, file_glob: Optional[str] = None, max_hits: int = 50) -> List[SearchHit]:
    """
    Simple regex search across repo. If file_glob is provided (e.g. ".py"),
    we filter by extension.
    """
    pattern = re.compile(query, re.IGNORECASE)
    hits: List[SearchHit] = []
    for rel in list_repo_tree(repo_root):
        if file_glob and not rel.lower().endswith(file_glob.lower()):
            continue
        full = _safe_join(repo_root, rel)
        if not is_text_file(full):
            continue
        try:
            text = read_file(repo_root, rel)
        except Exception:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line):
                hits.append(SearchHit(path=rel, line_no=i, line=line[:300]))
                if len(hits) >= max_hits:
                    return hits
    return hits

def summarize_module_context(repo_root: str, rel_path: str, max_chars: int = 25_000) -> str:
    """
    Returns file content (clipped) for LLM summarization.
    """
    text = read_file(repo_root, rel_path, max_chars=max_chars)
    return text