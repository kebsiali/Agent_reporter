from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ..chat import handle_chat
from ..exporter import export_plan_json, export_plan_markdown, export_plan_pptx
from ..indexer import build_knowledge_base_with_diagnostics, load_knowledge_base, save_diagnostics, save_knowledge_base
from ..planner import build_report_plan
from ..retrieval import build_semantic_index
from ..storage import find_by_hash, list_ingested_ppts, load_registry, register_ingested_file, save_registry
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


def _validate_project_id(project_id: str) -> str:
    if not VALID_PROJECT.fullmatch(project_id):
        raise HTTPException(status_code=400, detail="Invalid project_id. Use letters/numbers/_/- only.")
    return project_id


def _project_paths(base_data_dir: Path, project_id: str) -> dict[str, Path]:
    pid = _validate_project_id(project_id)
    root = base_data_dir / "gui_projects" / pid
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
        return {"status": "ok"}

    @app.get("/api/projects/{project_id}/ingested")
    def get_ingested(project_id: str) -> dict[str, Any]:
        paths = _project_paths(base_data_dir, project_id)
        registry = load_registry(paths["registry_path"])
        return {"project_id": project_id, "files": list_ingested_ppts(registry)}

    @app.get("/api/projects/{project_id}/context-files")
    def get_context_files(project_id: str) -> dict[str, Any]:
        paths = _project_paths(base_data_dir, project_id)
        paths["context_dir"].mkdir(parents=True, exist_ok=True)
        files = [p.name for p in sorted(paths["context_dir"].glob("*")) if p.is_file()]
        return {"project_id": project_id, "files": files}

    @app.get("/api/projects/{project_id}/template")
    def get_template(project_id: str) -> dict[str, Any]:
        paths = _project_paths(base_data_dir, project_id)
        profile = load_template_profile(paths["template_profile"])
        return {
            "project_id": project_id,
            "template_exists": paths["template_pptx"].exists(),
            "template_path": str(paths["template_pptx"]),
            "profile": profile,
        }

    @app.post("/api/projects/{project_id}/upload-template")
    async def upload_template(project_id: str, file: UploadFile = File(...)) -> dict[str, Any]:
        paths = _project_paths(base_data_dir, project_id)
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
        paths = _project_paths(base_data_dir, project_id)
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
        paths = _project_paths(base_data_dir, project_id)
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
                build_semantic_index(kb=kb, index_dir=paths["index_dir"], embedding_model="sentence-transformers/all-MiniLM-L6-v2")

        return {
            "project_id": project_id,
            "results": results,
            "newly_ingested": newly_saved,
            "registry_path": str(paths["registry_path"]),
            "kb_path": str(paths["kb_path"]),
        }

    @app.post("/api/projects/{project_id}/chat")
    def chat(project_id: str, payload: ChatRequest) -> dict[str, Any]:
        paths = _project_paths(base_data_dir, project_id)
        if not paths["kb_path"].exists():
            raise HTTPException(status_code=400, detail="Knowledge base not found. Ingest PPTs first.")
        response, session_path = handle_chat(
            sessions_dir=paths["sessions_dir"],
            session_id=project_id,
            kb_path=paths["kb_path"],
            index_dir=paths["index_dir"],
            message=payload.message,
            report_type=payload.report_type,
            semantic_top_k=payload.semantic_top_k,
        )
        return {"response": response, "session_path": str(session_path)}

    @app.post("/api/projects/{project_id}/plan")
    def plan(project_id: str, payload: PlanRequest) -> dict[str, Any]:
        paths = _project_paths(base_data_dir, project_id)
        if not paths["kb_path"].exists():
            raise HTTPException(status_code=400, detail="Knowledge base not found. Ingest PPTs first.")

        context_files = [p.name for p in sorted(paths["context_dir"].glob("*")) if p.is_file()] if paths["context_dir"].exists() else []
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
            "project_id": project_id,
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
