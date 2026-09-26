/**
 * Smart File Organizer — Client Application Logic
 * Modern, human-designed workflow:
 * 1. Scan directory -> 2. Discovered File Types Selection & Depth Configuration
 * -> 3. AI Analysis -> 4. Review & Edit Staging -> 5. Safe Batch Execution
 */

// Application State
const state = {
  currentRoot: "",
  scannedFiles: [],
  selectedCategories: new Set(),
  proposedOperations: [],
  duplicates: { exact_duplicates: [], similar_images: [] },
  unnecessaryFiles: [],
  settings: {
    default_provider: "gemini",
    gemini_key: "",
    openai_key: "",
    max_depth: 1,
  },
};

// DOM References
const elements = {
  pathInput: document.getElementById("target-path-input"),
  recursiveToggle: document.getElementById("recursive-scan-toggle"),
  btnStartScan: document.getElementById("btn-start-scan"),
  btnQuickSample: document.getElementById("btn-quick-sample"),
  systemStatusText: document.getElementById("system-status-text"),
  systemStatusPill: document.getElementById("system-status-pill"),

  // Discovered File Types & Scope Selection
  fileTypesPanel: document.getElementById("file-types-panel"),
  fileTypesCountBadge: document.getElementById("file-types-count-badge"),
  fileCategoriesGrid: document.getElementById("file-categories-grid"),
  btnSelectAllTypes: document.getElementById("btn-select-all-types"),
  btnDeselectAllTypes: document.getElementById("btn-deselect-all-types"),
  depthLimitSelect: document.getElementById("depth-limit-select"),
  depthHintText: document.getElementById("depth-hint-text"),
  nlPromptInput: document.getElementById("nl-prompt-input"),
  selectedFilesSummary: document.getElementById("selected-files-summary"),
  btnRunAI: document.getElementById("btn-run-ai-analysis"),
  btnRunAiText: document.getElementById("btn-run-ai-text"),

  // Metrics
  statTotalFiles: document.getElementById("stat-total-files"),
  statProposedOps: document.getElementById("stat-proposed-ops"),
  statDuplicates: document.getElementById("stat-duplicates"),
  statUnnecessary: document.getElementById("stat-unnecessary"),

  // Tab Badges
  badgeProposedCount: document.getElementById("badge-proposed-count"),
  badgeDuplicatesCount: document.getElementById("badge-duplicates-count"),
  badgeCleanupCount: document.getElementById("badge-cleanup-count"),

  // Tables & Content
  proposalsTableBody: document.getElementById("proposals-table-body"),
  exactDuplicatesList: document.getElementById("exact-duplicates-list"),
  similarImagesList: document.getElementById("similar-images-list"),
  cleanupTableBody: document.getElementById("cleanup-table-body"),
  historyListContainer: document.getElementById("history-list-container"),

  // Batch Table Controls
  checkAllOperations: document.getElementById("check-all-operations"),
  selectionSummary: document.getElementById("selection-summary"),
  btnExecuteApproved: document.getElementById("btn-execute-approved"),
  btnResetSuggestions: document.getElementById("btn-reset-suggestions"),
  btnBatchTrashUnnecessary: document.getElementById("btn-batch-trash-unnecessary"),

  // Slide Drawer
  btnHistoryDrawer: document.getElementById("btn-history-drawer"),
  btnCloseDrawer: document.getElementById("btn-close-drawer"),
  historyDrawer: document.getElementById("history-drawer"),
  drawerBackdrop: document.getElementById("drawer-backdrop"),

  // Progress Modal
  analysisBackdrop: document.getElementById("analysis-modal-backdrop"),
  analysisEngineBadge: document.getElementById("analysis-engine-badge"),
  analysisProgressCount: document.getElementById("analysis-progress-count"),
  analysisProgressPercent: document.getElementById("analysis-progress-percent"),
  analysisProgressBar: document.getElementById("analysis-progress-bar"),
  analysisCurrentFile: document.getElementById("analysis-current-file"),
  analysisMiniFeed: document.getElementById("analysis-mini-feed"),

  // Preview Modal
  previewBackdrop: document.getElementById("preview-modal-backdrop"),
  previewModalContent: document.getElementById("preview-modal-content"),
  previewFilename: document.getElementById("preview-filename"),
  btnClosePreview: document.getElementById("btn-close-preview"),

  // Settings Modal
  settingsBackdrop: document.getElementById("settings-modal-backdrop"),
  btnOpenSettings: document.getElementById("btn-open-settings"),
  btnCloseSettings: document.getElementById("btn-close-settings"),
  btnSaveSettings: document.getElementById("btn-save-settings"),
  geminiKeyInput: document.getElementById("gemini-api-key-input"),
  openaiKeyInput: document.getElementById("openai-api-key-input"),
  settingsMaxDepth: document.getElementById("settings-max-depth"),

  // Toast Container
  toastContainer: document.getElementById("toast-container"),
};

// Initialize Application
document.addEventListener("DOMContentLoaded", async () => {
  setupEventListeners();
  await loadSettings();
  setupSamplePath();
});

function setupSamplePath() {
  elements.pathInput.value = "C:\\Users\\mahes\\Documents\\Certificates - Copy";
}

