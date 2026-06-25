---
name: create-104-resume-from-draft
description: Create or update a company-specific 104 resume from an existing job-application package in your notes vault, entirely through the current cmux browser session. Copy a complete existing 104 resume when creating a new one, then tailor only its resume attachment, self-introduction, and 專長 while preserving common fields. Use when asked to build, refresh, or review a 104 resume; optionally attach explicitly supplied supporting documents. Do not use this skill to submit the job application.
---

# Create a 104 Resume From a Job Draft

Build or update one tailored 104 resume in the caller's cmux workspace. Treat the job-application documents as the source of truth, preserve other 104 resumes, and stop before applying.

## Scope and safety

- Use the `cmux-browser` and `cmux-workspace` workflows when available.
- Target the caller workspace and an explicit browser surface. Do not select a workspace, focus a pane, or rearrange layout.
- Create or update the 104 resume only. Never click the final job-application submit control.
- Do not change resume visibility, shared profile fields, or other resume cards unless the user explicitly asks.
- Upload a transcript, military document, or other sensitive file only when the user explicitly identifies that file for this 104/company workflow.
- Reuse a matching company resume instead of creating a duplicate.
- When no matching resume exists, copy a complete existing resume. Never start from a blank resume unless the user explicitly approves that fallback.
- In the copied target, change only its title, resume/supporting attachments, self-introduction, and 專長. Preserve education, experience, skills, preferences, languages, certificates, and all other common sections.

## 1. Locate the application package

Search under the linked Obsidian vault first. Set `APPLICATIONS_DIR` to your
job-application records directory:

```bash
rg --files -L "${APPLICATIONS_DIR:?set APPLICATIONS_DIR to your applications folder}" \
  | rg '<company>|<role>|Self Introduction|自我介紹|README|Cover Letter'
```

The usual package is:

```text
<applications-dir>/<company>/<role>/
├── README.md
├── Self Introduction.md
├── Cover Letter.md
└── <company> 產品研究.md
```

Read `README.md` for the exact role, status, job URL, chosen resume version, and required attachments. Use `Self Introduction.md` or `104 自我介紹.md` for the 104 introduction; do not substitute the cover letter.

Because the notes vault can be an iCloud-backed symlink:

- Resolve and reread the real target immediately before editing 104.
- Check `stat` and all same-role matching files if the user says the draft changed.
- If disk content is unchanged, do not guess from an editor's unsaved buffer; ask the user to save or identify the other file.

Extract the exact introduction body and enforce the 1000-character limit:

```bash
python3 scripts/extract_self_introduction.py \
  "<application-folder>/Self Introduction.md" --json
```

## 2. Resolve and verify files

- Resolve the resume path named by `README.md`; treat that PDF as the required source of truth and prefer the company-approved release PDF over similarly named drafts.
- Use an explicitly supplied resume path only when the user asks to override the README selection.
- Confirm every file exists and is under 20 MB before opening the uploader.
- Inspect the PDF metadata and first rendered page when file identity or quality is uncertain.
- Keep display labels concise: `履歷 PDF`, `成績單`, `結訓令`.

Do not silently replace the selected resume version. Ask only when two plausible files remain after checking the application package.

Create a renamed upload copy without modifying the README-selected source:

1. Derive `<companyname>` from the canonical company name in `README.md`. Use a lowercase ASCII slug containing only `a-z` and `0-9`; remove spaces and punctuation. For example, `Trend Micro` becomes `trendmicro`.
2. Create a unique directory with `mktemp -d /tmp/104-resume-upload.XXXXXX`.
3. Copy the source PDF to that directory as `resume_<companyname>.pdf`.
4. Check that the copied file exists, has the same byte size as the source, and remains under 20 MB.
5. Upload only this renamed copy as the resume attachment. Do not upload the original filename.
6. Keep the temporary file until 104 shows the saved attachment with the renamed filename. Then remove the unique temporary directory and confirm it no longer exists.

Limit cleanup to the unique directory returned by `mktemp`; never remove the source PDF or unrelated `/tmp` content.

## 3. Copy or target a complete 104 resume

Inspect the caller workspace without changing focus:

```bash
cmux identify --json
cmux list-panels --workspace "${CMUX_WORKSPACE_ID:-}" --json
```

Use the existing logged-in 104 browser surface. Open My104's resume manager and list the resume cards.

- If a matching `<company>履歷` card exists, open and update it.
- Otherwise choose a complete source resume in this order:
  1. A copy source explicitly named in the application `README.md`
  2. A source resume explicitly named by the user
  3. The most complete general-purpose resume
  4. The most recently verified complete existing resume
