# Updating the MPMS website — staff guide

The website is generated from a few content files. You edit the content files; a small script builds the Arabic and English pages. Nothing appears on the public site until the change is merged into the `main` branch, because Hostinger deploys `main` automatically.

## 1. Where things are

| You want to change… | Edit this file |
|---|---|
| Company name, address, phones, emails, working hours, management, vision/mission | `_src/content/company.json` |
| A service (text, scope, deliverables) | `_src/content/services.json` |
| Project references | `_src/content/projects.json` |
| Clients, agencies, suppliers | `_src/content/organizations.json` |
| ISO certificates, contractor classification | `_src/content/certifications.json` |
| Downloadable files (e.g. company profile) | `_src/content/downloads.json` + the file in `/downloads/` |
| Menu labels, page titles, form labels and messages, privacy notice | `_src/content/pages.json` |

Do **not** edit the HTML files in `ar/` and `en/` by hand — the next build overwrites them.

## 2. The status field (most important rule)

Every record has a `status`:

| status | Meaning | Public site | Internal preview |
|---|---|---|---|
| `published` | Checked against a document and approved for publication | shown | shown |
| `draft` | Waiting for confirmation or translation | hidden | shown, marked **DRAFT** |
| `restricted` | Sensitive (e.g. defence details) — needs explicit approval | hidden | hidden |
| `withdrawn` / `expired` / `unsupported` | Must not be shown | hidden | hidden |

Before changing anything to `published`, make sure:
1. You have the supporting document (certificate, contract, letter, approved profile) and its date.
2. The client agrees to be named (for projects and client lists), and nothing confidential is exposed.
3. Both `en` and `ar` texts are complete. The build **stops** if one language is missing or empty — the site never falls back to the other language.
4. You update `source` and `reviewed` (date in `YYYY-MM-DD`).

Certificates also need a correct `expiry`. A published certificate is hidden automatically once its expiry date passes, so keep it updated after each surveillance audit.

## 3. Writing rules

- Arabic: professional Saudi business Arabic. Company name: **شركة الطاقة الحديثة للخدمات البحرية**.
- English: plain technical English. Company name: **Modern Power Marine Services Co.** (short: MPMS).
- No superlatives ("leading", "best", "world-class") unless they quote an official statement.
- No numbers (staff counts, project counts, years of experience, response times) without a document behind them.
- Do not describe stock or generated images as MPMS work. Photos of MPMS work need permission from the client/site owner.
- Keep standards and codes exactly as written on the certificate, e.g. `ISO 9001:2015`.
- See `_docs/GLOSSARY.md` for agreed terms in both languages.

## 4. Check, preview, build

You need Python 3 (free from python.org; tick "Add to PATH" during installation).

1. **Check content:** `python _src/build.py --check`
2. **Preview (includes drafts):** double-click `preview.cmd`, then open http://localhost:8000/. Drafts are marked; the preview is never uploaded.
3. **Build the public pages:** double-click `build.cmd` (or `python _src/build.py`).

## 5. Publish safely

1. Work on a branch, never directly on `main`:
   `git checkout -b content/short-description`
2. Edit content → check → preview → build.
3. Commit both the content file and the rebuilt pages:
   `git add -A && git commit -m "Update ISO 9001 expiry after surveillance audit"`
4. Push the branch and open a pull request on GitHub. Ask a second person to review the preview and the changed text.
5. Merge into `main`. Hostinger deploys within a few minutes. Open the live page in both languages to confirm.

If something goes wrong after publishing, see "Rollback" in `_docs/DEPLOYMENT.md`.

## 6. Things that must never go on the website or into Git

Bank letters or account numbers, contracts, purchase orders, price lists, passwords, personal ID documents, staff personal data, and anything marked confidential by a client. The repository is visible to anyone who has its link if it is public.
