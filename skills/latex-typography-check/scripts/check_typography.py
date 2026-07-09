#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pdfplumber>=0.11"]
# ///
"""Lint the line-break typography of a compiled PDF.

Rules (formal English typesetting):
  hyphen-split   A word is hyphenated across a line break (line ends in "-").
  punct-start    A line starts with closing punctuation (, . ; : ! ? ) ] …).
  number-start   A wrapped continuation line starts with a bare number.
  runt           The last line of a multi-line paragraph has fewer than
                 --min-last-words words (default 3).

Optionally parses a LaTeX .log (--log) for Overfull/Underfull \\hbox warnings.

Works on the rendered PDF via pdfplumber word geometry: words are clustered
into visual rows, rows are split into segments at large horizontal gaps (so
two-column lines like `twocolentry` or `\\hfill` dates are not misread as one
line), and segments are grouped into paragraphs by left-edge alignment and
vertical leading. Bullet markers (• – etc.) always start a new paragraph.

Exit code: 0 = clean, 1 = violations found, 2 = usage/input error.
"""

import argparse
import json
import re
import statistics
import sys

try:
    import pdfplumber
except ImportError:
    sys.exit(
        "pdfplumber is not installed. Run this script via uv, which installs it "
        "automatically:\n  uv run check_typography.py <pdf>\n"
        "or install it manually: pip3 install pdfplumber"
    )

BULLET_MARKERS = {"•", "◦", "‣", "▪", "·", "–", "—", "*", "∗", "-", "○", "●", "◆", "►", "→"}
RE_HYPHEN_END = re.compile(r"[A-Za-z][-­‐]$")
RE_PUNCT_START = re.compile(r"^[,.;:!?%)\]}»”’…，。、；：！？』」）]")
RE_DIGIT_START = re.compile(r"^\d")
RE_WORDISH = re.compile(r"[0-9A-Za-zÀ-ɏ一-鿿]")

RE_LOG_BOX = re.compile(
    r"^(Overfull|Underfull) \\[hv]box \(([^)]+)\)(?: in paragraph| detected)?"
    r"(?: at lines? (\d+)(?:--(\d+))?)?",
    re.MULTILINE,
)


def cluster_rows(words, y_tol):
    """Group words sharing a baseline into visual rows."""
    rows = []
    for w in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if rows and abs(w["top"] - rows[-1]["top"]) <= y_tol:
            rows[-1]["words"].append(w)
        else:
            rows.append({"top": w["top"], "words": [w]})
    for r in rows:
        r["words"].sort(key=lambda w: w["x0"])
    return rows


def split_segments(row, gap):
    """Split a visual row into independent text runs at large x-gaps."""
    segs = []
    cur = [row["words"][0]]
    for w in row["words"][1:]:
        if w["x0"] - cur[-1]["x1"] > gap:
            segs.append(cur)
            cur = [w]
        else:
            cur.append(w)
    segs.append(cur)
    return segs


def make_line(seg_words):
    marker = None
    if len(seg_words) >= 2 and seg_words[0]["text"] in BULLET_MARKERS:
        marker, seg_words = seg_words[0], seg_words[1:]
    return {
        "marker": marker,
        "words": seg_words,
        "text": " ".join(w["text"] for w in seg_words),
        "x0": seg_words[0]["x0"],
        "x1": seg_words[-1]["x1"],
        "top": seg_words[0]["top"],
    }


def build_paragraphs(lines, median_size, x_tol, leading_factor, max_indent=24.0):
    """Group lines into paragraphs by left-edge alignment + vertical leading.

    The paragraph's left edge is taken from its body (second line onward) so
    that a \\parindent-ed first line still groups with its continuations.
    """
    max_leading = leading_factor * median_size
    paragraphs = []
    for ln in lines:  # lines arrive in top-down reading order
        attached = False
        if ln["marker"] is None:
            for para in reversed(paragraphs):
                last = para[-1]
                dy = ln["top"] - last["top"]
                if dy <= 0 or dy > max_leading:
                    continue
                body_x0 = para[1]["x0"] if len(para) > 1 else para[0]["x0"]
                aligned = abs(ln["x0"] - body_x0) <= x_tol
                # single-line para so far: allow its first line to be indented
                dedent = len(para) == 1 and 0 < para[0]["x0"] - ln["x0"] <= max_indent
                if aligned or dedent:
                    para.append(ln)
                    attached = True
                    break
        if not attached:
            paragraphs.append([ln])
    return paragraphs


def word_count(line):
    return sum(1 for w in line["words"] if RE_WORDISH.search(w["text"]))


def snippet(text, limit=70):
    return text if len(text) <= limit else text[: limit - 1] + "…"


