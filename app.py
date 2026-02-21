import os
import io
import zipfile
import tempfile
from typing import List, Dict, Optional

import streamlit as st

from llm import call_gemini
from repo_tools import list_repo_tree, read_file, write_file, search_code, summarize_module_context
from patcher import unified_diff, clamp_text


# ------------------ “Agent tools” API (as requested) ------------------ #
def search_code_tool(repo_root: str, query: str, file_ext: Optional[str] = None) -> str:
    hits = search_code(repo_root, query=query, file_glob=file_ext, max_hits=50)
    if not hits:
        return "No matches found."
    out = []
    for h in hits:
        out.append(f"{h.path}:{h.line_no}: {h.line}")
    return "\n".join(out)


def summarize_module(repo_root: str, rel_path: str) -> str:
    src = summarize_module_context(repo_root, rel_path)
    prompt = f"""
You are a senior engineer. Summarize this module/file for another engineer.
Include:
- Purpose
- Key functions/classes
- Dependencies
- Risks/bugs/smells
- Suggested refactors (short)

FILE: {rel_path}
CONTENT:
{src}
"""
    return call_gemini(prompt)


def create_refactor_plan(repo_root: str, goal: str, context_files: List[str]) -> str:
    parts = []
    for fp in context_files[:8]:
        parts.append(f"\n\n--- FILE: {fp} ---\n{clamp_text(read_file(repo_root, fp), 20_000)}")
    context = "\n".join(parts) if parts else "(No files provided.)"

    prompt = f"""
You are a refactor agent.
Create a step-by-step refactor plan as a checklist.
Also create "tasks/tickets" with titles + descriptions + acceptance criteria.

Goal:
{goal}

Repo context:
{context}

Output format:
1) High-level approach (short)
2) Refactor plan (checklist)
3) Tasks/Tickets:
   - [T1] Title
     Description:
     Files:
     Acceptance criteria:
"""
    return call_gemini(prompt)


def generate_patch(repo_root: str, rel_path: str, instructions: str) -> Dict[str, str]:
    old = read_file(repo_root, rel_path)
    prompt = f"""
You are a code refactor agent. You will rewrite the file content.
Rules:
- Preserve behavior unless instructions request changes.
- Keep formatting clean.
- Output ONLY the full new file content. No markdown fences. No commentary.

FILE: {rel_path}
INSTRUCTIONS:
{instructions}

CURRENT CONTENT:
{clamp_text(old, 60_000)}
"""
    new = call_gemini(prompt)
    if not new.strip():
        new = old
    diff = unified_diff(old, new, filename=rel_path)
    return {"old": old, "new": new, "diff": diff, "path": rel_path}


# ------------------ Repo loading helpers ------------------ #
def extract_zip_to_temp(uploaded_zip) -> str:
    tmpdir = tempfile.mkdtemp(prefix="repo_")
    with zipfile.ZipFile(uploaded_zip) as z:
        z.extractall(tmpdir)

    entries = os.listdir(tmpdir)
    if len(entries) == 1 and os.path.isdir(os.path.join(tmpdir, entries[0])):
        return os.path.join(tmpdir, entries[0])
    return tmpdir


def ensure_state():
    st.session_state.setdefault("repo_root", None)
    st.session_state.setdefault("repo_zip_key", None)  # ✅ prevents re-extract on rerun
    st.session_state.setdefault("files", [])
    st.session_state.setdefault("selected_file", None)
    st.session_state.setdefault("chat", [])
    st.session_state.setdefault("tasks", [])
    st.session_state.setdefault("last_plan", "")
    st.session_state.setdefault("pending_patch", None)
    st.session_state.setdefault("last_applied_file", None)  # ✅ for download after apply


