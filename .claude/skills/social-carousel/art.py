"""Procedural SVG art for the carousel skill: faceted gem, sparkles, icons, ornaments, grain."""
import math, random


def _hsl(h, s, l):
    h = (h % 360) / 360.0
    s = max(0, min(1, s)); l = max(0, min(1, l))
    def f(p, q, t):
        t %= 1
        if t < 1/6: return p + (q - p) * 6 * t
        if t < 1/2: return q
        if t < 2/3: return p + (q - p) * (2/3 - t) * 6
        return p
    if s == 0:
        r = g = b = l
    else:
        q = l * (1 + s) if l < .5 else l + s - l * s
        p = 2 * l - q
        r, g, b = f(p, q, h + 1/3), f(p, q, h), f(p, q, h - 1/3)
    return "#%02x%02x%02x" % (int(r * 255 + .5), int(g * 255 + .5), int(b * 255 + .5))


def gem(size=600, style="fire", seed=7, uid="g"):
    """Round brilliant seen from above. style: fire (spectral flashes), ice (white/blue), gold (champagne)."""
    rnd = random.Random(seed)
    R = size / 2 * 0.86
    cx = cy = size / 2
    rt, rs = 0.40 * R, 0.68 * R
    def pt(a, r): return (cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))
    C = [pt(22.5 + 45 * i, rt) for i in range(8)]
    S = [pt(45 * i, rs) for i in range(9)]
    O = [pt(22.5 * j, R) for j in range(17)]
    light = -120
    facets = [("table", C, 200, 0)]
    for i in range(8):
        facets.append(("star", [C[i - 1], C[i], S[i]], 45 * i, i))
        facets.append(("kite", [C[i], S[i], O[(2 * i + 1) % 16], S[i + 1]], 22.5 + 45 * i, i))
        facets.append(("gird", [S[i + 1], O[(2 * i + 1) % 16], O[(2 * i + 2) % 16]], 45 * i + 33, 2 * i))
        facets.append(("gird", [S[i + 1], O[(2 * i + 2) % 16], O[(2 * i + 3) % 16]], 45 * i + 56, 2 * i + 1))
    hue0, sat0 = {"fire": (214, .16), "ice": (212, .20), "gold": (38, .50)}[style]
    spectrum = [330, 355, 28, 48, 150, 185, 230, 275]
    out, defs = [], []
    for n, (kind, pts, ang, k) in enumerate(facets):
        d = 0.5 + 0.5 * math.cos(math.radians(ang - light))
        flick = rnd.uniform(-.07, .07)
        if kind == "table":
            l_hi, l_lo = .97, .80
        elif kind == "star":
            l_hi, l_lo = .94 - .10 * (1 - d) + flick, .70 - .20 * (1 - d)
        elif kind == "kite":
            l_hi, l_lo = .86 * d + .22 + flick, .60 * d + .12
        else:
            bright = (k % 2 == 0)
            l_hi = (.88 if bright else .46) * (.55 + .45 * d) + flick
            l_lo = l_hi - .22
        l_hi, l_lo = max(.26, min(.98, l_hi)), max(.16, min(.95, l_lo))
        h, s = hue0, sat0
        if style == "fire" and kind in ("gird", "star", "kite") and rnd.random() < .42:
            h, s = spectrum[(k * 3 + n) % 8], .46
            l_hi, l_lo = max(.62, min(.84, l_hi * .7 + .26)), max(.50, min(.68, l_lo * .7 + .22))
        if style == "gold":
            s = .55 if kind != "table" else .30
        # gradient from the facet's outer vertex towards the centre
        far = max(pts, key=lambda p: (p[0] - cx) ** 2 + (p[1] - cy) ** 2)
        near = min(pts, key=lambda p: (p[0] - cx) ** 2 + (p[1] - cy) ** 2)
        gid = f"{uid}f{n}"
        defs.append(f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="{far[0]:.1f}" y1="{far[1]:.1f}" x2="{near[0]:.1f}" y2="{near[1]:.1f}">'
                    f'<stop offset="0" stop-color="{_hsl(h, s, l_lo)}"/><stop offset="1" stop-color="{_hsl(h, s * .9, l_hi)}"/></linearGradient>')
        d_attr = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + " Z"
        out.append(f'<path d="{d_attr}" fill="url(#{gid})" stroke="rgba(255,255,255,.62)" stroke-width="1.2" stroke-linejoin="round"/>')
    # reflections inside the table: an eight-point star and a soft sheen
    refl = []
    for i in range(8):
        a = pt(45 * i, rt * .93); b = pt(22.5 + 45 * i, rt * .45); c = pt(45 * (i + 1), rt * .93)
        refl.append(f'<path d="M{cx:.1f},{cy:.1f} L{a[0]:.1f},{a[1]:.1f} L{b[0]:.1f},{b[1]:.1f} Z" fill="rgba(120,135,160,{.10 + .10 * (i % 2):.2f})" stroke="rgba(255,255,255,.5)" stroke-width="1"/>')
    hl = (f'<ellipse cx="{cx - R*.20:.1f}" cy="{cy - R*.30:.1f}" rx="{R*.34:.1f}" ry="{R*.10:.1f}" transform="rotate(-38 {cx - R*.20:.1f} {cy - R*.30:.1f})" fill="url(#{uid}-hl)"/>')
    ring = f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="rgba(255,255,255,.85)" stroke-width="2.4"/>'
    glow = f'<circle cx="{cx}" cy="{cy}" r="{R*1.18}" fill="url(#{uid}-glow)"/>'
    defs.append(f'<radialGradient id="{uid}-glow"><stop offset=".6" stop-color="#fff" stop-opacity=".22"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>'
                f'<radialGradient id="{uid}-hl"><stop offset="0" stop-color="#fff" stop-opacity=".9"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>')
    spark = sparkle(size * .13, cx - R * .50, cy - R * .56, uid + "s1") + sparkle(size * .08, cx + R * .74, cy + R * .46, uid + "s2")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" height="{size}">'
            f'<defs>{"".join(defs)}</defs>{glow}{"".join(out)}{"".join(refl)}{hl}{ring}{spark}</svg>')


