import json
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from vengine.api import create_app
from vengine.cli import main
from vengine.models import BooleanSpec, ContentBlock, ExerciseRevision, RubricSpec
from vengine.organize import Organization, PromptPart, QuotePart, ask_agy, bind_quotes, organize_store, segment
from vengine.store import Store

MIXED = """Nesta prova, faça o que se pede, utilizando o rascunho. Escreva os textos definitivos no Caderno de Textos Definitivos. Utilize apenas caneta esferográfica de tinta preta.

Em cada uma das questões discursivas de até 60 linhas, será atribuído ao domínio do conteúdo o valor máximo de 30,00 pontos.

-- PROVA ESCRITA DE DIREITO --

Questão 1

A scholar writes: "The discipline must renew its foundations."

Considerando o fragmento de texto apresentado como unicamente motivador, redija texto dissertativo acerca do tema. Em seu texto, aborde os seguintes aspectos: a expansão da disciplina.
"""

COVER = """Nesta prova, faça o que se pede, utilizando o rascunho. Escreva no Caderno de Textos Definitivos.

The delegation presented a written proposal.
"""


def test_protocol_separates_cover_rules_quote_and_task():
    result = segment(MIXED)
    assert result.confidence == "high"
    assert "".join(part.text for part in result.parts) == MIXED
    roles = [part.role for part in result.parts]
    assert roles == ["instructions", "scoring", "banner", "heading", "stimulus", "task"]
    by_role = {part.role: part.text for part in result.parts}
    assert "Nesta prova" in by_role["instructions"]
    assert "caneta" in by_role["instructions"]
    assert "domínio do conteúdo" in by_role["scoring"]
    assert "PROVA ESCRITA DE DIREITO" in by_role["banner"]
    assert "Questão 1" in by_role["heading"]
    assert "renew its foundations" in by_role["stimulus"]
    assert by_role["task"].lstrip().startswith("Considerando")
    assert "Nesta prova" not in by_role["task"]
    assert "aborde os seguintes aspectos" in by_role["task"]


def test_cover_prefix_peels_off_a_statement():
    result = segment(COVER)
    assert result.confidence == "high"
    assert "".join(part.text for part in result.parts) == COVER
    task = next(part.text for part in result.parts if part.role == "task")
    assert task.strip() == "The delegation presented a written proposal."
    assert "Nesta prova" not in task


def test_language_booklet_keeps_the_passage_out_of_the_rules():
    text = """PROVA ESCRITA DE LÍNGUA PORTUGUESA

Nesta prova, faça o que se pede, utilizando o rascunho. Escreva no Caderno de Textos Definitivos.

Serão apenados os textos fora do limite. Extensão máxima: 60 linhas [valor: 60,00 pontos]

A short passage about a neighbor.

Disserte sobre o tema apresentado.
"""
    result = segment(text)
    assert result.confidence == "high"
    assert "".join(part.text for part in result.parts) == text
    by_role = {part.role: part.text for part in result.parts}
    assert "Nesta prova" in by_role["instructions"]
    assert "apenados" in by_role["instructions"]
    assert "neighbor" in by_role["stimulus"]
    assert by_role["task"].lstrip().startswith("Disserte")
    assert "Nesta prova" not in by_role["task"]


EXCERPT = """CONCURSO PÚBLICO TERCEIRO-SECRETÁRIO DA CARREIRA DE DIPLOMATA
TIPO “U” PÁGINA 2/13
QUESTÃO 1
Leia, com atenção, o excerto a seguir.
A crise da dívida desestabilizou economias latino-americanas.
SIMONSEN, M. H.; WERLANG, S. R. O problema da dívida, com adaptações.
Considerando que o excerto tem caráter meramente motivador, redija um texto dissertativo abordando os seguintes tópicos:
 as características da reciclagem competitiva;
 o papel dos bancos privados internacionais.
Extensão do texto: até 60 linhas
[valor: 30,00 pontos]
"""


def test_protocol_separates_header_excerpt_and_topics():
    result = segment(EXCERPT)
    assert result.confidence == "high"
    assert "".join(part.text for part in result.parts) == EXCERPT
    by_role = {part.role: part.text for part in result.parts}
    assert "CONCURSO PÚBLICO" in by_role["banner"]
    assert "PÁGINA 2/13" in by_role["banner"]
    assert by_role["heading"].strip() == "QUESTÃO 1"
    assert "Leia, com atenção" in by_role["instructions"]
    assert "latino-americanas" in by_role["stimulus"]
    assert "com adaptações" in by_role["stimulus"]
    assert by_role["task"].lstrip().startswith("Considerando")
    assert "reciclagem competitiva" in by_role["task"]
    assert "Extensão do texto" in by_role["scoring"]
    assert "[valor: 30,00 pontos]" in by_role["scoring"]
    assert "CONCURSO PÚBLICO" not in by_role["task"]