- Prefer a general-purpose source over another company's tailored resume. If only company-specific sources are available, copy the most complete one and remove all inherited company-specific content during replacement.
- If multiple plausible source resumes remain, ask the user instead of guessing.
- Record the source resume title and visible section/attachment state so it can be checked for accidental changes later.
- Choose `新增履歷` -> `複製履歷`, select the source, and name the copy `<company>履歷`. Do not choose `手動建立` or `一般履歷`.
- Verify that a separate target resume card was created and that the source resume remains unchanged before tailoring the copy.
- If copying is unavailable or no complete source exists, stop and ask the user. Do not silently fall back to a blank resume.
- If a blank target was created accidentally, stop and report its state. Do not delete it or create another duplicate without explicit user direction.
- Links with `target=_blank` may create another cmux browser surface. Run `list-panels` again and continue with the new explicit `surface:N`.
- Refresh snapshots after navigation, modal changes, or saves; element refs are not stable.

## 4. Attach the tailored resume

Use the `附件` section, not a public link:

1. Inspect the target copy's inherited attachments.
2. Remove or replace the inherited resume attachment and any previous-company attachment. Never modify the source resume's attachments.
3. Preserve a generic attachment only when it remains relevant; include sensitive supporting documents only when explicitly requested for the current company.
4. Click `[data-e2e="btn-create-portfolio"]`.
5. Set `[data-e2e="input-portfolio-name"]` to `履歷 PDF`.
6. Open `[data-e2e="input-portfolio-uploadfile"]`.
7. Use Computer Use only for the native macOS file picker inside cmux; navigate with Command-Shift-G and choose the temporary `resume_<companyname>.pdf` copy.
8. Save and verify that the target contains exactly one current `履歷 PDF` attachment with the renamed filename and no previous-company resume attachment.
9. Delete the unique temporary upload directory only after that verification.

Repeat only for explicitly requested supporting documents.

Important cmux CLI parsing rule: do not put `--snapshot-after` after fill text. Run `fill` and `snapshot` as separate commands, or the option can become part of the saved text.

## 5. Set the self-introduction

1. Open `[data-gtm-cprofile="edit-個人資料-編輯"]`.
2. Replace `[data-e2e="input-bio"] .ql-editor` with the exact extracted body.
3. Read the text back and compare its wording, numbers, and paragraph order with the source file.
4. Save with `[data-e2e="btn-submit"]`.

104 may count fewer characters than the Markdown source because rich-text normalization removes some newlines. Preserve the text if it remains under 1000 characters.

If 104 asks whether to synchronize other resumes, verify that only the self-introduction was changed. The dialog states that `個人簡介` is excluded from synchronization. If any shared field changed, cancel and ask the user instead of confirming.

## 6. Create the 專長 section

Use 104's built-in examples to calibrate style: name a coherent capability area and explain what tasks the candidate can complete. Do not paste a keyword cloud or invent experience.

Replace the copied resume's company-tailored 專長 content with one target-specific section. Do not append the new section while leaving the previous company's 專長 in place.

Create one target-specific section:

- **Name:** a role-level capability such as `雲端基礎設施與軟體工程`, not a single tool.
- **Description:** 4-5 concise bullets. Each bullet should pair a capability with evidence, scale, outcome, or concrete tools from the resume and application package.
- **Tags:** up to 10 recognized 104 tags that directly match both the candidate and role.

Suggested bullet categories for infrastructure/software roles:

1. Deployment automation
2. Linux and container platforms
3. Backend/system development
4. Observability and operations
5. Cloud and CI/CD

Operate the form with stable selectors:

- Open: `[data-gtm-cprofile="edit-pg-專長"] button`
- Name: `#form-component-skill input.multiselect`, then press Enter
- Description: `[data-e2e="input-description"] .ql-editor`
- Tag input: `#form-component-skill input.form-element-tag-input__input`
- Save: `#form-component-skill [data-e2e="btn-submit"]`

For tags, type one exact term, wait for autocomplete, and click the visible `.form-element-inputbox--tag-active .multiselect__content-wrapper .multiselect__option`. Do not press Enter on `無搜尋結果`. Recommendation positions reorder after every selection; never select by recommendation number. Verify the accepted tag texts from `.form-element-tag-input__tag .text-truncate`.

After saving, 104 opens `專長版型`. Prefer `列表式` for evidence-rich descriptions, save again, and verify the rendered section.

## 7. Final verification

Read the live 104 page and confirm:

- Correct resume card/title
- Target was copied from the recorded complete source; no blank-resume workflow was used
- Source resume and all other resume cards remain unchanged
- Education, experience, skills, preferences, languages, certificates, and other common target sections remain intact
- Correct `resume_<companyname>.pdf` filename and `履歷 PDF` label
- No inherited previous-company resume attachment, self-introduction, or 專長 remains in the target
- Temporary upload directory removed while the README-selected source remains unchanged
- Exact self-introduction body
- 專長 name, 4-5 evidence bullets, and accepted tags
- Each explicitly requested supporting document
- No application was submitted

Report what was created or updated and any item that still needs user review. Do not claim success from a click alone; verify the rendered page state.
