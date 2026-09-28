"""What the shared intake folder holds, paper by paper, in either of its two shapes.

The folder was flat until 2026-09-24: one publisher PDF per file, named with the paper's stem.
Since 2026-09-25 a paper can also arrive as a directory named with its stem, holding the article
PDF under the publisher's own file name and the supplementary files beside it
(`matoba-2026-massively-parallel-assessment-of-gene/s41593-026-02454-2.pdf`,
`41593_2026_2454_MOESM3_ESM.xlsx`, ...). Both shapes are read here so that the upload and the
clean-up agree on what a paper is.

In a directory the article is the one PDF whose name is not a publisher's supplementary name.
A file name is a clue and not the verdict, though, and when it leaves no PDF or more than one the
directory is read instead: Cell Press packages the article as the folder's last `mmc` file
("Article plus Supplemental Information"), and NEJM and JCO name an appendix, a protocol or a data
supplement in ways no list of name fragments anticipates. Page one of each PDF is then read, a
file whose opening declares itself a supplement is set aside, and the article is the one left
whose opening carries a publisher's article heading.

When that still leaves no PDF or more than one, the paper is reported as a problem and nothing is
guessed: a supplementary PDF uploaded as the article would become the paper's note.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .metadata_pdf import MAX_PDF_BYTES, extract_first_page
from .paper_upload import STEM_PATTERN

# Publisher names for supplementary files: Nature `MOESM`/`_ESM`, Cell `mmc1`, Science `_sm`,
# PNAS `.sapp`, PLOS `.s001`, bioRxiv `media-1`, eLife `-supp1`, and plain "supplementary".
SUPPLEMENTARY_NAME = re.compile(
    r"moesm\d|_esm[._]|mmc\d|supp|_sm[._]|\.sapp\.|\.s\d{3}\.|media-\d|source[-_ ]?data|reporting[-_ ]?summary|"
    r"peer[-_ ]?review", re.I)

# What page one says it is. The openings below were read from the 348 PDFs the shared folder held
# on 2026-09-25: a supplement announces itself in its first line, and a publisher prints the
# article's own section heading above its title. Both are checked against the opening of page one
# with its whitespace squashed, the heading within the first HEADING_CHARS because a heading stands
# at the top of the page: a title that ends "... clinical trial" further down is not one.
SUPPLEMENT_OPENING = re.compile(
    r"supplement(?:ary|al)?\s+(?:information|materials?|appendix|methods?|figures?|tables?|data|notes?|"
    r"discussion|results?)|supplementary\b|supplemental\b|data\s+supplement|supporting\s+information|"
    r"peer\s+review\s+file|protocol(?:\s+title)?\s*:|protocol\s+for\s*:|clinical\s+study\s+protocol|"
    r"study\s+protocol|statistical\s+analysis\s+plan|reporting\s+summary|data\s+sharing\s+statement|"
    r"extended\s+data|online\s+content", re.I)
ARTICLE_HEADING = re.compile(
    r"\b(?:research\s+articles?|original\s+(?:article|reports?|investigation|research)|articles?|"
    r"research\s+letter|technical\s+report|brief\s+communication|review\s+article|perspective|"
    r"neuroresource|resource|journal\s+pre-?proof|matters\s+arising|clinical\s+trial\s+updates?)\b", re.I)
OPENING_CHARS = 200
HEADING_CHARS = 80


@dataclass
class FolderPaper:
    """One paper in the intake folder."""

    stem: str
    layout: str                                   # "file" (flat PDF) or "folder" (a directory)
    article: Path | None
    others: list[Path] = field(default_factory=list)   # everything else in its directory, sorted
    problem: str | None = None
    folder: Path | None = None                    # the directory, for the "folder" layout
    chosen_by: str = "file name"                  # or "first page", when the names did not say

    @property
    def path(self) -> Path:
        """What the clean-up moves: the flat PDF, or the whole directory."""
        return self.article if self.layout == "file" else self.folder

    def relative(self, path: Path) -> str:
        return path.relative_to(self.folder).as_posix()


def _visible_files(folder: Path) -> list[Path]:
    return sorted(path for path in folder.rglob("*")
                  if path.is_file() and not any(part.startswith(".") for part in path.relative_to(folder).parts))


def first_page_opening(pdf: Path) -> str:
    """The opening of page one, whitespace squashed; empty when the file cannot be read as a PDF."""
    try:
        with pdf.open("rb") as handle:
            raw = handle.read(MAX_PDF_BYTES + 1)
        if len(raw) > MAX_PDF_BYTES:
            return ""
        return re.sub(r"\s+", " ", extract_first_page(raw)).strip()[:OPENING_CHARS]
    except Exception:       # noqa: BLE001 - an unreadable file simply gives no evidence
        return ""


def article_by_first_page(pdfs: list[Path]) -> Path | None:
    """The one PDF whose page one declares no supplement and carries an article heading."""
    articles = []
    for pdf in pdfs:
        opening = first_page_opening(pdf)
        if not opening or SUPPLEMENT_OPENING.search(opening):
            continue
        if ARTICLE_HEADING.search(opening[:HEADING_CHARS]):
            articles.append(pdf)
    return articles[0] if len(articles) == 1 else None


def read_folder_paper(folder: Path) -> FolderPaper:
    stem = folder.name
    files = _visible_files(folder)
    paper = FolderPaper(stem=stem, layout="folder", article=None, folder=folder)
    if not STEM_PATTERN.fullmatch(stem):
        paper.others, paper.problem = files, "folder_name_not_a_stem"
        return paper
    pdfs = [path for path in files if path.parent == folder and path.suffix.lower() == ".pdf"]
    candidates = [path for path in pdfs if not SUPPLEMENTARY_NAME.search(path.name)]
    if len(candidates) != 1:
        read = article_by_first_page(pdfs)
        if read is None:
            paper.others = files
            paper.problem = "no_article_pdf" if not candidates else "article_unclear"
            return paper
        candidates, paper.chosen_by = [read], "first page"
    paper.article = candidates[0]
    paper.others = [path for path in files if path != paper.article]
    return paper


def folder_papers(root: Path) -> list[FolderPaper]:
    """Every paper in the intake folder, flat PDFs and per-paper directories alike."""
    papers = [FolderPaper(stem=path.stem, layout="file", article=path)
              for path in sorted(root.glob("*.pdf")) if path.is_file()]
    papers += [read_folder_paper(path) for path in sorted(root.iterdir())
               if path.is_dir() and not path.name.startswith(".")]
    return papers
