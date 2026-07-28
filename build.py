#!/usr/bin/env python3
"""Tiny static blog generator.

Usage:
    python build.py          # build the site into ./site
    python build.py serve    # build, then serve at http://127.0.0.1:8000

Content lives in ./content as markdown files. Posts go in ./content/posts
and are named YYYY-MM-DD-some-slug.md with a small frontmatter block:

    ---
    title: My post title
    date: 2026-06-23
    ---

No dependencies beyond the Python standard library.
"""

from __future__ import annotations

import calendar
import hashlib
import html
import re
import shutil
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
POSTS_DIR = CONTENT / "posts"
OUT = ROOT / "site"

# ---------------------------------------------------------------------------
# Site configuration — edit these values to make the site yours.
# ---------------------------------------------------------------------------

SITE = {
    "title": "Hrishi",
    "tagline": "growing crystals in silico, one event at a time",
    "author": "Hrishi Harsora",
    "email": "hrishi.harsora@iitgn.ac.in",
    # Your live URL (used for the RSS feed's absolute links).
    "base_url": "https://hrishiharsora.github.io",
    # External links shown in the navigation bar.
    "github_url": "https://github.com/HrishiHarsora",
    "cv_url": "https://drive.google.com/file/d/1zuEHBbX6TYTuY7v8Cb1yxR11cZQRl9Fg/view?usp=sharing",
    # Contact-card links. Leave blank to hide that icon.
    "linkedin_url": "https://www.linkedin.com/in/hrishih",
    "phone": "+919175007025",
}

# Inline SVG icons (fill inherits the link colour via currentColor).
ICONS = {
    "email": '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M20 4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2Zm0 4.24-8 5-8-5V6l8 5 8-5v2.24Z"/></svg>',
    "github": '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 .5C5.37.5 0 5.87 0 12.5c0 5.3 3.44 9.8 8.21 11.39.6.11.82-.26.82-.58 0-.28-.01-1.02-.02-2.01-3.34.73-4.04-1.61-4.04-1.61-.55-1.39-1.34-1.76-1.34-1.76-1.09-.75.08-.73.08-.73 1.21.09 1.84 1.24 1.84 1.24 1.07 1.83 2.81 1.3 3.5.99.11-.78.42-1.3.76-1.6-2.67-.3-5.47-1.33-5.47-5.93 0-1.31.47-2.38 1.24-3.22-.13-.3-.54-1.52.12-3.18 0 0 1.01-.32 3.3 1.23a11.5 11.5 0 0 1 6 0c2.29-1.55 3.3-1.23 3.3-1.23.66 1.66.25 2.88.12 3.18.77.84 1.24 1.91 1.24 3.22 0 4.61-2.81 5.63-5.49 5.93.43.37.81 1.1.81 2.22 0 1.61-.01 2.9-.01 3.29 0 .32.22.7.83.58C20.56 22.29 24 17.8 24 12.5 24 5.87 18.63.5 12 .5Z"/></svg>',
    "linkedin": '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M20.45 20.45h-3.56v-5.57c0-1.33-.02-3.04-1.85-3.04-1.85 0-2.13 1.45-2.13 2.94v5.67H9.35V9h3.42v1.56h.05c.48-.9 1.64-1.85 3.37-1.85 3.6 0 4.27 2.37 4.27 5.46v6.28ZM5.34 7.43a2.06 2.06 0 1 1 0-4.13 2.06 2.06 0 0 1 0 4.13ZM7.12 20.45H3.56V9h3.56v11.45ZM22.22 0H1.77C.79 0 0 .77 0 1.72v20.56C0 23.23.79 24 1.77 24h20.45c.98 0 1.78-.77 1.78-1.72V1.72C24 .77 23.2 0 22.22 0Z"/></svg>',
    "phone": '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M6.62 10.79a15.53 15.53 0 0 0 6.59 6.59l2.2-2.2a1 1 0 0 1 1.02-.24 11.36 11.36 0 0 0 3.57.57 1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1c0 1.25.2 2.45.57 3.57a1 1 0 0 1-.24 1.02l-2.21 2.2Z"/></svg>',
}

