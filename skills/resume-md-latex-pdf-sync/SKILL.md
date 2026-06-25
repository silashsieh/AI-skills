---
name: resume-md-latex-pdf-sync
description: Sync resume Markdown drafts to matching LaTeX and compiled PDF outputs. Use when asked to convert, resync, or verify resume Markdown variants, follow the existing LaTeX template conventions, rebuild PDFs with latexmk/XeLaTeX, and confirm Markdown, LaTeX, extracted PDF text, and rendered PDF pages agree.
---

# Resume MD-LaTeX-PDF Sync

## Scope

Treat the current Markdown files as the source of truth. Sync only the resume
variants the user names. For each variant `<variant>` the files are:

- `<variant>.md` — source of truth
- `<variant>.tex` — LaTeX, written under the drafts `latex/` directory
- `<variant>.pdf` — compiled output, in the same `latex/` directory

Use an existing `.tex` from another variant as the style template when creating
a missing `.tex` file. Preserve the existing preamble, spacing style, heading
structure, section order, and formatting conventions unless a layout repair is
necessary.

## Workflow

1. Locate the Markdown, LaTeX, and PDF files with `rg --files` or `find`.
2. Read the current Markdown and matching `.tex` files from disk. Do not assume a previous sync is still current.
3. Compare Markdown to LaTeX line by line:
   - Strip Markdown heading markers and bullets for comparison.
   - Ignore formatting-only differences such as Markdown bold/code/italic versus LaTeX `\textbf{}`, `\texttt{}`, `\textit{}`.
   - Normalize LaTeX escapes: `\&`, `\%`, `\_`, `\textasciitilde{}`.
   - Normalize arrows and symbols: `→` to `$\rightarrow$`, `↔` to `$\leftrightarrow$`, `×` to `$\times$`.
   - Normalize whitespace, non-breaking spaces, and PDF/LaTeX line wrapping.
   - Normalize any URL display convention: the Markdown may contain a full `https://github.com/<username>` link while the PDF/LaTeX displays the bare `github.com/<username>`.
   - Do not ignore wording, numbers, project titles, roles, dates, parenthetical qualifiers, or technology lists.
4. Patch only real drift in `.tex`. Keep edits scoped to the requested variants.
5. Re-run the Markdown-to-LaTeX comparison after patching. It must report OK for all requested variants before compiling.
6. Compile each requested variant's PDF from the `latex/` directory:

```bash
latexmk -g -xelatex -interaction=nonstopmode -halt-on-error '<variant>.tex'
```

Request escalation if XeLaTeX needs system font/cache access.

7. If compilation succeeds but a PDF spills to an extra page, keep the Markdown content intact and repair layout only. Prefer small spacing or margin adjustments that match the existing file style. Do not delete or rewrite resume content just to fit one page.
8. Verify the generated PDFs with text extraction and visual rendering.

## Markdown To LaTeX Mapping

Use the existing `.tex` style as the authority for formatting:

- Resume title and contact block stay in the existing `header` environment.
- Education entries use `twocolentry` for date alignment.
- Project titles use `onecolentry`, bold project name, role text, and `\hfill` date.
- Markdown `**bold**` becomes `\textbf{...}`.
- Markdown `*italic*` becomes `\textit{...}`.
- Markdown inline code becomes `\texttt{...}` with escaped underscores.
- Literal percent signs, ampersands, and underscores must be escaped as `\%`, `\&`, and `\_`.
- Use visible `\textasciitilde{}` for approximate counts such as `~150`; use LaTeX `~` only when intentionally creating a non-breaking space.
- Preserve literal hyphen ranges such as `20-50 min/day` when the Markdown uses that form.
- Use LaTeX arrows and multiplication signs where the existing templates do: `$\rightarrow$`, `$\leftrightarrow$`, `$\times$`.

## Verification

Run all checks before reporting completion. Run each per-variant command once
for every variant you synced.

1. Source check:
   - Confirm every non-empty Markdown content line appears in the `.tex` after normalization.
   - Report OK per variant. If any line is missing, inspect manually and patch the `.tex`.

2. Build check:

```bash
grep -H -E '^!|Fatal error|LaTeX Error|Package fontspec Error' '<variant>.log'
```

No matches are expected. Benign warnings may include `lastpage`, `xeCJK` unknown CJK monofont, and very small overfull boxes; mention them if relevant.

3. Page-count check:

```bash
pdfinfo '<variant>.pdf'
```

Each PDF should be one letter-size page unless the user explicitly accepts a longer resume.

4. PDF text check:

```bash
pdftotext '<variant>.pdf' -
```

Compare extracted text back to Markdown after normalizing line wraps, curly quotes, dashes, Markdown formatting, and the URL display convention. If extraction splits dates or headings across lines, verify the words are still present in order.

5. Visual check:

```bash
mkdir -p /tmp/resume-pdf-check
pdftoppm -png -r 144 '<variant>.pdf' /tmp/resume-pdf-check/<variant>
```

Open each rendered PNG with the image viewer and check for clipping, overlap, blank pages, bad glyphs, unreadable text, and suspicious wraps. Treat PDF rendering as the final layout authority.

## Final Report

Keep the final response concise. Include:

- Which `.tex` and `.pdf` files were synced.
- The meaningful wording fixes or layout-only changes made.
- Markdown-to-LaTeX check result.
- Markdown-to-PDF text check result.
- PDF page count and visual inspection result.
- Any remaining benign warnings.
