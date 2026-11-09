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
certs_all = load("certifications.json")["items"]
downloads_all = load("downloads.json")["items"]
T = load("pages.json")
SITE = company["site_url"].rstrip("/")


# ---------------------------------------------------------------- validation
def visible(rec):
    """Production shows 'published' only. Preview also shows 'draft' (never restricted/withdrawn/expired/unsupported)."""
    st = rec.get("status")
    return st == "published" or (PREVIEW and st == "draft")


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
        if not c.get("expiry"):
            fail(f"certification {c['id']}: published certificates need an expiry date")
            continue
        if dt.date.fromisoformat(c["expiry"]) < TODAY:
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
    if PREVIEW and rec is not None and is_draft(rec):
        return f' <span class="draft">{e(T[lang]["draft_badge"])}</span>'
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
    }] if path == "" else []
    if extra_ld:
        ld.append(extra_ld)
    ld_html = "".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in ld)
    fonts = ["plex-arabic-400", "plex-arabic-700"] if lang == "ar" else ["plex-latin-400", "plex-latin-600"]
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


def header(lang, path):
    t = T[lang]
    o = other(lang)
    items = []
    for p, key in NAV[1:]:
        current = path == p or (p and path.startswith(p))
        aria = ' aria-current="page"' if current else ""
        items.append(f'<li><a href="{url(lang, p)}"{aria}>{e(t["nav"][key])}</a></li>')
    preview_bar = (f'<div class="preview-bar" role="note">Internal preview — includes draft records marked '
                   f'“{e(T["en"]["draft_badge"])}”. Not for publication.</div>') if PREVIEW else ""
    return f"""<body>
{preview_bar}<a class="skip" href="#main">{e(t['skip'])}</a>
<header class="site-header">
  <div class="wrap bar">
    <a class="brand" href="{url(lang)}" aria-label="{e(company['name'][lang])} — {e(t['nav']['home'])}">
      <img src="/assets/img/logo.png" width="220" height="80" alt="">
      <span class="brand-ar" lang="ar">{e(company['name']['ar'])}</span>
    </a>
    <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="site-nav">
      <span class="nav-toggle-bars" aria-hidden="true"></span><span class="nav-toggle-label">{e(t['menu'])}</span>
    </button>
    <nav id="site-nav" class="site-nav" aria-label="{e(t['menu'])}">
      <ul>{''.join(items)}</ul>
      <div class="nav-tools">
        <a class="lang-switch" href="{url(o, path)}" hreflang="{o}" lang="{o}" data-lang="{o}" aria-label="{e(t['switch_aria'])}">{e(t['switch_label'])}</a>
        <a class="btn btn-small" href="{url(lang, 'contact/')}?type=quote#request">{e(t['cta_quote'])}</a>
      </div>
    </nav>
  </div>
</header>"""


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
    </div>
    <div><h2 class="foot-h">{e(t['footer_pages'])}</h2><ul class="foot-list">{links}</ul></div>
    <div><h2 class="foot-h">{e(t['footer_contact'])}</h2><ul class="foot-list">{contact}</ul>
      <address class="foot-addr">{address_html(lang)}</address></div>
  </div>
  <div class="wrap foot-legal"><p>© {TODAY.year} {e(company['name'][lang])}. {e(t['rights'])}</p></div>
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


def page_hero(lang, h1, lede, crumb_html, kicker=""):
    k = f'<p class="kicker">{e(kicker)}</p>' if kicker else ""
    return f"""<section class="page-hero"><div class="wrap">{crumb_html}{k}<h1>{e(h1)}</h1><p class="lede">{e(lede)}</p></div></section>"""