NAV = [
    ("Home", "/"),
    ("About", "/about/"),
    ("Publications", "/publications/"),
    ("Contact", "/contact/"),
    ("CV", SITE["cv_url"]),
]

# ---------------------------------------------------------------------------
# Markdown — a small converter covering the features a blog actually uses:
# headings, paragraphs, lists, blockquotes, fenced code, inline code,
# bold/italic, links, and horizontal rules.
# ---------------------------------------------------------------------------


def _inline(text: str) -> str:
    text = html.escape(text, quote=False)
    parts = re.split(r"(`[^`]+`)", text)
    rendered: list[str] = []
    for part in parts:
        if len(part) > 2 and part.startswith("`") and part.endswith("`"):
            rendered.append("<code>" + part[1:-1] + "</code>")
        else:
            part = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', part)
            part = re.sub(r"==([^=]+)==", r'<span class="hl">\1</span>', part)
            part = re.sub(r"\+\+([^+]+)\+\+", r"<u>\1</u>", part)
            part = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", part)
            part = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", part)
            rendered.append(part)
    return "".join(rendered)


def md_to_html(text: str) -> str:
    lines = text.split("\n")
    out: list[str] = []
    para: list[str] = []
    i = 0

    def flush_para() -> None:
        if para:
            out.append("<p>" + _inline(" ".join(para)) + "</p>")
            para.clear()

    while i < len(lines):
        stripped = lines[i].strip()

        if stripped.startswith("```"):
            flush_para()
            lang = stripped[3:].strip()
            i += 1
            code: list[str] = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1  # skip the closing fence
            cls = f' class="language-{html.escape(lang, quote=True)}"' if lang else ""
            out.append(f"<pre><code{cls}>" + html.escape("\n".join(code)) + "</code></pre>")
            continue

        if not stripped:
            flush_para()
            i += 1
            continue

        m = re.match(r"(#{1,6})\s+(.*)", stripped)
        if m:
            flush_para()
            level = len(m.group(1))
            out.append(f"<h{level}>{_inline(m.group(2))}</h{level}>")
            i += 1
            continue

        if re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", stripped):
            flush_para()
            out.append("<hr>")
            i += 1
            continue

        if stripped.startswith(">"):
            flush_para()
            quote: list[str] = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip()[1:].lstrip())
                i += 1
            out.append("<blockquote><p>" + _inline(" ".join(quote)) + "</p></blockquote>")
            continue

        if re.match(r"[-*]\s+", stripped):
            flush_para()
            items: list[str] = []
            while i < len(lines) and re.match(r"[-*]\s+", lines[i].strip()):
                item = re.sub(r"^[-*]\s+", "", lines[i].strip())
                items.append("<li>" + _inline(item) + "</li>")
                i += 1
            out.append("<ul>\n" + "\n".join(items) + "\n</ul>")
            continue

        if re.match(r"\d+\.\s+", stripped):
            flush_para()
            items = []
            while i < len(lines) and re.match(r"\d+\.\s+", lines[i].strip()):
                item = re.sub(r"^\d+\.\s+", "", lines[i].strip())
                items.append("<li>" + _inline(item) + "</li>")
                i += 1
            out.append("<ol>\n" + "\n".join(items) + "\n</ol>")
            continue

        para.append(stripped)
        i += 1

    flush_para()
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Content loading
# ---------------------------------------------------------------------------


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    meta: dict[str, str] = {}
    body = text
    if text.lstrip().startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].strip().splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    meta[key.strip().lower()] = value.strip()
            body = parts[2]
    return meta, body.strip()


class Post:
    def __init__(self, path: Path):
        meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
        stem = path.stem
        self.slug = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", stem)
        raw_date = meta.get("date") or stem[:10]
        self.date = datetime.strptime(raw_date, "%Y-%m-%d").date()
        self.title = meta.get("title", self.slug.replace("-", " ").title())
        self.html = md_to_html(body)
        self.url = f"/blog/{self.slug}/"

    @property
    def display_date(self) -> str:
        return f"{self.date:%d} {self.date:%b}, {self.date:%Y}"


