#!/usr/bin/env python3
"""
MPMS website builder (Arabic / English static site).

    python _src/build.py            -> builds the public site into the repository root
    python _src/build.py --preview  -> builds into _preview/ INCLUDING draft records,
                                       marked "DRAFT", with noindex (internal review only)
    python _src/build.py --check    -> validates content only, writes nothing

Only the Python standard library is used. Content lives in _src/content/*.json.
Read _docs/CONTENT-GUIDE.md before editing.
"""
import datetime as dt
import html
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "_src")
CONTENT = os.path.join(SRC, "content")
LANGS = ("ar", "en")
TODAY = dt.date.today()
BUILD_DATE = TODAY.isoformat()
ASSET_VERSION = TODAY.strftime("%Y%m%d")

ARGS = set(sys.argv[1:])
PREVIEW = "--preview" in ARGS
CHECK_ONLY = "--check" in ARGS
OUT = os.path.join(ROOT, "_preview") if PREVIEW else ROOT

# Folders/files at the repository root that this script generates (and may replace).
GENERATED_DIRS = ("ar", "en")
GENERATED_FILES = ("index.html", "404.html", "sitemap.xml", "robots.txt")

errors = []


def fail(msg):
    errors.append(msg)


def _no_dupes(pairs):
    keys = [k for k, _ in pairs]
    for k in set(keys):
        if keys.count(k) > 1:
            fail(f"duplicate key '{k}' in a content file")
    return dict(pairs)


def load(name):
    with open(os.path.join(CONTENT, name), encoding="utf-8") as f:
        return json.load(f, object_pairs_hook=_no_dupes)


company = load("company.json")
services_all = load("services.json")["items"]
projects_doc = load("projects.json")
projects_all = projects_doc["items"]
orgs_all = load("organizations.json")["items"]
_certs_doc = load("certifications.json")
certs_all = _certs_doc["items"]
CERT_DISPLAY = {"show_dates": True, "show_numbers": True, "hide_expired": True, **_certs_doc.get("display", {})}
downloads_all = load("downloads.json")["items"]
T = load("pages.json")
SITE = company["site_url"].rstrip("/")


# ---------------------------------------------------------------- validation
def visible(rec):
    """Production shows 'published' only. Preview also shows 'draft' (never restricted/withdrawn/expired/unsupported)."""
    st = rec.get("status")
    return st == "published"


def is_draft(rec):
    return rec.get("status") != "published"


def check_parity(a, b, path):
    """Both languages must have the same keys and no empty strings."""
    if isinstance(a, dict):
        if not isinstance(b, dict):
            fail(f"{path}: type differs between languages")
            return
        for k in set(a) | set(b):
            if k not in a or k not in b:
                fail(f"{path}.{k}: missing in {'ar' if k in a else 'en'}")
            else:
                check_parity(a[k], b[k], f"{path}.{k}")
    elif isinstance(a, list):
        if not isinstance(b, list) or len(a) != len(b):
            fail(f"{path}: list length differs between languages")
            return
        for i, (x, y) in enumerate(zip(a, b)):
            check_parity(x, y, f"{path}[{i}]")
    elif isinstance(a, str):
        if not isinstance(b, str):
            fail(f"{path}: type differs between languages")
        elif path.split(".")[-1] not in ("evidence_none",) and (not a.strip() or not b.strip()):
            fail(f"{path}: empty text in one language")


check_parity(T["en"], T["ar"], "pages")
for coll, label in ((services_all, "service"), (projects_all, "project"), (orgs_all, "organization"),
                    (certs_all, "certification"), (downloads_all, "download")):
    for r in coll:
        if r.get("status") in ("published", "draft"):
            if "en" not in r or "ar" not in r:
                fail(f"{label} {r.get('id', r.get('slug'))}: needs both 'en' and 'ar'")
            else:
                check_parity(r["en"], r["ar"], f"{label}:{r.get('id', r.get('slug'))}")

services = sorted([s for s in services_all if visible(s)], key=lambda s: s["order"])
service_by_slug = {s["slug"]: s for s in services}
orgs = {o["id"]: o for o in orgs_all if visible(o)}

projects = []
for p in projects_all:
    if not visible(p):
        continue
    if p["client"] not in orgs:
        if p["status"] == "published":
            fail(f"project {p['id']}: client '{p['client']}' is not a published organization")
        continue
    for s in p["services"]:
        if s not in service_by_slug and p["status"] == "published":
            fail(f"project {p['id']}: unknown service '{s}'")
    projects.append(p)

certs = []
for c in certs_all:
    if not visible(c):
        continue
    if c["status"] == "published":
        if CERT_DISPLAY["hide_expired"] and not c.get("expiry"):
            fail(f"certification {c['id']}: published certificates need an expiry date")
            continue
        if CERT_DISPLAY["hide_expired"] and dt.date.fromisoformat(c["expiry"]) < TODAY:
            print(f"NOTE: certification {c['id']} expired on {c['expiry']} and is hidden. Update or unpublish it.")
            continue
    certs.append(c)

agencies = [o for o in orgs.values() if o["relationship"] == "agency"]
clients = [o for o in orgs.values() if o["relationship"].startswith("client")]
downloads = [d for d in downloads_all if visible(d)]
for d in downloads:
    if d["status"] == "published" and not os.path.exists(os.path.join(ROOT, d["file"].lstrip("/"))):
        fail(f"download {d['id']}: file {d['file']} not found")

for field in ("name", "address", "founded"):
    if company[field]["status"] != "published":
        fail(f"company.{field} must be published")

if errors:
    print("BUILD STOPPED — fix these content problems:")
    for e_ in errors:
        print("  -", e_)
    sys.exit(1)
if CHECK_ONLY:
    print("Content OK.")
    sys.exit(0)


# ---------------------------------------------------------------- helpers
def e(s):
    return html.escape(str(s), quote=True)


def ltr(s):
    """Keep phone numbers, emails, codes and standards left-to-right inside Arabic text."""
    return f'<span dir="ltr">{e(s)}</span>'


def url(lang, path=""):
    return f"/{lang}/{path}"


def other(lang):
    return "en" if lang == "ar" else "ar"


def draft_mark(rec, lang):
    return ""


ICONS = {
    "vessel": '<path d="M3 15l2 4h14l2-4H3z"/><path d="M6 15V9h12v6"/><path d="M9 9V5h4l2 4"/><path d="M2 21c2 0 2-1 4-1s2 1 4 1 2-1 4-1 2 1 4 1 2-1 4-1"/>',
    "weld": '<path d="M4 20l7-7"/><path d="M11 13l3-3 4 4-3 3z"/><path d="M14 10l3-3"/><path d="M18 3l1 2 2 1-2 1-1 2-1-2-2-1 2-1z"/>',
    "engine": '<rect x="5" y="8" width="11" height="9" rx="1"/><path d="M16 11h3v3h-3"/><path d="M8 8V5h5v3"/><path d="M2 11h3v3H2z"/><circle cx="10.5" cy="12.5" r="2"/>',
    "berth": '<path d="M2 10h20"/><path d="M5 10v9M12 10v9M19 10v9"/><path d="M2 19c2 0 2 1 4 1s2-1 4-1 2 1 4 1 2-1 4-1 2 1 4 1"/><circle cx="8.5" cy="7" r="2"/>',
    "fire": '<path d="M12 3c1 3 5 5 5 10a5 5 0 01-10 0c0-2 1-3 2-4 0 2 1 3 2 3 0-4-1-6 1-9z"/>',
    "water": '<path d="M12 3s6 7 6 11a6 6 0 01-12 0c0-4 6-11 6-11z"/><path d="M9 15a3 3 0 003 3"/>',
    "hvac": '<circle cx="12" cy="12" r="8"/><path d="M12 12c0-4 3-5 4-3s-4 3-4 3zM12 12c-4 0-5 3-3 4s3-4 3-4zM12 12c0 4-3 5-4 3s4-3 4-3zM12 12c4 0 5-3 3-4s-3 4-3 4z"/>',
    "crane": '<path d="M6 21V5l12 3"/><path d="M6 5L3 8"/><path d="M15 7v6"/><rect x="13" y="13" width="4" height="3"/><path d="M3 21h8"/>',
    "crew": '<circle cx="9" cy="8" r="3"/><path d="M3 20c0-4 3-6 6-6s6 2 6 6"/><path d="M16 4.5a3 3 0 010 6"/><path d="M18 14c2 1 3 3 3 6"/>',
}