// Event Listeners
function setupEventListeners() {
  // Navigation Tabs
  document.querySelectorAll(".tab-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-item").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((c) => c.classList.remove("active"));
      btn.classList.add("active");
      const targetId = btn.getAttribute("data-tab");
      document.getElementById(targetId)?.classList.add("active");
    });
  });

  // Prompt Suggestion Chips
  document.querySelectorAll(".chip-btn").forEach((chip) => {
    chip.addEventListener("click", () => {
      elements.nlPromptInput.value = chip.getAttribute("data-prompt");
    });
  });

  // Scanning Controls
  elements.btnQuickSample.addEventListener("click", () => {
    setupSamplePath();
    triggerScan();
  });
  elements.btnStartScan.addEventListener("click", triggerScan);

  // File Types Selection Controls
  elements.btnSelectAllTypes?.addEventListener("click", selectAllFileTypes);
  elements.btnDeselectAllTypes?.addEventListener("click", deselectAllFileTypes);

  // Depth Limit Dropdown Change
  elements.depthLimitSelect?.addEventListener("change", (e) => {
    const depthVal = parseInt(e.target.value, 10);
    state.settings.max_depth = depthVal;
    updateDepthHint(depthVal);
    if (elements.settingsMaxDepth) {
      elements.settingsMaxDepth.value = String(depthVal);
    }
  });

  elements.settingsMaxDepth?.addEventListener("change", (e) => {
    const depthVal = parseInt(e.target.value, 10);
    state.settings.max_depth = depthVal;
    if (elements.depthLimitSelect) {
      elements.depthLimitSelect.value = String(depthVal);
      updateDepthHint(depthVal);
    }
  });

  // Run AI Analysis
  elements.btnRunAI?.addEventListener("click", triggerAIAnalysis);

  // Staged Operations Actions
  elements.btnExecuteApproved?.addEventListener("click", executeApprovedOperations);
  elements.btnResetSuggestions?.addEventListener("click", resetSuggestions);

  // Select all operations checkbox
  elements.checkAllOperations?.addEventListener("change", (e) => {
    const isChecked = e.target.checked;
    state.proposedOperations.forEach((op) => (op.approved = isChecked));
    renderProposals();
  });

  // Drawer
  elements.btnHistoryDrawer?.addEventListener("click", openHistoryDrawer);
  elements.btnCloseDrawer?.addEventListener("click", closeHistoryDrawer);
  elements.drawerBackdrop?.addEventListener("click", closeHistoryDrawer);

  // Modals
  elements.btnClosePreview?.addEventListener("click", closePreviewModal);
  elements.previewBackdrop?.addEventListener("click", (e) => {
    if (e.target === elements.previewBackdrop) closePreviewModal();
  });

  elements.btnOpenSettings?.addEventListener("click", openSettingsModal);
  elements.btnCloseSettings?.addEventListener("click", closeSettingsModal);
  elements.settingsBackdrop?.addEventListener("click", (e) => {
    if (e.target === elements.settingsBackdrop) closeSettingsModal();
  });
  elements.btnSaveSettings?.addEventListener("click", saveSettings);

  // Batch trash unnecessary
  elements.btnBatchTrashUnnecessary?.addEventListener("click", batchTrashUnnecessary);
}

function updateDepthHint(depthVal) {
  if (!elements.depthHintText) return;
  if (depthVal === 1) {
    elements.depthHintText.textContent = "1 Level: Folders are created directly in the target directory with no nested subdirectories.";
  } else if (depthVal === 2) {
    elements.depthHintText.textContent = "2 Levels: Creates main category folders and at most one subfolder level (e.g. Certificates/Web).";
  } else if (depthVal === 3) {
    elements.depthHintText.textContent = "3 Levels: Allows up to 3 hierarchical subfolder levels.";
  } else {
    elements.depthHintText.textContent = "Unlimited: Allows full hierarchical multi-level directory structures.";
  }
}

// 1. Scan Directory
async function triggerScan() {
  const path = elements.pathInput.value.trim();
  if (!path) {
    showToast("Please enter a target folder path to scan.", "error");
    return;
  }

  setSystemStatus("Scanning target directory...", true);
  elements.btnStartScan.disabled = true;

  try {
    const resp = await fetch("http://localhost:8000/api/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        path: path,
        recursive: elements.recursiveToggle.checked,
      }),
    });

    const data = await resp.json();
    if (!resp.ok) {
      throw new Error(data.detail || "Failed to scan folder.");
    }

    state.currentRoot = data.root_path;
    state.scannedFiles = data.files || [];
    state.duplicates = data.duplicates || { exact_duplicates: [], similar_images: [] };
    state.unnecessaryFiles = data.unnecessary || [];

    updateStats();
    renderDuplicates();
    renderCleanup();

    if (state.scannedFiles.length === 0) {
      if (elements.fileTypesPanel) elements.fileTypesPanel.style.display = "none";
      showToast("Directory scanned. No files found.", "info");
      setSystemStatus("No files found in folder.", false);
      return;
    }

    // Reveal and render discovered file types selection panel
    renderDiscoveredFileTypes();
    showToast(`Found ${state.scannedFiles.length} files. Review file types below to organize.`, "success");
    setSystemStatus(`Discovered ${state.scannedFiles.length} files. Select types to organize.`, false);

    // Scroll to the selection panel smoothly
    if (elements.fileTypesPanel) {
      elements.fileTypesPanel.style.display = "block";
      elements.fileTypesPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  } catch (err) {
    showToast(err.message, "error");
    setSystemStatus("Scan stopped: " + err.message, false);
  } finally {
    elements.btnStartScan.disabled = false;
  }
}

