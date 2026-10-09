#!/usr/bin/env python3
"""Render a Hebrew (RTL) social carousel from a JSON spec to PNG/JPG with headless Chromium.

  python3 render.py spec.json --out OUT_DIR [--format ig-feed] [--jpg] [--guides] [--lint] [--sheet]

Formats: ig-feed 1080x1350 | ig-feed-34 1080x1440 | ig-square 1080x1080 | fb-carousel 1080x1080 |
         fb-feed 1080x1350 | ig-story 1080x1920 | fb-story 1080x1920
Slide types: cover, point, list, stat, compare, quote, product, cta  (see SKILL.md)
"""
import argparse, html, json, os, re, sys, importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
FONTS = HERE / "assets" / "fonts"
CHROMIUM = os.environ.get("CHROMIUM_PATH", "/opt/pw-browsers/chromium")

# name: (width, height, kind)
FORMATS = {
    "ig-feed": (1080, 1350, "feed"), "ig-feed-34": (1080, 1440, "feed"), "ig-square": (1080, 1080, "feed"),
    "fb-carousel": (1080, 1080, "feed"), "fb-feed": (1080, 1350, "feed"),
    "ig-story": (1080, 1920, "story"), "fb-story": (1080, 1920, "story"),
}
# Content padding (px). Story: Meta ad guidance is 14% (~270) top, 20% (~384) bottom, 6% (~65) sides; we use the conservative values.
PAD = {"feed": dict(top=84, bottom=96, side=92), "story": dict(top=270, bottom=384, side=92)}

THEMES = {
    "ink":   dict(bg="{ink}",   fg="{cream}", accent="{gold_light}", small="{gold_light}", rule="rgba(247,243,236,.25)"),
    "cream": dict(bg="{cream}", fg="{ink}",   accent="{gold}",       small="{gold_dark}",  rule="rgba(17,17,17,.18)"),
    "sand":  dict(bg="{sand}",  fg="{ink}",   accent="{gold}",       small="{gold_dark}",  rule="rgba(17,17,17,.18)"),
}


