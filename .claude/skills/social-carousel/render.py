#!/usr/bin/env python3
"""Render a Hebrew (RTL) social carousel from a JSON spec to PNG/JPG with headless Chromium.

  python3 render.py spec.json --out OUT_DIR [--format ig-feed] [--jpg] [--guides] [--lint] [--sheet]

Structure is enforced: slide 1 is the cover (the thumbnail), the last slide is the CTA, every slide shows a numbered pager.
Formats: ig-feed 1080x1350 | ig-feed-34 1080x1440 | ig-square 1080x1080 | fb-carousel 1080x1080 | fb-feed 1080x1350 |
         ig-story 1080x1920 | fb-story 1080x1920
Slide types: cover, point, stat, compare, myth, quiz, list, quote, product, engage, cta   (see SKILL.md)
"""
import argparse, html, importlib.util, json, os, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import art  # noqa: E402

FONTS = HERE / "assets" / "fonts"
CHROMIUM = os.environ.get("CHROMIUM_PATH", "/opt/pw-browsers/chromium")

FORMATS = {  # name: (width, height, kind)
    "ig-feed": (1080, 1350, "feed"), "ig-feed-34": (1080, 1440, "feed"), "ig-square": (1080, 1080, "feed"),
    "fb-carousel": (1080, 1080, "feed"), "fb-feed": (1080, 1350, "feed"),
    "ig-story": (1080, 1920, "story"), "fb-story": (1080, 1920, "story"),
}
# Story safe zone: Meta ad pages say 14% (about 270 px) top, 20% (384 px) bottom, 6% (65 px) sides. Conservative values.
PAD = {"feed": dict(top=78, bottom=70, side=84), "story": dict(top=270, bottom=384, side=92)}
ACTIONS = {"ig-feed": "הקישור בביו", "ig-feed-34": "הקישור בביו", "ig-square": "הקישור בביו", "fb-carousel": "לחצו על הכפתור",
           "fb-feed": "הקישור בתגובה הראשונה", "ig-story": "הקישו על הסטיקר", "fb-story": "החליקו למעלה"}


# ---------------------------------------------------------------- helpers
def rich(s):
    """Escape text but allow <b>, <i>, <br>. Wrap Latin/number runs in <bdi> so punctuation does not flip in RTL."""
    s = html.escape(str(s), quote=False)
    for t in ("b", "i", "br"):
        s = s.replace(f"&lt;{t}&gt;", f"<{t}>").replace(f"&lt;/{t}&gt;", f"</{t}>").replace(f"&lt;{t}/&gt;", f"<{t}/>")
    parts = re.split(r"(<[^>]+>)", s)
    run = re.compile(r"[A-Za-z0-9][A-Za-z0-9.,%/+×\-]*(?:\s?₪)?")
    return "".join(p if p.startswith("<") else run.sub(lambda m: f"<bdi>{m.group(0)}</bdi>", p) for p in parts)


def plain(s):
    return re.sub(r"<[^>]+>", " ", str(s))


