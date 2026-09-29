"""Read/search/answer tools; ingestion is deliberately performed through the CLI."""
from mcp.server.fastmcp import FastMCP

from .cli import build_service


def create_server(service=None):
    mcp = FastMCP("byeori-local")

    def current():
        return service if service is not None else build_service()

    @mcp.tool()
    def list_papers() -> list[dict]:
        """List up to 100 recent registered papers and whether a note exists."""
        return current().store.papers()

    @mcp.tool()
    def search_wiki(query: str, limit: int = 10) -> list[dict]:
        """Search published Evidence Notes with BM25; use English scientific search terms."""
        return current().store.search(query, limit)

    @mcp.tool()
    def read_evidence_note(paper_id: str, start: int = 0, max_chars: int = 8000) -> dict:
        """Read a note window. Follow next_start to avoid silently losing later sections."""
        return current().read(paper_id, start=start, max_chars=max_chars)

    @mcp.tool()
    def read_paper_context(paper_id: str, paragraph_id: str) -> dict:
        """Resolve a note's P citation to the stored original extraction paragraph."""
        return current().context(paper_id, paragraph_id)

    @mcp.tool()
    def ask_byeori(question: str, paper_id: str | None = None) -> dict:
        """Answer with the configured Ollama model. Synchronous; may take several minutes."""
        return current().ask(question, paper_id)

    @mcp.tool()
    def get_job(job_id: str) -> list[dict]:
        """Inspect a CLI processing job. Interrupted running jobs require manual retry."""
        return current().store.jobs(job_id)

    return mcp


def main():
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
