# MPMS website management

Open https://modernpowersa.com/admin/. The initial account is saved locally in `_private/admin-access.json`. Never upload that file to Git or public_html. The admin login is separate from FTP and the database.

## Pages

Choose Pages, then the Arabic or English page. Edit the text fields without changing the website layout. Save a private draft, preview it while signed in, and publish when ready. Restore original page removes the live overrides while retaining the draft. This includes the homepage, company, services, service details, projects and quality pages.

Text edits are stored in MySQL, not in Git. Their keys are tied to the baseline HTML text and location. If a later template rebuild changes a field, its old override is ignored rather than applied to the wrong content. Recheck edited pages after a template update. Navigation and page structures remain template-controlled.

## Blog

Create an article with a unique English URL slug and both Arabic and English titles and bodies. Drafts stay private; published articles appear at `/ar/blog/` and `/en/blog/`, enter the sitemap, and have equivalent-language links. Plain text is supported, with ## headings and blank lines between paragraphs. Use the Media library to upload a JPG, PNG or WebP cover image.

## Contacts

New contact-form submissions are recorded in Contacts, including the request, company, contact details and email-transport result. Mark them new, in progress or closed and add internal notes. Historical email messages are not automatically imported. Mail transport acceptance is distinct from confirmed inbox delivery.

## Contact settings and media

Settings changes the public email, primary phone and addresses across the website. The mailbox receiving form submissions remains in the private form-config.php, avoiding accidental delivery changes. Media uploads are limited to validated JPG, PNG and WebP images up to 5 MB. Uploaded images persist across deployments.

## Accounts, backups and infrastructure

The account page changes the admin password. A secure random initial password is generated locally; no FTP or database password is used for admin login. Login uses hashed passwords, secure session cookies, CSRF protection and rate limits.

Download a private content backup from Settings to export page edits, blog posts, enquiries and public settings. Keep it private because it contains enquiry details. Database tables use the prefix `mpms_cms_`; existing tables are not removed or changed. Before a database migration, also use Hostinger's database backups.

Server configuration files are outside public_html in `_mpms_private`. Website source code and templates can be kept in Git; passwords, bootstrap files, enquiry records and database contents cannot.

This first version supports one administrator, existing-page text edits, blog articles, image uploads, public contact settings and enquiry tracking. Adding staff roles, creating entirely new service page layouts, and importing old mailbox history require separate implementation.