// 2. Pre-Analysis Discovered File Types Grouping & Selection
function renderDiscoveredFileTypes() {
  if (!elements.fileCategoriesGrid) return;
  elements.fileCategoriesGrid.innerHTML = "";

  // Group files by category
  const groups = {};
  state.scannedFiles.forEach((file) => {
    const cat = file.category || "General";
    if (!groups[cat]) {
      groups[cat] = {
        name: cat,
        files: [],
        extensions: new Set(),
        totalBytes: 0,
      };
    }
    groups[cat].files.push(file);
    if (file.extension) groups[cat].extensions.add(file.extension.toLowerCase());
    groups[cat].totalBytes += file.size_bytes || 0;
  });

  // Default: select all discovered categories
  state.selectedCategories = new Set(Object.keys(groups));

  if (elements.fileTypesCountBadge) {
    elements.fileTypesCountBadge.textContent = `${state.scannedFiles.length} file${state.scannedFiles.length > 1 ? "s" : ""} found`;
  }

  Object.values(groups).forEach((group) => {
    const card = document.createElement("div");
    card.className = "category-card selected";
    card.dataset.category = group.name;

    const extList = Array.from(group.extensions).slice(0, 4).join(", ") || group.name;
    const iconSvg = getCategoryIconSvg(group.name);

    card.innerHTML = `
      <div class="category-card-left">
        <label class="table-checkbox-label">
          <input type="checkbox" class="cat-checkbox" checked />
          <span class="checkbox-box"></span>
        </label>
        <div class="category-icon">${iconSvg}</div>
        <div class="category-text-wrap">
          <span class="category-name">${escapeHtml(group.name)}</span>
          <span class="category-extensions">${escapeHtml(extList)}</span>
        </div>
      </div>
      <div class="category-card-right">
        <span class="category-count">${group.files.length} file${group.files.length > 1 ? "s" : ""}</span>
        <span class="category-size">${formatBytes(group.totalBytes)}</span>
      </div>
    `;

    // Click handler for card selection toggle
    card.addEventListener("click", (e) => {
      // Prevent double trigger if clicking directly on checkbox input
      if (e.target.tagName.toLowerCase() === "input") return;
      const checkbox = card.querySelector(".cat-checkbox");
      checkbox.checked = !checkbox.checked;
      toggleCategorySelection(group.name, checkbox.checked, card);
    });

    const checkbox = card.querySelector(".cat-checkbox");
    checkbox.addEventListener("change", (e) => {
      toggleCategorySelection(group.name, e.target.checked, card);
    });

    elements.fileCategoriesGrid.appendChild(card);
  });

  updateSelectedFilesSummary();
}

function toggleCategorySelection(catName, isChecked, cardEl) {
  if (isChecked) {
    state.selectedCategories.add(catName);
    cardEl.classList.add("selected");
  } else {
    state.selectedCategories.delete(catName);
    cardEl.classList.remove("selected");
  }
  updateSelectedFilesSummary();
}

function selectAllFileTypes() {
  document.querySelectorAll(".category-card").forEach((card) => {
    const cat = card.dataset.category;
    state.selectedCategories.add(cat);
    card.classList.add("selected");
    const cb = card.querySelector(".cat-checkbox");
    if (cb) cb.checked = true;
  });
  updateSelectedFilesSummary();
}

function deselectAllFileTypes() {
  state.selectedCategories.clear();
  document.querySelectorAll(".category-card").forEach((card) => {
    card.classList.remove("selected");
    const cb = card.querySelector(".cat-checkbox");
    if (cb) cb.checked = false;
  });
  updateSelectedFilesSummary();
}

function updateSelectedFilesSummary() {
  const selectedFiles = state.scannedFiles.filter((f) => state.selectedCategories.has(f.category || "General"));
  const totalBytes = selectedFiles.reduce((acc, f) => acc + (f.size_bytes || 0), 0);

  if (elements.selectedFilesSummary) {
    elements.selectedFilesSummary.innerHTML = `Selected: <strong>${selectedFiles.length} of ${state.scannedFiles.length} files</strong> (${formatBytes(totalBytes)})`;
  }
  if (elements.btnRunAiText) {
    elements.btnRunAiText.textContent = `Run AI Organization (${selectedFiles.length} Files)`;
  }
  if (elements.btnRunAI) {
    elements.btnRunAI.disabled = selectedFiles.length === 0;
  }
}

function getCategoryIconSvg(category) {
  const cat = (category || "").toLowerCase();
  if (cat.includes("image")) {
    return `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>`;
  }
  if (cat.includes("doc")) {
    return `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>`;
  }
  if (cat.includes("audio") || cat.includes("music")) {
    return `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18V5l12-2v13"></path><circle cx="6" cy="18" r="3"></circle><circle cx="18" cy="16" r="3"></circle></svg>`;
  }
  if (cat.includes("video")) {
    return `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="23 7 16 12 23 17 23 7"></polygon><rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect></svg>`;
  }
  if (cat.includes("code") || cat.includes("script")) {
    return `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline></svg>`;
  }
  if (cat.includes("archive") || cat.includes("zip")) {
    return `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="21 8 21 21 3 21 3 8"></polyline><rect x="1" y="3" width="22" height="5"></rect><line x1="10" y1="12" x2="14" y2="12"></line></svg>`;
  }
  return `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path><polyline points="13 2 13 9 20 9"></polyline></svg>`;
}

