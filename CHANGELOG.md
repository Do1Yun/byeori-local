# Changelog

## Unreleased

Re-exported from the An Lab workspace on 2026-09-28 (see `RELEASE-SOURCE`).

- **Models.** `byeori deploy` writes notes and synthesis with Claude Opus 5.5 at `high` and keeps
  Claude Opus 5 as the fallback: a note or page Opus 5.5 declines is written by Opus 5 in the same
  call. `docs/COST.md` now gives measured per-note costs.
- **Long pages.** A synthesis page that needs more room is given it before the call.
- **Correcting a note.** `aws-revise-source-note` fixes a published note in place with exact
  replacements, refuses a note that changed since it was read, and records the reviser beside the
  first writer. An AWS rewrite of a note now names what wrote it.
- **Duplicates.** `aws-supersede-note` takes a preprint's note out once the published paper has its
  own and repoints every page that cited it.
- **Notes written outside AWS.** `aws-publish-source-note` publishes a note written in an agent
  session, recording the session's model and reasoning level and no invented token counts;
  `aws-set-note-reasoning` fills in the level on a note published before it was recorded.
- **Identity.** A conference paper is taken as a paper, and a PDF's own header can settle its
  identity once a registry holds it.
- **Student service.** Question pages and the line added to a cited note are written in English
  ("Questions Citing This Page"); a private question's answer is kept out of `wiki/lab-questions/`.
- **Supplementary files.** Only row-lookup tables of 10 MB or less are stored beside the note; the
  other files are recorded in the manifest.
- **Deploy.** The origin/main and contact-address checks in `scripts/deploy.sh` run only in the
  lab's own mode; a standalone install skips them.

## v0.1.0-beta.1 (2026-09-24)

Copyright 2026 Joon An and the An Lab, Apache-2.0. First public beta. Exported from the An Lab
workspace (see `RELEASE-SOURCE`).

Contains: the `byeori` package and CLI; the main stack (S3, DynamoDB, Lambda ingest and
synthesis, Fargate extraction, Step Functions, audit trail); the optional student service stack
and its MCP server; the optional Jev triage; installer commands `init`, `deploy`,
`build-workers`, `deploy-lab`, `deploy-jev-eval`, `grant-client`, `doctor`; `upload-pdf` for a
paper's original PDF; the journal policy as a data file.

Does not contain: a language setting for prompts (reserved as `BYEORI_LANGUAGE`); the lab's own
intake and repair tools; any shared or hosted instance.

Known limits of this beta:

- `build-workers` is unverified: the machine that verified this release had no Docker.
- A paper whose identity cannot be resolved against OpenAlex stays parked at
  `fulltext_ready_unclassified`; there is no per-paper fix yet.
- The student-facing offer messages, the lab-question page headings and the `byeori-lab` setup
  text are in Korean.
