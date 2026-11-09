# Deployment, rollback and domain transition

## How the site is deployed today

- Repository: `ai-balla/modernpowersa.com` (GitHub). Production branch: **`main`**.
- Evidence that Hostinger's Git auto-deployment publishes `main`: on 9 Nov 2026 the live file `/videos/1249414-hd_1920_1080_25fps.mp4` was a 133-byte Git LFS pointer. Hostinger's Git deploy does not fetch LFS objects, so the file came from Git, not from an FTP upload.
  → **Anything merged into `main` goes live.** Development happens on other branches (current: `dev/bilingual-rebuild`).
- There is also a manual FTP script (kept privately, outside Git). Do not use FTP and Git deployment for the same files; prefer Git.
- The site is static HTML. There is **no build step on the server**: the generated `ar/`, `en/`, `index.html`, `sitemap.xml`, `robots.txt` are committed.
- Server-side code: only `forms/send.php` (PHP 8 on Hostinger).

## Environment / configuration (no secrets in Git)

| Setting | Where | Notes |
|---|---|---|
| Form recipients, sender, rate limit, salt | `~/_mpms_private/form-config.php` on the hosting account (outside `public_html`) | Copy `forms/config.sample.php`. Without this file the form refuses to send and shows the failure message. |
| `MPMS_FORM_CONFIG` env var | optional | Overrides the config path (used for local testing). |
| SPF/DKIM for the sender domain | DNS of `modernpowersa.com` | Needed so form emails are not marked as spam. Check before launch. |

## Pre-launch checks (run on the branch)

```bash
python _src/build.py --check   # content rules, bilingual completeness, expired certificates
python _src/build.py           # regenerate pages; commit the result
git status                     # only expected files changed
```

Then, on a staging copy (see below) or immediately after merge:
- Open every page in Arabic and English, on a phone and a desktop.
- Submit the form once in each language to an **authorised test mailbox** and confirm the email arrives with correct Arabic text.
- Check `https://modernpowersa.com/robots.txt`, `/sitemap.xml`, and that `/about/`, `/contact/` etc. redirect to the new pages.
- Check that `/resources/…` and `/_src/…` return 410/404.

## Staging (recommended)

Create a Hostinger subdomain such as `staging.modernpowersa.com`, connect it to the branch `dev/bilingual-rebuild` (hPanel → Advanced → Git), and protect it with a password (hPanel → Password protect directories). The preview build (`--preview`) already adds `noindex`.

## Launch (merge to production)

1. Final approval of the open items in the decision list.
2. Set `status` values, rebuild, commit.
3. Create `~/_mpms_private/form-config.php` on the server.
4. Merge `dev/bilingual-rebuild` into `main` (pull request). Hostinger deploys.
5. Run the checks above on the live site.
6. Submit the new sitemap in Google Search Console (property: `https://modernpowersa.com`).

## Rollback

- **Fast:** on GitHub, revert the merge commit on `main` (Pull request → Revert). Hostinger redeploys the previous version.
- **Manual:** `git checkout main && git reset --hard <previous-commit> && git push --force-with-lease` (only with approval; rewrites history).
- The pre-rebuild state is commit `2c880aa` on `main`.
- Hostinger also keeps daily backups (hPanel → Files → Backups) as a last resort.

## Domain transition: modernpowermarine.com → modernpowersa.com

Keep **modernpowermarine.com running** until the new site has been live and checked for at least two weeks.

**Email is separate from the website.** Moving the website does not require changing email addresses. Do **not** change the MX, SPF, DKIM, DMARC or autodiscover records of `modernpowermarine.com`. When redirecting, change only the web records (or add the redirect in the old host's control panel / WordPress).

Redirect map for the old domain (301 unless stated):

| Old URL (modernpowermarine.com) | New URL (modernpowersa.com) |
|---|---|
| `/` | `/` (language chooser) |
| `/about/`, `/webcast/`, `/team/`, `/team-details/`, `/mohamed-jazzar/`, `/abdulaziz-abdulqader-jazzar/` | `/en/company/` |
| `/services-v-1/`, `/services-v-2/`, `/services/`, `/service-category/marine-services/` | `/en/services/` |
| `/service/mechanical-works/` | `/en/services/engines-generators-propulsion/` |
| `/service/steel-works/` | `/en/services/hull-steel-coatings/` |
| `/contact/`, `/?page_id=24` | `/en/contact/` |
| `/wp-content/uploads/2024/01/profile_MPMS.pdf` | `/en/contact/?type=docs` (until a corrected profile is published) |
| Theme demo pages: `/blog-*`, `/portfolio*`, `/case-study*`, `/case-study-category/*`, `/portfolio-category/*`, `/testimonials*`, `/faq/`, `/careers/`, `/job-list-page/`, `/shortcode/`, `/about-v-*`, `/contact-v-*`, `/footer/*`, `/author/*` | **410 Gone** (these are template pages, not MPMS content) |
| Anything else | `/` |

Example for the old host's `.htaccess` (Apache), placed above the WordPress block:

```apache
RewriteEngine On
RewriteRule ^(about|webcast|team|team-details|mohamed-jazzar|abdulaziz-abdulqader-jazzar)/?$ https://modernpowersa.com/en/company/ [R=301,L]
RewriteRule ^(services-v-1|services-v-2|services|service-category/marine-services)/?$ https://modernpowersa.com/en/services/ [R=301,L]
RewriteRule ^service/mechanical-works/?$ https://modernpowersa.com/en/services/engines-generators-propulsion/ [R=301,L]
RewriteRule ^service/steel-works/?$ https://modernpowersa.com/en/services/hull-steel-coatings/ [R=301,L]
RewriteRule ^contact/?$ https://modernpowersa.com/en/contact/ [R=301,L]
RewriteRule ^wp-content/uploads/2024/01/profile_MPMS\.pdf$ https://modernpowersa.com/en/contact/?type=docs [R=301,L]
RewriteRule ^(blog-|portfolio|case-study|testimonials|faq|careers|job-list-page|shortcode|about-v-|contact-v-|footer/|author/) - [G,L]
RewriteRule ^ https://modernpowersa.com/ [R=301,L]
```

Apply the old-domain redirects **only after** the new pages are live and approved.

## Launch checklist

- [ ] Bank/financial files removed from the live server and from the public repository (or repository made private)
- [ ] Decision list items answered; statuses updated; `python _src/build.py --check` passes
- [ ] Form config on server; test submission received in both languages
- [ ] SPF/DKIM verified for the form sender
- [ ] SSL active; HTTPS redirect enabled in `.htaccess`
- [ ] All pages checked on mobile and desktop, AR and EN
- [ ] Old-URL redirects on modernpowersa.com verified
- [ ] Sitemap submitted to Google Search Console
- [ ] Two weeks later: old-domain redirects applied; email records untouched
