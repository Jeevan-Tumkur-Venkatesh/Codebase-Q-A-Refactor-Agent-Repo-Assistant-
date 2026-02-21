repo-assistant/
  app.py
  repo_tools.py
  llm.py
  patcher.py
  requirements.txt
  README.md


  # Repo Assistant (Codebase Q&A + Refactor Agent)

## Features
- Repo explorer (upload a zip)
- File viewer + summarize_module()
- Chat Q&A about the repo
- search_code()
- Create refactor plan (with tickets text)
- Generate patch + show diff + apply patch + updated file downlaod option
- Architecture diagram text (Mermaid)

## Setup
1) Create `.env`:
GOOGLE_API_KEY=your_key_here

2) Install:
pip install -r requirements.txt

3) Run:
streamlit run app.py