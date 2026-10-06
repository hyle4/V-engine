import json
import sqlite3
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from vengine.ai import ProposalBatch, generate
from vengine.api import create_app
from vengine.cli import main
from vengine.documents import parse, supported_formats
from vengine.jobs import import_source, queue_source, run_job
from vengine.models import (
    Attempt,
    BooleanSpec,
    ContentBlock,
    DocumentIR,
    DocumentPage,
    ExerciseRevision,
    GradeResult,
    PassageRevision,
    RubricSpec,
)
from vengine.plugins import register_ai_provider, register_parser, register_proposer
from vengine.project import ProjectConfig, load_project, save_project
from vengine.store import Store


def test_project_config_roundtrip_and_api(tmp_path: Path):
    client = TestClient(create_app(tmp_path / "data", project_root=tmp_path))
    assert client.get("/api/project").json()["configured"] is False
    config = ProjectConfig(name="Language Lab", subject="Languages", ai_provider="none")
    response = client.put("/api/project", json=config.model_dump())
    assert response.status_code == 200
    assert load_project(tmp_path) == config
    assert "Language Lab" in (tmp_path / "vengine.toml").read_text()
    assert client.get("/api/project").json()["project"]["subject"] == "Languages"
    assert client.put("/api/project", json={"name": "X", "secret": "bad"}).status_code == 422
    save_project(tmp_path, config.model_copy(update={"name": 'A "quoted" name'}))
    assert load_project(tmp_path).name == 'A "quoted" name'


def test_blocked_imports_refuse_leetcode_and_auditor_files(tmp_path: Path):
    from vengine.project import refuses_import
    config = ProjectConfig(
        name="Diplomacy", subject="CACD", ai_provider="none",
        blocked_imports=["leetcode", "leet code", "blind 75", "blind75", "auditor"])
    assert refuses_import(config, "blind75.pdf")
    assert refuses_import(config, "CESPE_2025_Auditor_Fiscal.pdf")
    assert refuses_import(config, "problems.json", '[{"titleSlug": "two-sum"}]')
    assert not refuses_import(config, "IRBR_17_DIPLOMACIA.pdf")
    save_project(tmp_path, config)
    client = TestClient(create_app(tmp_path / "data", project_root=tmp_path))
    refused = client.post("/api/import", files={"file": (
        "leetcode.json", b'[{"title": "Two Sum"}]', "application/json")})
    assert refused.status_code == 422
    accepted = client.post("/api/import", files={"file": (
        "notes.txt", b"The capital is Paris.\n", "text/plain")})
    assert accepted.status_code == 200


def test_reader_settings_roundtrip(tmp_path: Path):
    config = ProjectConfig(
        name="Diplomacy", subject="CACD", ai_provider="none", show_project=False,
        font="JetBrainsMono Nerd Font", text_size="lg", reading_width="narrow",
        library_filters=["Objetiva", "Manhã"])
    save_project(tmp_path, config)
    assert load_project(tmp_path) == config
    client = TestClient(create_app(tmp_path / "data", project_root=tmp_path))
    assert client.put("/api/project", json=config.model_dump()).status_code == 200
    assert client.get("/api/project").json()["project"]["show_project"] is False
    rejected = config.model_dump()
    rejected["font"] = "Comic Sans"
    assert client.put("/api/project", json=rejected).status_code == 422
    smaller = config.model_copy(update={"text_size": "xs"})
    assert client.put("/api/project", json=smaller.model_dump()).status_code == 200
    assert load_project(tmp_path).text_size == "xs"


def test_collection_progress_counts_attempts(tmp_path: Path):
    store = Store(tmp_path / "data")
    collection_id = store.create_collection("CACD 2024 · Objetiva · Manhã")
    saved = [
        store.save_revision(ExerciseRevision(
            collection_id=collection_id, label=str(index),
            prompt=[ContentBlock(text=f"Item {index}")],
            interaction=BooleanSpec(correct=True), status="needs_review"))
        for index in (1, 2, 3)
    ]
    published = [store.approve(item.id) for item in saved]
    store.record_attempt(Attempt(
        exercise_id=published[0].exercise_id, revision_id=published[0].id,
        response=True, grade=GradeResult(outcome="correct", score=1)))
    store.record_attempt(Attempt(
        exercise_id=published[1].exercise_id, revision_id=published[1].id,
        response=False, grade=GradeResult(outcome="incorrect", score=0)))
    store.mark(published[2].exercise_id, starred=True)
    counts = {row["id"]: row for row in store.collections()}[collection_id]
    assert (counts["total"], counts["answered"], counts["correct"]) == (3, 2, 1)
    client = TestClient(create_app(tmp_path / "data", project_root=tmp_path))
    listed = {row["exercise_id"]: row for row in client.get(
        f"/api/exercises?collection_id={collection_id}&limit=500").json()}
    assert listed[published[0].exercise_id]["last_outcome"] == "correct"
    assert listed[published[1].exercise_id]["last_outcome"] == "incorrect"
    assert listed[published[2].exercise_id]["last_outcome"] is None
    assert listed[published[2].exercise_id]["starred"] is True
    assert client.get("/api/collections").json()[0]["correct"] == 1


