import json
import logging
import requests
import paramiko
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models import Source, Repository, Branch, Permission

logger = logging.getLogger(__name__)


def strip_gerrit_prefix(text):
    """Gerrit REST API returns )]}' prefix before JSON."""
    if text.startswith(")]}'"):
        text = text[4:]
    return text.strip()


class GerritSyncHTTP:
    def __init__(self, url, username, password):
        self.url = url.rstrip("/")
        self.auth = (username, password)
        self.session = requests.Session()
        self.session.auth = self.auth

    def get_projects(self):
        projects = {}
        start = 0
        while True:
            resp = self.session.get(
                f"{self.url}/a/projects/",
                params={"d": "", "S": start, "n": 500},
            )
            resp.raise_for_status()
            data = json.loads(strip_gerrit_prefix(resp.text))
            if not data:
                break
            projects.update(data)
            if len(data) < 500:
                break
            start += 500
        return projects

    def get_branches(self, project_name):
        encoded = requests.utils.quote(project_name, safe="")
        resp = self.session.get(f"{self.url}/a/projects/{encoded}/branches/")
        resp.raise_for_status()
        return json.loads(strip_gerrit_prefix(resp.text))

    def get_access(self, project_name):
        encoded = requests.utils.quote(project_name, safe="")
        resp = self.session.get(f"{self.url}/a/projects/{encoded}/access")
        resp.raise_for_status()
        return json.loads(strip_gerrit_prefix(resp.text))


class GerritSyncSSH:
    def __init__(self, url, username, ssh_key, ssh_port=29418):
        self.hostname = url.replace("https://", "").replace("http://", "").split("/")[0]
        self.username = username
        self.ssh_key = ssh_key
        self.ssh_port = ssh_port
        self.http_url = url.rstrip("/")

    def _exec_ssh(self, command):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                self.hostname,
                port=self.ssh_port,
                username=self.username,
                key_filename=self.ssh_key,
            )
            stdin, stdout, stderr = client.exec_command(f"gerrit {command}")
            output = stdout.read().decode()
            error = stderr.read().decode()
            if error and "fatal" in error.lower():
                logger.error(f"SSH error: {error}")
            return output
        finally:
            client.close()

    def get_projects(self):
        output = self._exec_ssh("ls-projects --format json --description")
        if not output.strip():
            return {}
        return json.loads(output)

    def get_branches(self, project_name):
        output = self._exec_ssh(f"ls-projects --format json -b {project_name}")
        if output.strip():
            return json.loads(output)
        # Fallback: parse text output
        output = self._exec_ssh(f"ls-projects -b -p {project_name}")
        branches = []
        for line in output.strip().split("\n"):
            if line.strip():
                branches.append({"ref": line.strip(), "revision": ""})
        return branches

    def get_access(self, project_name):
        # SSH doesn't have a direct access command, use REST fallback
        # Return empty if REST not available
        return {}


def sync_gerrit(db: Session, instance_config: dict):
    name = instance_config["name"]
    url = instance_config["url"]
    auth_type = instance_config.get("auth_type", "http")

    logger.info(f"Syncing Gerrit instance: {name}")

    if auth_type == "ssh":
        client = GerritSyncSSH(
            url,
            instance_config["username"],
            instance_config["ssh_key"],
            instance_config.get("ssh_port", 29418),
        )
    else:
        client = GerritSyncHTTP(
            url, instance_config["username"], instance_config["password"]
        )

    # Upsert source
    source = db.query(Source).filter_by(name=name).first()
    if not source:
        source = Source(name=name, source_type="gerrit", url=url)
        db.add(source)
        db.flush()

    # Clear old data
    db.query(Repository).filter_by(source_id=source.id).delete()
    db.flush()

    # Fetch projects
    projects = client.get_projects()
    for project_name, project_info in projects.items():
        description = ""
        if isinstance(project_info, dict):
            description = project_info.get("description", "")

        repo = Repository(
            source_id=source.id,
            name=project_name,
            description=description or "",
            state=project_info.get("state", "ACTIVE") if isinstance(project_info, dict) else "ACTIVE",
            web_url=f"{url}/admin/repos/{project_name}",
        )
        db.add(repo)
        db.flush()

        # Fetch branches
        try:
            branches = client.get_branches(project_name)
            if isinstance(branches, list):
                for b in branches:
                    ref = b.get("ref", "")
                    branch = Branch(
                        repository_id=repo.id,
                        name=ref.replace("refs/heads/", ""),
                        revision=b.get("revision", "")[:12],
                    )
                    db.add(branch)
        except Exception as e:
            logger.warning(f"Failed to get branches for {project_name}: {e}")

        # Fetch access/permissions
        try:
            access = client.get_access(project_name)
            if access:
                inherits_from = access.get("inherits_from", {})
                if inherits_from:
                    repo.parent_project = inherits_from.get("name", "")

                local_perms = access.get("local", {})
                for ref_pattern, ref_info in local_perms.items():
                    permissions = ref_info.get("permissions", {})
                    for perm_name, perm_info in permissions.items():
                        rules = perm_info.get("rules", {})
                        for group_id, rule_info in rules.items():
                            perm = Permission(
                                repository_id=repo.id,
                                ref_pattern=ref_pattern,
                                permission_name=perm_name,
                                group_name=group_id,
                                action=rule_info.get("action", "ALLOW"),
                            )
                            db.add(perm)
        except Exception as e:
            logger.warning(f"Failed to get access for {project_name}: {e}")

    source.last_synced = datetime.now(timezone.utc)
    db.commit()
    logger.info(f"Gerrit sync complete: {name} ({len(projects)} projects)")
