document.addEventListener("DOMContentLoaded", () => {
    const DEFAULT_ABOUT_TEXT =
        "PPL: Please Patch Legacy was built to rescue developers from unc-ish (brittle) legacy codebases and outdated dependencies. " +
        "Paste legacy snippets, upload manifests like requirements.txt or package.json, or import straight from a public GitHub repository, " +
        "then inspect a side-by-side Before vs. After breakdown with optional Second-Agent security auditing. " +
        "TBH this was made to rescue myself from the pain of manually researching topics and cleaning messy datasets—this took me idk how many days and constant questioning of my life choices. " +
        "I originally had to use one AI model that is free CUZ NONE IS FREE THESE DAYS, but after larping a few days on Insta I found out the AI chip company had free AI models too, so like a hungry dawg I lunged on that and hooked it in here. " +
        "The theme was inspired by Rosaria—specifically her Indenture namecard (from Genshin Impact)—and the name PPL was inspired by my tears and backpain.";

    const GOAL_PRESETS = {
        full_autonomous: {
            mode: "full_autonomous",
            targetStack: "Latest stable LTS & modern best practices",
        },
        py2to3: {
            mode: "full_autonomous",
            targetStack: "Python 3.12+ (f-strings, pathlib, typing, modern standard library)",
        },
        flask_to_fastapi: {
            mode: "full_autonomous",
            targetStack: "FastAPI + Pydantic v2 + Async endpoints + type annotations",
        },
        django_modern: {
            mode: "full_autonomous",
            targetStack: "Modern Django 5.x with async views, path() routing, and clean ORM queries",
        },
        requests_to_httpx: {
            mode: "full_autonomous",
            targetStack: "Async httpx.AsyncClient with timeouts, retries, and structured error handling",
        },
        pydantic_v1_to_v2: {
            mode: "migrate_dependencies",
            targetStack: "Pydantic v2 (model_validate, model_dump, ConfigDict, field_validator)",
        },
        sqlalchemy_1_to_2: {
            mode: "full_autonomous",
            targetStack: "SQLAlchemy 2.0 (Mapped, mapped_column, select() statements, async-ready)",
        },
        clean_code: {
            mode: "refactor",
            targetStack: "Clean Code, SOLID architecture, strict typing, and defensive error handling",
        },
        security_hardening: {
            mode: "refactor",
            targetStack: "OWASP-hardened code (parameterized SQL, no hardcoded secrets, safe input validation)",
        },
        perf_async: {
            mode: "refactor",
            targetStack: "High-performance async concurrency, O(n) algorithms, and minimal allocations",
        },
        upgrade_deps: {
            mode: "migrate_dependencies",
            targetStack: "Latest stable LTS packages and modern non-deprecated library equivalents",
        },
        js_to_ts: {
            mode: "full_autonomous",
            targetStack: "Modern ES2024+ / TypeScript with async-await and strict interfaces",
        },
        react_class_to_hooks: {
            mode: "full_autonomous",
            targetStack: "Modern React Functional Components with Hooks (useState, useEffect, useCallback)",
        },
        cjs_to_esm: {
            mode: "migrate_dependencies",
            targetStack: "Modern ES Modules (import/export) replacing CommonJS require/module.exports",
        },
        unit_tests: {
            mode: "refactor",
            targetStack: "Comprehensive unit test suite (Pytest / Vitest) covering edge cases and mocks",
        },
    };

    const SAMPLE_SNIPPETS = {
        py2: {
            filename: "legacy_fetcher.py",
            goal: "py2to3",
            code: [
                "import urllib2",
                "import ConfigParser",
                "",
                "def fetch_users(urls, headers):",
                "    results = {}",
                "    for i in xrange(len(urls)):",
                "        url = urls[i]",
                "        try:",
                "            req = urllib2.Request(url, headers=headers)",
                "            resp = urllib2.urlopen(req)",
                "            results[url] = resp.read()",
                "        except urllib2.URLError, e:",
                "            print 'Failed to fetch %s: %s' % (url, e)",
                "    for k, v in results.iteritems():",
                "        print k, len(v)",
                "    return results",
            ].join("\n"),
        },
        flask: {
            filename: "flask_users_api.py",
            goal: "flask_to_fastapi",
            code: [
                "from flask import Flask, request, jsonify",
                "import sqlite3",
                "",
                "app = Flask(__name__)",
                "",
                "@app.route('/users/<int:user_id>', methods=['GET'])",
                "def get_user(user_id):",
                "    conn = sqlite3.connect('users.db')",
                "    cur = conn.cursor()",
                "    cur.execute('SELECT id, name, email FROM users WHERE id = %s' % user_id)",
                "    row = cur.fetchone()",
                "    conn.close()",
                "    if not row:",
                "        return jsonify({'error': 'Not found'}), 404",
                "    return jsonify({'id': row[0], 'name': row[1], 'email': row[2]}), 200",
                "",
                "@app.route('/users', methods=['POST'])",
                "def create_user():",
                "    data = request.get_json()",
                "    if not data or 'name' not in data or 'email' not in data:",
                "        return jsonify({'error': 'Missing fields'}), 400",
                "    return jsonify({'status': 'created', 'user': data}), 201",
                "",
                "if __name__ == '__main__':",
                "    app.run(debug=True, port=5000)",
            ].join("\n"),
        },
        deps: {
            filename: "requirements.txt",
            goal: "upgrade_deps",
            code: [
                "Flask==0.12.2",
                "Werkzeug==0.14.1",
                "requests==2.18.4",
                "pycrypto==2.6.1",
                "pydantic==1.10.2",
                "nose==1.3.7",
                "python-jose==3.1.0",
                "SQLAlchemy==1.3.24",
            ].join("\n"),
        },
        js: {
            filename: "legacy_orders.js",
            goal: "js_to_ts",
            code: [
                "var request = require('request');",
                "",
                "function getOrderDetails(orderId, callback) {",
                "    var url = 'https://api.example.com/orders/' + orderId;",
                "    request(url, function (err, response, body) {",
                "        if (err) {",
                "            return callback(err, null);",
                "        }",
                "        var parsed = JSON.parse(body);",
                "        callback(null, parsed);",
                "    });",
                "}",
                "",
                "module.exports = { getOrderDetails: getOrderDetails };",
            ].join("\n"),
        },
    };

    const state = {
        inputSource: "paste",
        selectedFile: null,
        currentRecord: null,
        viewMode: "side-by-side",
        isSyncingScroll: false,
        nvidiaModels: [],
        githubRepo: null,
    };

    // Header, Theme & Status
    const themeSelect = document.getElementById("theme-select");
    const healthDot = document.getElementById("health-dot");
    const healthText = document.getElementById("health-text");
    const apiKeyWarning = document.getElementById("api-key-warning");
    const historyCountPill = document.getElementById("history-count-pill");
    const errorBanner = document.getElementById("error-banner");
    const errorMessage = document.getElementById("error-message");
    const dismissErrorBtn = document.getElementById("dismiss-error-btn");

    // Analytics & Charts
    const statTotalRuns = document.getElementById("stat-total-runs");
    const statAvgConf = document.getElementById("stat-avg-conf");
    const statTotalMigrations = document.getElementById("stat-total-migrations");
    const statDualRuns = document.getElementById("stat-dual-runs");
    const chartLinesTrend = document.getElementById("chart-lines-trend");
    const chartLanguages = document.getElementById("chart-languages");

    // Input Tabs & Panels
    const tabPaste = document.getElementById("tab-paste");
    const tabUpload = document.getElementById("tab-upload");
    const tabGithub = document.getElementById("tab-github");
    const panelPaste = document.getElementById("panel-paste");
    const panelUpload = document.getElementById("panel-upload");
    const panelGithub = document.getElementById("panel-github");

    const filenameInput = document.getElementById("filename-input");
    const codeInput = document.getElementById("code-input");
    const inputStats = document.getElementById("input-stats");
    const clearCodeBtn = document.getElementById("clear-code-btn");

    const samplePy2Btn = document.getElementById("sample-py2");
    const sampleFlaskBtn = document.getElementById("sample-flask");
    const sampleDepsBtn = document.getElementById("sample-deps");
    const sampleJsBtn = document.getElementById("sample-js");

    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");
    const filePreviewBox = document.getElementById("file-preview-box");
    const selectedFileName = document.getElementById("selected-file-name");
    const selectedFileMeta = document.getElementById("selected-file-meta");
    const clearFileBtn = document.getElementById("clear-file-btn");

    const githubUrlInput = document.getElementById("github-url-input");
    const githubInspectBtn = document.getElementById("github-inspect-btn");
    const githubStatus = document.getElementById("github-status");
    const githubRepoBrowser = document.getElementById("github-repo-browser");
    const githubRepoMeta = document.getElementById("github-repo-meta");
    const githubFileSearch = document.getElementById("github-file-search");
    const githubFileList = document.getElementById("github-file-list");

    // Goal & Dual Agents
    const goalSelect = document.getElementById("goal-select");
    const modeSelect = document.getElementById("mode-select");
    const targetStackInput = document.getElementById("target-stack-input");
    const instructionsInput = document.getElementById("instructions-input");

    const enableAgent2Checkbox = document.getElementById("enable-agent2-checkbox");
    const agent2Panel = document.getElementById("agent2-panel");
    const nvidiaModelSearch = document.getElementById("nvidia-model-search");
    const nvidiaModelSelect = document.getElementById("nvidia-model-select");
    const nvidiaModelsStatus = document.getElementById("nvidia-models-status");
    const nvidiaCustomKeyInput = document.getElementById("nvidia-custom-key-input");
    const refreshNvidiaModelsBtn = document.getElementById("refresh-nvidia-models-btn");

    const runRefactorBtn = document.getElementById("run-refactor-btn");
    const runBtnIcon = document.getElementById("run-btn-icon");
    const runBtnSpinner = document.getElementById("run-btn-spinner");
    const runBtnText = document.getElementById("run-btn-text");
    const loadingStatus = document.getElementById("loading-status");

    // Results Workbench
    const emptyWorkbench = document.getElementById("empty-workbench");
    const resultsSection = document.getElementById("results-section");
    const resFilename = document.getElementById("res-filename");
    const resLanguage = document.getElementById("res-language");
    const resFramework = document.getElementById("res-framework");
    const resMode = document.getElementById("res-mode");
    const resLinesDelta = document.getElementById("res-lines-delta");
    const resTargetStack = document.getElementById("res-target-stack");
    const resConfidenceRing = document.getElementById("res-confidence-ring");
    const resConfidenceText = document.getElementById("res-confidence-text");

    const viewSideBySideBtn = document.getElementById("view-side-by-side-btn");
    const viewDiffBtn = document.getElementById("view-diff-btn");
    const syncScrollLabel = document.getElementById("sync-scroll-label");
    const syncScrollCheckbox = document.getElementById("sync-scroll-checkbox");
    const copyAfterBtn = document.getElementById("copy-after-btn");
    const copyAfterText = document.getElementById("copy-after-text");
    const downloadAfterBtn = document.getElementById("download-after-btn");
    const sideBySideView = document.getElementById("side-by-side-view");
    const diffView = document.getElementById("diff-view");
    const diffContent = document.getElementById("diff-content");
    const beforeScroll = document.getElementById("before-scroll");
    const afterScroll = document.getElementById("after-scroll");
    const beforeLineCount = document.getElementById("before-line-count");
    const afterLineCount = document.getElementById("after-line-count");

    const agent2ResultCard = document.getElementById("agent2-result-card");
    const agent2ModelBadge = document.getElementById("agent2-model-badge");
    const agent2VerdictBadge = document.getElementById("agent2-verdict-badge");
    const agent2ScoreText = document.getElementById("agent2-score-text");
    const agent2NotesList = document.getElementById("agent2-notes-list");

    const resSummary = document.getElementById("res-summary");
    const resMigrationsList = document.getElementById("res-migrations-list");
    const resChangesList = document.getElementById("res-changes-list");
    const resRisksList = document.getElementById("res-risks-list");
    const resVerificationList = document.getElementById("res-verification-list");

    // History & About
    const historyList = document.getElementById("history-list");
    const refreshHistoryBtn = document.getElementById("refresh-history-btn");
    const clearHistoryBtn = document.getElementById("clear-history-btn");

    const editAboutBtn = document.getElementById("edit-about-btn");
    const aboutDisplay = document.getElementById("about-display");
    const aboutCustomText = document.getElementById("about-custom-text");
    const aboutEditor = document.getElementById("about-editor");
    const aboutTextarea = document.getElementById("about-textarea");
    const saveAboutBtn = document.getElementById("save-about-btn");
    const resetAboutBtn = document.getElementById("reset-about-btn");
    const cancelAboutBtn = document.getElementById("cancel-about-btn");

    function applyTheme(themeName) {
        document.body.classList.remove("theme-bloodmoon", "theme-cathedral");
        if (themeName === "bloodmoon") {
            document.body.classList.add("theme-bloodmoon");
        } else if (themeName === "cathedral") {
            document.body.classList.add("theme-cathedral");
        }
        themeSelect.value = themeName;
        localStorage.setItem("ppl_theme", themeName);
    }

    function initAboutText() {
        const saved = localStorage.getItem("ppl_about_text") || DEFAULT_ABOUT_TEXT;
        aboutCustomText.textContent = saved;
        aboutTextarea.value = saved;
    }

    function showError(message) {
        errorMessage.textContent = message;
        errorBanner.classList.remove("hidden");
    }

    function hideError() {
        errorBanner.classList.add("hidden");
        errorMessage.textContent = "";
    }

    function setLoading(isLoading) {
        runRefactorBtn.disabled = isLoading;
        if (isLoading) {
            runBtnIcon.classList.add("hidden");
            runBtnSpinner.classList.remove("hidden");
            runBtnText.textContent = enableAgent2Checkbox.checked
                ? "Dual Agents Patching..."
                : "Patching Legacy...";
            loadingStatus.classList.remove("hidden");
        } else {
            runBtnIcon.classList.remove("hidden");
            runBtnSpinner.classList.add("hidden");
            runBtnText.textContent = "Patch Legacy Now";
            loadingStatus.classList.add("hidden");
        }
    }

    function switchInputTab(source) {
        state.inputSource = source;
        const activeCls = "rounded-lg bg-gradient-to-r from-[#7c3749] to-[#ad556c] px-3 py-1.5 text-xs font-semibold text-white shadow transition";
        const idleCls = "rounded-lg px-3 py-1.5 text-xs font-semibold text-[#cc959f] transition hover:text-white";

        tabPaste.className = source === "paste" ? activeCls : idleCls;
        tabUpload.className = source === "upload" ? activeCls : idleCls;
        tabGithub.className = source === "github" ? activeCls : idleCls;

        panelPaste.classList.toggle("hidden", source !== "paste");
        panelUpload.classList.toggle("hidden", source !== "upload");
        panelGithub.classList.toggle("hidden", source !== "github");
    }

    function updateInputStats() {
        const val = codeInput.value;
        const lines = val ? val.split(/\r?\n/).length : 0;
        const statsSpan = inputStats.querySelector("span");
        if (statsSpan) {
            statsSpan.textContent = `${lines} lines • ${val.length} chars`;
        }
    }

    function handleSelectedFile(file) {
        if (!file) return;
        if (file.size > 1_000_000) {
            showError("Selected file exceeds the 1 MB maximum size for text source files.");
            return;
        }
        hideError();
        state.selectedFile = file;
        selectedFileName.textContent = file.name;
        selectedFileMeta.textContent = `${(file.size / 1024).toFixed(2)} KB • Ready to patch`;
        filePreviewBox.classList.remove("hidden");
        filePreviewBox.classList.add("flex");
    }

    function clearSelectedFile() {
        state.selectedFile = null;
        fileInput.value = "";
        filePreviewBox.classList.add("hidden");
        filePreviewBox.classList.remove("flex");
    }

    function applyGoalPreset(goalKey) {
        const preset = GOAL_PRESETS[goalKey];
        if (preset) {
            modeSelect.value = preset.mode;
            targetStackInput.value = preset.targetStack;
        } else if (goalKey === "custom") {
            targetStackInput.focus();
            targetStackInput.select();
        }
    }

    function loadSample(sampleKey) {
        const sample = SAMPLE_SNIPPETS[sampleKey];
        if (!sample) return;
        switchInputTab("paste");
        filenameInput.value = sample.filename;
        codeInput.value = sample.code;
        updateInputStats();
        goalSelect.value = sample.goal;
        applyGoalPreset(sample.goal);
        hideError();
    }

    async function extractErrorMessage(response) {
        try {
            const payload = await response.json();
            if (payload && payload.detail) {
                return typeof payload.detail === "string"
                    ? payload.detail
                    : JSON.stringify(payload.detail);
            }
        } catch (_) {
            // Fall back to HTTP status text
        }
        return `Server returned HTTP ${response.status} ${response.statusText}`;
    }

    async function checkHealth() {
        try {
            const res = await fetch("/api/health");
            if (!res.ok) throw new Error("Offline");
            const data = await res.json();

            if (data.api_key_configured) {
                healthDot.className = "h-2.5 w-2.5 rotate-45 rounded-[2px] bg-[#e8c4c9] shadow-[0_0_8px_rgba(213,163,170,0.85)]";
                healthText.textContent = data.nvidia_key_configured
                    ? "Cryo Vigil • Dual Ready"
                    : "Cryo Vigil • Online";
                apiKeyWarning.classList.add("hidden");
            } else {
                healthDot.className = "h-2.5 w-2.5 rotate-45 rounded-[2px] bg-amber-300";
                healthText.textContent = "Key Setup Needed";
                apiKeyWarning.classList.remove("hidden");
            }
        } catch (_) {
            healthDot.className = "h-2.5 w-2.5 rotate-45 rounded-[2px] bg-rose-400";
            healthText.textContent = "Sanctuary Offline";
        }
    }

    function renderNvidiaModelOptions(filterText = "") {
        const previousVal = nvidiaModelSelect.value;
        const term = filterText.trim().toLowerCase();
        const filtered = state.nvidiaModels.filter((m) => m.id.toLowerCase().includes(term));

        nvidiaModelSelect.replaceChildren();
        if (filtered.length === 0) {
            const opt = document.createElement("option");
            opt.value = "";
            opt.textContent = "No matching models found";
            nvidiaModelSelect.appendChild(opt);
            return;
        }

        filtered.forEach((m) => {
            const opt = document.createElement("option");
            opt.value = m.id;
            opt.textContent = `${m.id} (${m.tier})`;
            nvidiaModelSelect.appendChild(opt);
        });

        if (previousVal && filtered.some((m) => m.id === previousVal)) {
            nvidiaModelSelect.value = previousVal;
        }
    }

    async function loadNvidiaModels() {
        nvidiaModelsStatus.textContent = "Loading free Agent 2 models catalog...";
        try {
            const headers = {};
            const customKey = nvidiaCustomKeyInput.value.trim();
            if (customKey) {
                headers["x-nvidia-api-key"] = customKey;
            }
            const res = await fetch("/api/nvidia/models", { headers });
            if (!res.ok) throw new Error("Could not fetch catalog models");
            const data = await res.json();
            state.nvidiaModels = data.models || [];
            renderNvidiaModelOptions(nvidiaModelSearch.value);
            nvidiaModelsStatus.textContent = `${state.nvidiaModels.length} free models loaded for Agent 2.`;
        } catch (err) {
            nvidiaModelsStatus.textContent = err.message || "Could not load catalog.";
        }
    }

    function renderGithubRepoFiles(filterText = "") {
        githubFileList.replaceChildren();
        if (!state.githubRepo) return;

        const term = filterText.trim().toLowerCase();
        const matching = state.githubRepo.files.filter((f) => f.path.toLowerCase().includes(term));

        if (matching.length === 0) {
            const p = document.createElement("p");
            p.className = "py-3 text-center text-xs text-[#b58994]";
            p.textContent = "No matching source files found.";
            githubFileList.appendChild(p);
            return;
        }

        const fragment = document.createDocumentFragment();
        matching.forEach((fileObj) => {
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className =
                "flex w-full items-center justify-between rounded-lg border border-[#cc959f]/25 bg-[#12070c] px-3 py-1.5 text-left font-mono text-[11px] text-[#faecef] transition hover:border-[#d5a3aa] hover:bg-[#3a1623]";

            const pathSpan = document.createElement("span");
            pathSpan.className = "truncate pr-3";
            pathSpan.textContent = fileObj.path;

            const sizeSpan = document.createElement("span");
            sizeSpan.className = "shrink-0 text-[10px] text-[#b58994]";
            sizeSpan.textContent = `${(fileObj.size / 1024).toFixed(1)} KB`;

            btn.appendChild(pathSpan);
            btn.appendChild(sizeSpan);

            btn.addEventListener("click", () => fetchSpecificGithubFile(fileObj.path));
            fragment.appendChild(btn);
        });
        githubFileList.appendChild(fragment);
    }

    async function inspectGithubUrl() {
        hideError();
        const rawUrl = githubUrlInput.value.trim();
        if (!rawUrl) {
            showError("Please paste a public GitHub file or repository URL first.");
            return;
        }

        githubInspectBtn.disabled = true;
        githubInspectBtn.textContent = "Fetching...";
        githubStatus.classList.remove("hidden");
        githubStatus.textContent = "Connecting to GitHub...";

        try {
            const res = await fetch("/api/github/inspect", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url: rawUrl }),
            });
            if (!res.ok) {
                throw new Error(await extractErrorMessage(res));
            }
            const data = await res.json();

            if (data.kind === "file") {
                githubRepoBrowser.classList.add("hidden");
                switchInputTab("paste");
                filenameInput.value = data.filename || "github_file.py";
                codeInput.value = data.code || "";
                updateInputStats();
                githubStatus.textContent = `Loaded ${data.filename} from GitHub.`;
            } else if (data.kind === "repo") {
                state.githubRepo = data;
                githubRepoMeta.textContent = `${data.owner}/${data.repo} (${data.branch}) — ${data.files.length} files`;
                githubFileSearch.value = "";
                renderGithubRepoFiles("");
                githubRepoBrowser.classList.remove("hidden");
                githubStatus.textContent = "Select any file below to load it into the editor.";
            }
        } catch (err) {
            githubStatus.classList.add("hidden");
            showError(err.message || "Failed to fetch from GitHub.");
        } finally {
            githubInspectBtn.disabled = false;
            githubInspectBtn.textContent = "Fetch from GitHub";
        }
    }

    async function fetchSpecificGithubFile(filePath) {
        if (!state.githubRepo) return;
        hideError();
        githubStatus.classList.remove("hidden");
        githubStatus.textContent = `Downloading ${filePath}...`;

        try {
            const res = await fetch("/api/github/fetch-file", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    owner: state.githubRepo.owner,
                    repo: state.githubRepo.repo,
                    branch: state.githubRepo.branch,
                    path: filePath,
                }),
            });
            if (!res.ok) {
                throw new Error(await extractErrorMessage(res));
            }
            const data = await res.json();
            switchInputTab("paste");
            filenameInput.value = data.filename || filePath;
            codeInput.value = data.code || "";
            updateInputStats();
            githubStatus.textContent = `Loaded ${data.path} into editor.`;
        } catch (err) {
            showError(err.message || "Failed to download file from GitHub.");
        }
    }

    function renderLineNumberedCode(container, rawCode, lineCountEl) {
        container.replaceChildren();
        const normalized = (rawCode || "").replace(/\r\n/g, "\n");
        const lines = normalized.split("\n");
        lineCountEl.textContent = `${lines.length} ${lines.length === 1 ? "line" : "lines"}`;

        const fragment = document.createDocumentFragment();
        lines.forEach((lineText, idx) => {
            const row = document.createElement("div");
            row.className = "flex items-start rounded px-1 hover:bg-[#3a1623]/45";

            const numSpan = document.createElement("span");
            numSpan.className = "w-10 shrink-0 select-none pr-3 text-right text-[11px] text-[#b58994]/50";
            numSpan.textContent = String(idx + 1);

            const codeSpan = document.createElement("span");
            codeSpan.className = "whitespace-pre text-[#faecef]";
            codeSpan.textContent = lineText.length > 0 ? lineText : " ";

            row.appendChild(numSpan);
            row.appendChild(codeSpan);
            fragment.appendChild(row);
        });

        container.appendChild(fragment);
    }

    function computeLineDiff(beforeText, afterText) {
        const a = (beforeText || "").replace(/\r\n/g, "\n").split("\n");
        const b = (afterText || "").replace(/\r\n/g, "\n").split("\n");
        if (a.length * b.length > 400_000) return null;

        const m = a.length;
        const n = b.length;
        const dp = Array.from({ length: m + 1 }, () => new Uint32Array(n + 1));

        for (let i = m - 1; i >= 0; i--) {
            for (let j = n - 1; j >= 0; j--) {
                if (a[i] === b[j]) {
                    dp[i][j] = dp[i + 1][j + 1] + 1;
                } else {
                    dp[i][j] = dp[i + 1][j] >= dp[i][j + 1] ? dp[i + 1][j] : dp[i][j + 1];
                }
            }
        }

        const ops = [];
        let i = 0;
        let j = 0;
        while (i < m && j < n) {
            if (a[i] === b[j]) {
                ops.push({ type: "same", text: a[i], oldLine: i + 1, newLine: j + 1 });
                i++;
                j++;
            } else if (dp[i + 1][j] >= dp[i][j + 1]) {
                ops.push({ type: "del", text: a[i], oldLine: i + 1, newLine: null });
                i++;
            } else {
                ops.push({ type: "add", text: b[j], oldLine: null, newLine: j + 1 });
                j++;
            }
        }
        while (i < m) ops.push({ type: "del", text: a[i], oldLine: ++i, newLine: null });
        while (j < n) ops.push({ type: "add", text: b[j], oldLine: null, newLine: ++j });
        return ops;
    }

    function renderDiffView(beforeText, afterText) {
        diffContent.replaceChildren();
        const ops = computeLineDiff(beforeText, afterText);
        if (ops === null) {
            const p = document.createElement("p");
            p.className = "p-4 text-xs text-[#cc959f]";
            p.textContent = "File too large for inline LCS diffing—use the Side-by-Side view.";
            diffContent.appendChild(p);
            return;
        }

        const fragment = document.createDocumentFragment();
        ops.forEach((op) => {
            const row = document.createElement("div");
            let rowBg = "";
            let prefix = " ";
            let textColor = "text-[#f2dde0]/85";

            if (op.type === "del") {
                rowBg = "bg-rose-500/15";
                prefix = "-";
                textColor = "text-rose-200";
            } else if (op.type === "add") {
                rowBg = "bg-emerald-500/15";
                prefix = "+";
                textColor = "text-emerald-200";
            }

            row.className = `flex items-start px-2 ${rowBg}`;

            const oldNum = document.createElement("span");
            oldNum.className = "w-9 shrink-0 select-none pr-2 text-right text-[11px] text-[#b58994]/40";
            oldNum.textContent = op.oldLine !== null ? String(op.oldLine) : "";

            const newNum = document.createElement("span");
            newNum.className = "w-9 shrink-0 select-none pr-2 text-right text-[11px] text-[#b58994]/40";
            newNum.textContent = op.newLine !== null ? String(op.newLine) : "";

            const sign = document.createElement("span");
            sign.className = `w-5 shrink-0 select-none font-bold ${textColor}`;
            sign.textContent = prefix;

            const codeSpan = document.createElement("span");
            codeSpan.className = `whitespace-pre ${textColor}`;
            codeSpan.textContent = op.text.length > 0 ? op.text : " ";

            row.appendChild(oldNum);
            row.appendChild(newNum);
            row.appendChild(sign);
            row.appendChild(codeSpan);
            fragment.appendChild(row);
        });
        diffContent.appendChild(fragment);
    }

    function setComparisonViewMode(viewMode) {
        state.viewMode = viewMode;
        const activeCls = "rounded-lg bg-gradient-to-r from-[#7c3749] to-[#ad556c] px-3 py-1.5 text-xs font-semibold text-white";
        const idleCls = "rounded-lg px-3 py-1.5 text-xs font-semibold text-[#cc959f] hover:text-white";

        viewSideBySideBtn.className = viewMode === "side-by-side" ? activeCls : idleCls;
        viewDiffBtn.className = viewMode === "diff" ? activeCls : idleCls;
        sideBySideView.classList.toggle("hidden", viewMode !== "side-by-side");
        diffView.classList.toggle("hidden", viewMode !== "diff");
        syncScrollLabel.classList.toggle("hidden", viewMode !== "side-by-side");
    }

    function renderInsightList(listEl, items, emptyFallback) {
        listEl.replaceChildren();
        if (!Array.isArray(items) || items.length === 0) {
            const li = document.createElement("li");
            li.className = "italic opacity-70";
            li.textContent = emptyFallback;
            listEl.appendChild(li);
            return;
        }
        items.forEach((itemText) => {
            const li = document.createElement("li");
            li.className = "gothic-inset flex items-start gap-2 rounded-lg px-3 py-2 leading-relaxed";

            const bullet = document.createElement("span");
            bullet.className = "mt-1.5 h-1.5 w-1.5 shrink-0 rotate-45 rounded-[1px] bg-[#d5a3aa]";

            const textSpan = document.createElement("span");
            textSpan.textContent = String(itemText);

            li.appendChild(bullet);
            li.appendChild(textSpan);
            listEl.appendChild(li);
        });
    }

    function formatModeLabel(mode) {
        const labels = {
            full_autonomous: "Full Autonomous",
            refactor: "Code Refactor",
            migrate_dependencies: "Dependency Migration",
        };
        return labels[mode] || mode;
    }

    function renderRecord(record, shouldScroll = true) {
        state.currentRecord = record;
        emptyWorkbench.classList.add("hidden");
        resultsSection.classList.remove("hidden");

        resFilename.textContent = record.filename || "snippet.txt";
        resLanguage.textContent = record.detected_language || "Auto-Detected";
        resFramework.textContent = record.detected_framework || "Standard";
        resMode.textContent = formatModeLabel(record.mode);

        const beforeLines = record.lines_before || 0;
        const afterLines = record.lines_after || 0;
        resLinesDelta.textContent = `${beforeLines}L → ${afterLines}L`;
        resTargetStack.textContent = `Target Stack: ${record.target_stack}`;

        const score = Math.max(0, Math.min(100, Number(record.confidence_score || 0)));
        const circumference = 113.1;
        resConfidenceRing.style.strokeDashoffset = String(circumference - (score / 100) * circumference);
        resConfidenceText.textContent = `${score}%`;

        if (score >= 80) {
            resConfidenceRing.setAttribute("stroke", "#d5a3aa");
        } else if (score >= 50) {
            resConfidenceRing.setAttribute("stroke", "#fbbf24");
        } else {
            resConfidenceRing.setAttribute("stroke", "#fb7185");
        }

        renderLineNumberedCode(beforeScroll, record.original_code, beforeLineCount);
        renderLineNumberedCode(afterScroll, record.refactored_code, afterLineCount);
        renderDiffView(record.original_code, record.refactored_code);
        beforeScroll.scrollTop = 0;
        afterScroll.scrollTop = 0;

        if (record.second_agent_model) {
            agent2ResultCard.classList.remove("hidden");
            agent2ModelBadge.textContent = record.second_agent_model;
            agent2VerdictBadge.textContent = record.second_agent_verdict || "Reviewed";
            agent2ScoreText.textContent = record.second_agent_score > 0 ? `${record.second_agent_score}/100` : "";
            renderInsightList(
                agent2NotesList,
                record.second_agent_notes,
                "Second-agent review returned no extra notes."
            );
        } else {
            agent2ResultCard.classList.add("hidden");
        }

        resSummary.textContent = record.summary || "Refactoring completed.";
        renderInsightList(resMigrationsList, record.dependency_migrations, "No outdated dependencies required migration.");
        renderInsightList(resChangesList, record.changes_made, "No structural code changes were necessary.");
        renderInsightList(resRisksList, record.breaking_changes_and_risks, "No major breaking changes flagged.");
        renderInsightList(resVerificationList, record.verification_steps, "Run your test suite to confirm behavior.");

        if (shouldScroll) {
            resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
        }
    }

    function renderAnalyticsCharts(analytics) {
        statTotalRuns.textContent = String(analytics.total_runs || 0);
        statAvgConf.textContent = `${analytics.average_confidence || 0}%`;
        statTotalMigrations.textContent = String(analytics.total_migrations || 0);
        statDualRuns.textContent = String(analytics.dual_agent_runs || 0);

        chartLinesTrend.replaceChildren();
        const trend = analytics.recent_trend || [];
        if (trend.length === 0) {
            const p = document.createElement("p");
            p.className = "w-full py-6 text-center text-xs opacity-60";
            p.textContent = "Run your first patch to populate line-count charts.";
            chartLinesTrend.appendChild(p);
        } else {
            const maxLines = Math.max(
                10,
                ...trend.flatMap((t) => [Number(t.lines_before || 0), Number(t.lines_after || 0)])
            );
            trend.forEach((t) => {
                const col = document.createElement("div");
                col.className = "flex min-w-[30px] flex-1 flex-col items-center gap-1";

                const barsWrap = document.createElement("div");
                barsWrap.className = "flex h-24 w-full items-end justify-center gap-1";

                const bHeight = Math.max(6, Math.round((t.lines_before / maxLines) * 90));
                const aHeight = Math.max(6, Math.round((t.lines_after / maxLines) * 90));

                const bBar = document.createElement("div");
                bBar.className = "w-2.5 rounded-t bg-[#7c3749] transition-all";
                bBar.style.height = `${bHeight}px`;
                bBar.title = `${t.filename} Before: ${t.lines_before} lines`;

                const aBar = document.createElement("div");
                aBar.className = "w-2.5 rounded-t bg-[#d5a3aa] transition-all";
                aBar.style.height = `${aHeight}px`;
                aBar.title = `${t.filename} After: ${t.lines_after} lines`;

                barsWrap.appendChild(bBar);
                barsWrap.appendChild(aBar);

                const label = document.createElement("span");
                label.className = "max-w-[54px] truncate font-mono text-[9px]";
                label.style.color = "var(--text-muted)";
                label.textContent = `#${t.id}`;

                col.appendChild(barsWrap);
                col.appendChild(label);
                chartLinesTrend.appendChild(col);
            });
        }

        chartLanguages.replaceChildren();
        const langs = analytics.languages || [];
        if (langs.length === 0) {
            const p = document.createElement("p");
            p.className = "py-6 text-center text-xs opacity-60";
            p.textContent = "Detected languages and manifest types appear here.";
            chartLanguages.appendChild(p);
        } else {
            const maxCount = Math.max(1, ...langs.map((l) => l.count));
            langs.forEach((lang) => {
                const row = document.createElement("div");
                row.className = "space-y-1";

                const header = document.createElement("div");
                header.className = "flex justify-between text-[11px]";

                const nameSpan = document.createElement("span");
                nameSpan.className = "font-semibold";
                nameSpan.textContent = lang.name;

                const countSpan = document.createElement("span");
                countSpan.className = "font-mono text-[#d5a3aa]";
                countSpan.textContent = `${lang.count}`;

                header.appendChild(nameSpan);
                header.appendChild(countSpan);

                const track = document.createElement("div");
                track.className = "h-2 w-full overflow-hidden rounded-full bg-[#3a1623]/70";

                const fill = document.createElement("div");
                fill.className = "h-full rounded-full bg-gradient-to-r from-[#7c3749] to-[#d5a3aa]";
                fill.style.width = `${Math.round((lang.count / maxCount) * 100)}%`;

                track.appendChild(fill);
                row.appendChild(header);
                row.appendChild(track);
                chartLanguages.appendChild(row);
            });
        }
    }

    async function loadAnalytics() {
        try {
            const res = await fetch("/api/analytics");
            if (!res.ok) return;
            const data = await res.json();
            if (data.analytics) renderAnalyticsCharts(data.analytics);
        } catch (_) {
            // Silent fallback if backend offline
        }
    }

    async function runRefactoring() {
        hideError();
        const mode = modeSelect.value;
        const targetStack = targetStackInput.value.trim() || "Latest stable LTS & modern best practices";
        const customInstructions = instructionsInput.value.trim();
        const nvidiaModel = enableAgent2Checkbox.checked ? (nvidiaModelSelect.value || "") : "";
        const nvidiaKey = enableAgent2Checkbox.checked ? nvidiaCustomKeyInput.value.trim() : "";

        setLoading(true);
        try {
            let response;
            if (state.inputSource === "upload") {
                if (!state.selectedFile) {
                    throw new Error("Please drop or select a source file first.");
                }
                const formData = new FormData();
                formData.append("file", state.selectedFile);
                formData.append("mode", mode);
                formData.append("target_stack", targetStack);
                formData.append("custom_instructions", customInstructions);
                formData.append("nvidia_model", nvidiaModel);
                formData.append("nvidia_api_key", nvidiaKey);

                response = await fetch("/api/refactor/upload", {
                    method: "POST",
                    body: formData,
                });
            } else {
                const code = codeInput.value;
                if (!code.trim()) {
                    throw new Error(
                        state.inputSource === "github"
                            ? "First fetch a file from your GitHub URL (or click a file in the repository list)."
                            : "Please paste some source code or a dependency manifest first."
                    );
                }
                const filename = filenameInput.value.trim() || "snippet.py";
                response = await fetch("/api/refactor", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        code,
                        filename,
                        mode,
                        target_stack: targetStack,
                        custom_instructions: customInstructions,
                        nvidia_model: nvidiaModel,
                        nvidia_api_key: nvidiaKey,
                    }),
                });
            }

            if (!response.ok) {
                throw new Error(await extractErrorMessage(response));
            }
            const data = await response.json();
            if (!data.record) {
                throw new Error("Unexpected response from backend.");
            }

            renderRecord(data.record, true);
            await Promise.all([loadHistory(), loadAnalytics()]);
        } catch (err) {
            showError(err.message || "Unexpected error while patching code.");
        } finally {
            setLoading(false);
        }
    }

    function renderHistoryItems(items) {
        historyList.replaceChildren();
        historyCountPill.textContent = String(items.length);

        if (items.length === 0) {
            const emptyCard = document.createElement("div");
            emptyCard.className = "gothic-inset col-span-full rounded-xl p-6 text-center text-xs opacity-65";
            emptyCard.textContent = "No patches saved in SQLite yet. Run your first legacy rescue above!";
            historyList.appendChild(emptyCard);
            return;
        }

        const fragment = document.createDocumentFragment();
        items.forEach((item) => {
            const isActive = state.currentRecord && state.currentRecord.id === item.id;
            const card = document.createElement("div");
            card.className = `gothic-inset cursor-pointer rounded-xl p-4 transition hover:border-[#d5a3aa]/70 ${
                isActive ? "ring-2 ring-[#d5a3aa]/70" : ""
            }`;

            const topRow = document.createElement("div");
            topRow.className = "flex items-start justify-between gap-2";

            const titleWrap = document.createElement("div");
            titleWrap.className = "min-w-0";

            const nameEl = document.createElement("p");
            nameEl.className = "truncate font-mono text-xs font-bold";
            nameEl.textContent = item.filename;

            const stackEl = document.createElement("p");
            stackEl.className = "mt-0.5 truncate text-[11px] opacity-70";
            stackEl.textContent = item.target_stack;

            titleWrap.appendChild(nameEl);
            titleWrap.appendChild(stackEl);

            const delBtn = document.createElement("button");
            delBtn.type = "button";
            delBtn.title = "Delete record";
            delBtn.className = "rounded px-1.5 py-0.5 text-xs text-[#cc959f]/70 hover:bg-rose-500/20 hover:text-rose-300";
            delBtn.textContent = "×";
            delBtn.addEventListener("click", async (event) => {
                event.stopPropagation();
                await deleteHistoryItem(item.id);
            });

            topRow.appendChild(titleWrap);
            topRow.appendChild(delBtn);

            const badgesRow = document.createElement("div");
            badgesRow.className = "mt-3 flex flex-wrap items-center gap-1.5";

            const langBadge = document.createElement("span");
            langBadge.className = "rounded bg-[#9c4e60]/30 px-2 py-0.5 text-[10px] font-semibold text-[#f2dde0]";
            langBadge.textContent = item.detected_language;

            badgesRow.appendChild(langBadge);

            if (item.second_agent_model) {
                const dualBadge = document.createElement("span");
                dualBadge.className = "rounded bg-[#7c3749]/45 px-2 py-0.5 text-[10px] font-semibold text-[#e8c4c9]";
                dualBadge.textContent = "2x AI";
                badgesRow.appendChild(dualBadge);
            }

            const confBadge = document.createElement("span");
            confBadge.className = "ml-auto rounded bg-emerald-500/20 px-2 py-0.5 text-[10px] font-bold text-emerald-300";
            confBadge.textContent = `${item.confidence_score}%`;
            badgesRow.appendChild(confBadge);

            const timeEl = document.createElement("p");
            timeEl.className = "mt-2 text-[10px] opacity-55";
            timeEl.textContent = `#${item.id} • ${item.created_at} UTC`;

            card.appendChild(topRow);
            card.appendChild(badgesRow);
            card.appendChild(timeEl);

            card.addEventListener("click", () => {
                renderRecord(item, true);
                renderHistoryItems(items);
            });

            fragment.appendChild(card);
        });
        historyList.appendChild(fragment);
    }

    async function loadHistory() {
        try {
            const res = await fetch("/api/history?limit=50");
            if (!res.ok) throw new Error("Failed to load history");
            const data = await res.json();
            renderHistoryItems(data.items || []);
        } catch (err) {
            showError(err.message || "Could not load SQLite history.");
        }
    }

    async function deleteHistoryItem(recordId) {
        try {
            const res = await fetch(`/api/history/${recordId}`, { method: "DELETE" });
            if (!res.ok) throw new Error(await extractErrorMessage(res));
            if (state.currentRecord && state.currentRecord.id === recordId) {
                state.currentRecord = null;
                resultsSection.classList.add("hidden");
                emptyWorkbench.classList.remove("hidden");
            }
            await Promise.all([loadHistory(), loadAnalytics()]);
        } catch (err) {
            showError(err.message || "Failed to delete history entry.");
        }
    }

    async function clearAllHistory() {
        if (!window.confirm("Delete all saved patch history from SQLite?")) return;
        try {
            const res = await fetch("/api/history", { method: "DELETE" });
            if (!res.ok) throw new Error(await extractErrorMessage(res));
            state.currentRecord = null;
            resultsSection.classList.add("hidden");
            emptyWorkbench.classList.remove("hidden");
            await Promise.all([loadHistory(), loadAnalytics()]);
        } catch (err) {
            showError(err.message || "Failed to clear history.");
        }
    }

    function setupSyncScroll(sourceEl, targetEl) {
        sourceEl.addEventListener("scroll", () => {
            if (!syncScrollCheckbox.checked || state.isSyncingScroll) return;
            state.isSyncingScroll = true;
            const sourceMaxY = sourceEl.scrollHeight - sourceEl.clientHeight;
            const targetMaxY = targetEl.scrollHeight - targetEl.clientHeight;
            if (sourceMaxY > 0 && targetMaxY > 0) {
                targetEl.scrollTop = (sourceEl.scrollTop / sourceMaxY) * targetMaxY;
            }
            targetEl.scrollLeft = sourceEl.scrollLeft;
            window.requestAnimationFrame(() => {
                state.isSyncingScroll = false;
            });
        });
    }

    // Event bindings
    themeSelect.addEventListener("change", (e) => applyTheme(e.target.value));
    dismissErrorBtn.addEventListener("click", hideError);

    tabPaste.addEventListener("click", () => switchInputTab("paste"));
    tabUpload.addEventListener("click", () => switchInputTab("upload"));
    tabGithub.addEventListener("click", () => switchInputTab("github"));

    codeInput.addEventListener("input", updateInputStats);
    clearCodeBtn.addEventListener("click", () => {
        codeInput.value = "";
        updateInputStats();
    });

    samplePy2Btn.addEventListener("click", () => loadSample("py2"));
    sampleFlaskBtn.addEventListener("click", () => loadSample("flask"));
    sampleDepsBtn.addEventListener("click", () => loadSample("deps"));
    sampleJsBtn.addEventListener("click", () => loadSample("js"));

    fileInput.addEventListener("change", (event) => {
        const file = event.target.files && event.target.files[0];
        if (file) handleSelectedFile(file);
    });
    dropZone.addEventListener("dragover", (event) => {
        event.preventDefault();
        dropZone.classList.add("border-[#d5a3aa]");
    });
    dropZone.addEventListener("dragleave", () => dropZone.classList.remove("border-[#d5a3aa]"));
    dropZone.addEventListener("drop", (event) => {
        event.preventDefault();
        dropZone.classList.remove("border-[#d5a3aa]");
        const file = event.dataTransfer && event.dataTransfer.files && event.dataTransfer.files[0];
        if (file) handleSelectedFile(file);
    });
    clearFileBtn.addEventListener("click", clearSelectedFile);

    githubInspectBtn.addEventListener("click", inspectGithubUrl);
    githubFileSearch.addEventListener("input", (e) => renderGithubRepoFiles(e.target.value));

    goalSelect.addEventListener("change", (e) => applyGoalPreset(e.target.value));

    enableAgent2Checkbox.addEventListener("change", () => {
        const enabled = enableAgent2Checkbox.checked;
        agent2Panel.classList.toggle("hidden", !enabled);
        if (enabled && state.nvidiaModels.length === 0) {
            loadNvidiaModels();
        }
    });
    nvidiaModelSearch.addEventListener("input", (e) => renderNvidiaModelOptions(e.target.value));
    refreshNvidiaModelsBtn.addEventListener("click", loadNvidiaModels);

    runRefactorBtn.addEventListener("click", runRefactoring);
    viewSideBySideBtn.addEventListener("click", () => setComparisonViewMode("side-by-side"));
    viewDiffBtn.addEventListener("click", () => setComparisonViewMode("diff"));

    copyAfterBtn.addEventListener("click", async () => {
        if (!state.currentRecord) return;
        try {
            await navigator.clipboard.writeText(state.currentRecord.refactored_code || "");
            copyAfterText.textContent = "Copied!";
            setTimeout(() => {
                copyAfterText.textContent = "Copy After Code";
            }, 1800);
        } catch (_) {
            showError("Clipboard copy failed. Select and copy from the After pane directly.");
        }
    });

    downloadAfterBtn.addEventListener("click", () => {
        if (!state.currentRecord) return;
        const content = state.currentRecord.refactored_code || "";
        const origName = state.currentRecord.filename || "patched_code.txt";
        const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `patched_${origName}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    });

    refreshHistoryBtn.addEventListener("click", () => Promise.all([loadHistory(), loadAnalytics()]));
    clearHistoryBtn.addEventListener("click", clearAllHistory);

    // Editable About Section
    editAboutBtn.addEventListener("click", () => {
        aboutTextarea.value = aboutCustomText.textContent || DEFAULT_ABOUT_TEXT;
        aboutDisplay.classList.add("hidden");
        aboutEditor.classList.remove("hidden");
    });
    saveAboutBtn.addEventListener("click", () => {
        const updated = aboutTextarea.value.trim() || DEFAULT_ABOUT_TEXT;
        localStorage.setItem("ppl_about_text", updated);
        aboutCustomText.textContent = updated;
        aboutEditor.classList.add("hidden");
        aboutDisplay.classList.remove("hidden");
    });
    resetAboutBtn.addEventListener("click", () => {
        localStorage.removeItem("ppl_about_text");
        aboutCustomText.textContent = DEFAULT_ABOUT_TEXT;
        aboutTextarea.value = DEFAULT_ABOUT_TEXT;
        aboutEditor.classList.add("hidden");
        aboutDisplay.classList.remove("hidden");
    });
    cancelAboutBtn.addEventListener("click", () => {
        aboutEditor.classList.add("hidden");
        aboutDisplay.classList.remove("hidden");
    });

    setupSyncScroll(beforeScroll, afterScroll);
    setupSyncScroll(afterScroll, beforeScroll);

    // Boot
    applyTheme(localStorage.getItem("ppl_theme") || "rosaria");
    initAboutText();
    updateInputStats();
    checkHealth();
    loadHistory();
    loadAnalytics();
});