def test_plain_prompt_stays_intact():
    result = segment("What does the delegation present?")
    assert result.confidence == "high"
    assert result.reason == "plain"
    assert [(part.role, part.text) for part in result.parts] == [("task", "What does the delegation present?")]


def test_unseparated_cover_stays_in_review():
    result = segment("Nesta prova, faça o que se pede, utilizando o rascunho.")
    assert result.confidence == "review"
    assert result.parts == []


def test_agy_spans_must_slice_the_original(monkeypatch):
    text = "Nesta prova, faça o que se pede.\n\nThe council met."
    monkeypatch.setattr("vengine.organize.shutil.which", lambda name: "/usr/bin/agy")

    def fake_run(command, **kwargs):
        payload = {"structured_output": {"spans": [
            {"role": "instructions", "start": 0, "end": text.index("\n\n")},
            {"role": "task", "start": text.index("The"), "end": len(text)},
        ]}}
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr("vengine.organize.subprocess.run", fake_run)
    result = ask_agy(text)
    assert result.confidence == "high"
    assert "".join(part.text for part in result.parts) == text
    assert result.parts[-1].text == "The council met."


def test_agy_rejects_spans_that_skip_words(monkeypatch):
    text = "Nesta prova, faça o que se pede.\n\nThe council met."
    monkeypatch.setattr("vengine.organize.shutil.which", lambda name: "/usr/bin/agy")

    def fake_run(command, **kwargs):
        payload = {"structured_output": {"spans": [
            {"role": "instructions", "start": 0, "end": text.index("\n\n")},
            {"role": "task", "start": text.index("council"), "end": len(text)},
        ]}}
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr("vengine.organize.subprocess.run", fake_run)
    assert ask_agy(text).confidence == "review"


def test_organize_command_keeps_approval_and_words(tmp_path: Path, monkeypatch, capsys):
    project = tmp_path / "proj"
    project.mkdir()
    data = project / "data"
    store = Store(data)
    saved = store.save_revision(ExerciseRevision(
        label="1", prompt=[ContentBlock(text=MIXED)], interaction=RubricSpec(),
        status="needs_review", answer_origin="official"))
    approved = store.approve(saved.id)
    plain = store.save_revision(ExerciseRevision(
        label="2", prompt=[ContentBlock(text="What does the delegation present?")],
        interaction=RubricSpec(), status="needs_review", answer_origin="official"))
    store.approve(plain.id)
    monkeypatch.setattr("vengine.organize.ask_agy", lambda text: Organization(confidence="review", reason="unused"))
    monkeypatch.setattr(sys, "argv", ["vengine", "--project", str(project), "organize", "--provider", "protocol"])
    main()
    report = json.loads((data / "staging" / "organize.json").read_text(encoding="utf-8"))
    assert report["organized"] == 1
    assert report["unchanged"] == 1
    assert report["applied"] == 0
    assert store.latest(approved.exercise_id).metadata.get("organization") is None

    monkeypatch.setattr(sys, "argv", ["vengine", "--project", str(project), "organize", "--provider", "protocol", "--apply"])
    main()
    latest = store.latest(approved.exercise_id)
    assert latest.id == approved.id
    assert latest.status == "approved"
    assert latest.revision == 1
    assert "".join(part["text"] for part in latest.metadata["organization"]) == MIXED
    client = TestClient(create_app(data, project_root=project))
    listed = client.get("/api/exercises?limit=10").json()
    mixed = next(item for item in listed if item["label"] == "1")
    assert mixed["metadata"] == {}
    task = next(part["text"] for part in mixed["organization"] if part["role"] == "task")
    assert task.lstrip().startswith("Considerando")
    assert "Nesta prova" not in task
    plain_view = next(item for item in listed if item["label"] == "2")
    assert "organization" not in plain_view


def test_apply_rejects_a_rewritten_partition(tmp_path: Path):
    store = Store(tmp_path / "data")
    saved = store.save_revision(ExerciseRevision(
        prompt=[ContentBlock(text=COVER)], interaction=RubricSpec(), status="needs_review"))
    try:
        store.set_organization(saved.exercise_id, [{"role": "task", "text": "A different question."}])
    except ValueError as exc:
        assert "does not match" in str(exc)
    else:
        raise AssertionError("rewritten text was stored")


