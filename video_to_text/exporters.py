from __future__ import annotations

from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from .models import DocumentPage

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer
except Exception:  # pragma: no cover - optional dependency loading
    A4 = None
    ParagraphStyle = None
    getSampleStyleSheet = None
    PageBreak = None
    Paragraph = None
    SimpleDocTemplate = None
    Spacer = None


def write_markdown(output_path: Path, title: str, pages: list[DocumentPage]) -> None:
    lines = [f"# {title}", ""]
    lines.append(f"- Generated: {datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"- Pages: {len(pages)}")
    lines.append("")

    for page in pages:
        lines.append(f"## Page {page.page_number:04d}")
        lines.append(f"- Timestamp: {page.timestamp_sec:.2f}s")
        lines.append(f"- OCR confidence: {page.confidence:.3f}")
        lines.append("")
        lines.append(page.text if page.text else "(empty)")
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def write_html(output_path: Path, title: str, pages: list[DocumentPage]) -> None:
    generated = datetime.now().isoformat(timespec="seconds")
    sections = []
    for page in pages:
        text_html = "<br/>".join(escape(page.text).splitlines()) if page.text else "<em>(empty)</em>"
        sections.append(
            (
                "<article class=\"page\">"
                f"<h2>Page {page.page_number:04d}</h2>"
                f"<p class=\"meta\">timestamp {page.timestamp_sec:.2f}s | confidence {page.confidence:.3f}</p>"
                f"<div class=\"content\">{text_html}</div>"
                "</article>"
            )
        )

    html = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{escape(title)}</title>
  <style>
    :root {{
      --bg: #f4f1ea;
      --paper: #fffefb;
      --ink: #1d1c1a;
      --muted: #666055;
      --edge: #d8d1c2;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Noto Serif", "Georgia", serif;
      background: radial-gradient(circle at top left, #fbf8f1, var(--bg));
      color: var(--ink);
      line-height: 1.65;
      padding: 24px 16px 64px;
    }}
    main {{
      max-width: 900px;
      margin: 0 auto;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: clamp(1.8rem, 3vw, 2.4rem);
      letter-spacing: 0.02em;
    }}
    .summary {{
      color: var(--muted);
      margin-bottom: 28px;
      font-size: 0.95rem;
    }}
    .page {{
      background: var(--paper);
      border: 1px solid var(--edge);
      border-radius: 14px;
      padding: 18px;
      box-shadow: 0 10px 20px rgba(0,0,0,0.05);
      margin-bottom: 16px;
    }}
    .page h2 {{
      margin: 0;
      font-size: 1.2rem;
    }}
    .meta {{
      margin: 6px 0 14px;
      color: var(--muted);
      font-size: 0.85rem;
      font-family: "Consolas", "Courier New", monospace;
    }}
    .content {{
      white-space: normal;
      word-break: break-word;
    }}
  </style>
</head>
<body>
  <main>
    <h1>{escape(title)}</h1>
    <p class=\"summary\">Generated {escape(generated)} | pages {len(pages)}</p>
    {''.join(sections)}
  </main>
</body>
</html>
"""

    output_path.write_text(html, encoding="utf-8")


def write_pdf(output_path: Path, title: str, pages: list[DocumentPage]) -> None:
    if SimpleDocTemplate is None:
        raise RuntimeError("reportlab is not installed. Install reportlab to enable PDF export.")

    doc = SimpleDocTemplate(str(output_path), pagesize=A4, title=title)
    styles = getSampleStyleSheet()
    body_style = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        spaceAfter=8,
    )

    story = [Paragraph(escape(title), styles["Title"]), Spacer(1, 8)]
    story.append(
        Paragraph(
            escape(f"Generated {datetime.now().isoformat(timespec='seconds')} | pages {len(pages)}"),
            styles["Italic"],
        )
    )
    story.append(Spacer(1, 14))

    for idx, page in enumerate(pages, start=1):
        story.append(Paragraph(f"Page {page.page_number:04d}", styles["Heading2"]))
        story.append(
            Paragraph(
                escape(f"timestamp {page.timestamp_sec:.2f}s | confidence {page.confidence:.3f}"),
                styles["Italic"],
            )
        )
        story.append(Spacer(1, 6))

        text = page.text.strip() if page.text else "(empty)"
        for para in text.split("\n"):
            if para.strip():
                story.append(Paragraph(escape(para), body_style))
        story.append(Spacer(1, 6))

        if idx != len(pages):
            story.append(PageBreak())

    doc.build(story)