// 3. AI Analysis on Selected Files with Depth Limit
async function triggerAIAnalysis() {
  const selectedFiles = state.scannedFiles.filter((f) => state.selectedCategories.has(f.category || "General"));
  if (selectedFiles.length === 0) {
    showToast("Please select at least one file category to organize.", "error");
    return;
  }

  const directive = elements.nlPromptInput ? elements.nlPromptInput.value.trim() : "";
  const provider = state.settings.default_provider || "gemini";
  const depthLimit = elements.depthLimitSelect ? parseInt(elements.depthLimitSelect.value, 10) : state.settings.max_depth || 1;

  const providerLabel =
    provider === "gemini"
      ? "Google Gemini Vision"
      : provider === "openai"
      ? "OpenAI Vision"
      : "Local Content Intelligence";

  setSystemStatus(`Analyzing ${selectedFiles.length} files with ${providerLabel}...`, true);
  elements.btnRunAI.disabled = true;

  openAnalysisProgressModal(selectedFiles.length, providerLabel);

  try {
    const reqBody = {
      files: selectedFiles,
      custom_instructions: directive || null,
      api_provider: provider,
      api_key: provider === "gemini" ? state.settings.gemini_key : state.settings.openai_key,
      max_depth: depthLimit,
    };

    let streamSucceeded = false;
    let proposedOperations = [];

    // Attempt streaming endpoint for live progress updates
    try {
      const resp = await fetch("http://localhost:8000/api/analyze/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(reqBody),
      });

      if (resp.ok && resp.body) {
        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split("\n\n");
          buffer = parts.pop();

          for (const part of parts) {
            const trimmed = part.trim();
            if (trimmed.startsWith("data: ")) {
              try {
                const event = JSON.parse(trimmed.slice(6));
                if (event.type === "progress") {
                  proposedOperations.push(event.operation);
                  updateAnalysisProgress(event.current, event.total, event.filename, event.operation);
                }
              } catch (e) {
                console.warn("Error parsing SSE event:", e);
              }
            }
          }
        }
        streamSucceeded = true;
      }
    } catch (streamErr) {
      console.warn("Streaming unavailable, falling back to batch analysis:", streamErr);
    }

    // Fallback to standard batch API if streaming failed
    if (!streamSucceeded || proposedOperations.length === 0) {
      const resp = await fetch("http://localhost:8000/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(reqBody),
      });

      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.detail || "Analysis failed.");
      }
      proposedOperations = data.proposed_operations || [];
      updateAnalysisProgress(selectedFiles.length, selectedFiles.length, "Complete", null);
    }

    state.proposedOperations = proposedOperations;

    // Small delay to allow the user to see the 100% completion state
    await new Promise((resolve) => setTimeout(resolve, 400));
    closeAnalysisProgressModal();

    // Switch to Suggestions tab and render
    document.querySelectorAll(".tab-item").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((c) => c.classList.remove("active"));
    const propTabBtn = document.querySelector('[data-tab="tab-proposed"]');
    if (propTabBtn) propTabBtn.classList.add("active");
    const propTabPanel = document.getElementById("tab-proposed");
    if (propTabPanel) propTabPanel.classList.add("active");

    renderProposals();
    updateStats();

    showToast(`Generated ${state.proposedOperations.length} organization suggestions!`, "success");
    setSystemStatus("Suggestions ready for user confirmation.", false);
  } catch (err) {
    closeAnalysisProgressModal();
    showToast(err.message, "error");
    setSystemStatus("Analysis error: " + err.message, false);
  } finally {
    elements.btnRunAI.disabled = false;
  }
}

// Progress Modal Controllers
function openAnalysisProgressModal(totalFiles, providerName) {
  if (elements.analysisEngineBadge) elements.analysisEngineBadge.textContent = providerName;
  if (elements.analysisProgressCount) elements.analysisProgressCount.textContent = `0 of ${totalFiles} processed`;
  if (elements.analysisProgressPercent) elements.analysisProgressPercent.textContent = "0%";
  if (elements.analysisProgressBar) elements.analysisProgressBar.style.width = "0%";
  if (elements.analysisCurrentFile) elements.analysisCurrentFile.textContent = "Extracting content & visual metadata...";
  if (elements.analysisMiniFeed) elements.analysisMiniFeed.innerHTML = "";
  if (elements.analysisBackdrop) elements.analysisBackdrop.classList.add("active");
}

function updateAnalysisProgress(current, total, filename, operation) {
  const percent = total > 0 ? Math.round((current / total) * 100) : 0;
  if (elements.analysisProgressCount) elements.analysisProgressCount.textContent = `${current} of ${total} processed`;
  if (elements.analysisProgressPercent) elements.analysisProgressPercent.textContent = `${percent}%`;
  if (elements.analysisProgressBar) elements.analysisProgressBar.style.width = `${percent}%`;
  if (elements.analysisCurrentFile) elements.analysisCurrentFile.textContent = `Analyzing: ${filename}`;

  if (operation && elements.analysisMiniFeed) {
    const row = document.createElement("div");
    row.className = "feed-row";
    const suggestedTarget = `${operation.suggested_folder || "Organized"}/${operation.suggested_name || filename}`;
    row.innerHTML = `
      <div class="feed-row-left">
        <span class="feed-check">✓</span>
        <span class="feed-name">${escapeHtml(operation.original_name || filename)}</span>
      </div>
      <span class="badge badge-neutral">${escapeHtml(operation.category || "Classified")}</span>
    `;
    elements.analysisMiniFeed.prepend(row);
  }
}