def icon(name):
    return f'<svg class="ico" viewBox="0 0 24 24" aria-hidden="true" focusable="false">{ICONS.get(name, "")}</svg>'


def hull_lines():
    """Abstract body-plan drawing (ship sections) used as a graphic. Not a depiction of MPMS work."""
    parts = []
    cx, base, deck = 300, 330, 70
    for i in range(1, 8):
        k = i / 7.0
        half = 40 + 210 * (k ** 0.6)
        bilge = 30 + 150 * k
        # starboard (fore) and port (aft, slightly finer)
        for side, f in ((1, 1.0), (-1, 0.86)):
            hb = half * f
            parts.append(
                f'<path d="M{cx} {base} C {cx + side * bilge * f:.1f} {base} {cx + side * hb:.1f} {base - 40 - 60 * k:.1f} '
                f'{cx + side * hb:.1f} {deck + 40:.1f} L {cx + side * (hb + 6):.1f} {deck:.1f}"/>')
    wls = "".join(f'<line x1="40" x2="560" y1="{y}" y2="{y}" class="wl"/>' for y in (130, 190, 250, 300))
    return ('<svg class="hull" viewBox="0 0 600 380" role="img" aria-hidden="true" focusable="false">'
            f'{wls}<line x1="300" x2="300" y1="40" y2="350" class="cl"/><line x1="40" x2="560" y1="330" y2="330" class="bl"/>'
            f'<g class="st">{"".join(parts)}</g>'
            '<text x="44" y="122" class="lb">WL 4</text><text x="44" y="182" class="lb">WL 3</text>'
            '<text x="44" y="242" class="lb">WL 2</text><text x="44" y="292" class="lb">WL 1</text>'
            '<text x="306" y="52" class="lb">CL</text><text x="44" y="352" class="lb">BL</text></svg>')


def phones(lang, cls=""):
    out = []
    for p in company["phones"]:
        if visible(p) and p.get("tel"):
            out.append(f'<a class="{cls}" href="tel:{e(p["tel"])}"><span dir="ltr">{e(p["display"])}</span></a>{draft_mark(p, lang)}')
    return out


def emails(lang):
    return [(p, f'<a href="mailto:{e(p["address"])}"><span dir="ltr">{e(p["address"])}</span></a>{draft_mark(p, lang)}')
            for p in company["emails"] if visible(p)]


def address_html(lang):
    a = company["address"][lang]
    return "<br>".join(e(a[k]) for k in ("line1", "line2", "city", "country"))


def maps_url():
    from urllib.parse import quote
    return "https://www.google.com/maps/search/?api=1&query=" + quote(company["address"]["maps_query"])


# ---------------------------------------------------------------- layout
NAV = (("", "home"), ("company/", "company"), ("services/", "services"), ("projects/", "projects"),
       ("quality/", "quality"), ("contact/", "contact"))


def head(lang, path, title, desc, extra_ld=None, noindex=False):
    t = T[lang]
    o = other(lang)
    canon = SITE + url(lang, path)
    robots = '<meta name="robots" content="noindex, nofollow">' if (noindex or PREVIEW) else ""
    ld = [{
        "@context": "https://schema.org", "@type": "Organization",
        "name": company["name"]["en"], "alternateName": [company["name"]["ar"], company["name"]["short"]],
        "url": SITE + "/", "logo": SITE + "/assets/img/logo.png",
        "address": {"@type": "PostalAddress", **company["address"]["schema"]},
        "telephone": [p["tel"] for p in company["phones"] if p["status"] == "published" and p["tel"]],
        "email": [m["address"] for m in company["emails"] if m["status"] == "published"],
        "foundingDate": "2000", "foundingLocation": "Jeddah, Saudi Arabia",
        "vatID": company.get("registration", {}).get("vat", ""),
        "sameAs": [s["url"] for s in company.get("social", []) if s["status"] == "published"],
    }] if path == "" else []
    if extra_ld:
        ld.append(extra_ld)
    ld_html = "".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in ld)
    fonts = ["readex-arabic-400", "readex-arabic-600"] if lang == "ar" else ["readex-latin-400", "readex-latin-600"]
    preload = "".join(f'<link rel="preload" href="/assets/fonts/{f}.woff2" as="font" type="font/woff2" crossorigin>' for f in fonts)
    return f"""<!doctype html>
<html lang="{lang}" dir="{'rtl' if lang == 'ar' else 'ltr'}" class="no-js">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
{robots}
<link rel="canonical" href="{canon}">
<link rel="alternate" hreflang="{lang}" href="{canon}">
<link rel="alternate" hreflang="{o}" href="{SITE + url(o, path)}">
<link rel="alternate" hreflang="x-default" href="{SITE}/">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{e(company['name'][lang])}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{canon}">
<meta property="og:image" content="{SITE}/assets/img/og-image.jpg">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta property="og:locale" content="{'ar_SA' if lang == 'ar' else 'en_US'}">
<meta property="og:locale:alternate" content="{'en_US' if lang == 'ar' else 'ar_SA'}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#1b2152">
<link rel="icon" href="/assets/img/favicon-32.png" sizes="32x32" type="image/png">
<link rel="apple-touch-icon" href="/assets/img/apple-touch-icon.png">
{preload}
<link rel="stylesheet" href="/assets/css/site.css?v={ASSET_VERSION}">
<script>document.documentElement.className=document.documentElement.className.replace('no-js','js');</script>
{ld_html}
</head>"""


def header(lang, path, overlay=False):
    t = T[lang]
    o = other(lang)
    items = []
    for p, key in NAV[1:]:
        current = path == p or (p and path.startswith(p))
        aria = ' aria-current="page"' if current else ""
        items.append(f'<li><a href="{url(lang, p)}"{aria}>{e(t["nav"][key])}</a></li>')
    preview_bar = ""
    return f"""<body>
{preview_bar}<a class="skip" href="#main">{e(t['skip'])}</a>
<header class="site-header{' is-overlay' if overlay else ''}">
  <div class="wrap bar">
    <a class="brand" href="{url(lang)}" aria-label="{e(company['name'][lang])} — {e(t['nav']['home'])}">
      <img class="logo-dark" src="/assets/img/logo.png" width="220" height="80" alt="">
      <img class="logo-light" src="/assets/img/logo-white.png" width="220" height="80" alt="">
      <span class="brand-name">{e(t['company']['brand_name'])}</span>
    </a>
    <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="site-nav">
      <span class="nav-toggle-bars" aria-hidden="true"></span><span class="nav-toggle-label">{e(t['menu'])}</span>
    </button>
    <nav id="site-nav" class="site-nav" aria-label="{e(t['menu'])}">
      <ul>{''.join(items)}</ul>
      <div class="nav-tools">
        <a class="lang-switch" href="{url(o, path)}" hreflang="{o}" lang="{o}" data-lang="{o}" aria-label="{e(t['switch_aria'])}">{e(t['switch_label'])}</a>
        <a class="btn btn-small btn-red" href="{url(lang, 'contact/')}?type=quote#request">{e(t['cta_quote'])}</a>
      </div>
    </nav>
  </div>
</header>"""


