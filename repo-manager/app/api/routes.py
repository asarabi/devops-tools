from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import get_db, Source, Repository, Branch, Permission
from app.sync.scheduler import run_sync

router = APIRouter(prefix="/api")


@router.get("/sources")
def list_sources(db: Session = Depends(get_db)):
    sources = db.query(Source).all()
    result = []
    for s in sources:
        repo_count = db.query(func.count(Repository.id)).filter_by(source_id=s.id).scalar()
        result.append(
            {
                "id": s.id,
                "name": s.name,
                "source_type": s.source_type,
                "url": s.url,
                "last_synced": s.last_synced.isoformat() if s.last_synced else None,
                "repo_count": repo_count,
            }
        )
    return result


@router.get("/repositories")
def list_repositories(
    source_id: int = None,
    search: str = None,
    state: str = None,
    db: Session = Depends(get_db),
):
    query = db.query(Repository)
    if source_id:
        query = query.filter_by(source_id=source_id)
    if state:
        query = query.filter_by(state=state)
    if search:
        query = query.filter(Repository.name.ilike(f"%{search}%"))
    repos = query.order_by(Repository.name).all()

    result = []
    for r in repos:
        source = db.query(Source).get(r.source_id)
        result.append(
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "state": r.state,
                "source_name": source.name if source else "",
                "source_type": source.source_type if source else "",
                "parent_project": r.parent_project,
                "web_url": r.web_url,
                "default_branch": r.default_branch,
                "branch_count": len(r.branches),
            }
        )
    return result


@router.get("/repositories/{repo_id}")
def get_repository(repo_id: int, db: Session = Depends(get_db)):
    repo = db.query(Repository).get(repo_id)
    if not repo:
        return {"error": "not found"}
    source = db.query(Source).get(repo.source_id)
    return {
        "id": repo.id,
        "name": repo.name,
        "description": repo.description,
        "state": repo.state,
        "source_name": source.name if source else "",
        "source_type": source.source_type if source else "",
        "parent_project": repo.parent_project,
        "web_url": repo.web_url,
        "default_branch": repo.default_branch,
        "branches": [
            {"name": b.name, "revision": b.revision} for b in repo.branches
        ],
        "permissions": [
            {
                "ref_pattern": p.ref_pattern,
                "permission_name": p.permission_name,
                "group_name": p.group_name,
                "action": p.action,
            }
            for p in repo.permissions
        ],
    }


@router.get("/inheritance")
def get_inheritance_tree(source_id: int = None, db: Session = Depends(get_db)):
    """Build Gerrit project inheritance tree."""
    query = db.query(Repository).join(Source).filter(Source.source_type == "gerrit")
    if source_id:
        query = query.filter(Repository.source_id == source_id)
    repos = query.all()

    tree = {}
    for r in repos:
        parent = r.parent_project or "(root)"
        if parent not in tree:
            tree[parent] = []
        tree[parent].append({"id": r.id, "name": r.name, "state": r.state})

    return tree


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    total_repos = db.query(func.count(Repository.id)).scalar()
    total_branches = db.query(func.count(Branch.id)).scalar()
    total_sources = db.query(func.count(Source.id)).scalar()
    gerrit_repos = (
        db.query(func.count(Repository.id))
        .join(Source)
        .filter(Source.source_type == "gerrit")
        .scalar()
    )
    github_repos = (
        db.query(func.count(Repository.id))
        .join(Source)
        .filter(Source.source_type == "github")
        .scalar()
    )
    return {
        "total_sources": total_sources,
        "total_repos": total_repos,
        "total_branches": total_branches,
        "gerrit_repos": gerrit_repos,
        "github_repos": github_repos,
    }


@router.post("/sync")
def trigger_sync():
    try:
        run_sync()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