function closeAnalysisProgressModal() {
  if (elements.analysisBackdrop) elements.analysisBackdrop.classList.remove("active");
}

// 4. Render Proposals Table with Inline Editing
function renderProposals() {
  const tbody = elements.proposalsTableBody;
  tbody.innerHTML = "";

  if (state.proposedOperations.length === 0) {
    tbody.innerHTML = `
      <tr class="empty-state-row">
        <td colspan="6">
          <div class="empty-container">
            <div class="empty-icon">
              <svg viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
              </svg>
            </div>
            <div class="empty-heading">No Suggestions Available</div>
            <div class="empty-description">Select file types above and click "Run AI Organization" to generate structured naming suggestions.</div>
          </div>
        </td>
      </tr>
    `;
    updateSelectionSummary();
    return;
  }

  state.proposedOperations.forEach((op, idx) => {
    const tr = document.createElement("tr");

    const thumbnailHtml = op.thumbnail_b64
      ? `<img class="file-thumb-mini" src="data:image/jpeg;base64,${op.thumbnail_b64}" alt="thumb" />`
      : `<div class="file-thumb-mini" style="display:flex;align-items:center;justify-content:center;color:#64748b;">${getCategoryIconSvg(op.category)}</div>`;

    tr.innerHTML = `
      <td>
        <label class="table-checkbox-label">
          <input type="checkbox" class="op-checkbox" data-idx="${idx}" ${op.approved !== false ? "checked" : ""} />
          <span class="checkbox-box"></span>
        </label>
      </td>
      <td>
        <div class="cell-file-wrap">
          ${thumbnailHtml}
          <div class="file-info-col">
            <span class="file-name-text" title="${escapeHtml(op.original_name)}">${escapeHtml(op.original_name)}</span>
            <span class="file-meta-sub">${escapeHtml(op.category || "General")}</span>
          </div>
        </div>
      </td>
      <td>
        <input type="text" class="inline-edit-input op-name-input" data-idx="${idx}" value="${escapeHtml(op.suggested_name || op.original_name)}" />
      </td>
      <td>
        <input type="text" class="inline-edit-input op-folder-input" data-idx="${idx}" value="${escapeHtml(op.suggested_folder || "Organized")}" />
      </td>
      <td>
        <div class="reasoning-text" title="${escapeHtml(op.ai_reasoning || "")}">
          ${escapeHtml(op.ai_reasoning || "Categorized based on content analysis.")}
        </div>
      </td>
      <td style="text-align: right;">
        <button class="btn btn-secondary btn-sm btn-preview-op" data-path="${escapeHtml(op.original_path)}" title="Preview file">
          <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
          <span>Preview</span>
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });

  // Listeners for inline modifications
  tbody.querySelectorAll(".op-checkbox").forEach((cb) => {
    cb.addEventListener("change", (e) => {
      const idx = parseInt(e.target.dataset.idx, 10);
      state.proposedOperations[idx].approved = e.target.checked;
      updateSelectionSummary();
    });
  });

  tbody.querySelectorAll(".op-name-input").forEach((input) => {
    input.addEventListener("input", (e) => {
      const idx = parseInt(e.target.dataset.idx, 10);
      state.proposedOperations[idx].suggested_name = e.target.value.trim();
      state.proposedOperations[idx].target_name = e.target.value.trim();
    });
  });

  tbody.querySelectorAll(".op-folder-input").forEach((input) => {
    input.addEventListener("input", (e) => {
      const idx = parseInt(e.target.dataset.idx, 10);
      state.proposedOperations[idx].suggested_folder = e.target.value.trim();
      state.proposedOperations[idx].target_folder = e.target.value.trim();
    });
  });

  tbody.querySelectorAll(".btn-preview-op").forEach((btn) => {
    btn.addEventListener("click", () => openPreviewModal(btn.dataset.path));
  });

  updateSelectionSummary();
}

function updateSelectionSummary() {
  const approvedCount = state.proposedOperations.filter((o) => o.approved !== false).length;
  if (elements.selectionSummary) {
    elements.selectionSummary.textContent = `${approvedCount} of ${state.proposedOperations.length} selected for execution`;
  }
  if (elements.badgeProposedCount) elements.badgeProposedCount.textContent = state.proposedOperations.length;
  if (elements.statProposedOps) elements.statProposedOps.textContent = state.proposedOperations.length;
}

// 5. Execute Approved Operations
async function executeApprovedOperations() {
  const approvedOps = state.proposedOperations.filter((o) => o.approved !== false);
  if (approvedOps.length === 0) {
    showToast("No operations selected to execute.", "info");
    return;
  }

  // Pre-process final target paths in case user edited target_name or target_folder inline
  const operationsPayload = approvedOps.map((op) => {
    const copy = { ...op };
    if (state.currentRoot && copy.suggested_folder && copy.suggested_name) {
      const folderParts = copy.suggested_folder.replace(/\\/g, "/").split("/").filter(Boolean);
      const rootStr = state.currentRoot.replace(/\\/g, "/");
      copy.target_path = `${rootStr}/${folderParts.join("/")}/${copy.suggested_name}`;
    }
    return copy;
  });

  setSystemStatus("Executing file organization operations...", true);
  elements.btnExecuteApproved.disabled = true;

  try {
    const resp = await fetch("http://localhost:8000/api/execute", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ operations: operationsPayload }),
    });

    const data = await resp.json();
    if (!resp.ok) {
      throw new Error(data.detail || "Execution failed.");
    }

    showToast(`Successfully organized ${data.executed_count} files!`, "success");
    setSystemStatus(`Complete. ${data.executed_count} files organized.`, false);

    // Refresh view by rescanning
    await triggerScan();
    await loadHistory();
  } catch (err) {
    showToast(err.message, "error");
    setSystemStatus("Execution failed: " + err.message, false);
  } finally {
    elements.btnExecuteApproved.disabled = false;
  }
}

function resetSuggestions() {
  state.proposedOperations = [];
  renderProposals();
  showToast("Suggestions discarded.", "info");
}

// 6. Duplicates & Cleanup Views
function renderDuplicates() {
  const exactContainer = elements.exactDuplicatesList;
  const similarContainer = elements.similarImagesList;
  if (!exactContainer || !similarContainer) return;

  exactContainer.innerHTML = "";
  similarContainer.innerHTML = "";

  const exacts = state.duplicates.exact_duplicates || [];
  const similars = state.duplicates.similar_images || [];

  if (elements.badgeDuplicatesCount) elements.badgeDuplicatesCount.textContent = exacts.length + similars.length;
  if (elements.statDuplicates) elements.statDuplicates.textContent = exacts.length + similars.length;

  if (exacts.length === 0) {
    exactContainer.innerHTML = '<div class="empty-subpanel-state">No cryptographic duplicate files detected.</div>';
  } else {
    exacts.forEach((group) => {
      const card = document.createElement("div");
      card.className = "duplicate-group-card";
      card.innerHTML = `
        <div class="duplicate-group-header">
          <span>SHA-256: <code>${group.sha256.substring(0, 16)}...</code></span>
          <span>${group.count} identical copies (${formatBytes(group.wasted_bytes)} redundant)</span>
        </div>
        <div class="duplicate-files-list">
          ${group.files
            .map(
              (f, i) => `
            <div class="duplicate-file-row">
              <div>
                <strong>${escapeHtml(f.name)}</strong>
                <span style="color: var(--text-muted); font-size: 0.78rem; margin-left: 6px;">(${f.size_formatted})</span>
              </div>
              <div>
                ${i === 0 ? '<span class="badge badge-primary">Preserved</span>' : `<button class="btn btn-secondary btn-sm btn-trash-file" data-path="${escapeHtml(f.full_path)}">Recycle Copy</button>`}
              </div>
            </div>
          `
            )
            .join("")}
        </div>
      `;
      exactContainer.appendChild(card);
    });

    exactContainer.querySelectorAll(".btn-trash-file").forEach((b) => {
      b.addEventListener("click", () => trashSingleFile(b.dataset.path));
    });
  }

  if (similars.length === 0) {
    similarContainer.innerHTML = '<div class="empty-subpanel-state">No visually similar images detected.</div>';
  } else {
    similars.forEach((pair) => {
      const card = document.createElement("div");
      card.className = "duplicate-group-card";
      card.innerHTML = `
        <div class="duplicate-group-header">
          <span class="badge badge-warning">${pair.similarity_percent}% Similar</span>
        </div>
        <div class="duplicate-files-list">
          <div class="duplicate-file-row">
            <span>${escapeHtml(pair.file_a.name)}</span>
            <button class="btn btn-secondary btn-sm btn-preview-op" data-path="${escapeHtml(pair.file_a.full_path)}">Preview</button>
          </div>
          <div class="duplicate-file-row">
            <span>${escapeHtml(pair.file_b.name)}</span>
            <button class="btn btn-secondary btn-sm btn-preview-op" data-path="${escapeHtml(pair.file_b.full_path)}">Preview</button>
          </div>
        </div>
      `;
      similarContainer.appendChild(card);
    });

    similarContainer.querySelectorAll(".btn-preview-op").forEach((b) => {
      b.addEventListener("click", () => openPreviewModal(b.dataset.path));
    });
  }
}

function renderCleanup() {
  const tbody = elements.cleanupTableBody;
  if (!tbody) return;
  tbody.innerHTML = "";

  const list = state.unnecessaryFiles || [];
  if (elements.badgeCleanupCount) elements.badgeCleanupCount.textContent = list.length;
  if (elements.statUnnecessary) elements.statUnnecessary.textContent = list.length;

  if (list.length === 0) {
    tbody.innerHTML = '<tr class="empty-state-row"><td colspan="5"><div class="empty-subpanel-state">No clutter or temporary files found.</div></td></tr>';
    return;
  }

  list.forEach((item) => {
    const f = item.file;
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>
        <strong>${escapeHtml(f.name)}</strong>
        <div style="font-size: 0.74rem; color: var(--text-muted);">${escapeHtml(f.relative_path)}</div>
      </td>
      <td>${f.size_formatted}</td>
      <td style="color: #f87171;">${escapeHtml(item.primary_reason)}</td>
      <td><span class="badge badge-neutral">${escapeHtml(item.confidence)}</span></td>
      <td style="text-align: right;">
        <button class="btn btn-danger btn-sm btn-trash-unnecessary" data-path="${escapeHtml(f.full_path)}">Recycle</button>
      </td>
    `;
    tbody.appendChild(tr);
  });

  tbody.querySelectorAll(".btn-trash-unnecessary").forEach((btn) => {
    btn.addEventListener("click", () => trashSingleFile(btn.dataset.path));
  });
}

