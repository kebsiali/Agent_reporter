from __future__ import annotations

import hashlib
import re
import shutil
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ..child_memory import CURRENT_SCHEMA_VERSION, export_child_bundle, import_child_bundle
from ..chat import handle_chat
from ..exporter import export_plan_json, export_plan_markdown, export_plan_pptx
from ..indexer import (
    build_knowledge_base_with_diagnostics,
    load_knowledge_base,
    save_diagnostics,
    save_knowledge_base,
)
from ..planner import build_report_plan
from ..retrieval import build_semantic_index
from ..storage import find_by_hash, list_ingested_ppts, load_registry, register_ingested_file, save_registry
from ..storage.child_registry import (
    MASTER_CHILD_ID,
    archive_child,
    create_child,
    find_child,
    list_children,
    load_child_registry,
    save_child_registry,
    set_active_child,
)
from ..template import extract_template_profile, load_template_profile, save_template_profile


VALID_PROJECT = re.compile(r"^[a-zA-Z0-9_\-]{1,64}$")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    report_type: str = "simulation_request"
    semantic_top_k: int = 5


class PlanRequest(BaseModel):
    task_name: str = Field(min_length=1)
    task_desc: str = Field(min_length=1)
    report_type: str = "simulation_request"
    semantic_top_k: int = 4
    use_semantic: bool = True


class ChildCreateRequest(BaseModel):
    child_id: str = Field(min_length=1)
    child_name: str = Field(min_length=1)


class ChildSelectRequest(BaseModel):
    child_id: str = Field(min_length=1)


class ChildCloneRequest(BaseModel):
    source_child_id: str = Field(min_length=1)
    target_child_id: str = Field(min_length=1)
    target_child_name: str = Field(min_length=1)


def _validate_project_id(project_id: str) -> str:
    if not VALID_PROJECT.fullmatch(project_id):
        raise HTTPException(status_code=400, detail="Invalid child_id. Use letters/numbers/_/- only.")
    return project_id


def _registry_path(base_data_dir: Path) -> Path:
    return base_data_dir / "gui_projects" / "children_registry.json"


def _load_registry(base_data_dir: Path) -> dict[str, Any]:
    path = _registry_path(base_data_dir)
    reg = load_child_registry(path)
    save_child_registry(path, reg)
    return reg


def _save_registry(base_data_dir: Path, reg: dict[str, Any]) -> None:
    save_child_registry(_registry_path(base_data_dir), reg)


def _resolve_child_id(base_data_dir: Path, child_id_or_active: str) -> str:
    if child_id_or_active != "_active":
        return _validate_project_id(child_id_or_active)
    reg = _load_registry(base_data_dir)
    return reg.get("active_child_id", MASTER_CHILD_ID)


def _project_paths(base_data_dir: Path, child_id: str) -> dict[str, Path]:
    cid = _validate_project_id(child_id)
    root = base_data_dir / "gui_projects" / cid
    return {
        "root": root,
        "source_dir": root / "ingested_ppts",
        "context_dir": root / "context_files",
        "kb_path": root / "knowledge_base.json",
        "index_dir": root / "index",
        "sessions_dir": root / "sessions",
        "output_dir": root / "output",
        "diagnostics_path": root / "index_diagnostics.json",
        "registry_path": root / "ingestion_registry.json",
        "template_pptx": root / "template" / "company_template.pptx",
        "template_profile": root / "template" / "template_profile.json",
        "child_dir": root / "child",
        "child_exports": root / "child" / "exports",
        "child_snapshots": root / "child" / "snapshots",
    }