def load_posts() -> list[Post]:
    posts = [Post(p) for p in sorted(POSTS_DIR.glob("*.md"))]
    posts.sort(key=lambda p: p.date, reverse=True)
    return posts


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


BG_SCRIPT = """<script>
(function () {
  var canvas = document.getElementById('bg-canvas');
  if (!canvas) return;
  var ctx = canvas.getContext('2d');
  var W = 0, H = 0, dpr = Math.min(window.devicePixelRatio || 1, 2), parts = [];
  function resize() {
    W = window.innerWidth; H = window.innerHeight;
    canvas.width = W * dpr; canvas.height = H * dpr;
    canvas.style.width = W + 'px'; canvas.style.height = H + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    var n = Math.max(50, Math.min(170, Math.floor(W * H / 9000)));
    parts = [];
    for (var i = 0; i < n; i++) parts.push({ x: Math.random() * W, y: Math.random() * H });
  }
  resize();
  window.addEventListener('resize', resize);
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var step = 2.4;
  function draw(animate) {
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = 'rgba(0, 0, 0, 0.12)';
    for (var i = 0; i < parts.length; i++) {
      var p = parts[i];
      if (animate) {
        p.x += (Math.random() * 2 - 1) * step;
        p.y += (Math.random() * 2 - 1) * step;
        if (p.x < 0) p.x += W; else if (p.x > W) p.x -= W;
        if (p.y < 0) p.y += H; else if (p.y > H) p.y -= H;
      }
      ctx.beginPath();
      ctx.arc(p.x, p.y, 1.3, 0, 6.2832);
      ctx.fill();
    }
    if (animate) requestAnimationFrame(function () { draw(true); });
  }
  draw(!reduce);
})();
</script>"""


def render_page(title: str, content: str, *, description: str = "", body_class: str = "") -> str:
    nav_links = "\n      ".join(
        f'<a href="{html.escape(href, quote=True)}">{html.escape(label)}</a>'
        for label, href in NAV
    )
    desc = html.escape(description or SITE["tagline"], quote=True)
    body_attr = f' class="{body_class}"' if body_class else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{desc}">
  <link rel="stylesheet" href="/style.css?v={STYLE_VERSION}">
  <link rel="alternate" type="application/rss+xml" title="{html.escape(SITE['title'], quote=True)}"
        href="/feed.xml">
  <title>{html.escape(title)}</title>
