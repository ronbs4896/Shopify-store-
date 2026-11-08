"""Compare the two independent exports, then build the 40% sale and revert files.
New price = round(old price * 0.6) to a whole shekel; compare-at = old price."""
import csv, json, sys
from decimal import Decimal, ROUND_HALF_UP
D = sys.argv[1]
EXCLUDE = {'10308739465512'}  # gift card: never discounted
def load(name):
    with open(f'{D}/{name}', encoding='utf-8') as f:
        return {r['variant_id']: r for r in csv.DictReader(f)}
a, b = load('A.csv'), load('B.csv')
assert set(a) == set(b), ('variant sets differ', len(set(a) ^ set(b)))
diff = [k for k in a if a[k] != b[k]]
assert not diff, ('rows differ', diff[:10])
rows = list(a.values())
by_product = {}
revert = {}
skipped = []
for r in rows:
    price = Decimal(r['price'])
    if r['product_id'] in EXCLUDE or price <= 0:
        skipped.append(r['variant_id']); continue
    new = (price * Decimal('0.6')).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    by_product.setdefault(r['product_id'], []).append({
        'id': f"gid://shopify/ProductVariant/{r['variant_id']}",
        'price': f'{new:.2f}', 'compareAtPrice': f'{price:.2f}'})
    revert.setdefault(r['product_id'], []).append({
        'id': f"gid://shopify/ProductVariant/{r['variant_id']}",
        'price': f'{price:.2f}', 'compareAtPrice': (r['compare_at_price'] or None)})
def write(name, data):
    with open(f'{D}/{name}', 'w', encoding='utf-8') as f:
        for pid, vs in data.items():
            f.write(json.dumps({'productId': f'gid://shopify/Product/{pid}', 'variants': vs}, ensure_ascii=False) + '\n')
write('sale.jsonl', by_product); write('revert.jsonl', revert)
print('variants', len(rows), 'products', len(by_product), 'skipped (gift card / price 0):', len(skipped),
      'had compare before:', sum(1 for r in rows if r['compare_at_price']))
