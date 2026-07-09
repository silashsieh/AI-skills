---
name: latex-typography-check
description: Verify the line-break typography of a compiled PDF (LaTeX resume, cover letter, paper, or any formal English document). Use after building a PDF with latexmk/xelatex/lualatex, or when asked to check typography, line breaks, hyphenation, widows/orphans/runts, or "bad breaks" in a PDF. Rules enforced — no word hyphenated across a line break, no punctuation at line start, no bare number starting a wrapped line, paragraph last lines must have at least 3 words. Checks the rendered PDF (not the .tex source), so source linters like chktex cannot replace it.
---

# LaTeX Typography Check

Formal English typesetting has line-break rules that no source-level linter
(chktex, TeXtidote) can verify, because they only exist after TeX breaks the
paragraph into lines. This skill checks the **rendered PDF**.

## Rules

| Rule | Meaning | Typical LaTeX fix |
| --- | --- | --- |
| `hyphen-split` | A word was hyphenated across a line break | `\hyphenpenalty=10000 \exhyphenpenalty=10000` in preamble; or rewrite the sentence |
| `punct-start` | A line starts with `, . ; : ! ? ) ]` … | Almost always a space **before** the punctuation in the source — grep the `.tex` for ` ,` / ` .` and delete the space |
| `number-start` | A wrapped continuation line starts with a bare number | Tie the number to the word before it: `by~40\%`, `Figure~3`, `2~GB` |
| `runt` | Last line of a multi-line paragraph has < 3 words | `\looseness=-1` on the paragraph to pull the line up, or extend/shorten the text until the runt disappears |

With `--log <file.log>` it also surfaces `Overfull \hbox` / `Underfull \hbox`
warnings with their source line ranges.

## Run

```bash
uv run scripts/check_typography.py <file.pdf> [--log <file.log>]
```

`uv` installs the one dependency (pdfplumber) automatically on first run. No
`uv`? `pip3 install pdfplumber` then run with `python3`. Exit code 0 = clean,
1 = violations. Useful flags:

- `--min-last-words N` — runt threshold (default 3)
- `--gap PT` — x-gap that splits one visual row into separate columns
  (default 18 pt). Lower it if unrelated column texts get glued together;
  raise it if a stretched justified line gets split in two.
- `--json` — machine-readable output

## Workflow

1. Build the PDF as usual (for resumes: `latexmk -pdf` with XeLaTeX from the
   `履歷草稿/latex/` directory).
2. Run the checker on the PDF **and** the `.log`.
3. For each violation, find the text in the `.tex` source and apply the fix
   from the table above. Prefer the least invasive fix: a `~` tie or a space
   deletion beats rewriting; rewriting beats fighting TeX with penalties.
4. Rebuild and re-run until exit code 0. Fixes shift line breaks, so new
   violations can appear after a fix — always re-run.
5. Confirm visually: open the PDF and eyeball the paragraphs you touched
   (a fix can degrade justification spacing even when the rules pass).

### Prevention preamble

For documents that must never hyphenate (resumes, cover letters):

```latex
\usepackage{microtype}      % protrusion/expansion keeps unhyphenated text pretty
\hyphenpenalty=10000
\exhyphenpenalty=10000
```

Keep `microtype` — banning hyphenation without it produces loose, gappy
justified lines (which then show up as Underfull hbox warnings).

## Interpreting results — known limits

- **Two-column lines** (`twocolentry` education rows, `\hfill` project/date
  headers) are handled by the `--gap` split; a right-aligned date column is
  treated as its own single-line paragraph, so no rules fire on it.
- **Bullet lists**: a leading `•`/`–` marker always starts a new paragraph, so
  consecutive tight bullets are not misread as one wrapped paragraph.
- The `runt` rule only fires on paragraphs with ≥ 2 lines, so headings and
  single-line entries are exempt. A header block (name line + title line with
  identical left edge and tight leading) can occasionally be misgrouped as one
  paragraph — verify a surprising runt against the actual PDF before "fixing".
- `number-start` fires only on continuation lines; a bullet that legitimately
  *begins* with a number is fine.
- **Flush-left paragraphs with zero vertical gap** (consecutive `\noindent`
  paragraphs, `\parskip=0`) merge into one detected paragraph, which can hide
  a runt at the boundary. Documents using default `\parindent`, nonzero
  `\parskip`, or bullet lists are unaffected.
- `--word-tol` (default 1.5 pt) must stay below the font's interword space;
  if the report shows words glued together (`likethisexample`), the tolerance
  is fine at default — but if snippets show single letters split apart, raise
  it slightly.
- The checker reports `p<page> y≈<points-from-top>` — use the y-coordinate to
  locate the line visually in the PDF, then grep the snippet in the `.tex`.
