"""Local project storage. Every app owns its own database and immutable source bytes."""

from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
from pathlib import Path
from typing import Any

from .models import (
    Attempt,
    DocumentIR,
    DocumentPage,
    ExerciseRevision,
    ImportJob,
    PassageRevision,
    new_id,
    now,
)


def _has_official_answer(item: ExerciseRevision) -> bool:
    if item.answer_origin != "official":
        return False
    spec = item.interaction
    if spec.kind == "boolean":
        return spec.correct is not None
    if spec.kind == "choice":
        return bool(spec.correct)
    return False


class Store:
    def __init__(self, root: Path):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "sources").mkdir(exist_ok=True)
        self.db = self.root / "project.sqlite3"
        self._backup_before_migration()
        self.init_schema()

    def _backup_before_migration(self) -> None:
        if not self.db.exists():
            return
        with sqlite3.connect(f"{self.db.as_uri()}?mode=ro", uri=True) as source:
            version = source.execute("PRAGMA user_version").fetchone()[0]
            if version >= 4:
                return
            backup = self.root / ("project.sqlite3.pre-v3.bak" if version < 3
                                  else "project.sqlite3.pre-v4.bak")
            if backup.exists():
                return
            with sqlite3.connect(backup) as target:
                source.backup(target)

    def connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.db, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA busy_timeout=30000")
        return db

    def init_schema(self) -> None:
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS sources (
                    id TEXT PRIMARY KEY, sha256 TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
                    media_type TEXT NOT NULL, size INTEGER NOT NULL, path TEXT NOT NULL,
                    added_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS documents (
                    source_id TEXT PRIMARY KEY REFERENCES sources(id), body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS document_pages (
                    source_id TEXT NOT NULL REFERENCES sources(id), page INTEGER NOT NULL,
                    body TEXT NOT NULL, PRIMARY KEY(source_id, page));
                CREATE TABLE IF NOT EXISTS collections (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS revisions (
                    id TEXT PRIMARY KEY, exercise_id TEXT NOT NULL, revision INTEGER NOT NULL,
                    collection_id TEXT REFERENCES collections(id), status TEXT NOT NULL,
                    subject TEXT NOT NULL, body TEXT NOT NULL,
                    UNIQUE(exercise_id, revision));
                CREATE INDEX IF NOT EXISTS revisions_by_exercise ON revisions(exercise_id, revision DESC);
                CREATE INDEX IF NOT EXISTS revisions_by_status ON revisions(status, collection_id);
                CREATE TABLE IF NOT EXISTS passages (
                    id TEXT PRIMARY KEY, passage_id TEXT NOT NULL, revision INTEGER NOT NULL,
                    collection_id TEXT NOT NULL REFERENCES collections(id), status TEXT NOT NULL,
                    body TEXT NOT NULL, UNIQUE(passage_id, revision));
                CREATE INDEX IF NOT EXISTS passages_by_identity ON passages(passage_id, revision DESC);
                CREATE TABLE IF NOT EXISTS attempts (
                    id TEXT PRIMARY KEY, exercise_id TEXT NOT NULL, revision_id TEXT NOT NULL
                    REFERENCES revisions(id), body TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS attempts_by_exercise ON attempts(exercise_id, created_at DESC);
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES sources(id),
                    stage TEXT NOT NULL, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS marks (
                    exercise_id TEXT PRIMARY KEY, starred INTEGER NOT NULL DEFAULT 0,
                    note TEXT NOT NULL DEFAULT '');
                CREATE TABLE IF NOT EXISTS schedule (
                    exercise_id TEXT PRIMARY KEY, card_json TEXT NOT NULL, due TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS assessments (
                    attempt_id TEXT PRIMARY KEY REFERENCES attempts(id), rating INTEGER NOT NULL,
                    created_at TEXT NOT NULL);
                CREATE VIRTUAL TABLE IF NOT EXISTS exercise_search USING fts5(
                    exercise_id UNINDEXED, title, subject, body, tokenize='unicode61');
            """)
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version < 2:
                db.execute("DELETE FROM exercise_search")
                rows = db.execute("""SELECT r.body FROM revisions r WHERE r.status='approved'
                    AND r.revision=(SELECT MAX(x.revision) FROM revisions x
                                    WHERE x.exercise_id=r.exercise_id AND x.status='approved')""").fetchall()
                for row in rows:
                    self._index(db, ExerciseRevision.model_validate_json(row[0]))
                db.execute("PRAGMA user_version=2")
            if version < 3:
                db.execute("PRAGMA user_version=3")
            if version < 4:
                db.execute("PRAGMA user_version=4")

    def add_source(self, path: Path, media_type: str = "application/octet-stream",
                   display_name: str | None = None) -> dict[str, Any]:
        path = Path(path)
        digest = hashlib.sha256()
        size = 0
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                size += len(chunk)
                digest.update(chunk)
        sha = digest.hexdigest()
        target = self.root / "sources" / sha
        with self.connect() as db:
            existing = db.execute("SELECT * FROM sources WHERE sha256=?", (sha,)).fetchone()
            if existing:
                return dict(existing)
            temporary = target.with_name(target.name + ".tmp." + new_id())
            try:
                shutil.copyfile(path, temporary)
                if hashlib.sha256(temporary.read_bytes()).hexdigest() != sha:
                    raise ValueError("source changed while copying")
                os.replace(temporary, target)
            finally:
                temporary.unlink(missing_ok=True)
            record = (new_id(), sha, display_name or path.name, media_type, size,
                      str(target), now().isoformat())
            db.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?)", record)
            return dict(db.execute("SELECT * FROM sources WHERE id=?", (record[0],)).fetchone())

    def source(self, source_id: str) -> dict[str, Any] | None:
        with self.connect() as db:
            row = db.execute("SELECT * FROM sources WHERE id=?", (source_id,)).fetchone()
            return self._located_source(dict(row)) if row else None

    def _located_source(self, item: dict[str, Any]) -> dict[str, Any]:
        """Resolve a stored source path against this project's data directory."""
        path = Path(item["path"])
        portable = self.root / "sources" / item["sha256"]
        if not path.is_absolute():
            item["path"] = str((self.root / path).resolve())
        elif not path.exists() and portable.exists():
            item["path"] = str(portable.resolve())
        return item

    def save_document(self, document: DocumentIR) -> None:
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO documents VALUES (?,?)",
                       (document.source_id, document.model_dump_json()))

    def document(self, source_id: str) -> DocumentIR | None:
        with self.connect() as db:
            row = db.execute("SELECT body FROM documents WHERE source_id=?", (source_id,)).fetchone()
            return DocumentIR.model_validate_json(row[0]) if row else None

    def save_document_page(self, source_id: str, page: DocumentPage) -> None:
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO document_pages VALUES (?,?,?)",
                       (source_id, page.number, page.model_dump_json()))

    def document_pages(self, source_id: str) -> list[DocumentPage]:
        with self.connect() as db:
            rows = db.execute("SELECT body FROM document_pages WHERE source_id=? ORDER BY page",
                              (source_id,)).fetchall()
        return [DocumentPage.model_validate_json(row[0]) for row in rows]

    def create_collection(self, name: str, description: str = "", collection_id: str | None = None) -> str:
        collection_id = collection_id or new_id()
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO collections VALUES (?,?,?,?)",
                       (collection_id, name, description, now().isoformat()))
        return collection_id

    def collections(self) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = [dict(row) for row in db.execute("SELECT * FROM collections ORDER BY created_at DESC")]
            counts = self._collection_counts(db)
        for row in rows:
            row.update(counts.get(row["id"], {"total": 0, "answered": 0, "correct": 0}))
        return rows

    def _collection_counts(self, db: sqlite3.Connection) -> dict[str, dict[str, int]]:
        approved = """r.status='approved' AND r.collection_id IS NOT NULL
            AND r.revision=(SELECT MAX(x.revision) FROM revisions x
                            WHERE x.exercise_id=r.exercise_id AND x.status='approved')"""
        latest = """a.rowid=(SELECT a2.rowid FROM attempts a2
                   WHERE a2.exercise_id=r.exercise_id
                   ORDER BY a2.created_at DESC, a2.rowid DESC LIMIT 1)"""
        totals = dict(db.execute(
            f"SELECT r.collection_id, COUNT(*) FROM revisions r WHERE {approved} GROUP BY r.collection_id"
        ).fetchall())
        progress = db.execute(
            f"""SELECT r.collection_id, COUNT(*),
                       SUM(CASE WHEN json_extract(a.body, '$.grade.outcome')='correct' THEN 1 ELSE 0 END)
                FROM revisions r JOIN attempts a ON a.exercise_id=r.exercise_id
                WHERE {approved} AND {latest}
                GROUP BY r.collection_id"""
        ).fetchall()
        counts = {key: {"total": value, "answered": 0, "correct": 0} for key, value in totals.items()}
        for collection_id, answered, correct in progress:
            counts.setdefault(collection_id, {"total": 0, "answered": 0, "correct": 0})
            counts[collection_id]["answered"] = answered
            counts[collection_id]["correct"] = correct or 0
        return counts

    def practice_states(self, exercise_ids: list[str]) -> dict[str, dict[str, Any]]:
        if not exercise_ids:
            return {}
        marks = ",".join("?" * len(exercise_ids))
        with self.connect() as db:
            starred = dict(db.execute(
                f"SELECT exercise_id, starred FROM marks WHERE exercise_id IN ({marks})",
                exercise_ids,
            ).fetchall())
            outcomes = dict(db.execute(
                f"""SELECT a.exercise_id, json_extract(a.body, '$.grade.outcome')
                    FROM attempts a
                    WHERE a.exercise_id IN ({marks})
                      AND a.rowid=(SELECT a2.rowid FROM attempts a2
                                   WHERE a2.exercise_id=a.exercise_id
                                   ORDER BY a2.created_at DESC, a2.rowid DESC LIMIT 1)""",
                exercise_ids,
            ).fetchall())
        return {
            exercise_id: {
                "starred": bool(starred.get(exercise_id, 0)),
                "last_outcome": outcomes.get(exercise_id),
            }
            for exercise_id in exercise_ids
        }

    def save_revision(self, item: ExerciseRevision) -> ExerciseRevision:
        with self.connect() as db:
            self._insert_revision(db, item)
        return item

    def _insert_revision(self, db: sqlite3.Connection, item: ExerciseRevision) -> None:
        previous = db.execute("SELECT MAX(revision) FROM revisions WHERE exercise_id=?",
                              (item.exercise_id,)).fetchone()[0]
        if item.revision != (previous or 0) + 1:
            raise ValueError("revisions must be sequential and immutable")
        db.execute("INSERT INTO revisions VALUES (?,?,?,?,?,?,?)",
                   (item.id, item.exercise_id, item.revision, item.collection_id,
                    item.status, item.subject, item.model_dump_json()))
        if item.status == "approved":
            self._index(db, item)

    def save_passage(self, passage: PassageRevision) -> PassageRevision:
        with self.connect() as db:
            previous = db.execute("SELECT MAX(revision) FROM passages WHERE passage_id=?",
                                  (passage.passage_id,)).fetchone()[0]
            if passage.revision != (previous or 0) + 1:
                raise ValueError("passage revisions must be sequential and immutable")
            db.execute("INSERT INTO passages VALUES (?,?,?,?,?,?)",
                       (passage.id, passage.passage_id, passage.revision,
                        passage.collection_id, passage.status, passage.model_dump_json()))
        return passage

    def latest_passage(self, passage_id: str) -> PassageRevision | None:
        with self.connect() as db:
            row = db.execute("SELECT body FROM passages WHERE passage_id=? ORDER BY revision DESC LIMIT 1",
                             (passage_id,)).fetchone()
        return PassageRevision.model_validate_json(row[0]) if row else None

    def get_passage_revision(self, revision_id: str) -> PassageRevision | None:
        with self.connect() as db:
            row = db.execute("SELECT body FROM passages WHERE id=?", (revision_id,)).fetchone()
        return PassageRevision.model_validate_json(row[0]) if row else None

    def revise_passage(self, passage_id: str, *, title: str, blocks: list) -> PassageRevision:
        prior = self.latest_passage(passage_id)
        if prior is None:
            raise KeyError(passage_id)
        if prior.status == "needs_review" and prior.revision > 1:
            raise ValueError("Approve the pending passage edit first")
        changed = prior.model_copy(update={"id": new_id(), "revision": prior.revision + 1,
                                           "title": title, "blocks": blocks,
                                           "status": "needs_review", "approved_at": None,
                                           "created_at": now()})
        return self.save_passage(changed)

    def approve_passage(self, revision_id: str) -> PassageRevision:
        """Publish one shared text and snapshot it into all current linked questions."""
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT body FROM passages WHERE id=?", (revision_id,)).fetchone()
            if not row:
                raise KeyError(revision_id)
            passage = PassageRevision.model_validate_json(row[0])
            latest = db.execute("SELECT id FROM passages WHERE passage_id=? ORDER BY revision DESC LIMIT 1",
                                (passage.passage_id,)).fetchone()[0]
            if latest != revision_id or passage.status == "archived":
                raise ValueError("Only the latest active passage can be approved")
            if passage.status == "approved":
                return passage
            passage = passage.model_copy(update={"status": "approved", "approved_at": now()})
            db.execute("UPDATE passages SET status=?, body=? WHERE id=?",
                       (passage.status, passage.model_dump_json(), passage.id))
            rows = db.execute("""SELECT r.body FROM revisions r WHERE
                r.revision=(SELECT MAX(x.revision) FROM revisions x WHERE x.exercise_id=r.exercise_id)
                AND r.collection_id=?""", (passage.collection_id,)).fetchall()
            for row in rows:
                item = ExerciseRevision.model_validate_json(row[0])
                if item.passage_id != passage.passage_id or item.status == "archived":
                    continue
                updated = item.model_copy(update={
                    "id": new_id(), "revision": item.revision + 1,
                    "contexts": passage.blocks, "passage_revision_id": passage.id,
                    "created_at": now(),
                    "approved_at": now() if item.status == "approved" else None,
                })
                self._insert_revision(db, updated)
        return passage

    def _index(self, db: sqlite3.Connection, item: ExerciseRevision) -> None:
        db.execute("DELETE FROM exercise_search WHERE exercise_id=?", (item.exercise_id,))
        text = " ".join(block.text for block in item.prompt + item.contexts)
        db.execute("INSERT INTO exercise_search VALUES (?,?,?,?)",
                   (item.exercise_id, item.title, item.subject, text))

    def get_revision(self, revision_id: str) -> ExerciseRevision | None:
        with self.connect() as db:
            row = db.execute("SELECT body FROM revisions WHERE id=?", (revision_id,)).fetchone()
            return ExerciseRevision.model_validate_json(row[0]) if row else None

    def latest(self, exercise_id: str) -> ExerciseRevision | None:
        with self.connect() as db:
            row = db.execute("SELECT body FROM revisions WHERE exercise_id=? ORDER BY revision DESC LIMIT 1",
                             (exercise_id,)).fetchone()
            return ExerciseRevision.model_validate_json(row[0]) if row else None

    def published(self, exercise_id: str) -> ExerciseRevision | None:
        with self.connect() as db:
            row = db.execute("""SELECT body FROM revisions WHERE exercise_id=? AND status='approved'
                                ORDER BY revision DESC LIMIT 1""", (exercise_id,)).fetchone()
            return ExerciseRevision.model_validate_json(row[0]) if row else None

    def revise(self, exercise_id: str, changes: dict[str, Any]) -> ExerciseRevision:
        prior = self.latest(exercise_id)
        if prior is None:
            raise KeyError(exercise_id)
        data = prior.model_dump(mode="json")
        data.update(changes)
        data.update(id=new_id(), revision=prior.revision + 1, status="needs_review",
                    approved_at=None, created_at=now().isoformat())
        return self.save_revision(ExerciseRevision.model_validate(data))

    def set_organization(self, exercise_id: str, parts: list[dict[str, Any]]) -> ExerciseRevision:
        """Store a prompt partition on the current revision without changing its words or status."""
        from .organize import parts_match, prompt_text

        prior = self.latest(exercise_id)
        if prior is None:
            raise KeyError(exercise_id)
        if not parts_match(prompt_text(prior), parts):
            raise ValueError("organization does not match the original prompt")
        metadata = dict(prior.metadata)
        metadata["organization"] = parts
        item = prior.model_copy(update={"metadata": metadata})
        with self.connect() as db:
            db.execute("UPDATE revisions SET body=? WHERE id=?", (item.model_dump_json(), item.id))
            if item.status == "approved":
                self._index(db, item)
        return item

    def approve(self, revision_id: str) -> ExerciseRevision:
        with self.connect() as db:
            row = db.execute("SELECT body FROM revisions WHERE id=?", (revision_id,)).fetchone()
            if not row:
                raise KeyError(revision_id)
            item = ExerciseRevision.model_validate_json(row[0])
            if item.status == "archived":
                raise ValueError("archived revision cannot be approved")
            if item.metadata.get("annulled"):
                raise ValueError("Annulled item cannot be approved for scored practice")
            if item.passage_id:
                passage = db.execute("SELECT body FROM passages WHERE id=?",
                                     (item.passage_revision_id,)).fetchone()
                if not passage or PassageRevision.model_validate_json(passage[0]).status != "approved":
                    raise ValueError("Approve the shared text before this question")
            if item.interaction.kind == "choice" and not item.interaction.correct:
                raise ValueError("Set a verified answer before approval")
            if item.interaction.kind == "boolean" and item.interaction.correct is None:
                raise ValueError("Set a verified answer before approval")
            latest = db.execute("SELECT id FROM revisions WHERE exercise_id=? ORDER BY revision DESC LIMIT 1",
                                (item.exercise_id,)).fetchone()[0]
            if latest != revision_id:
                raise ValueError("only the latest revision can be approved")
            if item.status == "approved":
                return item
            item = item.model_copy(update={"status": "approved", "approved_at": now()})
            db.execute("UPDATE revisions SET status=?, body=? WHERE id=?",
                       (item.status, item.model_dump_json(), item.id))
            self._index(db, item)
        return item

    def accept_official(self) -> dict[str, int]:
        """Approve passages, then review drafts that already carry an official answer.

        Annulled drafts and items without a verified C/E or boolean answer stay in review.
        This does not invent or replace answers.
        """
        pending = self._all_latest("needs_review")
        publishable: list[ExerciseRevision] = []
        skipped_annulled = 0
        skipped_open = 0
        for item in pending:
            if item.metadata.get("annulled"):
                skipped_annulled += 1
            elif _has_official_answer(item):
                publishable.append(item)
            else:
                skipped_open += 1
        passages = 0
        seen: set[str] = set()
        for item in publishable:
            if not item.passage_id or item.passage_id in seen:
                continue
            seen.add(item.passage_id)
            passage = self.latest_passage(item.passage_id)
            if passage is None or passage.status == "approved":
                continue
            self.approve_passage(passage.id)
            passages += 1
        accepted = 0
        for item in publishable:
            latest = self.latest(item.exercise_id)
            if latest is None or latest.status == "approved":
                continue
            if latest.metadata.get("annulled") or not _has_official_answer(latest):
                continue
            self.approve(latest.id)
            accepted += 1
        return {"passages": passages, "accepted": accepted,
                "skipped_annulled": skipped_annulled, "skipped_open": skipped_open}

    def _all_latest(self, status: str) -> list[ExerciseRevision]:
        items: list[ExerciseRevision] = []
        offset = 0
        while True:
            page = self.list_exercises(status, limit=500, offset=offset)
            items.extend(page)
            if len(page) < 500:
                return items
            offset += len(page)

    def archive_review(self, revision_ids: list[str]) -> int:
        """Discard only current review drafts; keep earlier published revisions intact."""
        if not revision_ids or len(revision_ids) > 100 or len(set(revision_ids)) != len(revision_ids):
            raise ValueError("Select between 1 and 100 distinct review drafts")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            drafts = []
            for revision_id in revision_ids:
                row = db.execute("SELECT body FROM revisions WHERE id=?", (revision_id,)).fetchone()
                if row is None:
                    raise KeyError(revision_id)
                item = ExerciseRevision.model_validate_json(row[0])
                latest = db.execute("SELECT id FROM revisions WHERE exercise_id=? ORDER BY revision DESC LIMIT 1",
                                    (item.exercise_id,)).fetchone()[0]
                if item.status != "needs_review" or latest != revision_id:
                    raise ValueError("Only current review drafts can be discarded")
                drafts.append(item)
            for item in drafts:
                archived = item.model_copy(update={"status": "archived"})
                db.execute("UPDATE revisions SET status=?, body=? WHERE id=?",
                           (archived.status, archived.model_dump_json(), item.id))
        return len(drafts)

    def list_exercises(self, status: str | None = None, collection_id: str | None = None,
                       limit: int = 100, offset: int = 0) -> list[ExerciseRevision]:
        if status == "approved":
            clauses = ["r.status='approved'", "r.revision=(SELECT MAX(x.revision) FROM revisions x WHERE x.exercise_id=r.exercise_id AND x.status='approved')"]
        else:
            clauses = ["r.revision=(SELECT MAX(x.revision) FROM revisions x WHERE x.exercise_id=r.exercise_id)"]
        args: list[Any] = []
        if status:
            clauses.append("r.status=?")
            args.append(status)
        if collection_id:
            clauses.append("r.collection_id=?")
            args.append(collection_id)
        sql = "SELECT r.body FROM revisions r WHERE " + " AND ".join(clauses)
        sql += " ORDER BY r.rowid DESC LIMIT ? OFFSET ?"
        with self.connect() as db:
            rows = db.execute(sql, (*args, min(limit, 500), offset)).fetchall()
            return [ExerciseRevision.model_validate_json(row[0]) for row in rows]

    def search(self, query: str, limit: int = 50) -> list[ExerciseRevision]:
        if not query.strip():
            return []
        with self.connect() as db:
            try:
                rows = db.execute("SELECT exercise_id FROM exercise_search WHERE exercise_search MATCH ? LIMIT ?",
                                  (query, min(limit, 100))).fetchall()
            except sqlite3.OperationalError:
                return []
        return [item for row in rows if (item := self.published(row[0])) is not None]

    def record_attempt(self, attempt: Attempt) -> None:
        from fsrs import Rating

        with self.connect() as db:
            db.execute("INSERT INTO attempts VALUES (?,?,?,?,?)",
                       (attempt.id, attempt.exercise_id, attempt.revision_id,
                        attempt.model_dump_json(), attempt.created_at.isoformat()))
            rating = {"correct": Rating.Good, "partial": Rating.Hard,
                      "incorrect": Rating.Again}.get(attempt.grade.outcome)
            if rating:
                self._schedule(db, attempt.exercise_id, rating, attempt.created_at)

    @staticmethod
    def _schedule(db: sqlite3.Connection, exercise_id: str, rating: Any, at: Any) -> None:
        from fsrs import Card, Scheduler

        row = db.execute("SELECT card_json FROM schedule WHERE exercise_id=?",
                         (exercise_id,)).fetchone()
        card = Card.from_json(row[0]) if row else Card()
        card, _ = Scheduler().review_card(card, rating, review_datetime=at)
        db.execute("INSERT OR REPLACE INTO schedule VALUES (?,?,?)",
                   (exercise_id, card.to_json(), card.due.isoformat()))

    def assess(self, attempt_id: str, rating: int) -> dict[str, Any]:
        from fsrs import Rating

        if rating not in {1, 2, 3, 4}:
            raise ValueError("Rating must be 1-4")
        with self.connect() as db:
            row = db.execute("SELECT body FROM attempts WHERE id=?", (attempt_id,)).fetchone()
            if row is None:
                raise KeyError(attempt_id)
            attempt = Attempt.model_validate_json(row[0])
            if attempt.grade.outcome != "ungraded":
                raise ValueError("Only open responses can be self-assessed")
            if db.execute("SELECT 1 FROM assessments WHERE attempt_id=?", (attempt_id,)).fetchone():
                raise ValueError("This attempt was already assessed")
            at = now()
            db.execute("INSERT INTO assessments VALUES (?,?,?)", (attempt_id, rating, at.isoformat()))
            self._schedule(db, attempt.exercise_id, Rating(rating), at)
            return {"attempt_id": attempt_id, "rating": rating,
                    "due": db.execute("SELECT due FROM schedule WHERE exercise_id=?",
                                      (attempt.exercise_id,)).fetchone()[0]}

    def due_exercises(self, limit: int = 100, offset: int = 0) -> list[ExerciseRevision]:
        with self.connect() as db:
            rows = db.execute("""SELECT r.body FROM revisions r
                LEFT JOIN schedule s ON s.exercise_id=r.exercise_id
                WHERE r.status='approved'
                  AND r.revision=(SELECT MAX(x.revision) FROM revisions x WHERE x.exercise_id=r.exercise_id AND x.status='approved')
                  AND (s.due IS NULL OR s.due<=?)
                ORDER BY CASE WHEN s.due IS NULL THEN 1 ELSE 0 END, s.due
                LIMIT ? OFFSET ?""", (now().isoformat(), min(limit, 500), offset)).fetchall()
        return [ExerciseRevision.model_validate_json(row[0]) for row in rows]

    def attempts(self, exercise_id: str | None = None, limit: int = 100) -> list[Attempt]:
        with self.connect() as db:
            if exercise_id:
                rows = db.execute("SELECT body FROM attempts WHERE exercise_id=? ORDER BY created_at DESC LIMIT ?",
                                  (exercise_id, min(limit, 500))).fetchall()
            else:
                rows = db.execute("SELECT body FROM attempts ORDER BY created_at DESC LIMIT ?",
                                  (min(limit, 500),)).fetchall()
        return [Attempt.model_validate_json(row[0]) for row in rows]

    def save_job(self, job: ImportJob) -> None:
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO jobs VALUES (?,?,?,?)",
                       (job.id, job.source_id, job.stage, job.model_dump_json()))

    def job(self, job_id: str) -> ImportJob | None:
        with self.connect() as db:
            row = db.execute("SELECT body FROM jobs WHERE id=?", (job_id,)).fetchone()
            return ImportJob.model_validate_json(row[0]) if row else None

    def jobs(self) -> list[ImportJob]:
        with self.connect() as db:
            return [ImportJob.model_validate_json(row[0]) for row in
                    db.execute("SELECT body FROM jobs ORDER BY rowid DESC")]

    def mark(self, exercise_id: str, *, starred: bool | None = None, note: str | None = None) -> dict[str, Any]:
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO marks(exercise_id) VALUES (?)", (exercise_id,))
            if starred is not None:
                db.execute("UPDATE marks SET starred=? WHERE exercise_id=?", (int(starred), exercise_id))
            if note is not None:
                db.execute("UPDATE marks SET note=? WHERE exercise_id=?", (note, exercise_id))
            return dict(db.execute("SELECT * FROM marks WHERE exercise_id=?", (exercise_id,)).fetchone())

    def stats(self) -> dict[str, Any]:
        with self.connect() as db:
            return {
                "sources": db.execute("SELECT COUNT(*) FROM sources").fetchone()[0],
                "collections": db.execute("SELECT COUNT(*) FROM collections").fetchone()[0],
                "approved": db.execute("SELECT COUNT(DISTINCT exercise_id) FROM revisions WHERE status='approved'").fetchone()[0],
                "review": db.execute("SELECT COUNT(*) FROM revisions r WHERE status='needs_review' AND revision=(SELECT MAX(revision) FROM revisions WHERE exercise_id=r.exercise_id)").fetchone()[0],
                "attempts": db.execute("SELECT COUNT(*) FROM attempts").fetchone()[0],
            }
