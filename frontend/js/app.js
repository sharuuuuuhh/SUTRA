/**
 * Sutra - Main Web Application Logic (Supabase Auth & Session Handling)
 */

document.addEventListener("DOMContentLoaded", async () => {
  const session = await getSupabaseSession();
  if (!session) {
    window.location.href = "/";
    return;
  }

  initAppHeader();
  initRailNavigation();
  initDropzones();
  initSegmentedControls();
  initFormSubmissions();
  initResultActions();
  await loadUserProfile();
});

// Application State
const appState = {
  currentView: "simplify", // 'simplify' | 'predict' | 'history' | 'result'
  simplify: {
    notes: [],
    syllabus: [],
    depth: "standard",
    language: "english"
  },
  predict: {
    past_questions: [],
    notes: [],
    syllabus: [],
    scheme: "detect",
    language: "english"
  },
  currentResult: null,
  progressInterval: null
};

const PROGRESS_MESSAGES = [
  "Reading and structuring uploaded pages...",
  "Mapping concepts against KTU syllabus modules...",
  "Extracting recurring 14-mark questions & Part A essentials...",
  "Formatting crisp explanations & exam-ready skeletons...",
  "Polishing formulas and finalizing study guide..."
];

// ----------------- HEADER & USER PROFILE -----------------

async function loadUserProfile() {
  try {
    const user = await apiFetch("/api/auth/me");
    const nameEl = document.getElementById("user-display-name");
    const quotaText = document.getElementById("quota-text");
    const quotaDot = document.getElementById("quota-dot");

    if (nameEl && user.name) {
      nameEl.textContent = user.name.split(" ")[0]; // First name
    }
    if (quotaText && user.usage) {
      const remaining = Math.max(0, user.usage.limit - user.usage.used);
      quotaText.textContent = `${user.usage.used} of ${user.usage.limit} runs today`;
      if (remaining === 0) {
        quotaDot.classList.add("warning");
      } else {
        quotaDot.classList.remove("warning");
      }
    }
  } catch (err) {
    console.error("Failed to load user profile:", err);
  }
}

function initAppHeader() {
  const logoutBtn = document.getElementById("logout-btn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
      showToast("Signing out...", "info");
      await signOutUser();
    });
  }
}

// ----------------- NAVIGATION & VIEW SWITCHING -----------------

function initRailNavigation() {
  const railBtns = document.querySelectorAll(".rail-btn");

  railBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const view = btn.getAttribute("data-view");
      switchView(view);
    });
  });
}

function switchView(viewName) {
  appState.currentView = viewName;

  document.querySelectorAll(".rail-btn").forEach(btn => {
    if (btn.getAttribute("data-view") === viewName) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });

  const simplifyPanel = document.getElementById("simplify-panel");
  const predictPanel = document.getElementById("predict-panel");
  const historyPanel = document.getElementById("history-panel");
  const resultPanel = document.getElementById("result-panel");

  if (simplifyPanel) simplifyPanel.style.display = viewName === "simplify" ? "block" : "none";
  if (predictPanel) predictPanel.style.display = viewName === "predict" ? "block" : "none";
  if (historyPanel) historyPanel.style.display = viewName === "history" ? "block" : "none";
  if (resultPanel) resultPanel.style.display = viewName === "result" ? "block" : "none";

  if (viewName === "history") {
    loadHistoryList();
  }

  window.scrollTo({ top: 0, behavior: "smooth" });
}

// ----------------- DROPZONE MANAGEMENT -----------------

const ACCEPTED_EXTENSIONS = ["pdf", "docx", "txt", "md", "png", "jpg", "jpeg", "webp"];
const MAX_FILE_SIZE_MB = 20;

function initDropzones() {
  const dropzones = document.querySelectorAll(".dropzone");

  dropzones.forEach(dropzone => {
    const fileInput = dropzone.querySelector("input[type='file']");
    const zoneId = dropzone.getAttribute("data-zone-id");

    dropzone.addEventListener("click", () => fileInput.click());

    dropzone.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        fileInput.click();
      }
    });

    dropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropzone.classList.add("drag-over");
    });

    dropzone.addEventListener("dragleave", () => {
      dropzone.classList.remove("drag-over");
    });

    dropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      dropzone.classList.remove("drag-over");
      if (e.dataTransfer && e.dataTransfer.files.length) {
        handleFilesAdded(zoneId, Array.from(e.dataTransfer.files));
      }
    });

    fileInput.addEventListener("change", () => {
      if (fileInput.files.length) {
        handleFilesAdded(zoneId, Array.from(fileInput.files));
        fileInput.value = "";
      }
    });
  });
}