def load_lint():
    p = HERE.parent / "hebrew-punctuation" / "check_he.py"
    if not p.exists():
        return None
    spec = importlib.util.spec_from_file_location("check_he", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def rich(s):
    """Escape text but allow <b>, <i>, <br>. Wrap Latin/number runs in <bdi> so punctuation does not flip in RTL."""
    s = html.escape(str(s), quote=False)
    for t in ("b", "i", "br"):
        s = s.replace(f"&lt;{t}&gt;", f"<{t}>").replace(f"&lt;/{t}&gt;", f"</{t}>").replace(f"&lt;{t}/&gt;", f"<{t}/>")
    parts = re.split(r"(<[^>]+>)", s)
    run = re.compile(r"[A-Za-z0-9][A-Za-z0-9.,%/+×\-]*(?:\s?₪)?")
    parts = [p if p.startswith("<") else run.sub(lambda m: f"<bdi>{m.group(0)}</bdi>", p) for p in parts]
    return "".join(parts)


def fonts_css():
    out = []
    for fam, files in (("FRL", "FrankRuhlLibre"), ("HB", "Heebo")):
        for f in sorted(FONTS.glob(f"{files}-*.ttf")):
            w = f.stem.split("-")[1]
            out.append(f"@font-face{{font-family:'{fam}';src:url('file://{f}') format('truetype');font-weight:{w};}}")
    return "\n".join(out)


CSS = """
*{box-sizing:border-box}html,body{margin:0;background:#000}
.slide{position:relative;width:%(W)spx;height:%(H)spx;overflow:hidden;display:flex;flex-direction:column;
  padding:%(pt)spx %(ps)spx %(pb)spx;background:%(bg)s;color:%(fg)s;direction:rtl;font-family:'HB',sans-serif;--k:1;--u:%(u)s}
.bg{position:absolute;inset:0;background-size:cover;background-position:center}
.scrim{position:absolute;inset:0;background:linear-gradient(to top,rgba(12,9,5,.88) 0%%,rgba(12,9,5,.55) 45%%,rgba(12,9,5,.05) 100%%)}
.bar{position:relative;z-index:2;display:flex;justify-content:space-between;align-items:center;height:56px;flex:0 0 auto;font-size:32px}
.wm{font-family:'FRL',serif;font-weight:700;letter-spacing:.28em;font-size:34px;direction:ltr}
.ct{color:%(small)s;font-weight:500;direction:ltr;letter-spacing:.06em}
.content{position:relative;z-index:2;flex:1;min-height:0;display:flex;flex-direction:column;justify-content:center;overflow:hidden}
.content.bottom{justify-content:flex-end}.content.start{justify-content:flex-start;padding-top:40px}
.eyebrow{font-weight:500;font-size:calc(36px*var(--k)*var(--u));color:%(small)s;margin:0 0 28px}
h1,h2{font-family:'FRL',serif;margin:0;text-wrap:balance;letter-spacing:0}
h1{font-weight:700;font-size:calc(116px*var(--k)*var(--u));line-height:1.12}
h2{font-weight:700;font-size:calc(80px*var(--k)*var(--u));line-height:1.18}
p{text-wrap:pretty;margin:0;font-size:calc(44px*var(--k)*var(--u));line-height:1.5;font-weight:400}
.sub{margin-top:36px;font-size:calc(46px*var(--k)*var(--u));line-height:1.45;opacity:.92}
.rule{width:120px;height:4px;background:%(accent)s;margin:34px 0;border-radius:2px}
.num{font-family:'FRL',serif;font-weight:900;font-size:calc(250px*var(--k)*var(--u));line-height:.95;color:%(accent)s;direction:ltr;text-align:right}
.src{margin-top:40px;font-size:34px;color:%(small)s;font-weight:500}
.hint{position:relative;z-index:2;flex:0 0 auto;font-size:34px;color:%(small)s;font-weight:500;text-align:right;padding-top:24px}
ul{list-style:none;margin:36px 0 0;padding:0;display:flex;flex-direction:column;gap:30px}
li{display:flex;gap:26px;align-items:flex-start;font-size:calc(46px*var(--k)*var(--u));line-height:1.4}
li svg{flex:0 0 52px;margin-top:6px}
table{width:100%%;border-collapse:collapse;margin-top:36px;font-size:calc(40px*var(--k)*var(--u))}
th,td{padding:22px 14px;text-align:right;border-bottom:2px solid %(rule)s;line-height:1.3}
th{font-weight:700;color:%(small)s;font-size:calc(36px*var(--k)*var(--u))}
td:first-child{font-weight:500}
.q{font-family:'FRL',serif;font-weight:500;font-size:calc(84px*var(--k)*var(--u));line-height:1.28;text-wrap:balance}
.pimg{width:100%%;flex:1;min-height:0;border-radius:28px;background-size:cover;background-position:center;background-color:rgba(168,137,79,.18)}
.btn{display:inline-block;margin-top:44px;padding:26px 54px;border-radius:999px;background:%(accent)s;color:#111;font-weight:700;font-size:calc(44px*var(--k)*var(--u))}
.guides{position:absolute;inset:0;z-index:50;pointer-events:none}
.guides div{position:absolute;border:3px dashed}
"""

K0 = {"cover": 1.0, "point": 1.15, "list": 1.3, "compare": 1.25, "stat": 1.05, "quote": 1.15, "product": 1.0, "cta": 1.1}

CHECK = ('<svg viewBox="0 0 52 52" width="52" height="52"><circle cx="26" cy="26" r="25" fill="none" '
         'stroke="currentColor" stroke-width="2" opacity=".5"/><path d="M15 27l8 8 15-17" fill="none" '
         'stroke="currentColor" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/></svg>')


def img_css(path, base):
    if not path:
        return ""
    p = Path(path)
    if not p.is_absolute():
        p = (base / p)
    if not p.exists():
        sys.exit(f"image not found: {p}")
    return f"background-image:url('file://{p}')"


def body_for(s, ctx):
    t = s["type"]
    base = ctx["base"]
    if t == "cover":
        img = img_css(s.get("image"), base)
        bg = f'<div class="bg" style="{img}"></div><div class="scrim"></div>' if img else ""
        content = (f'<div class="content bottom"><div class="eyebrow">{rich(s.get("eyebrow",""))}</div>'
                   f'<h1>{rich(s["title"])}</h1>' + (f'<div class="rule"></div><p class="sub">{rich(s["subtitle"])}</p>' if s.get("subtitle") else "") + '</div>')
        return bg, content, "ink" if img else s.get("theme", "ink")
    if t == "point":
        return "", (f'<div class="content"><div class="num">{rich(s.get("number",""))}</div><div class="rule"></div>'
                    f'<h2>{rich(s["title"])}</h2><p class="sub">{rich(s["text"])}</p></div>'), s.get("theme", "cream")
    if t == "list":
        items = "".join(f"<li>{CHECK}<span>{rich(i)}</span></li>" for i in s["items"])
        return "", f'<div class="content"><h2>{rich(s["title"])}</h2><ul>{items}</ul></div>', s.get("theme", "sand")
    if t == "stat":
        src = f'<div class="src">{rich("מקור: " + s["source"])}</div>' if s.get("source") else ""
        return "", (f'<div class="content"><div class="num">{rich(s["value"])}</div><div class="rule"></div>'
                    f'<h2>{rich(s["title"])}</h2><p class="sub">{rich(s.get("text",""))}</p>{src}</div>'), s.get("theme", "ink")
    if t == "compare":
        head = "".join(f"<th>{rich(c)}</th>" for c in s["cols"])
        rows = "".join("<tr>" + "".join(f"<td>{rich(c)}</td>" for c in r) + "</tr>" for r in s["rows"])
        src = f'<div class="src">{rich("מקור: " + s["source"])}</div>' if s.get("source") else ""
        return "", (f'<div class="content"><h2>{rich(s["title"])}</h2><table><thead><tr>{head}</tr></thead>'
                    f'<tbody>{rows}</tbody></table>{src}</div>'), s.get("theme", "cream")
    if t == "quote":
        who = f'<p class="sub">{rich(s["by"])}</p>' if s.get("by") else ""
        return "", f'<div class="content"><div class="q">{rich(s["text"])}</div><div class="rule"></div>{who}</div>', s.get("theme", "sand")
    if t == "product":
        if "price" in s and not ctx["spec"].get("prices_approved"):
            sys.exit("a product slide has a price but the spec has no \"prices_approved\": true (store rule: prices only with owner approval)")
        img = img_css(s.get("image"), base)
        price = f'<p class="sub"><bdi>{html.escape(str(s["price"]))}</bdi></p>' if "price" in s else ""
        return "", (f'<div class="content start"><div class="pimg" style="{img}"></div><h2 style="margin-top:36px">{rich(s["title"])}</h2>'
                    f'<p class="sub" style="margin-top:12px">{rich(s.get("text",""))}</p>{price}</div>'), s.get("theme", "cream")
    if t == "cta":
        url = ctx["brand"].get("url", "")
        btn = f'<div class="btn">{rich(s.get("button","לכל המאמר באתר"))}</div>'
        u = f'<p class="sub" style="direction:ltr;text-align:right">{html.escape(s.get("url", url))}</p>' if (s.get("url") or url) else ""
        return "", f'<div class="content"><h2>{rich(s["title"])}</h2><p class="sub">{rich(s.get("text",""))}</p>{btn}{u}</div>', s.get("theme", "ink")
    sys.exit(f"unknown slide type: {t}")


def lint_texts(spec, mod):
    findings = []
    heading_keys = {"eyebrow", "title", "button", "value", "number", "cols"}
    def walk(o, key, where):
        if isinstance(o, str):
            if re.search(r"[֐-׿]", o):
                mod.findings.clear()
                mod.check_line(re.sub(r"<[^>]+>", " ", o).strip(), where, heading=key in heading_keys)
                findings.extend(mod.findings)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, key if key != "rows" and key != "items" else "", f"{where}[{i}]")
        elif isinstance(o, dict):
            for k, v in o.items():
                if k in ("image", "type", "theme", "url"):
                    continue
                walk(v, k, f"{where}.{k}")
    for i, s in enumerate(spec["slides"], 1):
        walk(s, "", f"slide {i}")
    if spec.get("caption"):
        walk(spec["caption"], "caption", "caption")
    return findings


