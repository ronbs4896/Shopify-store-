---
name: social-carousel
description: Build Hebrew (RTL) Instagram and Facebook carousels and story frames for the SEORA store from a short JSON spec, rendered by headless Chromium to exact-size PNG or JPG. Use whenever the owner asks for a carousel, a swipe post, a feed series, a story series, or "קרוסלה" for Instagram or Facebook, including turning a blog article into a carousel.
---

# Social carousels (Instagram + Facebook, Hebrew RTL)

One JSON spec in, numbered slide images out. The renderer is `render.py` in this folder; it uses the brand fonts in `assets/fonts` (Frank Ruhl Libre for headlines, Heebo for body, both OFL) and the colours in `brand.json`.

```
python3 .claude/skills/social-carousel/render.py spec.json --out OUT_DIR --lint --sheet
python3 .claude/skills/social-carousel/render.py spec.json --out OUT_DIR --format ig-story
python3 .claude/skills/social-carousel/render.py spec.json --out OUT_DIR --guides      # review only, never publish these
```

Flags: `--format` (overrides the spec), `--jpg` (quality 92), `--guides` (draws safe areas, files get a `_guides` suffix), `--lint` (runs the Hebrew punctuation checker on every text field and the caption, fails on errors), `--sheet` (writes `contact-sheet.png` for a quick look).
Chromium is expected at `/opt/pw-browsers/chromium` (override with `CHROMIUM_PATH`). Always look at the contact sheet and at least the first and densest slide with the Read tool before sending anything.

## Workflow

1. **Facts first.** Take facts only from approved articles or from a source the owner has accepted. Every statistic or property slide gets a `source` line. If a fact is not approved, leave it out.
2. **Write the spec** (see below). One idea per slide. Slide 1 is the hook, the last slide is the call to action.
3. **Lint** (`--lint`). Fix every ERROR, think about every WARN.
4. **Render, then review** the contact sheet and the slides. Text that shrank (`note: slide N text shrunk`) or overflowed (`WARNING`) means the copy is too long: shorten it, do not accept it.
5. **Check guides once** (`--guides`): nothing important may touch the dashed rectangles or the 3:4 crop on slide 1.
6. **Deliver** the slides plus: a caption, an alt text per slide, and (for stories) the sticker plan. Use `SendUserFile` for the images.

## Formats

| `--format` | Size | Use |
|---|---|---|
| `ig-feed` (default) | 1080x1350 (4:5) | Instagram feed carousel, 2 to 20 slides |
| `ig-feed-34` | 1080x1440 (3:4) | Same, fills the 3:4 profile tile without cropping (check the app accepts it) |
| `ig-square` | 1080x1080 | Instagram square |
| `fb-carousel` | 1080x1080 | Facebook carousel ad cards, 2 to 10, one ratio for all |
| `fb-feed` | 1080x1350 | Facebook multi-photo post |
| `ig-story`, `fb-story` | 1080x1920 | Story frames, one image per frame |

Stories have no native carousel: post the frames in order. The renderer reserves 270 px at the top, 384 px at the bottom and 92 px at the sides, and puts a `1/N` counter plus "הקישו להמשך" on the cover. Leave the lower third free for the link sticker and the middle for poll or question stickers. These margins are conservative; Meta's own pages disagree (see `references/specs.md`).

## Spec

```json
{
  "format": "ig-feed",
  "prices_approved": false,
  "brand": {"wordmark": "SEORA", "url": "seora.co.il"},
  "slides": [ {"type": "cover", "title": "..."} ],
  "caption": "..."
}
```

| `type` | Fields |
|---|---|
| `cover` | `title`, `eyebrow`, `subtitle`, `image` (optional, gets a dark scrim) |
| `point` | `number` ("01"), `title`, `text` |
| `list` | `title`, `items` (3 to 5 short lines) |
| `stat` | `value` (big number), `title`, `text`, `source` |
| `compare` | `title`, `cols`, `rows` (list of lists, first cell is the row label), `source` |
| `quote` | `text`, `by` |
| `product` | `title`, `text`, `image`, `price` (only with `"prices_approved": true`) |
| `cta` | `title`, `text`, `button`, `url` |

All slides accept `theme` (`ink`, `cream`, `sand`). Text fields accept `<b>`, `<i>` and `<br>`. Latin letters and numbers are wrapped in `<bdi>` automatically so punctuation does not flip in RTL. Image paths are relative to the spec file. In the cloud session `cdn.shopify.com` is blocked, so product photos have to be local files the owner supplies.

## Store rules that apply to every slide

- Hebrew follows the `hebrew-punctuation` skill (no full stop after headings and buttons, ב-5 and ה-GRA with a hyphen, ״ in acronyms, no em dash). `--lint` checks it.
- Spell it **מואסנייט**. Moissanite is **not a diamond**: never "יהלום מעבדה" for it, and avoid "יהלום מוסאנייט" in new copy.
- No prices or discounts without the owner's explicit approval (the renderer refuses a `price` without `prices_approved`).
- No invented reviews, ratings, follower counts or "thousands of customers".
- Do not promise "עמיד במים", "היפואלרגני", "לא מתייבש", "אקולוגי" or "ניטרלי פחמן". Plated silver wears; say so if it comes up.
- Do not call the GRA card an independent laboratory certificate.
- Text in images has no hard limit on Meta, but keep each slide to one idea and under about 25 words of body copy.

## Design rules

- Type: headlines 80 px or more, body 44 px or more, labels 32 px or more (a 1080 px slide is shown at roughly a third of its size on a phone).
- Contrast at least 4.5:1 for small text. Metallic gold on cream is for large text and decoration only; the renderer uses a darker gold for small gold text.
- Slide 1 must work as a 3:4 profile tile and as a standalone post. Keep its key content between x = 40 and x = 1040.
- Keep every slide the same size. The first slide sets the frame and the others are cropped to it.
- Never reverse the file order for Hebrew: slide 1 is always the cover.

## Direction (RTL) and swipe cues

No source says how Instagram's carousel behaves in Hebrew UI (swipe direction, dots, counter). So the design uses direction-agnostic cues: a `1/N` counter drawn in the image and the words "החליקו להמשך". Do not write "החליקו שמאלה", do not draw one big arrow and do not run a panorama across slides until the owner has run the two-phone test in `references/specs.md`.

## Caption, alt text, hashtags (as of October 2026, verify before relying)

- Caption: up to 2,200 characters, and only about the first 125 are visible before "עוד", so put the hook there. Link goes in the bio (feed) or the link sticker (story).
- Hashtags: Instagram has limited posts to 5 since December 2025.
- Alt text: one per slide, under about 100 characters, describing what is on the slide.
- Facebook carousel ads: 1:1 cards, 2 to 10, headline 32 characters or fewer, primary text 125.

## Known gaps

`references/specs.md` lists what is verified and what is not. The main open items: swipe direction in Hebrew UI, the organic Stories bottom margin (20% or 35%), whether 3:4 is accepted in carousels, and Meta's ad policy wording for diamond-alternative sellers. Treat them as unknown, not as rules.