</head>
<body{body_attr}>
  <canvas id="bg-canvas" aria-hidden="true"></canvas>
  <header>
    <a class="site-title" href="/">{html.escape(SITE['title'])}</a>
    <nav>
      {nav_links}
    </nav>
  </header>
  <main>
{content}
  </main>
{BG_SCRIPT}
</body>
</html>
"""


def post_list_html(posts: list[Post]) -> str:
    items = "\n".join(
        f'      <li><span class="date">{p.display_date}</span>'
        f'<a href="{p.url}">{html.escape(p.title)}</a></li>'
        for p in posts
    )
    return f'    <ul class="blog-posts">\n{items}\n    </ul>'


def write_page(path: Path, html_text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html_text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


_MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
_MONTHS.update({m.lower(): i for i, m in enumerate(calendar.month_abbr) if m})


def _entry_date(when: str) -> datetime:
    """Parse a timeline date string into a sortable datetime (newest sorts first).

    Understands 'December 2025', 'Dec 2025', '2025-12', '2025-12-05', '2025',
    and ranges like 'May - July 2026' (sorted by the first month it mentions).
    Anything unrecognised sorts to the bottom.
    """
    when = when.strip()
    if "present" in when.lower():   # ongoing — always sorts to the very top
        return datetime.max
    for fmt in ("%B %Y", "%b %Y", "%Y-%m-%d", "%Y-%m", "%B %d, %Y", "%Y"):
        try:
            return datetime.strptime(when, fmt)
        except ValueError:
            continue
    # Fallback for ranges / free-form: first month name + first 4-digit year.
    year = re.search(r"\b(\d{4})\b", when)
    month = next((_MONTHS[w.lower()] for w in re.findall(r"[A-Za-z]+", when)
                  if w.lower() in _MONTHS), None)
    if year:
        return datetime(int(year.group(1)), month or 1, 1)
    return datetime.min


def progress_section_html() -> str:
    """Render just the achievements timeline (shown on the home page).

    Entries are blocks separated by blank lines. The first line of a block is
    `date :: headline`; any following lines are extra detail lines (markdown
    links and *italics* work in every line). Entries are sorted by date, newest
    first, so you can add a new one anywhere in the file.
    """
    _, body = parse_frontmatter((CONTENT / "progress.md").read_text(encoding="utf-8"))

    entries: list[tuple[datetime, str, str, list[str]]] = []
    for block in re.split(r"\n\s*\n", body.strip()):
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if not lines or "::" not in lines[0]:
            continue
        when, _, headline = lines[0].partition("::")
        entries.append((_entry_date(when), when.strip(), headline.strip(), lines[1:]))

    entries.sort(key=lambda e: e[0], reverse=True)

    items: list[str] = []
    for _, when, headline, _details in entries:
        # A date range (en/em dash, spaced hyphen, or "to") renders as a spanning
        # bar instead of a point; an ongoing "Present" entry also runs its bar up
        # to the very top of the timeline to signal it's still happening.
        is_present = "present" in when.lower()
        is_range = is_present or bool(re.search(r"[–—]|\s-\s|\bto\b", when, re.IGNORECASE))
        classes = " ".join(c for c, on in (("range", is_range), ("present", is_present)) if on)
        li_open = f'      <li class="{classes}">' if classes else "      <li>"
        # Only the date and headline are shown; any further detail lines in
        # progress.md are kept in the source but not rendered on the timeline.
        spans = [
            f'<span class="when">{html.escape(when)}</span>',
            f'<span class="what">{_inline(headline)}</span>',
        ]
        items.append(li_open + "".join(spans) + "</li>")

    timeline = '    <ol class="timeline">\n' + "\n".join(items) + "\n    </ol>"
    return '    <div class="timeline-scroll">\n' + timeline + "\n    </div>"


def contact_icons_html() -> str:
    """The row of contact icon links."""
    links: list[tuple[str, str, str]] = []  # (href, label, icon key)
    if SITE.get("email"):
        links.append((f'mailto:{SITE["email"]}', "Email", "email"))
    if SITE.get("linkedin_url"):
        links.append((SITE["linkedin_url"], "LinkedIn", "linkedin"))
    if SITE.get("phone"):
        links.append((f'tel:{SITE["phone"]}', "Phone", "phone"))
    if SITE.get("github_url"):
        links.append((SITE["github_url"], "GitHub", "github"))

    icons = "\n        ".join(
        f'<a href="{html.escape(href, quote=True)}" aria-label="{label}" title="{label}">'
        f"{ICONS[key]}</a>"
        for href, label, key in links
    )
    return '<div class="contact-icons">\n        ' + icons + "\n      </div>"


def build_contact() -> None:
    email = SITE.get("email", "")
    lead = (
        f'      <p>Reach me at <a href="mailto:{email}">{email}</a>, '
        "or through the links below.</p>\n"
        if email
        else ""
    )
    content = (
        '    <section class="contact-card">\n'
        + lead
        + "      " + contact_icons_html() + "\n"
        + "    </section>"
    )
    write_page(OUT / "contact" / "index.html", render_page(f"Contact — {SITE['title']}", content))


def build_home() -> None:
    intro_meta, intro_body = parse_frontmatter((CONTENT / "home.md").read_text(encoding="utf-8"))
    content = md_to_html(intro_body) + "\n" + progress_section_html()
    write_page(
        OUT / "index.html",
        render_page(SITE["title"], content, body_class="home"),
    )


def build_blog(posts: list[Post]) -> None:
    content = "    <h1>Blog</h1>\n" + post_list_html(posts)
    write_page(OUT / "blog" / "index.html", render_page(f"Blog — {SITE['title']}", content))

    for post in posts:
        content = (
            f"    <h1>{html.escape(post.title)}</h1>\n"
            f'    <p class="post-meta">{post.display_date}</p>\n'
            + post.html
            + '\n    <p class="back-link"><a href="/blog/">&larr; all posts</a></p>'
        )
        write_page(
            OUT / "blog" / post.slug / "index.html",
            render_page(f"{post.title} — {SITE['title']}", content, description=post.title),
        )


def build_simple_page(name: str, heading: str, *, show_heading: bool = False) -> None:
    meta, body = parse_frontmatter((CONTENT / f"{name}.md").read_text(encoding="utf-8"))
    title = meta.get("title", heading)
    content = md_to_html(body)
    if show_heading:
        content = f"    <h1>{html.escape(title)}</h1>\n" + content
    write_page(OUT / name / "index.html", render_page(f"{title} — {SITE['title']}", content))


def build_404() -> None:
    content = (
        "    <h1>404</h1>\n"
        "    <p>That page doesn&rsquo;t exist. It may have desorbed from the surface.</p>\n"
        '    <p><a href="/">&larr; back home</a></p>'
    )
    write_page(OUT / "404.html", render_page(f"404 — {SITE['title']}", content))


def build_feed(posts: list[Post]) -> None:
    def rfc822(d: date) -> str:
        dt = datetime(d.year, d.month, d.day, 12, 0, tzinfo=timezone.utc)
        return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")

    base = SITE["base_url"].rstrip("/")
    items = []
    for p in posts:
        items.append(
            "    <item>\n"
            f"      <title>{html.escape(p.title)}</title>\n"
            f"      <link>{base}{p.url}</link>\n"
            f"      <guid>{base}{p.url}</guid>\n"
            f"      <pubDate>{rfc822(p.date)}</pubDate>\n"
            f"      <description>{html.escape(p.html)}</description>\n"
            "    </item>"
        )
    feed = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        "  <channel>\n"
        f"    <title>{html.escape(SITE['title'])}</title>\n"
        f"    <link>{base}/</link>\n"
        f"    <description>{html.escape(SITE['tagline'])}</description>\n"
        + "\n".join(items)
        + "\n  </channel>\n</rss>\n"
    )
    write_page(OUT / "feed.xml", feed)


STYLE = """\
:root {
  --width: 720px;
  --font-main: "Times New Roman", Times, serif;
  --font-mono: "Times New Roman", Times, serif;
  --background: #ffffff;
  --text: #000000;
  --muted: #555555;
  --link: #000000;
  --accent-bg: #f2f2f2;
  --border: #cccccc;
}

