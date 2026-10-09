"""A local HTTP server for exercising the service without the network.

Canned mode (`HTTPClient` with `live=False`) is enough for most tests: a URL maps
to a body. It cannot stand in for the parts of HTTP that carry the security
argument — a redirect to a host the graph never named, a response over the size
cap, a server that never answers. Those need a real socket, and this provides one
on `127.0.0.1`, on an ephemeral port, for the body of a `with`.

Used by the test suite and by the feed evaluation's hostile-corpus run, which is
a build step: so it lives in the package, is stdlib-only, and binds nothing but
the loopback interface. No test and no build step touches any other address.
"""

from __future__ import annotations

import contextlib
import threading
import time
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# A route answers a request: (status, headers, body).
Response = tuple[int, Mapping[str, str], bytes]
Route = Response | Callable[[], Response]


def ok(body: str | bytes, content_type: str = "application/xml; charset=utf-8") -> Response:
    data = body if isinstance(body, bytes) else body.encode()
    return (200, {"Content-Type": content_type}, data)


def redirect(location: str) -> Response:
    return (302, {"Location": location}, b"")


def slow(seconds: float, body: str = "late") -> Callable[[], Response]:
    def respond() -> Response:
        time.sleep(seconds)
        return ok(body)

    return respond


class Server:
    """A running fixture server. `requests` records every path asked for, so a
    caller can assert that something was *not* fetched."""

    def __init__(self, httpd: ThreadingHTTPServer, requests: list[str]):
        self._httpd = httpd
        self.requests = requests
        self.port: int = httpd.server_address[1]

    def url(self, path: str, host: str = "127.0.0.1") -> str:
        return f"http://{host}:{self.port}{path}"


@contextmanager
def serving(routes: Mapping[str, Route]) -> Iterator[Server]:
    """Serve `routes` (path → response) on 127.0.0.1 for the body of the `with`.

    Reachable as both `127.0.0.1` and `localhost` — two different *hosts* to an
    allowlist, which is what a redirect-off-the-allowlist case needs. `routes` is
    read on every request, so a caller may add to it once it knows the port."""
    requests: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            requests.append(self.path)
            route = routes.get(self.path)
            if route is None:
                self.send_error(404)
                return
            status, headers, body = route() if callable(route) else route
            self.send_response(status)
            for name, value in headers.items():
                self.send_header(name, value)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            # The client may have given up (a size cap, a timeout).
            with contextlib.suppress(BrokenPipeError, ConnectionResetError):
                self.wfile.write(body)

        def log_message(self, *_args: object) -> None:  # keep output quiet
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    httpd.daemon_threads = True
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield Server(httpd, requests)
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)
