"""
Bulk CSV import for RSS sources.

CSV format expected (3 columns, header optional):
    country_name, source_url, source_name

Robustness:
  - UTF-8 with or without BOM
  - Auto-detect delimiter: comma, semicolon, or tab
  - Header row auto-detected (if the second column of row 0 contains 'http'
    we assume NO header)
  - Country name in any language -> translated via country_translator
  - URL uniqueness enforced both at row level (within file) and DB level
  - Per-row outcome reporting

Per-row outcome codes (in order of preference):
    'added'                       — new source successfully created
    'country_created'             — added + had to create the country first
                                    (carries country translation info too)
    'skipped_duplicate_url'       — URL already exists in DB
    'skipped_duplicate_in_file'   — URL appears twice in this CSV
    'invalid_row'                 — missing columns / bad URL / empty fields
    'error'                       — unexpected DB/IO error during save

Each successful row also reports its translation source ('curated' /
'canonical' / 'arabic' / 'google' / 'asis').
"""

import csv
import io
import re
from typing import Callable, Dict, List, Optional, Tuple

from country_translator import translate_country_to_arabic
# Country and Source models are imported lazily inside import_rows() so this
# module can be imported (and the parser tested) without SQLAlchemy installed.


# ──────────────────────────────────────────────────────────────────────
# CSV parsing
# ──────────────────────────────────────────────────────────────────────

_URL_RE = re.compile(r'^https?://[^\s]+$', re.IGNORECASE)


def _decode_bytes(data: bytes) -> str:
    """Decode CSV bytes, handling BOM and common encodings."""
    # UTF-8 with BOM
    if data.startswith(b'\xef\xbb\xbf'):
        return data[3:].decode('utf-8', errors='replace')
    # Try UTF-8 first, fall back to cp1256 (Windows Arabic) then latin-1
    for enc in ('utf-8', 'cp1256', 'latin-1'):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode('utf-8', errors='replace')


def _sniff_dialect(sample: str) -> csv.Dialect:
    """Detect delimiter. Falls back to comma."""
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=',;\t')
        return dialect
    except csv.Error:
        class _D(csv.Dialect):
            delimiter = ','
            quotechar = '"'
            doublequote = True
            skipinitialspace = True
            lineterminator = '\n'
            quoting = csv.QUOTE_MINIMAL
        return _D()


def _looks_like_header(row: List[str]) -> bool:
    """A row is a header if NO cell contains an http:// URL."""
    if not row or len(row) < 2:
        return False
    joined = ' '.join(row).lower()
    return 'http' not in joined


def parse_csv_rows(file_bytes: bytes) -> Tuple[List[Dict], List[Dict]]:
    """
    Parse CSV file bytes into rows.

    Returns:
        (valid_rows, invalid_rows) where each row is a dict:
            valid:   {row_num, country_raw, url, name}
            invalid: {row_num, raw, reason}
    """
    text = _decode_bytes(file_bytes)
    if not text.strip():
        return [], [{'row_num': 0, 'raw': '', 'reason': 'الملف فارغ'}]

    sample = text[:4096]
    dialect = _sniff_dialect(sample)

    reader = csv.reader(io.StringIO(text), dialect)
    valid: List[Dict] = []
    invalid: List[Dict] = []

    rows = list(reader)
    if not rows:
        return [], [{'row_num': 0, 'raw': '', 'reason': 'الملف فارغ'}]

    start_idx = 1 if _looks_like_header(rows[0]) else 0

    for i, row in enumerate(rows[start_idx:], start=start_idx + 1):
        # Skip completely empty lines
        if not row or all(not (c or '').strip() for c in row):
            continue

        # Strip every cell; tolerate trailing extra columns
        cells = [(c or '').strip() for c in row]
        if len(cells) < 3:
            invalid.append({
                'row_num': i,
                'raw': ','.join(cells),
                'reason': f'يحتاج 3 أعمدة، وُجد {len(cells)}'
            })
            continue

        country_raw = cells[0]
        url = cells[1]
        name = cells[2]

        # Basic validation
        if not country_raw:
            invalid.append({'row_num': i, 'raw': ','.join(cells[:3]),
                            'reason': 'اسم الدولة مفقود'})
            continue
        if not url:
            invalid.append({'row_num': i, 'raw': ','.join(cells[:3]),
                            'reason': 'الرابط مفقود'})
            continue
        if not _URL_RE.match(url):
            invalid.append({'row_num': i, 'raw': ','.join(cells[:3]),
                            'reason': 'الرابط يجب أن يبدأ بـ http(s)://'})
            continue
        if not name:
            invalid.append({'row_num': i, 'raw': ','.join(cells[:3]),
                            'reason': 'اسم المصدر مفقود'})
            continue

        valid.append({
            'row_num': i,
            'country_raw': country_raw,
            'url': url,
            'name': name,
        })

    return valid, invalid


# ──────────────────────────────────────────────────────────────────────
# Import processor
# ──────────────────────────────────────────────────────────────────────

def _normalize_url_for_dedup(url: str) -> str:
    """Trim trailing slash, lowercase scheme+host. Keep path/query as-is."""
    if not url:
        return url
    u = url.strip()
    # Lowercase only the protocol + host portion
    m = re.match(r'^(https?://)([^/]+)(.*)$', u, re.IGNORECASE)
    if m:
        proto, host, rest = m.groups()
        u = proto.lower() + host.lower() + rest
    if u.endswith('/'):
        u = u[:-1]
    return u


