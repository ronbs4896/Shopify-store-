---
name: social-carousel
description: Build Hebrew (RTL) Instagram and Facebook carousels and story frames for the SEORA store from a short JSON spec, rendered by headless Chromium to exact-size PNG or JPG. The first slide is the thumbnail, the last is the call to action, every slide has a numbered pager, and there is always an interactive slide. Use whenever the owner asks for a carousel, a swipe post, a feed series, a story series, or "קרוסלה" for Instagram or Facebook, including turning a blog article into a carousel.
---

# Social carousels (Instagram + Facebook, Hebrew RTL)

One JSON spec in, numbered slide images out. The renderer is `render.py` in this folder. Art is drawn in code (`art.py`: faceted gem, sparkles, icons, ornaments), so no photos are needed. A photo can be added to a cover or product slide when the owner supplies a local file.

```
python3 .claude/skills/social-carousel/render.py spec.json --out OUT_DIR --lint --sheet
python3 .claude/skills/social-carousel/render.py spec.json --out OUT_DIR --format ig-story
python3 .claude/skills/social-carousel/render.py spec.json --out OUT_DIR --guides     # review only, never publish these
```

Flags: `--format` (overrides the spec), `--jpg` (quality 92), `--guides` (safe areas, files get a `_guides` suffix), `--lint` (Hebrew punctuation checker on every text field and the caption, fails on errors), `--sheet` (writes `contact-sheet.png`).
Chromium is expected at `/opt/pw-browsers/chromium` (override with `CHROMIUM_PATH`). **Always look at the contact sheet, and at the first, the densest and the last slide at full size, with the Read tool, before sending anything.**

## The structure is fixed

1. **Slide 1 is the thumbnail** (`cover`). It is what people see in the feed and in the 3:4 profile tile, so it has the hero art, a short tag line (`eyebrow`, for example "מדריך · 8 שקפים"), a title of up to about 7 words and a one-line promise.
2. **Slides 2 to N-1 are content.** One idea per slide. At least one of them must be interactive (`quiz`, `myth` or `engage`); the renderer warns when none is.
3. **The last slide is the CTA** (`cta`): one clear action as a large button, a question that invites a comment, and the site address. The default action text depends on the format (feed: "הקישור בביו", story: "הקישו על הסטיקר", Facebook post: "הקישור בתגובה הראשונה"); override with `action`.
4. **Every slide shows a numbered pager** (1, 2, 3 ... N, the current one filled in gold, 1 on the right). With more than 9 slides it becomes a segmented bar plus "5/12".
5. Optional `teaser` on a slide shows "בשקף הבא: ..." above the pager and gives a reason to keep swiping.
6. The renderer refuses a spec whose first slide is not `cover` or whose last is not `cta` (set `"strict": false` only for a deliberate exception).

## Interaction (what makes people comment, save and share)

- `quiz`: a question with 2 to 4 options (א, ב, ג), "כתבו את התשובה בתגובות, והאמת בשקף הבא". Put the answer on the next slide (a `stat` or `point`).
- `myth`: "מיתוס" and "האמת" on one slide. Good for sharing.
- `engage`: the "שווה לשמור" slide with three tiles (שמרו, שלחו, הגיבו). Put it second from the end.
- `cta` `ask`: a closing question, such as "איזו אבן הייתם בוחרים? כתבו בתגובות".
- Hook on slide 1 (a question or a surprising claim that slide 3 answers), `teaser` lines in between, and a caption that repeats the question.
- Stories: use `quiz` frames and leave the middle band free for a poll or question sticker, and the lower third for the link sticker.

## Formats

| `--format` | Size | Use |
|---|---|---|
| `ig-feed` (default) | 1080x1350 (4:5) | Instagram feed carousel, 2 to 20 slides |
| `ig-feed-34` | 1080x1440 (3:4) | Same, fills the 3:4 profile tile (check the app accepts it) |
| `ig-square`, `fb-carousel` | 1080x1080 | Square; Facebook carousel ad cards (2 to 10, one ratio) |
| `fb-feed` | 1080x1350 | Facebook multi-photo post |
| `ig-story`, `fb-story` | 1080x1920 | Story frames, one image per frame |

Stories have no native carousel: post the frames in order. The renderer keeps everything 270 px from the top, 384 px from the bottom and 92 px from the sides. The square format is tight, so keep its copy shorter.

## Spec

```json
{
  "format": "ig-feed",
  "label": "מדריך אבנים",
  "prices_approved": false,
  "slides": [ {"type": "cover", "eyebrow": "...", "title": "...", "subtitle": "..."} ],
  "caption": "..."
}
```