async function batchTrashUnnecessary() {
  const list = state.unnecessaryFiles || [];
  if (list.length === 0) {
    showToast("No clutter files to recycle.", "info");
    return;
  }
  if (!confirm(`Are you sure you want to recycle all ${list.length} flagged clutter files?`)) {
    return;
  }

  const operations = list.map((item) => ({
    id: "del-" + Math.random().toString(36).substring(2, 9),
    action_type: "delete",
    original_path: item.file.full_path,
    original_name: item.file.name,
    ai_reasoning: `Batch clutter cleanup: ${item.primary_reason}`,
    approved: true,
  }));

  try {
    const resp = await fetch("http://localhost:8000/api/execute", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ operations }),
    });
    const data = await resp.json();
    if (data.success) {
      showToast(`Recycled ${data.executed_count} clutter files!`, "success");
      await triggerScan();
      await loadHistory();
    }
  } catch (e) {
    showToast("Batch cleanup failed: " + e.message, "error");
  }
}

async function trashSingleFile(filePath) {
  if (!confirm(`Recycle file?\n${filePath}`)) return;

  const op = {
    id: "del-" + Date.now(),
    action_type: "delete",
    original_path: filePath,
    original_name: filePath.split(/[\\/]/).pop(),
    ai_reasoning: "User confirmed cleanup deletion.",
    approved: true,
  };

  try {
    const resp = await fetch("http://localhost:8000/api/execute", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ operations: [op] }),
    });
    const data = await resp.json();
    if (data.success) {
      showToast("File recycled with undo capability.", "info");
      await triggerScan();
      await loadHistory();
    }
  } catch (e) {
    showToast("Delete failed: " + e.message, "error");
  }
}

