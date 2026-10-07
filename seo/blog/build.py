"""Builds the SEORA blog articles from src/*.html into out/*.html and out/manifest.json.

Placeholders in the sources:
  [[cards: handle | note ;; handle | note]]   product cards grid
  [[p:handle|text]]   link to a product
  [[c:handle|text]]   link to a collection
  [[a:handle|text]]   link to another article in the blog
  [[pg:handle|text]]  link to a page
Classes named sk-* are turned into inline styles, because the theme has no CSS for them.
Every handle is checked against data/products.json and the known collections, pages and articles.
"""
import json
import re
import sys
from html import escape
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).parent
BLOG = "magazine"
PRODUCTS = json.loads((ROOT / "data/products.json").read_text(encoding="utf-8"))
META = json.loads((ROOT / "articles.json").read_text(encoding="utf-8"))
ARTICLES = {a["handle"] for a in META}
COLLECTIONS = {
    "טבעות-יהלומי-מוסאנייט", "צמידי-יהלומי-מוסאנייט", "עגילי-יהלומי-מואסנייט",
    "שרשראות-יהלומי-מואסנייט", "סט-תכשיטי-מוסאנייט", "הנמכרים-ביותר", "שעונים-לגברים",
    "maserati-לגברים", "hugo-boss-לגברים", "emporio-armani-לגברים", "michael-kors-לגברים",
    "michael-kors-לנשים", "pierre-richardson-לנשים", "frontpage", "roberto-marino-לנשים",
    "roberto-marino-לגברים", "סט-שעונים-זוגי", "all",
}
PAGES = {"מחשבון-זהב", "מחשבון-כסף", "מדיניות-החזרות", "contact"}
EXTRA_PRODUCTS = {"גיפט-קארד"}  # exists in the store menu, not in the product dump

STYLES = {
    "sk-lead": "font-size:1.15em;line-height:1.8;margin:0 0 14px",
    "sk-meta": "font-size:.9em;opacity:.7;margin:0 0 22px",
    "sk-box": "background:#f7f3ec;border-right:4px solid #b08d57;border-radius:10px;padding:16px 22px;margin:26px 0",
    "sk-tip": "background:#eef5f1;border-radius:10px;padding:14px 20px;margin:24px 0",
    "sk-toc": "background:#fafaf8;border:1px solid #ece6dc;border-radius:10px;padding:14px 22px;margin:26px 0",
    "sk-quote": "border-right:4px solid #b08d57;margin:28px 0;padding:4px 20px;font-size:1.25em;line-height:1.6;font-weight:700",
    "sk-table-wrap": "overflow-x:auto;margin:22px 0",
    "sk-table": "width:100%;border-collapse:collapse;font-size:.95em;min-width:460px",
    "sk-th": "background:#f7f3ec;border-bottom:1px solid #e6dfd3;padding:10px 12px;text-align:right",
    "sk-td": "border-bottom:1px solid #eee8de;padding:10px 12px;text-align:right;vertical-align:top",
    "sk-cta": "background:#f7f3ec;border-radius:12px;padding:20px 24px;margin:32px 0;text-align:center",
    "sk-btn": "display:inline-block;background:#111;color:#fff;padding:12px 26px;border-radius:999px;text-decoration:none;font-weight:700;margin:6px",
    "sk-related": "border:1px solid #ece6dc;border-radius:10px;padding:14px 22px;margin:30px 0",
    "sk-note": "font-size:.85em;opacity:.7;margin-top:30px",
}
# Compact product card: small thumbnail beside the name. Inline styles so it renders the same
# on any theme; the SEORA magazine theme also styles .seora-product / .seora-products.
CARD_GRID = "display:flex;flex-wrap:wrap;gap:12px;margin:24px 0"
CARD = ("flex:1 1 260px;max-width:420px;display:flex;align-items:center;gap:14px;padding:10px 12px;"
        "border:1px solid #e9e3d8;border-radius:12px;background:#fff;color:inherit;text-decoration:none;line-height:1.45")
CARD_IMG = "flex:0 0 auto;width:76px;height:76px;object-fit:cover;border-radius:8px;margin:0"

errors, warnings = [], []


def enc(handle):
    # Hebrew handles stay readable in the HTML (valid IRIs). Browsers and Shopify encode them on request.
    if any(c in handle for c in ' "<>#?'):
        errors.append(f"bad handle: {handle}")
    return handle


def product_url(h):
    if h not in PRODUCTS and h not in EXTRA_PRODUCTS:
        errors.append(f"unknown product: {h}")
    elif h in PRODUCTS and not PRODUCTS[h].get("inStock"):
        warnings.append(f"out of stock: {h}")
    return f"/products/{enc(h)}"


