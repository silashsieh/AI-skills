# AI-skills

Silas Hsieh's personal skill library for AI coding agents. Each skill is a
self-contained folder under [`skills/`](skills/) with a `SKILL.md` (the
instructions an agent reads) and, where useful, an `agents/openai.yaml` for
Codex and a `scripts/` helper directory.

The repo is **multi-harness**: the same `SKILL.md` files are read by both
Claude Code and Codex. This repo is the single source of truth — the agent
skill directories just symlink back to it (see [Install](#install)).

## Skills

| Skill | Purpose |
| --- | --- |
| [`coupon-ics-from-screenshot`](skills/coupon-ics-from-screenshot/SKILL.md) | Generate an Apple Calendar–compatible `.ics` file from coupon screenshots — all-day events keyed to due dates, no `VALARM` unless asked, with iCalendar validation. |
| [`create-104-resume-from-draft`](skills/create-104-resume-from-draft/SKILL.md) | Build or refresh a company-specific 104 resume from an existing job-application package, tailoring only the attachment, self-introduction, and 專長 while preserving shared fields. Stops before submitting. |
| [`fetch-104-jobs`](skills/fetch-104-jobs/SKILL.md) | Pull structured job/company data from 104 人力銀行 through a real browser session, bypassing Cloudflare. Hooks the site's own XHR and triggers an in-place fetch to capture clean JSON (direct API requests return 403). **⚠️ For web-service research/education only; may violate 104's ToS.** |
| [`resume-md-latex-pdf-sync`](skills/resume-md-latex-pdf-sync/SKILL.md) | Sync resume Markdown drafts to matching LaTeX and rebuilt PDFs (latexmk/XeLaTeX), preserving V5/V5.1 layout conventions and verifying Markdown ↔ LaTeX ↔ extracted PDF text ↔ rendered pages all agree. |

## Layout

```text
AI-skills/
├── .claude-plugin/plugin.json   # Claude Code plugin manifest
├── .codex-plugin/plugin.json    # Codex plugin manifest
├── skills/
│   └── <skill-name>/
│       ├── SKILL.md             # required: agent instructions + frontmatter
│       ├── agents/openai.yaml   # optional: Codex interface metadata
│       └── scripts/             # optional: reusable helper scripts
├── LICENSE
└── README.md
```

### SKILL.md convention

Every `SKILL.md` opens with YAML frontmatter containing two required fields:

```yaml
---
name: skill-name              # letters, numbers, hyphens only
description: Use when …       # ≤1024 chars; describe ONLY the triggering
                              # conditions, not the workflow
---
```

The `description` is what an agent matches against to decide whether to load
the skill, so lead with the situation it fires in ("Use when the user provides
coupon screenshots…"), not a summary of the steps.

## Using these skills

Distribution is not yet decided. Two general options:

- **Local symlink/copy** — point each skill folder at the directories the
  agents read (`~/.claude/skills` for Claude Code, `~/.codex/skills` for Codex).
  No manifest needed; instant and offline.
- **Plugin/marketplace** — add a `.claude-plugin/marketplace.json` so the repo
  can be installed with `/plugin marketplace add silashsieh/AI-skills` then
  `/plugin install ai-skills@ai-skills`, and updated via `git pull`. This is
  the [obra/superpowers](https://github.com/obra/superpowers) model.

The `.claude-plugin/` and `.codex-plugin/` manifests already carry the plugin
identity for the second option whenever you choose to enable it.

## Adding a skill

1. Create `skills/<skill-name>/SKILL.md` with the frontmatter above.
2. Add `agents/openai.yaml` if it should surface in Codex, and `scripts/` for
   any helpers.
3. Add a row to the table above.

## License

[MIT](LICENSE) © 2026 Silas Hsieh