function handleFilesAdded(zoneId, files) {
  const [formMode, fieldName] = zoneId.split("-");
  const targetArray = appState[formMode][fieldName];

  for (const file of files) {
    const ext = file.name.split(".").pop().toLowerCase();
    if (!ACCEPTED_EXTENSIONS.includes(ext)) {
      showToast(`Unsupported file: "${file.name}". Accepted formats: PDF, DOCX, TXT, MD, PNG, JPG, WEBP.`, "error", 5000);
      continue;
    }

    if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
      showToast(`File "${file.name}" exceeds the 20MB limit.`, "error", 5000);
      continue;
    }

    const exists = targetArray.some(f => f.name === file.name && f.size === file.size);
    if (!exists) {
      targetArray.push(file);
    }
  }

  renderFileChips(zoneId);
}

function removeFile(zoneId, index) {
  const [formMode, fieldName] = zoneId.split("-");
  appState[formMode][fieldName].splice(index, 1);
  renderFileChips(zoneId);
}

function renderFileChips(zoneId) {
  const [formMode, fieldName] = zoneId.split("-");
  const files = appState[formMode][fieldName];
  const chipsContainer = document.getElementById(`${zoneId}-chips`);
  if (!chipsContainer) return;

  chipsContainer.innerHTML = "";

  files.forEach((file, idx) => {
    const chip = document.createElement("div");
    chip.className = "file-chip";

    const sizeKb = (file.size / 1024).toFixed(0);
    const sizeStr = file.size > 1024 * 1024 
      ? `${(file.size / (1024 * 1024)).toFixed(1)} MB` 
      : `${sizeKb} KB`;

    chip.innerHTML = `
      <span>📄 ${escapeHtml(file.name)} (${sizeStr})</span>
      <button type="button" class="file-chip-remove" aria-label="Remove file" data-index="${idx}">&times;</button>
    `;

    chip.querySelector(".file-chip-remove").addEventListener("click", (e) => {
      e.stopPropagation();
      removeFile(zoneId, idx);
    });

    chipsContainer.appendChild(chip);
  });
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ----------------- SEGMENTED CONTROLS -----------------

function initSegmentedControls() {
  const controls = document.querySelectorAll(".segmented-control");

  controls.forEach(control => {
    const buttons = control.querySelectorAll(".segmented-btn");
    buttons.forEach(btn => {
      btn.addEventListener("click", () => {
        buttons.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");

        const targetField = control.getAttribute("data-field");
        const val = btn.getAttribute("data-value");
        if (targetField === "simplify-depth") {
          appState.simplify.depth = val;
        }
      });
    });
  });
}

// ----------------- FORM SUBMISSIONS & PROCESS -----------------

function initFormSubmissions() {
  const simplifyForm = document.getElementById("form-simplify");
  const predictForm = document.getElementById("form-predict");

  if (simplifyForm) {
    simplifyForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!appState.simplify.notes.length) {
        showToast("Please upload your lecture notes before proceeding.", "error");
        return;
      }

      const subject = document.getElementById("simplify-subject").value;
      const language = document.getElementById("simplify-language").value;

      const formData = new FormData();
      formData.append("mode", "simplify");
      formData.append("subject", subject);
      formData.append("depth", appState.simplify.depth);
      formData.append("language", language);

      appState.simplify.notes.forEach(f => formData.append("notes", f));
      appState.simplify.syllabus.forEach(f => formData.append("syllabus", f));

      await executeProcess(formData);
    });
  }

  if (predictForm) {
    predictForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!appState.predict.past_questions.length) {
        showToast("Please upload at least one previous year question paper.", "error");
        return;
      }
      if (!appState.predict.notes.length && !appState.predict.syllabus.length) {
        showToast("Please upload notes OR syllabus to calibrate the prediction.", "error");
        return;
      }

      const subject = document.getElementById("predict-subject").value;
      const scheme = document.getElementById("predict-scheme").value;
      const language = document.getElementById("predict-language").value;

      const formData = new FormData();
      formData.append("mode", "predict");
      formData.append("subject", subject);
      formData.append("scheme", scheme);
      formData.append("language", language);

      appState.predict.past_questions.forEach(f => formData.append("past_questions", f));
      appState.predict.notes.forEach(f => formData.append("notes", f));
      appState.predict.syllabus.forEach(f => formData.append("syllabus", f));

      await executeProcess(formData);
    });
  }
}

async function executeProcess(formData) {
  showLoadingOverlay();

  try {
    const res = await apiFetch("/api/process", {
      method: "POST",
      body: formData
    });

    hideLoadingOverlay();
    loadUserProfile();
    displayResult(res);
  } catch (err) {
    hideLoadingOverlay();
    showToast(err.message || "An error occurred while processing.", "error", 7000);
  }
}

// ----------------- LOADING OVERLAY & PROGRESS -----------------