def cta_band(lang, service_slug=None):
    t = T[lang]
    q = f"?type=quote&service={service_slug}" if service_slug else "?type=quote"
    tel = phones(lang, "band-tel")
    return f"""<section class="band"><div class="wrap band-in">
  <div><h2>{e(t['home']['band_h'])}</h2><p>{e(t['home']['band_p'])}</p></div>
  <div class="band-actions"><a class="btn btn-light" href="{url(lang, 'contact/')}{q}#request">{e(t['cta_quote'])}</a>{tel[0] if tel else ''}</div>
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
    return (f'<li class="svc"><a href="{url(lang, "services/" + s["slug"] + "/")}">'
            f'<span class="svc-n" aria-hidden="true">{s["order"]:02d}</span>{icon(s["icon"])}'
            f'<h{hl} class="svc-h">{e(d["title"])}{draft_mark(s, lang)}</h{hl}><p>{e(d["short"])}</p>'
            f'<span class="more" aria-hidden="true">{e(T[lang]["services"]["more"])}</span></a></li>')


def project_rows(lang, items, show_service=True):
    t = T[lang]
    rows = []
    for p in items:
        org = orgs[p["client"]][lang]["name"]
        ref = (f'<span class="ref">{e(t["projects"]["reference"])} {ltr(p["reference"])}</span>' if p.get("reference") else "")
        svc_tags = "".join(f'<li><a href="{url(lang, "services/" + s + "/")}">{e(service_by_slug[s][lang]["title"])}</a></li>'
                           for s in p["services"] if s in service_by_slug)
        svc = f'<td class="tags"><ul>{svc_tags}</ul></td>' if show_service else ""
        rows.append(f'<tr data-services="{" ".join(p["services"])}"><th scope="row">{e(org)}{draft_mark(orgs[p["client"]], lang)}</th>'
                    f'<td>{e(p[lang]["title"])}{draft_mark(p, lang)} {ref}</td>{svc}</tr>')
    return "".join(rows)


def build_home(lang):
    t = T[lang]
    h = t["home"]
    picks = [p for p in projects if p["id"] in ("swcc-unloading-arm", "rsnf-dive-boat-survey", "maaden-generators",
                                                "samref-fenders", "kaust-research-vessel", "rsnf-crane-docking")]
    client_list = "".join(f'<li>{e(o[lang]["name"])}{draft_mark(o, lang)}</li>' for o in clients)
    body = f"""{head(lang, '', h['title'], h['description'])}
{header(lang, '')}
<main id="main">
<section class="hero"><div class="wrap hero-in">
  <div class="hero-text">
    <p class="kicker">{e(h['eyebrow'])}</p>
    <h1>{e(h['h1'])}</h1>
    <p class="lede">{e(h['lede'])}</p>
    <p class="actions"><a class="btn" href="{url(lang, 'contact/')}?type=quote#request">{e(t['cta_quote'])}</a>
    <a class="btn btn-ghost" href="{url(lang, 'services/')}">{e(h['cta_services'])}</a></p>
  </div>
  <div class="hero-art">{hull_lines()}<p class="coord">{(ltr('21.5°') + ' شمالًا · ' + ltr('39.2°') + ' شرقًا — جدة') if lang == 'ar' else '21.5° N · 39.2° E — Jeddah'}</p></div>
</div></section>

<section class="facts" aria-label="{e(h['facts_title'])}"><div class="wrap"><dl class="facts-grid">
  <div><dt>{ltr('2000')}</dt><dd>{e(h['fact_2000'])}</dd></div>
  <div><dt>{ltr('2012')}</dt><dd>{e(h['fact_2012'])}</dd></div>
  <div><dt>{e(h['fact_hq_k'])}</dt><dd>{e(h['fact_hq'])}</dd></div>
</dl></div></section>

<section class="section"><div class="wrap">
  <div class="sec-head"><p class="kicker">{e(h['services_k'])}</p><h2>{e(h['services_h'])}</h2><p>{e(h['services_p'])}</p></div>
  <ul class="svc-grid">{''.join(service_card(lang, s) for s in services)}</ul>
</div></section>

<section class="section alt"><div class="wrap">
  <div class="sec-head"><p class="kicker">{e(h['projects_k'])}</p><h2>{e(h['projects_h'])}</h2><p>{e(h['projects_p'])}</p></div>
  <div class="table-wrap"><table class="ledger"><caption class="sr-only">{e(h['projects_h'])}</caption>
    <thead><tr><th scope="col">{e(t['projects']['col_client'])}</th><th scope="col">{e(t['projects']['col_scope'])}</th><th scope="col">{e(t['projects']['col_service'])}</th></tr></thead>
    <tbody>{project_rows(lang, picks)}</tbody></table></div>
  <p class="after"><a class="arrow" href="{url(lang, 'projects/')}">{e(h['projects_all'])}</a></p>
</div></section>

<section class="section"><div class="wrap">
  <div class="sec-head"><h2>{e(h['clients_h'])}</h2><p>{e(h['clients_p'])}</p></div>
  <ul class="clients">{client_list}</ul>
