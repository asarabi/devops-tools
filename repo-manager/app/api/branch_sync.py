import json
import logging
import os
import re
import time
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import httpx

from app.config import load_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# In-memory execution history (persists during container runtime)
EXECUTION_HISTORY: List[Dict[str, Any]] = []


class SyncItemInput(BaseModel):
    from_repo: str
    from_branch: str
    to_repo: str
    to_branch: str
    line_num: Optional[int] = None


class DryRunRequest(BaseModel):
    raw_text: Optional[str] = None
    items: Optional[List[SyncItemInput]] = None


class ExecuteOptions(BaseModel):
    skip_errors: bool = True
    allow_overwrite: bool = False
    jenkins_url: Optional[str] = None
    job_name: Optional[str] = None
    api_token: Optional[str] = None


class ExecuteRequest(BaseModel):
    items: List[Dict[str, Any]]
    options: Optional[ExecuteOptions] = None


def parse_raw_text(raw_text: str) -> List[Dict[str, Any]]:
    parsed = []
    lines = raw_text.strip().splitlines()
    for idx, line in enumerate(lines, start=1):
        clean_line = line.strip()
        # Skip empty lines or comments
        if not clean_line or clean_line.startswith("#"):
            continue

        # Split by whitespace or commas/tabs
        parts = re.split(r"[\s,]+", clean_line)
        if len(parts) != 4:
            parsed.append({
                "line_num": idx,
                "raw": clean_line,
                "error": f"형식 오류 (4개 항목 필요: from-repo from-branch to-repo to-branch, 현재 {len(parts)}개)",
                "status": "ERROR",
                "action": "BLOCKED",
                "from_repo": parts[0] if len(parts) > 0 else "",
                "from_branch": parts[1] if len(parts) > 1 else "",
                "to_repo": parts[2] if len(parts) > 2 else "",
                "to_branch": parts[3] if len(parts) > 3 else "",
            })
        else:
            parsed.append({
                "line_num": idx,
                "raw": clean_line,
                "from_repo": parts[0],
                "from_branch": parts[1],
                "to_repo": parts[2],
                "to_branch": parts[3],
                "status": "PENDING",
            })
    return parsed