def sparkle(r, x, y, uid="sp"):
    """Slim four-point star with long arms and a soft halo."""
    k = r * .035
    d = (f"M{x},{y-r} Q{x+k},{y-k} {x+r},{y} Q{x+k},{y+k} {x},{y+r} Q{x-k},{y+k} {x-r},{y} Q{x-k},{y-k} {x},{y-r} Z")
    return (f'<defs><radialGradient id="{uid}h"><stop offset="0" stop-color="#fff" stop-opacity=".95"/><stop offset=".25" stop-color="#fff" stop-opacity=".35"/>'
            f'<stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient></defs>'
            f'<circle cx="{x}" cy="{y}" r="{r*.38}" fill="url(#{uid}h)" opacity=".6"/><path d="{d}" fill="#fff" fill-opacity=".92"/>'
            f'<circle cx="{x}" cy="{y}" r="{r*.07}" fill="#fff"/>')


def rays(size, n=24, inner=.18, outer=.98, opacity=.10):
    cx = cy = size / 2
    out = []
    for i in range(n):
        a = 360 / n * i
        w = 1.4 if i % 2 else 3.2
        x1, y1 = cx + size / 2 * inner * math.cos(math.radians(a)), cy + size / 2 * inner * math.sin(math.radians(a))
        x2, y2 = cx + size / 2 * outer * math.cos(math.radians(a)), cy + size / 2 * outer * math.sin(math.radians(a))
        out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#fff" stroke-opacity="{opacity if i%2 else opacity*1.8:.3f}" stroke-width="{w}"/>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" height="{size}">{"".join(out)}</svg>'


def orbit(size, ticks=72):
    """Thin gold ring with tick marks, to frame the hero gem."""
    cx = cy = size / 2
    r = size / 2 - 4
    t = []
    for i in range(ticks):
        a = math.radians(360 / ticks * i)
        L = 14 if i % 6 == 0 else 6
        t.append(f'<line x1="{cx + (r-L)*math.cos(a):.1f}" y1="{cy + (r-L)*math.sin(a):.1f}" x2="{cx + r*math.cos(a):.1f}" y2="{cy + r*math.sin(a):.1f}"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" height="{size}">'
            f'<g stroke="currentColor" stroke-width="2" fill="none" stroke-opacity=".85"><circle cx="{cx}" cy="{cy}" r="{r}"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r-26}" stroke-opacity=".35"/>{"".join(t)}</g></svg>')


