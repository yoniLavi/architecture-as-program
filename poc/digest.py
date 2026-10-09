"""The local digest: what `Notifier<'digest'>` is bound to on this machine.

The feed-triage service's one outward act, other than fetching its allowlisted
feeds, is to tell its reader what it found. Here "tell" means: append to a dated
Markdown file under `var/digests/` and re-render the HTML page beside it. Nothing
leaves the machine, which is the point of choosing a local file over mail or a
webhook — the service can be run for weeks without a credential existing for it.

The content is adversarial. A digest is model output over feed items that anyone
on the internet could have written, so the HTML is built by escaping everything
and re-admitting a fixed handful of constructs: headings, list items, rules,
bold, and links whose target is plainly `http` or `https`. There is no raw-HTML
passthrough and no other URL scheme, so an item cannot plant a script, an image
beacon or a `javascript:` link in the page its reader opens. What an item *can*
still do is make the digest say something false — the residual the evaluation
measures and no renderer removes.
"""

from __future__ import annotations

import html
import os
import re
from collections.abc import Callable
from pathlib import Path

# A link the page will render as an anchor: bracketed text, then a parenthesised
# http(s) URL with no whitespace, quote or angle bracket in it.
_LINK = re.compile(r"\[([^\]\n]+)\]\((https?://[^\s()<>\"']+)\)")
_BOLD = re.compile(r"\*\*([^*\n]+)\*\*")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  body {{ font: 16px/1.55 system-ui, sans-serif; max-width: 44rem; margin: 2rem auto;
         padding: 0 1rem; color: #1b1b1b; background: #fcfcfa; }}
  h1 {{ font-size: 1.5rem; }} h2 {{ font-size: 1.15rem; margin-top: 2rem; }}
  h3 {{ font-size: 1rem; }} li {{ margin: .6rem 0; }}
  a {{ color: #0b57d0; }} hr {{ border: 0; border-top: 1px solid #ddd; margin: 2rem 0; }}
  @media (prefers-color-scheme: dark) {{
    body {{ color: #e6e6e6; background: #161616; }} a {{ color: #8ab4f8; }}
    hr {{ border-top-color: #444; }}
  }}
</style>
</head>
<body>
{body}
</body>
</html>
"""


def _inline(text: str) -> str:
    """Escape a line, then re-admit links and bold. Everything else stays text."""
    out: list[str] = []
    position = 0
    for match in _LINK.finditer(text):
        out.append(_bold(text[position : match.start()]))
        label, url = match.group(1), match.group(2)
        out.append(
            f'<a href="{html.escape(url, quote=True)}" rel="noopener noreferrer">'
            f"{html.escape(label)}</a>"
        )
        position = match.end()
    out.append(_bold(text[position:]))
    return "".join(out)


def _bold(text: str) -> str:
    pieces = _BOLD.split(text)
    # `split` with one group alternates plain, bold, plain, ...
    return "".join(
        f"<strong>{html.escape(piece)}</strong>" if i % 2 else html.escape(piece)
        for i, piece in enumerate(pieces)
    )


def render_html(markdown: str, *, title: str) -> str:
    """Render the digest's Markdown subset as a standalone HTML page."""
    body: list[str] = []
    in_list = False
    paragraph: list[str] = []

    def flush() -> None:
        nonlocal in_list
        if paragraph:
            body.append(f"<p>{_inline(' '.join(paragraph))}</p>")
            paragraph.clear()
        if in_list:
            body.append("</ul>")
            in_list = False

    for raw in markdown.splitlines():
        line = raw.rstrip()
        if line.startswith("- "):
            if paragraph:
                flush()
            if not in_list:
                body.append("<ul>")
                in_list = True
            body.append(f"<li>{_inline(line[2:])}</li>")
            continue
        if line.startswith("  ") and in_list and line.strip():
            # A continuation line of the item above.
            body[-1] = body[-1][: -len("</li>")] + "<br>" + _inline(line.strip()) + "</li>"
            continue
        if not line.strip():
            flush()
            continue
        heading = re.match(r"^(#{1,3}) (.+)$", line)
        if heading:
            flush()
            level = len(heading.group(1))
            body.append(f"<h{level}>{_inline(heading.group(2))}</h{level}>")
        elif line.strip() == "---":
            flush()
            body.append("<hr>")
        else:
            if in_list:
                flush()
            paragraph.append(line.strip())
    flush()
    return _PAGE.format(title=html.escape(title), body="\n".join(body))


def _replace(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def publish(directory: Path, date: str, message: str) -> Path:
    """Append `message` to the digest for `date` and re-render its page.

    One file per day: a service ticking hourly adds a section each time it finds
    something, and the day's page is the whole day. Returns the Markdown path."""
    if not _DATE.match(date):
        raise ValueError(f"not a date: {date!r}")
    directory.mkdir(parents=True, exist_ok=True)
    md_path = directory / f"{date}.md"
    existing = md_path.read_text() if md_path.exists() else ""
    combined = (
        f"{existing.rstrip()}\n\n---\n\n{message.strip()}\n" if existing else message.strip() + "\n"
    )
    _replace(md_path, combined)
    _replace(directory / f"{date}.html", render_html(combined, title=f"Feed digest — {date}"))
    return md_path


def publisher(directory: Path, today: Callable[[], str]) -> Callable[[str], None]:
    """What a `World` binds `Notifier<'digest'>` to: a function of the message
    alone. The date in the *filename* is the host's, from `today`; the date in the
    *text* is whatever the graph's clock-holding node put there."""

    def _publish(message: str) -> None:
        publish(directory, today(), message)

    return _publish


def latest(directory: Path) -> Path | None:
    """The most recent digest page, if any has been written."""
    pages = sorted(p for p in directory.glob("*.html") if _DATE.match(p.stem))
    return pages[-1] if pages else None
