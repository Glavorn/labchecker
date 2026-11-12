from conftest import TEACHER


def make_student(client, name="Петров Пётр"):
    r = client.post("/api/students", json={"full_name": name}, headers=TEACHER)
    assert r.status_code == 200
    return r.json()


def as_student(key):
    return {"X-Student-Key": key}


def submit(client, headers, lab, name, content, student_id=None):
    data = {"lab_id": lab["id"]}
    if student_id is not None:
        data["student_id"] = student_id
    return client.post(
        "/api/submissions",
        data=data,
        files={"file": (name, content.encode(), "text/plain")},
        headers=headers,
    )


def test_create_student_returns_invite(client):
    s = make_student(client)
    assert len(s["invite_key"]) >= 40
    listed = client.get("/api/students", headers=TEACHER).json()[0]
    assert "invite_key" not in listed and "invite_key_hash" not in listed


def test_me_requires_key(client):
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/me", headers=as_student("garbage")).status_code == 401


def test_me_returns_profile(client):
    s = make_student(client)
    me = client.get("/api/me", headers=as_student(s["invite_key"])).json()
    assert me["id"] == s["id"]
    assert me["full_name"] == "Петров Пётр"


def test_regenerated_key_invalidates_old(client):
    s = make_student(client)
    old = s["invite_key"]
    r = client.post(f"/api/students/{s['id']}/invite")
    assert r.status_code == 401
    new = client.post(f"/api/students/{s['id']}/invite", headers=TEACHER).json()["invite_key"]
    assert new != old
    assert client.get("/api/me", headers=as_student(old)).status_code == 401
    assert client.get("/api/me", headers=as_student(new)).status_code == 200


def test_invite_unknown_student(client):
    assert client.post("/api/students/999/invite", headers=TEACHER).status_code == 404


def test_lists_require_teacher(client, student):
    assert client.get("/api/students").status_code == 401
    assert client.get("/api/submissions").status_code == 401
    assert client.get("/api/students", headers=TEACHER).status_code == 200
    assert client.get("/api/submissions", headers=TEACHER).status_code == 200


def test_labs_visible_to_student(client, py_lab):
    s = make_student(client)
    labs = client.get("/api/labs", headers=as_student(s["invite_key"])).json()
    assert [lab["id"] for lab in labs] == [py_lab["id"]]


def test_student_submits_as_self(client, py_lab):
    me = make_student(client, "Я")
    other = make_student(client, "Другой")
    r = submit(client, as_student(me["invite_key"]), py_lab, "a.py", "x = 1\n", student_id=other["id"])
    assert r.status_code == 200
    assert r.json()["student_id"] == me["id"]


def test_anonymous_cannot_submit(client, student, py_lab):
    r = submit(client, {}, py_lab, "a.py", "x = 1\n", student_id=student["id"])
    assert r.status_code == 401


def test_teacher_submits_for_student(client, student, py_lab):
    r = submit(client, TEACHER, py_lab, "a.py", "x = 1\n", student_id=student["id"])
    assert r.status_code == 200
    assert r.json()["student_id"] == student["id"]
    assert submit(client, TEACHER, py_lab, "a.py", "x = 1\n").status_code == 422


def test_student_sees_only_own(client, py_lab):
    me = make_student(client, "Я")
    other = make_student(client, "Другой")
    submit(client, as_student(me["invite_key"]), py_lab, "mine.py", "x = 1\n")
    submit(client, as_student(other["invite_key"]), py_lab, "theirs.py", "y = 2\n")
    mine = client.get("/api/me/submissions", headers=as_student(me["invite_key"])).json()
    assert [s["filename"] for s in mine] == ["mine.py"]
    assert mine[0]["source_code"] == "x = 1\n"
    assert mine[0]["lab_title"] == py_lab["title"]
    assert mine[0]["student_name"] == "Я"


def test_review_with_comment(client, py_lab):
    s = make_student(client)
    sub = submit(client, as_student(s["invite_key"]), py_lab, "a.py", "x = 1\n").json()
    assert sub["reviewed_at"] is None
    r = client.patch(
        f"/api/submissions/{sub['id']}",
        json={"status": "needs_revision", "teacher_comment": "Добавь docstring"},
        headers=TEACHER,
    ).json()
    assert r["status"] == "needs_revision"
    assert r["teacher_comment"] == "Добавь docstring"
    assert r["reviewed_at"].endswith(("Z", "+00:00"))
    mine = client.get("/api/me/submissions", headers=as_student(s["invite_key"])).json()
    assert mine[0]["teacher_comment"] == "Добавь docstring"


def test_queue_filter_by_status(client, py_lab):
    s = make_student(client)
    key = as_student(s["invite_key"])
    submit(client, key, py_lab, "clean.py", 'print("ok")\n')
    submit(client, key, py_lab, "dirty.py", "import os\n")
    queue = client.get("/api/submissions?status=checked", headers=TEACHER).json()
    assert [q["filename"] for q in queue] == ["clean.py"]
    assert queue[0]["source_code"] == 'print("ok")\n'