// 7. Preview Modal
async function openPreviewModal(filePath) {
  elements.previewFilename.textContent = "Loading file details...";
  elements.previewModalContent.innerHTML = '<div class="preview-loading">Extracting metadata and content...</div>';
  elements.previewBackdrop.classList.add("active");

  try {
    const resp = await fetch(`http://localhost:8000/api/preview?path=${encodeURIComponent(filePath)}`);
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || "Preview failed");

    elements.previewFilename.textContent = data.file_name;
    const meta = data.metadata || {};

    let metaRows = "";
    Object.entries(meta).forEach(([k, v]) => {
      if (v) {
        metaRows += `<tr><td style="color:var(--text-muted);width:120px;">${escapeHtml(k)}</td><td><strong>${escapeHtml(String(v))}</strong></td></tr>`;
      }
    });

    let visualSection = "";
    if (data.thumbnail_b64) {
      visualSection = `<div style="text-align:center;margin-bottom:16px;"><img src="data:image/jpeg;base64,${data.thumbnail_b64}" style="max-height:220px;border-radius:6px;border:1px solid var(--border-subtle);" /></div>`;
    }

    elements.previewModalContent.innerHTML = `
      ${visualSection}
      <div style="font-size:0.84rem;margin-bottom:12px;">
        <table style="width:100%;border-collapse:collapse;">
          <tr><td style="color:var(--text-muted);width:120px;">Size</td><td>${formatBytes(data.size_bytes)}</td></tr>
          <tr><td style="color:var(--text-muted);">Content Type</td><td>${escapeHtml(data.content_type || "Unknown")}</td></tr>
          ${metaRows}
        </table>
      </div>
      ${
        data.text_sample
          ? `<div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:4px;text-transform:uppercase;font-weight:600;">Text Extract</div>
             <pre style="background:var(--bg-app);padding:10px;border-radius:6px;font-family:var(--font-mono);font-size:0.78rem;max-height:160px;overflow-y:auto;white-space:pre-wrap;color:var(--text-secondary);">${escapeHtml(data.text_sample)}</pre>`
          : ""
      }
    `;
  } catch (err) {
    elements.previewModalContent.innerHTML = `<div style="color: #ef4444;">Preview error: ${escapeHtml(err.message)}</div>`;
  }
}

function closePreviewModal() {
  elements.previewBackdrop.classList.remove("active");
}

// 8. Settings Modal
function openSettingsModal() {
  const provider = state.settings.default_provider || "gemini";
  const radio = document.querySelector(`input[name="ai_provider"][value="${provider}"]`);
  if (radio) radio.checked = true;

  if (elements.geminiKeyInput) elements.geminiKeyInput.value = state.settings.gemini_key || "";
  if (elements.openaiKeyInput) elements.openaiKeyInput.value = state.settings.openai_key || "";
  if (elements.settingsMaxDepth) elements.settingsMaxDepth.value = String(state.settings.max_depth || 1);

  elements.settingsBackdrop.classList.add("active");
}

