"""Check an after-export (CSV, same columns as A.csv) against the sale plan."""
import csv, json, sys
D = sys.argv[1]; after = sys.argv[2]
plan = {}
for l in open(f'{D}/sale.jsonl', encoding='utf-8'):
    for v in json.loads(l)['variants']:
        plan[v['id'].rsplit('/', 1)[1]] = (v['price'], v['compareAtPrice'])
before = {r['variant_id']: r for r in csv.DictReader(open(f'{D}/A.csv', encoding='utf-8'))}
rows = {r['variant_id']: r for r in csv.DictReader(open(after, encoding='utf-8'))}
bad = []
for vid, r in rows.items():
    if vid in plan:
        if (r['price'], r['compare_at_price']) != plan[vid]:
            bad.append((vid, r['price'], r['compare_at_price'], plan[vid]))
    else:  # gift card: must be unchanged
        b = before[vid]
        if (r['price'], r['compare_at_price']) != (b['price'], b['compare_at_price']):
            bad.append((vid, 'excluded changed', r['price'], r['compare_at_price']))
missing = set(plan) - set(rows)
print('rows', len(rows), 'planned', len(plan), 'mismatches', len(bad), 'missing', len(missing))
for x in bad[:30]: print(x)
