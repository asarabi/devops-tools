from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from ..core import systemd

router = APIRouter(prefix="/api/services", tags=["services"])


class CreateServiceRequest(BaseModel):
    name: str = Field(..., description="Service name (e.g. repo-manager or my-app.service)")
    description: str = Field("", description="Description of the service")
    exec_start: str = Field(..., description="Full command to execute (e.g. /usr/bin/python3 /path/to/app.py)")
    working_directory: Optional[str] = Field("", description="Working directory path")
    user: Optional[str] = Field("", description="Execution user (e.g. ck21im)")
    restart: Optional[str] = Field("always", description="Restart policy (always, on-failure, no)")
    environment: Optional[List[str]] = Field(default_factory=list, description="Environment variables (e.g. PORT=8080)")
    category: Optional[str] = Field("Custom", description="Category for grouping")
    enable_now: Optional[bool] = Field(True, description="Enable and start immediately")
    raw_content: Optional[str] = Field(None, description="Direct raw unit file content if provided")


class UpdateUnitRequest(BaseModel):
    content: str = Field(..., description="Full unit file content")
    restart_after_save: Optional[bool] = Field(True, description="Restart service after saving unit file")


class TemplatePreviewRequest(BaseModel):
    name: str
    description: str = ""
    exec_start: str
    working_directory: Optional[str] = ""
    user: Optional[str] = ""
    restart: Optional[str] = "always"
    environment: Optional[List[str]] = Field(default_factory=list)


@router.get("")
def list_services():
    """Retrieve all tracked & custom systemd services with live status"""
    services = systemd.get_all_managed_services()

    stats = {
        "total": len(services),
        "running": sum(1 for s in services if s.get("is_running")),
        "stopped": sum(1 for s in services if not s.get("is_running") and not s.get("is_failed")),
        "failed": sum(1 for s in services if s.get("is_failed")),
        "enabled": sum(1 for s in services if s.get("is_enabled")),
    }

    return {
        "stats": stats,
        "services": services,
    }


@router.post("/preview")
def preview_template(req: TemplatePreviewRequest):
    """Preview the generated systemd .service file content"""
    content = systemd.generate_service_template(
        service_name=req.name,
        description=req.description,
        exec_start=req.exec_start,
        working_dir=req.working_directory or "",
        user=req.user or "",
        restart=req.restart or "always",
        env_vars=req.environment or [],
    )
    return {"content": content}


@router.post("")
def create_service(req: CreateServiceRequest):
    """Create a new systemd unit file and register it"""
    name = req.name.strip()
    if not name.endswith(".service"):
        name = f"{name}.service"

    if req.raw_content and req.raw_content.strip():
        content = req.raw_content
    else:
        content = systemd.generate_service_template(
            service_name=name,
            description=req.description,
            exec_start=req.exec_start,
            working_dir=req.working_directory or "",
            user=req.user or "",
            restart=req.restart or "always",
            env_vars=req.environment or [],
        )

    ok, msg = systemd.write_unit_file(
        service_name=name,
        content=content,
        enable_now=req.enable_now,
        category=req.category or "Custom",
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    # Fetch newly created details
    details = systemd.get_service_details(name)
    return {"success": True, "message": msg, "service": details}


@router.get("/{name}")
def get_service(name: str):
    """Get service live details and unit file content"""
    details = systemd.get_service_details(name)
    ok, content = systemd.read_unit_content(name)
    return {
        "details": details,
        "unit_content": content if ok else "",
        "can_read_unit": ok,
    }


@router.put("/{name}")
def update_service_unit(name: str, req: UpdateUnitRequest):
    """Update unit file content and reload daemon"""
    ok, msg = systemd.write_unit_file(service_name=name, content=req.content, enable_now=False)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    if req.restart_after_save:
        systemd.control_service(name, "restart")

    details = systemd.get_service_details(name)
    return {"success": True, "message": msg, "service": details}


@router.delete("/{name}")
def delete_service(name: str):
    """Stop, disable, delete unit file and unregister"""
    ok, msg = systemd.delete_service_unit(name)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}


@router.post("/{name}/{action}")
def control_service(name: str, action: str):
    """Control service: start, stop, restart, enable, disable, reload"""
    ok, msg = systemd.control_service(name, action)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    details = systemd.get_service_details(name)
    return {"success": True, "message": msg, "service": details}


@router.get("/{name}/logs")
def get_logs(name: str, lines: int = Query(100, ge=1, le=1000)):
    """Fetch recent journalctl logs for service"""
    logs = systemd.get_service_logs(name, lines=lines)
    return {"name": name, "lines": lines, "logs": logs}
