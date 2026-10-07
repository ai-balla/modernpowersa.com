# modernpowersa.com

Website for **Modern Power Marine Services Co. (MPMS)** — static HTML/CSS/JS.

## For AI agents / maintainers — read this first

Agent instructions, the current handoff, and the activity log are kept in **`AGENT.md`**,
which ships **via FTP** in the private bundle `~/_mpms_private` (outside the web root) and
is **intentionally not stored in Git**.

➡️ **A `git clone` alone is not enough.** To work on this project:

1. Download the FTP **web root** (`/public_html`) — the website.
2. Download the FTP **private bundle** (`~/_mpms_private`) — gives `AGENT.md` + `_private/`;
   copy them into the project root.
3. Attach the Git history (see `AGENT.md` §6, "Bootstrapping on a new PC").
4. Read `AGENT.md` fully, then follow its rules and update its Handoff + Activity Log.

Credentials live in `_private/site-info.md` (FTP-only, outside the web root — never committed
and never publicly reachable).

## Channels

| Channel | Location | Contains |
|---|---|---|
| **Git** | `ai-balla/modernpowersa.com` | the public website only |
| **Web root** | FTP `/public_html` | the public website only |
| **Private bundle** | FTP `~/_mpms_private` (outside web root) | `AGENT.md` + `_private/` (credentials) |

`_archive/` and `website.zip` are local-only and are deployed nowhere.

## Deploy

```powershell
powershell -ExecutionPolicy Bypass -File .\_private\ftp-upload.ps1
```

The script does both phases: website → web root, private bundle → `~/_mpms_private`.
