"""build.py — generate the HUSTLEBOT GitHub Pages dashboard from hustlebot.db.

The dashboard is the ONLY reader of the write-only DB. Run on demand or from
the research cron. Output: C:/Users/Gray/hustlebot/dashboard/ (static site).

Usage: python3 build.py [--out dashboard]
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import date
from pathlib import Path

DB = Path(r"C:\Users\Gray\hustlebot\hustlebot.db")
DEFAULT_OUT = Path(r"C:\Users\Gray\hustlebot\dashboard")


def query(conn, sql):
    return [dict(r) for r in conn.execute(sql).fetchall()]


def esc(s) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _links_html(f) -> str:
    parts = []
    for l in json.loads(f["links"] or "[]"):
        el = (l or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        parts.append(f'<a href="{el}">{el[:50]}</a>')
    return ", ".join(parts)


def build(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row

    sources = query(conn, "SELECT * FROM sources ORDER BY scraped_at DESC LIMIT 50")
    facts = query(conn, "SELECT * FROM facts ORDER BY id DESC LIMIT 200")
    proposals = query(conn, "SELECT * FROM proposals ORDER BY id DESC")
    stats = {
        "sources": len(sources), "facts": len(facts),
        "proposals": len(proposals), "updated": date.today().isoformat(),
        "redflags": sum(1 for f in facts if "redflag" in (f["flags"] or "[]")),
    }
    conn.close()

    data = {"stats": stats, "sources": sources, "facts": facts, "proposals": proposals}
    (out_dir / "data.json").write_text(json.dumps(data, indent=1), encoding="utf-8")

    html = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>HUSTLEBOT — Profit Pipeline Dashboard</title>
<style>
body{font-family:system-ui,sans-serif;background:#0d1117;color:#e6edf3;margin:0;padding:24px;max-width:1100px;margin:0 auto}
h1{color:#58a6ff}h2{color:#79c0ff;border-bottom:1px solid #30363d;padding-bottom:6px}
.card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px;margin:10px 0}
.stats{display:flex;gap:14px;flex-wrap:wrap}.stat{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px 20px;text-align:center}
.stat b{font-size:26px;color:#58a6ff;display:block}.flag-r{color:#f85149}.flag-g{color:#3fb950}
.tag{display:inline-block;background:#21262d;border-radius:10px;padding:2px 8px;margin:2px;font-size:12px}
a{color:#58a6ff}code{background:#21262d;padding:1px 5px;border-radius:4px}
</style></head><body>
<h1>🤖 HUSTLEBOT — Profit Pipeline Dashboard</h1>
<p>Updated: __UPDATED__ · <span class="tag">write-only DB</span> <span class="tag">token-lite</span></p>
<div class="stats">
<div class="stat"><b>__SOURCES__</b>videos scanned</div>
<div class="stat"><b>__FACTS__</b>facts salvaged</div>
<div class="stat"><b>__PROPOSALS__</b>stack proposals</div>
<div class="stat"><b>__REDFLAGS__</b>red flags flagged</div>
</div>
<h2>Stack Proposals (with profit math)</h2>
__PROPOSALS_HTML__
<h2>Latest Salvaged Facts</h2>
__FACTS_HTML__
<h2>Recent Sources</h2>
__SOURCES_HTML__
</body></html>"""

    props = "".join(
        f'<div class="card"><b>{esc(p["stack"])}</b> <span class="tag">{esc(p["status"])}</span>'
        f'<div><code>{esc(p["math"])}</code></div><div class="tag">{esc(p["date"])}</div></div>'
        for p in proposals
    ) or '<div class="card">No proposals yet.</div>'

    fac = "".join(
        f'<div class="card"><span class="tag">{esc(f["category"])}</span> '
        + "".join(
            f'<span class="tag flag-{"r" if "redflag" in fl else "g"}">{esc(fl)}</span>'
            for fl in json.loads(f["flags"] or "[]")
        )
        + f'<div>{esc(f["content"])}</div>'
        + (f'<div><code>{esc(f["math"])}</code></div>' if f["math"] else "")
        + (f'<div>{_links_html(f)}</div>' if json.loads(f["links"] or "[]") else "")
        + f'<div class="tag">{esc(f["created_at"])}</div></div>'
        for f in facts[:30]
    ) or '<div class="card">No facts yet.</div>'

    src = "".join(
        f'<div class="card"><a href="{esc(s["url"])}">{esc(s["title"])[:80]}</a>'
        f' <span class="tag">{esc(s["platform"])}</span>'
        f' <span class="tag">{esc(s["channel"])[:30]}</span>'
        f' <div class="tag">{esc(s["scraped_at"])}</div></div>'
        for s in sources[:30]
    ) or '<div class="card">No sources yet.</div>'

    html = (html.replace("__UPDATED__", stats["updated"])
                .replace("__SOURCES__", str(stats["sources"]))
                .replace("__FACTS__", str(stats["facts"]))
                .replace("__PROPOSALS__", str(stats["proposals"]))
                .replace("__REDFLAGS__", str(stats["redflags"]))
                .replace("__PROPOSALS_HTML__", props)
                .replace("__FACTS_HTML__", fac)
                .replace("__SOURCES_HTML__", src))
    (out_dir / "index.html").write_text(html, encoding="utf-8")
    print(f"dashboard → {out_dir} (stats: {stats})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()
    build(Path(args.out))
