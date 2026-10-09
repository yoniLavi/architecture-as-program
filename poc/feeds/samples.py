"""Two small, benign feeds: one RSS 2.0, one Atom.

Fixtures, kept in the package rather than under `tests/` because two things
outside the test suite run the service against them: the generation experiment's
`run` step, and the feed evaluation's tier comparison. Five items between them —
two the stub classifier keeps as must-reads, one as worth a look, two it drops.
"""

from __future__ import annotations

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

# The two feeds, at URLs inside the canonical graph's allowlist, as a canned web.
WEB: dict[str, str] = {
    "https://lobste.rs/t/plt.rss": RSS,
    "https://simonwillison.net/atom/everything/": ATOM,
}
