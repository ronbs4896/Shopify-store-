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

- RTL: layout/theme.liquid sets dir="rtl" on <html> for Hebrew; assets/global.js SliderComponent and SlideshowComponent are patched for RTL scrolling (negative scrollLeft). Check carousels after theme updates.
- Hebrew font: Birzia (Hebrew range only) in layout/theme.liquid with Light 300, Medium 500, Bold 700, Black 900 (files in Shopify Files). Weights are not forced: elements keep their own weight and the browser maps 400-500 to Medium, 600-700 to Bold, 800-900 to Black; headings default to Black. Birzia has no Regular or SemiBold.
- RTL cards: layout/theme.liquid outputs the card text alignment settings as start/end (left→start, right→end) so cards follow the page direction; assets/seora-rtl.css (linked after lumin.css) mirrors physical left/right rules (price gap, quick-add icon) and hides the vendor line on product cards (every product has the default vendor "My Store"). It also flips theme rules that force left: cart progress message and upsell, form fields and floating labels (search buttons go to the left), predictive search, cart page table, mobile menu back row, `.left` utility class, contact headings. The Sense RTL app embed is also enabled in settings_data. All text on the site must read and align right to left (owner request).
- Video testimonials: sections/seora-video-reviews.liquid ("SEORA המלצות וידאו"), a row of tall video cards with a play button and the customer name at the bottom; replaces the old shoppable-video-new section (disabled, not deleted) on the home page and both product templates. Names stay empty until the owner fills in real customer names.
- Product carousel: sections/seora-product-carousel.liquid ("SEORA קרוסלת מוצרים"), cards with a rounded image frame, a round sale badge with rotating text (only on products whose compare-at price is above the price; {n} = real discount percent), title, divider, optional reviews row (real review metafields only), short line from metafield custom.text-v1, pill button. Defaults to the "הנמכרים ביותר" collection. Not placed on any template; the owner adds it in the editor.
- Collection pages: category dropdown (sections/seora-collection-chips.liquid, assets/seora-collection-bar.css) next to the filter button; product-card scrolling tags are off.
- Product page stock badge (sections/main-product-seora.liquid, snippets/spi-*): shows the real units left only when stock is tracked and at or under stock_low_limit (default 10); above that the normal in-stock text. Never show a made-up number. The upsell add button stays "נוסף לעגלה" with a "הסרה" link.
- WhatsApp: floating button bottom right (bottom left is the accessibility widget), snippets/seora-whatsapp.liquid (rendered in layout/theme.liquid), number 972523199277 with a prefilled message.
- Newsletter: sections/seora-newsletter.liquid ("SEORA מועדון לקוחות"), last section on the home page under the blog; the old newsletter section is disabled. Shopify customer form, tag newsletter.
- Footer: sections/seora-footer.liquid (section "SEORA פוטר" in the footer group; the old Lumin footer is disabled, not deleted). Social links are section settings; Instagram, Facebook and TikTok stay hidden until the owner fills them in.

- Theme files are written only to an unpublished theme; the owner publishes.
- Do not create a new theme for each change. Keep one staging theme and reuse it. When the owner publishes staging, the theme that was live becomes unpublished: bring it up to date with the live files (themeFilesCopy/Upsert) and use it as the next staging theme. Duplicate a theme only if no unpublished Claude theme exists, and tell the owner first.
- Theme names: anything Claude creates or renames from now on is labelled "By RBS", never "(Claude)" (owner request, 2026-11-04). Example: "SEORA - טיוטה (By RBS)".
- Staging theme now: gid://shopify/OnlineStoreTheme/191299092776 "SEORA - טיוטה (By RBS)" (unpublished again after the owner published 190447812904 on 2026-11-08). Live: 190447812904, also named "SEORA - טיוטה (By RBS)"; tell them apart by id and role. They swap each time the owner publishes; check roles with `themes { id name role }` before writing. To sync, themeFilesUpsert with body type URL pointing at raw.githubusercontent.com of a pushed commit works for text and binary files (the repo is public); settings_data.json keeps the live checksum. Shopify blocks themeFilesDelete for Claude: unused files stay until the owner deletes them in the code editor. A section whose schema is invalid (e.g. an external default on a url setting) is dropped silently by URL upserts, so verify checksums after every upload. JSON files saved by the theme editor are stored minified: their checksumMd5 is the md5 of json.dumps(data, ensure_ascii=False, separators=(',',':')) with every "/" escaped as "\/", so compare a pretty local copy that way.
- Prices and discounts change only with the owner's explicit approval.
- Meta ads: single-image ads only (one image per ad). Never build carousels unless the owner explicitly asks for one.
- No invented reviews or ratings.
- Iron rule for every blog article: it goes up with internal links (to other articles and to collections) and with a named author. Authors alternate by article order, odd orders "רון בן שושן" and even orders "מתן כלפון". Each author has a photo that the theme shows next to the byline (the owner supplies the photos). Never publish with "צוות SEORA" or without an author.
- Article tables must be 100% width with no horizontal scroll on mobile (theme CSS in `assets/seora-blog.css` enforces it; keep table markup plain).
- Publishing a theme (themePublish) is blocked for Claude by the Shopify MCP safety policy even when the owner approves; the owner clicks Publish in the Shopify admin. Before they do, re-diff staging against live (live changes between syncs, e.g. templates/index.json and config/settings_data.json).
- Author photos: the theme reads assets/author-ron-ben-shushan.jpg and assets/author-matan-kalfon.jpg (square, at least 400 px). Until they exist the initial letter shows.
- Favicon: white serif S on a black rounded square (owner's choice, 2026-11-04; replaced the gold Ś). Files assets/seora-favicon-*.png, linked in layout/theme.liquid; source SVG and renderer in docs/favicon/ (option A).
