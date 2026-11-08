# Price changes

## 2026-11-08: 40% sale on all products (owner request)

- `2026-11-08-before-40pct.csv`: every variant's price before the sale (exported twice independently and compared). No variant had a compare-at price.
- `2026-11-08-sale-40pct.jsonl`: bulk mutation variables (productVariantsBulkUpdate). New price = old price x 0.6 rounded to a whole shekel; compare-at = old price. The gift card (product 10308739465512) is excluded.
- `2026-11-08-revert.jsonl`: restores the old price and clears the compare-at price. Run it with the same bulk mutation to undo the sale.
- The automatic discount LOVE40 (40% at checkout) was deactivated at the same time so the two do not stack.
