from pathlib import Path
from unittest.mock import patch

def sample_payload():
    return {"recipients": [
        {"name": "Asha Sharma", "email": "asha@example.com", "course": "Python Basics"},
        {"name": "Rahul Verma", "email": "rahul@example.com", "course": "Web Development"}
    ]}

def test_create_job_and_status(client):
    response = client.post("/jobs", json=sample_payload())
    assert response.status_code == 202
    body = response.json()
    assert body["total"] == 2
    assert body["status"] in {"queued", "completed", "completed_with_errors"}
    job = client.get(f"/jobs/{body['id']}")
    assert job.status_code == 200
    assert job.json()["progress_percent"] == 100
    assert job.json()["succeeded"] == 2

def test_input_validation(client):
    response = client.post("/jobs", json={"recipients": [
        {"name": "", "email": "not-an-email", "course": ""}
    ]})
    assert response.status_code == 422

def test_certificate_generation_and_retrieval(client):
    body = client.post("/jobs", json=sample_payload()).json()
    status = client.get(f"/jobs/{body['id']}").json()
    recipient = status["recipients"][0]
    assert recipient["status"] == "succeeded"
    cert = client.get(recipient["download_url"])
    assert cert.status_code == 200
    assert cert.headers["content-type"] == "application/pdf"
    assert cert.content.startswith(b"%PDF")

def test_one_certificate_failure_does_not_stop_others(client):
    from app import main as main_module
    original = main_module.generate_certificate

    def flaky(name, course, certificate_id):
        if name == "Asha Sharma":
            raise RuntimeError("simulated PDF failure")
        return original(name, course, certificate_id)

    with patch("app.main.generate_certificate", side_effect=flaky):
        created = client.post("/jobs", json=sample_payload())
    assert created.status_code == 202
    status = client.get(f"/jobs/{created.json()['id']}").json()
    by_name = {r["name"]: r for r in status["recipients"]}
    assert by_name["Asha Sharma"]["status"] == "failed"
    assert by_name["Asha Sharma"]["error"]
    assert by_name["Rahul Verma"]["status"] == "succeeded"
    assert status["failed"] == 1
    assert status["succeeded"] == 1

def test_missing_job_and_certificate(client):
    assert client.get("/jobs/99999").status_code == 404
    assert client.get("/certificates/not-real").status_code == 404
