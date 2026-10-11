"use strict";

const dropZone = document.getElementById("drop-zone");
const fileInput = document.getElementById("file-input");
const uploadButton = document.getElementById("upload-btn");
const statusElement = document.getElementById("status");
const resultCard = document.getElementById("result-card");
const minutesOutput = document.getElementById("minutes-output");
const transcriptOutput = document.getElementById("transcript-output");
const selectedFileElement = document.getElementById("selected-file");
const selectedFileName = document.getElementById("selected-file-name");
const selectedFileSize = document.getElementById("selected-file-size");
const minutesDownload = document.getElementById("download-minutes");
const transcriptDownload = document.getElementById("download-transcript");
const historyCard = document.getElementById("history-card");
const historyList = document.getElementById("job-history");

let selectedFile = null;
let selectedEngine = "whisper";
let pollTimer = null;

document.querySelectorAll(".engine-option").forEach((option) => {
  option.addEventListener("click", () => {
    document.querySelectorAll(".engine-option").forEach((item) => {
      item.classList.remove("selected");
    });
    option.classList.add("selected");
    option.querySelector("input").checked = true;
    selectedEngine = option.dataset.engine;
  });
});

document.querySelectorAll(".tab-btn").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((item) => {
      item.classList.remove("active");
    });
    document.querySelectorAll(".tab-content").forEach((content) => {
      content.classList.remove("active");
    });
    button.classList.add("active");
    document.getElementById(`tab-${button.dataset.tab}`).classList.add("active");
  });
});

dropZone.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("click", (event) => event.stopPropagation());
dropZone.addEventListener("dragover", (event) => {
  event.preventDefault();
  dropZone.classList.add("dragover");
});
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));
dropZone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropZone.classList.remove("dragover");
  if (event.dataTransfer.files.length) setFile(event.dataTransfer.files[0]);
});
fileInput.addEventListener("change", () => {
  if (fileInput.files.length) setFile(fileInput.files[0]);
});

function setFile(file) {
  selectedFile = file;
  document.getElementById("drop-prompt").classList.add("hidden");
  selectedFileElement.classList.remove("hidden");
  selectedFileName.textContent = file.name;
  selectedFileSize.textContent = `${(file.size / 1024 / 1024).toFixed(1)} MB`;
  uploadButton.disabled = false;
  statusElement.classList.add("hidden");
}

function setStatus(message, kind = "info", loading = false) {
  statusElement.replaceChildren();
  if (loading) {
    const spinner = document.createElement("span");
    spinner.className = "spinner";
    statusElement.append(spinner);
  }
  statusElement.append(document.createTextNode(message));
  statusElement.classList.remove("hidden");

  const styles = {
    info: ["#f0f4ff", "#333"],
    success: ["#eafbe7", "#2b8a3e"],
    error: ["#fff0f0", "#c92a2a"],
  };
  [statusElement.style.background, statusElement.style.color] = styles[kind];
}

async function readJson(response) {
  try {
    return await response.json();
  } catch {
    return {};
  }
}

async function loadHistory() {
  try {
    const response = await fetch("/jobs");
    if (!response.ok) return;
    const data = await readJson(response);
    historyList.replaceChildren();
    for (const job of data.jobs || []) {
      const row = document.createElement("li");
      const meta = document.createElement("div");
      meta.className = "job-meta";

      const name = document.createElement("span");
      name.className = "job-filename";
      name.textContent = job.filename;
      meta.append(name);

      const details = document.createElement("span");
      details.className = "job-date";
      details.textContent = `${new Date(job.created_at).toLocaleString("vi-VN")} · ${job.message}`;
      meta.append(details);
      row.append(meta);

      if (job.status === "completed") {
        const actions = document.createElement("div");
        actions.className = "job-actions";
        for (const [kind, label] of [["minutes", "Tải biên bản"], ["transcript", "Tải transcript"]]) {
          const link = document.createElement("a");
          link.href = `/results/${encodeURIComponent(job.job_id)}/${kind}`;
          link.textContent = label;
          actions.append(link);
        }
        row.append(actions);
      }
      historyList.append(row);
    }
    historyCard.classList.toggle("hidden", historyList.childElementCount === 0);
  } catch {
    // The upload and current job remain usable if history cannot be loaded.
  }
}

uploadButton.addEventListener("click", async () => {
  if (!selectedFile) return;
  uploadButton.disabled = true;
  resultCard.classList.add("hidden");
  minutesDownload.classList.add("hidden");
  transcriptDownload.classList.add("hidden");
  setStatus("Đang tải file lên...", "info", true);

  const formData = new FormData();
  formData.append("file", selectedFile);
  formData.append("engine", selectedEngine);

  try {
    const response = await fetch("/upload", { method: "POST", body: formData });
    const data = await readJson(response);
    if (!response.ok) {
      setStatus(data.error || "Không thể tải file lên.", "error");
      uploadButton.disabled = false;
      return;
    }
    loadHistory();
    pollStatus(data.job_id);
  } catch (error) {
    setStatus(`Lỗi kết nối tới server: ${error.message}`, "error");
    uploadButton.disabled = false;
  }
});

function pollStatus(jobId) {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    try {
      const response = await fetch(`/status/${encodeURIComponent(jobId)}`);
      const data = await readJson(response);
      if (!response.ok) throw new Error(data.error || "Không đọc được trạng thái job.");

      if (data.status === "completed") {
        clearInterval(pollTimer);
        pollTimer = null;
        setStatus("Hoàn tất! Xem kết quả bên dưới.", "success");
        // Render transcript and model output as text to prevent HTML/script injection.
        minutesOutput.textContent = data.minutes || "";
        transcriptOutput.textContent = data.transcript || "";
        minutesDownload.href = `/results/${encodeURIComponent(jobId)}/minutes`;
        transcriptDownload.href = `/results/${encodeURIComponent(jobId)}/transcript`;
        minutesDownload.classList.remove("hidden");
        transcriptDownload.classList.remove("hidden");
        resultCard.classList.remove("hidden");
        uploadButton.disabled = false;
        loadHistory();
      } else if (data.status === "error") {
        clearInterval(pollTimer);
        pollTimer = null;
        setStatus(data.message || "Không xử lý được file.", "error");
        uploadButton.disabled = false;
        loadHistory();
      } else {
        setStatus(data.message || "Đang xử lý...", "info", true);
      }
    } catch (error) {
      clearInterval(pollTimer);
      pollTimer = null;
      setStatus(error.message || "Mất kết nối tới server.", "error");
      uploadButton.disabled = false;
    }
  }, 3000);
}

loadHistory();
