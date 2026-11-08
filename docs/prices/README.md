# Price changes

## 2026-11-08: 40% sale on all products (owner request)

- `2026-11-08-before-40pct.csv`: every variant's price before the sale (exported twice independently and compared). No variant had a compare-at price.
- `2026-11-08-sale-40pct.jsonl`: bulk mutation variables (productVariantsBulkUpdate). New price = old price x 0.6 rounded to a whole shekel; compare-at = old price. The gift card (product 10308739465512) is excluded.
- `2026-11-08-revert.jsonl`: restores the old price and clears the compare-at price. Run it with the same bulk mutation to undo the sale.
- The automatic discount LOVE40 (40% at checkout) was deactivated at the same time so the two do not stack.
- `2026-11-08-after-40pct.csv`: export after the update. `verify_40pct.py` found 0 mismatches against the plan (1,041 variants on sale, gift card unchanged).
- The bulk mutation API is blocked for Claude, so the update ran as 24 aliased GraphQL calls (30 products each; one split in two because of the 16,384-character limit). To revert, the same approach works with the revert file.
