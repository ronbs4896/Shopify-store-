---
name: social-carousel
description: Build Hebrew (RTL) Instagram and Facebook carousels and story frames for the SEORA store from a short JSON spec, rendered by headless Chromium to exact-size PNG or JPG. The first slide is the thumbnail, the last is the call to action, every slide has a counter and progress dashes, and there is always an interactive slide. Use whenever the owner asks for a carousel, a swipe post, a feed series, a story series, or "קרוסלה" for Instagram or Facebook, including turning a blog article into a carousel.
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

1. **Slide 1 is the thumbnail** (`cover`). It is what people see in the feed and in the 3:4 profile tile, so it has a chip (`eyebrow`, for example "מדריך · 8 שקפים"), a huge gold number or phrase (`big`), a white lead-in (`mid`), the highlighted title, a one-line promise, a visual (gem or photo) and a "שמרו את הפוסט..." line (`save`).
2. **Slides 2 to N-1 are content.** One idea per slide. At least one of them must be interactive (`quiz`, `myth` or `engage`); the renderer warns when none is.
3. **The last slide is the CTA** (`cta`): one clear action as a card with a question and a comment keyword (`keyword`, only if the owner will really send something to people who comment it) or a button, "ועקבו אחרי SEORA", and three tiles (שמרו, שתפו, הגיבו). The default action text depends on the format (feed: "הקישור בביו", story: "הקישו על הסטיקר", Facebook post: "הקישור בתגובה הראשונה"); override with `action`.
4. **Every slide shows where you are**: a counter "03 / 08" top-left, the wordmark top-right, and segmented dashes bottom-right that fill from the right (slide 1 is the right-most dash), plus "החליקו" with an arrow bottom-left (on the last slide the site address instead).
5. Content slides group at most 4 numbered cards (`cards`), each with a bold title, optional Latin `tags` and 2 to 3 lines of text. The section label (`label`, for example "שלב 2 מתוך 3") sits above the title.
6. The renderer refuses a spec whose first slide is not `cover` or whose last is not `cta` (set `"strict": false` only for a deliberate exception).

## Interaction (what makes people comment, save and share)

- `quiz`: a question with 2 to 4 options (א, ב, ג), "כתבו את התשובה בתגובות, והאמת בשקף הבא". Put the answer on the next slide (a `stat` or `point`).
- `myth`: "מיתוס" and "האמת" on one slide. Good for sharing.
- `engage`: the "שווה לשמור" slide with three tiles (שמרו, שלחו, הגיבו). Put it second from the end.
- `cta` `ask`: a closing question, such as "איזו אבן הייתם בוחרים? כתבו בתגובות".
- Hook on slide 1 (a question or a surprising claim that slide 3 answers), and a caption that repeats the question.
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
| `cover` | `title`, `eyebrow` (chip), `big`, `mid`, `subtitle`, `save`, `gem` (`fire`, `ice`, `gold`), `seed`, `image` (optional round photo instead of the gem) |
| `cards` | `label`, `title`, `items` (1 to 4 of `title`, `text`, `tags`), `start` (first number, to continue across slides) |
| `point` | `label`, `number`, `title`, `text`, `callout` |
| `stat` | `value`, `title`, `text`, `source`, `gem` |
| `compare` | `eyebrow`, `title`, `cols`, `rows`, `highlight` (column index), `source` |
| `myth` | `myth`, `truth` |
| `quiz` | `title`, `options`, `ask`, `eyebrow` |
| `list` | `title`, `items` (3 to 5 short lines) |
| `quote` | `text`, `by` |
| `product` | `title`, `text`, `image`, `price` (only with `"prices_approved": true`) |
| `engage` | `title`, `text`, `items` (`icon`, `title`, `text`; defaults to שמרו, שלחו, הגיבו) |
| `cta` | `eyebrow`, `ask`, `keyword`, `text`, `follow` (default: wordmark), `tagline`, `items` (three tiles); without `keyword`: `title`, `action` button |

All slides share one dark gold design (ink background, warm gold glows, faint lattice). Text fields accept `<b>`, `<i>` and `<br>`; Latin letters and numbers are isolated automatically so punctuation does not flip in RTL. Icons are Phosphor Icons, duotone weight (MIT, `assets/icons/`, licence file included), painted with a gold gradient and shown in glass or solid-gold medallions (`art.badge`). Use them in `cards` items (`icon`), `point` (`icon`) and `engage`/`cta` tiles. Names: any file in `assets/icons` (diamond, ruler, scales, shield-check, sparkle, certificate, seal-check, crown-simple, truck, package, gift, heart, star, bookmark-simple, paper-plane-tilt, chat-circle, check, x, ...) plus the old aliases gem, scale, shield, magnifier, bolt, bookmark, send, comment, cross, arrow. To add more, copy `<name>-duotone.svg` from the `@phosphor-icons/core` npm package to `assets/icons/<name>.svg`. Image paths are relative to the spec file. In the cloud session `cdn.shopify.com` is blocked, so photos have to be local files the owner supplies.

## Fonts: one family for Hebrew, numbers and English

Headlines, numbers, the wordmark and the pager all use the **display** font and body text uses the **body** font, both configured in `brand.json` (`fonts`). Today both are **Birzia** (Light 300, Medium 500, Bold 700, Black 900; all verified to contain every Hebrew letter, digits, Latin, ₪, ״ and ׳). The Birzia files are the owner's licensed font: they live in `assets/fonts/Birzia-<weight>.otf` and are **git-ignored** (not in the public repo); on a clone without them the renderer warns and falls back to Rubik (display) and Heebo (body) from `brand.json` `fallback`. Birzia's Latin letters are capitals only, so tags and the site address render in capitals. To change a font, put `Family-400.ttf`, `Family-700.ttf` and so on in `assets/fonts` and change the name in `brand.json`. Before rendering, the script checks every character in the spec against the font and **stops with an error if the font has no glyph for a Hebrew letter, a digit or a Latin letter**, so a font that only works in English cannot slip through. 

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

- Type (1080 wide): page title 80 px, card title 44 px, card text 34 px, tags and chips 26 to 30 px. Cards are the only place text goes below 40 px.
- Contrast: small text is white or light gold on the dark background; never dark text on a mid-tone.
- Slide 1 must work as a 3:4 tile and as a standalone post: keep its key content between x = 40 and x = 1040.
- Keep every slide the same size. Never reverse the file order for Hebrew: slide 1 is the cover.
- If a slide reports `text shrunk` or `overflows`, shorten the copy instead of accepting it.

## Direction (RTL) and swipe cues

No source says how Instagram's carousel behaves in Hebrew UI (swipe direction, dots, counter). The design therefore uses direction-agnostic cues: the counter, the dashes and the word "החליקו" with a small arrow (taken from the approved reference; it points left, which is unverified for Instagram's Hebrew UI). Do not write "החליקו שמאלה" and do not run a panorama across slides until the owner has run the two-phone test in `references/specs.md`.

## Known gaps

`references/specs.md` lists what is verified and what is not: swipe direction in Hebrew UI, the organic Stories bottom margin (20% or 35%), whether 3:4 is accepted in carousels, and Meta's ad policy wording for diamond-alternative sellers. Treat them as unknown.
