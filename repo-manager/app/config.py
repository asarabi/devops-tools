import os
import yaml

CONFIG_PATH = os.environ.get("CONFIG_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml"))


def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {
            "jenkins": {
                "url": os.environ.get("JENKINS_URL", "http://localhost:9090"),
                "job_name": os.environ.get("JENKINS_JOB", "repo-sync-pipeline"),
                "username": os.environ.get("JENKINS_USER", "admin"),
                "api_token": os.environ.get("JENKINS_TOKEN", ""),
            },
            "repo_scope": {
                "url": os.environ.get("REPO_SCOPE_URL", ""),
            },
        }
    try:
        with open(CONFIG_PATH, "r") as f:
            cfg = yaml.safe_load(f) or {}
            cfg.setdefault("jenkins", {
                "url": os.environ.get("JENKINS_URL", "http://localhost:9090"),
                "job_name": os.environ.get("JENKINS_JOB", "repo-sync-pipeline"),
                "username": os.environ.get("JENKINS_USER", "admin"),
                "api_token": os.environ.get("JENKINS_TOKEN", ""),
            })
            cfg.setdefault("repo_scope", {
                "url": os.environ.get("REPO_SCOPE_URL", ""),
            })
            return cfg
    except Exception:
        return {}
