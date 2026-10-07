# modernpowersa.com

Website for **Modern Power Marine Services Co. (MPMS)** — static HTML/CSS/JS.

## For AI agents / maintainers — read this first

Agent instructions, the current handoff, and the activity log are kept in **`AGENT.md`**,
which is **delivered via FTP and intentionally not stored in Git**.

➡️ **A `git clone` alone is not enough.** To work on this project:

1. Pull the full **FTP** root (this gives the website **plus** `AGENT.md` and `_private/`).
2. Attach the Git history to that folder (see `AGENT.md` §6, "Bootstrapping on a new PC").
3. Read `AGENT.md` fully, then follow its rules and update its Handoff + Activity Log.

Access details and credentials are in `_private/site-info.md` (FTP only — never committed).

## Channels

| Channel | Contains |
|---|---|
| **Git** (`ai-balla/modernpowersa.com`) | the public website only |
| **FTP** (`/public_html`) | everything: website + `AGENT.md` + `_private/` (credentials) |

`_archive/` and `website.zip` are local-only and are deployed nowhere.

## Deploy

```powershell
powershell -ExecutionPolicy Bypass -File .\_private\ftp-upload.ps1
```
