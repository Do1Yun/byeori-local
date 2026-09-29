"""What paper this is, asked of OpenAlex and accepted only when the PDF agrees.

GROBID reads what is printed on the page, and on a real journal PDF that is often not enough: the
lightweight CRF header model left the publication date empty on a Nature Communications paper
here, and read an arXiv stamp as the year on another. A note with no year cannot be placed in the
sequence of work it belongs to, which is most of what a reader wants from a wiki of papers.

So the extraction is checked against the same authority the AWS path uses, through the same
judgement: byeori.identity.judge decides whether a record is this paper, and a record that does
not agree is refused rather than attached. The lookup is optional and never blocks a note: when
it is off, unreachable or uncertain, the note carries what the extraction read and says so.
"""
from __future__ import annotations

import re
from urllib.parse import quote

import httpx

from byeori import identity, identity_resolve

OPENALEX_API = "https://api.openalex.org"
TEXT_HEAD_CHARS = 4000
DOI_IN_TEI = re.compile(r'<idno[^>]*type="DOI"[^>]*>([^<]+)</idno>', re.I)


class OpenAlexLookup:
    """Raw OpenAlex works, the shape identity_resolve.find expects to judge."""

    def __init__(self, url=OPENALEX_API, *, mailto=None, timeout=20.0, transport=None):
        self.url, self.mailto, self.timeout, self.transport = url.rstrip("/"), mailto, timeout, transport

    def _get(self, path, params):
        # OpenAlex asks callers to identify themselves; doing so is what keeps the shared pool fast.
        headers = {"User-Agent": f"byeori-local ({self.mailto})" if self.mailto else "byeori-local"}
        if self.mailto:
            params = dict(params, mailto=self.mailto)
        with httpx.Client(base_url=self.url, timeout=self.timeout, trust_env=False,
                          transport=self.transport, headers=headers) as client:
            response = client.get(path, params=params)
            response.raise_for_status()
            payload = response.json()
        return payload if isinstance(payload, dict) else {}

    def fetch_work(self, doi):
        doi = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)", "", str(doi or "").strip().lower())
        if not re.fullmatch(r"10\.\d{4,9}/\S+", doi):
            return None
        try:
            results = self._get("/works", {"filter": f"doi:https://doi.org/{quote(doi, safe='/')}",
                                           "per_page": 1}).get("results") or []
        except (httpx.HTTPError, ValueError):
            # A DOI OpenAlex does not hold is an answer, not a failure.
            return None
        return results[0] if results else None

    def search(self, query, year):
        if not query:
            return []
        params = {"search": query, "per_page": 10}
        if year:
            params["filter"] = f"from_publication_date:{year - 1}-01-01,to_publication_date:{year + 1}-12-31"
        try:
            return self._get("/works", params).get("results") or []
        except (httpx.HTTPError, ValueError):
            return []


def doi_in_tei(xml: bytes):
    found = DOI_IN_TEI.search(xml[:xml.find(b"</teiHeader>") + 1].decode("utf-8", "replace")
                              if b"</teiHeader>" in xml else "")
    return found[1].strip() if found else None


def text_head(blocks):
    return " ".join(block["text"] for block in blocks)[:TEXT_HEAD_CHARS]


def resolve(xml: bytes, stem: str, blocks, *, lookup):
    """The paper this extraction is, or why the question was left open.

    Never raises: a note is published whether or not its identity could be settled, and the note
    records which it was.
    """
    if lookup is None:
        return {"state": "disabled"}
    try:
        header = identity.parse_header(xml.decode("utf-8", "replace"))
        found = identity_resolve.find(header, stem, text_head(blocks), doi=doi_in_tei(xml),
                                      fetch_work=lookup.fetch_work, search=lookup.search)
    except Exception as exc:                              # noqa: BLE001 - never block a note
        return {"state": "unavailable", "error": f"{type(exc).__name__}: {exc}"}
    if found.get("state") != "found":
        return {"state": "not_found"}
    record = found["record"]
    return {"state": "found", "how": found["how"], "work_id": record.get("work_id"),
            "doi": record.get("doi"), "title": record.get("title"),
            "year": record.get("publication_year"), "journal": record.get("source"),
            "authors": record.get("authors") or [],
            "title_score": found["check"].get("title_score"),
            "first_author_agrees": found["check"].get("first_author_agrees")}


def merged(extracted, resolved):
    """The extraction's reading, corrected where an agreed record knows better.

    The authority decides the year, the journal and the DOI, because that is what it is for and
    what the extraction is worst at; the title stays as printed unless the PDF printed none.
    Both readings are kept, so a disagreement is visible rather than lost.
    """
    if resolved.get("state") != "found":
        return dict(extracted, metadata_source="extraction", work_id=None)
    merged_fields = dict(extracted)
    for field in ("year", "journal", "doi"):
        if resolved.get(field):
            merged_fields[field] = str(resolved[field])
    if not merged_fields.get("title"):
        merged_fields["title"] = resolved.get("title") or ""
    if not merged_fields.get("authors") and resolved.get("authors"):
        merged_fields["authors"] = [{"surname": "", "forenames": "", "name": name}
                                    for name in resolved["authors"]]
    return merged_fields | {"metadata_source": "openalex", "work_id": resolved.get("work_id"),
                            "extracted_year": extracted.get("year", ""),
                            "extracted_journal": extracted.get("journal", "")}
