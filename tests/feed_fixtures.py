"""Shared fixtures for the feed-triage tests: sample feeds and a local server.

No test touches the network. A test that needs real HTTP semantics — a redirect,
an oversized body, a slow response — gets them from `serving(...)`, an HTTP
server bound to 127.0.0.1 on an ephemeral port for the duration of a `with`.
"""

from __future__ import annotations

import contextlib
import threading
import time
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>Fixture RSS</title>
    <link>https://feeds.example.com/</link>
    <item>
      <title>A capability model for WebAssembly components</title>
      <link>https://feeds.example.com/posts/wasm-capabilities</link>
      <guid>post-1</guid>
      <pubDate>Thu, 08 Oct 2026 09:00:00 GMT</pubDate>
      <description>&lt;p&gt;We propose a &lt;b&gt;capability&lt;/b&gt; model for WASM.&lt;/p&gt;</description>
    </item>
    <item>
      <title>Version 2.0 released</title>
      <link>https://feeds.example.com/posts/v2</link>
      <guid>post-2</guid>
      <description>Release notes: the new version is now available.</description>
    </item>
    <item>
      <title>Weekend photos</title>
      <link>https://feeds.example.com/posts/photos</link>
      <guid>post-3</guid>
      <description>Some pictures of the garden.</description>
    </item>
  </channel>
</rss>
"""

ATOM = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Fixture Atom</title>
  <entry>
    <title>Prompt injection in coding agents</title>
    <link href="https://blog.example.net/injection" rel="alternate"/>
    <link href="https://blog.example.net/injection.json" rel="self"/>
    <id>tag:blog.example.net,2026:injection</id>
    <updated>2026-10-08T10:00:00Z</updated>
    <summary type="html">A new exploit: an injection vulnerability in a coding agent.</summary>
  </entry>
  <entry>
    <title>Thoughts on gardening</title>
    <link href="https://blog.example.net/garden"/>
    <id>tag:blog.example.net,2026:garden</id>
    <updated>2026-10-07T10:00:00Z</updated>
    <content type="xhtml"><div xmlns="http://www.w3.org/1999/xhtml">Opinion: <i>tomatoes</i> are fine.</div></content>
  </entry>
</feed>
"""

# The classic entity-expansion bomb, small enough to print and large enough to
# matter if a parser expanded it: 10^9 "lol"s.
BILLION_LAUGHS = """<?xml version="1.0"?>
<!DOCTYPE lolz [
  <!ENTITY lol "lol">
  <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
  <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
  <!ENTITY lol4 "&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;">
  <!ENTITY lol5 "&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;&lol4;">
  <!ENTITY lol6 "&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;&lol5;">
  <!ENTITY lol7 "&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;&lol6;">
  <!ENTITY lol8 "&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;&lol7;">
  <!ENTITY lol9 "&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;&lol8;">
]>
<rss version="2.0"><channel><item><title>&lol9;</title></item></channel></rss>
"""

EXTERNAL_ENTITY = """<?xml version="1.0"?>
<!DOCTYPE rss [ <!ENTITY xxe SYSTEM "file:///etc/passwd"> ]>
<rss version="2.0"><channel><item><title>&xxe;</title></item></channel></rss>
"""


# A route answers a request: (status, headers, body).
Response = tuple[int, Mapping[str, str], bytes]
Route = Response | Callable[[], Response]


def ok(body: str, content_type: str = "application/xml; charset=utf-8") -> Response:
    return (200, {"Content-Type": content_type}, body.encode())


def redirect(location: str) -> Response:
    return (302, {"Location": location}, b"")


def slow(seconds: float, body: str = "late") -> Callable[[], Response]:
    def respond() -> Response:
        time.sleep(seconds)
        return ok(body)

    return respond


class Server:
    """A running fixture server. `requests` records every path asked for, so a
    test can assert that something was *not* fetched."""

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
    allowlist, which is what a redirect-off-the-allowlist test needs."""
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
            # The client may have given up (the size-cap and timeout tests).
            with contextlib.suppress(BrokenPipeError, ConnectionResetError):
                self.wfile.write(body)

        def log_message(self, *_args: object) -> None:  # keep test output quiet
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
