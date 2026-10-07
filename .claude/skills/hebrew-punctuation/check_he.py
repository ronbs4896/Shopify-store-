#!/usr/bin/env python3
"""Hebrew punctuation checker for SEORA copy (rules in SKILL.md).

Usage:
  check_he.py --text "כותרת. עוד קטע."            # free text, one item per line
  check_he.py --headings --text "..."              # every line is a heading
  check_he.py templates/product.seora.json ...     # theme JSON: headings detected by setting key
  check_he.py seo/blog/src/article.html            # HTML/Liquid: tags stripped, h1-h6 treated as headings

Exit code 1 if any ERROR was found.
"""
import argparse
import html
import json
import re
import sys

HEB = '֐-׿'
HEADING_KEYS = re.compile(
    r'(^|_)(heading|title|eyebrow|label|badge|subtitle|caption|cta|button|tag|trust_\d|item\d_title|highlight)(_|$|\d)',
    re.I)
SENTENCE_KEYS = re.compile(r'(text|answer|description|content|sub|note|paragraph|row_content)', re.I)

findings = []


def report(level, where, text, msg):
    findings.append((level, where, text, msg))


def strip_tags(s):
    s = re.sub(r'<br\s*/?>', '\n', s)
    s = re.sub(r'</(p|li|h[1-6]|div)>', '\n', s)
    s = re.sub(r'<[^>]+>', '', s)
    return html.unescape(s)


def check_line(line, where, heading=False):
    t = line.strip()
    if not t or not re.search(f'[{HEB}]', t):
        return
    if re.search(r'gradient\(|#[0-9a-fA-F]{3,6}\b|\d+px|https?://', t):
        return  # CSS values / URLs, not copy
    # spaces
    if re.search(r'\s+[.,:;?!)](?=\s|$)', t):
        report('ERROR', where, t, 'רווח לפני סימן פיסוק (הסימן נצמד למילה שלפניו)')
    if re.search(f'[,;:?!](?=[{HEB}A-Za-z])', t) or re.search(f'(?<=[{HEB}])\\.(?=[{HEB}])', t):
        report('ERROR', where, t, 'חסר רווח אחרי סימן פיסוק')
    if '  ' in t:
        report('WARN', where, t, 'שני רווחים רצופים')
    if re.search(r'\(\s|\s\)', t):
        report('ERROR', where, t, 'רווח בתוך סוגריים')
    # repeated marks
    if re.search(r'[!?]{2,}|\?!|!\?', t):
        report('ERROR', where, t, 'סימני קריאה/שאלה כפולים')
    # dashes
    if '—' in t:
        report('ERROR', where, t, 'קו ארוך (—) אסור בחנות: להחליף בפסיק או במשפט חדש')
    if re.search(r'\s[-–]\s', t):
        report('WARN', where, t, 'מקף/קו עם רווחים כמפריד: עדיף פסיק')
    # maqaf after prefix letter before digit/Latin
    if re.search(f'(?<![{HEB}\\w])[בהולמשכ](?=[0-9A-Za-z])', t):
        report('ERROR', where, t, 'חסר מקף בין אות שימוש לספרה/לועזית (ב-5, ה-GRA)')
    if re.search(f'(?<![{HEB}\\w])[בהולמשכ](-\\s|\\s-)(?=[0-9A-Za-z])', t):
        report('ERROR', where, t, 'רווח ליד המקף אחרי אות שימוש (ב-5 צמוד)')
    # gershayim / geresh
    if re.search(f'[{HEB}]"[{HEB}]', t):
        report('ERROR', where, t, 'ראשי תיבות במירכאות רגילות: להשתמש בגרשיים ״ (ש״ח, ס״מ)')
    if re.search(f"[{HEB}]'", t):
        report('ERROR', where, t, "אפוסטרוף אחרי אות עברית: להשתמש בגרש ׳ (וכו׳, ג׳ינס)")
    # currency / percent
    if re.search(r'\d\s+%', t):
        report('ERROR', where, t, 'רווח לפני % (20%)')
    if re.search(r'\d₪', t):
        report('WARN', where, t, 'מחיר: מומלץ "299 ₪" עם רווח')
    # fragment chains: 2+ ". " splits where pieces are short
    parts = [p for p in re.split(r'(?<=\.)\s+', t) if p]
    if len(parts) >= 2:
        short = [p for p in parts if len(p.split()) <= 5]
        if len(short) >= 2 and len(short) >= len(parts) - 1:
            report('ERROR' if heading else 'WARN', where, t,
                   'שרשרת קטעים קצרים עם נקודות (סגנון קופי אנגלי): לחבר בפסיק או לנסח משפט אחד')
    # headings
    if heading:
        if re.search(r'[.;:,]$', t):
            report('ERROR', where, t, 'אין סימן פיסוק בסוף כותרת/כפתור/תגית')
        elif re.search(r'\.\s', t):
            report('WARN', where, t, 'נקודה באמצע כותרת: לשקול פסיק או פיצול לכותרת + שורת משנה')
        if t.endswith('!'):
            report('WARN', where, t, 'סימן קריאה בכותרת: בטון יוקרתי עדיף בלי')