function showLoadingOverlay() {
  const overlay = document.getElementById("loading-overlay");
  const progressText = document.getElementById("rotating-progress-text");
  if (!overlay) return;

  overlay.style.display = "flex";
  let msgIdx = 0;
  if (progressText) progressText.textContent = PROGRESS_MESSAGES[0];

  clearInterval(appState.progressInterval);
  appState.progressInterval = setInterval(() => {
    msgIdx = (msgIdx + 1) % PROGRESS_MESSAGES.length;
    if (progressText) {
      progressText.style.opacity = "0";
      setTimeout(() => {
        progressText.textContent = PROGRESS_MESSAGES[msgIdx];
        progressText.style.opacity = "1";
      }, 200);
    }
  }, 2800);
}

function hideLoadingOverlay() {
  const overlay = document.getElementById("loading-overlay");
  if (overlay) overlay.style.display = "none";
  clearInterval(appState.progressInterval);
}

// ----------------- RESULT PRESENTATION & ACTIONS -----------------

function displayResult(result) {
  appState.currentResult = result;
  switchView("result");

  const titleEl = document.getElementById("result-title");
  const contentEl = document.getElementById("result-content");

  if (titleEl) titleEl.textContent = result.title;
  if (contentEl) {
    contentEl.innerHTML = renderMarkdownWithKaTeX(result.output);
  }
}

function initResultActions() {
  const copyBtn = document.getElementById("result-copy-btn");
  const downloadBtn = document.getElementById("result-download-btn");
  const printBtn = document.getElementById("result-print-btn");
  const backBtn = document.getElementById("result-back-btn");

  if (copyBtn) {
    copyBtn.addEventListener("click", async () => {
      if (!appState.currentResult) return;
      try {
        await navigator.clipboard.writeText(appState.currentResult.output);
        showToast("Study notes copied to clipboard!", "success");
      } catch (err) {
        showToast("Failed to copy notes to clipboard.", "error");
      }
    });
  }

  if (downloadBtn) {
    downloadBtn.addEventListener("click", () => {
      if (!appState.currentResult) return;
      const blob = new Blob([appState.currentResult.output], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      const safeTitle = (appState.currentResult.title || "sutra-notes").replace(/[^a-zA-Z0-9_-]/g, "_");
      a.href = url;
      a.download = `${safeTitle}.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      showToast("Downloaded Markdown file.", "success");
    });
  }

  if (printBtn) {
    printBtn.addEventListener("click", () => {
      window.print();
    });
  }

  if (backBtn) {
    backBtn.addEventListener("click", () => {
      switchView("simplify");
    });
  }
}

// ----------------- HISTORY VIEW -----------------

async function loadHistoryList() {
  const container = document.getElementById("history-items-container");
  const emptyEl = document.getElementById("history-empty-state");
  if (!container) return;

  container.innerHTML = "<p style='color: var(--color-ink-muted);'>Loading study history...</p>";

  try {
    const historyList = await apiFetch("/api/history");
    container.innerHTML = "";

    if (!historyList || historyList.length === 0) {
      if (emptyEl) emptyEl.style.display = "block";
      return;
    }

    if (emptyEl) emptyEl.style.display = "none";

    historyList.forEach(item => {
      const card = document.createElement("div");
      card.className = "history-card";

      const dateObj = new Date(item.created_at);
      const dateStr = dateObj.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric"
      });

      const modeBadge = item.mode === "simplify"
        ? '<span class="status-pill pill-covered">Simplify</span>'
        : '<span class="status-pill pill-partly">Predict</span>';

      card.innerHTML = `
        <div>
          <div class="history-card-header">
            <h4 class="history-card-title">${escapeHtml(item.title)}</h4>
            ${modeBadge}
          </div>
          <div class="history-card-date">${dateStr} &bull; ${item.subject || "General"}</div>
        </div>
        <div class="history-card-actions">
          <button type="button" class="btn btn-secondary btn-sm open-hist-btn" data-id="${item.id}">Open note</button>
          <button type="button" class="btn btn-ghost btn-sm delete-hist-btn" data-id="${item.id}" style="color: var(--color-margin-red);">Delete</button>
        </div>
      `;

      card.querySelector(".open-hist-btn").addEventListener("click", async () => {
        try {
          const detail = await apiFetch(`/api/history/${item.id}`);
          displayResult(detail);
        } catch (err) {
          showToast(err.message || "Failed to load session.", "error");
        }
      });

      card.querySelector(".delete-hist-btn").addEventListener("click", async () => {
        if (!confirm("Are you sure you want to delete this study session?")) return;
        try {
          await apiFetch(`/api/history/${item.id}`, { method: "DELETE" });
          showToast("Session removed.", "info");
          loadHistoryList();
        } catch (err) {
          showToast(err.message || "Failed to delete item.", "error");
        }
      });

      container.appendChild(card);
    });

  } catch (err) {
    container.innerHTML = `<p style="color: var(--color-margin-red);">${escapeHtml(err.message || "Failed to load history.")}</p>`;
  }
}