</div></section>
{cta_band(lang)}
</main>
{footer(lang)}"""
    write(f"{lang}/index.html", body)


def build_company(lang):
    t = T[lang]
    c = t["company"]
    cr, ld = crumbs(lang, [(t["nav"]["home"], ""), (t["nav"]["company"], None)])
    st = company["statements"]
    lead = "".join(f'<li><p class="person">{e(p[lang]["name"])}{draft_mark(p, lang)}</p><p class="role">{e(p[lang]["role"])}</p></li>'
                   for p in company["leadership"] if visible(p))
    ag = ""
    if agencies:
        ag = (f'<section class="section alt"><div class="wrap"><div class="sec-head"><h2>{e(c["agencies_h"])}</h2><p>{e(c["agencies_p"])}</p></div>'
              '<ul class="cards3">' + "".join(
                  f'<li class="card"><h3 lang="en" dir="ltr">{e(a[lang]["name"])}</h3>{draft_mark(a, lang)}<p>{e(a[lang].get("description", ""))}</p></li>'
                  for a in agencies) + "</ul></div></section>")
    body = f"""{head(lang, 'company/', c['title'], c['description'], ld)}
{header(lang, 'company/')}
<main id="main">
{page_hero(lang, c['h1'], c['lede'], cr)}
<section class="section"><div class="wrap split">
  <div><h2>{e(c['history_h'])}</h2>
    <ol class="timeline">
      <li><span class="yr">{ltr('2000')}</span><p>{e(c['history_2000'])}</p></li>
      <li><span class="yr">{ltr('2012')}</span><p>{e(c['history_2012'])}</p></li>
    </ol></div>
  <div><h2>{e(c['office_h'])}</h2><address class="addr">{address_html(lang)}</address>
    <p><a class="arrow" href="{e(maps_url())}" rel="noopener" target="_blank">{e(t['contact']['map'])}</a></p></div>
</div></section>
<section class="section alt"><div class="wrap">
  <div class="sec-head"><h2>{e(c['statements_h'])}</h2></div>
  <dl class="statements">
    <div><dt>{e(c['vision'])}</dt><dd>{e(st['vision'][lang])}</dd></div>
    <div><dt>{e(c['mission'])}</dt><dd>{e(st['mission'][lang])}</dd></div>
    <div><dt>{e(c['objective'])}</dt><dd>{e(st['objective'][lang])}</dd></div>
  </dl>
</div></section>
<section class="section"><div class="wrap">
  <div class="sec-head"><h2>{e(c['leadership_h'])}</h2></div>
  <ul class="people">{lead}</ul>
</div></section>
{ag}
{cta_band(lang)}
</main>
{footer(lang)}"""
    write(f"{lang}/company/index.html", body)


def build_services(lang):
    t = T[lang]
    s_ = t["services"]
    cr, ld = crumbs(lang, [(t["nav"]["home"], ""), (t["nav"]["services"], None)])
    body = f"""{head(lang, 'services/', s_['title'], s_['description'], ld)}
{header(lang, 'services/')}
<main id="main">
{page_hero(lang, s_['h1'], s_['lede'], cr)}
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
<section class="page-hero"><div class="wrap">{cr}<p class="kicker">{s['order']:02d} · {e(t['nav']['services'])}</p>
  <h1>{e(d['title'])}{draft_mark(s, lang)}</h1><p class="lede">{e(d['intro'])}</p></div></section>
<section class="section"><div class="wrap detail">
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
{page_hero(lang, p_['h1'], p_['lede'], cr)}
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
{cta_band(lang)}
</main>
{footer(lang)}"""
    write(f"{lang}/projects/index.html", body)


def fmt_date(iso, lang):
    if not iso:
        return ""
    d = dt.date.fromisoformat(iso)
    return ltr(d.strftime("%d-%m-%Y"))


def build_quality(lang):
    t = T[lang]
    q = t["quality"]
    cr, ld = crumbs(lang, [(t["nav"]["home"], ""), (t["nav"]["quality"], None)])
    table = ""
    if certs:
        def first_cell(c):
            if c["standard"]:
                return f'<tr><th scope="row">{ltr(c["standard"])}{draft_mark(c, lang)}<span class="sub">{e(c[lang]["name"])}</span></th>'
            return f'<tr><th scope="row">{e(c[lang]["name"])}{draft_mark(c, lang)}</th>'
        rows = "".join(
            first_cell(c) +
            f'<td>{e(c[lang]["scope"])}</td><td>{ltr(c["issuer"]) if c["issuer"] else ""}</td>'
            f'<td>{ltr(c["number"]) if c["number"] else ""}</td><td>{fmt_date(c["expiry"], lang)}'
            + (f' <a href="{e(c["file"])}">{e(q["view"])}</a>' if c.get("file") and c["status"] == "published" else "")
            + "</td></tr>" for c in certs)
        table = (f'<div class="table-wrap"><table class="ledger"><caption class="sr-only">{e(q["h1"])}</caption><thead><tr>'
                 f'<th scope="col">{e(q["col_standard"])}</th><th scope="col">{e(q["col_scope"])}</th><th scope="col">{e(q["col_issuer"])}</th>'
                 f'<th scope="col">{e(q["col_number"])}</th><th scope="col">{e(q["col_valid"])}</th></tr></thead><tbody>{rows}</tbody></table></div>')
    body = f"""{head(lang, 'quality/', q['title'], q['description'], ld)}
{header(lang, 'quality/')}
<main id="main">
{page_hero(lang, q['h1'], q['lede'], cr)}
<section class="section"><div class="wrap">
  {table}
  <div class="panel panel-wide"><h2>{e(q['docs_h'])}</h2><p>{e(q['docs_p'])}</p>
    <p><a class="btn" href="{url(lang, 'contact/')}?type=docs#request">{e(q['docs_btn'])}</a></p></div>
