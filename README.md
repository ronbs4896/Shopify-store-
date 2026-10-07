# ŚEORA – Shopify theme customizations

Custom theme files for the **ŚEORA** store (seora.co.il), built on top of the
"אתר רון" theme (Dawn based).

| File | Purpose |
| --- | --- |
| `sections/moissanite-compare.liquid` | "השוואת מואסנייט" section: moissanite vs. natural diamond comparison card with gold heading, price badges and CTA bar. Fully editable in the theme editor (texts, images, colors, rows). |
| `templates/product.json` | Product template with the comparison section placed right after the main product section. |
| `seo/` | Blog "המגזין של SEORA" (`/blogs/magazine`) and SEO work: the five published articles, the script that builds and link-checks them, the GA4 / Search Console setup guide and open SEO findings. Not part of the theme. See `seo/README.md`. |

## Deploying

The files are uploaded to an unpublished copy of the live theme via the
Shopify Admin API. Preview it from **Online Store → Themes**, then **Publish**
when ready.