def guess_mime_by_ext(path: str) -> str:
    ext = os.path.splitext(path.lower())[1]
    if ext in {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".kt", ".go", ".rs", ".c", ".cpp", ".cs"}:
        return "text/plain"
    if ext in {".json"}:
        return "application/json"
    if ext in {".yml", ".yaml"}:
        return "text/yaml"
    if ext in {".md"}:
        return "text/markdown"
    if ext in {".html"}:
        return "text/html"
    if ext in {".css", ".scss"}:
        return "text/css"
    return "text/plain"


# ------------------ UI ------------------ #
def main():
    ensure_state()
    st.set_page_config(page_title="Repo Assistant", page_icon="🧰", layout="wide")
    st.title("Codebase Q&A + Refactor Agent (Repo Assistant)")

    with st.sidebar:
        st.header("Repo Explorer")

        uploaded = st.file_uploader("Upload a repo as .zip", type=["zip"])

        # ✅ Extract ONLY when a NEW zip is uploaded
        if uploaded is not None:
            current_key = f"{uploaded.name}-{uploaded.size}"
            if st.session_state.get("repo_zip_key") != current_key:
                try:
                    repo_root = extract_zip_to_temp(uploaded)
                    st.session_state["repo_root"] = repo_root
                    st.session_state["files"] = list_repo_tree(repo_root)
                    st.session_state["selected_file"] = st.session_state["files"][0] if st.session_state["files"] else None
                    st.session_state["repo_zip_key"] = current_key

                    # reset patch state on new repo
                    st.session_state["pending_patch"] = None
                    st.session_state["last_applied_file"] = None

                    st.success("Repo loaded ✅")
                except Exception as e:
                    st.error(f"Failed to load repo: {e}")

        repo_root = st.session_state["repo_root"]
        files = st.session_state["files"]

        if repo_root:
            st.caption(f"Repo root: {repo_root}")

            filter_text = st.text_input("Filter files", value="")
            filtered = [f for f in files if filter_text.lower() in f.lower()] if filter_text else files

            st.session_state["selected_file"] = st.selectbox(
                "Files",
                options=filtered if filtered else ["(no files)"],
                index=0 if filtered else 0,
            )

            st.divider()

            st.subheader("Tools")
            tool_query = st.text_input("search_code() query (regex ok)", value="")
            tool_ext = st.text_input("Optional ext filter (e.g. .py)", value="")
            if st.button("Run search_code()"):
                if tool_query.strip():
                    out = search_code_tool(repo_root, tool_query.strip(), tool_ext.strip() or None)
                    st.code(out)
                else:
                    st.warning("Enter a search query.")

            st.divider()

            st.subheader("Tasks/Tickets")
            if st.session_state["tasks"]:
                for i, t in enumerate(st.session_state["tasks"], start=1):
                    with st.expander(f"[T{i}] {t.get('title','(no title)')}"):
                        st.write(t.get("description", ""))
                        if t.get("acceptance"):
                            st.markdown("**Acceptance criteria:**")
                            st.write(t["acceptance"])
            else:
                st.caption("No tasks yet. Create a plan to generate tickets.")

    if not st.session_state["repo_root"]:
        st.info("Upload a repo zip to start.")
        return

    repo_root = st.session_state["repo_root"]
    selected_file = st.session_state["selected_file"]

    left, right = st.columns([1.15, 1])

    with left:
        st.subheader("File Viewer")
        if selected_file and selected_file != "(no files)":
            try:
                content = read_file(repo_root, selected_file)
                st.caption(selected_file)
                st.code(content, language=None)
                if st.button("summarize_module()"):
                    summary = summarize_module(repo_root, selected_file)
                    st.session_state["chat"].append({"role": "assistant", "content": f"Summary of `{selected_file}`:\n\n{summary}"})
                    st.success("Summary added to chat ✅")
            except Exception as e:
                st.error(f"Could not read file: {e}")

        st.subheader("Architecture Diagram (text)")
        if st.button("Generate architecture diagram text (Mermaid)"):
            sample_files = st.session_state["files"][:200]
            prompt = f"""
Generate a MERMAID architecture diagram (text only) for this repo.
Use `graph TD` or `graph LR`.
Show main modules and relationships.

Repo files (sample):
{chr(10).join(sample_files)}

Output ONLY mermaid text.
"""
            mermaid = call_gemini(prompt)
            st.code(mermaid)

    with right:
        st.subheader("Chat")

        for msg in st.session_state["chat"]:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        user_msg = st.chat_input("Ask about the repo… (e.g., where is config loaded?)")
        if user_msg:
            st.session_state["chat"].append({"role": "user", "content": user_msg})

            file_snip = ""
            if selected_file and selected_file != "(no files)":
                file_snip = clamp_text(read_file(repo_root, selected_file), 12_000)

            context = f"""
Repo files (sample):
{chr(10).join(st.session_state["files"][:200])}

Selected file: {selected_file}
Selected file content:
{file_snip}
"""

            tool_help = """
Available tools you can ask me to use:
- search_code(query, ext?)
- summarize_module(path)
- create_refactor_plan(goal, context_files)
- generate_patch(path, instructions)
"""

            prompt = f"""
You are a repo assistant. Answer questions about the codebase.
If you need exact locations, suggest using search_code().

User question:
{user_msg}

Context:
{context}

{tool_help}
"""
            answer = call_gemini(prompt)
            st.session_state["chat"].append({"role": "assistant", "content": answer})
            st.rerun()

        st.divider()

        st.subheader("Refactor Agent Actions")

        plan_goal = st.text_area("Refactor goal / change request", value="", height=100)
        selected_context_files = st.multiselect(
            "Select context files for plan (optional)",
            options=st.session_state["files"],
            default=[selected_file] if selected_file and selected_file != "(no files)" else [],
        )

        c1, c2 = st.columns(2)

        with c1:
            if st.button("Create plan"):
                plan = create_refactor_plan(repo_root, plan_goal or "General refactor", selected_context_files)
                st.session_state["last_plan"] = plan
                st.session_state["chat"].append({"role": "assistant", "content": f"📌 Refactor Plan:\n\n{plan}"})
                st.success("Plan created ✅")
                st.rerun()

        with c2:
            patch_instructions = st.text_area("Patch instructions for selected file", value="", height=100)
            if st.button("Generate patch (with diff)"):
                if not selected_file or selected_file == "(no files)":
                    st.error("Select a file first.")
                else:
                    patch = generate_patch(
                        repo_root,
                        selected_file,
                        patch_instructions or plan_goal or "Refactor for clarity",
                    )
                    st.session_state["pending_patch"] = patch
                    st.success("Patch generated ✅")
                    st.rerun()

        # -------- Patch Diff + Apply + Download --------
        pending = st.session_state.get("pending_patch")
        if pending:
            st.markdown("### Patch Diff")
            st.code(pending["diff"] if pending["diff"].strip() else "(No diff)", language="diff")

            a, b = st.columns(2)

            with a:
                if st.button("Apply patch"):
                    write_file(repo_root, pending["path"], pending["new"])
                    st.session_state["last_applied_file"] = pending  # ✅ keep for download after apply
                    st.session_state["pending_patch"] = None
                    st.success("Patch applied ✅ (file updated)")
                    st.rerun()

            with b:
                st.download_button(
                    label="⬇️ Download updated file",
                    data=pending["new"],
                    file_name=os.path.basename(pending["path"]),
                    mime=guess_mime_by_ext(pending["path"]),
                )

        # -------- Download AFTER apply (last applied) --------
        last_applied = st.session_state.get("last_applied_file")
        if last_applied:
            st.markdown("### Download last applied file")
            st.download_button(
                label="⬇️ Download applied file",
                data=last_applied["new"],
                file_name=os.path.basename(last_applied["path"]),
                mime=guess_mime_by_ext(last_applied["path"]),
            )


if __name__ == "__main__":
    main()