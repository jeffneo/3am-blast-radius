"""Render LAB-GUIDE.md and FACILITATOR-GUIDE.md to PDF for printing and the zip.

    uv run --with markdown build/make_pdf.py

Print needs differ from the screen version, handled here rather than by keeping
a second copy of the guide:

  * Collapsible <details> blocks (the stretch solutions) cannot be opened on
    paper and print closed. They move to an Answers appendix at the back, and
    each leaves a pointer where it was.
  * Query results are ASCII tables, some well over 150 characters wide, which
    overflow a page as monospace text. They become real tables that wrap.

Printing is done by headless Google Chrome, so the output matches the page in a
browser. Needs `markdown` (uv fetches it) and Chrome at the usual macOS path.
"""

from __future__ import annotations

import html
import re
import shutil
import subprocess
import sys
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
FONT = ROOT / "build/fonts/LabMono-Regular.ttf"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

DETAILS_RE = re.compile(r"<details>\s*<summary>(.*?)</summary>\s*(.*?)</details>", re.S)
RESULT_RE = re.compile(r"```\n(\+-[-+]*\n.*?)\n```", re.S)
H3_RE = re.compile(r"^### (.+)$", re.M)

# One entry per document: source, output, title (also the page footer), the h2 headings that start a page,
# the h3 that starts a page, and the note under the title.
DOCS = [
    dict(src="LAB-GUIDE.md", pdf="LAB-GUIDE.pdf", html="lab-guide.html",
         title="3 a.m. Blast Radius: Lab Guide", footer="3 a.m. Blast Radius · lab guide",
         h2_pages=("Part 2:", "Part 3:", "Part 4:", "Part 5:", "Stretch challenges", "Answers"),
         h3_page="The readiness check",
         note=('<b>Printed copy.</b> Queries copy out of this PDF correctly in macOS Preview and in Chrome. '
               'If a pasted query ever fails, copy it from <code>LAB-GUIDE.md</code> or the files in '
               '<code>queries/</code> in the repository or zip instead.')),
    dict(src="FACILITATOR-GUIDE.md", pdf="FACILITATOR-GUIDE.pdf", html="facilitator-guide.html",
         title="3 a.m. Blast Radius: Facilitator Guide", footer="3 a.m. Blast Radius · facilitator guide · SPOILERS",
         h2_pages=("3. What must", "4. Run of show", "6. The floor", "8. Questions", "Appendix A"),
         h3_page=None,
         note=('<b>Printed copy.</b> The living version is <code>FACILITATOR-GUIDE.md</code>; it is generated, so edit '
               '<code>build/docs/FACILITATOR.tmpl.md</code>, not this file.')),
]

CSS = """
/* Lab Mono: Source Code Pro with a raised underscore, so queries copy out of the PDF intact on macOS.
   See build/fonts/make_labmono.py. */
@font-face { font-family: "Lab Mono"; src: url("__FONT__"); }
@page {
  size: Letter;
  margin: 0.6in 0.65in 0.7in;
  @bottom-left { content: "__FOOTER__"; font: 8pt -apple-system, Helvetica, sans-serif; color: #888; }
  @bottom-right { content: "Page " counter(page) " of " counter(pages); font: 8pt -apple-system, Helvetica, sans-serif; color: #888; }
}
html { font: 10pt/1.45 -apple-system, "Helvetica Neue", Helvetica, Arial, sans-serif; color: #1d1d1f; }
body { margin: 0; }
h1 { font-size: 22pt; line-height: 1.15; margin: 0 0 4pt; color: #7a1f1f; }
h1 + p { font-size: 11pt; color: #444; margin-top: 0; }
h2 { font-size: 15pt; color: #7a1f1f; border-bottom: 1.5pt solid #7a1f1f; padding-bottom: 3pt; margin: 18pt 0 8pt; break-after: avoid; }
h2.page { break-before: page; margin-top: 0; }
h3 { font-size: 11.5pt; margin: 14pt 0 4pt; color: #1d1d1f; break-after: avoid; }
h3.page { break-before: page; margin-top: 0; }
p, li { orphans: 3; widows: 3; }
p:has(+ pre), p:has(+ table), p:has(+ ol), p:has(+ ul) { break-after: avoid; }
a { color: #0b5cad; text-decoration: none; }
hr { display: none; }
code { font: 8.8pt "Lab Mono", Menlo, monospace; background: #f2f4f7; padding: 0 2pt; border-radius: 2pt; }
pre { font: 8pt/1.35 "Lab Mono", Menlo, monospace; background: #f5f7fa; border: 0.6pt solid #d9dee5;
      border-left: 3pt solid #7a1f1f; border-radius: 3pt; padding: 6pt 8pt; white-space: pre-wrap;
      break-inside: avoid; margin: 6pt 0; }
pre code { background: none; padding: 0; font: inherit; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0 8pt; font-size: 9pt; break-inside: avoid; }
th, td { border: 0.6pt solid #d0d6de; padding: 3pt 5pt; text-align: left; vertical-align: top; }
th { background: #f6ecec; font-weight: 600; }
table.result { font: 7.4pt/1.3 "Lab Mono", Menlo, monospace; border-left: 3pt solid #2e8b57; }
table.result th { background: #eaf5ee; }
p.rows { font-size: 8pt; color: #666; margin: -4pt 0 8pt; }
blockquote { margin: 8pt 0; padding: 5pt 9pt; background: #fff8e6; border-left: 3pt solid #e0a800; }
blockquote p { margin: 0; }
.print-note { font-size: 9pt; background: #eef5fc; border: 0.6pt solid #b9d3ee; border-radius: 3pt; padding: 6pt 9pt; margin: 8pt 0 12pt; }
.answer-ref { font-size: 9pt; color: #555; font-style: italic; }
"""