| `type` | Fields |
|---|---|
| `cover` | `title`, `eyebrow`, `subtitle`, `gem` (`fire`, `ice`, `gold`), `seed`, `image` (optional round photo instead of the gem) |
| `point` | `number`, `icon`, `title`, `text`, `callout` |
| `stat` | `value`, `title`, `text`, `source`, `gem` |
| `compare` | `eyebrow`, `title`, `cols`, `rows`, `highlight` (column index), `source` |
| `myth` | `myth`, `truth` |
| `quiz` | `title`, `options`, `ask`, `eyebrow` |
| `list` | `title`, `items` (3 to 5 short lines) |
| `quote` | `text`, `by` |
| `product` | `title`, `text`, `image`, `price` (only with `"prices_approved": true`) |
| `engage` | `title`, `text`, `items` (`icon`, `title`, `text`; defaults to שמרו, שלחו, הגיבו) |
| `cta` | `title`, `text`, `action`, `ask`, `url` |

Every slide accepts `theme` (`ink`, `cream`, `sand`), `teaser` and `hint`. Text fields accept `<b>`, `<i>` and `<br>`; Latin letters and numbers are isolated automatically so punctuation does not flip in RTL. Icons for `point` and `engage`: gem, ruler, scale, shield, drop, magnifier, bolt, check, cross, bookmark, send, comment, heart, star, gift, tag, question, clock, flame, arrow, link, globe. Image paths are relative to the spec file. In the cloud session `cdn.shopify.com` is blocked, so photos have to be local files the owner supplies.

## Fonts: one family for Hebrew, numbers and English

Headlines, numbers, the wordmark and the pager all use the **display** font and body text uses the **body** font, both configured in `brand.json` (`fonts`). Today they are Frank Ruhl Libre and Heebo, which contain Hebrew, Latin and digits. To change a font, put `Family-400.ttf`, `Family-700.ttf` and so on in `assets/fonts` and change the name in `brand.json`. Before rendering, the script checks every character in the spec against the font and **stops with an error if the font has no glyph for a Hebrew letter, a digit or a Latin letter**, so a font that only works in English cannot slip through. The brand font the owner wants is still to be confirmed (see the open item below).

## Store rules that apply to every slide

- Hebrew follows the `hebrew-punctuation` skill. `--lint` checks it.
- Spell it **מואסנייט**. Moissanite is **not a diamond**: never "יהלום מעבדה" for it, and avoid "יהלום מוסאנייט" in new copy.
- No prices or discounts without the owner's explicit approval (the renderer refuses a `price` without `prices_approved`).
- No invented reviews, ratings, follower counts or "thousands of customers".
- Every number and claim gets a `source` line, and comes only from approved articles or sources the owner accepted.
- Do not promise "עמיד במים", "היפואלרגני", "אקולוגי" or "ניטרלי פחמן". Plated silver wears; say so if it comes up.
- Do not call the GRA card an independent laboratory certificate.

## Caption (always write one, it is part of the deliverable)

1. A hook in the first 125 characters (only about that much shows before "עוד"). 2,200 characters at most.
2. One line of value, then a question people can answer in a comment.
3. The action, matching the last slide (for feed "הקישור בביו").
4. Up to 5 hashtags (Instagram has limited posts to 5 since December 2025; verify before relying on it).
5. Alt text for every slide, under about 100 characters.

## Design rules

- Type: headlines 80 px or more, body 44 px or more, labels 30 px or more.
- Contrast: gold on cream is used for large text and decoration only; small gold text is the darker gold.
- Slide 1 must work as a 3:4 tile and as a standalone post: keep its key content between x = 40 and x = 1040.
- Keep every slide the same size. Never reverse the file order for Hebrew: slide 1 is the cover.
- If a slide reports `text shrunk` or `overflows`, shorten the copy instead of accepting it.

## Direction (RTL) and swipe cues

No source says how Instagram's carousel behaves in Hebrew UI (swipe direction, dots, counter). The design therefore uses direction-agnostic cues: the numbered pager and the words "החליקו לגלות". Do not write "החליקו שמאלה", do not draw a big arrow and do not run a panorama across slides until the owner has run the two-phone test in `references/specs.md`.

## Known gaps

`references/specs.md` lists what is verified and what is not: swipe direction in Hebrew UI, the organic Stories bottom margin (20% or 35%), whether 3:4 is accepted in carousels, and Meta's ad policy wording for diamond-alternative sellers. Treat them as unknown. Open item: the owner asked for a specific brand font ("בירזיה"); its exact name or file is needed.