def registration(lang):
    r = company.get("registration")
    if not r or not visible(r):
        return ""
    L = r[lang]
    return (f'<p class="reg">{e(L["cr"])} {ltr(r["cr"])} · {e(L["unified"])} {ltr(r["unified"])} · {e(L["vat"])} {ltr(r["vat"])}</p>')


def footer(lang):
    t = T[lang]
    links = "".join(f'<li><a href="{url(lang, p)}">{e(t["nav"][k])}</a></li>' for p, k in NAV)
    links += f'<li><a href="{url(lang, "privacy/")}">{e(t["privacy_link"])}</a></li>'
    contact = "".join(f"<li>{x}</li>" for x in phones(lang)) + "".join(f"<li>{x}</li>" for _, x in emails(lang))
    return f"""<footer class="site-footer">
  <div class="wrap foot">
    <div class="foot-brand">
      <img src="/assets/img/logo-white.png" width="200" height="73" alt="">
      <p class="foot-name">{e(company['name'][lang])}</p>
      <p>{e(t['footer_tagline'])}</p>
      {social_links(lang)}
    </div>
    <div><h2 class="foot-h">{e(t['footer_pages'])}</h2><ul class="foot-list">{links}</ul></div>
    <div><h2 class="foot-h">{e(t['footer_contact'])}</h2><ul class="foot-list">{contact}</ul>
      <address class="foot-addr">{address_html(lang)}</address></div>
  </div>
  <div class="wrap foot-legal"><p>© {TODAY.year} {e(company['name'][lang])}. {e(t['rights'])}</p>{registration(lang)}</div>
</footer>
<script src="/assets/js/site.js?v={ASSET_VERSION}" defer></script>
</body>
</html>
"""