def _sha256(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def create_app(base_data_dir: Path = Path("data")) -> FastAPI:
    app = FastAPI(title="Reporter Agent GUI API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/")
    def root() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        _load_registry(base_data_dir)
        return {"status": "ok"}

    @app.get("/api/children")
    def get_children() -> dict[str, Any]:
        reg = _load_registry(base_data_dir)
        return {"active_child_id": reg.get("active_child_id", MASTER_CHILD_ID), "children": list_children(reg)}

    @app.post("/api/children/create")
    def create_child_api(payload: ChildCreateRequest) -> dict[str, Any]:
        reg = _load_registry(base_data_dir)
        created = create_child(reg, payload.child_id, payload.child_name)
        _save_registry(base_data_dir, reg)
        _project_paths(base_data_dir, payload.child_id)["root"].mkdir(parents=True, exist_ok=True)
        return {"created": created}

    @app.post("/api/children/select")
    def select_child_api(payload: ChildSelectRequest) -> dict[str, Any]:
        reg = _load_registry(base_data_dir)
        set_active_child(reg, payload.child_id)
        _save_registry(base_data_dir, reg)
        return {"active_child_id": payload.child_id}

    @app.post("/api/children/archive")
    def archive_child_api(payload: ChildSelectRequest) -> dict[str, Any]:
        reg = _load_registry(base_data_dir)
        archived = archive_child(reg, payload.child_id)
        _save_registry(base_data_dir, reg)
        return {"archived": archived, "active_child_id": reg.get("active_child_id")}

    @app.post("/api/children/clone")
    def clone_child_api(payload: ChildCloneRequest) -> dict[str, Any]:
        reg = _load_registry(base_data_dir)
        src = find_child(reg, payload.source_child_id)
        if not src:
            raise HTTPException(status_code=404, detail="Source child not found.")
        created = create_child(
            reg,
            payload.target_child_id,
            payload.target_child_name,
            origin=f"cloned_from:{payload.source_child_id}",
        )
        _save_registry(base_data_dir, reg)

        src_paths = _project_paths(base_data_dir, payload.source_child_id)
        dst_paths = _project_paths(base_data_dir, payload.target_child_id)
        if src_paths["root"].exists():
            shutil.copytree(src_paths["root"], dst_paths["root"], dirs_exist_ok=True)
        else:
            dst_paths["root"].mkdir(parents=True, exist_ok=True)
        return {"cloned": created}

    @app.get("/api/projects/{project_id}/ingested")
    def get_ingested(project_id: str) -> dict[str, Any]:
        child_id = _resolve_child_id(base_data_dir, project_id)
        paths = _project_paths(base_data_dir, child_id)
        registry = load_registry(paths["registry_path"])
        return {"project_id": child_id, "files": list_ingested_ppts(registry)}

    @app.get("/api/projects/{project_id}/context-files")
    def get_context_files(project_id: str) -> dict[str, Any]:
        child_id = _resolve_child_id(base_data_dir, project_id)
        paths = _project_paths(base_data_dir, child_id)
        paths["context_dir"].mkdir(parents=True, exist_ok=True)
        files = [p.name for p in sorted(paths["context_dir"].glob("*")) if p.is_file()]
        return {"project_id": child_id, "files": files}

    @app.get("/api/projects/{project_id}/template")
    def get_template(project_id: str) -> dict[str, Any]:
        child_id = _resolve_child_id(base_data_dir, project_id)
        paths = _project_paths(base_data_dir, child_id)
        profile = load_template_profile(paths["template_profile"])
        return {
            "project_id": child_id,
            "template_exists": paths["template_pptx"].exists(),
            "template_path": str(paths["template_pptx"]),
            "profile": profile,
        }

    @app.get("/api/projects/{project_id}/child/status")
    def child_status(project_id: str) -> dict[str, Any]:
        child_id = _resolve_child_id(base_data_dir, project_id)
        paths = _project_paths(base_data_dir, child_id)
        paths["child_exports"].mkdir(parents=True, exist_ok=True)
        exports = [p.name for p in sorted(paths["child_exports"].glob("*.zip"))]
        return {
            "project_id": child_id,
            "child_id": child_id,
            "schema_version": CURRENT_SCHEMA_VERSION,
            "exports_count": len(exports),
            "exports": exports[-20:],
        }

    @app.post("/api/projects/{project_id}/child/export")
    def child_export(project_id: str) -> dict[str, Any]:
        child_id = _resolve_child_id(base_data_dir, project_id)
        paths = _project_paths(base_data_dir, child_id)
        zip_path = export_child_bundle(
            child_id=child_id,
            project_root=paths["root"],
            bundle_out_dir=paths["child_exports"],
            app_version="0.1.0",
        )
        return {"project_id": child_id, "bundle": str(zip_path)}

    @app.post("/api/projects/{project_id}/child/import")
    async def child_import(project_id: str, file: UploadFile = File(...)) -> dict[str, Any]:
        child_id = _resolve_child_id(base_data_dir, project_id)
        paths = _project_paths(base_data_dir, child_id)
        if not (file.filename or "").lower().endswith(".zip"):
            raise HTTPException(status_code=400, detail="CHILD bundle must be a .zip file.")
        payload = await file.read()
        if not payload:
            raise HTTPException(status_code=400, detail="Uploaded bundle is empty.")
        paths["child_dir"].mkdir(parents=True, exist_ok=True)
        temp_zip = paths["child_dir"] / "import_bundle.zip"
        temp_zip.write_bytes(payload)
        result = import_child_bundle(
            bundle_zip=temp_zip,
            project_root=paths["root"],
            snapshots_dir=paths["child_snapshots"],
        )
        temp_zip.unlink(missing_ok=True)
        return result

    @app.post("/api/projects/{project_id}/upload-template")
    async def upload_template(project_id: str, file: UploadFile = File(...)) -> dict[str, Any]:
        child_id = _resolve_child_id(base_data_dir, project_id)
        paths = _project_paths(base_data_dir, child_id)
        if not (file.filename or "").lower().endswith((".ppt", ".pptx")):
            raise HTTPException(status_code=400, detail="Template must be PPT/PPTX.")
        payload = await file.read()
        if not payload:
            raise HTTPException(status_code=400, detail="Uploaded template is empty.")
        paths["template_pptx"].parent.mkdir(parents=True, exist_ok=True)
        paths["template_pptx"].write_bytes(payload)
        profile = extract_template_profile(paths["template_pptx"])
        save_template_profile(paths["template_profile"], profile)
        return {"template_path": str(paths["template_pptx"]), "profile": profile}

    @app.post("/api/projects/{project_id}/upload-context")
    async def upload_context(project_id: str, files: list[UploadFile] = File(...)) -> dict[str, Any]:
        child_id = _resolve_child_id(base_data_dir, project_id)
        paths = _project_paths(base_data_dir, child_id)
        paths["context_dir"].mkdir(parents=True, exist_ok=True)
        saved: list[str] = []
        for up in files:
            payload = await up.read()
            if not payload:
                continue
            fname = Path(up.filename or "file.bin").name
            out_path = paths["context_dir"] / fname
            out_path.write_bytes(payload)
            saved.append(fname)
        return {"saved_files": saved}

    @app.post("/api/projects/{project_id}/ingest-ppts")
    async def ingest_ppts(project_id: str, files: list[UploadFile] = File(...)) -> dict[str, Any]:
        child_id = _resolve_child_id(base_data_dir, project_id)
        paths = _project_paths(base_data_dir, child_id)
        paths["source_dir"].mkdir(parents=True, exist_ok=True)
        registry = load_registry(paths["registry_path"])
        results: list[dict[str, Any]] = []
        newly_saved = 0

        for up in files:
            file_name = Path(up.filename or "").name
            if not file_name.lower().endswith((".ppt", ".pptx")):
                results.append({"file_name": file_name, "status": "unsupported"})
                continue

            payload = await up.read()
            if not payload:
                results.append({"file_name": file_name, "status": "empty"})
                continue

            content_hash = _sha256(payload)
            existing = find_by_hash(registry, content_hash)
            if existing:
                register_ingested_file(
                    registry=registry,
                    file_name=existing["file_name"],
                    stored_path=existing["stored_path"],
                    content_hash=content_hash,
                    status="already_ingested",
                )
                results.append({"file_name": file_name, "status": "already_ingested"})
                continue

            safe_name = f"{content_hash[:8]}_{file_name}"
            out_path = paths["source_dir"] / safe_name
            out_path.write_bytes(payload)
            register_ingested_file(
                registry=registry,
                file_name=file_name,
                stored_path=str(out_path),
                content_hash=content_hash,
                status="ingested",
            )
            newly_saved += 1
            results.append({"file_name": file_name, "status": "ingested"})

        save_registry(paths["registry_path"], registry)

        if newly_saved > 0:
            kb, diagnostics = build_knowledge_base_with_diagnostics(paths["source_dir"])
            save_knowledge_base(kb, paths["kb_path"])
            save_diagnostics(diagnostics, paths["diagnostics_path"])
            if kb.slides:
                build_semantic_index(
                    kb=kb,
                    index_dir=paths["index_dir"],
                    embedding_model="sentence-transformers/all-MiniLM-L6-v2",
                )

        return {
            "project_id": child_id,
            "results": results,
            "newly_ingested": newly_saved,
            "registry_path": str(paths["registry_path"]),
            "kb_path": str(paths["kb_path"]),
        }

    @app.post("/api/projects/{project_id}/chat")
    def chat(project_id: str, payload: ChatRequest) -> dict[str, Any]:
        child_id = _resolve_child_id(base_data_dir, project_id)
        paths = _project_paths(base_data_dir, child_id)
        if not paths["kb_path"].exists():
            raise HTTPException(status_code=400, detail="Knowledge base not found. Ingest PPTs first.")
        response, session_path = handle_chat(
            sessions_dir=paths["sessions_dir"],
            session_id=child_id,
            kb_path=paths["kb_path"],
            index_dir=paths["index_dir"],
            message=payload.message,
            report_type=payload.report_type,
            semantic_top_k=payload.semantic_top_k,
        )
        return {"response": response, "session_path": str(session_path)}

    @app.post("/api/projects/{project_id}/plan")
    def plan(project_id: str, payload: PlanRequest) -> dict[str, Any]:
        child_id = _resolve_child_id(base_data_dir, project_id)
        paths = _project_paths(base_data_dir, child_id)
        if not paths["kb_path"].exists():
            raise HTTPException(status_code=400, detail="Knowledge base not found. Ingest PPTs first.")

        context_files = (
            [p.name for p in sorted(paths["context_dir"].glob("*")) if p.is_file()]
            if paths["context_dir"].exists()
            else []
        )
        context_note = ""
        if context_files:
            context_note = "\nContext files provided: " + ", ".join(context_files)

        kb = load_knowledge_base(paths["kb_path"])
        plan_obj = build_report_plan(
            kb=kb,
            task_name=payload.task_name,
            task_description=payload.task_desc + context_note,
            report_type=payload.report_type,
            semantic_index_dir=paths["index_dir"],
            semantic_top_k=payload.semantic_top_k,
            enable_semantic=payload.use_semantic,
        )

        slug = "".join(c if c.isalnum() else "-" for c in payload.task_name.lower()).strip("-") or "report-plan"
        paths["output_dir"].mkdir(parents=True, exist_ok=True)
        md_path = paths["output_dir"] / f"{slug}.md"
        json_path = paths["output_dir"] / f"{slug}.json"
        pptx_path = paths["output_dir"] / f"{slug}.pptx"
        export_plan_markdown(plan_obj, md_path)
        export_plan_json(plan_obj, json_path)
        profile = load_template_profile(paths["template_profile"])
        export_plan_pptx(
            plan_obj,
            pptx_path,
            template_pptx=paths["template_pptx"] if paths["template_pptx"].exists() else None,
            style_profile=profile,
        )

        return {
            "project_id": child_id,
            "plan": plan_obj.to_dict(),
            "outputs": {
                "markdown": str(md_path),
                "json": str(json_path),
                "pptx": str(pptx_path),
            },
        }

    return app


def run_gui(host: str = "127.0.0.1", port: int = 8000, reload: bool = False) -> None:
    import uvicorn

    uvicorn.run("reporter_agent.gui.app:create_app", factory=True, host=host, port=port, reload=reload)

