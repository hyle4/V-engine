"""Recoverable import pipeline with visible stage checkpoints."""

from __future__ import annotations

from pathlib import Path

from . import ai, documents, extract
from .models import ExerciseRevision, ImportJob
from .plugins import propose as propose_custom
from .store import Store


def queue_source(store: Store, path: Path, *, name: str | None = None,
                 generate_ai: bool = False, provider: str = "gemini",
                 count: int = 8, proposer: str = "builtin",
                 subject: str = "General", mode: str = "study",
                 answer_path: Path | None = None, title: str | None = None) -> ImportJob:
    path = Path(path)
    if path.suffix.lower() not in documents.supported_formats():
        raise ValueError(f"Unsupported source format: {path.suffix}")
    if mode not in {"study", "originals"}:
        raise ValueError("Import mode must be study or originals")
    if mode == "study" and answer_path is not None:
        raise ValueError("Answer keys require originals mode")
    if mode == "originals" and generate_ai:
        raise ValueError("Original exam import does not generate questions")
    source = store.add_source(path, documents.media_type(path),
                              display_name=(name + path.suffix) if name else None)
    answer_source = store.add_source(answer_path, documents.media_type(answer_path)) if answer_path else None
    original_collection = None
    for job in store.jobs():
        if job.source_id == source["id"] and job.mode == "originals" and job.stage == "review_ready":
            original_collection = job.collection_id
        if (job.source_id == source["id"] and job.stage == "review_ready" and job.mode == mode
                and job.answer_source_id == (answer_source["id"] if answer_source else None)
                and not generate_ai and job.proposer == proposer and job.subject == subject):
            return job
    job = ImportJob(source_id=source["id"], mode=mode,
                    answer_source_id=answer_source["id"] if answer_source else None,
                    title=title, collection_id=original_collection if mode == "originals" else None,
                    generate_ai=generate_ai,
                    provider=provider, count=count, proposer=proposer, subject=subject)
    store.save_job(job)
    return job


def import_source(store: Store, path: Path, *, name: str | None = None,
                  generate_ai: bool = False, provider: str = "gemini",
                  count: int = 8, proposer: str = "builtin",
                  subject: str = "General", mode: str = "study",
                  answer_path: Path | None = None, title: str | None = None) -> ImportJob:
    job = queue_source(store, path, name=name, generate_ai=generate_ai,
                       provider=provider, count=count, proposer=proposer, subject=subject,
                       mode=mode, answer_path=answer_path, title=title)
    if job.stage != "review_ready":
        run_job(store, job.id, name=name)
    return store.job(job.id)


def run_job(store: Store, job_id: str, *, name: str | None = None) -> ImportJob:
    job = store.job(job_id)
    if job is None:
        raise KeyError(job_id)
    if job.stage in {"review_ready", "cancelled"}:
        return job
    source = store.source(job.source_id)
    if source is None:
        raise KeyError(job.source_id)
    try:
        job = job.model_copy(update={"stage": "extracting", "progress": .2, "error": None})
        store.save_job(job)
        document = store.document(job.source_id)
        if document is None:
            def checkpoint(page, total):
                current = store.job(job_id)
                if current and current.stage == "cancelled":
                    raise RuntimeError("Import cancelled")
                store.save_document_page(job.source_id, page)
                if current:
                    store.save_job(current.model_copy(update={"progress": .2 + .35 * page.number / total}))

            document = documents.parse(Path(source["path"]), source["id"], source["name"],
                                       cached_pages=store.document_pages(job.source_id),
                                       on_page=checkpoint)
            store.save_document(document)
        if (current := store.job(job_id)) and current.stage == "cancelled":
            return current
        collection = job.collection_id or store.create_collection(
            job.title or name or Path(source["name"]).stem)
        job = job.model_copy(update={"stage": "generating", "progress": .6,
                                     "collection_id": collection})
        store.save_job(job)
        def record_usage(usage):
            current = store.job(job_id)
            if current:
                totals = {key: current.usage.get(key, 0) + value for key, value in usage.items()}
                store.save_job(current.model_copy(update={"usage": totals}))

        if job.mode == "originals":
            from .exam import extract_originals, propose_bundle
            answer_document = None
            if job.answer_source_id:
                answer_source = store.source(job.answer_source_id)
                answer_document = store.document(job.answer_source_id)
                if answer_document is None:
                    answer_document = documents.parse(Path(answer_source["path"]),
                                                      job.answer_source_id, answer_source["name"])
                    store.save_document(answer_document)
            passages, items = propose_bundle(extract_originals(document), document, collection,
                                             document.source_id, answers=answer_document,
                                             subject=job.subject)
            for passage in passages:
                if store.latest_passage(passage.passage_id) is None:
                    store.save_passage(passage)
        else:
            items = ai.generate(document, collection, provider=job.provider, count=job.count,
                                on_batch=record_usage) if job.generate_ai \
                else extract.propose(document, collection) if job.proposer == "builtin" \
                else propose_custom(job.proposer, document, collection)
        from uuid import NAMESPACE_URL, uuid5
        for index, item in enumerate(items):
            item = ExerciseRevision.model_validate(item)
            if item.subject == "General":
                item = item.model_copy(update={"subject": job.subject})
            if (current := store.job(job_id)) and current.stage == "cancelled":
                return current
            stable_id = uuid5(NAMESPACE_URL, f"vengine:original:{job.source_id}:{item.label}").hex \
                if job.mode == "originals" else uuid5(NAMESPACE_URL, f"vengine:{job.id}:{index}").hex
            prior = store.latest(stable_id)
            if prior:
                if job.mode == "originals" and item.answer_source and (
                        prior.answer_source != item.answer_source
                        or prior.interaction.kind == "choice" and
                        prior.interaction.correct != item.interaction.correct):
                    store.revise(stable_id, {
                        "interaction": prior.interaction.model_copy(update={
                            "correct": item.interaction.correct}).model_dump(mode="json"),
                        "answer_source": item.answer_source.model_dump(mode="json"),
                        "answer_origin": "official",
                    })
                continue
            item = item.model_copy(update={"exercise_id": stable_id,
                                            "metadata": {**item.metadata, "import_job_id": job.id}})
            store.save_revision(item)
        if (current := store.job(job_id)) and current.stage == "cancelled":
            return current
        job = store.job(job_id).model_copy(update={"stage": "review_ready", "progress": 1,
                                     "proposals_count": len(items)})
        store.save_job(job)
        return job
    except Exception as exc:
        if (current := store.job(job_id)) and current.stage == "cancelled":
            return current
        job = job.model_copy(update={"stage": "failed", "error": str(exc)[:500]})
        store.save_job(job)
        return job
