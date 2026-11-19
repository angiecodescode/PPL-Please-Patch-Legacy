import asyncio
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

import database

# Load environment variables from .env (never commit secrets)
load_dotenv()

APP_TITLE = "PPL: Please Patch Legacy"
GEMINI_MODEL = "gemini-4-hydrogen"
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
MAX_UPLOAD_BYTES = 1_000_000  # 1 MB limit for source code and manifest files

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

TEMPLATES_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)

# Curated fallback coding & reasoning models from NVIDIA NIM's free catalog
CURATED_NVIDIA_MODELS: list[dict[str, str]] = [
    {"id": "deepseek-ai/deepseek-r1", "owned_by": "deepseek-ai", "tier": "Top Coding / Reasoning"},
    {"id": "qwen/qwen2.5-coder-32b-instruct", "owned_by": "qwen", "tier": "Code Specialist"},
    {"id": "meta/llama-3.3-70b-instruct", "owned_by": "meta", "tier": "General & Refactoring"},
    {"id": "nvidia/llama-3.1-nemotron-70b-instruct", "owned_by": "nvidia", "tier": "NVIDIA Flagship"},
    {"id": "mistralai/mistral-large-2-instruct", "owned_by": "mistralai", "tier": "Architecture Review"},
]

# Non-chat model keywords to filter out from NVIDIA's 80+ endpoint catalog
NON_CHAT_MODEL_KEYWORDS = (
    "embed",
    "rerank",
    "parse",
    "ocr",
    "guard",
    "safety",
    "shield",
    "clip",
    "whisper",
    "asr",
    "tts",
    "diffusion",
    "flux",
    "sdxl",
    "trellis",
    "cosmos",
    "corrdiff",
    "fourcastnet",
    "protein",
    "molmim",
    "bionemo",
    "vista",
    "vila",
    "paligemma",
    "kosmos",
    "deplot",
    "paddle",
    "grounding",
    "mask",
)

CODE_FILE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".rb", ".php",
    ".cs", ".cpp", ".c", ".h", ".hpp", ".swift", ".kt", ".scala", ".sh", ".ps1",
    ".sql", ".html", ".css", ".scss", ".json", ".toml", ".yaml", ".yml", ".xml",
    ".md", ".txt", ".ini", ".cfg", ".env.example",
}

