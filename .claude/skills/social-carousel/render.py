#!/usr/bin/env python3
"""Render a Hebrew (RTL) social carousel from a JSON spec to PNG/JPG with headless Chromium.

  python3 render.py spec.json --out OUT_DIR [--format ig-feed] [--jpg] [--guides] [--lint] [--sheet]

Structure is enforced: slide 1 is the cover (the thumbnail), the last slide is the CTA, every slide shows a numbered pager.
Formats: ig-feed 1080x1350 | ig-feed-34 1080x1440 | ig-square 1080x1080 | fb-carousel 1080x1080 | fb-feed 1080x1350 |
         ig-story 1080x1920 | fb-story 1080x1920
Slide types: cover, cards, point, stat, compare, myth, quiz, list, quote, product, engage, cta   (see SKILL.md)
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


# ---------------------------------------------------------------- css (v3: dark card system)
CSS = """
*{box-sizing:border-box}html,body{margin:0;background:#000}
.slide{position:relative;width:@W@px;height:@H@px;overflow:hidden;display:flex;flex-direction:column;padding:@PT@px @PS@px @PB@px;
  direction:rtl;font-family:'body',sans-serif;--k:1;--u:@U@;color:#f7f3ec;
  background:radial-gradient(90% 55% at 100% 0%,rgba(227,199,141,.22) 0%,transparent 60%),radial-gradient(80% 50% at 0% 100%,rgba(176,141,87,.20) 0%,transparent 62%),linear-gradient(180deg,#171109 0%,#0c0906 55%,#0a0806 100%)}
.slide *{letter-spacing:0}
.bgart{position:absolute;inset:0;z-index:0;overflow:hidden}.bgart>*{position:absolute}
.hdr{position:relative;z-index:3;display:flex;justify-content:space-between;align-items:center;flex:0 0 auto;height:56px}
.cnt{font-family:'display',sans-serif;font-weight:500;font-size:30px;color:rgba(247,243,236,.62);direction:ltr}
.cnt b{color:#e3c78d;font-weight:700}
.wm{font-family:'display',sans-serif;font-weight:800;font-size:38px;letter-spacing:.32em!important;direction:ltr;color:#f7f3ec;margin-inline-end:-.32em}
.main{position:relative;z-index:3;flex:1;min-height:0;display:flex;flex-direction:column;justify-content:center;overflow:hidden;padding:18px 0 10px}
.main.top{justify-content:flex-start;padding-top:34px}
.eyebrow{align-self:flex-start;font-size:calc(30px*var(--u));font-weight:600;color:#e3c78d;margin-bottom:10px;display:flex;gap:12px;align-items:center}
.eyebrow:before{content:"";width:34px;height:3px;border-radius:2px;background:#e3c78d}
.gt{background:linear-gradient(180deg,#fbeec6 0%,#e3c78d 40%,#b08d57 78%,#98733a 100%);-webkit-background-clip:text;background-clip:text;color:transparent}
h1,h2,h3{font-family:'display',sans-serif;margin:0;text-wrap:balance}
h2{font-weight:800;font-size:calc(80px*var(--k)*var(--u));line-height:1.12;margin-bottom:calc(30px*var(--k))}
p{text-wrap:pretty;margin:0;font-size:calc(40px*var(--k)*var(--u));line-height:1.48;color:rgba(247,243,236,.88)}
.chip{display:inline-flex;align-items:center;gap:12px;border:1.5px solid rgba(227,199,141,.55);background:rgba(227,199,141,.10);color:#e3c78d;border-radius:999px;padding:9px 26px;font-size:calc(28px*var(--u));font-weight:600}
.chip svg{width:30px;height:30px}
.card{position:relative;border-radius:30px;padding:calc(26px*var(--k)) calc(32px*var(--k));background:linear-gradient(160deg,rgba(255,255,255,.075),rgba(255,255,255,.03));border:1.5px solid rgba(227,199,141,.26);box-shadow:0 18px 50px rgba(0,0,0,.35)}
.cards{display:flex;flex-direction:column;gap:calc(20px*var(--k))}
.ci{display:flex;gap:26px;align-items:flex-start}
.ci .n{flex:0 0 auto;font-family:'display',sans-serif;font-weight:800;font-size:calc(58px*var(--k)*var(--u));line-height:1;color:#e3c78d;min-width:calc(84px*var(--k));text-align:left;direction:ltr;padding-top:4px}
.ci .t{flex:1;min-width:0}
.ci h3{font-weight:700;font-size:calc(44px*var(--k)*var(--u));line-height:1.2;margin-bottom:8px}
.ci p{font-size:calc(34px*var(--k)*var(--u));line-height:1.45}
.tags{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:12px}
.tag{font-family:'display',sans-serif;font-size:calc(26px*var(--u));font-weight:500;color:#e3c78d;background:rgba(227,199,141,.12);border:1px solid rgba(227,199,141,.35);border-radius:10px;padding:2px 14px;direction:ltr}
.big{font-family:'display',sans-serif;font-weight:900;line-height:.98;direction:rtl}
.src{margin-top:26px;font-size:calc(30px*var(--u));color:rgba(227,199,141,.85);font-weight:500}
table{width:100%;border-collapse:separate;border-spacing:0;font-size:calc(38px*var(--k)*var(--u));border-radius:30px;overflow:hidden;border:1.5px solid rgba(227,199,141,.26);background:rgba(255,255,255,.04)}
th{background:rgba(227,199,141,.16);color:#e3c78d;font-weight:700;padding:calc(24px*var(--k)) 16px;text-align:right;font-size:calc(34px*var(--k)*var(--u))}
td{padding:calc(24px*var(--k)) 16px;text-align:right;border-top:1.5px solid rgba(227,199,141,.16);line-height:1.3}
td:first-child{font-weight:700}td.hl{background:rgba(227,199,141,.13);font-weight:700;color:#fbeec6}
.panel.m{border-color:rgba(255,130,130,.5);background:linear-gradient(160deg,rgba(190,60,60,.20),rgba(190,60,60,.06))}
.panel.t{border-color:rgba(227,199,141,.7);background:linear-gradient(160deg,rgba(227,199,141,.24),rgba(227,199,141,.07))}
.pt{display:flex;align-items:center;gap:12px;font-weight:800;font-size:calc(34px*var(--u));margin-bottom:12px;font-family:'display',sans-serif}
.pt svg{width:38px;height:38px}
.opt{display:flex;align-items:center;gap:24px;border-radius:26px;border:1.5px solid rgba(227,199,141,.35);background:rgba(255,255,255,.05);padding:calc(20px*var(--k)) 28px;margin-top:calc(18px*var(--k));font-size:calc(42px*var(--k)*var(--u));font-weight:600}
.opt .l{flex:0 0 68px;height:68px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-family:'display',sans-serif;font-weight:800;font-size:40px;background:linear-gradient(145deg,#fbeec6,#c9a35a);color:#14100b}
.ask{margin-top:26px;text-align:center;font-size:calc(34px*var(--u));color:#e3c78d;font-weight:500;line-height:1.4}
.vis{position:relative;display:flex;align-items:center;justify-content:center}
.tiles{display:flex;gap:18px;margin-top:calc(26px*var(--k))}
.tile{flex:1;border-radius:26px;padding:calc(26px*var(--k)) 14px;text-align:center;background:rgba(255,255,255,.05);border:1.5px solid rgba(227,199,141,.3)}
.tile svg{width:56px;height:56px;color:#e3c78d;margin:0 auto 12px;display:block}
.tile b{display:block;font-size:calc(38px*var(--u));font-family:'display',sans-serif;font-weight:700;margin-bottom:4px}
.tile span{font-size:calc(28px*var(--u));line-height:1.35;opacity:.8;display:block}
.kw{display:inline-block;font-family:'display',sans-serif;font-weight:800;font-size:calc(64px*var(--k)*var(--u));line-height:1;color:#14100b;background:linear-gradient(135deg,#fbeec6,#d3b277 55%,#a67f3f);border-radius:20px;padding:10px 30px 14px;margin:0 18px;box-shadow:0 10px 30px rgba(176,141,87,.35)}
.savebar{display:flex;align-items:center;gap:14px;font-size:calc(30px*var(--u));font-weight:600;color:rgba(247,243,236,.85)}
.savebar svg{width:34px;height:34px;color:#e3c78d}
.ftr{position:relative;z-index:3;flex:0 0 auto;display:flex;justify-content:space-between;align-items:center;height:50px}
.hint{display:flex;align-items:center;gap:12px;font-size:28px;font-weight:600;color:rgba(247,243,236,.7)}
.hint svg{width:30px;height:30px;color:#e3c78d;transform:scaleX(-1)}
.dash{display:flex;gap:8px;direction:rtl}
.dash i{display:block;width:34px;height:6px;border-radius:3px;background:rgba(247,243,236,.20)}
.dash i.done{background:rgba(227,199,141,.62)}.dash i.on{background:linear-gradient(90deg,#fbeec6,#c9a35a);width:52px}
.url{font-family:'display',sans-serif;font-size:28px;font-weight:600;color:#e3c78d;direction:ltr;letter-spacing:.06em!important}
.guides{position:absolute;inset:0;z-index:50;pointer-events:none}.guides div{position:absolute;border:3px dashed}
"""
K0 = {"cover": 1.0, "cards": 1.25, "point": 1.3, "stat": 1.15, "compare": 1.35, "myth": 1.3, "quiz": 1.3, "list": 1.15, "quote": 1.1, "product": 1.0, "engage": 1.3, "cta": 1.0}


# ---------------------------------------------------------------- slide bodies
def dashes(idx, n):
    return '<div class="dash">' + "".join(f'<i class="{"on" if i == idx else "done" if i < idx else ""}"></i>' for i in range(1, n + 1)) + "</div>"


def tags_html(tags):
    return '<div class="tags">' + "".join(f'<span class="tag">{html.escape(t)}</span>' for t in tags) + "</div>" if tags else ""


def build_body(s, idx, n, ctx):
    t, base, kind, fmt = s["type"], ctx["base"], ctx["kind"], ctx["fmt"]
    story = kind == "story"
    ic = lambda name, size=64, st=3.2: art.icon(name, size, st)
    eyebrow = f'<div class="eyebrow">{rich(s["label"])}</div>' if s.get("label") else (f'<div class="eyebrow">{rich(s["eyebrow"])}</div>' if s.get("eyebrow") and t != "cover" else "")
    if t == "cover":
        pad = PAD[kind]
        main_h = ctx["H"] - pad["top"] - 56 - pad["bottom"] - 50 - 28
        text_h = 60 + (230 if s.get("big") else 0) + (80 if s.get("mid") else 0) + 120 + (70 if s.get("subtitle") else 0) + 60
        gs = int(max(0, min(600, main_h - text_h - 30)))
        img = img_css(s.get("image"), base)
        vis = ""
        if gs >= 200:
            if img:
                inner = f'<div style="width:{gs}px;height:{gs}px;border-radius:50%;{img};background-size:cover;background-position:center;border:3px solid #e3c78d;box-shadow:0 30px 80px rgba(0,0,0,.6)"></div>'
            else:
                inner = (f'<div style="position:relative;width:{gs}px;height:{gs}px"><div style="position:absolute;inset:-70px;opacity:.85">{art.rays(gs + 140, 28, .2, .98, .08)}</div>'
                         f'<div style="position:absolute;inset:0">{art.gem(gs, s.get("gem", "fire"), s.get("seed", 7), "cv")}</div>'
                         f'<div style="position:absolute;inset:-36px;color:#e3c78d;opacity:.8">{art.orbit(gs + 72)}</div></div>')
            vis = f'<div class="vis" style="margin:22px 0 10px;height:{gs + 40}px">{inner}</div>'
        chip = f'<div class="chip" style="align-self:flex-start;margin-bottom:22px">{rich(s["eyebrow"])}</div>' if s.get("eyebrow") else ""
        big = f'<div class="big gt" style="font-size:calc(230px*var(--k)*var(--u))">{rich(s["big"])}</div>' if s.get("big") else ""
        mid = f'<div style="font-family:display;font-weight:500;font-size:calc(52px*var(--k)*var(--u));margin:6px 0 4px;color:rgba(247,243,236,.92)">{rich(s["mid"])}</div>' if s.get("mid") else ""
        sz = 104 if (s.get("big") or s.get("mid")) else 118
        hl = f'<h1 style="font-weight:800;font-size:calc({sz}px*var(--k)*var(--u));line-height:1.08;margin-top:6px" class="{"" if (s.get("big") or s.get("mid")) else "gt"}">{rich(s["title"])}</h1>'
        sub = f'<p style="margin-top:20px;font-size:calc(38px*var(--k)*var(--u))">{rich(s["subtitle"])}</p>' if s.get("subtitle") else ""
        save = f'<div class="savebar" style="margin-top:26px">{ic("bookmark", 34, 3)}{rich(s.get("save", "שמרו את הפוסט לפני שבוחרים אבן"))}</div>'
        return f'<div class="main">{chip}{big}{mid}{hl}{sub}{vis}{save}</div>'
    if t in ("cards", "point"):
        if t == "point":  # single large card: title + text (+ callout)
            items = [{"title": s.get("title2") or "", "text": s.get("text", "")}]
            body = (f'<div class="card"><p style="font-size:calc(44px*var(--k)*var(--u))">{rich(s["text"])}</p></div>'
                    + (f'<div class="card" style="margin-top:20px;border-color:rgba(227,199,141,.6)"><div class="ci">{ic("star", 52, 3)}<div class="t"><p style="color:#fbeec6;font-weight:500">{rich(s["callout"])}</p></div></div></div>' if s.get("callout") else ""))
            num = f'<div class="big gt" style="font-size:calc(150px*var(--k)*var(--u));margin-bottom:10px">{rich(s["number"])}</div>' if s.get("number") else ""
            return f'<div class="main">{eyebrow}{num}<h2>{rich(s["title"])}</h2>{body}</div>'
        start = s.get("start")
        rows = []
        for j, it in enumerate(s["items"]):
            num = f'{(start + j):02d}' if start is not None else f'{j + 1:02d}'
            rows.append(f'<div class="card"><div class="ci"><div class="n"><bdi>{num}</bdi></div><div class="t">{tags_html(it.get("tags"))}'
                        f'<h3>{rich(it["title"])}</h3><p>{rich(it.get("text", ""))}</p></div></div></div>')
        return f'<div class="main top">{eyebrow}<h2>{rich(s["title"])}</h2><div class="cards">{"".join(rows)}</div></div>'
    if t == "stat":
        src = f'<div class="src">{rich("מקור: " + s["source"])}</div>' if s.get("source") else ""
        return (f'<div class="main">{eyebrow}<div class="big gt" style="font-size:calc(270px*var(--k)*var(--u))">{rich(s["value"])}</div>'
                f'<h2 style="margin-top:14px">{rich(s["title"])}</h2><div class="card"><p>{rich(s.get("text", ""))}</p></div>{src}</div>')
    if t == "compare":
        hl = s.get("highlight", 1)
        head = "".join(f"<th>{rich(c)}</th>" for c in s["cols"])
        rows = "".join("<tr>" + "".join(f'<td class="{"hl" if j == hl else ""}">{rich(c)}</td>' for j, c in enumerate(r)) + "</tr>" for r in s["rows"])
        src = f'<div class="src">{rich("מקור: " + s["source"])}</div>' if s.get("source") else ""
        return f'<div class="main">{eyebrow or f"<div class=eyebrow>השוואה</div>"}<h2>{rich(s["title"])}</h2><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>{src}</div>'
    if t == "myth":
        return (f'<div class="main">{eyebrow or "<div class=eyebrow>מיתוס או עובדה</div>"}<div class="cards" style="gap:24px">'
                f'<div class="card panel m"><div class="pt" style="color:#ff9a9a">{ic("cross", 38, 4)}מיתוס</div>'
                f'<h2 style="font-size:calc(66px*var(--k)*var(--u));margin:0">{rich(s["myth"])}</h2></div>'
                f'<div class="card panel t"><div class="pt" style="color:#e3c78d">{ic("check", 38, 4)}האמת</div>'
                f'<p style="font-size:calc(42px*var(--k)*var(--u));font-weight:500;color:#fff">{rich(s["truth"])}</p></div></div></div>')
    if t == "quiz":
        letters = ["א", "ב", "ג", "ד"]
        opts = "".join(f'<div class="opt"><div class="l">{letters[i]}</div><div>{rich(o)}</div></div>' for i, o in enumerate(s["options"]))
        ask = f'<div class="ask">{rich(s.get("ask", "כתבו את התשובה בתגובות, והאמת בשקף הבא"))}</div>'
        return f'<div class="main">{eyebrow or "<div class=eyebrow>בוחנים את עצמנו</div>"}<h2>{rich(s["title"])}</h2>{opts}{ask}</div>'
    if t == "list":
        items = "".join(f'<div class="card"><div class="ci"><div class="n" style="min-width:0">{ic("check", 46, 4)}</div><div class="t"><p style="font-size:calc(40px*var(--k)*var(--u));color:#fff;font-weight:500">{rich(i)}</p></div></div></div>' for i in s["items"])
        return f'<div class="main top">{eyebrow}<h2>{rich(s["title"])}</h2><div class="cards">{items}</div></div>'
    if t == "quote":
        who = f'<p style="margin-top:20px;color:#e3c78d">{rich(s["by"])}</p>' if s.get("by") else ""
        return (f'<div class="main">{eyebrow}<div class="card" style="padding:48px 44px"><div class="big gt" style="font-size:220px;height:120px;line-height:.9">”</div>'
                f'<div style="font-family:display;font-weight:600;font-size:calc(66px*var(--k)*var(--u));line-height:1.28">{rich(s["text"])}</div>{who}</div></div>')
    if t == "product":
        if "price" in s and not ctx["spec"].get("prices_approved"):
            sys.exit('a product slide has a price but the spec has no "prices_approved": true (store rule: prices only with owner approval)')
        img = img_css(s.get("image"), base)
        price = f'<p style="margin-top:8px;color:#e3c78d;font-weight:700"><bdi>{html.escape(str(s["price"]))}</bdi></p>' if "price" in s else ""
        return (f'<div class="main top">{eyebrow}<div style="flex:1;min-height:0;border-radius:30px;{img};background-size:cover;background-position:center;'
                f'background-color:rgba(227,199,141,.12);border:1.5px solid rgba(227,199,141,.4)"></div><h2 style="margin:26px 0 8px;font-size:calc(64px*var(--k)*var(--u))">{rich(s["title"])}</h2>'
                f'<p>{rich(s.get("text", ""))}</p>{price}</div>')
    if t == "engage":
        items = s.get("items") or [
            {"icon": "bookmark", "title": "שמרו", "text": "לפעם הבאה שבוחרים תכשיט"},
            {"icon": "send", "title": "שלחו", "text": "למי שמחפשת רעיון"},
            {"icon": "comment", "title": "הגיבו", "text": "ספרו מה חשבתם"}]
        tiles = "".join(f'<div class="tile">{ic(i.get("icon", "heart"), 56, 3)}<b>{rich(i["title"])}</b><span>{rich(i.get("text", ""))}</span></div>' for i in items)
        return (f'<div class="main">{eyebrow or "<div class=eyebrow>לפני שממשיכים</div>"}<h2>{rich(s["title"])}</h2>'
                f'<div class="card"><p>{rich(s.get("text", ""))}</p></div><div class="tiles">{tiles}</div></div>')
    if t == "cta":
        brand = ctx["brand"]
        handle = s.get("follow", brand.get("handle") or brand.get("wordmark", "SEORA"))
        action = s.get("action") or ACTIONS.get(fmt, "הקישור בביו")
        kw = s.get("keyword")
        if kw:
            q = (f'<p style="text-align:center;font-size:calc(40px*var(--k)*var(--u));color:#fff">{rich(s.get("ask", ""))}</p>'
                 f'<div style="text-align:center;margin-top:18px;font-family:display;font-weight:800;font-size:calc(56px*var(--k)*var(--u))">הגיבו<span class="kw">{html.escape(kw)}</span></div>'
                 f'<p style="text-align:center;margin-top:16px;font-size:calc(30px*var(--u));opacity:.8">{rich(s.get("text", ""))}</p>')
        else:
            q = (f'<h2 class="gt" style="text-align:center;margin:0 0 12px">{rich(s["title"])}</h2>'
                 + (f'<p style="text-align:center">{rich(s["text"])}</p>' if s.get("text") else "")
                 + f'<div style="text-align:center;margin-top:22px"><span class="kw" style="font-size:calc(46px*var(--k)*var(--u));margin:0">{rich(action)}</span></div>'
                 + (f'<div class="ask" style="margin-top:18px">{rich(s["ask"])}</div>' if s.get("ask") else ""))
        items = s.get("items") or [
            {"icon": "bookmark", "title": "שמרו", "text": "לפעם הבאה"},
            {"icon": "send", "title": "שתפו", "text": "עם מי שמחפשת"},
            {"icon": "comment", "title": "הגיבו", "text": "ספרו לנו"}]
        tiles = "".join(f'<div class="tile">{ic(i.get("icon", "heart"), 52, 3)}<b>{rich(i["title"])}</b><span>{rich(i.get("text", ""))}</span></div>' for i in items)
        chip = f'<div style="text-align:center;margin-bottom:24px"><span class="chip">{rich(s.get("eyebrow", "וזה לא נגמר כאן"))}</span></div>'
        tag = f'<p style="text-align:center;margin-top:10px;font-size:calc(32px*var(--u));opacity:.8">{rich(s["tagline"])}</p>' if s.get("tagline") else ""
        return (f'<div class="main">{chip}<div class="card" style="padding:calc(34px*var(--k)) 30px">{q}</div>'
                f'<div style="text-align:center;margin-top:calc(28px*var(--k));font-family:display;font-weight:500;font-size:calc(40px*var(--u));color:rgba(247,243,236,.85)">ועקבו אחרי</div>'
                f'<div class="big gt" style="text-align:center;font-size:calc(96px*var(--k)*var(--u));letter-spacing:.14em!important;direction:ltr">{html.escape(handle)}</div>{tag}<div class="tiles">{tiles}</div></div>')
    sys.exit(f"unknown slide type: {t}")


def build_slide(s, idx, n, ctx):
    W, H, kind = ctx["W"], ctx["H"], ctx["kind"]
    main = build_body(s, idx, n, ctx)
    pad = PAD[kind]
    css = CSS
    for k, v in dict(W=W, H=H, PT=pad["top"], PS=pad["side"], PB=pad["bottom"], U=1.08 if kind == "story" else 1).items():
        css = css.replace(f"@{k}@", str(v))
    wm = html.escape(ctx["brand"].get("wordmark", "SEORA"))
    last = idx == n
    if last:
        left = f'<span class="url">{html.escape(ctx["brand"].get("url", ""))}</span>'
    else:
        left = f'<span class="hint">{art.icon("arrow", 30, 3.4)}{"הקישו להמשך" if kind == "story" else "החליקו"}</span>'
    bg = (f'<div class="bgart"><div style="inset:0;opacity:.9">{art.lattice("#e3c78d", .045)}</div>'
          f'<div style="inset:0;mix-blend-mode:overlay;opacity:.6">{art.grain(.2)}</div></div>')
    guides = ""
    if ctx["guides"]:
        side = 65 if kind == "story" else 40
        top, bot = (270, 384) if kind == "story" else (0, 0)
        guides = f'<div class="guides"><div style="left:{side}px;right:{side}px;top:{top}px;bottom:{bot}px;border-color:#e0245e"></div>'
        if kind == "feed" and idx == 1 and int(H * 0.75) < W:
            cw = int(H * 0.75)
            guides += f'<div style="left:{(W - cw)//2}px;width:{cw}px;top:0;bottom:0;border-color:#1d9bf0"></div>'
        guides += "</div>"
    return (f'<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><style>{fonts_css(ctx["brand"])}{css}</style></head><body>'
            f'<div class="slide" id="s" data-k0="{K0.get(s["type"], 1)}">{bg}'
            f'<div class="hdr"><span class="wm">{wm}</span><span class="cnt"><b>{idx:02d}</b> / {n:02d}</span></div>{main}'
            f'<div class="ftr">{dashes(idx, n)}{left}</div>{guides}</div></body></html>')



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
