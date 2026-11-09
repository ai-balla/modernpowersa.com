# modernpowersa.com

Bilingual (Arabic / English) website of **Modern Power Marine Services Co.** — شركة الطاقة الحديثة للخدمات البحرية.

- Static HTML generated from structured content by `_src/build.py` (Python 3, standard library only).
- Arabic at `/ar/`, English at `/en/`, language chooser at `/`.
- Request form handled by `forms/send.php`; its settings live outside the web root.

| Task | Read |
|---|---|
| Update text, services, projects, certificates | `_docs/CONTENT-GUIDE.md` |
| Deploy, roll back, move the old domain | `_docs/DEPLOYMENT.md` |
| Agreed Arabic/English terms | `_docs/GLOSSARY.md` |

**Production:** Hostinger deploys the `main` branch automatically. Do development on another branch and merge by pull request.

Maintainers who use the private agent handbook (`AGENT.md`, delivered separately, never in Git) should read it as well.