def import_rows(
    db,
    rows: List[Dict],
    canonicalizer: Optional[Callable[[str], str]] = None,
    admin_user_id: Optional[int] = None,
    default_enabled: bool = True,
) -> Dict:
    """
    Process parsed rows and commit to DB.

    Args:
        db: SQLAlchemy session
        rows: list of dicts from parse_csv_rows
        canonicalizer: optional fn(arabic_name) -> canonical_arabic_name
                       (pass app._canonical_country)
        admin_user_id: user id to attribute new Country rows to (None = global)
        default_enabled: whether new sources start enabled

    Returns:
        {
            'summary': {
                'total': int, 'added': int, 'skipped_duplicate_url': int,
                'skipped_duplicate_in_file': int, 'countries_created': int,
                'invalid_row': int, 'error': int
            },
            'details': [ {row_num, country_raw, country_ar, url, name,
                          outcome, translation_source, message} ]
        }
    """
    # Lazy import so this module can be imported without sqlalchemy installed
    from models import Country, Source

    details: List[Dict] = []
    summary = {
        'total': len(rows),
        'added': 0,
        'skipped_duplicate_url': 0,
        'skipped_duplicate_in_file': 0,
        'countries_created': 0,
        'invalid_row': 0,
        'error': 0,
    }

    # Pre-load existing sources (by normalized URL) for fast dedup
    existing_sources = db.query(Source).all()
    existing_url_map: Dict[str, Source] = {
        _normalize_url_for_dedup(s.url): s for s in existing_sources
    }

    # Pre-load existing countries (by canonical Arabic name)
    existing_countries = db.query(Country).all()
    country_by_name: Dict[str, Country] = {}
    for c in existing_countries:
        canon = canonicalizer(c.name_ar) if canonicalizer else c.name_ar
        country_by_name.setdefault(canon, c)

    # Track URLs added in THIS import to catch in-file duplicates
    seen_in_file: set = set()

    for row in rows:
        row_num = row['row_num']
        country_raw = row['country_raw']
        url = row['url']
        name = row['name']

        try:
            # ── 1. Translate country name ──────────────────────────
            country_ar, src = translate_country_to_arabic(
                country_raw, canonicalizer=canonicalizer
            )
            if not country_ar:
                details.append({
                    'row_num': row_num,
                    'country_raw': country_raw,
                    'country_ar': '',
                    'url': url,
                    'name': name,
                    'outcome': 'invalid_row',
                    'translation_source': src,
                    'message': 'تعذّر تحويل اسم الدولة',
                })
                summary['invalid_row'] += 1
                continue

            # ── 2. URL dedup (in-file) ─────────────────────────────
            norm_url = _normalize_url_for_dedup(url)
            if norm_url in seen_in_file:
                details.append({
                    'row_num': row_num,
                    'country_raw': country_raw,
                    'country_ar': country_ar,
                    'url': url,
                    'name': name,
                    'outcome': 'skipped_duplicate_in_file',
                    'translation_source': src,
                    'message': 'الرابط مكرر داخل الملف',
                })
                summary['skipped_duplicate_in_file'] += 1
                continue
            seen_in_file.add(norm_url)

            # ── 3. URL dedup (DB) ─────────────────────────────────
            if norm_url in existing_url_map:
                existing = existing_url_map[norm_url]
                msg = 'الرابط موجود مسبقاً'
                if existing.country_name != country_ar:
                    msg += f" (تحت دولة أخرى: {existing.country_name})"
                details.append({
                    'row_num': row_num,
                    'country_raw': country_raw,
                    'country_ar': country_ar,
                    'url': url,
                    'name': name,
                    'outcome': 'skipped_duplicate_url',
                    'translation_source': src,
                    'message': msg,
                })
                summary['skipped_duplicate_url'] += 1
                continue

            # ── 4. Find or create country ─────────────────────────
            country = country_by_name.get(country_ar)
            country_was_created = False
            if not country:
                country = Country(
                    user_id=admin_user_id,
                    name_ar=country_ar,
                    enabled=True,
                )
                db.add(country)
                db.flush()  # need country.id before creating Source
                country_by_name[country_ar] = country
                country_was_created = True
                summary['countries_created'] += 1

            # ── 5. Create source ──────────────────────────────────
            source = Source(
                country_id=country.id,
                country_name=country_ar,
                name=name,
                url=url,  # store original URL, not the normalized one
                enabled=default_enabled,
            )
            db.add(source)
            db.commit()
            existing_url_map[norm_url] = source
            summary['added'] += 1

            details.append({
                'row_num': row_num,
                'country_raw': country_raw,
                'country_ar': country_ar,
                'url': url,
                'name': name,
                'outcome': 'added',
                'translation_source': src,
                'message': ('تمت إضافة المصدر' + (' وإنشاء الدولة'
                                                  if country_was_created else '')),
            })

        except Exception as e:
            db.rollback()
            summary['error'] += 1
            details.append({
                'row_num': row_num,
                'country_raw': country_raw,
                'country_ar': '',
                'url': url,
                'name': name,
                'outcome': 'error',
                'translation_source': 'asis',
                'message': str(e)[:200],
            })

    return {'summary': summary, 'details': details}