* { box-sizing: border-box; }

html { background-color: var(--background); }

/* Animated Monte Carlo background canvas, pinned behind all content. */
#bg-canvas {
  position: fixed;
  inset: 0;
  z-index: -1;
  pointer-events: none;
}

body {
  margin: 0 auto;
  padding: 22px;
  max-width: var(--width);
  font-family: var(--font-main);
  font-size: 0.92rem;
  line-height: 1.45;
  background: transparent;
  color: var(--text);
}

header { margin-bottom: 1.6rem; }

.site-title {
  font-size: 2.4rem;
  font-weight: 700;
  color: var(--text);
  text-decoration: none;
  display: block;
  margin-bottom: 0.3rem;
}

nav { margin-top: 0.4rem; }
nav a { margin-right: 0.9rem; }

a { color: var(--link); }
a:hover { text-decoration-thickness: 2px; }

h1, h2, h3 { line-height: 1.25; }
h1 { font-size: 1.4rem; }
h2 { font-size: 1.15rem; }

.post-meta { color: var(--muted); margin-top: -0.6rem; }
.back-link { margin-top: 2.5rem; }

ul.blog-posts { list-style: none; padding: 0; }
ul.blog-posts li {
  display: flex;
  gap: 1rem;
  align-items: baseline;
  margin-bottom: 0.35rem;
}
ul.blog-posts .date {
  color: var(--muted);
  flex: 0 0 7.2em;
  font-variant-numeric: tabular-nums;
}

