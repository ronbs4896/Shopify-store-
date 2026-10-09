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
- Staging theme now: "SEORA - טיוטה קבועה (Claude)", gid://shopify/OnlineStoreTheme/190441914664 (synced with live on 2026-10-08, plus the hidden video view counts). Live: 190447812904. They swap each time the owner publishes; check roles with `themes { id name role }` before writing.
- Prices and discounts change only with the owner's explicit approval.
- No invented reviews or ratings.
