import json
from pathlib import Path
from time import monotonic, sleep

from fastapi.testclient import TestClient

from vengine.api import create_app
from vengine.documents import parse
from vengine.exam import extract_originals, ingest_structured
from vengine.jobs import import_source
from vengine.store import Store

EXAM = """Leia o texto para responder às questões 1 a 2.
TEXTO 1
A missão diplomática negocia um acordo entre países.

Questão 1. Qual atividade aparece no texto?
A) Negociação de um acordo
B) Construção de uma ponte

Questão 2. Quem participa do acordo?
A) Países
B) Municípios
"""


def test_original_exam_binds_shared_text_and_official_answers(tmp_path: Path):
    source = tmp_path / "exam.txt"
    key = tmp_path / "answers.txt"
    source.write_text(EXAM)
    key.write_text("1 A\n2 A\n")
    store = Store(tmp_path / "data")
    job = import_source(store, source, mode="originals", answer_path=key)
    assert job.stage == "review_ready", job.error
    assert job.proposals_count == 2
    items = sorted(store.list_exercises("needs_review"), key=lambda item: item.label)
    assert items[0].passage_id == items[1].passage_id
    assert "missão diplomática" in items[0].contexts[0].text
    assert items[0].interaction.correct == ["A"]
    assert items[0].answer_source is not None
    assert "answer_source" not in items[0].public_view()
    passage = store.latest_passage(items[0].passage_id)
    assert passage.status == "needs_review"
    store.approve_passage(passage.id)
    current = store.latest(items[0].exercise_id)
    assert current.revision == 2
    store.approve(current.id)
    assert store.published(current.exercise_id).interaction.correct == ["A"]


def test_grouped_ce_exam_uses_grid_key_and_holds_annulments(tmp_path: Path):
    source = tmp_path / "grouped.txt"
    key = tmp_path / "key.txt"
    source.write_text("""Texto I
A source passage with enough text to be reviewed beside each question.
QUESTÃO 1
Com base no texto I, julgue os itens.
1 The first assertion has a complete statement.
2 The second assertion has a complete statement.
3 The third assertion has a complete statement.
4 The fourth assertion has a complete statement.
QUESTÃO 2
Julgue os itens seguintes.
1 Another first assertion has enough words.
2 Another second assertion has enough words.
3 Another third assertion has enough words.
4 Another fourth assertion has enough words.
""")
    key.write_text("C E X C E E C C\nGABARITOS OFICIAIS DEFINITIVOS\n"
                   "Questão 1 Questão 2\n")
    store = Store(tmp_path / "data")
    job = import_source(store, source, mode="originals", answer_path=key)
    assert job.stage == "review_ready", job.error
    assert job.proposals_count == 8
    items = {item.label: item for item in store.list_exercises("needs_review")}
    assert sorted(items) == ["1.1", "1.2", "1.3", "1.4", "2.1", "2.2", "2.3", "2.4"]
    assert items["1.1"].interaction.correct is True
    assert items["1.2"].interaction.correct is False
    assert items["1.3"].interaction.correct is None
    assert items["1.1"].passage_id == items["1.4"].passage_id
    assert items["2.1"].passage_id is None
    try:
        store.approve(items["1.3"].id)
    except ValueError as exc:
        assert "shared text" in str(exc)
    else:
        raise AssertionError("unapproved passage must block question approval")
    store.approve_passage(store.latest_passage(items["1.3"].passage_id).id)
    try:
        store.approve(store.latest(items["1.3"].exercise_id).id)
    except ValueError as exc:
        assert "verified answer" in str(exc)
    else:
        raise AssertionError("annulled item must not be scored")
    later = Store(tmp_path / "later")
    first = import_source(later, source, mode="originals")
    second = import_source(later, source, mode="originals", answer_path=key)
    assert first.collection_id == second.collection_id
    revised = later.list_exercises("needs_review")
    assert len(revised) == 8
    assert all(item.revision == 2 for item in revised)
    assert next(item for item in revised if item.label == "1.2").interaction.correct is False


def test_shared_correction_creates_new_question_revision(tmp_path: Path):
    source = tmp_path / "exam.txt"
    key = tmp_path / "answers.txt"
    source.write_text(EXAM)
    key.write_text("1 A\n2 A\n")
    store = Store(tmp_path / "data")
    import_source(store, source, mode="originals", answer_path=key)
    items = store.list_exercises("needs_review")
    passage_id = items[0].passage_id
    store.approve_passage(store.latest_passage(passage_id).id)
    for item in items:
        store.approve(store.latest(item.exercise_id).id)
    old = store.published(items[0].exercise_id)
    edited = store.revise_passage(passage_id, title="Texto 1", blocks=[
        old.contexts[0].model_copy(update={"text": "A missão diplomática negocia um acordo."})])
    store.approve_passage(edited.id)
    new = store.published(items[0].exercise_id)
    assert new.revision == old.revision + 1
    assert new.contexts[0].text == "A missão diplomática negocia um acordo."
    assert store.get_revision(old.id).contexts[0].text != new.contexts[0].text
    assert store.published(items[1].exercise_id).contexts[0].text == new.contexts[0].text