function closeSettingsModal() {
  elements.settingsBackdrop.classList.remove("active");
}

async function loadSettings() {
  try {
    const resp = await fetch("http://localhost:8000/api/settings");
    const data = await resp.json();
    if (data.success && data.settings) {
      state.settings = { ...state.settings, ...data.settings };
      if (data.settings.max_depth) {
        state.settings.max_depth = parseInt(data.settings.max_depth, 10) || 1;
      }
      if (elements.depthLimitSelect) {
        elements.depthLimitSelect.value = String(state.settings.max_depth);
        updateDepthHint(state.settings.max_depth);
      }
      if (elements.settingsMaxDepth) {
        elements.settingsMaxDepth.value = String(state.settings.max_depth);
      }
    }
  } catch (e) {
    console.warn("Could not load backend settings:", e);
  }
}

async function saveSettings() {
  const selectedRadio = document.querySelector('input[name="ai_provider"]:checked');
  const provider = selectedRadio ? selectedRadio.value : "gemini";
  const geminiKey = elements.geminiKeyInput.value.trim();
  const openaiKey = elements.openaiKeyInput.value.trim();
  const maxDepth = elements.settingsMaxDepth ? parseInt(elements.settingsMaxDepth.value, 10) : 1;

  try {
    const resp = await fetch("http://localhost:8000/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        default_provider: provider,
        gemini_key: geminiKey,
        openai_key: openaiKey,
        max_depth: maxDepth,
      }),
    });
    const data = await resp.json();
    if (data.success) {
      state.settings.default_provider = provider;
      state.settings.gemini_key = geminiKey;
      state.settings.openai_key = openaiKey;
      state.settings.max_depth = maxDepth;

      if (elements.depthLimitSelect) {
        elements.depthLimitSelect.value = String(maxDepth);
        updateDepthHint(maxDepth);
      }

      showToast("Configuration saved successfully.", "success");
      closeSettingsModal();
    }
  } catch (err) {
    showToast("Failed to save settings: " + err.message, "error");
  }
}

// 9. History Slide Drawer & Undo
function openHistoryDrawer() {
  loadHistory();
  elements.historyDrawer.classList.add("active");
  elements.drawerBackdrop.classList.add("active");
}

function closeHistoryDrawer() {
  elements.historyDrawer.classList.remove("active");
  elements.drawerBackdrop.classList.remove("active");
}

async function loadHistory() {
  const container = elements.historyListContainer;
  container.innerHTML = '<div class="empty-drawer-state">Loading operation log...</div>';

  try {
    const resp = await fetch("http://localhost:8000/api/history");
    const data = await resp.json();
    if (!data.success || !data.history || data.history.length === 0) {
      container.innerHTML = '<div class="empty-drawer-state">No operations logged yet.</div>';
      return;
    }

    container.innerHTML = "";
    data.history.forEach((item) => {
      const card = document.createElement("div");
      card.className = "history-item-card";
      card.innerHTML = `
        <div class="history-item-top">
          <span>${escapeHtml(item.action_type || "organize").toUpperCase()}</span>
          <span>${item.executed_at ? item.executed_at.substring(0, 19).replace("T", " ") : ""}</span>
        </div>
        <div class="history-path-info">${escapeHtml(item.source_path)}</div>
        <div style="font-size: 0.76rem; color: var(--text-muted);">➔ ${escapeHtml(item.destination_path || "Deleted")}</div>
        <div style="display: flex; justify-content: flex-end; margin-top: 6px;">
          ${
            item.status === "completed"
              ? `<button class="btn btn-secondary btn-sm btn-undo-op" data-id="${item.id}">Undo</button>`
              : '<span class="badge badge-neutral">Reverted</span>'
          }
        </div>
      `;
      container.appendChild(card);
    });

    container.querySelectorAll(".btn-undo-op").forEach((b) => {
      b.addEventListener("click", () => undoSingleOperation(b.dataset.id));
    });
  } catch (err) {
    container.innerHTML = `<div style="color: #ef4444;">Error loading history: ${err.message}</div>`;
  }
}

async function undoSingleOperation(opId) {
  try {
    const resp = await fetch("http://localhost:8000/api/undo", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ operation_id: parseInt(opId, 10) }),
    });
    const data = await resp.json();
    if (data.success) {
      showToast("Operation undone successfully.", "success");
      await loadHistory();
      await triggerScan();
    } else {
      showToast(data.message || "Undo failed.", "error");
    }
  } catch (err) {
    showToast("Undo error: " + err.message, "error");
  }
}

// Helpers
function updateStats() {
  if (elements.statTotalFiles) elements.statTotalFiles.textContent = state.scannedFiles.length;
}

function setSystemStatus(text, isBusy) {
  if (elements.systemStatusText) elements.systemStatusText.textContent = text;
  if (elements.systemStatusPill) {
    if (isBusy) {
      elements.systemStatusPill.className = "status-indicator busy";
    } else {
      elements.systemStatusPill.className = "status-indicator ready";
    }
  }
}

function showToast(message, type = "info") {
  if (!elements.toastContainer) return;
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = message;

  elements.toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(8px)";
    toast.style.transition = "all 150ms ease";
    setTimeout(() => toast.remove(), 160);
  }, 3200);
}

function formatBytes(bytes) {
  if (!bytes || bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
