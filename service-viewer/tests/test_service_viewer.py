import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from app.main import app
from app.core import systemd

client = TestClient(app)


def test_core_systemd():
    print("\n--- 1. Testing Core systemd functions ---")
    services = systemd.get_all_managed_services()
    print(f"Total managed services discovered: {len(services)}")
    assert isinstance(services, list)

    # Test template generator
    tpl = systemd.generate_service_template(
        service_name="test-app",
        description="Test Application",
        exec_start="/usr/bin/python3 /tmp/app.py",
        working_dir="/tmp",
        user="testuser",
        restart="always",
        env_vars=["PORT=8000", "ENV=test"],
    )
    assert "[Unit]" in tpl
    assert "ExecStart=/usr/bin/python3 /tmp/app.py" in tpl
    assert "User=testuser" in tpl
    assert "Environment=PORT=8000" in tpl
    print("Template generation: OK")

    # Test reading existing service if ollama exists
    ollama_details = systemd.get_service_details("ollama.service")
    print(f"Ollama details: active_state={ollama_details.get('active_state')}, user={ollama_details.get('execution_user')}, pid={ollama_details.get('pid')}")
    assert ollama_details["name"] == "ollama.service"
    assert ollama_details["execution_user"] == "ollama"
    print("Core systemd tests passed!")


def test_api_endpoints():
    print("\n--- 2. Testing API endpoints ---")

    # GET /health
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    print("GET /health: OK")

    # GET /
    res = client.get("/")
    assert res.status_code == 200
    assert "Service Viewer" in res.text
    print("GET /: OK")

    # GET /api/services
    res = client.get("/api/services")
    assert res.status_code == 200
    data = res.json()
    assert "stats" in data
    assert "services" in data
    print(f"GET /api/services: OK (stats: {data['stats']})")

    # POST /api/services/preview
    res = client.post(
        "/api/services/preview",
        json={
            "name": "sample-worker",
            "description": "Sample Worker Service",
            "exec_start": "/usr/bin/python3 run_worker.py",
            "working_directory": "/home/ck21im/worker",
            "user": "ck21im",
            "restart": "always",
            "environment": ["DEBUG=1"],
        },
    )
    assert res.status_code == 200
    content = res.json()["content"]
    assert "ExecStart=/usr/bin/python3 run_worker.py" in content
    print("POST /api/services/preview: OK")

    # GET /api/services/ollama.service
    res = client.get("/api/services/ollama.service")
    assert res.status_code == 200
    data = res.json()
    assert data["details"]["name"] == "ollama.service"
    print("GET /api/services/ollama.service: OK")

    # GET /api/services/ollama.service/logs
    res = client.get("/api/services/ollama.service/logs?lines=5")
    assert res.status_code == 200
    assert "logs" in res.json()
    print("GET /api/services/ollama.service/logs: OK")

    # Test Self-Protection (POST /api/services/service-viewer.service/stop should fail)
    res = client.post("/api/services/service-viewer.service/stop")
    assert res.status_code == 400
    assert "자체 보호" in res.json()["detail"]
    print("POST /api/services/service-viewer.service/stop: BLOCKED (Self-protection OK)")


if __name__ == "__main__":
    test_core_systemd()
    test_api_endpoints()
    print("\n=== ALL SERVICE-VIEWER TESTS PASSED SUCCESSFULLY! ===\n")
