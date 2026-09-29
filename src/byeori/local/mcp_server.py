"""Read/search/answer tools; ingestion is deliberately performed through the CLI."""
from mcp.server.fastmcp import FastMCP

from .cli import build_service


def create_server(service=None):
    mcp = FastMCP("byeori-local")

    def current():
        return service if service is not None else build_service()

    @mcp.tool()
    def list_papers() -> list[dict]:
        """List up to 100 recent registered papers, their active note revision and extraction status."""
        return current().store.papers()

    @mcp.tool()
    def search_wiki(query: str, limit: int = 10) -> list[dict]:
        """Search published Evidence Notes with BM25; use English scientific search terms."""
        return current().store.search(query, limit)

    @mcp.tool()
    def read_evidence_note(paper_id: str, start: int = 0, max_chars: int = 8000,
                           revision: str | None = None) -> dict:
        """Read a note window. Pass the returned revision_id back to keep reading one version."""
        return current().read(paper_id, start=start, max_chars=max_chars, revision=revision)

    @mcp.tool()
    def list_note_revisions(paper_id: str) -> list[dict]:
        """Every published revision of this paper's note, newest first, with the active one marked."""
        return current().store.revisions(paper_id)

    @mcp.tool()
    def read_paper_context(paper_id: str, paragraph_id: str, revision: str | None = None) -> dict:
        """Resolve a note's P citation against the extraction that note revision was written from."""
        return current().context(paper_id, paragraph_id, revision)

    @mcp.tool()
    def ask_byeori(question: str, paper_id: str | None = None) -> dict:
        """Answer with the configured Ollama model. Synchronous; may take several minutes.

        Returns answer_status 'answered' or 'insufficient_evidence'; a refusal is not an error.
        """
        return current().ask(question, paper_id)

    @mcp.tool()
    def get_job(job_id: str) -> list[dict]:
        """Inspect a CLI processing job: its status, the stage it reached, and its error."""
        return current().store.jobs(job_id)

    return mcp


def main():
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
