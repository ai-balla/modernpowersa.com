# Deployment and rollback

## Current architecture

The bilingual public website uses generated HTML as its baseline. A PHP/MySQL layer serves the normal Arabic and English URLs, applies published admin edits, and provides the blog. The contact form sends email and records requests in the admin inbox.

Public baseline templates and application code belong in Git. Live page edits, blog articles, contact requests and admin password hashes belong in the database. Never commit database exports or private configuration.

## Publishing from this PC

Double-click `deploy.cmd`. It refreshes local private settings, runs the content and Git-secret checks, connects through FTP, backs up changed files, uploads only allowlisted public files, verifies upload hashes, and checks live responses. It does not push to GitHub and does not delete files from the server. Previously verified unchanged files are skipped. Runtime media uploads and database content survive publishing.

Hostinger automatic Git publishing is not configured. A GitHub push alone does not publish this website. Development code should be committed on a branch, tested, merged to main, and pushed separately to keep source history current.

See `FTP-DEPLOYMENT.md` for commands and `ADMIN-GUIDE.md` for content management.

## Private server configuration

The following files are uploaded outside public_html, in the account-level `_mpms_private` folder:

- `form-config.php`: form recipients, sender and rate limit.
- `database-config.php`: MySQL connection settings.
- `admin-bootstrap.php`: initial admin setup, used only when no CMS admin account exists.
- `public-settings.php`: baseline public contact defaults.

The FTP login, credential documents, admin-access.json, deployment scripts and local backups never go into public_html or Git. Local settings live in `_private/`; this entire folder is ignored by Git. Local pre-commit/pre-push guards also block private paths and configured passwords.

CMS tables use the `mpms_cms_` prefix. The installer does not drop or modify pre-existing application tables.

## Verification and backups

- Validate the baseline content with `python _src/build.py --check`.
- Check PHP syntax before publishing PHP changes.
- Use `python _private/deploy-site.py --verify-live` for public-file checks.
- Image bytes may be optimized by Hostinger; the FTP file hash and a valid HTTP image response are checked separately.
- The form endpoint must reject GET with 405 and invalid POST data with 422.
- Check both languages, mobile navigation, draft isolation, publishing, articles, contact records and admin sign-out.
- Confirm actual test-email receipt separately from mail-transport acceptance.

File rollback copies are under `_private/backups/DATE-TIME/`. The private deployment manifest lists hashes and the backup location. Admin Settings can export a private content backup; also retain Hostinger database backups. Restore the matching files and database state deliberately; do not blindly delete public_html or rewrite Git history.

## Old domain

Keep modernpowermarine.com running until the replacement has been tested and approved. Do not change its email-related DNS records. The URL map is documented in `DOMAIN-TRANSITION.md`; apply it only when the owner is ready to retire the older website.
