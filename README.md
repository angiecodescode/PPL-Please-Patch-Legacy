# PPL: Please Patch Legacy

> *An AI-Powered Autonomous Code Refactoring, Dependency Migration & Dual-Agent Audit Studio — styled after Rosaria's Indenture namecard from Genshin Impact.*

![Python](https://img.shields.io/badge/Python-3.11%2B-9c4e60?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-ad556c?style=flat-square)
![SQLite](https://img.shields.io/badge/SQLite-Persistent_History-7c3749?style=flat-square)
![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-Gothic_UI-d5a3aa?style=flat-square)

---

## Why I Built PPL

PPL: Please Patch Legacy was built to rescue developers from unc-ish (brittle) legacy codebases and outdated dependencies.

TBH, this started out to rescue myself from the pain of manually researching outdated library migrations and cleaning messy code/datasets, after God knows how many days and constant questioning of my life choices i somehow made this. I originally started with one free AI model, and after larping on Instagram for days, I discovered NVIDIA's free developer API catalog too, so I hooked both together for an optional Second-Agent audit. The visual theme was inspired by Rosaria's *Indenture* namecard (Genshin Impact), and the name **PPL** came straight from my tears and backpain and my receding hairline. and i am new to fullstack and ngl this was a very difficult project to do, it took a while(more then a month) to wrap my head around it. thanks for reading.

---

## Key Features

- **3 Flexible Input Modes:** Paste raw code/manifests, drag-and-drop local files (`requirements.txt`, `package.json`, `.py`, `.js`, `.ts`, etc.), or paste a **public GitHub file/repository URL** to browse and patch files directly.
- **16 Migration Goal Presets:** Python 2 -> Python 3.12+, Flask -> FastAPI + Pydantic v2, Legacy Django -> Django 5, Sync `requests` -> Async `httpx`, Pydantic v1 -> v2, SQLAlchemy 1.x -> 2.0, Legacy JS -> TypeScript, React Class -> Hooks, Security Hardening, and more.
- **Dual-Agent Architecture:**
  - **Primary Agent:** Autonomous refactoring & dependency migration via the official `google-genai` SDK (`gemini-4-hydrogen`) with multi-key rotation support.
  - **Optional Agent 2 Auditor:** Connects to NVIDIA NIM's live free model catalog (DeepSeek, Qwen, Nemotron, Llama, Mistral, etc.) to independently audit the patched output for bugs, edge cases, and security issues.
- **Side-by-Side Before vs. After & Unified Line Diff:** Synchronized dual-pane code comparison, inline `- / +` line-by-line LCS diffing, radial confidence gauge, and 1-click file download.
- **SQLite Telemetry & Charts:** Automatically persists every patch in local SQLite (`refactoring_history.db`) and renders live line-count and language distribution charts.
- **Rosaria Gothic Studio + Live Theme Switcher:** Switch anytime between **Rosaria (Indenture)**, **Bloodmoon Crimson**, and **Cathedral Rose (Light)**.

---

## Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Backend** | Python 3, FastAPI, Uvicorn |
| **Primary AI Engine** | Official `google-genai` SDK (`gemini-4-hydrogen`) |
| **Optional Agent 2** | NVIDIA NIM OpenAI-compatible API (`build.nvidia.com`) |
| **Database** | SQLite (`sqlite3`) with automatic schema migration |
| **Frontend** | HTML5, Tailwind CSS (CDN), Vanilla JavaScript, Custom SVG Art |
| **Security** | `.env` via `python-dotenv`, strict GitHub-only URL allowlist for repo fetching |

---

## Run Locally in 4 Steps

### 1. Clone the repository
```bash
git clone https://github.com/angiecodescode/PPL-Please-Patch-Legacy.git
cd PPL-Please-Patch-Legacy
```

### 2. Create & activate a virtual environment
**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure your `.env` file
Copy `.env.example` to `.env` and add your keys:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_API_KEYS=
NVIDIA_API_KEY=
```
- Get a Gemini API key from **Google AI Studio**.
- *(Optional)* Get a free `nvapi-...` key from **build.nvidia.com** to unlock the live catalog for Agent 2 auditing.

### 4. Start the server
```bash
python -m uvicorn main:app --reload
```
Open **`http://127.0.0.1:8000`** in your browser.

---

## Project Structure

```text
├── .env.example          # Environment variable template (secrets excluded via .gitignore)
├── .gitignore            # Protects .env, virtual environments, and local .db files
├── README.md             # Project documentation
├── requirements.txt      # Python dependencies
├── database.py           # SQLite storage, auto-migrations, and analytics queries
├── main.py               # FastAPI server, AI orchestration, and GitHub URL importer
├── static/
│   └── app.js            # Vanilla JS client, LCS diffing, charts, and theme switcher
└── templates/
    └── index.html        # Rosaria-themed HTML + Tailwind CSS workbench
```

---

## Contributing

Contributions, new migration presets, and bug fixes are always welcome! Feel free to open an issue or submit a pull request and feel free to yap. tbh i am new to fullstack to feel free to advice on any flaws.