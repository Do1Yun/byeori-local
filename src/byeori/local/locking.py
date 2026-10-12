"""Cross-process worker lock released by the OS even after a crashed process."""
from contextlib import contextmanager
import os
from pathlib import Path
import tempfile
import threading
from urllib.parse import urlparse
import hashlib

_registry_guard = threading.Lock()
_locks = {}
_depth = threading.local()


@contextmanager
def serial_lock(path):
    """A blocking, thread- and process-safe lock, reentrant only for this thread."""
    path = Path(path).resolve()
    with _registry_guard:
        lock = _locks.setdefault(str(path), threading.RLock())
    with lock:
        held = getattr(_depth, "held", set())
        if str(path) in held:
            yield
            return
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with path.open("a+b") as stream:
            if path.stat().st_size == 0:
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            if os.name == "nt":
                import msvcrt
                # LK_LOCK has a finite retry count; retry without misreporting contention.
                import time
                while True:
                    try:
                        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                        break
                    except OSError:
                        time.sleep(0.1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            _depth.held = held | {str(path)}
            try:
                yield
            finally:
                _depth.held = held
                stream.seek(0)
                if os.name == "nt":
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def runtime_path(url="http://127.0.0.1:11434"):
    parsed = urlparse(url)
    host = parsed.hostname or "127.0.0.1"
    if host in {"localhost", "127.0.0.1", "::1"}:
        host = "loopback"
    identity = f"{parsed.scheme}://{host}:{parsed.port or (443 if parsed.scheme == 'https' else 80)}{parsed.path.rstrip('/')}"
    user = str(os.getuid()) if hasattr(os, "getuid") else os.environ.get("USERNAME", "user")
    root = Path(os.environ.get("BYEORI_LOCAL_RUNTIME_DIR") or
                str(Path(tempfile.gettempdir()) / f"byeori-local-{user}"))
    return root.expanduser() / (hashlib.sha256(identity.encode()).hexdigest() + ".lock")


@contextmanager
def inference_lock(url="http://127.0.0.1:11434"):
    with serial_lock(runtime_path(url)):
        yield


@contextmanager
def worker_lock(root):
    path = root / ".worker.lock"
    with path.open("a+b") as stream:
        if path.stat().st_size == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError("Another worker is processing this workspace; retry when it finishes") from exc
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
