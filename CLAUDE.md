# SEORA store: notes for Claude

## Hebrew text (always)

Every piece of Hebrew text, including chat replies to the store owner, follows `.claude/skills/hebrew-punctuation/SKILL.md`. Load the skill before writing Hebrew copy, then run the checker on the draft or on the files you changed:

```
python3 .claude/skills/hebrew-punctuation/check_he.py --headings --text "כותרת"
python3 .claude/skills/hebrew-punctuation/check_he.py templates/product.seora.json
```

The short version: no full stop at the end of headings, buttons or labels; no chains of short fragments separated by full stops; no space before punctuation; a hyphen between a prefix letter and a number or Latin word (ב-5, ה-GRA); ״ in acronyms (ש״ח, ס״מ); no em dashes.

## Skills

- `.claude/skills/hebrew-punctuation`: every Hebrew text (see above).
- `.claude/skills/social-carousel`: Instagram and Facebook carousels and story frames in Hebrew, rendered from a JSON spec. Read its SKILL.md first; it also lists the store rules that apply to social copy.

## Store rules

- Theme files are written only to an unpublished theme; the owner publishes.
- Do not create a new theme for each change. Keep one staging theme and reuse it. When the owner publishes staging, the theme that was live becomes unpublished: bring it up to date with the live files (themeFilesCopy/Upsert) and use it as the next staging theme. Duplicate a theme only if no unpublished Claude theme exists, and tell the owner first.
- Staging theme now: "SEORA - טיוטה קבועה (Claude)", gid://shopify/OnlineStoreTheme/190441914664 (synced with live on 2026-10-09, plus favicon, cart drawer, home blog section, article card thumbnails, author photo slot, 100% tables). Live: 190447812904. They swap each time the owner publishes; check roles with `themes { id name role }` before writing.
- Prices and discounts change only with the owner's explicit approval.
- No invented reviews or ratings.
- Iron rule for every blog article: it goes up with internal links (to other articles and to collections) and with a named author. Authors alternate by article order, odd orders "רון בן שושן" and even orders "מתן כלפון". Each author has a photo that the theme shows next to the byline (the owner supplies the photos). Never publish with "צוות SEORA" or without an author.
- Article tables must be 100% width with no horizontal scroll on mobile (theme CSS in `assets/seora-blog.css` enforces it; keep table markup plain).
- Publishing a theme (themePublish) is blocked for Claude by the Shopify MCP safety policy even when the owner approves; the owner clicks Publish in the Shopify admin. Before they do, re-diff staging against live (live changes between syncs, e.g. templates/index.json and config/settings_data.json).
- Author photos: the theme reads assets/author-ron-ben-shushan.jpg and assets/author-matan-kalfon.jpg (square, at least 400 px). Until they exist the initial letter shows.
- Favicon: gold Ś monogram on ink (assets/seora-favicon-*.png, linked in layout/theme.liquid). Replace the PNGs if the owner supplies a different mark.