</div></section>
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
    phone_list = "".join(f"<li>{x}</li>" for x in phones(lang))
    mail_list = "".join(f'<li><span class="sub">{e(m["label_" + lang])}</span>{x}</li>' for m, x in emails(lang))
    hours = ""
    if visible(company["hours"]):
        hours = f'<div><dt>{e(c["hours"])}</dt><dd>{e(company["hours"][lang])}{draft_mark(company["hours"], lang)}</dd></div>'
    svc_opts = "".join(f'<option value="{s["slug"]}">{e(s[lang]["title"])}</option>' for s in services)
    msgs = {k: c[k] for k in ("err_required", "err_email", "err_phone", "err_consent", "err_long", "err_summary",
                              "f_sending", "f_submit", "f_consent_short", "ok_h", "ok_p", "fail_h", "fail_p")}
    body = f"""{head(lang, 'contact/', c['title'], c['description'], ld)}
{header(lang, 'contact/')}
<main id="main">
{page_hero(lang, c['h1'], c['lede'], cr)}
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
{page_hero(lang, p['h1'], p['description'], cr)}
<section class="section"><div class="wrap prose">{secs}
<p class="hint">{e(p['updated'])}: {ltr(company['reviewed'])}</p></div></section>
</main>
{footer(lang)}"""
    write(f"{lang}/privacy/index.html", body)


def build_root():
    en, ar = T["en"], T["ar"]
    body = f"""<!doctype html>
<html lang="ar" dir="rtl" class="no-js">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(company['name']['ar'])} | {e(company['name']['en'])}</title>
<meta name="description" content="{e(ar['home']['description'])} {e(en['home']['description'])}">
{'<meta name="robots" content="noindex, nofollow">' if PREVIEW else ''}
<link rel="canonical" href="{SITE}/">
<link rel="alternate" hreflang="ar" href="{SITE}/ar/"><link rel="alternate" hreflang="en" href="{SITE}/en/"><link rel="alternate" hreflang="x-default" href="{SITE}/">
<meta property="og:title" content="{e(company['name']['en'])}"><meta property="og:image" content="{SITE}/assets/img/og-image.jpg">
<link rel="icon" href="/assets/img/favicon-32.png" sizes="32x32" type="image/png">
<link rel="stylesheet" href="/assets/css/site.css?v={ASSET_VERSION}">
<script>try{{var l=localStorage.getItem('mpms-lang');if(l==='ar'||l==='en'){{location.replace('/'+l+'/');}}}}catch(e){{}}</script>
</head>
<body class="chooser">
<main id="main" class="chooser-in">
  <img src="/assets/img/logo.png" width="330" height="121" alt="{e(company['name']['en'])}">
  <h1><span lang="ar">{e(company['name']['ar'])}</span><span lang="en" dir="ltr">{e(company['name']['en'])}</span></h1>
  <p class="choose">
    <a class="btn" href="/ar/" hreflang="ar" lang="ar" data-lang="ar">العربية</a>
    <a class="btn btn-ghost" href="/en/" hreflang="en" lang="en" dir="ltr" data-lang="en">English</a>
  </p>
</main>
<script src="/assets/js/site.js?v={ASSET_VERSION}" defer></script>
</body></html>
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
            [f"services/{s['slug']}/" for s in services]
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
            shutil.rmtree(OUT)
        os.makedirs(OUT)
        for d in ("assets", "forms"):
            shutil.copytree(os.path.join(ROOT, d), os.path.join(OUT, d))
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
