"""Loopback API and bundled practice interface."""

from __future__ import annotations

import os
import shutil
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .documents import render_pdf_page
from .grading import grade
from .jobqueue import JobQueue
from .jobs import queue_source
from .models import Attempt, ContentBlock, ExerciseRevision, Interaction
from .organize import for_practice
from .project import ProjectConfig, load_project, save_project
from .store import Store


def _view(item: ExerciseRevision, *, reveal: bool) -> dict[str, Any]:
    view = item.public_view(reveal=reveal)
    organization = for_practice(item)
    if organization:
        view["organization"] = organization
    return view


class ReviewEdit(BaseModel):
    changes: dict[str, Any]


class Submission(BaseModel):
    response: Any


class MarkUpdate(BaseModel):
    starred: bool | None = None
    note: str | None = None


class Assessment(BaseModel):
    rating: int


class ArchiveBatch(BaseModel):
    revision_ids: list[str]


class PassageEdit(BaseModel):
    title: str
    text: str


class AuthorExercise(BaseModel):
    title: str = ""
    subject: str = "General"
    collection_id: str | None = None
    prompt: list[ContentBlock]
    interaction: Interaction


def create_app(root: Path, *, project_root: Path | None = None,
               web_root: Path | None = None) -> FastAPI:
    store = Store(root)
    queue = JobQueue(store)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        queue.recover()
        yield
        queue.close()

    app = FastAPI(title="V-engine", version="0.3.0", lifespan=lifespan)
    app.state.store = store
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])
    web = Path(web_root) if web_root is not None else Path(__file__).parent / "web"
    app.mount("/static", StaticFiles(directory=web), name="static")

    def available_providers() -> dict[str, bool]:
        from .plugins import ai_provider_names

        return {"gemini": bool(os.getenv("GEMINI_API_KEY")),
                "agy": bool(shutil.which("agy")),
                **{name: True for name in ai_provider_names() if name not in {"gemini", "agy"}}}

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        from fastapi.responses import JSONResponse
        origin = request.headers.get("origin")
        if request.method not in {"GET", "HEAD", "OPTIONS"} and origin:
            allowed = f"{request.url.scheme}://{request.headers.get('host')}"
            if origin != allowed:
                return JSONResponse({"detail": "Cross-origin write blocked"}, status_code=403)
        return await call_next(request)

    @app.get("/")
    def index():
        return FileResponse(web / "index.html")

    @app.get("/api/health")
    def health():
        return {"status": "ok", "stats": store.stats(),
                "providers": available_providers()}

    @app.get("/api/project")
    def project():
        config = load_project(project_root) if project_root else None
        return {"configured": config is not None, "editable": project_root is not None,
                "project": config.model_dump() if config else None}

    @app.put("/api/project")
    def update_project(config: ProjectConfig):
        if project_root is None:
            raise HTTPException(409, "Start with --project to configure this workspace")
        from .plugins import ai_provider_names, proposer_names

        if config.proposer not in proposer_names():
            raise HTTPException(422, "Unknown proposal adapter")
        if config.ai_provider not in {"auto", "none", *ai_provider_names()}:
            raise HTTPException(422, "Unknown AI provider")
        save_project(project_root, config)
        return {"configured": True, "editable": True, "project": config.model_dump()}

    @app.get("/api/capabilities")
    def capabilities():
        from .documents import supported_formats
        from .plugins import proposer_names
        from .runner import available_runners

        return {"formats": sorted(supported_formats()), "proposers": proposer_names(),
                "ocr": bool(shutil.which("tesseract")),
                "providers": available_providers(),
                "runners": available_runners()}

    @app.get("/api/project/options")
    def project_options():
        from .documents import supported_formats
        from .plugins import proposer_names

        return {"formats": sorted(supported_formats()), "proposers": proposer_names()}

    @app.get("/api/collections")
    def collections():
        return store.collections()

    @app.get("/api/sources/{source_id}/file")
    def source_file(source_id: str):
        source = store.source(source_id)
        if source is None:
            raise HTTPException(404, "Source not found")
        inline = source["media_type"] in {"application/pdf", "image/png", "image/jpeg", "image/webp"}
        return FileResponse(source["path"], media_type=source["media_type"],
                            filename=source["name"],
                            content_disposition_type="inline" if inline else "attachment",
                            headers={"X-Content-Type-Options": "nosniff"})

    @app.get("/api/sources/{source_id}/render/{page}")
    async def source_render(source_id: str, page: int):
        source = store.source(source_id)
        if source is None or page < 1:
            raise HTTPException(404, "Source not found")
        path = Path(source["path"])
        if path.suffix.lower() != ".pdf" and source["media_type"] != "application/pdf":
            raise HTTPException(404, "Page not found")
        try:
            png = await run_in_threadpool(render_pdf_page, path, page)
        except ValueError as exc:
            raise HTTPException(404, str(exc))
        return Response(content=png, media_type="image/png",
                        headers={"Cache-Control": "private, max-age=86400",
                                 "X-Content-Type-Options": "nosniff"})

    @app.get("/api/sources/{source_id}/pages/{page}")
    def source_page(source_id: str, page: int):
        source = store.source(source_id)
        document = store.document(source_id)
        if source is None or document is None:
            raise HTTPException(404, "Source not found")
        selected = next((item for item in document.pages if item.number == page), None)
        if selected is None:
            raise HTTPException(404, "Page not found")
        return {"source": {"id": source_id, "name": source["name"]},
                "page": selected.model_dump(mode="json")}

    @app.get("/api/exercises")
    def exercises(status: str = "approved", collection_id: str | None = None,
                  limit: int = 100, offset: int = 0, due: bool = False):
        if status not in {"approved", "needs_review", "draft", "archived"}:
            raise HTTPException(400, "Invalid status")
        items = store.due_exercises(limit, offset) if due and status == "approved" else \
            store.list_exercises(status, collection_id, limit, offset)
        states = store.practice_states([item.exercise_id for item in items]) if status == "approved" else {}
        views = []
        for item in items:
            view = _view(item, reveal=status != "approved")
            if status == "approved":
                extra = states.get(item.exercise_id, {})
                view["starred"] = bool(extra.get("starred"))
                view["last_outcome"] = extra.get("last_outcome")
            views.append(view)
        return views

    @app.post("/api/exercises")
    def create_exercise(body: AuthorExercise):
        item = ExerciseRevision(title=body.title, subject=body.subject,
                                collection_id=body.collection_id, prompt=body.prompt,
                                interaction=body.interaction, status="needs_review",
                                answer_origin="author",
                                review_notes=["Verify the prompt and answer before approval."])
        return store.save_revision(item).model_dump(mode="json")

    @app.get("/api/exercises/{exercise_id}")
    def exercise(exercise_id: str, review: bool = False):
        item = store.latest(exercise_id) if review else store.published(exercise_id)
        if item is None:
            raise HTTPException(404, "Exercise not found")
        if item.status != "approved" and not review:
            raise HTTPException(404, "Exercise not published")
        return _view(item, reveal=review)

    @app.post("/api/exercises/{exercise_id}/run")
    def run_sample(exercise_id: str, submission: Submission):
        item = store.published(exercise_id)
        if item is None or item.status != "approved":
            raise HTTPException(404, "Exercise not published")
        result = grade(item, submission.response, sample_only=True)
        return {"result": result.model_dump(mode="json")}

    @app.post("/api/exercises/{exercise_id}/submit")
    def submit(exercise_id: str, submission: Submission):
        item = store.published(exercise_id)
        if item is None or item.status != "approved":
            raise HTTPException(404, "Exercise not published")
        result = grade(item, submission.response)
        attempt = Attempt(exercise_id=item.exercise_id, revision_id=item.id,
                          response=submission.response, grade=result)
        store.record_attempt(attempt)
        return {"attempt": attempt.model_dump(mode="json"),
                "answer": item.public_view(reveal=True)["interaction"],
                "explanation": [block.model_dump(mode="json") for block in item.explanation]}

    @app.get("/api/exercises/{exercise_id}/attempts")
    def attempts(exercise_id: str):
        return [a.model_dump(mode="json") for a in store.attempts(exercise_id)]

    @app.post("/api/attempts/{attempt_id}/assess")
    def assess(attempt_id: str, body: Assessment):
        try:
            return store.assess(attempt_id, body.rating)
        except KeyError:
            raise HTTPException(404, "Attempt not found")
        except ValueError as exc:
            raise HTTPException(409, str(exc))

    @app.patch("/api/review/{exercise_id}")
    def edit(exercise_id: str, body: ReviewEdit):
        allowed = {"title", "label", "subject", "topics", "language", "prompt", "contexts",
                   "interaction", "sources", "explanation", "review_notes", "answer_origin", "metadata"}
        if not body.changes or not set(body.changes) <= allowed:
            raise HTTPException(400, "Invalid review fields")
        current = store.latest(exercise_id)
        if current and current.passage_id and "contexts" in body.changes:
            raise HTTPException(409, "Edit shared text through its passage review")
        try:
            return store.revise(exercise_id, body.changes).model_dump(mode="json")
        except KeyError:
            raise HTTPException(404, "Exercise not found")
        except ValueError as exc:
            raise HTTPException(422, str(exc))

    @app.post("/api/review/{revision_id}/approve")
    def approve(revision_id: str):
        try:
            return store.approve(revision_id).model_dump(mode="json")
        except KeyError:
            raise HTTPException(404, "Revision not found")
        except ValueError as exc:
            raise HTTPException(409, str(exc))

    @app.post("/api/review/archive")
    def archive_reviews(body: ArchiveBatch):
        try:
            return {"archived": store.archive_review(body.revision_ids)}
        except KeyError as exc:
            raise HTTPException(404, f"Revision not found: {exc.args[0]}")
        except ValueError as exc:
            raise HTTPException(409, str(exc))

    @app.get("/api/passages/{passage_id}")
    def passage(passage_id: str):
        item = store.latest_passage(passage_id)
        if item is None:
            raise HTTPException(404, "Shared text not found")
        return item.model_dump(mode="json")

    @app.patch("/api/review/passages/{passage_id}")
    def edit_passage(passage_id: str, body: PassageEdit):
        if not body.text.strip():
            raise HTTPException(422, "Shared text cannot be empty")
        try:
            prior = store.latest_passage(passage_id)
            if prior is None:
                raise KeyError(passage_id)
            source = prior.blocks[0].source if prior.blocks else None
            changed = store.revise_passage(passage_id, title=body.title.strip(),
                                           blocks=[ContentBlock(text=body.text.strip(), source=source)])
            return changed.model_dump(mode="json")
        except KeyError:
            raise HTTPException(404, "Shared text not found")
        except ValueError as exc:
            raise HTTPException(409, str(exc))

    @app.post("/api/review/passages/{revision_id}/approve")
    def approve_passage(revision_id: str):
        try:
            return store.approve_passage(revision_id).model_dump(mode="json")
        except KeyError:
            raise HTTPException(404, "Shared text revision not found")
        except ValueError as exc:
            raise HTTPException(409, str(exc))

    @app.post("/api/import")
    async def upload(file: Annotated[UploadFile, File()], generate_ai: bool | None = None,
                     provider: str | None = None, count: int | None = None,
                     mode: str = "study", title: str | None = None,
                     answer_file: Annotated[UploadFile | None, File()] = None):
        suffix = Path(file.filename or "").suffix.lower()
        from .documents import supported_formats
        if suffix not in supported_formats():
            raise HTTPException(415, "Unsupported file format")
        if mode not in {"study", "originals"}:
            raise HTTPException(422, "Invalid import mode")
        if answer_file and (mode != "originals" or Path(answer_file.filename or "").suffix.lower()
                            not in supported_formats()):
            raise HTTPException(422, "Answer key needs a supported file and originals mode")
        config = load_project(project_root) if project_root else None
        count = count if count is not None else (config.ai_count if config else 8)
        if not 1 <= count <= 30:
            raise HTTPException(400, "count must be between 1 and 30")
        preferred = config.ai_provider if config else "auto"
        selected_provider = provider or (preferred if preferred not in {"auto", "none"} else
                                         "gemini" if os.getenv("GEMINI_API_KEY") else "agy")
        providers = available_providers()
        if mode == "originals":
            generate_ai = False
            selected_provider = "none"
        elif selected_provider not in providers:
            raise HTTPException(422, "Unknown AI provider")
        if generate_ai is None:
            generate_ai = preferred != "none" and providers[selected_provider]
        if generate_ai and preferred == "none" and provider is None:
            raise HTTPException(409, "AI generation is disabled for this project")
        if generate_ai and not providers[selected_provider]:
            raise HTTPException(409, "Selected AI provider is not configured")
        answer_temp = None
        with tempfile.NamedTemporaryFile(suffix=suffix, prefix="vengine-upload-", delete=False) as tmp:
            temp_path = Path(tmp.name)
            try:
                size = 0
                while chunk := await file.read(1024 * 1024):
                    size += len(chunk)
                    if size > 100 * 1024 * 1024:
                        raise HTTPException(413, "Maximum upload size is 100 MB")
                    await run_in_threadpool(tmp.write, chunk)
                tmp.close()
                if answer_file:
                    answer_suffix = Path(answer_file.filename or "").suffix.lower()
                    with tempfile.NamedTemporaryFile(suffix=answer_suffix, prefix="vengine-key-",
                                                     delete=False) as key_tmp:
                        answer_temp = Path(key_tmp.name)
                        key_size = 0
                        while key_chunk := await answer_file.read(1024 * 1024):
                            key_size += len(key_chunk)
                            if key_size > 100 * 1024 * 1024:
                                raise HTTPException(413, "Maximum answer key size is 100 MB")
                            await run_in_threadpool(key_tmp.write, key_chunk)
                job = await run_in_threadpool(
                    queue_source, store, temp_path, name=Path(file.filename or "Source").stem,
                    generate_ai=generate_ai, provider=selected_provider, count=count,
                    proposer=config.proposer if config else "builtin",
                    subject=config.subject if config else "General", mode=mode,
                    answer_path=answer_temp, title=title)
                queue.submit(job.id)
                return job.model_dump(mode="json")
            finally:
                await file.close()
                if answer_file:
                    await answer_file.close()
                temp_path.unlink(missing_ok=True)
                if answer_temp:
                    answer_temp.unlink(missing_ok=True)

    @app.get("/api/jobs")
    def jobs():
        return [job.model_dump(mode="json") for job in store.jobs()]

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str):
        job = store.job(job_id)
        if job is None:
            raise HTTPException(404, "Job not found")
        return job.model_dump(mode="json")

    @app.post("/api/jobs/{job_id}/cancel")
    def cancel_job(job_id: str):
        try:
            return queue.cancel(job_id).model_dump(mode="json")
        except KeyError:
            raise HTTPException(404, "Job not found")

    @app.post("/api/jobs/{job_id}/resume")
    def resume_job(job_id: str):
        try:
            return queue.submit(job_id).model_dump(mode="json")
        except KeyError:
            raise HTTPException(404, "Job not found")

    @app.get("/api/search")
    def search(q: str):
        return [_view(item, reveal=False) for item in store.search(q) if item.status == "approved"]

    @app.put("/api/exercises/{exercise_id}/mark")
    def mark(exercise_id: str, body: MarkUpdate):
        if store.latest(exercise_id) is None:
            raise HTTPException(404, "Exercise not found")
        return store.mark(exercise_id, starred=body.starred, note=body.note)

    return app
