from pathlib import Path
from time import monotonic, sleep

from fastapi.testclient import TestClient

from vengine.api import create_app
from vengine.grading import grade
from vengine.models import (
    ChoiceSpec,
    CodeCase,
    CodeSpec,
    CompositeSpec,
    ContentBlock,
    ExerciseRevision,
    GradeResult,
    Option,
    PluginSpec,
)
from vengine.plugins import register_grader
from vengine.store import Store


def wait_job(client: TestClient, job_id: str) -> dict:
    deadline = monotonic() + 5
    while monotonic() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["stage"] in {"review_ready", "failed", "cancelled"}:
            return job
        sleep(0.01)
    raise AssertionError("Import job did not finish")


def test_import_review_practice_and_immutable_attempts(tmp_path: Path):
    client = TestClient(create_app(tmp_path / "data"))
    text = b"Question 1\nWhat is 2 + 2?\nA. 3\nB. 4\nC. 5"
    response = client.post("/api/import?generate_ai=false", files={"file": ("math.txt", text, "text/plain")})
    assert response.status_code == 200, response.text
    assert wait_job(client, response.json()["id"])["stage"] == "review_ready"
    source_id = response.json()["source_id"]
    source_page = client.get(f"/api/sources/{source_id}/pages/1")
    assert source_page.status_code == 200
    assert "Question 1" in source_page.json()["page"]["blocks"][0]["text"]
    review = client.get("/api/exercises", params={"status": "needs_review"}).json()
    assert len(review) == 1
    item = review[0]
    exercise_id = item["exercise_id"]
    assert client.get(f"/api/exercises/{exercise_id}").status_code == 404
    edited = client.patch(f"/api/review/{exercise_id}", json={"changes": {
        "interaction": {"kind": "choice", "options": item["interaction"]["options"],
                        "correct": ["B"]}}})
    assert edited.status_code == 200, edited.text
    new_revision = edited.json()
    assert new_revision["revision"] == 2
    assert client.post(f"/api/review/{item['id']}/approve").status_code == 409
    assert client.post(f"/api/review/{new_revision['id']}/approve").status_code == 200
    public = client.get(f"/api/exercises/{exercise_id}").json()
    assert "correct" not in public["interaction"]
    first = client.post(f"/api/exercises/{exercise_id}/submit", json={"response": "A"}).json()
    second = client.post(f"/api/exercises/{exercise_id}/submit", json={"response": "B"}).json()
    assert first["attempt"]["grade"]["outcome"] == "incorrect"
    assert second["attempt"]["grade"]["outcome"] == "correct"
    assert len(client.get(f"/api/exercises/{exercise_id}/attempts").json()) == 2
    assert client.get("/api/health").json()["stats"]["attempts"] == 2
    repeat = client.post("/api/import?generate_ai=false", files={"file": ("math.txt", text, "text/plain")})
    assert repeat.json()["id"] == response.json()["id"]


def test_code_never_runs_without_sandbox(tmp_path: Path):
    marker = tmp_path / "would_be_bad"
    code = f"open({str(marker)!r}, 'w').write('unsafe')\ndef solve(x): return x"
    item = ExerciseRevision(prompt=[ContentBlock(text="Echo")],
                            interaction=CodeSpec(language="python", cases=[
                                CodeCase(input=[1], expected=1)]))
    result = grade(item, code)
    assert result.outcome == "error"
    assert not marker.exists()


def test_revision_history_and_search(tmp_path: Path):
    store = Store(tmp_path)
    item = ExerciseRevision(title="Fractions", prompt=[ContentBlock(text="Half of 8?")],
                            interaction=ChoiceSpec(options=[Option(id="A", blocks=[ContentBlock(text="4")]),
                                                            Option(id="B", blocks=[ContentBlock(text="2")])],
                                                   correct=["A"]), status="needs_review")
    store.save_revision(item)
    assert store.search("Fractions") == []
    approved = store.approve(item.id)
    assert approved.status == "approved"
    assert store.search("Fractions")[0].id == item.id
    next_item = store.revise(item.exercise_id, {"title": "A changed title"})
    assert next_item.status == "needs_review"
    assert store.get_revision(item.id).status == "approved"
    assert store.latest(item.exercise_id).id == next_item.id
    assert store.published(item.exercise_id).id == item.id
    assert store.list_exercises(status="approved")[0].id == item.id
    assert store.search("Fractions")[0].id == item.id


def test_project_plugin_keeps_private_key_out_of_public_contract():
    register_grader("test-vocabulary", lambda spec, response: GradeResult(
        outcome="correct" if response == spec.private_payload["answer"] else "incorrect",
        score=float(response == spec.private_payload["answer"])))
    item = ExerciseRevision(prompt=[ContentBlock(text="Translate casa")],
                            interaction=PluginSpec(plugin="test-vocabulary",
                                                   public_payload={"language": "en"},
                                                   private_payload={"answer": "house"}))
    assert "private_payload" not in item.public_view()["interaction"]
    assert grade(item, "house").outcome == "correct"


def test_loopback_rejects_dns_rebinding_host(tmp_path: Path):
    client = TestClient(create_app(tmp_path))
    assert client.get("/api/health", headers={"Host": "evil.example"}).status_code == 400
    assert client.post("/api/exercises", headers={"Origin": "https://evil.example"},
                       json={"prompt": [{"text": "Prompt"}],
                             "interaction": {"kind": "rubric"}}).status_code == 403


def test_composite_public_view_recursively_hides_nested_answers():
    item = ExerciseRevision(prompt=[ContentBlock(text="Two parts")],
                            interaction=CompositeSpec(parts=[
                                {"kind": "choice", "correct": ["B"], "options": []},
                                {"kind": "text", "answer": "secret", "accepted": ["secret"]}]))
    public = item.public_view()
    assert "correct" not in public["interaction"]["parts"][0]
    assert "answer" not in public["interaction"]["parts"][1]
    assert "secret" not in str(public)


def test_composite_grades_each_part_without_revealing_keys():
    item = ExerciseRevision(prompt=[ContentBlock(text="Two parts")],
                            interaction=CompositeSpec(parts=[
                                {"kind": "boolean", "correct": True},
                                {"kind": "text", "accepted": ["house"]}]))
    result = grade(item, [True, "wrong"])
    assert result.outcome == "partial"
    assert result.score == 0.5
    assert [part["outcome"] for part in result.details["parts"]] == ["correct", "incorrect"]
    assert grade(item, [True]).outcome == "error"
