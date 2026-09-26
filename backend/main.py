"""
FastAPI Main Application
Connects all system modules and serves the web interface.
"""

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pathlib import Path
from typing import List, Dict, Any, Optional
import os
import json

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from backend.path_controller import PathController, PathSecurityException
from backend.scanner import FileScanner
from backend.extractors.metadata_extractor import MetadataExtractor
from backend.extractors.content_extractor import ContentExtractor
from backend.duplicate_detector import DuplicateDetector
from backend.unnecessary_detector import UnnecessaryDetector
from backend.ai_analyzer import AIAnalyzer
from backend.organization_engine import OrganizationEngine
from backend.database import Database

# Initialize core services
app = FastAPI(title="AI File Manager API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

path_controller = PathController()
database = Database()
org_engine = OrganizationEngine(path_controller, database)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


# Pydantic request models
class ScanRequest(BaseModel):
    path: str
    recursive: bool = False


class AnalyzeRequest(BaseModel):
    files: List[Dict[str, Any]]
    custom_instructions: Optional[str] = None
    api_provider: Optional[str] = "gemini"
    api_key: Optional[str] = None
    max_depth: Optional[int] = None


class ExecuteRequest(BaseModel):
    operations: List[Dict[str, Any]]


class UndoRequest(BaseModel):
    operation_id: int


class SettingsRequest(BaseModel):
    gemini_key: Optional[str] = None
    openai_key: Optional[str] = None
    default_provider: Optional[str] = "offline"
    max_phash_distance: Optional[int] = 4
    max_depth: Optional[int] = 1


# API Endpoints
@app.post("/api/scan")
async def scan_folder(req: ScanRequest):
    try:
        validated_root = path_controller.set_allowed_root(req.path)
    except PathSecurityException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    scanner = FileScanner(validated_root)
    files = scanner.scan(recursive=req.recursive)

    # Detect duplicates
    duplicates_info = DuplicateDetector.find_duplicates(files)

    # Detect unnecessary/temp/backup files
    unnecessary_files = UnnecessaryDetector.scan_for_unnecessary(files)

    return {
        "success": True,
        "root_path": str(validated_root),
        "total_files": len(files),
        "files": files,
        "duplicates": duplicates_info,
        "unnecessary": unnecessary_files,
    }


@app.post("/api/analyze")
async def analyze_files(req: AnalyzeRequest):
    if not path_controller.allowed_root:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No directory currently selected.")

    # Retrieve stored API keys if not supplied in request
    provider = req.api_provider or database.get_setting("default_provider") or os.getenv("DEFAULT_AI_PROVIDER", "offline")
    api_key = req.api_key
    if not api_key:
        if provider == "gemini":
            api_key = database.get_setting("gemini_key") or os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_KEY") or os.getenv("AI_API_KEY")
        elif provider == "openai":
            api_key = database.get_setting("openai_key") or os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY") or os.getenv("AI_API_KEY")

    max_depth = req.max_depth
    if max_depth is None and database.get_setting("max_depth"):
        try:
            max_depth = int(database.get_setting("max_depth"))
        except (ValueError, TypeError):
            max_depth = None
    ai = AIAnalyzer(api_provider=provider, api_key=api_key)
    proposed_operations = []

    for file_info in req.files:
        path_str = file_info.get("full_path")
        if not path_str or not Path(path_str).exists():
            continue

        try:
            # Extract Level 1 metadata & Level 2 content
            metadata = MetadataExtractor.extract(path_str)
            content = ContentExtractor.extract_content(path_str)

            # AI Analysis
            analysis = ai.analyze_file(
                file_info=file_info,
                metadata=metadata,
                content=content,
                custom_instructions=req.custom_instructions,
                max_depth=max_depth
            )

            # Build proposed operation
            op = org_engine.plan_operation(
                original_path=path_str,
                suggested_name=analysis.get("suggested_name"),
                suggested_folder=analysis.get("suggested_folder"),
                action_type="organize",
                ai_suggestion=f"{analysis.get('suggested_folder')}/{analysis.get('suggested_name')}",
                ai_reasoning=analysis.get("reasoning"),
            )
            op["category"] = analysis.get("category")
            op["suggested_name"] = op.get("suggested_name") or op.get("target_name") or analysis.get("suggested_name")
            op["suggested_folder"] = op.get("suggested_folder") or op.get("target_folder") or analysis.get("suggested_folder")
            op["confidence"] = analysis.get("confidence", 0.8)
            op["engine"] = analysis.get("engine", "local")
            op["thumbnail_b64"] = content.get("thumbnail_b64")
            op["metadata"] = metadata
            proposed_operations.append(op)

        except Exception as e:
            # Fallback entry on per-file processing error
            proposed_operations.append({
                "id": file_info.get("name"),
                "original_path": path_str,
                "original_name": file_info.get("name"),
                "error": str(e),
                "approved": False,
            })

    return {
        "success": True,
        "proposed_operations": proposed_operations,
        "custom_instructions_applied": req.custom_instructions,
    }


@app.post("/api/analyze/stream")
async def analyze_files_stream(req: AnalyzeRequest):
    if not path_controller.allowed_root:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No directory currently selected.")

    provider = req.api_provider or database.get_setting("default_provider") or os.getenv("DEFAULT_AI_PROVIDER", "offline")
    api_key = req.api_key
    if not api_key:
        if provider == "gemini":
            api_key = database.get_setting("gemini_key") or os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_KEY") or os.getenv("AI_API_KEY")
        elif provider == "openai":
            api_key = database.get_setting("openai_key") or os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY") or os.getenv("AI_API_KEY")

    max_depth = req.max_depth
    if max_depth is None and database.get_setting("max_depth"):
        try:
            max_depth = int(database.get_setting("max_depth"))
        except (ValueError, TypeError):
            max_depth = None
    ai = AIAnalyzer(api_provider=provider, api_key=api_key)

    async def event_generator():
        total = len(req.files)
        yield f"data: {json.dumps({'type': 'start', 'total': total})}\n\n"

        for idx, file_info in enumerate(req.files, 1):
            path_str = file_info.get("full_path")
            if not path_str or not Path(path_str).exists():
                continue

            try:
                metadata = MetadataExtractor.extract(path_str)
                content = ContentExtractor.extract_content(path_str)

                analysis = ai.analyze_file(
                    file_info=file_info,
                    metadata=metadata,
                    content=content,
                    custom_instructions=req.custom_instructions,
                    max_depth=max_depth
                )

                op = org_engine.plan_operation(
                    original_path=path_str,
                    suggested_name=analysis.get("suggested_name"),
                    suggested_folder=analysis.get("suggested_folder"),
                    action_type="organize",
                    ai_suggestion=f"{analysis.get('suggested_folder')}/{analysis.get('suggested_name')}",
                    ai_reasoning=analysis.get("reasoning"),
                )
                op["category"] = analysis.get("category")
                op["suggested_name"] = op.get("suggested_name") or op.get("target_name") or analysis.get("suggested_name")
                op["suggested_folder"] = op.get("suggested_folder") or op.get("target_folder") or analysis.get("suggested_folder")
                op["confidence"] = analysis.get("confidence", 0.8)
                op["engine"] = analysis.get("engine", "local")
                op["thumbnail_b64"] = content.get("thumbnail_b64")
                op["metadata"] = metadata

                msg = {
                    "type": "progress",
                    "current": idx,
                    "total": total,
                    "filename": file_info.get("name"),
                    "category": file_info.get("category", "General"),
                    "operation": op,
                }
                yield f"data: {json.dumps(msg)}\n\n"
            except Exception as e:
                err_op = {
                    "id": file_info.get("name"),
                    "original_path": path_str,
                    "original_name": file_info.get("name"),
                    "error": str(e),
                    "approved": False,
                }
                msg = {
                    "type": "progress",
                    "current": idx,
                    "total": total,
                    "filename": file_info.get("name"),
                    "category": file_info.get("category", "General"),
                    "operation": err_op,
                }
                yield f"data: {json.dumps(msg)}\n\n"

        yield f"data: {json.dumps({'type': 'complete', 'total': total})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/api/execute")