def build_slide(s, idx, total, ctx):
    W, H, kind = ctx["W"], ctx["H"], ctx["kind"]
    bg_html, content, theme_name = body_for(s, ctx)
    th = {k: v.format(**ctx["colors"]) for k, v in THEMES[theme_name].items()}
    pad = PAD[kind]
    css = CSS % dict(W=W, H=H, pt=pad["top"], ps=pad["side"], pb=pad["bottom"], u=1.08 if kind == "story" else 1,
                     bg=th["bg"], fg=th["fg"], accent=th["accent"], small=th["small"], rule=th["rule"])
    wm = html.escape(ctx["brand"].get("wordmark", "SEORA"))
    cue = ""
    if idx < total and s.get("hint", True) and s["type"] == "cover":
        cue = '<div class="hint">' + ("הקישו להמשך" if kind == "story" else "החליקו להמשך") + "</div>"
    guides = ""
    if ctx["guides"]:
        side = 65 if kind == "story" else 40
        top = 270 if kind == "story" else 0
        bot = 384 if kind == "story" else 0
        guides = (f'<div class="guides"><div style="left:{side}px;right:{side}px;top:{top}px;bottom:{bot}px;border-color:#e0245e"></div>')
        if kind == "feed" and idx == 1:
            cw = int(H * 0.75)
            if cw < W:
                guides += f'<div style="left:{(W-cw)//2}px;width:{cw}px;top:0;bottom:0;border-color:#1d9bf0"></div>'
        guides += "</div>"
    return (f'<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><style>{fonts_css()}{css}</style></head><body>'
            f'<div class="slide" id="s" data-k0="{K0.get(s["type"], 1)}">{bg_html}<div class="bar"><span class="wm">{wm}</span>'
            f'<span class="ct"><bdi>{idx}/{total}</bdi></span></div>{content}{cue}{guides}</div></body></html>')


