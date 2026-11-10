# Old-domain transition plan

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

