function projectId() {
  return "_active";
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

async function loadChildren() {
  const res = await fetch("/api/children");
  const data = await res.json();
  const select = document.getElementById("childSelect");
  select.innerHTML = "";
  for (const c of data.children || []) {
    const opt = document.createElement("option");
    opt.value = c.child_id;
    opt.textContent = `${c.child_name} (${c.child_id}) [${c.status}]`;
    if (c.child_id === data.active_child_id) opt.selected = true;
    select.appendChild(opt);
  }
}

async function selectChild(childId) {
  const res = await fetch("/api/children/select", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ child_id: childId })
  });
  const data = await res.json();
  setText("childResult", JSON.stringify(data, null, 2));
  await loadIngested();
}

async function loadIngested() {
  const res = await fetch(`/api/projects/${projectId()}/ingested`);
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
  const form = new FormData();
  for (const f of files) form.append("files", f);
  const res = await fetch(`/api/projects/${projectId()}/ingest-ppts`, { method: "POST", body: form });
  const data = await res.json();
  setText("ingestResult", JSON.stringify(data, null, 2));
  await loadIngested();
}

document.getElementById("childSelect").addEventListener("change", async (e) => {
  await selectChild(e.target.value);
});

document.getElementById("createChildBtn").addEventListener("click", async () => {
  const childId = document.getElementById("newChildId").value.trim();
  const childName = document.getElementById("newChildName").value.trim();
  if (!childId || !childName) return;
  const res = await fetch("/api/children/create", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ child_id: childId, child_name: childName })
  });
  const data = await res.json();
  setText("childResult", JSON.stringify(data, null, 2));
  await loadChildren();
});

document.getElementById("cloneChildBtn").addEventListener("click", async () => {
  const source = document.getElementById("childSelect").value;
  const target = prompt("Target child id:");
  const name = prompt("Target child name:");
  if (!source || !target || !name) return;
  const res = await fetch("/api/children/clone", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source_child_id: source, target_child_id: target, target_child_name: name })
  });
  const data = await res.json();
  setText("childResult", JSON.stringify(data, null, 2));
  await loadChildren();
});

document.getElementById("archiveChildBtn").addEventListener("click", async () => {
  const childId = document.getElementById("childSelect").value;
  if (!childId) return;
  const res = await fetch("/api/children/archive", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ child_id: childId })
  });
  const data = await res.json();
  setText("childResult", JSON.stringify(data, null, 2));
  await loadChildren();
  await loadIngested();
});

document.getElementById("loadIngestedBtn").addEventListener("click", loadIngested);
document.getElementById("ingestBtn").addEventListener("click", async () => {
  const files = document.getElementById("pptFiles").files;
  if (!files.length) return;
  await ingestSelected(files);
});

document.getElementById("ctxUploadBtn").addEventListener("click", async () => {
  const files = document.getElementById("ctxFiles").files;
  if (!files.length) return;
  const form = new FormData();
  for (const f of files) form.append("files", f);
  const res = await fetch(`/api/projects/${projectId()}/upload-context`, { method: "POST", body: form });
  const data = await res.json();
  setText("ctxResult", JSON.stringify(data, null, 2));
});

document.getElementById("templateUploadBtn").addEventListener("click", async () => {
  const input = document.getElementById("templateFile");
  if (!input.files.length) return;
  const form = new FormData();
  form.append("file", input.files[0]);
  const res = await fetch(`/api/projects/${projectId()}/upload-template`, { method: "POST", body: form });
  const data = await res.json();
  setText("templateResult", JSON.stringify(data, null, 2));
});

document.getElementById("templateStatusBtn").addEventListener("click", async () => {
  const res = await fetch(`/api/projects/${projectId()}/template`);
  const data = await res.json();
  setText("templateResult", JSON.stringify(data, null, 2));
});

