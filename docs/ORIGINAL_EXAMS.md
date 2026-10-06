# Original exam intake

Originals mode transcribes exam items for review. It does not generate new questions. Input can be PDF, image, text, Markdown, JSON, or CSV; scans require Tesseract with the appropriate language data. The engine keeps original bytes, parsed pages, a collection, shared text revisions, question revisions, and attempts in the project's local `data/` directory.

## Direct import

```sh
vengine --project /path/to/project import /path/to/project/data/exam.pdf --mode originals --answers /path/to/project/data/key.pdf --title "Diplomacy exam · 2025"
```

The answer key is optional. Clear question headings and A–H alternatives become review drafts. Explicit text ranges such as “questões 1 a 3” bind a common reading text to those questions. A complete Cebraspe-style sequence of four C/E assertions under each `QUESTÃO` heading becomes four independent boolean items, labelled `1.1` through `1.4`. For a complete four-column official key grid, `C` means Certo, `E` means Errado, and `X` means annulled. An annulled item remains in review and cannot be approved for scored practice. Unclear numbering, OCR, layout, key mappings, and bindings require manual review. Import failure reports the reason and keeps the source; it does not create guessed items.
Importing the same exam again with a newly supplied official key reuses its collection and creates answer revisions for the existing questions.

## Assistant-corrected transcript

When the source layout defeats automatic parsing, the coding assistant prepares a UTF-8 JSON file under `data/staging/` with this `vengine-exam.v1` shape. This example is synthetic; it contains no real exam material.

```json
{
  "schema_version": 1,
  "title": "Sample diplomacy exam",
  "passages": [
    {
      "key": "text-1",
      "title": "Texto 1",
      "text": "A delegation presents a proposal and invites the council to discuss it.",
      "page": 1,
      "questions": [1, 2]
    }
  ],
  "questions": [
    {
      "number": 1,
      "page": 1,
      "prompt": "What does the delegation present?",
      "options": {"A": "A proposal", "B": "A treaty"},
      "answer": null,
      "passage_key": "text-1"
    },
    {
      "number": 2,
      "page": 1,
      "prompt": "Who is invited to discuss it?",
      "options": {"A": "The council", "B": "The press"},
      "answer": null,
      "passage_key": "text-1"
    }
  ]
}
```

For a C/E item in the same format, use `{"number": 3, "item": 1, "page": 2, "prompt": "...", "answer": null}`. The `item` field is 1–4; omit `options`. The answer may be `C`, `E`, or `X` after checking the official key. Passage keys and `(question number, item number)` pairs must be unique. Each linked question number must appear in that passage's `questions` list. `page` is the original source page, starting at 1. `options` maps original letters A–H to full text. Omit `options` for an open response. Leave `answer` null unless the answer has been checked; a separate official key takes precedence. Mismatches are review issues. All imported items begin in review.

```sh
vengine --project /path/to/project import-exam-json /path/to/project/data/staging/exam.json --source /path/to/project/data/exam.pdf --answers /path/to/project/data/key.pdf
```

Repeat ingestion of the same source and identical transcript is idempotent. A changed transcript represents a new import; make later corrections in review to preserve question identity. The assistant must compare every nonmatching prompt and answer with the original page before requesting approval.

## Review and practice

Each shared text has its own revision. Approve it before approving linked questions. Editing and approving a shared text creates new linked question revisions in one transaction, including for already published questions. Existing attempts still point to their earlier question revisions. The practice UI shows the text beside the question on wide screens and above it on narrow screens; the text can be hidden with the glyph control. Source and answer-key references remain available during review, while the answer key stays out of the pre-submit question response.

For an Itamaraty/CACD project, start with the learner's exam booklet and official gabarito, identify year and booklet in the collection title, then verify language passages, question ranges, and every official answer against those files. The public V-engine repository contains no CACD exam corpus.

## Verified real-file trial

The [official 2017 CACD morning booklet](https://cdn.cebraspe.org.br/concursos/IRBR_17_DIPLOMACIA/arquivos/327_IRBR_001_01.PDF) and [definitive key](https://cdn.cebraspe.org.br/concursos/IRBR_17_DIPLOMACIA/arquivos/Gab_Definitivo_327_IRBR_001_01.PDF) were downloaded into `/tmp` and imported into a separate local project. Extraction found 34 question groups, 136 C/E assertions, four shared reading texts, 40 assertions linked to those texts, and 136 key cells, including five annulments. The importer created 136 review drafts and no automatically approved questions. This confirms this booklet's text layer and grid layout; other years and booklet variants still need a trial import and source review. The source PDFs and transcribed questions are not part of the repository or package.