ol.timeline {
  list-style: none;
  padding: 0;
  margin: 1.5rem 0 0 0.5rem;
  border-left: 2px solid var(--text);
}
ol.timeline { line-height: 1.25; }
ol.timeline li {
  position: relative;
  padding: 0 0 0.5rem 1.5rem;
}
ol.timeline li::before {
  content: "";
  position: absolute;
  left: -0.29rem;
  top: 0.55rem;
  width: 0.42rem;
  height: 0.42rem;
  background: var(--text);
  border-radius: 50%;
}
/* A date range spans its whole entry as a rounded bar instead of a dot. */
ol.timeline li.range::before {
  top: 0.5rem;
  bottom: 0.5rem;
  height: auto;
  border-radius: 0.21rem;
}
/* An ongoing "Present" entry runs its bar right up to the top of the timeline. */
ol.timeline li.present::before {
  top: -1rem;
}
ol.timeline .when {
  display: block;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  font-size: 1.05em;
  margin-bottom: 0.05rem;
}
ol.timeline .what { display: block; }
ol.timeline .detail {
  display: block;
  font-size: 0.85em;
  margin-top: 0.1rem;
  white-space: nowrap;
}

.hl { color: #1a5fb4; font-weight: 700; }

/* Contact icons at the bottom of the home page. */
.contact-card {
  margin-top: 1.5rem;
  text-align: center;
}
.contact-icons { display: flex; justify-content: center; gap: 1.6rem; }
.contact-icons a {
  color: var(--text);
  display: inline-flex;
  transition: color 0.15s ease;
}
.contact-icons a:hover { color: #1a5fb4; }
.contact-icons svg { width: 22px; height: 22px; display: block; }

/* Publications-style numbered lists: space entries out, hanging indent. */
main ol:not(.timeline) { padding-left: 1.4rem; }
main ol:not(.timeline) li { margin-bottom: 0.55rem; padding-left: 0.3rem; }

/* Sub-pages (everything except the home timeline): tighter line spacing. */
body:not(.home) { line-height: 1.3; }
body:not(.home) main p { margin: 0 0 0.5rem; }

/* Home page: pin to viewport height and let the timeline scroll on its own,
   so the achievements list never makes the whole page taller than the screen. */
body.home {
  height: 100vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
body.home header { margin-bottom: 1.1rem; }
body.home main {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
body.home main > p { margin: 0 0 0.45rem; }
body.home .timeline-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding-left: 0.4rem;
  margin-top: 0.4rem;           /* small gap above the timeline */
  scrollbar-width: none;        /* Firefox: hide scrollbar */
  -ms-overflow-style: none;     /* old Edge/IE */
}
body.home .timeline-scroll::-webkit-scrollbar { width: 0; height: 0; }  /* Chrome/Safari */
body.home ol.timeline { margin-top: 1rem; }

code {
  font-family: var(--font-mono);
  font-size: 0.92em;
  background: var(--accent-bg);
  padding: 0.12em 0.35em;
  border-radius: 4px;
}

pre {
  background: var(--accent-bg);
  padding: 0.9em 1.1em;
  border-radius: 6px;
  overflow-x: auto;
}
pre code { background: none; padding: 0; }

blockquote {
  margin: 1.2em 0;
  padding-left: 1em;
  border-left: 3px solid var(--border);
  color: var(--muted);
  font-style: italic;
}

hr { border: none; border-top: 1px solid var(--border); margin: 2em 0; }

@media (max-width: 540px) {
  ul.blog-posts li { flex-direction: column; gap: 0; margin-bottom: 0.9rem; }
  ul.blog-posts .date { flex: none; font-size: 0.9em; }
}
"""


STYLE_VERSION = hashlib.md5(STYLE.encode("utf-8")).hexdigest()[:8]


def build() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    posts = load_posts()
    build_home()
    build_blog(posts)
    build_simple_page("about", "About")
    build_simple_page("publications", "Publications")
    build_contact()
    build_404()
    build_feed(posts)
    (OUT / "style.css").write_text(STYLE, encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")  # serve as-is on GitHub Pages
    print(f"Built {len(posts)} posts -> {OUT}")


def serve(port: int = 8000) -> None:
    import functools
    import http.server

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(OUT))
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), handler) as srv:
        print(f"Serving at http://127.0.0.1:{port} (Ctrl+C to stop)")
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    build()
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
        serve(port)