def grain(opacity=.10):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%"><filter id="n"><feTurbulence type="fractalNoise" '
            'baseFrequency=".9" numOctaves="2" stitchTiles="stitch"/><feColorMatrix values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 .5 0"/></filter>'
            f'<rect width="100%" height="100%" filter="url(#n)" opacity="{opacity}"/></svg>')


def lattice(color="#ffffff", opacity=.05, step=90):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%"><defs><pattern id="l" width="{step}" height="{step}" patternUnits="userSpaceOnUse">'
            f'<path d="M{step/2},6 L{step-6},{step/2} L{step/2},{step-6} L6,{step/2} Z" fill="none" stroke="{color}" stroke-opacity="{opacity}" stroke-width="1.5"/></pattern></defs>'
            f'<rect width="100%" height="100%" fill="url(#l)"/></svg>')


ICON_DIR = __import__("pathlib").Path(__file__).resolve().parent / "assets" / "icons"
ALIAS = {"gem": "diamond", "ruler": "ruler", "scale": "scales", "shield": "shield-check", "magnifier": "magnifying-glass", "bolt": "lightning",
         "bookmark": "bookmark-simple", "send": "paper-plane-tilt", "comment": "chat-circle", "cross": "x", "arrow": "arrow-right",
         "crown": "crown-simple", "share": "share-network", "swipe": "hand-swipe-left", "verified": "seal-check", "cert": "certificate"}
_n = [0]


def icon_names():
    return sorted(p.stem for p in ICON_DIR.glob("*.svg"))


def icon(name, size=64, stroke=None, color=None):
    """Phosphor duotone icon (MIT). color=None paints a gold gradient, otherwise any CSS colour or 'currentColor'."""
    import re
    name = ALIAS.get(name, name)
    f = ICON_DIR / f"{name}.svg"
    if not f.exists():
        f = ICON_DIR / "diamond.svg"
    svg = f.read_text(encoding="utf-8")
    _n[0] += 1
    gid = f"ig{_n[0]}"
    paint = color or f"url(#{gid})"
    defs = (f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff3cf"/>'
            f'<stop offset=".5" stop-color="#e3c78d"/><stop offset="1" stop-color="#b08d57"/></linearGradient></defs>') if not color else ""
    svg = svg.replace('fill="currentColor"', f'fill="{paint}"', 1).replace('opacity="0.2"', 'opacity="0.38"')
    svg = svg.replace("<svg ", f'<svg width="{size}" height="{size}" ', 1)
    return re.sub(r"(<svg[^>]*>)", lambda m: m.group(1) + defs, svg, count=1)


def badge(name, size=96, filled=False):
    """Icon medallion: glass tile with gold rim and glow (outlined) or solid gold tile with a dark icon (filled)."""
    r = size * .30
    inner = icon(name, int(size * .58), color="#17110a") if filled else icon(name, int(size * .60))
    bg = ("background:linear-gradient(145deg,#fff3cf,#d3b277 55%,#a67f3f);box-shadow:0 10px 28px rgba(176,141,87,.45),inset 0 2px 0 rgba(255,255,255,.6)" if filled else
          "background:radial-gradient(120% 120% at 30% 15%,rgba(227,199,141,.30),rgba(227,199,141,.06) 60%),rgba(255,255,255,.04);"
          "border:1.5px solid rgba(227,199,141,.55);box-shadow:0 12px 30px rgba(0,0,0,.4),0 0 30px rgba(227,199,141,.18),inset 0 1px 0 rgba(255,255,255,.25)")
    return (f'<div style="width:{size}px;height:{size}px;border-radius:{r:.0f}px;display:flex;align-items:center;justify-content:center;flex:0 0 auto;position:relative;overflow:hidden;{bg}">'
            f'<div style="position:absolute;left:0;right:0;top:0;height:48%;background:linear-gradient(180deg,rgba(255,255,255,{.34 if filled else .10}),transparent)"></div>'
            f'<div style="position:relative;display:flex">{inner}</div></div>')


def corner(color="#d3b277"):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 60 60" width="60" height="60" fill="none" stroke="{color}" stroke-width="2.2">'
            f'<path d="M2 58V2h56"/><path d="M12 48V12h36" opacity=".5"/><path d="M2 2l14 14" opacity=".7"/></svg>')