def test_agy_copies_are_rejected_when_a_word_changes():
    original = "Nesta prova, faça o que se pede.\n\nThe council met."
    quotes = [
        QuotePart(role="instructions", text="Nesta prova, faça o que se pede."),
        QuotePart(role="task", text="The council gathered."),
    ]
    assert bind_quotes(original, quotes) is None


def test_agy_organizes_one_open_prompt_the_protocol_cannot_split(tmp_path: Path, monkeypatch, capsys):
    project = tmp_path / "proj"
    project.mkdir()
    store = Store(project / "data")
    store.save_revision(ExerciseRevision(
        label="1", prompt=[ContentBlock(text=MIXED)], interaction=RubricSpec(),
        status="needs_review", answer_origin="official"))
    store.save_revision(ExerciseRevision(
        label="2", prompt=[ContentBlock(text="What does the delegation present?")],
        interaction=BooleanSpec(correct=True), status="needs_review", answer_origin="official"))
    open_prompt = "QUESTÃO 2\n" + ("The debt arithmetic collapsed the competitive recycling of private bank loans. " * 12)
    store.save_revision(ExerciseRevision(
        label="3", prompt=[ContentBlock(text=open_prompt)], interaction=RubricSpec(),
        status="needs_review", answer_origin="official"))
    calls = []

    def fake(text: str) -> Organization:
        calls.append(text)
        cut = text.index("The debt")
        return Organization(confidence="high", reason="agy", parts=[
            PromptPart(role="heading", text=text[:cut]),
            PromptPart(role="task", text=text[cut:]),
        ])

    monkeypatch.setattr("vengine.cli.shutil.which", lambda name: "/usr/bin/agy" if name == "agy" else None)
    monkeypatch.setattr("vengine.organize.ask_agy", fake)
    monkeypatch.setattr(sys, "argv", [
        "vengine", "--project", str(project), "organize", "--provider", "agy", "--apply"])
    main()
    assert calls == [open_prompt]
    stored = store.list_exercises(limit=10)
    mixed = next(item for item in stored if item.label == "1")
    assert "".join(part["text"] for part in mixed.metadata["organization"]) == MIXED
    opened = next(item for item in stored if item.label == "3")
    assert "".join(part["text"] for part in opened.metadata["organization"]) == open_prompt
    assert "organization" not in next(item for item in stored if item.label == "2").metadata
    assert "1\t3\thigh\tagy" in capsys.readouterr().err


def test_ask_agy_binds_verbatim_parts(monkeypatch):
    text = "Nesta prova, faça o que se pede.\n\nThe council met."
    monkeypatch.setattr("vengine.organize.shutil.which", lambda name: "/usr/bin/agy")

    def fake_run(command, **kwargs):
        payload = {"structured_output": {"parts": [
            {"role": "instructions", "text": "Nesta prova, faça o que se pede."},
            {"role": "task", "text": "The council met."},
        ]}}
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr("vengine.organize.subprocess.run", fake_run)
    result = ask_agy(text)
    assert result.confidence == "high"
    assert result.reason == "agy"
    assert "".join(part.text for part in result.parts) == text
    assert result.parts[-1].text == "The council met."


def test_uncertain_prompt_uses_agy_then_stays_unapplied_when_spans_fail(tmp_path: Path):
    store = Store(tmp_path / "data")
    text = "Nesta prova, faça o que se pede, utilizando o rascunho."
    saved = store.save_revision(ExerciseRevision(
        prompt=[ContentBlock(text=text)], interaction=RubricSpec(), status="needs_review"))

    def recover(prompt: str) -> Organization:
        cut = prompt.index(",")
        return Organization(confidence="high", reason="agy", parts=[
            PromptPart(role="instructions", text=prompt[:cut]),
            PromptPart(role="task", text=prompt[cut:]),
        ])

    report = organize_store(store, apply=True, resolve=recover)
    assert report["organized"] == 1 and report["applied"] == 1
    stored = store.latest(saved.exercise_id)
    assert stored.status == "needs_review"
    assert "".join(part["text"] for part in stored.metadata["organization"]) == text

    other = Store(tmp_path / "other")
    kept = other.save_revision(ExerciseRevision(
        prompt=[ContentBlock(text=text)], interaction=RubricSpec(), status="needs_review"))
    missed = organize_store(other, apply=True, resolve=lambda prompt: Organization(confidence="review", reason="bad spans"))
    assert missed["uncertain"] == 1 and missed["applied"] == 0
    assert "organization" not in other.latest(kept.exercise_id).metadata
