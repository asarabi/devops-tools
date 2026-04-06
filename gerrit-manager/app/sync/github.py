import logging
import requests
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models import Source, Repository, Branch

logger = logging.getLogger(__name__)


class GitHubSync:
    def __init__(self, url, token):
        self.url = url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
            }
        )

    def get_org_repos(self, org):
        repos = []
        page = 1
        while True:
            resp = self.session.get(
                f"{self.url}/orgs/{org}/repos",
                params={"per_page": 100, "page": page},
            )
            resp.raise_for_status()
            data = resp.json()
            if not data:
                break
            repos.extend(data)
            page += 1
        return repos

    def get_user_repos(self):
        repos = []
        page = 1
        while True:
            resp = self.session.get(
                f"{self.url}/user/repos",
                params={"per_page": 100, "page": page, "affiliation": "owner"},
            )
            resp.raise_for_status()
            data = resp.json()
            if not data:
                break
            repos.extend(data)
            page += 1
        return repos

    def get_branches(self, owner, repo_name):
        branches = []
        page = 1
        while True:
            resp = self.session.get(
                f"{self.url}/repos/{owner}/{repo_name}/branches",
                params={"per_page": 100, "page": page},
            )
            resp.raise_for_status()
            data = resp.json()
            if not data:
                break
            branches.extend(data)
            page += 1
        return branches


def sync_github(db: Session, instance_config: dict):
    name = instance_config["name"]
    url = instance_config.get("url", "https://api.github.com")
    token = instance_config["token"]
    orgs = instance_config.get("orgs", [])
    include_user_repos = instance_config.get("include_user_repos", False)

    logger.info(f"Syncing GitHub instance: {name}")

    client = GitHubSync(url, token)

    # Upsert source
    source = db.query(Source).filter_by(name=name).first()
    if not source:
        source = Source(name=name, source_type="github", url=url)
        db.add(source)
        db.flush()

    # Clear old data
    db.query(Repository).filter_by(source_id=source.id).delete()
    db.flush()

    all_repos = []

    # Fetch org repos
    for org in orgs:
        try:
            repos = client.get_org_repos(org)
            for r in repos:
                r["_org"] = org
            all_repos.extend(repos)
        except Exception as e:
            logger.error(f"Failed to fetch repos for org {org}: {e}")

    # Fetch user repos
    if include_user_repos:
        try:
            all_repos.extend(client.get_user_repos())
        except Exception as e:
            logger.error(f"Failed to fetch user repos: {e}")

    for r in all_repos:
        full_name = r.get("full_name", r.get("name", ""))
        repo = Repository(
            source_id=source.id,
            name=full_name,
            description=r.get("description") or "",
            state="ARCHIVED" if r.get("archived") else "ACTIVE",
            web_url=r.get("html_url", ""),
            default_branch=r.get("default_branch", "main"),
        )
        db.add(repo)
        db.flush()

        # Fetch branches
        try:
            owner = full_name.split("/")[0] if "/" in full_name else ""
            repo_name = full_name.split("/")[1] if "/" in full_name else full_name
            branches = client.get_branches(owner, repo_name)
            for b in branches:
                branch = Branch(
                    repository_id=repo.id,
                    name=b.get("name", ""),
                    revision=b.get("commit", {}).get("sha", "")[:12],
                )
                db.add(branch)
        except Exception as e:
            logger.warning(f"Failed to get branches for {full_name}: {e}")

    source.last_synced = datetime.now(timezone.utc)
    db.commit()
    logger.info(f"GitHub sync complete: {name} ({len(all_repos)} repos)")