def test_later_official_key_revises_existing_exam(tmp_path: Path):
    source = tmp_path / "exam.txt"
    key = tmp_path / "answers.txt"
    source.write_text(EXAM)
    key.write_text("1 A\n2 A\n")
    store = Store(tmp_path / "data")
    first = import_source(store, source, mode="originals")
    original = store.list_exercises("needs_review")
    assert all(not item.interaction.correct for item in original)
    second = import_source(store, source, mode="originals", answer_path=key)
    assert second.stage == "review_ready", second.error
    assert second.collection_id == first.collection_id
    assert len(store.collections()) == 1
    updated = store.list_exercises("needs_review")
    assert {item.exercise_id for item in updated} == {item.exercise_id for item in original}
    assert all(item.revision == 2 and item.interaction.correct == ["A"] for item in updated)


def test_structured_exam_import_is_idempotent_and_rejects_bad_binding(tmp_path: Path):
    source = tmp_path / "exam.txt"
    source.write_text(EXAM)
    bundle = tmp_path / "exam.json"
    payload = {
        "schema_version": 1,
        "title": "Diplomacy trial",
        "passages": [{"key": "text-1", "title": "Texto 1", "page": 1,
                      "text": "A missão diplomática negocia um acordo entre países.",
                      "questions": [1, 2]}],
        "questions": [{"number": 1, "page": 1, "prompt": "Qual atividade aparece no texto?",
                       "options": {"A": "Negociação de um acordo", "B": "Construção de uma ponte"},
                       "passage_key": "text-1"}],
    }
    bundle.write_text(json.dumps(payload))
    store = Store(tmp_path / "data")
    first = ingest_structured(store, bundle, source)
    second = ingest_structured(store, bundle, source)
    assert first["questions"] == 1
    assert second["questions"] == 0
    assert len(store.collections()) == 1
    payload["questions"][0]["number"] = 3
    bundle.write_text(json.dumps(payload))
    try:
        ingest_structured(store, bundle, source)
    except ValueError as exc:
        assert "binding" in str(exc)
    else:
        raise AssertionError("invalid passage binding was accepted")


def test_originals_api_keeps_answers_private_until_review(tmp_path: Path):
    client = TestClient(create_app(tmp_path / "data", project_root=tmp_path))
    response = client.post("/api/import?mode=originals", files={
        "file": ("exam.txt", EXAM.encode(), "text/plain"),
        "answer_file": ("key.txt", b"1 A\n2 A\n", "text/plain"),
    })
    assert response.status_code == 200, response.text
    job = response.json()
    deadline = monotonic() + 5
    while job["stage"] not in {"review_ready", "failed"} and monotonic() < deadline:
        sleep(0.01)
        job = client.get(f"/api/jobs/{job['id']}").json()
    assert job["stage"] == "review_ready", job.get("error")
    draft = client.get("/api/exercises?status=needs_review").json()[0]
    assert draft["passage_id"]
    passage = client.get(f"/api/passages/{draft['passage_id']}").json()
    assert passage["status"] == "needs_review"
    assert client.post(f"/api/review/passages/{passage['id']}/approve").status_code == 200
    revised = client.get(f"/api/exercises/{draft['exercise_id']}?review=true").json()
    assert client.post(f"/api/review/{revised['id']}/approve").status_code == 200
    public = client.get(f"/api/exercises/{draft['exercise_id']}").json()
    assert "answer_source" not in public
    assert "correct" not in public["interaction"]
    assert public["contexts"]
    edited = client.patch(f"/api/review/passages/{draft['passage_id']}", json={
        "title": "Texto corrigido", "text": "A missão diplomática apresenta um acordo entre países."
    })
    assert edited.status_code == 200, edited.text
    assert client.post(f"/api/review/passages/{edited.json()['id']}/approve").status_code == 200
    updated = client.get(f"/api/exercises/{draft['exercise_id']}").json()
    assert updated["revision"] == public["revision"] + 1
    assert "apresenta" in updated["contexts"][0]["text"]


def test_second_passage_between_question_groups(tmp_path: Path):
    source = tmp_path / "two-texts.txt"
    source.write_text(EXAM + """
Leia o texto para responder às questões 3 a 4.
TEXTO 2
Uma comissão apresenta o relatório ao conselho.

Questão 3. Quem apresenta o relatório?
A) Uma comissão
B) Um tribunal

Questão 4. A quem o relatório é apresentado?
A) Ao conselho
B) Ao público

Questão 5. Qual é a capital de um país hipotético?
A) Alfa
B) Beta
""")
    bundle = extract_originals(parse(source, "source"))
    assert len(bundle.passages) == 2
    assert [q.passage_key for q in bundle.questions[:2]] == [bundle.passages[0].key] * 2
    assert [q.passage_key for q in bundle.questions[2:4]] == [bundle.passages[1].key] * 2
    assert bundle.questions[4].passage_key is None
