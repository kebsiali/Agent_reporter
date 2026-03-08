function projectId() {
  const value = document.getElementById("projectId").value.trim();
  return value || "default_project";
}

function setText(id, text) {
  document.getElementById(id).textContent = text;
}

function addChatLine(role, text) {
  const log = document.getElementById("chatLog");
  const div = document.createElement("div");
  div.className = role === "user" ? "chat-user" : "chat-agent";
  div.textContent = `${role.toUpperCase()}: ${text}`;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

async function loadIngested() {
  const pid = projectId();
  const res = await fetch(`/api/projects/${pid}/ingested`);
  const data = await res.json();
  const ul = document.getElementById("ingestedList");
  ul.innerHTML = "";
  for (const f of data.files || []) {
    const li = document.createElement("li");
    li.textContent = `${f.file_name} (${f.status})`;
    ul.appendChild(li);
  }
}

async function ingestSelected(files) {
  const pid = projectId();
  const form = new FormData();
  for (const f of files) form.append("files", f);
  const res = await fetch(`/api/projects/${pid}/ingest-ppts`, { method: "POST", body: form });
  const data = await res.json();
  setText("ingestResult", JSON.stringify(data, null, 2));
  await loadIngested();
}

document.getElementById("loadIngestedBtn").addEventListener("click", loadIngested);
document.getElementById("ingestBtn").addEventListener("click", async () => {
  const files = document.getElementById("pptFiles").files;
  if (!files.length) return;
  await ingestSelected(files);
});

document.getElementById("ctxUploadBtn").addEventListener("click", async () => {
  const pid = projectId();
  const files = document.getElementById("ctxFiles").files;
  if (!files.length) return;
  const form = new FormData();
  for (const f of files) form.append("files", f);
  const res = await fetch(`/api/projects/${pid}/upload-context`, { method: "POST", body: form });
  const data = await res.json();
  setText("ctxResult", JSON.stringify(data, null, 2));
});

document.getElementById("generateBtn").addEventListener("click", async () => {
  const pid = projectId();
  const payload = {
    task_name: document.getElementById("taskName").value.trim(),
    task_desc: document.getElementById("taskDesc").value.trim(),
    report_type: document.getElementById("reportType").value
  };
  const res = await fetch(`/api/projects/${pid}/plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  const data = await res.json();
  setText("planResult", JSON.stringify(data, null, 2));
});

document.getElementById("chatBtn").addEventListener("click", async () => {
  const pid = projectId();
  const input = document.getElementById("chatInput");
  const message = input.value.trim();
  if (!message) return;
  addChatLine("user", message);
  input.value = "";
  const res = await fetch(`/api/projects/${pid}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message })
  });
  const data = await res.json();
  addChatLine("agent", data.response || JSON.stringify(data));
});

const dropZone = document.getElementById("dropZone");
dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropZone.classList.add("dragover");
});
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));
dropZone.addEventListener("drop", async (e) => {
  e.preventDefault();
  dropZone.classList.remove("dragover");
  const files = e.dataTransfer.files;
  if (!files.length) return;
  await ingestSelected(files);
});

loadIngested();

