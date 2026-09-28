"""lab_answer._publish_page: a private question's answer never becomes a page students can read."""
from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from byeori import lab_answer

RECORD = {"question": "What does the wiki say?", "answer": "It says this.",
          "citations": [{"key": "wiki/sources/paper-one.md", "section": "Results"}],
          "limitations": [], "unresolved_items": [], "evidence_state": "sufficient", "status": "completed"}


class Writer:
    def __init__(self):
        self.puts: list[str] = []

    def get_markdown(self, key):
        return None

    def put_markdown(self, key, text, *, create_only=False, expected_etag=None):
        self.puts.append(key)


def run(job):
    return SimpleNamespace(pages=Writer(), job=job, job_id="j1", holds=[],
                           now=lambda: datetime(2026, 9, 26, tzinfo=UTC))


@pytest.mark.parametrize("job", [{"private_material": True, "period": "2026-09"}, {"period": "2026-09"}])
def test_a_private_or_unflagged_question_writes_no_page_and_no_hub(job):
    r = run(job)
    lab_answer._publish_page(r, RECORD)
    assert r.pages.puts == [] and r.holds == []


def test_a_public_question_writes_its_page_and_the_hub_of_what_it_cited():
    r = run({"private_material": False, "period": "2026-09"})
    lab_answer._publish_page(r, RECORD)
    assert r.pages.puts == ["wiki/lab-questions/2026-09/j1.md",
                            "wiki/lab-questions/by-page/sources/paper-one.md"]
