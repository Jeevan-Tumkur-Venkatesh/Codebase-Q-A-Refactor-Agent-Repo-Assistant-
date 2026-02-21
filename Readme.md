# Codebase Q&A Refactor Agent – Repo Assistant

An AI-powered Streamlit application that allows users to upload any code repository (ZIP) and:

- Search code using regex
- Ask natural-language questions about the repository
- Generate module and file summaries
- Create structured refactor plans with actionable tickets
- Generate AI-based patches for selected files
- Preview unified diffs before applying changes
- Apply and download updated files
- Generate architecture diagrams in Mermaid format

This tool is designed to help developers quickly understand unfamiliar codebases and plan safe refactors.

---

## Live Demo

https://jeevan-codebase-q-a-refactor-agent-repo-assistant--app.streamlit.app/

Upload a small repository ZIP and try queries such as:
- "Find hardcoded secrets"
- "Summarize this module"
- "Generate a refactor plan"

---

## Architecture Overview

Streamlit UI  
├── Repo Tools (filesystem operations, search, read/write)  
├── LLM Layer (Google Gemini API)  
├── Patch Engine (diff generation and apply)  
└── Session State (context management)

---

## Project Structure

| File | Description |
|------|-------------|
app.py | Streamlit UI and agent orchestration |
repo_tools.py | Repository tree listing, safe file read/write, regex search |
llm.py | Gemini API wrapper |
patcher.py | Unified diff generation and text truncation |
requirements.txt | Python dependencies |

---

## Features

### Repository Upload
- Upload any `.zip` repository
- Extracted into a temporary workspace
- Skips large folders such as `.git`, `node_modules`, and virtual environments

### Code Search
Regex-based search across text files.  
Example:

TODO|FIXME|password|token|secret

Output format:

path/to/file.py:42 → matched line


### Repository Q&A
Ask questions about the codebase using selected files as context:
- "What does this service do?"
- "Where is authentication handled?"
- "Are there security risks?"

### Module Summarization
Generates:
- Responsibilities
- Key functions
- Potential risks
- Refactor suggestions

### Refactor Plan Generator
Produces:
- High-level strategy
- File-by-file checklist
- Ticket-style actionable tasks

### Patch Generation
- Rewrites the full content of a selected file
- Shows a unified diff preview
- Option to apply or download the patch

### Architecture Diagram
Generates Mermaid diagram text describing modules and relationships.

---

## Local Setup

### 1. Clone the repository

git clone https://github.com/Jeevan-Tumkur-Venkatesh/Codebase-Q-A-Refactor-Agent-Repo-Assistant-

cd Codebase-Q-A-Refactor-Agent-Repo-Assistant-


### 2. Create a virtual environment (recommended)

python -m venv venv
source venv/bin/activate


### 3. Install dependencies

pip install -r requirements.txt


### 4. Add environment variables
Create a `.env` file in the project root:

GOOGLE_API_KEY=your_gemini_api_key


### 5. Run the application

streamlit run app.py


---

## Deployment (Streamlit Cloud)

Add the API key in:
App → Settings → Secrets


GOOGLE_API_KEY = "your_key_here"


Then reboot the app.

---

## Demo Workflow

1. Upload a small repository ZIP
2. Run a search (e.g., `TODO|FIXME|password`)
3. Select a file and generate a summary
4. Ask a question about the module
5. Generate a refactor plan
6. Generate a patch → review diff → apply

---

## Safety Mechanisms

- Safe path joining to prevent directory traversal
- File size truncation before sending to the LLM
- Diff preview before applying any change
- Temporary workspace per session

---

## Limitations

- Patch generation is limited to a single file at a time
- No automated test or lint validation before applying patches
- Limited context window (only selected files are sent to the LLM)
- Repository must be uploaded as a ZIP (no direct GitHub cloning)

---

## Roadmap

- Multi-file refactor patches
- GitHub repository URL ingestion
- ripgrep-based fast search
- Test and lint validation pipeline
- Patch rollback support
- Role-based analysis modes (security, performance, reviewer)

---

## Tech Stack

- Python 3.9+
- Streamlit
- Google Gemini API
- python-dotenv
- difflib (for unified diffs)

---

## Use Cases

- Understanding legacy codebases
- Planning refactors safely
- Identifying hardcoded secrets
- Generating architecture documentation
- Code review assistance
- Technical demos and interviews

---

## Author

Jeevan Tumkur Venkatesh  
MS Computer Science – Syracuse University  

GitHub:  
https://github.com/Jeevan-Tumkur-Venkatesh

---

## Summary

This project combines static repository tooling with LLM reasoning to accelerate code comprehension and refactoring. It provides structured insights, actionable plans, and controlled patch application to reduce the risk and effort involved in modifying unfamiliar codebases.