def test_locale_roundtrip_and_page_render(tmp_path: Path):
    import pypdfium2 as pdfium

    config = ProjectConfig(name="Diplomacy", subject="CACD", ai_provider="none", locale="pt-BR")
    save_project(tmp_path, config)
    assert load_project(tmp_path).locale == "pt-BR"
    assert 'locale = "pt-BR"' in (tmp_path / "vengine.toml").read_text()
    pdf = pdfium.PdfDocument.new()
    pdf.new_page(200, 200)
    path = tmp_path / "blank.pdf"
    pdf.save(path)
    source = Store(tmp_path / "data").add_source(path, "application/pdf")
    client = TestClient(create_app(tmp_path / "data", project_root=tmp_path))
    assert client.get("/api/project").json()["project"]["locale"] == "pt-BR"
    rejected = config.model_dump()
    rejected["locale"] = "fr"
    assert client.put("/api/project", json=rejected).status_code == 422
    rendered = client.get(f"/api/sources/{source['id']}/render/1")
    assert rendered.status_code == 200
    assert rendered.content.startswith(b"\x89PNG")
    assert client.get(f"/api/sources/{source['id']}/render/9").status_code == 404


def test_annulled_item_cannot_be_approved(tmp_path: Path):
    from vengine.models import BooleanSpec

    store = Store(tmp_path / "data")
    item = store.save_revision(ExerciseRevision(
        prompt=[ContentBlock(text="Annulled official item.")],
        interaction=BooleanSpec(correct=True),
        status="needs_review",
        metadata={"annulled": True},
    ))
    try:
        store.approve(item.id)
    except ValueError as exc:
        assert "nnulled" in str(exc)
    else:
        raise AssertionError("annulled item must stay out of scored practice")


def test_accept_official_requires_passage_and_skips_annulled(tmp_path: Path, monkeypatch, capsys):
    store = Store(tmp_path / "data")
    collection_id = store.create_collection("Exam")
    passage = store.save_passage(PassageRevision(
        collection_id=collection_id, title="Page 1",
        blocks=[ContentBlock(text="The delegation presents a proposal.")]))
    official = store.save_revision(ExerciseRevision(
        collection_id=collection_id, passage_id=passage.passage_id,
        passage_revision_id=passage.id, contexts=passage.blocks,
        prompt=[ContentBlock(text="The delegation presents a proposal.")],
        interaction=BooleanSpec(correct=True), answer_origin="official",
        status="needs_review"))
    annulled = store.save_revision(ExerciseRevision(
        collection_id=collection_id, prompt=[ContentBlock(text="Annulled item stays out.")],
        interaction=BooleanSpec(correct=True), answer_origin="official",
        status="needs_review", metadata={"annulled": True}))
    store.save_revision(ExerciseRevision(
        collection_id=collection_id, prompt=[ContentBlock(text="Write a short essay.")],
        interaction=RubricSpec(), status="needs_review"))
    try:
        store.approve(official.id)
    except ValueError as exc:
        assert "shared text" in str(exc)
    else:
        raise AssertionError("passage must be approved first")
    monkeypatch.setattr(sys, "argv", ["vengine", "--data", str(tmp_path / "data"), "accept-official"])
    main()
    counts = json.loads(capsys.readouterr().out)
    assert counts == {"passages": 1, "accepted": 1, "skipped_annulled": 1, "skipped_open": 1}
    published = store.published(official.exercise_id)
    assert published is not None and published.interaction.correct is True
    assert store.latest(annulled.exercise_id).status == "needs_review"


def test_custom_source_and_proposer_pipeline(tmp_path: Path):
    def parse_flash(path: Path, source_id: str, filename: str) -> DocumentIR:
        return DocumentIR(source_id=source_id, title=filename,
                          pages=[DocumentPage(number=1, blocks=[ContentBlock(text=path.read_text())])],
                          parser="test", parser_version="1")

    def propose_flash(document: DocumentIR, collection_id: str) -> list[ExerciseRevision]:
        return [ExerciseRevision(collection_id=collection_id,
                                 prompt=[ContentBlock(text=document.pages[0].blocks[0].text)],
                                 interaction=RubricSpec(), status="needs_review")]

    register_parser(".flash", parse_flash)
    register_proposer("test-flash", propose_flash)
    options = TestClient(create_app(tmp_path / "options-data")).get("/api/project/options").json()
    assert ".flash" in options["formats"]
    assert "test-flash" in options["proposers"]
    source = tmp_path / "cards.flash"
    source.write_text("Translate casa")
    assert ".flash" in supported_formats()
    assert parse(source, "source").parser == "test"
    store = Store(tmp_path / "data")
    job = queue_source(store, source, proposer="test-flash")
    assert job.stage == "queued"
    assert run_job(store, job.id).stage == "review_ready"
    assert len(store.list_exercises(status="needs_review")) == 1


