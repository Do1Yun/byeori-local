"""Markdown claim locations and evidence fingerprints; no model or storage side effects."""
import hashlib
import json
import re

PARAGRAPH_CITATION = re.compile(r"\[(P\d+)\]")
ANY_CITATION = re.compile(r"\[(?:P\d+|E\d+(?:[-–:]P\d+(?:\s*[,;]\s*P\d+)*)?)\]")


def sentences(text):
    """Keep trailing source markers with their sentence. Decimal points are not boundaries.

    This conservative segmentation is a review aid, not an atomic-claim or entailment proof.
    """
    return [piece.strip() for piece in re.findall(
        r".+?(?:[.!?](?=\s|$)(?:\s*\[[^\]\n]+\])*(?=\s|$)|$)", text) if piece.strip()]


def markdown_units(text):
    """Yield prose, blockquotes and table rows with line locations and column context."""
    lines = text.splitlines()
    header = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "---", "<!--")):
            header = None
            continue
        if "|" in stripped:
            if re.fullmatch(r"[\s|:\-]+", stripped):
                continue
            if index + 1 < len(lines) and re.fullmatch(r"[\s|:\-]+", lines[index + 1]):
                header = stripped
                continue
            yield {"text": ((header + "\n") if header else "") + stripped,
                   "line": index + 1, "kind": "table_row"}
            continue
        header = None
        stripped = re.sub(r"^>\s*", "", stripped)
        stripped = re.sub(r"^(?:[-*\u2022]|\d+[.)])\s+", "", stripped)
        for piece in sentences(stripped):
            if re.fullmatch(r"(?:\[[^\]]+\]\s*)+", piece):
                continue
            if re.search(r"[\w]", piece):
                yield {"text": piece, "line": index + 1, "kind": "prose"}


def claim_fingerprint(paper_id, claim):
    packet = {"schema": 2, "paper_id": paper_id,
              "claim": " ".join(claim["claim"].split()),
              "cited": sorted(set(claim["cited"])),
              "sources": sorted((source["id"], source.get("kind"), source.get("section"),
                                  hashlib.sha256(source["text"].encode()).hexdigest())
                                 for source in claim["sources"])}
    return hashlib.sha256(json.dumps(packet, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


# ingest_lambda.CATALOG_SUMMARY_CHARS, repeated rather than imported: that module opens AWS
# clients when it loads, and nothing here may need credentials.
SUMMARY_CHARS = 260


def note_summary(text):
    """The note's own One-line Summary, which is what the catalogues show for it."""
    match = re.search(r"^## One-line Summary\s*$(.*?)(?=^## )", text, re.M | re.S)
    return " ".join(match[1].split())[:SUMMARY_CHARS] if match else ""


def split_frontmatter(text):
    """The note's frontmatter and its body, so one can be rewritten without touching the other."""
    if not text.startswith("---\n"):
        return "", text
    end = text.find("\n---\n", 4)
    return (text[:end + 5], text[end + 5:].lstrip("\n")) if end > 0 else ("", text)


def parse_frontmatter(text):
    """The note's frontmatter as fields, and the body the model wrote."""
    front, body = split_frontmatter(text)
    fields = {}
    for line in front.splitlines():
        key, separator, value = line.partition(":")
        if not separator or line.strip() in {"---", ""}:
            continue
        try:
            fields[key.strip()] = json.loads(value.strip())
        except json.JSONDecodeError:
            fields[key.strip()] = value.strip().strip('"')
    return fields, body