def ascii_table_to_html(block: str) -> str:
    rows = [l for l in block.splitlines() if l.startswith("|")]
    cells = [[c.strip() for c in r.strip().strip("|").split(" | ")] for r in rows]
    head, body = cells[0], cells[1:]
    out = ['<table class="result"><thead><tr>']
    out += [f"<th>{html.escape(h)}</th>" for h in head]
    out.append("</tr></thead><tbody>")
    for r in body:
        out.append("<tr>" + "".join(f"<td>{html.escape(c)}</td>" for c in r) + "</tr>")
    out.append("</tbody></table>")
    tail = re.search(r"^(\d+ rows?)$", block, re.M)
    if tail:
        out.append(f'<p class="rows">{tail.group(1)}</p>')
    return "\n\n" + "".join(out) + "\n\n"


LIST_ITEM = re.compile(r"^\s*(?:[-*]|\d+\.) ")


def blank_line_before_lists(text: str) -> str:
    """GitHub starts a list right after a paragraph; python-markdown wants a blank line
    first. The facilitator guide's step cards rely on the GitHub behaviour."""
    out, fenced = [], False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
        elif (not fenced and LIST_ITEM.match(line) and out and out[-1].strip()
              and not LIST_ITEM.match(out[-1]) and not out[-1].startswith((" ", "|", ">"))):
            out.append("")
        out.append(line)
    return "\n".join(out) + "\n"


def copy_test(md: str, pdf: Path) -> None:
    """Every Cypher block must come out of the PDF intact when copied on macOS.

    Apple's PDFKit (Preview, Safari, Quick Look) pasted each underscore of
    `FIRED_ON` onto a line of its own, which Neo4j Browser rejects. It is what an
    attendee on a Mac would use, so test with it, comparing with all whitespace
    removed (indentation and line breaks legitimately change). Needs `swift`."""
    if not shutil.which("swift"):
        print("  copy test skipped: needs macOS (swift)")
        return
    r = subprocess.run(["swift", str(ROOT / "build/pdf_text.swift"), str(pdf)], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"copy test could not read {pdf.name}:\n{r.stderr}")
    squash = lambda s: re.sub(r"\s+", "", s)
    pasted = squash(r.stdout)
    blocks = re.findall(r"```cypher\n(.*?)\n```", md, re.S)
    # Count occurrences: H1, H3, H5 and H7 are the same statement, and an intact
    # copy of one must not vouch for a broken copy of another.
    need = {squash(b): sum(squash(x) == squash(b) for x in blocks) for b in blocks}
    bad = [b for b in blocks if pasted.count(squash(b)) < need[squash(b)]]
    if bad:
        sys.exit(f"copy test FAILED for {len(bad)} of {len(blocks)} queries in {pdf.name}; first:\n{bad[0]}")
    print(f"  copy test: all {len(blocks)} queries paste back intact")


def render(doc: dict) -> None:
    src, html_out, pdf_out = ROOT / doc["src"], ROOT / "build/.work" / doc["html"], ROOT / doc["pdf"]
    text = re.sub(r"<!-- GENERATED.*?-->\s*", "", src.read_text(), flags=re.S)

    answers = []

    def move(m: re.Match) -> str:
        heading = H3_RE.findall(text[:m.start()])
        title = heading[-1] if heading else f"Answer {len(answers) + 1}"
        summary = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        if summary and summary != "Query and result":      # e.g. the two hints of S11
            title = f"{title} ({summary})"
        answers.append((title, m.group(2).strip()))
        return f'<p class="answer-ref">Solution: see "{html.escape(title)}" in the Answers section at the back.</p>'

    text = DETAILS_RE.sub(move, text)
    if answers:
        text += "\n\n---\n\n## Answers\n\nSolutions to the stretch challenges. No peeking until you have tried.\n\n"
        for title, body in answers:
            text += f"### {title}\n\n{body}\n\n"

    text = RESULT_RE.sub(lambda m: ascii_table_to_html(m.group(1)), text)

    text = blank_line_before_lists(text)
    body = markdown.markdown(text, extensions=["tables", "fenced_code", "sane_lists"])
    for label in doc["h2_pages"]:
        body = body.replace(f"<h2>{label}", f'<h2 class="page">{label}', 1)
    # The lab guide's readiness check gets a page of its own: it prints as a one-page handout.
    if doc["h3_page"]:
        body = body.replace(f"<h3>{doc['h3_page']}", f'<h3 class="page">{doc["h3_page"]}', 1)
    note = f'<div class="print-note">{doc["note"]}</div>'
    first_h2 = body.find("<h2")
    body = body[:first_h2] + note + body[first_h2:]

    page = ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            f"<title>{doc['title']}</title><style>{CSS.replace('__FOOTER__', doc['footer']).replace('__FONT__', FONT.as_uri())}</style></head>"
            f"<body>{body}</body></html>")
    html_out.parent.mkdir(parents=True, exist_ok=True)
    html_out.write_text(page)

    r = subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={pdf_out}", html_out.as_uri()], capture_output=True, text=True)
    if r.returncode or not pdf_out.exists():
        sys.exit(f"Chrome failed:\n{r.stderr}")
    print(f"wrote {pdf_out.relative_to(ROOT)} ({pdf_out.stat().st_size / 1e3:.0f} kB"
          + (f", {len(answers)} answers moved to the appendix)" if answers else ")"))
    copy_test(src.read_text(), pdf_out)


def main() -> None:
    for doc in DOCS:
        render(doc)


if __name__ == "__main__":
    main()