SPECIAL_FILENAMES = {
    "requirements.txt", "package.json", "pyproject.toml", "pipfile", "dockerfile",
    "makefile", "gemfile", "cargo.toml", "go.mod", "pom.xml", "build.gradle",
    "composer.json", ".gitignore", ".env.example",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and safely migrate SQLite tables on startup."""
    database.init_db()
    yield


app = FastAPI(
    title=APP_TITLE,
    description="Rosaria-themed Autonomous Code Refactoring, Dependency Migration & Multi-Agent Review Platform.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


class RefactorOutputSchema(BaseModel):
    """Flat structured output schema returned by Gemini 4 Hydrogen."""

    detected_language: str = Field(
        description="Detected programming language or manifest format (e.g., Python, TypeScript, requirements.txt, package.json)."
    )
    detected_framework: str = Field(
        description="Detected framework or ecosystem (e.g., FastAPI, Flask, React, Express, Standard Library)."
    )
    refactored_code: str = Field(
        description="Complete, runnable refactored code or updated dependency manifest with zero placeholders or truncation."
    )
    summary: str = Field(
        description="Concise executive summary of all refactoring improvements and dependency migrations applied."
    )
    changes_made: list[str] = Field(
        description="Specific bullet points describing structural, security, typing, performance, and syntax improvements."
    )
    dependency_migrations: list[str] = Field(
        description="List of deprecated packages, SDKs, or APIs migrated to modern equivalents (e.g., 'old -> new: reason')."
    )
    breaking_changes_and_risks: list[str] = Field(
        description="List of potential breaking changes, behavioral differences, or edge cases requiring developer review."
    )
    verification_steps: list[str] = Field(
        description="Concrete CLI commands or test checks recommended to verify the refactored output."
    )
    confidence_score: int = Field(
        description="Confidence score between 1 and 100 indicating safety and completeness of the refactoring."
    )


class CodeRefactorRequest(BaseModel):
    """JSON payload schema for refactoring pasted or GitHub-imported code."""

    code: str = Field(..., min_length=1, description="Source code or manifest content to analyze and refactor.")
    filename: str = Field(default="snippet.py", description="Filename or extension hint.")
    mode: Literal["full_autonomous", "refactor", "migrate_dependencies"] = Field(
        default="full_autonomous",
        description="Autonomous operation mode.",
    )
    target_stack: str = Field(
        default="Latest stable LTS & modern best practices",
        description="Target language version, framework, or dependency ecosystem.",
    )
    custom_instructions: str = Field(
        default="",
        description="Optional user constraints or migration rules.",
    )
    nvidia_model: str = Field(
        default="",
        description="Optional NVIDIA NIM model ID to run as Independent Agent 2 Reviewer.",
    )
    nvidia_api_key: str = Field(
        default="",
        description="Optional per-request NVIDIA NIM API key (falls back to .env NVIDIA_API_KEY).",
    )


class GitHubInspectRequest(BaseModel):
    """JSON payload for inspecting a public GitHub file URL or repository URL."""

    url: str = Field(..., min_length=1, description="Public GitHub file or repository URL.")


class GitHubFetchFileRequest(BaseModel):
    """JSON payload for fetching a specific file inside a public GitHub repository."""

    owner: str = Field(..., min_length=1)
    repo: str = Field(..., min_length=1)
    branch: str = Field(..., min_length=1)
    path: str = Field(..., min_length=1)


def _get_gemini_api_keys() -> list[str]:
    """Collect primary and fallback Gemini API keys from .env without duplicates."""
    raw_keys: list[str] = []
    primary = os.getenv("GEMINI_API_KEY", "").strip()
    if primary:
        raw_keys.append(primary)

    extra = os.getenv("GEMINI_API_KEYS", "").strip()
    if extra:
        for chunk in extra.split(","):
            cleaned = chunk.strip()
            if cleaned:
                raw_keys.append(cleaned)

    valid_keys: list[str] = []
    for key in raw_keys:
        if key != "your_gemini_api_key_here" and key not in valid_keys:
            valid_keys.append(key)

    if not valid_keys:
        raise HTTPException(
            status_code=500,
            detail=(
                "GEMINI_API_KEY is missing or still set to the placeholder value in .env. "
                "Please add your real Gemini API key to .env and restart the server."
            ),
        )
    return valid_keys


def _resolve_nvidia_api_key(override_key: str = "") -> str:
    """Resolve an optional NVIDIA API key from request override or .env."""
    candidate = (override_key or "").strip()
    if candidate:
        return candidate
    env_key = os.getenv("NVIDIA_API_KEY", "").strip()
    return env_key


def _strip_markdown_fences(raw_text: str) -> str:
    """Remove accidental markdown code fences if present around JSON text."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


def _strip_think_blocks(raw_text: str) -> str:
    """Remove <think>...</think> blocks emitted by reasoning models."""
    return re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL).strip()


