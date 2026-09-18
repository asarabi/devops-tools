import os
import json
import subprocess
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional, Tuple

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
TRACKED_FILE = DATA_DIR / "tracked_services.json"
SYSTEMD_SYSTEM_DIR = Path("/etc/systemd/system")
SYSTEMD_USER_DIR = Path.home() / ".config" / "systemd" / "user"


def run_cmd(args: List[str]) -> Tuple[int, str, str]:
    """Execute command safely and return (returncode, stdout, stderr)"""
    try:
        proc = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except subprocess.TimeoutExpired:
        return 124, "", "Command timed out after 15s"
    except Exception as e:
        return 1, "", str(e)


def load_tracked_services() -> List[Dict]:
    if not TRACKED_FILE.exists():
        return []
    try:
        with open(TRACKED_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_tracked_services(services: List[Dict]):
    with open(TRACKED_FILE, "w", encoding="utf-8") as f:
        json.dump(services, f, indent=2, ensure_ascii=False)


def scan_custom_system_services() -> List[Dict[str, str]]:
    """Scan /etc/systemd/system and ~/.config/systemd/user for real unit files"""
    discovered = []

    # 1. Scan /etc/systemd/system (System services)
    if SYSTEMD_SYSTEM_DIR.exists():
        for item in SYSTEMD_SYSTEM_DIR.glob("*.service"):
            # Real file (not a symlink to /lib/systemd or /usr/lib/systemd)
            if not item.is_symlink():
                discovered.append({"name": item.name, "scope": "system", "category": "System (Custom)"})
            else:
                target = str(item.resolve())
                if not target.startswith("/lib/systemd") and not target.startswith("/usr/lib/systemd"):
                    discovered.append({"name": item.name, "scope": "system", "category": "System (Custom)"})

    # 2. Scan ~/.config/systemd/user (User-level services)
    if SYSTEMD_USER_DIR.exists():
        for item in SYSTEMD_USER_DIR.glob("*.service"):
            discovered.append({"name": item.name, "scope": "user", "category": "User Service"})

    return discovered


def format_bytes(size: int) -> str:
    if size <= 0 or size > 10**15:
        return "-"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def get_service_details(service_name: str) -> Dict:
    """Retrieve detailed properties of a systemd unit"""
    if not service_name.endswith(".service"):
        service_name = f"{service_name}.service"

    props_to_fetch = [
        "Id",
        "Description",
        "LoadState",
        "ActiveState",
        "SubState",
        "UnitFileState",
        "MainPID",
        "MemoryCurrent",
        "ActiveEnterTimestamp",
        "ExecMainStartTimestamp",
        "FragmentPath",
    ]
    cmd = ["systemctl", "show", service_name, f"--property={','.join(props_to_fetch)}"]
    code, out, _ = run_cmd(cmd)

    props = {}
    if code == 0:
        for line in out.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                props[k.strip()] = v.strip()

    active_state = props.get("ActiveState", "unknown")
    sub_state = props.get("SubState", "unknown")
    unit_file_state = props.get("UnitFileState", "unknown")
    load_state = props.get("LoadState", "not-found")

    pid_str = props.get("MainPID", "0")
    pid = int(pid_str) if pid_str.isdigit() else 0

    mem_str = props.get("MemoryCurrent", "0")
    mem_bytes = int(mem_str) if mem_str.isdigit() else 0

    unit_path = props.get("FragmentPath", "")
    if not unit_path and (SYSTEMD_SYSTEM_DIR / service_name).exists():
        unit_path = str(SYSTEMD_SYSTEM_DIR / service_name)

    active_since = props.get("ActiveEnterTimestamp", "")

    return {
        "name": service_name,
        "description": props.get("Description", ""),
        "load_state": load_state,
        "active_state": active_state,
        "sub_state": sub_state,
        "unit_file_state": unit_file_state,
        "pid": pid,
        "memory_formatted": format_bytes(mem_bytes),
        "memory_bytes": mem_bytes,
        "active_since": active_since,
        "unit_path": unit_path,
        "is_running": active_state == "active" and sub_state == "running",
        "is_failed": active_state == "failed" or sub_state == "failed",
        "is_enabled": unit_file_state == "enabled",
    }


def get_all_managed_services() -> List[Dict]:
    """Get list of tracked services merged with auto-discovered custom services"""
    tracked = {s["name"]: s for s in load_tracked_services()}
    custom_units = scan_custom_system_services()

    # Add custom units to tracked if not present
    updated = False
    for item in custom_units:
        unit_name = item["name"]
        if unit_name not in tracked:
            tracked[unit_name] = {
                "name": unit_name,
                "description": "",
                "category": item.get("category", "Custom"),
                "scope": item.get("scope", "system"),
                "tracked_at": datetime.now(timezone.utc).isoformat(),
            }
            updated = True

    if updated:
        save_tracked_services(list(tracked.values()))

    result = []
    for s_meta in tracked.values():
        name = s_meta["name"]
        details = get_service_details(name)
        # Merge metadata
        merged = {**s_meta, **details}
        result.append(merged)

    # Sort: running first, then name
    result.sort(key=lambda x: (0 if x.get("is_running") else 1, x["name"]))
    return result


def control_service(service_name: str, action: str) -> Tuple[bool, str]:
    """Run start, stop, restart, enable, disable on a service"""
    if not service_name.endswith(".service"):
        service_name = f"{service_name}.service"

    allowed_actions = ["start", "stop", "restart", "enable", "disable", "reload"]
    if action not in allowed_actions:
        return False, f"Invalid action '{action}'. Allowed: {', '.join(allowed_actions)}"

    cmd = ["systemctl", action, service_name]
    code, out, err = run_cmd(cmd)

    # If failed due to permissions, try sudo if possible or return helpful message
    if code != 0:
        error_msg = err or out or f"Failed with exit code {code}"
        if "interactive authentication" in error_msg.lower() or "access denied" in error_msg.lower():
            # Try with sudo -n
            sudo_code, s_out, s_err = run_cmd(["sudo", "-n", "systemctl", action, service_name])
            if sudo_code == 0:
                return True, f"Service {service_name} {action}ed successfully via sudo"
            return False, f"권한 부족: 'sudo' 실행 또는 passwordless sudoers 설정이 필요합니다. ({error_msg})"
        return False, error_msg

    return True, f"Service {service_name} {action}ed successfully"


def get_service_logs(service_name: str, lines: int = 100) -> str:
    """Fetch journalctl logs for service"""
    if not service_name.endswith(".service"):
        service_name = f"{service_name}.service"

    cmd = ["journalctl", "-u", service_name, "-n", str(lines), "--no-pager"]
    code, out, err = run_cmd(cmd)
    if code == 0:
        return out if out else "(No log entries found for this service)"
    return f"Error reading logs: {err or out}"


def read_unit_content(service_name: str) -> Tuple[bool, str]:
    """Read .service file content"""
    if not service_name.endswith(".service"):
        service_name = f"{service_name}.service"

    unit_file = SYSTEMD_SYSTEM_DIR / service_name
    if unit_file.exists():
        try:
            with open(unit_file, "r", encoding="utf-8") as f:
                return True, f.read()
        except PermissionError:
            # Try sudo cat
            code, out, err = run_cmd(["sudo", "-n", "cat", str(unit_file)])
            if code == 0:
                return True, out
            return False, f"Permission denied reading {unit_file}"
        except Exception as e:
            return False, str(e)

    # Fallback to systemctl cat
    code, out, err = run_cmd(["systemctl", "cat", service_name])
    if code == 0 and out:
        return True, out
    return False, f"Unit file for {service_name} not found."


def write_unit_file(service_name: str, content: str, enable_now: bool = False, category: str = "Custom") -> Tuple[bool, str]:
    """Write unit file to /etc/systemd/system/ and reload daemon"""
    if not service_name.endswith(".service"):
        service_name = f"{service_name}.service"

    unit_file = SYSTEMD_SYSTEM_DIR / service_name

    # Try direct write
    write_success = False
    try:
        with open(unit_file, "w", encoding="utf-8") as f:
            f.write(content)
        write_success = True
    except PermissionError:
        # Write to temp file then sudo mv
        temp_file = DATA_DIR / f".tmp_{service_name}"
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(content)
        code, _, err = run_cmd(["sudo", "-n", "mv", str(temp_file), str(unit_file)])
        if code == 0:
            run_cmd(["sudo", "-n", "chmod", "644", str(unit_file)])
            write_success = True
        else:
            if temp_file.exists():
                temp_file.unlink()
            return False, f"파일 저장 실패 (권한 필요): {err or 'sudo 권한이 필요합니다'}"

    # Reload systemd
    code, _, err = run_cmd(["systemctl", "daemon-reload"])
    if code != 0:
        run_cmd(["sudo", "-n", "systemctl", "daemon-reload"])

    # Update tracked list
    tracked = load_tracked_services()
    existing = next((s for s in tracked if s["name"] == service_name), None)
    if not existing:
        tracked.append({
            "name": service_name,
            "description": "",
            "category": category,
            "tracked_at": datetime.now(timezone.utc).isoformat(),
        })
        save_tracked_services(tracked)

    if enable_now:
        control_service(service_name, "enable")
        control_service(service_name, "start")

    return True, f"Service unit {service_name} created/updated successfully."


def delete_service_unit(service_name: str) -> Tuple[bool, str]:
    """Stop, disable, remove file, reload daemon, and un-track service"""
    if not service_name.endswith(".service"):
        service_name = f"{service_name}.service"

    # Stop and disable
    control_service(service_name, "stop")
    control_service(service_name, "disable")

    unit_file = SYSTEMD_SYSTEM_DIR / service_name
    if unit_file.exists():
        try:
            unit_file.unlink()
        except PermissionError:
            code, _, err = run_cmd(["sudo", "-n", "rm", "-f", str(unit_file)])
            if code != 0:
                return False, f"파일 삭제 실패: {err}"

    # Reload systemd
    code, _, _ = run_cmd(["systemctl", "daemon-reload"])
    if code != 0:
        run_cmd(["sudo", "-n", "systemctl", "daemon-reload"])

    # Remove from tracked
    tracked = load_tracked_services()
    tracked = [s for s in tracked if s["name"] != service_name]
    save_tracked_services(tracked)

    return True, f"Service {service_name} deleted successfully."


def generate_service_template(
    service_name: str,
    description: str,
    exec_start: str,
    working_dir: str = "",
    user: str = "",
    restart: str = "always",
    env_vars: Optional[List[str]] = None,
) -> str:
    """Generate standard systemd service unit template"""
    lines = [
        "[Unit]",
        f"Description={description or service_name}",
        "After=network.target",
        "",
        "[Service]",
        "Type=simple",
    ]
    if user:
        lines.append(f"User={user}")
    if working_dir:
        lines.append(f"WorkingDirectory={working_dir}")

    if env_vars:
        for env in env_vars:
            if env.strip():
                lines.append(f"Environment={env.strip()}")

    lines.extend([
        f"ExecStart={exec_start}",
        f"Restart={restart}",
        "RestartSec=3",
        "",
        "[Install]",
        "WantedBy=multi-user.target",
        "",
    ])
    return "\n".join(lines)
