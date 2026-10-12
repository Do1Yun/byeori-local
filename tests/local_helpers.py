"""Ollama protocol fixtures, including installed-model preflight without inference."""
import httpx


def ollama_transport(chat, model="test", *, remote=None):
    def serve(request):
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": model, "digest": "a" * 64,
                "size": 100, "details": {"family": "qwen3"}, **(remote or {})}]})
        if request.url.path == "/api/show":
            return httpx.Response(200, json={"template": "{{ .Messages }}", "capabilities": ["completion"],
                                             "model_info": {"qwen3.context_length": 40960}})
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": "0.34.4"})
        assert request.url.path == "/api/chat"
        return chat(request)
    return httpx.MockTransport(serve)