def check_pdf(path, opts):
    violations = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            # x_tolerance must sit below TeX's interword space (~2-3pt at 10-11pt
            # fonts) or whole justified lines merge into single "words"
            words = page.extract_words(
                keep_blank_chars=False,
                use_text_flow=False,
                x_tolerance=opts.word_tol,
                extra_attrs=["size"],
            )
            if not words:
                continue
            median_size = statistics.median(w["size"] for w in words)
            lines = []
            for row in cluster_rows(words, opts.y_tol):
                for seg in split_segments(row, opts.gap):
                    lines.append(make_line(seg))
            paragraphs = build_paragraphs(lines, median_size, opts.x_tol, opts.leading_factor)

            for para in paragraphs:
                for i, ln in enumerate(para):
                    where = {"page": page.page_number, "y": round(ln["top"])}
                    if RE_HYPHEN_END.search(ln["text"]):
                        violations.append(
                            {
                                **where,
                                "rule": "hyphen-split",
                                "text": snippet(ln["text"]),
                                "detail": "word split across lines"
                                + (" (at paragraph end — stray hyphen?)" if i == len(para) - 1 else ""),
                            }
                        )
                    if RE_PUNCT_START.match(ln["text"]):
                        violations.append(
                            {
                                **where,
                                "rule": "punct-start",
                                "text": snippet(ln["text"]),
                                "detail": f"line begins with '{ln['text'][0]}'",
                            }
                        )
                    if i > 0 and RE_DIGIT_START.match(ln["text"]):
                        violations.append(
                            {
                                **where,
                                "rule": "number-start",
                                "text": snippet(ln["text"]),
                                "detail": "wrapped line begins with a number — tie it to the previous word",
                            }
                        )
                if len(para) >= 2:
                    wc = word_count(para[-1])
                    if wc < opts.min_last_words:
                        violations.append(
                            {
                                "page": page.page_number,
                                "y": round(para[-1]["top"]),
                                "rule": "runt",
                                "text": snippet(para[-1]["text"]),
                                "detail": (
                                    f"paragraph last line has {wc} word(s), want ≥ {opts.min_last_words}; "
                                    f"¶ begins “{snippet(para[0]['text'], 40)}”"
                                ),
                            }
                        )
    return violations


def check_log(path):
    warnings = []
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except OSError as e:
        sys.exit(f"cannot read log file: {e}")
    for m in RE_LOG_BOX.finditer(text):
        kind, why, l1, l2 = m.groups()
        loc = f"source lines {l1}–{l2 or l1}" if l1 else "location unknown"
        warnings.append({"rule": f"{kind.lower()}-box", "detail": f"{why}, {loc}"})
    return warnings


def main():
    ap = argparse.ArgumentParser(description="Lint line-break typography of a compiled PDF.")
    ap.add_argument("pdfs", nargs="+", help="PDF file(s) to check")
    ap.add_argument("--log", help="LaTeX .log file to scan for Overfull/Underfull hbox warnings")
    ap.add_argument("--min-last-words", type=int, default=3, help="minimum words on a paragraph's last line (default 3)")
    ap.add_argument("--gap", type=float, default=18.0, help="x-gap (pt) that splits a row into separate columns (default 18)")
    ap.add_argument("--word-tol", type=float, default=1.5, help="x tolerance (pt) separating words; must be below the interword space (default 1.5)")
    ap.add_argument("--y-tol", type=float, default=3.0, help="y tolerance (pt) for grouping words into rows (default 3)")
    ap.add_argument("--x-tol", type=float, default=2.5, help="left-edge tolerance (pt) for paragraph continuation (default 2.5)")
    ap.add_argument("--leading-factor", type=float, default=1.6, help="max leading as multiple of median font size (default 1.6)")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of a text report")
    args = ap.parse_args()

    all_violations = {}
    for pdf_path in args.pdfs:
        try:
            all_violations[pdf_path] = check_pdf(pdf_path, args)
        except Exception as e:
            sys.exit(f"error reading {pdf_path}: {e}")
    log_warnings = check_log(args.log) if args.log else []

    total = sum(len(v) for v in all_violations.values())
    if args.json:
        print(json.dumps({"violations": all_violations, "log_warnings": log_warnings,
                          "total": total}, ensure_ascii=False, indent=2))
    else:
        for pdf_path, violations in all_violations.items():
            print(f"== {pdf_path} ==")
            if not violations:
                print("  clean — no typography violations")
            for v in violations:
                print(f"  [{v['rule']:<12}] p{v['page']} y≈{v['y']:<4} “{v['text']}”")
                print(f"                 ↳ {v['detail']}")
        if log_warnings:
            print(f"== {args.log} ==")
            for w in log_warnings:
                print(f"  [{w['rule']:<12}] {w['detail']}")
        print(f"\n{total} violation(s)" + (f", {len(log_warnings)} log warning(s)" if args.log else ""))

    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
