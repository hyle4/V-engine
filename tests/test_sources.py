from pathlib import Path
from time import monotonic, sleep

from fastapi.testclient import TestClient

from vengine import ai
from vengine.api import create_app
from vengine.jobs import import_source
from vengine.models import ContentBlock, DocumentIR, DocumentPage
from vengine.store import Store


def test_ai_proposals_require_real_citation_and_human_review(tmp_path: Path, monkeypatch):
    source = tmp_path / "notes.txt"
    source.write_text("France is in Europe. Its capital is Paris.\n")

    def proposed(prompt: str):
        assert "SOURCE:" in prompt
        return ai.ProposalBatch(exercises=[
            ai.Proposal(kind="text", prompt="What is the capital of France?", answer="Paris",
                        page=1, source_quote="Its capital is Paris."),
            ai.Proposal(kind="text", prompt="What is the capital of Mars?", answer="Ares",
                        page=1, source_quote="Mars is Ares"),
        ])

    monkeypatch.setattr(ai, "_agy", proposed)
    store = Store(tmp_path / "data")
    job = import_source(store, source, generate_ai=True, provider="agy", count=2)
    assert job.stage == "review_ready"
    assert store.stats()["review"] == 1
    assert store.stats()["approved"] == 0
    item = store.list_exercises(status="needs_review")[0]
    assert item.answer_origin == "ai_proposed"
    assert item.sources[0].quote == "Its capital is Paris."


def test_api_defaults_to_configured_cloud_provider(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr("vengine.api.shutil.which", lambda name: "/usr/bin/agy" if name == "agy" else None)
    monkeypatch.setattr(ai, "_agy", lambda prompt: ai.ProposalBatch(exercises=[ai.Proposal(
        kind="text", prompt="Where is the capital of France?", answer="Paris",
        page=1, source_quote="capital is Paris")]))
    client = TestClient(create_app(tmp_path))
    job = client.post("/api/import", files={"file": (
        "notes.txt", b"The capital is Paris.\n", "text/plain")}).json()
    assert job["generate_ai"] is True
    assert job["provider"] == "agy"
    deadline = monotonic() + 5
    while job["stage"] not in {"review_ready", "failed"} and monotonic() < deadline:
        sleep(0.01)
        job = client.get(f"/api/jobs/{job['id']}").json()
    assert job["stage"] == "review_ready"
    assert job["proposals_count"] == 1


def test_ai_samples_across_long_document(monkeypatch):
    calls = []

    def proposed(prompt: str):
        calls.append(prompt)
        page = int(prompt.split("PAGE ")[1].split("\n")[0])
        return ai.ProposalBatch(exercises=[ai.Proposal(
            kind="text", prompt=f"What fact appears on page {page}?", answer=f"Fact {page}",
            page=page, source_quote=f"Fact {page}")])

    monkeypatch.setattr(ai, "_agy", proposed)
    document = DocumentIR(source_id="source", title="Long", parser="test", parser_version="1",
                          pages=[DocumentPage(number=i, blocks=[ContentBlock(
                              text=f"Fact {i}. " + "x" * 20000)]) for i in range(1, 5)])
    items = ai.generate(document, "collection", provider="agy", count=3)
    assert len(calls) == 3
    assert len(items) == 3
    assert {item.sources[0].page for item in items} == {1, 3, 4}


def test_open_response_self_assessment_schedules_review(tmp_path: Path):
    client = TestClient(create_app(tmp_path))
    item = client.post("/api/exercises", json={
        "subject": "History", "prompt": [{"text": "Explain the event."}],
        "interaction": {"kind": "rubric", "criteria": ["Accuracy"]}}).json()
    assert client.post(f"/api/review/{item['id']}/approve").status_code == 200
    submitted = client.post(f"/api/exercises/{item['exercise_id']}/submit",
                            json={"response": "My explanation"}).json()
    assert submitted["attempt"]["grade"]["outcome"] == "ungraded"
    attempt_id = submitted["attempt"]["id"]
    assessed = client.post(f"/api/attempts/{attempt_id}/assess", json={"rating": 3})
    assert assessed.status_code == 200
    assert assessed.json()["due"]
    assert client.post(f"/api/attempts/{attempt_id}/assess", json={"rating": 3}).status_code == 409