def link(kind, handle, text):
    handle = handle.strip()
    if kind == "p":
        url = product_url(handle)
    elif kind == "c":
        if handle not in COLLECTIONS:
            errors.append(f"unknown collection: {handle}")
        url = f"/collections/{enc(handle)}"
    elif kind == "a":
        if handle not in ARTICLES:
            errors.append(f"unknown article: {handle}")
        url = f"/blogs/{BLOG}/{handle}"
    elif kind == "pg":
        if handle not in PAGES:
            errors.append(f"unknown page: {handle}")
        url = f"/pages/{enc(handle)}"
    else:
        errors.append(f"unknown link kind: {kind}")
        url = "#"
    return f'<a href="{url}">{text.strip()}</a>'


def money(v):
    return f"{int(round(v)):,} ₪"


def card(handle, note):
    handle = handle.strip()
    url = product_url(handle)
    p = PRODUCTS.get(handle)
    if not p:
        return ""
    img = p["image"] or ""
    img = img + ("&" if "?" in img else "?") + "width=200"
    alt = escape(p["title"])
    return (
        f'<a class="seora-product" href="{url}" style="{CARD}">'
        f'<img src="{img}" alt="{alt}" loading="lazy" width="76" height="76" style="{CARD_IMG}">'
        f'<span style="min-width:0">'
        f'<b style="display:block;font-size:.95em">{escape(p["title"])}</b>'
        f'<small style="display:block;margin-top:2px;font-size:.85em;opacity:.75">{note.strip()}</small>'
        f'<u style="display:inline-block;margin-top:4px;font-size:.85em;font-weight:700">לצפייה במוצר</u>'
        "</span></a>"
    )


def cards(spec):
    items = [s.split("|", 1) for s in spec.split(";;") if s.strip()]
    return f'<div class="seora-products" style="{CARD_GRID}">' + "".join(card(h, n) for h, n in items) + "</div>"


def build(src):
    html = src
    html = re.sub(r"\[\[cards:(.*?)\]\]", lambda m: cards(m.group(1)), html, flags=re.S)
    html = re.sub(r"\[\[(p|c|a|pg):([^|\]]+)\|([^\]]+)\]\]", lambda m: link(m.group(1), m.group(2), m.group(3)), html)
    html = re.sub(r'(<div class="sk-cta">.*?</div>)',
                  lambda m: m.group(1).replace('<a href=', f'<a style="{STYLES["sk-btn"]}" href='), html, flags=re.S)
    for cls, style in STYLES.items():
        html = re.sub(rf'class="{cls}"', f'style="{style}"', html)
    for gone in ("sk-toc", "sk-box", "sk-meta", "sk-quote", "sk-related", "sk-cta", "sk-lead"):
        if f'class="{gone}"' in src:
            errors.append(f"{gone} is no longer used in articles")
    if "[[" in html:
        errors.append("unresolved placeholder")
    if re.search(r'class="sk-', html):
        errors.append("unknown sk- class")
    return html.strip() + "\n"


def text_of(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


manifest = []
for meta in META:
    h = meta["handle"]
    src = (ROOT / "src" / f"{h}.html").read_text(encoding="utf-8")
    out = build(src)
    ids = set(re.findall(r'id="([^"]+)"', out))
    for anchor in re.findall(r'href="#([^"]+)"', out):
        if anchor not in ids:
            errors.append(f"{h}: anchor without target #{anchor}")
    txt = text_of(out)
    if "—" in txt or "…" in txt:
        errors.append(f"{h}: em dash or ellipsis in text")
    if len(meta["seo_title"]) > 60:
        warnings.append(f"{h}: seo_title {len(meta['seo_title'])} chars")
    if not 110 <= len(meta["seo_description"]) <= 160:
        warnings.append(f"{h}: seo_description {len(meta['seo_description'])} chars")
    (ROOT / "out" / f"{h}.html").write_text(out, encoding="utf-8")
    img = PRODUCTS[meta["image_product"]]["image"]
    n_links = len(re.findall(r'href="/', out))
    manifest.append({**meta, "body": out, "image_url": img, "words": len(txt.split()),
                     "internal_links": n_links})
    print(f"{h}: {len(txt.split())} words, {n_links} internal links, {len(ids)} anchors")

(ROOT / "out" / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
for w in sorted(set(warnings)):
    print("WARN", w)
for e in errors:
    print("ERROR", e)
sys.exit(1 if errors else 0)
