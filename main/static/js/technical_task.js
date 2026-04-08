const form = document.getElementById("technicalTaskForm");
const autoSaveToast = document.getElementById("autoSaveToast");
const savingIndicator = document.getElementById("savingIndicator");
let autoSaveTimer = null;
let isSaving = false;
const AUTO_SAVE_DELAY = 2000;
function showAutoSaveToast() {
  autoSaveToast.classList.add("show");
  setTimeout(() => {
    autoSaveToast.classList.remove("show");
  }, 2000);
}
function showSavingIndicator() {
  savingIndicator.classList.add("show");
}
function hideSavingIndicator() {
  savingIndicator.classList.remove("show");
}
function getCsrfToken() {
  return document.querySelector("[name=csrfmiddlewaretoken]").value;
}
function getFormDataForAutoSave() {
  const formData = new FormData(form);
  const data = {};
  for (let [key, value] of formData.entries()) {
    if (key !== "attachments" && key !== "csrfmiddlewaretoken") {
      data[key] = value;
    }
  }
  return data;
}
async function autoSave() {
  if (isSaving) return;
  const data = getFormDataForAutoSave();
  const hasData = Object.values(data).some(
    (v) => v && v.trim && v.trim() !== "",
  );
  if (!hasData) return;
  isSaving = true;
  showSavingIndicator();
  try {
    const response = await fetch("/auto-save-technical-task/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify(data),
    });
    const result = await response.json();
    if (result.success) {
      showAutoSaveToast();
    } else {
      console.warn("Auto-save warning:", result.error);
    }
  } catch (error) {
    console.error("Auto-save error:", error);
  } finally {
    isSaving = false;
    hideSavingIndicator();
  }
}
function scheduleAutoSave() {
  if (autoSaveTimer) {
    clearTimeout(autoSaveTimer);
  }
  autoSaveTimer = setTimeout(autoSave, AUTO_SAVE_DELAY);
}
const inputs = form.querySelectorAll("input, select, textarea");
inputs.forEach((input) => {
  input.addEventListener("input", scheduleAutoSave);
  input.addEventListener("change", scheduleAutoSave);
});
const fileUploadArea = document.getElementById("fileUploadArea");
const fileInput = document.getElementById("fileInput");
const fileList = document.getElementById("fileList");
let selectedFiles = [];
fileUploadArea.addEventListener("click", () => {
  fileInput.click();
});
fileUploadArea.addEventListener("dragover", (e) => {
  e.preventDefault();
  fileUploadArea.style.borderColor = "var(--primary)";
  fileUploadArea.style.background = "rgba(0, 82, 204, 0.05)";
});
fileUploadArea.addEventListener("dragleave", (e) => {
  e.preventDefault();
  fileUploadArea.style.borderColor = "rgba(255, 255, 255, 0.2)";
  fileUploadArea.style.background = "transparent";
});
fileUploadArea.addEventListener("drop", (e) => {
  e.preventDefault();
  const files = Array.from(e.dataTransfer.files);
  addFiles(files);
  fileUploadArea.style.borderColor = "rgba(255, 255, 255, 0.2)";
  fileUploadArea.style.background = "transparent";
  scheduleAutoSave();
});
fileInput.addEventListener("change", (e) => {
  addFiles(Array.from(e.target.files));
  scheduleAutoSave();
});
function addFiles(files) {
  files.forEach((file) => {
    if (file.size > 20 * 1024 * 1024) {
      alert(`Файл${file.name}превышает20МБ`);
      return;
    }
    selectedFiles.push(file);
  });
  updateFileList();
  updateFormData();
}
function updateFileList() {
  fileList.innerHTML = "";
  selectedFiles.forEach((file, index) => {
    const fileItem = document.createElement("div");
    fileItem.className = "file-item";
    fileItem.innerHTML = `<i class="fas fa-file"></i><span>${escapeHtml(file.name)}</span><small>(${(file.size / 1024).toFixed(1)}KB)</small><i class="fas fa-times remove-file"data-index="${index}"></i>`;
    fileList.appendChild(fileItem);
  });
  document.querySelectorAll(".remove-file").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      const index = parseInt(btn.dataset.index);
      selectedFiles.splice(index, 1);
      updateFileList();
      updateFormData();
      scheduleAutoSave();
    });
  });
}
function updateFormData() {
  const dataTransfer = new DataTransfer();
  selectedFiles.forEach((file) => {
    dataTransfer.items.add(file);
  });
  fileInput.files = dataTransfer.files;
}
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
form.addEventListener("submit", (e) => {
  const required = [
    "full_name",
    "phone",
    "email",
    "task_type",
    "title",
    "description",
  ];
  let isValid = true;
  required.forEach((field) => {
    const input = form.querySelector(`[name=${field}]`);
    if (input && !input.value.trim()) {
      input.style.borderColor = "var(--danger)";
      isValid = false;
    } else if (input) {
      input.style.borderColor = "";
    }
  });
  if (!isValid) {
    e.preventDefault();
    alert("Пожалуйста, заполните все обязательные поля");
  }
});
window.addEventListener("beforeunload", () => {
  const data = getFormDataForAutoSave();
  const hasData = Object.values(data).some(
    (v) => v && v.trim && v.trim() !== "",
  );
  if (hasData) {
    navigator.sendBeacon("/auto-save-technical-task/", JSON.stringify(data));
  }
});