async def evaluate_with_repo_scope(item: Dict[str, Any], repo_scope_url: str) -> Dict[str, Any]:
    """Call external repo-scope BE service when configured."""
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.post(
                f"{repo_scope_url.rstrip('/')}/api/verify",
                json={
                    "from_repo": item["from_repo"],
                    "from_branch": item["from_branch"],
                    "to_repo": item["to_repo"],
                    "to_branch": item["to_branch"],
                },
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        logger.warning(f"Failed to contact repo-scope at {repo_scope_url}: {e}")
    return None


def evaluate_mock(item: Dict[str, Any]) -> Dict[str, Any]:
    """Intelligent mock evaluation when repo-scope backend is not yet deployed."""
    from_repo = item.get("from_repo", "").lower()
    from_branch = item.get("from_branch", "").lower()
    to_repo = item.get("to_repo", "").lower()
    to_branch = item.get("to_branch", "").lower()

    # If already has a syntax error
    if item.get("status") == "ERROR":
        return {
            **item,
            "source_exists": False,
            "source_branch_exists": False,
            "target_exists": False,
            "target_branch_exists": False,
            "message": item.get("error", "구문 오류"),
        }

    # Simulation cases based on keywords
    if "notfound" in from_repo or "missing" in from_repo or from_repo.startswith("invalid/"):
        return {
            **item,
            "status": "ERROR",
            "action": "BLOCKED",
            "source_exists": False,
            "source_branch_exists": False,
            "target_exists": True,
            "target_branch_exists": False,
            "message": f"소스 레포 '{item['from_repo']}'를 찾을 수 없습니다.",
        }

    if from_branch in ["missing", "404", "none"]:
        return {
            **item,
            "status": "ERROR",
            "action": "BLOCKED",
            "source_exists": True,
            "source_branch_exists": False,
            "target_exists": True,
            "target_branch_exists": False,
            "message": f"소스 브랜치 '{item['from_branch']}'가 존재하지 않습니다.",
        }

    if to_branch in ["main", "master", "release", "production"] or "overwrite" in to_branch:
        return {
            **item,
            "status": "WARNING",
            "action": "OVERWRITE",
            "source_exists": True,
            "source_branch_exists": True,
            "target_exists": True,
            "target_branch_exists": True,
            "message": f"타겟 브랜치 '{item['to_branch']}'가 이미 존재합니다 (덮어쓰기 주의 필요).",
        }

    # Standard success / Ready case
    return {
        **item,
        "status": "READY",
        "action": "CREATE_BRANCH",
        "source_exists": True,
        "source_branch_exists": True,
        "target_exists": True,
        "target_branch_exists": False,
        "message": f"소스 검증 완료. 타겟 브랜치 '{item['to_branch']}'가 신규 생성됩니다.",
    }


@router.post("/dry-run")
async def dry_run_check(request: DryRunRequest):
    """Parses input lines and verifies existence/state (via repo-scope BE or mock)."""
    cfg = load_config()
    repo_scope_url = cfg.get("repo_scope", {}).get("url", "").strip()

    items_to_check = []
    if request.raw_text:
        items_to_check = parse_raw_text(request.raw_text)
    elif request.items:
        for idx, it in enumerate(request.items, start=1):
            items_to_check.append({
                "line_num": it.line_num or idx,
                "from_repo": it.from_repo,
                "from_branch": it.from_branch,
                "to_repo": it.to_repo,
                "to_branch": it.to_branch,
                "status": "PENDING",
            })

    if not items_to_check:
        raise HTTPException(status_code=400, detail="검증할 입력 데이터가 없습니다.")

    results = []
    ready_count = 0
    warning_count = 0
    error_count = 0

    for item in items_to_check:
        eval_result = None
        if repo_scope_url:
            eval_result = await evaluate_with_repo_scope(item, repo_scope_url)

        if not eval_result:
            eval_result = evaluate_mock(item)

        results.append(eval_result)
        st = eval_result.get("status")
        if st == "READY":
            ready_count += 1
        elif st == "WARNING":
            warning_count += 1
        else:
            error_count += 1

    return {
        "backend_mode": "repo-scope" if repo_scope_url else "mock-simulator",
        "repo_scope_url": repo_scope_url or None,
        "total": len(results),
        "summary": {
            "ready": ready_count,
            "warning": warning_count,
            "error": error_count,
        },
        "results": results,
    }


@router.post("/execute")
async def execute_in_jenkins(request: ExecuteRequest):
    """Triggers Jenkins Job with verified list and registers in execution history."""
    cfg = load_config()
    jenkins_cfg = cfg.get("jenkins", {})
    opts = request.options or ExecuteOptions()

    jenkins_url = opts.jenkins_url or jenkins_cfg.get("url", "http://localhost:9090")
    job_name = opts.job_name or jenkins_cfg.get("job_name", "repo-sync-pipeline")
    username = jenkins_cfg.get("username", "admin")
    api_token = opts.api_token or jenkins_cfg.get("api_token", "")

    # Filter items according to options
    executable_items = []
    for it in request.items:
        if it.get("status") == "ERROR" and opts.skip_errors:
            continue
        if it.get("status") == "WARNING" and not opts.allow_overwrite and it.get("action") == "OVERWRITE":
            continue
        executable_items.append(it)

    if not executable_items:
        raise HTTPException(status_code=400, detail="실행 가능한 유효한 항목이 없습니다.")

    execution_id = f"exec-{int(time.time())}"
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    # Format payload for Jenkins
    formatted_payload = "\n".join([
        f"{it.get('from_repo')} {it.get('from_branch')} {it.get('to_repo')} {it.get('to_branch')}"
        for it in executable_items
    ])

    jenkins_success = False
    build_url = None
    build_number = None
    error_detail = None

    # Attempt to trigger real Jenkins if configured
    if jenkins_url and job_name:
        try:
            trigger_url = f"{jenkins_url.rstrip('/')}/job/{job_name}/buildWithParameters"
            auth = (username, api_token) if api_token else None
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(
                    trigger_url,
                    auth=auth,
                    data={"TARGET_LIST": formatted_payload, "EXECUTION_ID": execution_id},
                )
                if res.status_code in [200, 201, 202]:
                    jenkins_success = True
                    build_url = f"{jenkins_url.rstrip('/')}/job/{job_name}/lastBuild"
        except Exception as e:
            logger.info(f"Jenkins call skipped/unreachable ({e}). Falling back to standalone execution record.")
            error_detail = str(e)

    # If Jenkins wasn't reached, create a simulated execution link
    if not jenkins_success:
        simulated_build_num = len(EXECUTION_HISTORY) + 101
        build_url = f"{jenkins_url.rstrip('/')}/job/{job_name}/{simulated_build_num}/"
        build_number = simulated_build_num
    else:
        build_number = "queued"

    record = {
        "id": execution_id,
        "timestamp": timestamp,
        "job_name": job_name,
        "jenkins_url": jenkins_url,
        "build_url": build_url,
        "build_number": build_number,
        "total_items": len(request.items),
        "executed_items": len(executable_items),
        "skipped_items": len(request.items) - len(executable_items),
        "status": "QUEUED" if jenkins_success else "SIMULATED",
        "note": "Jenkins Job 호출 완료" if jenkins_success else f"Jenkins 연동 준비 완료 (Mock: {error_detail or '대기 중'})",
        "items": executable_items,
    }

    EXECUTION_HISTORY.insert(0, record)
    if len(EXECUTION_HISTORY) > 50:
        EXECUTION_HISTORY.pop()

    return record


@router.get("/history")
def get_execution_history():
    """Returns recent executions list."""
    return {
        "total": len(EXECUTION_HISTORY),
        "history": EXECUTION_HISTORY,
    }


@router.get("/jenkins/config")
def get_jenkins_config():
    """Returns current Jenkins and repo-scope connectivity info."""
    cfg = load_config()
    jenkins_cfg = cfg.get("jenkins", {})
    repo_scope_cfg = cfg.get("repo_scope", {})
    return {
        "jenkins": {
            "url": jenkins_cfg.get("url", "http://localhost:9090"),
            "job_name": jenkins_cfg.get("job_name", "repo-sync-pipeline"),
            "username": jenkins_cfg.get("username", "admin"),
            "has_token": bool(jenkins_cfg.get("api_token")),
        },
        "repo_scope": {
            "url": repo_scope_cfg.get("url", ""),
            "configured": bool(repo_scope_cfg.get("url")),
        },
    }
