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
import time
from urllib.parse import quote

import httpx

from byeori import identity, identity_resolve

OPENALEX_API = "https://api.openalex.org"
TEXT_HEAD_CHARS = 4000
DOI_IN_TEI = re.compile(r'<idno[^>]*type="DOI"[^>]*>([^<]+)</idno>', re.I)


class OpenAlexLookup:
    """Raw OpenAlex works, the shape identity_resolve.find expects to judge."""

    def __init__(self, url=OPENALEX_API, *, mailto=None, api_key=None, timeout=20.0, transport=None):
        self.url, self.mailto, self.timeout, self.transport = url.rstrip("/"), mailto, timeout, transport
        self.api_key = api_key

    def _get(self, path, params):
        headers = {"User-Agent": f"byeori-local ({self.mailto})" if self.mailto else "byeori-local"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if self.mailto:
            params = dict(params, mailto=self.mailto)
        with httpx.Client(base_url=self.url, timeout=self.timeout, trust_env=False,
                          transport=self.transport, headers=headers) as client:
            response = client.get(path, params=params)
            if response.status_code == 429:
                # One bounded retry only. A long Retry-After is an operator-visible limit,
                # not a reason to block paper processing for minutes.
                try:
                    delay = float(response.headers.get("Retry-After", "1"))
                except ValueError:
                    delay = 1
                if 0 <= delay <= 1:
                    time.sleep(delay)
                    response = client.get(path, params=params)
            response.raise_for_status()
            payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("OpenAlex returned an invalid payload")
        return payload

    def fetch_work(self, doi):
        doi = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)", "", str(doi or "").strip().lower())
        if not re.fullmatch(r"10\.\d{4,9}/\S+", doi):
            return None
        try:
            results = self._get("/works", {"filter": f"doi:https://doi.org/{quote(doi, safe='/')}",
                                           "per_page": 1}).get("results") or []
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise
        return results[0] if results else None

    def search(self, query, year):
        if not query:
            return []
        params = {"search": query, "per_page": 10}
        if year:
            params["filter"] = f"from_publication_date:{year - 1}-01-01,to_publication_date:{year + 1}-12-31"
        return self._get("/works", params).get("results") or []


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
    except httpx.HTTPStatusError as exc:
        return {"state": "rate_limited" if exc.response.status_code == 429 else "unavailable",
                "error_type": type(exc).__name__, "http_status": exc.response.status_code}
    except Exception as exc:                              # noqa: BLE001 - never block a note
        return {"state": "unavailable", "error_type": type(exc).__name__}
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
    """The extraction's reading, with the gaps an agreed record can fill.

    The authority fills what the page did not print, which is the case that matters: the
    lightweight extractor leaves the date empty on real journal PDFs, and a note with no year
    cannot be placed in the sequence of work it belongs to. It does not overrule what the page did
    print, because it is not reliably better: asked about "Attention is all you need" OpenAlex
    answered 2025, and about Bahdanau 2014, the arXiv record rather than the conference paper.
    A disagreement is recorded for a person to settle, never resolved by this code.
    """
    if resolved.get("state") != "found":
        return dict(extracted, metadata_source=extracted.get("metadata_source", "extraction"),
                    work_id=extracted.get("work_id"))
    fields, disagreements = dict(extracted), {}
    provenance = dict(fields.get("metadata_provenance") or {})
    for field in ("year", "journal", "doi"):
        value = resolved.get(field)
        if not value:
            continue
        if not fields.get(field):
            fields[field] = str(value)
            provenance[field] = "openalex"
        elif str(fields[field]).strip().lower() != str(value).strip().lower():
            disagreements[field] = str(value)
    if not fields.get("title"):
        fields["title"] = resolved.get("title") or ""
    if not fields.get("authors") and resolved.get("authors"):
        fields["authors"] = [{"surname": "", "forenames": "", "name": name}
                             for name in resolved["authors"]]
    existing_work = fields.get("work_id")
    if existing_work and resolved.get("work_id") and existing_work != resolved["work_id"]:
        disagreements["work_id"] = resolved["work_id"]
    return fields | {"metadata_source": fields.get("metadata_source") or "openalex",
                     "work_id": existing_work or resolved.get("work_id"),
                     "metadata_provenance": provenance} \
        | {f"openalex_{field}": value for field, value in disagreements.items()} \
        | ({"metadata_disagreement": ", ".join(sorted(disagreements))} if disagreements else {})