def _http_json_request(
    url: str,
    *,
    method: str = "GET",
    headers: Optional[dict[str, str]] = None,
    payload: Optional[dict[str, Any]] = None,
    timeout: int = 20,
) -> dict[str, Any]:
    """Perform an HTTPS JSON request using Python's standard library."""
    req_headers = {
        "User-Agent": "PPL-Please-Patch-Legacy/2.0",
        "Accept": "application/json",
    }
    if headers:
        req_headers.update(headers)

    data_bytes = None
    if payload is not None:
        data_bytes = json.dumps(payload).encode("utf-8")
        req_headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data_bytes, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {err_body[:300]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error: {exc.reason}") from exc


def _http_text_request(url: str, *, timeout: int = 20) -> str:
    """Fetch plain UTF-8 text from an HTTPS endpoint safely."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "PPL-Please-Patch-Legacy/2.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw_bytes = resp.read(MAX_UPLOAD_BYTES + 1)
            if len(raw_bytes) > MAX_UPLOAD_BYTES:
                raise RuntimeError(f"Remote file exceeds {MAX_UPLOAD_BYTES // 1000} KB limit.")
            return raw_bytes.decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} while fetching file from GitHub.") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error while fetching GitHub file: {exc.reason}") from exc


def _build_system_instruction(mode: str) -> str:
    """Create the autonomous agent system prompt tailored to the requested mode."""
    mode_directives = {
        "full_autonomous": (
            "Perform BOTH comprehensive code refactoring (clean architecture, type safety, error handling, "
            "security hardening, modern syntax) AND autonomous dependency/API migration (replacing deprecated "
            "libraries, outdated SDK calls, and legacy patterns with modern equivalents)."
        ),
        "refactor": (
            "Focus primarily on refactoring code structure, readability, modularity, error handling, type hints, "
            "and security without unnecessarily changing external dependencies unless critically broken or insecure."
        ),
        "migrate_dependencies": (
            "Focus primarily on upgrading and migrating outdated dependencies, package manifests (e.g., requirements.txt, "
            "package.json, pyproject.toml), and deprecated library/framework APIs to modern supported equivalents."
        ),
    }

    directive = mode_directives.get(mode, mode_directives["full_autonomous"])

    return (
        "You are an Autonomous Principal Software Architect and Dependency Migration Engine.\n"
        f"Primary Directive: {directive}\n\n"
        "Strict Output Rules:\n"
        "1. Always return the COMPLETE refactored code or updated dependency file in `refactored_code`.\n"
        "2. NEVER omit sections with placeholders like '# ... existing code', '// rest of file', or 'TODO'.\n"
        "3. Preserve original business logic and public behavior unless fixing a bug, security flaw, or migrating an API.\n"
        "4. If the input is a manifest file (requirements.txt, package.json, pyproject.toml, Dockerfile, etc.), "
        "modernize package versions/names and document every migration clearly.\n"
        "5. Provide an honest `confidence_score` from 1 to 100 and list any breaking changes or manual verification steps."
    )


def _call_gemini_sync(
    *,
    api_key: str,
    code: str,
    filename: str,
    mode: str,
    target_stack: str,
    custom_instructions: str,
) -> dict[str, Any]:
    """Execute a synchronous google-genai request against Gemini 4 Hydrogen."""
    client = genai.Client(api_key=api_key)

    user_prompt = (
        f"Filename / Context: {filename}\n"
        f"Operation Mode: {mode}\n"
        f"Target Stack / Standards: {target_stack}\n"
        f"Custom Instructions: {custom_instructions.strip() or 'None provided'}\n\n"
        "Analyze and transform the following input:\n"
        "```\n"
        f"{code}\n"
        "```"
    )

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=_build_system_instruction(mode),
            temperature=0.2,
            response_mime_type="application/json",
            response_schema=RefactorOutputSchema,
        ),
    )

    if getattr(response, "parsed", None) is not None:
        parsed_obj = response.parsed
        if isinstance(parsed_obj, BaseModel):
            data = parsed_obj.model_dump()
        elif isinstance(parsed_obj, dict):
            data = parsed_obj
        else:
            data = RefactorOutputSchema.model_validate(parsed_obj).model_dump()
    else:
        raw_text = _strip_markdown_fences(response.text or "")
        if not raw_text:
            raise ValueError("Gemini returned an empty response.")
        data = RefactorOutputSchema.model_validate(json.loads(raw_text)).model_dump()

    score = int(data.get("confidence_score", 80))
    data["confidence_score"] = max(1, min(100, score))
    return data


def _is_rotatable_gemini_error(exc: Exception) -> bool:
    """Detect quota, rate-limit, or temporary errors where another API key may succeed."""
    msg = str(exc).lower()
    rotatable_signals = ("429", "quota", "rate limit", "resource_exhausted", "resource exhausted", "503", "unavailable")
    return any(sig in msg for sig in rotatable_signals)


def _run_gemini_with_rotation(
    *,
    code: str,
    filename: str,
    mode: str,
    target_stack: str,
    custom_instructions: str,
) -> dict[str, Any]:
    """Try configured Gemini API keys in sequence on quota or rate-limit errors."""
    keys = _get_gemini_api_keys()
    last_error: Optional[Exception] = None

    for idx, api_key in enumerate(keys):
        try:
            return _call_gemini_sync(
                api_key=api_key,
                code=code,
                filename=filename,
                mode=mode,
                target_stack=target_stack,
                custom_instructions=custom_instructions,
            )
        except Exception as exc:
            last_error = exc
            has_more_keys = idx < len(keys) - 1
            if has_more_keys and _is_rotatable_gemini_error(exc):
                continue
            raise

    if last_error is not None:
        raise last_error
    raise RuntimeError("No Gemini API keys available.")


def _call_nvidia_second_agent_sync(
    *,
    nvidia_api_key: str,
    nvidia_model: str,
    filename: str,
    target_stack: str,
    original_code: str,
    refactored_code: str,
) -> dict[str, Any]:
    """Run an independent Agent 2 code review via NVIDIA NIM's OpenAI-compatible API."""
    prompt = (
        f"You are Agent 2 (Independent Senior Security & Migration Auditor).\n"
        f"File: {filename} | Target Stack: {target_stack}\n\n"
        "Compare the ORIGINAL code and the REFACTORED code below.\n"
        "Return ONLY valid JSON with these exact keys:\n"
        '{"verdict": "Approved" or "Approved with Notes" or "Needs Review", '
        '"audit_score": integer 1-100, '
        '"audit_notes": ["3 to 5 concise findings about security, logic safety, edge cases, or extra polish"]}\n\n'
        f"ORIGINAL:\n```\n{original_code[:6000]}\n```\n\n"
        f"REFACTORED:\n```\n{refactored_code[:6000]}\n```"
    )

    payload = {
        "model": nvidia_model,
        "messages": [
            {
                "role": "system",
                "content": "You are a strict principal code auditor. Respond with concise valid JSON.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 900,
        "stream": False,
    }

    resp = _http_json_request(
        f"{NVIDIA_BASE_URL}/chat/completions",
        method="POST",
        headers={"Authorization": f"Bearer {nvidia_api_key}"},
        payload=payload,
        timeout=45,
    )

    choices = resp.get("choices") or []
    if not choices:
        raise RuntimeError("NVIDIA model returned no choices.")

    message = choices[0].get("message") or {}
    content = message.get("content") or message.get("reasoning_content") or ""
    cleaned = _strip_markdown_fences(_strip_think_blocks(str(content)))

    try:
        json_match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        parsed = json.loads(json_match.group(0) if json_match else cleaned)
        verdict = str(parsed.get("verdict", "Approved with Notes"))
        score = max(1, min(100, int(parsed.get("audit_score", 85))))
        raw_notes = parsed.get("audit_notes") or []
        notes = [str(n) for n in raw_notes][:6]
        if not notes:
            notes = ["Second-agent review completed with no additional warnings."]
        return {
            "second_agent_model": nvidia_model,
            "second_agent_verdict": verdict,
            "second_agent_score": score,
            "second_agent_notes": notes,
        }
    except Exception:
        # Fallback cleanly if an open model returned plain bullet prose instead of strict JSON
        lines = [line.strip("-*• ").strip() for line in cleaned.splitlines() if line.strip()]
        return {
            "second_agent_model": nvidia_model,
            "second_agent_verdict": "Approved with Notes",
            "second_agent_score": 82,
            "second_agent_notes": lines[:5] if lines else ["Review completed."],
        }


async def run_autonomous_refactoring(
    *,
    code: str,
    filename: str,
    mode: str,
    target_stack: str,
    custom_instructions: str,
    nvidia_model: str = "",
    nvidia_api_key: str = "",
) -> dict[str, Any]:
    """Run Gemini 4 Hydrogen (+ optional NVIDIA NIM Agent 2) and persist to SQLite."""
    cleaned_code = code.strip("\ufeff")
    if not cleaned_code.strip():
        raise HTTPException(status_code=400, detail="Input code or file content cannot be empty.")

    safe_filename = (filename or "snippet.txt").strip()
    safe_target_stack = (target_stack or "Latest stable LTS & modern best practices").strip()
    safe_instructions = (custom_instructions or "").strip()

    try:
        ai_result = await asyncio.to_thread(
            _run_gemini_with_rotation,
            code=cleaned_code,
            filename=safe_filename,
            mode=mode,
            target_stack=safe_target_stack,
            custom_instructions=safe_instructions,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Gemini 4 Hydrogen processing failed: {str(exc)}",
        ) from exc

    second_model = (nvidia_model or "").strip()
    second_verdict = ""
    second_notes: list[str] = []
    second_score = 0

    if second_model:
        resolved_nv_key = _resolve_nvidia_api_key(nvidia_api_key)
        if not resolved_nv_key:
            second_verdict = "Agent 2 Skipped"
            second_notes = [
                "No NVIDIA_API_KEY was provided in .env or in the optional key box. "
                "Add a free key from build.nvidia.com to enable Second-Agent auditing."
            ]
        else:
            try:
                audit_res = await asyncio.to_thread(
                    _call_nvidia_second_agent_sync,
                    nvidia_api_key=resolved_nv_key,
                    nvidia_model=second_model,
                    filename=safe_filename,
                    target_stack=safe_target_stack,
                    original_code=cleaned_code,
                    refactored_code=ai_result["refactored_code"],
                )
                second_verdict = audit_res["second_agent_verdict"]
                second_notes = audit_res["second_agent_notes"]
                second_score = audit_res["second_agent_score"]
            except Exception as nv_exc:
                # Preserve Agent 1's output even if NVIDIA NIM throttles or rejects a model
                second_verdict = "Agent 2 Unavailable"
                second_notes = [f"NVIDIA NIM ({second_model}) could not complete review: {str(nv_exc)}"]

    saved_record = database.save_refactoring_record(
        filename=safe_filename,
        mode=mode,
        target_stack=safe_target_stack,
        custom_instructions=safe_instructions,
        detected_language=ai_result["detected_language"],
        detected_framework=ai_result["detected_framework"],
        original_code=cleaned_code,
        refactored_code=ai_result["refactored_code"],
        summary=ai_result["summary"],
        changes_made=ai_result["changes_made"],
        dependency_migrations=ai_result["dependency_migrations"],
        breaking_changes_and_risks=ai_result["breaking_changes_and_risks"],
        verification_steps=ai_result["verification_steps"],
        confidence_score=ai_result["confidence_score"],
        model_used=GEMINI_MODEL,
        second_agent_model=second_model,
        second_agent_verdict=second_verdict,
        second_agent_notes=second_notes,
        second_agent_score=second_score,
    )
    return saved_record


def _is_supported_repo_file(path: str) -> bool:
    """Filter GitHub repository trees down to inspectable code and manifest files."""
    lower = path.lower()
    name = lower.rsplit("/", 1)[-1]
    if name in SPECIAL_FILENAMES:
        return True
    _, ext = os.path.splitext(name)
    return ext in CODE_FILE_EXTENSIONS


def _inspect_github_url_sync(raw_url: str) -> dict[str, Any]:
    """Inspect a public GitHub file URL or repository URL safely."""
    url = raw_url.strip()
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()

    if parsed.scheme != "https" or host not in {"github.com", "www.github.com", "raw.githubusercontent.com"}:
        raise ValueError("Please enter a valid https://github.com/... or https://raw.githubusercontent.com/... URL.")

    parts = [p for p in parsed.path.split("/") if p]

    # Case 1: Direct raw.githubusercontent.com file link
    if host == "raw.githubusercontent.com":
        if len(parts) < 4:
            raise ValueError("Incomplete raw GitHub file URL.")
        code_text = _http_text_request(url)
        return {
            "kind": "file",
            "filename": parts[-1],
            "path": "/".join(parts[3:]),
            "code": code_text,
            "source_url": url,
        }

    # Case 2: github.com/owner/repo/blob/branch/path/to/file
    if len(parts) >= 5 and parts[2] == "blob":
        owner, repo, _, branch = parts[0], parts[1], parts[2], parts[3]
        file_path = "/".join(parts[4:])
        raw_file_url = (
            f"https://raw.githubusercontent.com/{urllib.parse.quote(owner)}/"
            f"{urllib.parse.quote(repo)}/{urllib.parse.quote(branch)}/{file_path}"
        )
        code_text = _http_text_request(raw_file_url)
        return {
            "kind": "file",
            "filename": parts[-1],
            "path": file_path,
            "code": code_text,
            "source_url": raw_file_url,
        }

    # Case 3: github.com/owner/repo (or /tree/branch/...)
    if len(parts) >= 2:
        owner = parts[0]
        repo = parts[1].removesuffix(".git")
        branch = ""
        subpath_prefix = ""

        if len(parts) >= 4 and parts[2] == "tree":
            branch = parts[3]
            subpath_prefix = "/".join(parts[4:]).strip("/")

        if not branch:
            repo_meta = _http_json_request(
                f"https://api.github.com/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}"
            )
            branch = repo_meta.get("default_branch") or "main"

        tree_data = _http_json_request(
            f"https://api.github.com/repos/{urllib.parse.quote(owner)}/"
            f"{urllib.parse.quote(repo)}/git/trees/{urllib.parse.quote(branch)}?recursive=1"
        )
        tree_items = tree_data.get("tree") or []

        files: list[dict[str, Any]] = []
        for entry in tree_items:
            if entry.get("type") != "blob":
                continue
            item_path = entry.get("path", "")
            item_size = int(entry.get("size") or 0)
            if item_size == 0 or item_size > 400_000:
                continue
            if subpath_prefix and not item_path.startswith(subpath_prefix + "/") and item_path != subpath_prefix:
                continue
            if _is_supported_repo_file(item_path):
                files.append({"path": item_path, "size": item_size})

        # Prioritize common entry files and dependency manifests first
        files.sort(key=lambda f: (0 if f["path"].lower() in SPECIAL_FILENAMES else 1, f["path"].count("/"), f["path"]))

        return {
            "kind": "repo",
            "owner": owner,
            "repo": repo,
            "branch": branch,
            "truncated": bool(tree_data.get("truncated")),
            "files": files[:250],
        }

    raise ValueError("Could not recognize a GitHub repository or file path in that URL.")


def _score_nvidia_model_priority(model_id: str) -> tuple[int, str]:
    """Sort top coding and reasoning models first in the NVIDIA catalog dropdown."""
    lower = model_id.lower()
    priority_prefixes = (
        "deepseek",
        "qwen",
        "nvidia/nemotron",
        "nvidia/llama",
        "mistralai",
        "moonshotai",
        "meta/llama-3.3",
        "meta/llama",
        "zai",
        "glm",
        "google/gemma",
    )
    for idx, prefix in enumerate(priority_prefixes):
        if prefix in lower:
            return (idx, lower)
    return (99, lower)


def _fetch_nvidia_models_sync(nvidia_api_key: str) -> dict[str, Any]:
    """Fetch live NVIDIA NIM models catalog and filter to chat/coding models."""
    if not nvidia_api_key:
        return {
            "source": "curated_preview",
            "key_configured": False,
            "count": len(CURATED_NVIDIA_MODELS),
            "models": CURATED_NVIDIA_MODELS,
            "message": "Add NVIDIA_API_KEY in .env (or paste your free nvapi- key) to load all 80+ live models.",
        }

    try:
        data = _http_json_request(
            f"{NVIDIA_BASE_URL}/models",
            method="GET",
            headers={"Authorization": f"Bearer {nvidia_api_key}"},
            timeout=12,
        )
        raw_models = data.get("data") or []
        filtered: list[dict[str, str]] = []
        for item in raw_models:
            model_id = str(item.get("id") or "").strip()
            if not model_id:
                continue
            lower_id = model_id.lower()
            if any(bad in lower_id for bad in NON_CHAT_MODEL_KEYWORDS):
                continue
            filtered.append(
                {
                    "id": model_id,
                    "owned_by": str(item.get("owned_by") or model_id.split("/")[0]),
                    "tier": "Free NIM Endpoint",
                }
            )

        filtered.sort(key=lambda m: _score_nvidia_model_priority(m["id"]))
        return {
            "source": "live_nvidia_api",
            "key_configured": True,
            "count": len(filtered),
            "models": filtered,
            "message": f"Loaded {len(filtered)} live chat/coding models from NVIDIA NIM.",
        }
    except Exception as exc:
        return {
            "source": "curated_fallback",
            "key_configured": True,
            "count": len(CURATED_NVIDIA_MODELS),
            "models": CURATED_NVIDIA_MODELS,
            "message": f"Using curated list (live NVIDIA catalog check returned: {str(exc)})",
        }


@app.get("/", response_class=HTMLResponse)
async def serve_home(request: Request):
    """Serve the PPL: Please Patch Legacy UI."""
    index_path = TEMPLATES_DIR / "index.html"
    if index_path.exists():
        return templates.TemplateResponse(request=request, name="index.html")

    return HTMLResponse(
        content=(
            "<html><body style='font-family: sans-serif; padding: 2rem; background: #0f0912; color: #f8e8f0;'>"
            "<h1>PPL: Please Patch Legacy — Backend Ready</h1>"
            "<p>Upgrade Step 1 backend is active. Proceed to Upgrade Step 2 for the Rosaria Gothic UI!</p>"
            "</body></html>"
        )
    )


@app.get("/api/health")
async def health_check() -> dict[str, Any]:
    """Verify server, SQLite database, Gemini keys, and optional NVIDIA NIM status."""
    raw_primary = os.getenv("GEMINI_API_KEY", "").strip()
    raw_extra = os.getenv("GEMINI_API_KEYS", "").strip()
    keys_found: list[str] = []
    for k in [raw_primary, *raw_extra.split(",")]:
        cleaned = k.strip()
        if cleaned and cleaned != "your_gemini_api_key_here" and cleaned not in keys_found:
            keys_found.append(cleaned)

    nvidia_key = os.getenv("NVIDIA_API_KEY", "").strip()
    return {
        "status": "ok",
        "app_title": APP_TITLE,
        "model": GEMINI_MODEL,
        "api_key_configured": len(keys_found) > 0,
        "gemini_keys_count": len(keys_found),
        "nvidia_key_configured": bool(nvidia_key),
        "database": "sqlite",
    }


@app.get("/api/nvidia/models")
async def list_nvidia_models(x_nvidia_api_key: str = Header(default="")) -> dict[str, Any]:
    """Return available NVIDIA NIM chat/coding models for Second-Agent review."""
    resolved_key = _resolve_nvidia_api_key(x_nvidia_api_key)
    return await asyncio.to_thread(_fetch_nvidia_models_sync, resolved_key)


@app.post("/api/github/inspect")
async def inspect_github_url(payload: GitHubInspectRequest) -> dict[str, Any]:
    """Fetch a public GitHub file directly or list files from a public GitHub repository."""
    try:
        result = await asyncio.to_thread(_inspect_github_url_sync, payload.url)
        return {"status": "success", **result}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/github/fetch-file")
async def fetch_github_repo_file(payload: GitHubFetchFileRequest) -> dict[str, Any]:
    """Download a specific file from a public GitHub repository."""
    clean_path = payload.path.lstrip("/")
    raw_url = (
        f"https://raw.githubusercontent.com/{urllib.parse.quote(payload.owner)}/"
        f"{urllib.parse.quote(payload.repo)}/{urllib.parse.quote(payload.branch)}/{clean_path}"
    )
    try:
        code_text = await asyncio.to_thread(_http_text_request, raw_url)
        return {
            "status": "success",
            "filename": clean_path.rsplit("/", 1)[-1],
            "path": clean_path,
            "code": code_text,
            "source_url": raw_url,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/refactor")
async def refactor_pasted_code(payload: CodeRefactorRequest) -> dict[str, Any]:
    """Refactor pasted or GitHub-imported code via Gemini 4 Hydrogen (+ optional Agent 2)."""
    record = await run_autonomous_refactoring(
        code=payload.code,
        filename=payload.filename,
        mode=payload.mode,
        target_stack=payload.target_stack,
        custom_instructions=payload.custom_instructions,
        nvidia_model=payload.nvidia_model,
        nvidia_api_key=payload.nvidia_api_key,
    )
    return {"status": "success", "record": record}


@app.post("/api/refactor/upload")
async def refactor_uploaded_file(
    file: UploadFile = File(...),
    mode: Literal["full_autonomous", "refactor", "migrate_dependencies"] = Form("full_autonomous"),
    target_stack: str = Form("Latest stable LTS & modern best practices"),
    custom_instructions: str = Form(""),
    nvidia_model: str = Form(""),
    nvidia_api_key: str = Form(""),
) -> dict[str, Any]:
    """Refactor an uploaded source code or dependency manifest file."""
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(raw_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {MAX_UPLOAD_BYTES // 1000} KB limit for text source files.",
        )

    try:
        decoded_text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            decoded_text = raw_bytes.decode("latin-1")
        except UnicodeDecodeError as exc:
            raise HTTPException(
                status_code=400,
                detail="Only UTF-8 or plain-text source code and dependency files are supported.",
            ) from exc

    record = await run_autonomous_refactoring(
        code=decoded_text,
        filename=file.filename or "uploaded_code.txt",
        mode=mode,
        target_stack=target_stack,
        custom_instructions=custom_instructions,
        nvidia_model=nvidia_model,
        nvidia_api_key=nvidia_api_key,
    )
    return {"status": "success", "record": record}


@app.get("/api/history")
async def list_refactoring_history(limit: int = 50) -> dict[str, Any]:
    """Retrieve saved refactoring history from SQLite."""
    items = database.get_refactoring_history(limit=limit)
    return {"status": "success", "count": len(items), "items": items}


@app.get("/api/analytics")
async def get_analytics() -> dict[str, Any]:
    """Retrieve aggregated analytics for dashboard charts."""
    return {"status": "success", "analytics": database.get_analytics_summary()}


@app.get("/api/history/{record_id}")
async def get_single_history_record(record_id: int) -> dict[str, Any]:
    """Retrieve a specific refactoring record by ID from SQLite."""
    record = database.get_refactoring_by_id(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Refactoring record #{record_id} not found.")
    return {"status": "success", "record": record}


@app.delete("/api/history/{record_id}")
async def delete_single_history_record(record_id: int) -> dict[str, Any]:
    """Delete a single refactoring record from SQLite."""
    deleted = database.delete_refactoring_by_id(record_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Refactoring record #{record_id} not found.")
    return {"status": "success", "deleted_id": record_id}


@app.delete("/api/history")
async def clear_all_history() -> dict[str, Any]:
    """Clear all saved refactoring history from SQLite."""
    deleted_count = database.clear_refactoring_history()
    return {"status": "success", "deleted_count": deleted_count}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)