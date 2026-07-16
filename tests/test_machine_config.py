import json
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

import yaml

from agent.dashboard import make_handler
from agent.machine_config import delete_machine, list_machines, save_machine


def config_file(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("agent:\n  service_name: test\nmachines: []\n", encoding="utf-8")
    return path


def test_machine_crud_masks_password(tmp_path):
    path = config_file(tmp_path)
    saved = save_machine(path, {
        "name": "server one", "ip_address": "10.1.2.3", "username": "monitor",
        "password": "secret", "port": 22, "enabled": True,
    })

    assert saved["password_configured"] is True
    assert "password" not in saved
    assert "password" not in list_machines(path)[0]
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["machines"][0]["password"] == "secret"
    assert delete_machine(path, saved["id"]) is True
    assert list_machines(path) == []


def test_updating_without_password_keeps_existing_password(tmp_path):
    path = config_file(tmp_path)
    saved = save_machine(path, {"ip_address": "10.1.2.3", "username": "a", "password": "secret"})
    save_machine(path, {"ip_address": "10.1.2.4", "username": "b", "password": ""}, saved["id"])

    assert yaml.safe_load(path.read_text(encoding="utf-8"))["machines"][0]["password"] == "secret"


def test_machine_api_creates_and_lists_target(tmp_path):
    path = config_file(tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(tmp_path, path))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        connection = HTTPConnection("127.0.0.1", server.server_port)
        body = json.dumps({"ip_address": "127.0.0.1", "username": "agent", "password": "pw"})
        connection.request("POST", "/api/machines", body, {"Content-Type": "application/json"})
        response = connection.getresponse()
        assert response.status == 201
        assert "password" not in json.loads(response.read())
        connection.request("GET", "/api/machines")
        response = connection.getresponse()
        assert json.loads(response.read())[0]["ip_address"] == "127.0.0.1"
    finally:
        server.shutdown()
        server.server_close()