def walk_json(obj, path, filename):
    if isinstance(obj, dict):
        for k, v in obj.items():
            walk_json(v, path + [str(k)], filename)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            walk_json(v, path + [str(i)], filename)
    elif isinstance(obj, str) and re.search(f'[{HEB}]', obj):
        key = path[-1] if path else ''
        where = f'{filename}:{".".join(path[-4:])}'
        is_heading = bool(HEADING_KEYS.search(key)) and not SENTENCE_KEYS.search(key) and '<p>' not in obj
        for line in strip_tags(obj).split('\n'):
            check_line(line, where, heading=is_heading)


def _schema_text(block):
    # keep only Hebrew string values from the schema JSON, one per line
    return '\n'.join(re.findall(r'"default"\s*:\s*"([^"]*[\u0590-\u05FF][^"]*)"', block))


def check_file(fn, headings):
    raw = open(fn, encoding='utf-8').read()
    if fn.endswith('.json'):
        body = raw[raw.index('*/') + 2:] if raw.lstrip().startswith('/*') else raw
        walk_json(json.loads(body), [], fn)
        return
    # html / liquid / md / txt
    raw = re.sub(r'{%-?\s*schema\s*-?%}.*?{%-?\s*endschema\s*-?%}', lambda m: _schema_text(m.group(0)), raw, flags=re.S)
    for m in re.finditer(r'<h[1-6][^>]*>(.*?)</h[1-6]>', raw, re.S):
        check_line(strip_tags(re.sub(r'{%.*?%}|{{.*?}}', ' ', m.group(1), flags=re.S)), f'{fn}:<h>', heading=True)
    text = re.sub(r'<h[1-6][^>]*>.*?</h[1-6]>', '\n', raw, flags=re.S)
    text = re.sub(r'{%.*?%}|{{.*?}}', ' ', text, flags=re.S)
    for i, line in enumerate(strip_tags(text).split('\n'), 1):
        check_line(line, f'{fn}:{i}', heading=headings)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='*')
    ap.add_argument('--text')
    ap.add_argument('--headings', action='store_true', help='treat every line as a heading/button/label')
    a = ap.parse_args()
    if a.text:
        for i, line in enumerate(a.text.split('\n'), 1):
            check_line(line, f'text:{i}', heading=a.headings)
    for fn in a.files:
        check_file(fn, a.headings)
    errors = 0
    for level, where, text, msg in findings:
        errors += level == 'ERROR'
        print(f'{level:5} {where}\n      {text[:140]}\n      → {msg}')
    print(f'\n{errors} errors, {len(findings) - errors} warnings')
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