def b64(svg):
    import base64
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def load_lint():
    p = HERE.parent / "hebrew-punctuation" / "check_he.py"
    if not p.exists():
        return None
    spec = importlib.util.spec_from_file_location("check_he", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def all_text(spec):
    out = []
    def walk(o, key=""):
        if isinstance(o, str):
            if key not in ("image", "type", "theme", "icon", "format", "gem", "_note"):
                out.append(o)
        elif isinstance(o, list):
            for v in o: walk(v, key)
        elif isinstance(o, dict):
            for k, v in o.items(): walk(v, k)
    walk(spec)
    return out


def check_fonts(spec, brand):
    """Fail when a font has no glyph for a character used in the slides (the 'font only works in English' problem)."""
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        print("note: fontTools not installed, skipping the glyph coverage check (pip install fonttools)")
        return
    text = "".join(plain(t) for t in all_text(spec)) + "0123456789 ,.:%/-"
    chars = sorted({c for c in text if not c.isspace() and c not in "‎‏"})
    bad = False
    for role, fam in brand["fonts"].items():
        files = sorted(FONTS.glob(f"{fam}-*.ttf"))
        if not files:
            sys.exit(f"font '{fam}' ({role}) has no files in {FONTS} named {fam}-<weight>.ttf")
        cmap = TTFont(files[0]).getBestCmap()
        miss = [c for c in chars if ord(c) not in cmap and not (role == "body" and False)]
        # characters the font lacks only matter if that role renders them; report Hebrew, digits and Latin
        miss = [c for c in miss if re.match(r"[֐-׿A-Za-z0-9₪%]", c)]
        if miss:
            bad = True
            print(f"ERROR font {fam} ({role}) has no glyph for: {' '.join(miss)}")
    if bad:
        sys.exit(1)


def fonts_css(brand):
    out = []
    for role, fam in brand["fonts"].items():
        for f in sorted(FONTS.glob(f"{fam}-*.ttf")):
            w = f.stem.split("-")[1]
            out.append(f"@font-face{{font-family:'{role}';src:url('file://{f}') format('truetype');font-weight:{w};}}")
    return "\n".join(out)


def img_css(path, base):
    if not path:
        return ""
    p = Path(path)
    p = p if p.is_absolute() else base / p
    if not p.exists():
        sys.exit(f"image not found: {p}")
    return f"background-image:url('file://{p}')"


# ---------------------------------------------------------------- css
CSS = """
*{box-sizing:border-box}html,body{margin:0;background:#000}
.slide{position:relative;width:@W@px;height:@H@px;overflow:hidden;display:flex;flex-direction:column;padding:@PT@px @PS@px @PB@px;
  direction:rtl;font-family:'body',sans-serif;--k:1;--u:@U@;--small:@SMALL@;--fg:@FG@;background:@BG@;color:@FG@}
.slide *{letter-spacing:0}
.bgart{position:absolute;inset:0;z-index:0;overflow:hidden}.bgart>*{position:absolute}
.frame{position:absolute;inset:30px;border:1.5px solid @GOLDL@;opacity:.55;z-index:1;pointer-events:none}
.cn{position:absolute;z-index:1;width:60px;height:60px}
.cn.a{top:18px;left:18px}.cn.b{top:18px;right:18px;transform:scaleX(-1)}.cn.c{bottom:18px;left:18px;transform:scaleY(-1)}.cn.d{bottom:18px;right:18px;transform:scale(-1,-1)}
.hdr{position:relative;z-index:3;display:flex;justify-content:space-between;align-items:center;flex:0 0 auto;height:60px}
.wm{font-family:'display',serif;font-weight:700;letter-spacing:.3em!important;font-size:34px;direction:ltr;color:@FG@}
.lbl{font-size:30px;font-weight:500;color:@SMALL@}
.main{position:relative;z-index:3;flex:1;min-height:0;display:flex;flex-direction:column;justify-content:center;overflow:hidden}
.main.bottom{justify-content:flex-end}.main.start{justify-content:flex-start;padding-top:26px}
.gt{background:linear-gradient(180deg,#fbeec6 0%,#e3c78d 38%,#b08d57 70%,#8a6a35 100%);-webkit-background-clip:text;background-clip:text;color:transparent}
h1,h2,h3{font-family:'display',serif;margin:0;text-wrap:balance}
h1{font-weight:700;font-size:calc(112px*var(--k)*var(--u));line-height:1.1}
h2{font-weight:700;font-size:calc(82px*var(--k)*var(--u));line-height:1.16}
h3{font-weight:700;font-size:calc(52px*var(--k)*var(--u));line-height:1.2}
p{text-wrap:pretty;margin:0;font-size:calc(44px*var(--k)*var(--u));line-height:1.48}
.sub{margin-top:30px;opacity:.94}
.chip{display:inline-flex;align-items:center;gap:14px;align-self:flex-start;border:2px solid @GOLDL@;color:@SMALL@;border-radius:999px;padding:10px 28px;font-size:calc(34px*var(--u));font-weight:500;margin-bottom:30px}
.chip svg{width:34px;height:34px}
.rule{width:130px;height:5px;border-radius:3px;background:linear-gradient(90deg,#e3c78d,#b08d57);margin:30px 0}
.num{font-family:'display',serif;font-weight:900;font-size:calc(240px*var(--k)*var(--u));line-height:.92;direction:rtl}
.src{margin-top:34px;font-size:calc(32px*var(--u));color:@SMALL@;font-weight:500}
.ico{width:150px;height:150px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:#14100b;
  background:linear-gradient(145deg,#fbeec6,#d3b277 55%,#9a7a3f);box-shadow:0 18px 40px rgba(0,0,0,.28)}
.ico svg{width:84px;height:84px}
.row{display:flex;align-items:center;gap:36px}
.callout{margin-top:40px;display:flex;gap:26px;align-items:flex-start;border-radius:24px;padding:28px 32px;background:@CARD@;border:2px solid @GOLDL@;font-size:calc(40px*var(--u));line-height:1.4}
.callout svg{flex:0 0 56px;width:56px;height:56px;color:@SMALL@}
ul.ck{list-style:none;margin:34px 0 0;padding:0;display:flex;flex-direction:column;gap:22px}
ul.ck li{display:flex;gap:26px;align-items:center;background:@CARD@;border:2px solid @RULE@;border-radius:24px;padding:24px 30px;font-size:calc(44px*var(--k)*var(--u));line-height:1.3}
ul.ck li .b{flex:0 0 64px;height:64px;border-radius:50%;display:flex;align-items:center;justify-content:center;background:linear-gradient(145deg,#fbeec6,#c9a35a);color:#14100b}
ul.ck li .b svg{width:38px;height:38px}
table{width:100%;border-collapse:separate;border-spacing:0;margin-top:34px;font-size:calc(40px*var(--k)*var(--u));background:@CARD@;border-radius:26px;overflow:hidden;border:2px solid @RULE@}
th{background:#14100b;color:#e3c78d;font-weight:700;padding:26px 18px;text-align:right;font-size:calc(36px*var(--k)*var(--u))}
td{padding:26px 18px;text-align:right;border-top:2px solid @RULE@;line-height:1.3}
td:first-child{font-weight:700}tr:nth-child(even) td{background:rgba(176,141,87,.07)}
td.hl{background:rgba(176,141,87,.20)!important;font-weight:700}
.panel{border-radius:34px;padding:44px 48px;position:relative}
.panel.m{background:rgba(190,60,60,.14);border:2px solid rgba(220,90,90,.55)}
.panel.t{background:linear-gradient(160deg,#f3e2b5,#d5b574);color:#14100b}
.tag{display:inline-flex;align-items:center;gap:14px;font-weight:700;font-size:calc(38px*var(--u));margin-bottom:18px}
.tag svg{width:44px;height:44px}
.opt{display:flex;align-items:center;gap:26px;border-radius:999px;border:2px solid @GOLDL@;background:@CARD@;padding:20px 34px;margin-top:22px;font-size:calc(46px*var(--k)*var(--u));font-weight:500}
.opt .l{flex:0 0 74px;height:74px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-family:'display',serif;font-weight:700;font-size:44px;background:linear-gradient(145deg,#fbeec6,#c9a35a);color:#14100b}
.q{font-family:'display',serif;font-weight:500;font-size:calc(84px*var(--k)*var(--u));line-height:1.26;text-wrap:balance}
.qm{font-family:'display',serif;font-size:360px;line-height:.6;height:170px;opacity:.9}
.pimg{width:100%;flex:1;min-height:0;border-radius:200px 200px 28px 28px;background-size:cover;background-position:center;background-color:rgba(176,141,87,.18);border:3px solid @GOLDL@}
.tiles{display:flex;gap:22px;margin-top:40px}
.tile{flex:1;border-radius:28px;padding:34px 22px;text-align:center;background:@CARD@;border:2px solid @GOLDL@}
.tile .ico{width:112px;height:112px;margin:0 auto 22px}.tile .ico svg{width:62px;height:62px}
.tile b{display:block;font-size:calc(40px*var(--u));margin-bottom:8px;font-family:'display',serif}
.tile span{font-size:calc(32px*var(--u));line-height:1.35;opacity:.9;display:block}
.btn{display:flex;align-items:center;justify-content:center;gap:24px;margin-top:44px;border-radius:999px;padding:34px 44px;
  background:linear-gradient(135deg,#fbeec6,#d3b277 50%,#a67f3f);color:#14100b;font-weight:800;font-size:calc(54px*var(--k)*var(--u));
  box-shadow:0 22px 50px rgba(0,0,0,.45),inset 0 2px 0 rgba(255,255,255,.55)}
.btn svg{width:60px;height:60px}
.ask{margin-top:34px;text-align:center;font-size:calc(40px*var(--u));color:@SMALL@;font-weight:500;line-height:1.4}
.teaser{position:relative;z-index:3;flex:0 0 auto;text-align:center;font-size:32px;color:@SMALL@;font-weight:500;padding-bottom:14px}
.pager{position:relative;z-index:3;flex:0 0 auto;display:flex;justify-content:center;align-items:center;gap:12px;height:82px;padding-top:12px}
.pg{width:56px;height:56px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-family:'display',serif;font-weight:700;font-size:30px;
  border:2px solid @PGLINE@;color:@PGTXT@}
.pg.on{width:68px;height:68px;font-size:36px;background:linear-gradient(145deg,#fbeec6,#c9a35a 60%,#9a7a3f);border-color:transparent;color:#14100b;box-shadow:0 8px 24px rgba(0,0,0,.35)}
.pg.done{border-color:@GOLDL@;color:@SMALL@}
.bar{display:flex;gap:8px;width:100%}.bar i{flex:1;height:10px;border-radius:5px;background:@PGLINE@}.bar i.done{background:@GOLDL@}.bar i.on{background:linear-gradient(90deg,#fbeec6,#c9a35a)}
.pgn{font-size:34px;font-weight:700;color:@SMALL@;margin-inline-start:20px;direction:ltr}
.guides{position:absolute;inset:0;z-index:50;pointer-events:none}.guides div{position:absolute;border:3px dashed}
"""

THEMES = {
    "ink":   dict(BG="radial-gradient(120% 90% at 50% 18%,#2b2118 0%,#120e0a 55%,#0a0806 100%)", FG="#f7f3ec", SMALL="#e3c78d",
                  CARD="rgba(255,255,255,.06)", RULE="rgba(247,243,236,.16)", PGLINE="rgba(247,243,236,.35)", PGTXT="rgba(247,243,236,.6)"),
    "cream": dict(BG="linear-gradient(180deg,#faf6ee 0%,#f1eadc 100%)", FG="#14100b", SMALL="#7d6232",
                  CARD="rgba(255,255,255,.75)", RULE="rgba(20,16,11,.14)", PGLINE="rgba(20,16,11,.28)", PGTXT="rgba(20,16,11,.5)"),
    "sand":  dict(BG="linear-gradient(180deg,#efe7d8 0%,#e4d9c3 100%)", FG="#14100b", SMALL="#6e5428",
                  CARD="rgba(255,255,255,.62)", RULE="rgba(20,16,11,.16)", PGLINE="rgba(20,16,11,.3)", PGTXT="rgba(20,16,11,.55)"),
}
K0 = {"cover": 1.0, "point": 1.12, "stat": 1.05, "compare": 1.2, "myth": 1.08, "quiz": 1.1, "list": 1.2, "quote": 1.1, "product": 1.0, "engage": 1.05, "cta": 1.05}


# ---------------------------------------------------------------- slide bodies
def pager_html(idx, n):
    if n <= 9:
        cells = "".join(
            f'<div class="pg {"on" if i == idx else "done" if i < idx else ""}"><bdi>{i}</bdi></div>' for i in range(1, n + 1))
        return f'<div class="pager">{cells}</div>'
    segs = "".join(f'<i class="{"on" if i == idx else "done" if i < idx else ""}"></i>' for i in range(1, n + 1))
    return f'<div class="pager"><div class="bar">{segs}</div><span class="pgn"><bdi>{idx}/{n}</bdi></span></div>'


def watermark(size, style="gold", opacity=.10, where="left:-120px;bottom:60px", seed=5):
    return f'<div style="{where};opacity:{opacity};width:{size}px;height:{size}px">{art.gem(size, style, seed, "wm")}</div>'


def build_body(s, idx, n, ctx):
    t, base, kind, fmt = s["type"], ctx["base"], ctx["kind"], ctx["fmt"]
    story = kind == "story"
    ic = lambda name, size=64, st=3.2: art.icon(name, size, st)
    if t == "cover":
        pad = PAD[kind]
        main_h = ctx["H"] - pad["top"] - 60 - pad["bottom"] - 82 - 46
        gs = int(max(220, min(560, main_h - 428 - 90)))
        img = img_css(s.get("image"), base)
        if img:
            hero = (f'<div style="position:relative;width:{gs}px;height:{gs}px;margin:0 auto;border-radius:50%;{img};background-size:cover;'
                    f'background-position:center;border:4px solid #e3c78d;box-shadow:0 30px 80px rgba(0,0,0,.6)"></div>')
        else:
            hero = (f'<div style="position:relative;width:{gs+90}px;height:{gs+90}px;margin:0 auto;flex:0 0 auto">'
                    f'<div style="position:absolute;inset:-90px;opacity:.9">{art.rays(gs + 270, 28, .2, .98, .09)}</div>'
                    f'<div style="position:absolute;left:45px;top:45px">{art.gem(gs, s.get("gem", "fire"), s.get("seed", 7), "cv")}</div>'
                    f'<div style="position:absolute;inset:0;color:#e3c78d">{art.orbit(gs + 90)}</div></div>')
        pills = f'<div class="chip" style="align-self:center;margin:6px 0 20px">{rich(s["eyebrow"])}</div>' if s.get("eyebrow") else ""
        sub = f'<p class="sub" style="text-align:center;margin-top:16px;font-size:calc(42px*var(--k)*var(--u))">{rich(s["subtitle"])}</p>' if s.get("subtitle") else ""
        main = (f'<div class="main" style="justify-content:center;gap:28px">{hero}<div style="text-align:center;display:flex;flex-direction:column;align-items:center">'
                f'{pills}<h1 class="gt" style="font-size:calc(100px*var(--k)*var(--u))">{rich(s["title"])}</h1>{sub}</div></div>')
        return main, "ink", ""
    if t == "point":
        icon = s.get("icon", "gem")
        callout = (f'<div class="callout">{ic("star", 56)}<div>{rich(s["callout"])}</div></div>') if s.get("callout") else ""
        num = f'<div class="num gt">{rich(s["number"])}</div>' if s.get("number") else ""
        top = f'<div class="row" style="justify-content:space-between;margin-bottom:10px"><div class="ico">{ic(icon, 84, 3)}</div>{num}</div>'
        main = f'<div class="main">{top}<div class="rule"></div><h2>{rich(s["title"])}</h2><p class="sub">{rich(s["text"])}</p>{callout}</div>'
        return main, s.get("theme", "cream"), watermark(560, "gold", .10, "left:-150px;bottom:40px")
    if t == "stat":
        src = f'<div class="src">{rich("מקור: " + s["source"])}</div>' if s.get("source") else ""
        main = (f'<div class="main"><div class="num gt" style="font-size:calc(300px*var(--k)*var(--u))">{rich(s["value"])}</div><div class="rule"></div>'
                f'<h2>{rich(s["title"])}</h2><p class="sub">{rich(s.get("text", ""))}</p>{src}</div>')
        return main, s.get("theme", "ink"), watermark(640, s.get("gem", "ice"), .11, "left:-250px;top:150px", 11)
    if t == "compare":
        hl = s.get("highlight", 1)
        head = "".join(f"<th>{rich(c)}</th>" for c in s["cols"])
        rows = "".join("<tr>" + "".join(f'<td class="{"hl" if j == hl else ""}">{rich(c)}</td>' for j, c in enumerate(r)) + "</tr>" for r in s["rows"])
        src = f'<div class="src">{rich("מקור: " + s["source"])}</div>' if s.get("source") else ""
        chip = f'<div class="chip">{ic("scale", 34, 3)}{rich(s.get("eyebrow", "השוואה"))}</div>'
        main = f'<div class="main">{chip}<h2>{rich(s["title"])}</h2><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>{src}</div>'
        return main, s.get("theme", "cream"), ""
    if t == "myth":
        main = (f'<div class="main" style="gap:26px"><div class="panel m"><div class="tag" style="color:#ff9a9a">{ic("cross", 44, 4)}מיתוס</div>'
                f'<h2 style="font-size:calc(72px*var(--k)*var(--u))">{rich(s["myth"])}</h2></div>'
                f'<div class="panel t"><div class="tag" style="color:#5b4318">{ic("check", 44, 4)}האמת</div>'
                f'<p style="font-size:calc(46px*var(--k)*var(--u));font-weight:500;line-height:1.4">{rich(s["truth"])}</p></div></div>')
        return main, s.get("theme", "ink"), ""
    if t == "quiz":
        letters = ["א", "ב", "ג", "ד"]
        opts = "".join(f'<div class="opt"><div class="l">{letters[i]}</div><div>{rich(o)}</div></div>' for i, o in enumerate(s["options"]))
        ask = f'<div class="ask">{rich(s.get("ask", "כתבו את התשובה בתגובות, והאמת בשקף הבא"))}</div>'
        main = (f'<div class="main"><div class="chip">{ic("question", 34, 3)}{rich(s.get("eyebrow", "בוחנים את עצמנו"))}</div><h2>{rich(s["title"])}</h2>{opts}{ask}</div>')
        return main, s.get("theme", "cream"), watermark(520, "gold", .09, "left:-130px;top:90px", 9)
    if t == "list":
        items = "".join(f'<li><div class="b">{ic("check", 38, 4)}</div><div>{rich(i)}</div></li>' for i in s["items"])
        main = f'<div class="main"><h2>{rich(s["title"])}</h2><ul class="ck">{items}</ul></div>'
        return main, s.get("theme", "sand"), ""
    if t == "quote":
        who = f'<p class="sub" style="color:var(--small)">{rich(s["by"])}</p>' if s.get("by") else ""
        main = f'<div class="main"><div class="qm gt">”</div><div class="q">{rich(s["text"])}</div><div class="rule"></div>{who}</div>'
        return main, s.get("theme", "sand"), ""
    if t == "product":
        if "price" in s and not ctx["spec"].get("prices_approved"):
            sys.exit('a product slide has a price but the spec has no "prices_approved": true (store rule: prices only with owner approval)')
        img = img_css(s.get("image"), base)
        price = f'<p class="sub"><bdi>{html.escape(str(s["price"]))}</bdi></p>' if "price" in s else ""
        main = (f'<div class="main start"><div class="pimg" style="{img}"></div><h2 style="margin-top:34px">{rich(s["title"])}</h2>'
                f'<p class="sub" style="margin-top:10px">{rich(s.get("text", ""))}</p>{price}</div>')
        return main, s.get("theme", "cream"), ""
    if t == "engage":
        items = s.get("items") or [
            {"icon": "bookmark", "title": "שמרו", "text": "לפעם הבאה שבוחרים תכשיט"},
            {"icon": "send", "title": "שלחו", "text": "למי שמחפשת רעיון"},
            {"icon": "comment", "title": "הגיבו", "text": "ספרו מה חשבתם"}]
        tiles = "".join(f'<div class="tile"><div class="ico">{ic(i.get("icon", "heart"), 62, 3)}</div><b>{rich(i["title"])}</b><span>{rich(i.get("text", ""))}</span></div>' for i in items)
        main = (f'<div class="main"><div class="chip">{ic("heart", 34, 3)}{rich(s.get("eyebrow", "לפני שממשיכים"))}</div><h2>{rich(s["title"])}</h2>'
                f'<p class="sub">{rich(s.get("text", ""))}</p><div class="tiles">{tiles}</div></div>')
        return main, s.get("theme", "sand"), ""
    if t == "cta":
        action = s.get("action") or ACTIONS.get(fmt, "הקישור בביו")
        gsz = 330 if not story else 380
        gem = (f'<div style="margin:0 auto 26px;width:{gsz}px;height:{gsz}px;position:relative"><div style="position:absolute;inset:-60px;opacity:.9">{art.rays(gsz + 120, 24, .2, .98, .10)}</div>'
               f'<div style="position:absolute;inset:0">{art.gem(gsz, "gold", 4, "ct")}</div></div>')
        ask = f'<div class="ask">{rich(s["ask"])}</div>' if s.get("ask") else ""
        url = s.get("url", ctx["brand"].get("url", ""))
        u = f'<div class="ask" style="margin-top:22px;color:var(--fg);direction:ltr;font-size:calc(42px*var(--u));letter-spacing:.04em!important">{html.escape(url)}</div>' if url else ""
        sec = f'<p class="sub" style="text-align:center;margin-top:20px">{rich(s["text"])}</p>' if s.get("text") else ""
        main = (f'<div class="main" style="text-align:center">{gem}<h2 class="gt" style="text-align:center">{rich(s["title"])}</h2>{sec}'
                f'<div class="btn">{rich(action)}{ic("arrow", 60, 4)}</div>{ask}{u}</div>')
        return main, "ink", ""
    sys.exit(f"unknown slide type: {t}")


def build_slide(s, idx, n, ctx):
    W, H, kind = ctx["W"], ctx["H"], ctx["kind"]
    main, theme_name, extra = build_body(s, idx, n, ctx)
    th = THEMES[theme_name]
    c = ctx["colors"]
    pad = PAD[kind]
    css = CSS
    mapping = dict(W=W, H=H, PT=pad["top"], PS=pad["side"], PB=pad["bottom"], U=1.08 if kind == "story" else 1, GOLDL=c["gold_light"] if theme_name == "ink" else c["gold"], **th)
    for k, v in mapping.items():
        css = css.replace(f"@{k}@", str(v))
    wm = html.escape(ctx["brand"].get("wordmark", "SEORA"))
    label = ""
    if s["type"] != "cover" and ctx.get("label"):
        label = html.escape(ctx["label"])
    teaser = ""
    if s.get("teaser") and idx < n:
        teaser = f'<div class="teaser">{rich("בשקף הבא: " + s["teaser"])}</div>'
    hint = ""
    if s["type"] == "cover" and n > 1:
        hint = f'<div class="teaser">{"הקישו להמשך" if kind == "story" else "החליקו לגלות"}</div>'
    bg = ""
    if theme_name == "ink":
        bg = (f'<div class="bgart"><div style="inset:0;opacity:.9">{art.lattice("#e3c78d", .05)}</div>'
              f'<div style="left:-200px;top:-160px;width:620px;height:620px;border-radius:50%;background:radial-gradient(circle,rgba(227,199,141,.20),transparent 65%)"></div>'
              f'<div style="right:-220px;bottom:-200px;width:700px;height:700px;border-radius:50%;background:radial-gradient(circle,rgba(227,199,141,.14),transparent 65%)"></div>'
              f'<div style="inset:0;mix-blend-mode:overlay;opacity:.7">{art.grain(.22)}</div>{extra}</div>')
    else:
        bg = (f'<div class="bgart"><div style="inset:0">{art.lattice("#7d6232", .06)}</div>'
              f'<div style="inset:0;mix-blend-mode:multiply;opacity:.5">{art.grain(.10)}</div>{extra}</div>')
    corners = "".join(f'<div class="cn {x}">{art.corner(c["gold_light"] if theme_name == "ink" else c["gold"])}</div>' for x in "abcd")
    guides = ""
    if ctx["guides"]:
        side = 65 if kind == "story" else 40
        top = 270 if kind == "story" else 0
        bot = 384 if kind == "story" else 0
        guides = f'<div class="guides"><div style="left:{side}px;right:{side}px;top:{top}px;bottom:{bot}px;border-color:#e0245e"></div>'
        if kind == "feed" and idx == 1 and int(H * 0.75) < W:
            cw = int(H * 0.75)
            guides += f'<div style="left:{(W - cw)//2}px;width:{cw}px;top:0;bottom:0;border-color:#1d9bf0"></div>'
        guides += "</div>"
    return (f'<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><style>{fonts_css(ctx["brand"])}{css}</style></head><body>'
            f'<div class="slide" id="s" data-k0="{K0.get(s["type"], 1)}">{bg}<div class="frame"></div>{corners}'
            f'<div class="hdr"><span class="wm">{wm}</span><span class="lbl">{label}</span></div>{main}{teaser or hint}{pager_html(idx, n)}{guides}</div></body></html>')


FIT_JS = """() => document.fonts.ready.then(() => {
  const s = document.getElementById('s'); const c = s.querySelector('.main');
  let k = parseFloat(s.dataset.k0 || '1'); s.style.setProperty('--k', k);
  while (c && c.scrollHeight > c.clientHeight + 1 && k > 0.5) { k -= 0.03; s.style.setProperty('--k', k.toFixed(2)); }
  return {k: k, overflow: c ? c.scrollHeight > c.clientHeight + 1 : false};
})"""


def validate(spec, fmt, kind):
    sl = spec["slides"]
    errs, warns = [], []
    if spec.get("strict", True):
        if sl[0]["type"] != "cover":
            errs.append("slide 1 must be the cover (it is the thumbnail)")
        if sl[-1]["type"] != "cta":
            errs.append("the last slide must be the CTA")
        if not any(s["type"] in ("quiz", "myth", "engage") for s in sl[1:-1]) and len(sl) >= 5:
            warns.append("no interactive slide (quiz, myth or engage): add one so people have a reason to comment, save or share")
        if len(sl) < 5 and kind == "feed":
            warns.append("fewer than 5 slides: a carousel of 6 to 10 slides usually works better")
        if not spec.get("caption"):
            warns.append("no caption in the spec: write one with a hook in the first 125 characters, a question, and the action")
        for i, s in enumerate(sl[:-1], 1):
            if s["type"] not in ("cover", "cta") and not s.get("teaser") and i < len(sl) - 1:
                pass
    return errs, warns


def lint_texts(spec, mod):
    findings = []
    heading_keys = {"eyebrow", "title", "button", "value", "number", "cols", "action", "myth", "teaser"}
    def walk(o, key, where):
        if isinstance(o, str):
            if re.search(r"[֐-׿]", o):
                mod.findings.clear()
                mod.check_line(plain(o).strip(), where, heading=key in heading_keys)
                findings.extend(mod.findings)
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, key if key not in ("rows", "items", "options") else "", f"{where}[{i}]")
        elif isinstance(o, dict):
            for k, v in o.items():
                if k in ("image", "type", "theme", "icon", "url", "gem", "_note"):
                    continue
                walk(v, k, f"{where}.{k}")
    for i, s in enumerate(spec["slides"], 1):
        walk(s, "", f"slide {i}")
    if spec.get("caption"):
        walk(spec["caption"], "caption", "caption")
    return findings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--out", required=True)
    ap.add_argument("--format")
    ap.add_argument("--jpg", action="store_true")
    ap.add_argument("--guides", action="store_true", help="draw safe-area guides (review only, never publish)")
    ap.add_argument("--lint", action="store_true")
    ap.add_argument("--sheet", action="store_true")
    a = ap.parse_args()
    specp = Path(a.spec).resolve()
    spec = json.loads(specp.read_text(encoding="utf-8"))
    fmt = a.format or spec.get("format", "ig-feed")
    if fmt not in FORMATS:
        sys.exit(f"unknown format {fmt}; choose from {', '.join(FORMATS)}")
    W, H, kind = FORMATS[fmt]
    brand = json.loads((HERE / "brand.json").read_text(encoding="utf-8"))
    for k, v in spec.get("brand", {}).items():
        if isinstance(v, dict):
            brand.setdefault(k, {}).update(v)
        else:
            brand[k] = v
    check_fonts(spec, brand)
    errs, warns = validate(spec, fmt, kind)
    for w in warns:
        print("WARNING", w)
    if errs:
        for e in errs:
            print("ERROR", e)
        sys.exit(1)
    if a.lint:
        mod = load_lint()
        if mod is None:
            sys.exit("hebrew-punctuation skill not found next to this skill")
        f = lint_texts(spec, mod)
        for lv, where, text, msg in f:
            print(f"{lv:5} {where}: {text[:90]}\n      -> {msg}")
        e = sum(1 for x in f if x[0] == "ERROR")
        print(f"lint: {e} errors, {len(f) - e} warnings")
        if e:
            sys.exit(1)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    slides = spec["slides"]
    n = len(slides)
    if kind == "feed" and not 2 <= n <= 20:
        sys.exit("an Instagram carousel needs 2 to 20 slides")
    if fmt == "fb-carousel" and n > 10:
        sys.exit("Facebook carousel ads allow at most 10 cards")
    ctx = dict(W=W, H=H, kind=kind, fmt=fmt, brand=brand, colors=brand["colors"], base=specp.parent, guides=a.guides, spec=spec,
               label=spec.get("label", ""))
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
                print(f"WARNING slide {i}: text still overflows at the minimum size; shorten it")
            elif r["k"] < 0.9:
                print(f"note: slide {i} text shrunk to {r['k']:.2f}x to fit; consider shortening it")
            name = out / f"slide-{i:02d}{'_guides' if a.guides else ''}.{ext}"
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
            sheet.write_text(f'<body style="margin:0;background:#222;width:{cols * (w + 12)}px;direction:ltr">{cells}</body>', encoding="utf-8")
            sp = b.new_page(viewport={"width": cols * (w + 12), "height": 400})
            sp.goto(f"file://{sheet}")
            sp.wait_for_timeout(300)
            sp.screenshot(path=str(out / "contact-sheet.png"), full_page=True)
            sheet.unlink()
        b.close()
    print(f"{n} slides, {W}x{H} ({fmt}) -> {out}")


if __name__ == "__main__":
    main()