document.getElementById("generateBtn").addEventListener("click", async () => {
  const payload = {
    task_name: document.getElementById("taskName").value.trim(),
    task_desc: document.getElementById("taskDesc").value.trim(),
    report_type: document.getElementById("reportType").value
  };
  const res = await fetch(`/api/projects/${projectId()}/plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  const data = await res.json();
  setText("planResult", JSON.stringify(data, null, 2));
});

document.getElementById("chatBtn").addEventListener("click", async () => {
  const input = document.getElementById("chatInput");
  const message = input.value.trim();
  if (!message) return;
  addChatLine("user", message);
  input.value = "";
  const res = await fetch(`/api/projects/${projectId()}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message })
  });
  const data = await res.json();
  addChatLine("agent", data.response || JSON.stringify(data));
});

document.getElementById("childStatusBtn").addEventListener("click", async () => {
  const res = await fetch(`/api/projects/${projectId()}/child/status`);
  const data = await res.json();
  setText("childResult", JSON.stringify(data, null, 2));
});

document.getElementById("childExportBtn").addEventListener("click", async () => {
  const res = await fetch(`/api/projects/${projectId()}/child/export`, { method: "POST" });
  const data = await res.json();
  setText("childResult", JSON.stringify(data, null, 2));
});

document.getElementById("childImportBtn").addEventListener("click", async () => {
  const input = document.getElementById("childImportFile");
  if (!input.files.length) return;
  const form = new FormData();
  form.append("file", input.files[0]);
  const res = await fetch(`/api/projects/${projectId()}/child/import`, { method: "POST", body: form });
  const data = await res.json();
  setText("childResult", JSON.stringify(data, null, 2));
});

document.getElementById("childImportAsNewBtn").addEventListener("click", async () => {
  const input = document.getElementById("childImportFile");
  const childId = document.getElementById("importNewChildId").value.trim();
  const childName = document.getElementById("importNewChildName").value.trim();
  if (!input.files.length || !childId || !childName) return;
  const form = new FormData();
  form.append("file", input.files[0]);
  const res = await fetch(`/api/children/import-as-new?child_id=${encodeURIComponent(childId)}&child_name=${encodeURIComponent(childName)}`, {
    method: "POST",
    body: form
  });
  const data = await res.json();
  setText("childResult", JSON.stringify(data, null, 2));
  await loadChildren();
});

document.getElementById("mergePreviewBtn").addEventListener("click", async () => {
  const source = document.getElementById("mergeSourceId").value.trim();
  const target = document.getElementById("mergeTargetId").value.trim();
  const strategy = document.getElementById("mergeStrategy").value;
  if (!source || !target) return;
  const res = await fetch("/api/children/merge-preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source_child_id: source, target_child_id: target, strategy })
  });
  const data = await res.json();
  setText("childResult", JSON.stringify(data, null, 2));
});

document.getElementById("mergeApplyBtn").addEventListener("click", async () => {
  const source = document.getElementById("mergeSourceId").value.trim();
  const target = document.getElementById("mergeTargetId").value.trim();
  const strategy = document.getElementById("mergeStrategy").value;
  if (!source || !target) return;
  const res = await fetch("/api/children/merge-apply", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source_child_id: source, target_child_id: target, strategy })
  });
  const data = await res.json();
  setText("childResult", JSON.stringify(data, null, 2));
  await loadChildren();
});

document.getElementById("masterPolicyBtn").addEventListener("click", async () => {
  const mode = document.getElementById("masterPolicyMode").value;
  const strategy = document.getElementById("masterPolicyStrategy").value;
  const res = await fetch("/api/master/policy", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode, strategy })
  });
  const data = await res.json();
  setText("masterResult", JSON.stringify(data, null, 2));
});

document.getElementById("masterHealthBtn").addEventListener("click", async () => {
  const res = await fetch("/api/master/health");
  const data = await res.json();
  setText("masterResult", JSON.stringify(data, null, 2));
});

document.getElementById("masterSyncBtn").addEventListener("click", async () => {
  const strategy = document.getElementById("masterPolicyStrategy").value;
  const res = await fetch(`/api/master/sync/run?strategy=${encodeURIComponent(strategy)}`, {
    method: "POST"
  });
  const data = await res.json();
  setText("masterResult", JSON.stringify(data, null, 2));
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

async function boot() {
  await loadChildren();
  await loadIngested();
}

boot();