def test_project_cli_stats_uses_project_data(tmp_path: Path, monkeypatch, capsys):
    project = tmp_path / "course"
    store = Store(project / "data")
    store.create_collection("Course")
    monkeypatch.setattr(sys, "argv", ["vengine", "--project", str(project), "stats"])
    main()
    assert json.loads(capsys.readouterr().out)["collections"] == 1


def test_import_inherits_project_subject(tmp_path: Path):
    source = tmp_path / "notes.txt"
    source.write_text("Plants turn toward the light.")
    store = Store(tmp_path / "data")
    job = import_source(store, source, subject="Botany")
    assert job.stage == "review_ready"
    assert store.list_exercises(status="needs_review")[0].subject == "Botany"
    changed = queue_source(store, source, subject="Ecology")
    assert changed.id != job.id


def test_migration_backup_handles_project_path_with_uri_characters(tmp_path: Path):
    data = tmp_path / "course #1" / "data"
    data.mkdir(parents=True)
    with sqlite3.connect(data / "project.sqlite3") as db:
        db.execute("CREATE TABLE previous (value TEXT)")
        db.execute("INSERT INTO previous VALUES ('keep')")
    store = Store(data)
    assert store.db.exists()
    with sqlite3.connect(data / "project.sqlite3.pre-v3.bak") as db:
        assert db.execute("SELECT value FROM previous").fetchone()[0] == "keep"


def test_v3_database_gets_passage_schema_and_backup(tmp_path: Path):
    data = tmp_path / "data"
    data.mkdir()
    with sqlite3.connect(data / "project.sqlite3") as db:
        db.execute("PRAGMA user_version=3")
        db.execute("CREATE TABLE existing (value TEXT)")
        db.execute("INSERT INTO existing VALUES ('retained')")
    store = Store(data)
    with sqlite3.connect(store.db) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 4
        assert db.execute("SELECT value FROM existing").fetchone()[0] == "retained"
        assert db.execute("SELECT name FROM sqlite_master WHERE name='passages'").fetchone()
    with sqlite3.connect(data / "project.sqlite3.pre-v4.bak") as db:
        assert db.execute("SELECT value FROM existing").fetchone()[0] == "retained"


def test_custom_ai_provider_usage_and_citation_gate():
    def provider(prompt: str) -> ProposalBatch:
        assert "SOURCE:" in prompt
        return ProposalBatch.model_validate({
            "usage": {"input_tokens": 120, "output_tokens": 30},
            "exercises": [
                {"kind": "text", "prompt": "What color is the specimen?", "answer": "blue",
                 "page": 1, "source_quote": "specimen is blue"},
                {"kind": "text", "prompt": "What shape is the specimen?", "answer": "round",
                 "page": 1, "source_quote": "specimen is round"},
            ],
        })

    register_ai_provider("test-cited-ai", provider)
    document = DocumentIR(source_id="source-1", title="Sample", parser="test", parser_version="1",
                          pages=[DocumentPage(number=1, blocks=[ContentBlock(
                              text="The specimen is blue and the test is complete.")])])
    usage = []
    items = generate(document, "collection-1", provider="test-cited-ai", count=2,
                     on_batch=usage.append)
    assert len(items) == 1
    assert items[0].sources[0].quote == "specimen is blue"
    assert usage == [{"requests": 1, "input_tokens": 120, "output_tokens": 30}]


def test_batch_discard_is_atomic_and_keeps_published_revision(tmp_path: Path):
    client = TestClient(create_app(tmp_path / "data"))
    body = {"prompt": [{"text": "Original prompt"}], "interaction": {"kind": "rubric"}}
    first = client.post("/api/exercises", json=body).json()
    second = client.post("/api/exercises", json=body).json()
    assert client.post(f"/api/review/{first['id']}/approve").status_code == 200
    edited = client.patch(f"/api/review/{first['exercise_id']}",
                          json={"changes": {"prompt": [{"text": "Edited prompt"}]}}).json()
    response = client.post("/api/review/archive",
                           json={"revision_ids": [second["id"], first["id"]]})
    assert response.status_code == 409
    assert len(client.get("/api/exercises?status=needs_review").json()) == 2
    response = client.post("/api/review/archive",
                           json={"revision_ids": [second["id"], edited["id"]]})
    assert response.json() == {"archived": 2}
    assert client.get("/api/exercises?status=needs_review").json() == []
    published = client.get(f"/api/exercises/{first['exercise_id']}").json()
    assert published["prompt"][0]["text"] == "Original prompt"