FIT_JS = """() => document.fonts.ready.then(() => {
  const s = document.getElementById('s'); const c = s.querySelector('.content');
  let k = parseFloat(s.dataset.k0 || '1'); s.style.setProperty('--k', k);
  while (c && c.scrollHeight > c.clientHeight + 1 && k > 0.55) { k -= 0.03; s.style.setProperty('--k', k.toFixed(2)); }
  return {k: k, overflow: c ? c.scrollHeight > c.clientHeight + 1 : false};
})"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--out", required=True)
    ap.add_argument("--format")
    ap.add_argument("--jpg", action="store_true", help="export JPEG (quality 92) instead of PNG")
    ap.add_argument("--guides", action="store_true", help="draw safe-area guides (review only, never publish)")
    ap.add_argument("--lint", action="store_true", help="run the Hebrew punctuation checker on all slide text and the caption")
    ap.add_argument("--sheet", action="store_true", help="also write contact-sheet.png")
    a = ap.parse_args()
    specp = Path(a.spec).resolve()
    spec = json.loads(specp.read_text(encoding="utf-8"))
    fmt = a.format or spec.get("format", "ig-feed")
    if fmt not in FORMATS:
        sys.exit(f"unknown format {fmt}; choose from {', '.join(FORMATS)}")
    W, H, kind = FORMATS[fmt]
    brand = json.loads((HERE / "brand.json").read_text(encoding="utf-8"))
    brand.update(spec.get("brand", {}))
    if a.lint:
        mod = load_lint()
        if mod is None:
            sys.exit("hebrew-punctuation skill not found next to this skill")
        f = lint_texts(spec, mod)
        for lv, where, text, msg in f:
            print(f"{lv:5} {where}: {text[:90]}\n      -> {msg}")
        errs = sum(1 for x in f if x[0] == "ERROR")
        print(f"lint: {errs} errors, {len(f)-errs} warnings")
        if errs:
            sys.exit(1)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    slides = spec["slides"]
    n = len(slides)
    if kind == "feed" and (n < 2 or n > 20):
        sys.exit("an Instagram carousel needs 2 to 20 slides; Facebook carousel ads 2 to 10")
    if fmt == "fb-carousel" and n > 10:
        sys.exit("Facebook carousel ads allow at most 10 cards")
    ctx = dict(W=W, H=H, kind=kind, brand=brand, colors=brand["colors"], base=specp.parent, guides=a.guides, spec=spec)
    from playwright.sync_api import sync_playwright
    ext = "jpg" if a.jpg else "png"
    files = []
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=CHROMIUM)
        page = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        for i, s in enumerate(slides, 1):
            tmp = out / f".slide-{i:02d}.html"
            tmp.write_text(build_slide(s, i, n, ctx), encoding="utf-8")
            page.goto(f"file://{tmp}")
            r = page.evaluate(FIT_JS)
            if r["overflow"]:
                print(f"WARNING slide {i}: text still overflows at minimum size; shorten it")
            elif r["k"] < 1:
                print(f"note: slide {i} text shrunk to {r['k']:.2f}x to fit")
            name = out / (f"slide-{i:02d}{'_guides' if a.guides else ''}.{ext}")
            kw = dict(path=str(name), clip=dict(x=0, y=0, width=W, height=H))
            if a.jpg:
                kw.update(type="jpeg", quality=92)
            page.screenshot(**kw)
            tmp.unlink()
            files.append(name)
        if a.sheet:
            cols = min(n, 4)
            w = 270 if kind == "feed" else 200
            h = int(w * H / W)
            cells = "".join(f'<img src="file://{f}" width="{w}" height="{h}" style="margin:6px">' for f in files)
            sheet = out / ".sheet.html"
            sheet.write_text(f'<body style="margin:0;background:#222;width:{cols*(w+12)}px;direction:ltr">{cells}</body>', encoding="utf-8")
            sp = b.new_page(viewport={"width": cols * (w + 12), "height": 400})
            sp.goto(f"file://{sheet}")
            sp.wait_for_timeout(300)
            sp.screenshot(path=str(out / "contact-sheet.png"), full_page=True)
            sheet.unlink()
        b.close()
    print(f"{n} slides, {W}x{H} ({fmt}) -> {out}")


if __name__ == "__main__":
    main()