def crumbs(lang, trail):
    """trail = [(label, path or None), ...] — first item is home."""
    t = T[lang]
    lis, items = [], []
    for i, (label, p) in enumerate(trail):
        if p is not None and i < len(trail) - 1:
            lis.append(f'<li><a href="{url(lang, p)}">{e(label)}</a></li>')
        else:
            lis.append(f'<li aria-current="page">{e(label)}</li>')
        items.append({"@type": "ListItem", "position": i + 1, "name": label,
                      **({"item": SITE + url(lang, p)} if p is not None else {})})
    html_ = f'<nav class="crumbs" aria-label="{e(t["breadcrumb"])}"><ol>{"".join(lis)}</ol></nav>'
    return html_, {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": items}


WAVES = ('<svg class="ph-waves" viewBox="0 0 1440 120" preserveAspectRatio="none" aria-hidden="true" focusable="false">'
         '<path class="w1" d="M0 70 C 180 40 360 100 540 70 S 900 40 1080 70 S 1440 100 1620 70 S 1980 40 2160 70 S 2520 100 2880 70 V120 H0Z"/>'
         '<path class="w2" d="M0 86 C 200 60 400 110 600 86 S 1000 60 1200 86 S 1600 110 1800 86 S 2200 60 2400 86 S 2800 110 2880 86 V120 H0Z"/>'
         '<path class="w3" d="M0 100 C 240 84 480 116 720 100 S 1200 84 1440 100 S 1920 116 2160 100 S 2640 84 2880 100 V120 H0Z"/></svg>')


def page_hero(lang, h1, lede, crumb_html, kicker="", photo="deck-work", extra=""):
    k = f'<p class="kicker">{e(kicker)}</p>' if kicker else ""
    img = (f'<img class="ph-img" src="/assets/img/photo/{photo}.jpg" srcset="/assets/img/photo/{photo}-800.jpg 800w, /assets/img/photo/{photo}.jpg 1600w" '
           f'sizes="100vw" alt="" decoding="async" fetchpriority="high">') if photo else ""
    return (f'<section class="page-hero{" has-photo" if photo else ""}">{img}<div class="wrap ph-in">{crumb_html}{k}'
            f'<h1>{e(h1)}</h1><p class="lede">{e(lede)}</p>{extra}</div>{WAVES}<div class="waterline" aria-hidden="true"></div></section>')

def cta_band(lang, service_slug=None):
    t = T[lang]
    q = f"?type=quote&service={service_slug}" if service_slug else "?type=quote"
    tel = phones(lang, "band-tel")
    return f"""<section class="band">
  <video class="band-video" muted loop playsinline preload="none" poster="/assets/video/sea-poster.jpg" data-autoplay aria-hidden="true" tabindex="-1">
    <source src="/assets/video/sea-1280.mp4" type="video/mp4"></video>
  <div class="wrap band-in">
  <div><h2>{e(t['home']['band_h'])}</h2><p>{e(t['home']['band_p'])}</p></div>
  <div class="band-actions"><a class="btn btn-red" href="{url(lang, 'contact/')}{q}#request">{e(t['cta_quote'])}</a>{tel[0] if tel else ''}</div>
</div></section>"""

# ---------------------------------------------------------------- pages
written = []


def write(rel, content):
    full = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    written.append(rel)


def service_card(lang, s, hl=3):
    d = s[lang]
    b = s.get("banner", "deck-work")
    return (f'<li class="svc"><a href="{url(lang, "services/" + s["slug"] + "/")}">'
            f'<span class="svc-media"><img src="/assets/img/photo/{b}-800.jpg" alt="" loading="lazy" decoding="async" width="800" height="533"></span>'
            f'<span class="svc-body">{icon(s["icon"])}<h{hl} class="svc-h">{e(d["title"])}{draft_mark(s, lang)}</h{hl}>'
            f'<span class="svc-p">{e(d["short"])}</span></span></a></li>')

def project_rows(lang, items, show_service=True):
    t = T[lang]
    rows = []
    for p in items:
        org = orgs[p["client"]][lang]["name"]
        ref = (f'<span class="ref">{e(t["projects"]["reference"])} {ltr(p["reference"])}</span>' if p.get("reference") else "")
        svc_tags = "".join(f'<li><a href="{url(lang, "services/" + s + "/")}">{e(service_by_slug[s][lang]["title"])}</a></li>'
                           for s in p["services"] if s in service_by_slug)
        svc = f'<td class="tags"><ul>{svc_tags}</ul></td>' if show_service else ""
        lg = orgs[p["client"]].get("logo_client")
        logo = f'<span class="org-logo"><img src="/assets/img/clients/{lg}.png" alt="" loading="lazy"></span>' if lg else '<span class="org-logo is-empty" aria-hidden="true"></span>'
        rows.append(f'<tr data-services="{" ".join(p["services"])}"><th scope="row"><span class="org">{logo}<span>{e(org)}{draft_mark(orgs[p["client"]], lang)}</span></span></th>'
                    f'<td>{e(p[lang]["title"])}{draft_mark(p, lang)} {ref}</td>{svc}</tr>')
    return "".join(rows)


def agency_list(lang, cls="agencies"):
    if not agencies:
        return ""
    lis = []
    for a in agencies:
        name = a[lang]["name"]
        mark = (f'<img src="/assets/img/logos/{e(a["logo"])}.png" alt="{e(name)}" loading="lazy">' if a.get("logo")
                else f'<span class="wordmark" lang="en" dir="ltr">{e(name.split(" (")[0].replace(" Co., Ltd.", ""))}</span>')
        country = a[lang].get("country", "")
        meta = f'<span class="agency-country">{e(country)}</span>' if country else ""
        lis.append(f'<li class="agency"><div class="agency-mark">{mark}</div><div class="agency-body">'
                   f'<p class="agency-name" lang="en" dir="ltr">{e(name)}</p><p class="agency-desc">{e(a[lang].get("description", ""))}</p>'
                   f'<p class="agency-meta"><span class="agency-tag">{e(T[lang]["company"]["agent_tag"])}</span>{meta}</p></div></li>')
    return f'<ul class="{cls}">{"".join(lis)}</ul>'

def social_links(lang):
    out = []
    for s in company.get("social", []):
        if visible(s):
            label = s["label_" + lang]
            out.append(f'<li><a class="social" href="{e(s["url"])}" rel="noopener me" target="_blank" aria-label="{e(label)}">'
                       f'{SOCIAL_ICONS.get(s["id"], "")}<span>{e(label)}</span></a>{draft_mark(s, lang)}</li>')
    return f'<ul class="socials">{"".join(out)}</ul>' if out else ""


SOCIAL_ICONS = {
    "linkedin": '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M4.98 3.5a2.5 2.5 0 11-.01 5 2.5 2.5 0 01.01-5zM3 9h4v12H3zM9 9h3.8v1.7h.1c.5-1 1.8-2 3.7-2 4 0 4.7 2.6 4.7 6V21h-4v-5.4c0-1.3 0-3-1.8-3s-2.1 1.4-2.1 2.9V21H9z"/></svg>',
    "facebook": '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M14 8h3V4h-3c-2.8 0-4.5 1.8-4.5 4.6V11H7v4h2.5v7h4v-7h3l.5-4h-3.5V8.8c0-.5.3-.8.5-.8z"/></svg>',
    "x": '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M17.8 3h3.1l-6.8 7.7L22 21h-6.2l-4.9-6.3L5.3 21H2.2l7.3-8.3L2 3h6.4l4.4 5.8zm-1.1 16.2h1.7L7.4 4.7H5.6z"/></svg>',
    "instagram": '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M12 7a5 5 0 100 10 5 5 0 000-10zm0 8.2a3.2 3.2 0 110-6.4 3.2 3.2 0 010 6.4zM17.3 5.5a1.2 1.2 0 100 2.4 1.2 1.2 0 000-2.4zM12 2c-2.7 0-3 0-4.1.1C4.4 2.2 2.2 4.4 2.1 7.9 2 9 2 9.3 2 12s0 3 .1 4.1c.1 3.5 2.3 5.7 5.8 5.8 1.1.1 1.4.1 4.1.1s3 0 4.1-.1c3.5-.1 5.7-2.3 5.8-5.8.1-1.1.1-1.4.1-4.1s0-3-.1-4.1c-.1-3.5-2.3-5.7-5.8-5.8C15 2 14.7 2 12 2z"/></svg>',
    "youtube": '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M23 7.2a3 3 0 00-2.1-2.1C19 4.6 12 4.6 12 4.6s-7 0-8.9.5A3 3 0 001 7.2 31 31 0 00.5 12a31 31 0 00.5 4.8 3 3 0 002.1 2.1c1.9.5 8.9.5 8.9.5s7 0 8.9-.5a3 3 0 002.1-2.1 31 31 0 00.5-4.8 31 31 0 00-.5-4.8zM9.8 15.1V8.9l5.4 3.1z"/></svg>',
}


WORK_IMAGES = ["drydock-1", "slipway-1", "hull-1", "blasting-1", "engine-2", "engine-3", "engine-1", "electrical-1",
               "fenders-1", "fenders-2", "berth-1", "survey-1", "safety-1"]


def gallery(lang, s):
    if not s.get("images"):
        return ""
    alt = T[lang]["services"]["photo_alt"].format(title=s[lang]["title"])
    figs = "".join(f'<figure><a href="/assets/img/work/{e(i)}.jpg" data-lightbox><img src="/assets/img/work/{e(i)}.jpg" alt="{e(alt)}" width="960" height="720" loading="lazy" decoding="async"></a></figure>'
                   for i in s["images"])
    return f'<div class="gallery g{min(len(s["images"]), 4)}">{figs}</div>'


def work_strip(lang):
    t = T[lang]
    alt = t["home"]["work_h"]
    figs = "".join(f'<li><a href="/assets/img/work/{i}.jpg" data-lightbox><img src="/assets/img/work/{i}.jpg" alt="{e(alt)}" loading="lazy" decoding="async" width="960" height="720"></a></li>'
                   for i in WORK_IMAGES)
    return f'<ul class="work-strip" tabindex="0" aria-label="{e(alt)}">{figs}</ul>'


def clients_marquee(lang):
    items = company.get("clients_logos", [])
    if not items:
        return ""
    lis = "".join(f'<li><img src="/assets/img/clients/{k}.png" alt="{e(ar if lang == "ar" else en)}" loading="lazy" decoding="async"></li>' for k, en, ar in items)
    # Second copy is decorative (hidden from assistive tech) so the strip can loop seamlessly.
    dup = "".join(f'<li aria-hidden="true"><img src="/assets/img/clients/{k}.png" alt="" loading="lazy" decoding="async"></li>' for k, en, ar in items)
    return f'<div class="marquee"><ul class="marquee-track">{lis}{dup}</ul></div>'


def stats_band(lang):
    t = T[lang]
    cells = []
    for s in company.get("stats", []):
        v = len(projects) if s["value"] == "projects" else s["value"]
        cells.append(f'<li><span class="stat-n" data-count="{v}"{" data-plain" if s.get("plain") else ""}><span dir="ltr">{v}</span></span>'
                     f'<span class="stat-l">{e(s[lang])}</span></li>')
    return f'<section class="stats" aria-label="{e(t["home"]["stats_label"])}"><ul class="wrap stats-in">{"".join(cells)}</ul></section>'


def cert_seals(lang):
    out = []
    for c in certs:
        if not c["standard"].startswith("ISO"):
            continue
        num = c["standard"].replace("ISO/IEC ", "").replace("ISO ", "").split(":")[0]
        out.append(f'<li class="seal"><svg viewBox="0 0 120 120" aria-hidden="true" focusable="false"><circle cx="60" cy="60" r="56"/><circle cx="60" cy="60" r="47" class="in"/></svg>'
                   f'<span class="seal-txt"><span class="seal-iso">ISO</span><span class="seal-num" dir="ltr">{e(num)}</span></span>'
                   f'<span class="seal-name">{e(c[lang]["name"])}</span></li>')
    return f'<ul class="seals">{"".join(out)}</ul>' if out else ""


def draft_marks():
    marks = "".join(f'<li><span dir="ltr">{n}M</span></li>' for n in (12, 10, 8, 6, 4, 2))
    return f'<ol class="draft-marks" aria-hidden="true">{marks}</ol>'

def build_home(lang):
    t = T[lang]
    h = t["home"]
    picks = [p for p in projects if p["id"] in ("swcc-unloading-arm", "patrol-boat-w6", "maaden-generators",
                                                "samref-fenders", "kaust-research-vessel", "rsnf-crane-docking")]
    body = f"""{head(lang, '', h['title'], h['description'])}
{header(lang, '', overlay=True)}
<main id="main">
<section class="hero">
  <video class="hero-video" muted loop playsinline autoplay preload="metadata" poster="/assets/video/hero-poster.jpg" aria-label="{e(h['video_label'])}" data-autoplay>
    <source src="/assets/video/hero-640.mp4" type="video/mp4" media="(max-width: 700px)">
    <source src="/assets/video/hero-1280.mp4" type="video/mp4">
  </video>
  <div class="hero-shade" aria-hidden="true"></div>
  {draft_marks()}
  <div class="wrap hero-in">
    <p class="hero-place">{e(h['eyebrow'])}</p>
    <h1>{e(h['hero_h1'])}</h1>
    <p class="lede">{e(h['hero_lede'])}</p>
    <p class="actions"><a class="btn btn-red" href="{url(lang, 'contact/')}?type=quote#request">{e(t['cta_quote'])}</a>
    <a class="btn btn-glass" href="{url(lang, 'services/')}">{e(h['cta_services'])}</a></p>
  </div>
  <button class="video-toggle" type="button" aria-pressed="false" data-label-pause="{e(h['pause'])}" data-label-play="{e(h['play'])}" aria-label="{e(h['pause'])}"><span aria-hidden="true"></span></button>
</section>
{stats_band(lang)}

<section class="section agencies-sec"><div class="wrap">
  <div class="sec-head row"><h2>{e(h['agencies_h'])}</h2><p>{e(t['company']['agencies_p'])}</p></div>
  {agency_list(lang)}
</div></section>

<section class="section svc-sec"><div class="wrap">
  <div class="sec-head row"><h2>{e(h['services_h'])}</h2><p>{e(h['services_p'])}</p></div>
  <ul class="svc-grid">{''.join(service_card(lang, s) for s in services)}</ul>
</div></section>

<section class="section work-sec dark"><div class="wrap">
  <div class="sec-head row"><h2>{e(h['work_h'])}</h2><p>{e(h['work_p'])}</p></div>
</div>{work_strip(lang)}</section>

<section class="section"><div class="wrap split-refs">
  <div class="sec-head"><h2>{e(h['projects_h'])}</h2><p>{e(h['projects_p'])}</p>
    <p><a class="link-strong" href="{url(lang, 'projects/')}">{e(h['projects_all'])}</a></p>
    <figure class="refs-photo"><img src="/assets/img/work/drydock-1.jpg" alt="{e(h['work_h'])}" loading="lazy" width="960" height="720"></figure></div>
  <div class="table-wrap"><table class="ledger"><caption class="sr-only">{e(h['projects_h'])}</caption>
    <thead><tr><th scope="col">{e(t['projects']['col_client'])}</th><th scope="col">{e(t['projects']['col_scope'])}</th></tr></thead>
    <tbody>{project_rows(lang, picks, show_service=False)}</tbody></table></div>
</div></section>

<section class="section clients-sec alt"><div class="wrap">
  <div class="sec-head row"><h2>{e(h['clients_h'])}</h2><p>{e(h['clients_p'])}</p></div>
</div>{clients_marquee(lang)}</section>

<section class="section certs-sec"><div class="wrap certs-in">
  <div class="sec-head"><h2>{e(h['certs_h'])}</h2><p>{e(h['certs_p'])}</p><p><a class="link-strong" href="{url(lang, 'quality/')}">{e(h['certs_more'])}</a></p></div>
  {cert_seals(lang)}
</div></section>

<section class="section updates-sec alt" data-updates="{url(lang, 'blog/')}"><div class="wrap">
  <div class="sec-head row"><h2>{e(h['updates_h'])}</h2><p>{e(h['updates_p'])}</p></div>
  <div class="updates-grid" data-updates-target></div>
  <p><a class="btn btn-ghost" href="{url(lang, 'blog/')}">{e(h['updates_all'])}</a></p>
</div></section>
{cta_band(lang)}
</main>
{footer(lang)}"""
    write(f"{lang}/index.html", body)

def leader_card(lang, p):
    c = T[lang]["company"]
    d = p[lang]
    href = url(lang, "company/" + p["slug"] + "/")
    steps = "".join(f'<li>{e(x)}</li>' for x in d["career"][:3])
    watch = (f'<a class="btn btn-ghost btn-small" href="{href}#interview">{PLAY_ICON}{e(c["watch"])}</a>' if p.get("video") else "")
    return (f'<li class="profile"><figure class="profile-photo"><img src="/assets/img/team/{p["photo"]}.jpg" alt="{e(d["name"])}" width="280" height="280" loading="lazy">'
            f'<figcaption><span class="person">{e(d["name"])}</span><span class="role">{e(d["role"])}</span></figcaption></figure>'
            f'<div class="profile-body"><p class="profile-sum">{e(d["summary"])}</p>'
            f'<h3 class="profile-h">{e(c["career_h"])}</h3><ol class="profile-steps">{steps}</ol>'
            f'<p class="profile-actions"><a class="btn btn-small" href="{href}">{e(c["bio"])}</a>{watch}</p></div></li>')

PLAY_ICON = '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false"><path fill="currentColor" d="M8 5v14l11-7z"/></svg>'

def department_management_table(lang):
    """Keep the owner-supplied right-to-left column order; stack full cells on phones."""
    members = [p for p in company.get("department_managers", []) if visible(p)]
    if not members:
        return ""
    caption = "مديرو الإدارات" if lang == "ar" else "Department managers"
    cells = "".join(
        f'<td><div class="management-name"><span class="management-ar" lang="ar" dir="rtl">{e(p["name_ar"])}</span>'
        f'<span class="management-en" lang="en" dir="ltr">{e(p["name_en"])}</span></div>'
        f'<div class="management-role"><span lang="ar" dir="rtl">{e(p["role_ar"])}</span>'
        f'<span class="management-role-en" lang="en" dir="ltr">{e(p["role_en"])}</span></div></td>'
        for p in members
    )
    return f'<table class="management-team" dir="rtl"><caption>{e(caption)}</caption><tbody><tr>{cells}</tr></tbody></table>'


def build_company(lang):
    t = T[lang]
    c = t["company"]
    cr, ld = crumbs(lang, [(t["nav"]["home"], ""), (t["nav"]["company"], None)])
    st = company["statements"]
    lead = "".join(leader_card(lang, p) for p in company["leadership"] if visible(p))
    ov = company["overview"][lang]
    facts = "".join(f'<div><dt>{e(k)}</dt><dd>{ltr(v) if v[:1].isdigit() else e(v)}</dd></div>' for k, v in company["facts"][lang])
    ag = ""
    if agencies:
        ag = (f'<section class="section alt"><div class="wrap"><div class="sec-head"><h2>{e(c["agencies_h"])}</h2><p>{e(c["agencies_p"])}</p></div>'
              f'{agency_list(lang)}</div></section>')
    body = f"""{head(lang, 'company/', c['title'], c['description'], ld)}
{header(lang, 'company/')}
<main id="main">
{page_hero(lang, c['h1'], c['lede'], cr, photo='hull-scaffold')}
<section class="section"><div class="wrap split overview">
  <div><h2>{e(c['overview_h'])}</h2>{''.join(f'<p>{e(x)}</p>' for x in ov)}</div>
  <aside class="panel facts-panel"><h2 class="h-small">{e(c['facts_h'])}</h2><dl class="kv">{facts}</dl></aside>
</div></section>
<section class="section alt"><div class="wrap split">
  <div><h2>{e(c['history_h'])}</h2>
    <ol class="timeline">
      <li><span class="yr">{ltr('2000')}</span><p>{e(c['history_2000'])}</p></li>
      <li><span class="yr">{ltr('2012')}</span><p>{e(c['history_2012'])}</p></li>
    </ol></div>
  <div><h2>{e(c['office_h'])}</h2><address class="addr">{address_html(lang)}</address>
    <p><a class="arrow" href="{e(maps_url())}" rel="noopener" target="_blank">{e(t['contact']['map'])}</a></p></div>
</div></section>
<section class="section"><div class="wrap">
  <div class="sec-head"><h2>{e(c['statements_h'])}</h2></div>
  <dl class="statements">
    <div><dt>{e(c['vision'])}</dt><dd>{e(st['vision'][lang])}</dd></div>
    <div><dt>{e(c['mission'])}</dt><dd>{e(st['mission'][lang])}</dd></div>
    <div><dt>{e(c['objective'])}</dt><dd>{e(st['objective'][lang])}</dd></div>
  </dl>
</div></section>
<section class="section"><div class="wrap">
  <div class="sec-head"><h2>{e(c['leadership_h'])}</h2><p>{e(c['leadership_p'])}</p></div>
  <ul class="profiles">{lead}</ul>
  {department_management_table(lang)}
</div></section>
{ag}
{cta_band(lang)}
</main>
{footer(lang)}"""
    write(f"{lang}/company/index.html", body)

    for p in company["leadership"]:
        if not visible(p):
            continue
        d = p[lang]
        path = f"company/{p['slug']}/"
        cr2, ld2 = crumbs(lang, [(t["nav"]["home"], ""), (t["nav"]["company"], "company/"), (d["name"], None)])
        video = ""
        if p.get("video"):
            video = (f'<section class="section alt" id="interview"><div class="wrap"><h2>{e(d["video_h"])}</h2>'
                     f'<div class="video-frame"><video controls preload="none" poster="/assets/video/{p["video"]}-poster.jpg" playsinline>'
                     f'<source src="/assets/video/{p["video"]}.mp4" type="video/mp4"></video></div></div></section>')
        body = f"""{head(lang, path, d['name'] + ' | ' + company['name'][lang], d['summary'], ld2)}
{header(lang, path)}
<main id="main">
{page_hero(lang, d['name'], d['role'], cr2, photo='hull-scaffold')}
<section class="section"><div class="wrap bio">
  <figure class="bio-photo"><img src="/assets/img/team/{p['photo']}.jpg" alt="{e(d['name'])}" width="280" height="280"></figure>
  <div class="bio-body">
    <p class="bio-lead">{e(d['summary'])}</p>
    <h2>{e(c['career_h'])}</h2>
    <ol class="timeline">{''.join(f'<li><p>{e(x)}</p></li>' for x in d['career'])}</ol>
    <h2>{e(c['achievements_h'])}</h2>
    <ul class="ticks">{''.join(f'<li>{e(x)}</li>' for x in d['achievements'])}</ul>
    <p><a class="link-strong" href="{url(lang, 'company/')}">{e(c['back_company'])}</a></p>
  </div>
</div></section>
{video}
{cta_band(lang)}
</main>
{footer(lang)}"""
        write(f"{lang}/{path}index.html", body)


def build_services(lang):
    t = T[lang]
    s_ = t["services"]
    cr, ld = crumbs(lang, [(t["nav"]["home"], ""), (t["nav"]["services"], None)])
    body = f"""{head(lang, 'services/', s_['title'], s_['description'], ld)}
{header(lang, 'services/')}
<main id="main">
{page_hero(lang, s_['h1'], s_['lede'], cr, photo='hull-welding-2')}
<section class="section"><div class="wrap"><ul class="svc-grid">{''.join(service_card(lang, s, 2) for s in services)}</ul></div></section>
{cta_band(lang)}
</main>
{footer(lang)}"""
    write(f"{lang}/services/index.html", body)

    for s in services:
        d = s[lang]
        path = f"services/{s['slug']}/"
        cr, ld = crumbs(lang, [(t["nav"]["home"], ""), (t["nav"]["services"], "services/"), (d["title"], None)])
        rel = [p for p in projects if s["slug"] in p["services"]]
        ev = ""
        if rel:
            ev = (f'<section class="section alt"><div class="wrap"><div class="sec-head"><h2>{e(s_["evidence_h"])}</h2>'
                  f'<p class="basis">{e(projects_doc["basis_labels"]["profile-2023"][lang])}</p></div>'
                  f'<div class="table-wrap"><table class="ledger"><caption class="sr-only">{e(s_["evidence_h"])}</caption>'
                  f'<thead><tr><th scope="col">{e(t["projects"]["col_client"])}</th><th scope="col">{e(t["projects"]["col_scope"])}</th></tr></thead>'
                  f'<tbody>{project_rows(lang, rel, show_service=False)}</tbody></table></div></div></section>')
        others = "".join(f'<li><a href="{url(lang, "services/" + o["slug"] + "/")}">{e(o[lang]["title"])}</a></li>'
                         for o in services if o["slug"] != s["slug"])
        desc = d["short"]
        body = f"""{head(lang, path, d['title'] + ' | ' + company['name'][lang], desc, ld)}
{header(lang, path)}
<main id="main">
{page_hero(lang, d['title'], d['intro'], cr, kicker=t['nav']['services'], photo=s.get('banner', 'deck-work'))}
<section class="section"><div class="wrap">{gallery(lang, s)}</div><div class="wrap detail">
  <div class="detail-main">
    <h2>{e(s_['scope_h'])}</h2>
    <ul class="ticks">{''.join(f'<li>{e(x)}</li>' for x in d['scope'])}</ul>
    <h2>{e(s_['deliverables_h'])}</h2>
    <ol class="steps">{''.join(f'<li>{e(x)}</li>' for x in d['deliverables'])}</ol>
  </div>
  <aside class="detail-side">
    <div class="panel"><h2 class="h-small">{e(s_['delivery_h'])}</h2><p>{e(s_['delivery'][s['delivery']])}</p></div>
    <div class="panel panel-dark"><h2 class="h-small">{e(s_['next_h'])}</h2><p>{e(s_['next_p'])}</p>
      <p><a class="btn btn-light" href="{url(lang, 'contact/')}?type=quote&amp;service={s['slug']}#request">{e(s_['next_btn'])}</a></p></div>
  </aside>
</div></section>
{ev}
<section class="section"><div class="wrap"><h2 class="h-small">{e(s_['other_h'])}</h2><ul class="chips">{others}</ul></div></section>
</main>
{footer(lang)}"""
        write(f"{lang}/{path}index.html", body)


def build_projects(lang):
    t = T[lang]
    p_ = t["projects"]
    cr, ld = crumbs(lang, [(t["nav"]["home"], ""), (t["nav"]["projects"], None)])
    used = [s for s in services if any(s["slug"] in p["services"] for p in projects)]
    opts = "".join(f'<option value="{s["slug"]}">{e(s[lang]["title"])}</option>' for s in used)
    body = f"""{head(lang, 'projects/', p_['title'], p_['description'], ld)}
{header(lang, 'projects/')}
<main id="main">
{page_hero(lang, p_['h1'], p_['lede'], cr, photo='propeller')}
<section class="section"><div class="wrap">
  <div class="filter" hidden>
    <label for="svc-filter">{e(p_['filter_label'])}</label>
    <select id="svc-filter"><option value="">{e(p_['filter_all'])}</option>{opts}</select>
    <p class="count" aria-live="polite"><span data-count>{len(projects)}</span> {e(p_['count'])}</p>
  </div>
  <div class="table-wrap"><table class="ledger" id="project-table"><caption class="sr-only">{e(p_['h1'])}</caption>
    <thead><tr><th scope="col">{e(p_['col_client'])}</th><th scope="col">{e(p_['col_scope'])}</th><th scope="col">{e(p_['col_service'])}</th></tr></thead>
    <tbody>{project_rows(lang, projects)}</tbody></table></div>
</div></section>
<section class="section clients-sec alt"><div class="wrap"><div class="sec-head"><h2>{e(p_['logos_h'])}</h2></div></div>{clients_marquee(lang)}</section>
{cta_band(lang)}
</main>
{footer(lang)}"""
    write(f"{lang}/projects/index.html", body)


def fmt_date(iso, lang):
    if not iso:
        return ""
    d = dt.date.fromisoformat(iso)
    return ltr(d.strftime("%d-%m-%Y"))


def mini_seal(c, lang="en"):
    if c["standard"].startswith("ISO"):
        top, num = "ISO", c["standard"].replace("ISO/IEC ", "").replace("ISO ", "").split(":")[0]
    else:
        top, num = ("الدرجة" if lang == "ar" else "Grade"), "2"
    return (f'<span class="mseal" aria-hidden="true"><svg viewBox="0 0 120 120"><circle cx="60" cy="60" r="56"/><circle cx="60" cy="60" r="47" class="in"/></svg>'
            f'<span class="mseal-t"><span>{top}</span><b dir="ltr">{num}</b></span></span>')


def seals_marquee(lang):
    items = []
    for c in certs:
        label = c["standard"].split(":")[0] if c["standard"] else c[lang]["name"].split("—")[0].strip()
        items.append(f'{mini_seal(c, lang)}<span class="ms-label" dir="{"ltr" if c["standard"] else "auto"}">{e(label)}</span>')
    lis = "".join(f'<li class="seal-item">{x}</li>' for x in items)
    dup = "".join(f'<li class="seal-item" aria-hidden="true">{x}</li>' for x in items)
    return f'<div class="marquee"><ul class="marquee-track seals-track">{lis}{dup}</ul></div>'


def build_quality(lang):
    t = T[lang]
    q = t["quality"]
    cr, ld = crumbs(lang, [(t["nav"]["home"], ""), (t["nav"]["quality"], None)])
    table = ""
    if certs:
        def first_cell(c):
            seal = mini_seal(c, lang)
            if c["standard"]:
                return f'<tr><th scope="row"><span class="org">{seal}<span>{ltr(c["standard"])}{draft_mark(c, lang)}<span class="sub">{e(c[lang]["name"])}</span></span></span></th>'
            return f'<tr><th scope="row"><span class="org">{seal}<span>{e(c[lang]["name"])}{draft_mark(c, lang)}</span></span></th>'
        sn, sd = CERT_DISPLAY["show_numbers"], CERT_DISPLAY["show_dates"]

        def other_cells(c):
            cells = f'<td>{e(c[lang]["scope"])}</td><td>{ltr(c["issuer"]) if c["issuer"] else ""}</td>'
            if sn:
                cells += f'<td>{ltr(c["number"]) if c["number"] else ""}</td>'
            if sd:
                cells += f'<td>{fmt_date(c["expiry"], lang)}</td>'
            return cells + "</tr>"
        rows = "".join(first_cell(c) + other_cells(c) for c in certs)
        head_cells = (f'<th scope="col">{e(q["col_standard"])}</th><th scope="col">{e(q["col_scope"])}</th><th scope="col">{e(q["col_issuer"])}</th>'
                      + (f'<th scope="col">{e(q["col_number"])}</th>' if sn else "") + (f'<th scope="col">{e(q["col_valid"])}</th>' if sd else ""))
        table = (f'<div class="table-wrap"><table class="ledger certs"><caption class="sr-only">{e(q["h1"])}</caption><thead><tr>'
                 f'{head_cells}</tr></thead><tbody>{rows}</tbody></table></div>')
    body = f"""{head(lang, 'quality/', q['title'], q['description'], ld)}
{header(lang, 'quality/')}
<main id="main">
{page_hero(lang, q['h1'], q['lede'], cr, photo='deck-chemicals')}
<section class="section"><div class="wrap">
  {table}
  <div class="panel panel-wide"><h2>{e(q['docs_h'])}</h2><p>{e(q['docs_p'])}</p>
    <p><a class="btn" href="{url(lang, 'contact/')}?type=docs#request">{e(q['docs_btn'])}</a></p></div>
</div></section>
<section class="section clients-sec alt"><div class="wrap"><div class="sec-head"><h2>{e(q['seals_h'])}</h2></div></div>{seals_marquee(lang)}</section>
{cta_band(lang)}
</main>
{footer(lang)}"""
    write(f"{lang}/quality/index.html", body)


def field(lang, name, label, kind="text", required=False, hint=None, auto=None, maxlength=200, inputmode=None):
    c = T[lang]["contact"]
    req = ' required aria-required="true"' if required else ""
    star = ' <span class="req" aria-hidden="true">*</span>' if required else ""
    hid = f"{name}-hint"
    hint_html = f'<p class="hint" id="{hid}">{e(hint)}</p>' if hint else ""
    desc = ' aria-describedby="' + " ".join(x for x in (hid if hint else "", f"{name}-err") if x) + '"'
    ac = f' autocomplete="{auto}"' if auto else ""
    im = f' inputmode="{inputmode}"' if inputmode else ""
    dirattr = ' dir="ltr"' if kind in ("email", "tel") else ""
    if kind == "textarea":
        ctrl = f'<textarea id="{name}" name="{name}" rows="7" maxlength="{maxlength}"{req}{desc}></textarea>'
    else:
        pattern = ' pattern="[+0-9 ()\\-]{7,20}"' if kind == "tel" else ""
        ctrl = f'<input id="{name}" name="{name}" type="{kind}" maxlength="{maxlength}"{req}{ac}{im}{pattern}{dirattr}{desc}>'
    return (f'<div class="field" data-field="{name}"><label for="{name}">{e(label)}{star}</label>{hint_html}{ctrl}'
            f'<p class="err" id="{name}-err" hidden></p></div>')


def build_contact(lang):
    t = T[lang]
    c = t["contact"]
    cr, ld = crumbs(lang, [(t["nav"]["home"], ""), (t["nav"]["contact"], None)])
    phone_list = "".join(f"<li>{x}</li>" for x in phones(lang)) + "".join(
        f'<li><span class="sub">{e(p["label_" + lang])}</span><span dir="ltr">{e(p["display"])}</span></li>'
        for p in company["phones"] if visible(p) and not p.get("tel"))
    mail_list = "".join(f'<li><span class="sub">{e(m["label_" + lang])}</span>{x}</li>' for m, x in emails(lang))
    hours = ""
    if visible(company["hours"]):
        hours = f'<div><dt>{e(c["hours"])}</dt><dd>{"<br>".join(e(x) for x in company["hours"][lang].split(" · "))}</dd></div>'
    svc_opts = "".join(f'<option value="{s["slug"]}">{e(s[lang]["title"])}</option>' for s in services)
    msgs = {k: c[k] for k in ("err_required", "err_email", "err_phone", "err_consent", "err_long", "err_summary",
                              "f_sending", "f_submit", "f_consent_short", "ok_h", "ok_p", "fail_h", "fail_p")}
    body = f"""{head(lang, 'contact/', c['title'], c['description'], ld)}
{header(lang, 'contact/')}
<main id="main">
{page_hero(lang, c['h1'], c['lede'], cr, photo='berth-aerial')}
<section class="section"><div class="wrap contact">
  <div class="contact-details">
    <h2>{e(c['details_h'])}</h2>
    <dl class="kv">
      <div><dt>{e(c['phone'])}</dt><dd><ul class="plain">{phone_list}</ul></dd></div>
      <div><dt>{e(c['email'])}</dt><dd><ul class="plain">{mail_list}</ul></dd></div>
      <div><dt>{e(c['address'])}</dt><dd><address>{address_html(lang)}</address>
        <a class="arrow" href="{e(maps_url())}" rel="noopener" target="_blank">{e(c['map'])}</a></dd></div>
      {hours}
    </dl>
    {social_links(lang)}
  </div>
  <div class="contact-form" id="request">
    <h2>{e(c['form_h'])}</h2>
    <p class="hint">{e(c['required_note'])}</p>
    <div class="form-status" role="status" aria-live="polite" tabindex="-1" hidden></div>
    <div class="err-summary" role="alert" tabindex="-1" hidden><p>{e(c['err_summary'])}</p><ul></ul></div>
    <form id="request-form" action="/forms/send.php" method="post" accept-charset="UTF-8" data-messages='{e(json.dumps(msgs, ensure_ascii=False))}'>
      <input type="hidden" name="lang" value="{lang}">
      <input type="hidden" name="ts" value="">
      <div class="hp" aria-hidden="true"><label for="website">{e(c['f_hp'])}</label><input id="website" name="website" type="text" tabindex="-1" autocomplete="off"></div>
      <div class="field" data-field="type"><label for="type">{e(c['f_type'])} <span class="req" aria-hidden="true">*</span></label>
        <select id="type" name="type" required aria-required="true" aria-describedby="type-err">
          <option value="quote">{e(c['t_quote'])}</option><option value="docs">{e(c['t_docs'])}</option>
          <option value="general">{e(c['t_general'])}</option><option value="supplier">{e(c['t_supplier'])}</option>
        </select><p class="err" id="type-err" hidden></p></div>
      <div class="field" data-field="service"><label for="service">{e(c['f_service'])}</label>
        <select id="service" name="service"><option value="">{e(c['f_service_none'])}</option>{svc_opts}</select></div>
      <div class="row2">{field(lang, 'name', c['f_name'], required=True, auto='name', maxlength=120)}
      {field(lang, 'company', c['f_company'], auto='organization', maxlength=160)}</div>
      <div class="row2">{field(lang, 'email', c['f_email'], 'email', True, auto='email', maxlength=160)}
      {field(lang, 'phone', c['f_phone'], 'tel', False, c['f_phone_hint'], 'tel', 30, 'tel')}</div>
      {field(lang, 'location', c['f_location'], hint=c['f_location_hint'], maxlength=200)}
      {field(lang, 'message', c['f_message'], 'textarea', True, c['f_message_hint'], maxlength=5000)}
      <div class="field check" data-field="consent"><input id="consent" name="consent" type="checkbox" value="yes" required aria-required="true" aria-describedby="consent-err">
        <label for="consent">{e(c['f_consent'])} (<a href="{url(lang, 'privacy/')}">{e(t['privacy_link'])}</a>)</label><p class="err" id="consent-err" hidden></p></div>
      <p><button class="btn" type="submit">{e(c['f_submit'])}</button></p>
    </form>
  </div>
</div></section>
</main>
{footer(lang)}"""
    write(f"{lang}/contact/index.html", body)

    for slug, hk, pk, ok in (("sent", "ok_h", "ok_p", True), ("error", "fail_h", "fail_p", False)):
        cr2, _ = crumbs(lang, [(t["nav"]["home"], ""), (t["nav"]["contact"], "contact/"), (c[hk], None)])
        extra = "" if ok else f'<ul class="plain">{"".join(f"<li>{x}</li>" for x in phones(lang))}{"".join(f"<li>{x}</li>" for _, x in emails(lang))}</ul>'
        body = f"""{head(lang, f'contact/{slug}/', c[hk] + ' | ' + company['name'][lang], c[pk], noindex=True)}
{header(lang, f'contact/{slug}/')}
<main id="main">
<section class="page-hero"><div class="wrap">{cr2}<h1>{e(c[hk])}</h1><p class="lede">{e(c[pk])}</p>{extra}
<p><a class="arrow" href="{url(lang, 'contact/')}">{e(c['back'])}</a></p></div></section>
</main>
{footer(lang)}"""
        write(f"{lang}/contact/{slug}/index.html", body)


def build_privacy(lang):
    t = T[lang]
    p = t["privacy"]
    cr, ld = crumbs(lang, [(t["nav"]["home"], ""), (p["h1"], None)])
    secs = "".join(f"<h2>{e(h)}</h2><p>{e(b)}</p>" for h, b in p["body"])
    body = f"""{head(lang, 'privacy/', p['title'], p['description'], ld)}
{header(lang, 'privacy/')}
<main id="main">
{page_hero(lang, p['h1'], p['description'], cr, photo=None)}
<section class="section"><div class="wrap prose">{secs}
<p class="hint">{e(p['updated'])}: {ltr(company['reviewed'])}</p></div></section>
</main>
{footer(lang)}"""
    write(f"{lang}/privacy/index.html", body)


def build_root():
    en, ar = T["en"], T["ar"]
    body = f"""<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(company['name']['ar'])} | {e(company['name']['en'])}</title>
<meta name="description" content="{e(ar['home']['description'])}">
<meta name="robots" content="noindex, follow">
<link rel="alternate" hreflang="ar" href="{SITE}/ar/"><link rel="alternate" hreflang="en" href="{SITE}/en/"><link rel="alternate" hreflang="x-default" href="{SITE}/">
<link rel="icon" href="/assets/img/favicon-32.png" sizes="32x32" type="image/png">
<script>(function(){{var l='';try{{l=localStorage.getItem('mpms-lang')||'';}}catch(e){{}}
if(l!=='ar'&&l!=='en'){{var n=(navigator.languages&&navigator.languages[0])||navigator.language||'en';l=/^ar/i.test(n)?'ar':'en';}}
location.replace('/'+l+'/');}})();</script>
<noscript><meta http-equiv="refresh" content="0; url=/ar/"></noscript>
</head>
<body><p><a href="/ar/" lang="ar">العربية</a> · <a href="/en/" lang="en">English</a></p></body></html>
"""
    write("index.html", body)

    nf = f"""<!doctype html>
<html lang="en" dir="ltr">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(en['notfound']['title'])}</title><meta name="robots" content="noindex">
<link rel="icon" href="/assets/img/favicon-32.png" sizes="32x32" type="image/png">
<link rel="stylesheet" href="/assets/css/site.css?v={ASSET_VERSION}"></head>
<body class="chooser"><main id="main" class="chooser-in">
<img src="/assets/img/logo.png" width="330" height="121" alt="{e(company['name']['en'])}">
<div class="nf" lang="ar" dir="rtl"><h1>{e(ar['notfound']['h1'])}</h1><p>{e(ar['notfound']['p'])}</p><p><a class="btn" href="/ar/">{e(ar['notfound']['home'])}</a></p></div>
<div class="nf" lang="en"><h2>{e(en['notfound']['h1'])}</h2><p>{e(en['notfound']['p'])}</p><p><a class="btn btn-ghost" href="/en/">{e(en['notfound']['home'])}</a></p></div>
</main></body></html>
"""
    write("404.html", nf)


def build_seo():
    paths = ["", "company/", "services/", "projects/", "quality/", "contact/", "privacy/"] + \
            [f"services/{s['slug']}/" for s in services] + \
            [f"company/{p['slug']}/" for p in company["leadership"] if p["status"] == "published"]
    urls = []
    for p in paths:
        for lang in LANGS:
            alts = "".join(f'<xhtml:link rel="alternate" hreflang="{l}" href="{SITE}{url(l, p)}"/>' for l in LANGS)
            alts += f'<xhtml:link rel="alternate" hreflang="x-default" href="{SITE}/"/>'
            urls.append(f"<url><loc>{SITE}{url(lang, p)}</loc><lastmod>{BUILD_DATE}</lastmod>{alts}</url>")
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
          'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' + "\n".join(urls) + "\n</urlset>\n")
    if PREVIEW:
        write("robots.txt", "User-agent: *\nDisallow: /\n")
    else:
        write("robots.txt", f"User-agent: *\nDisallow: /forms/\nDisallow: /*/contact/sent/\nDisallow: /*/contact/error/\n\nSitemap: {SITE}/sitemap.xml\n")


def main():
    if PREVIEW:
        if os.path.isdir(OUT):
            shutil.rmtree(OUT, ignore_errors=True)
        os.makedirs(OUT, exist_ok=True)
        for d in ("assets", "forms"):
            shutil.copytree(os.path.join(ROOT, d), os.path.join(OUT, d), dirs_exist_ok=True)
    else:
        for d in GENERATED_DIRS:
            if os.path.isdir(os.path.join(OUT, d)):
                shutil.rmtree(os.path.join(OUT, d))
    for lang in LANGS:
        build_home(lang)
        build_company(lang)
        build_services(lang)
        build_projects(lang)
        build_quality(lang)
        build_contact(lang)
        build_privacy(lang)
    build_root()
    build_seo()
    print(f"{'PREVIEW' if PREVIEW else 'PRODUCTION'} build: {len(written)} files written to {os.path.relpath(OUT, ROOT) or '.'}")
    print(f"  services {len(services)} · projects {len(projects)} · organizations {len(orgs)} · "
          f"certificates shown {len(certs)} · downloads {len(downloads)}")


if __name__ == "__main__":
    main()
