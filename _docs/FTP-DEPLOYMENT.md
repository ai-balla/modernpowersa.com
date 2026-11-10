# Local FTP publishing

The reusable deployment pipeline is saved in this website folder. It does not push to GitHub and does not depend on Hostinger's Git integration.

- Double-click `deploy.cmd` to validate, back up, publish, and verify the website.
- Run `python _private/deploy-site.py` for a check without connecting or uploading.
- Run `python _private/deploy-site.py --test-connection` to test the FTP login.
- Run `python _private/deploy-site.py --verify-live` to compare live public files against this release.

## Private settings

`_private/deploy-secrets.json` holds FTP and database settings. The owner-supplied `FTP Accounts - db credintials.txt` is the source used to configure it. Both are ignored by Git. The legacy private uploader was updated to use the same FTP login.

`_private/database-config.php` holds the new database settings for future server-side work. The current static website and email form do not use a database; these database credentials are deliberately not deployed.

`_private/form-config.php` holds the email form configuration. During publishing, only this file is placed outside public_html, at the path the form handler reads. FTP passwords, database passwords, credential documents, and deployment scripts never go to public_html.

The current server supplied by Hostinger uses the existing FTP protocol. To use explicit encrypted FTP, set `protocol` to `ftps` and a certificate-valid hostname in the private JSON; certificate checks remain enabled.

## Safeguards

The publisher uses an explicit allowlist: ar/, en/, assets/, forms/send.php, and the five public root files. It does not upload private folders, source documents, old media, source code, credential files, or archives. It never deletes server files.

The pipeline checks Git exclusion, scans tracked content for the configured passwords, validates bilingual content, and backs up every existing file it will replace under `_private/backups/DATE-TIME/` before uploading. Each upload uses a temporary name and is downloaded again to verify its SHA-256 before publishing. A failed login stops before any server changes.

After deployment, `last-deployment.json` records the public file hashes and rollback location. `last-verification.json` records the live comparison. These reports are private and do not contain passwords.

Local Git pre-commit and pre-push hooks block private credential paths and the currently configured passwords in staged/outgoing objects. Hooks apply to this checkout only and can be bypassed by Git's explicit bypass options; never force-add secrets or bypass the guard. Other machines require the same guard installation.

## Rollback

Restore only the files listed in the deployment manifest from its matching private backup, and verify the website afterwards. The publisher intentionally provides no automatic recursive deletion or history rewriting.

## Remaining launch checks

An accepted PHP mail() call does not prove inbox delivery. After publishing, submit an authorized request in Arabic and English and confirm receipt at info@modernpowersa.com. Check the actual historic bank-document URL returns 410. Old files remain physically present until separately quarantined or removed; do not confuse blocked access with deletion.
