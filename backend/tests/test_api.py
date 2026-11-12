from conftest import TEACHER


def submit(client, student, lab, name, content):
    return client.post(
        "/api/submissions",
        data={"student_id": student["id"], "lab_id": lab["id"]},
        files={"file": (name, content.encode(), "text/plain")},
        headers=TEACHER,
    )


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_docs_served_under_api(client):
    assert client.get("/api/docs").status_code == 200
    assert client.get("/api/openapi.json").status_code == 200


def test_write_endpoints_require_token(client):
    assert client.post("/api/students", json={"full_name": "X"}).status_code == 401
    assert client.post("/api/labs", json={"title": "X", "language": "python"}).status_code == 401
    assert client.patch("/api/submissions/1", json={"status": "accepted"}).status_code == 401


def test_wrong_token_rejected(client):
    r = client.post("/api/students", json={"full_name": "X"}, headers={"X-Teacher-Token": "nope"})
    assert r.status_code == 401


def test_auth_check(client):
    assert client.get("/api/auth/check").status_code == 401
    assert client.get("/api/auth/check", headers=TEACHER).json() == {"teacher": True}


def test_no_token_configured_blocks_writes(client, monkeypatch):
    monkeypatch.setenv("TEACHER_TOKEN", "")
    r = client.post("/api/students", json={"full_name": "X"}, headers={"X-Teacher-Token": ""})
    assert r.status_code == 503


def test_labs_are_public(client, py_lab):
    assert client.get("/api/labs").status_code == 200


def test_teacher_can_change_status(client, student, py_lab):
    sub = submit(client, student, py_lab, "ok.py", 'print("ok")\n').json()
    url = f"/api/submissions/{sub['id']}"
    assert client.patch(url, json={"status": "accepted"}).status_code == 401
    r = client.patch(url, json={"status": "accepted"}, headers=TEACHER)
    assert r.status_code == 200
    assert r.json()["status"] == "accepted"


def test_empty_name_rejected(client):
    r = client.post("/api/students", json={"full_name": ""}, headers=TEACHER)
    assert r.status_code == 422


def test_unknown_lab_and_student(client, student, py_lab):
    r = client.post(
        "/api/submissions",
        data={"student_id": student["id"], "lab_id": 999},
        files={"file": ("a.py", b"x = 1\n")},
        headers=TEACHER,
    )
    assert r.status_code == 404
    r = client.post(
        "/api/submissions",
        data={"student_id": 999, "lab_id": py_lab["id"]},
        files={"file": ("a.py", b"x = 1\n")},
        headers=TEACHER,
    )
    assert r.status_code == 404


def test_upload_size_limit(client, student, py_lab):
    r = submit(client, student, py_lab, "big.py", "#" * 2000)
    assert r.status_code == 413


def test_python_with_issues(client, student, py_lab):
    r = submit(client, student, py_lab, "bad.py", "import os\nx = 1\n")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "needs_revision"
    assert "F401" in body["checker_output"]
    assert "bad.py:1:1" in body["checker_output"]
    assert "/tmp" not in body["checker_output"]


def test_python_clean(client, student, py_lab):
    body = submit(client, student, py_lab, "good.py", 'print("ok")\n').json()
    assert body["status"] == "checked"
    assert body["checker_output"] == "Проблем не найдено."


def test_bash_without_shebang_is_ok(client, student, sh_lab):
    body = submit(client, student, sh_lab, "run.sh", 'echo "hello"\n').json()
    assert body["status"] == "checked", body["checker_output"]


def test_bash_with_issues(client, student, sh_lab):
    body = submit(client, student, sh_lab, "run.sh", "#!/bin/bash\necho $1\n").json()
    assert body["status"] == "needs_revision"
    assert "SC2086" in body["checker_output"]
    assert "/tmp" not in body["checker_output"]


def test_filename_path_is_stripped(client, student, py_lab):
    body = submit(client, student, py_lab, "../../etc/evil.py", "x = 1\n").json()
    assert body["filename"] == "evil.py"


def test_datetimes_are_utc_aware(client, student, py_lab):
    body = submit(client, student, py_lab, "a.py", "x = 1\n").json()
    assert body["created_at"].endswith("Z") or body["created_at"].endswith("+00:00")
    assert client.get("/api/students", headers=TEACHER).json()[0]["created_at"].endswith(("Z", "+00:00"))
