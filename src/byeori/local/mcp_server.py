"""Read/search/answer tools; ingestion is deliberately performed through the CLI."""
from mcp.server.fastmcp import FastMCP

from .cli import build_service
from .jobs import QuestionJobs


def create_server(service=None):
    mcp = FastMCP("byeori-local")
    # One service and one question worker for the life of the server: a job submitted by one
    # call has to still be there for the call that polls it.
    state = {"service": service, "jobs": None}

    def current():
        if state["service"] is None:
            state["service"] = build_service()
        return state["service"]

    def questions():
        if state["jobs"] is None:
            state["jobs"] = QuestionJobs(current())
        return state["jobs"]

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
        """Submit a question and return its job ID at once; the local model takes minutes.

        Poll get_job for the job's status. Its result carries answer_status 'answered' or
        'insufficient_evidence'; a refusal to answer is not an error. One question runs at a time.
        """
        return questions().submit(question, paper_id)

    @mcp.tool()
    def cancel_job(job_id: str) -> dict:
        """Ask a question job to stop.

        cancel_requested says the request was accepted; stopped says the job has actually ended.
        A job already inside the model call stops when that call returns, and its answer is
        discarded.
        """
        return questions().cancel(job_id)

    @mcp.tool()
    def get_job(job_id: str) -> dict:
        """A job's status, the stage it reached, its error, and its result once it succeeded."""
        return current().store.job(job_id)

    @mcp.tool()
    def list_jobs(limit: int = 20) -> list[dict]:
        """Recent jobs of both kinds, newest first: papers processed and questions asked."""
        return current().store.jobs(limit=limit)

    return mcp


def main():
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