async def execute_operations(req: ExecuteRequest):
    if not path_controller.allowed_root:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No directory currently selected.")

    res = org_engine.execute_batch(req.operations)
    return {
        "success": True,
        "batch_id": res["batch_id"],
        "executed_count": res["executed_count"],
        "failed_count": res["failed_count"],
        "results": res["results"],
    }


@app.post("/api/undo")
async def undo_operation(req: UndoRequest):
    try:
        res = org_engine.undo_operation(req.operation_id)
        return res
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.get("/api/history")
async def get_history(limit: int = 100):
    rows = database.get_history(limit)
    return {"success": True, "history": rows}


@app.get("/api/preview")
async def preview_file(path: str = Query(..., description="Full path to file")):
    try:
        validated_p = path_controller.validate_path(path)
    except PathSecurityException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    if not validated_p.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File does not exist.")

    metadata = MetadataExtractor.extract(validated_p)
    content = ContentExtractor.extract_content(validated_p)

    return {
        "file_name": validated_p.name,
        "size_bytes": validated_p.stat().st_size,
        "metadata": metadata,
        "content_type": content.get("content_type"),
        "text_sample": content.get("text_sample"),
        "key_details": content.get("key_details"),
        "thumbnail_b64": content.get("thumbnail_b64"),
    }


@app.get("/api/settings")
async def get_settings():
    settings = database.get_all_settings()
    if "gemini_key" not in settings and os.getenv("GEMINI_API_KEY"):
        settings["gemini_key"] = os.getenv("GEMINI_API_KEY")
    if "openai_key" not in settings and os.getenv("OPENAI_API_KEY"):
        settings["openai_key"] = os.getenv("OPENAI_API_KEY")
    if "default_provider" not in settings and os.getenv("DEFAULT_AI_PROVIDER"):
        settings["default_provider"] = os.getenv("DEFAULT_AI_PROVIDER")
    if "max_depth" not in settings:
        settings["max_depth"] = "1"
    return {
        "success": True,
        "settings": settings,
    }


@app.post("/api/settings")
async def update_settings(req: SettingsRequest):
    if req.gemini_key is not None:
        database.set_setting("gemini_key", req.gemini_key)
    if req.openai_key is not None:
        database.set_setting("openai_key", req.openai_key)
    if req.default_provider is not None:
        database.set_setting("default_provider", req.default_provider)
    if req.max_phash_distance is not None:
        database.set_setting("max_phash_distance", str(req.max_phash_distance))
    if req.max_depth is not None:
        database.set_setting("max_depth", str(req.max_depth))

    return {"success": True, "message": "Settings updated successfully."}


# Serve Frontend Assets and Single Page App
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

