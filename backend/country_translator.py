"""
Country name translator for bulk source import.

Goal: ensure that no matter what language/spelling the admin uploads,
the country lands in the DB under the EXACT canonical Arabic name that
already exists, so we never create duplicate Country rows.

Strategy:
  1. Curated dictionary (preferred) — ~200 countries with the most common
     aliases in EN/FR/ES/DE + Arabic variants. Manually verified to match
     the Arabic names already in the production DB.
  2. If input is already Arabic → run through _canonical_country() to
     merge spelling variants (e.g. 'الامارات' -> 'الإمارات').
  3. Google Translate fallback — only when the input is not Arabic AND
     not in the curated map. Result is then re-checked against the map.
  4. If everything fails, return the input as-is and flag in report.
"""

import re
import unicodedata
from typing import Tuple, Optional


# ──────────────────────────────────────────────────────────────────────
# Curated alias → canonical Arabic name dictionary
# ──────────────────────────────────────────────────────────────────────
# Keys are lowercase, accent-stripped, whitespace-collapsed.
# Values must EXACTLY match the canonical Arabic names already used in
# the production DB (verified against monitor_status output 2026-05-24).

_CURATED: dict = {
    # ─── Arab World ────────────────────────────────────────────────
    'saudi arabia': 'السعودية', 'saudi': 'السعودية', 'ksa': 'السعودية',
    'kingdom of saudi arabia': 'السعودية', 'arabie saoudite': 'السعودية',
    'arabia saudita': 'السعودية',
    'المملكة العربية السعودية': 'السعودية', 'المملكه العربيه السعوديه': 'السعودية',

    'uae': 'الإمارات', 'u.a.e.': 'الإمارات',
    'united arab emirates': 'الإمارات', 'emirates': 'الإمارات',
    'emirats arabes unis': 'الإمارات', 'emiratos arabes unidos': 'الإمارات',
    'الامارات': 'الإمارات', 'الامارات العربيه المتحده': 'الإمارات',
    'الإمارات العربية المتحدة': 'الإمارات',

    'egypt': 'مصر', 'arab republic of egypt': 'مصر', 'egypte': 'مصر', 'egipto': 'مصر',
    'qatar': 'قطر', 'state of qatar': 'قطر',
    'kuwait': 'الكويت', 'state of kuwait': 'الكويت', 'koweit': 'الكويت',
    'bahrain': 'البحرين', 'kingdom of bahrain': 'البحرين', 'bahrein': 'البحرين',
    'oman': 'عُمان', 'sultanate of oman': 'عُمان', 'عمان': 'عُمان',
    'yemen': 'اليمن',
    'iraq': 'العراق', 'irak': 'العراق',
    'syria': 'سوريا', 'syrian arab republic': 'سوريا', 'syrie': 'سوريا',
    'lebanon': 'لبنان', 'liban': 'لبنان', 'libano': 'لبنان',
    'jordan': 'الأردن', 'jordanie': 'الأردن', 'jordania': 'الأردن', 'الاردن': 'الأردن',
    'palestine': 'فلسطين', 'state of palestine': 'فلسطين', 'palestina': 'فلسطين',
    'morocco': 'المغرب', 'maroc': 'المغرب', 'marruecos': 'المغرب',
    'algeria': 'الجزائر', 'algerie': 'الجزائر', 'argelia': 'الجزائر',
    'tunisia': 'تونس', 'tunisie': 'تونس', 'tunez': 'تونس',
    'libya': 'ليبيا', 'libye': 'ليبيا',
    'sudan': 'السودان', 'soudan': 'السودان',
    'mauritania': 'موريتانيا', 'mauritanie': 'موريتانيا',
    'somalia': 'الصومال', 'somalie': 'الصومال',
    'djibouti': 'جيبوتي',
    'comoros': 'جزر القمر',

    # ─── Europe ────────────────────────────────────────────────────
    'uk': 'بريطانيا', 'u.k.': 'بريطانيا',
    'united kingdom': 'بريطانيا', 'great britain': 'بريطانيا',
    'britain': 'بريطانيا', 'england': 'بريطانيا',
    'royaume-uni': 'بريطانيا', 'royaume uni': 'بريطانيا',
    'reino unido': 'بريطانيا', 'inglaterra': 'بريطانيا',
    'المملكة المتحدة': 'بريطانيا', 'المملكه المتحده': 'بريطانيا',

    'france': 'فرنسا', 'francia': 'فرنسا', 'frankreich': 'فرنسا',
    'germany': 'ألمانيا', 'deutschland': 'ألمانيا', 'allemagne': 'ألمانيا', 'alemania': 'ألمانيا', 'المانيا': 'ألمانيا',
    'spain': 'إسبانيا', 'espagne': 'إسبانيا', 'espana': 'إسبانيا', 'españa': 'إسبانيا', 'اسبانيا': 'إسبانيا',
    'italy': 'إيطاليا', 'italie': 'إيطاليا', 'italia': 'إيطاليا', 'ايطاليا': 'إيطاليا',
    'portugal': 'البرتغال',
    'netherlands': 'هولندا', 'holland': 'هولندا', 'pays-bas': 'هولندا', 'paises bajos': 'هولندا',
    'belgium': 'بلجيكا', 'belgique': 'بلجيكا', 'belgica': 'بلجيكا', 'bélgica': 'بلجيكا',
    'switzerland': 'سويسرا', 'suisse': 'سويسرا', 'suiza': 'سويسرا',
    'austria': 'النمسا', 'autriche': 'النمسا',
    'sweden': 'السويد', 'suede': 'السويد', 'suède': 'السويد',
    'norway': 'النرويج', 'norvege': 'النرويج', 'norvège': 'النرويج', 'noruega': 'النرويج',
    'denmark': 'الدنمارك', 'danemark': 'الدنمارك', 'dinamarca': 'الدنمارك',
    'finland': 'فنلندا', 'finlande': 'فنلندا',
    'ireland': 'أيرلندا', 'irlande': 'أيرلندا', 'irlanda': 'أيرلندا',
    'iceland': 'آيسلندا', 'islande': 'آيسلندا',
    'greece': 'اليونان', 'grece': 'اليونان', 'grèce': 'اليونان', 'grecia': 'اليونان',
    'poland': 'بولندا', 'pologne': 'بولندا', 'polonia': 'بولندا',
    'czech republic': 'التشيك', 'czechia': 'التشيك', 'tchequie': 'التشيك',
    'slovakia': 'سلوفاكيا',
    'hungary': 'المجر', 'hongrie': 'المجر',
    'romania': 'رومانيا', 'roumanie': 'رومانيا',
    'bulgaria': 'بلغاريا', 'bulgarie': 'بلغاريا',
    'ukraine': 'أوكرانيا', 'ucrania': 'أوكرانيا',
    'russia': 'روسيا', 'russian federation': 'روسيا', 'russie': 'روسيا', 'rusia': 'روسيا',
    'belarus': 'بيلاروسيا', 'bielorussie': 'بيلاروسيا',
    'serbia': 'صربيا', 'serbie': 'صربيا',
    'croatia': 'كرواتيا', 'croatie': 'كرواتيا',
    'bosnia': 'البوسنة', 'bosnia and herzegovina': 'البوسنة',
    'albania': 'ألبانيا', 'albanie': 'ألبانيا',
    'kosovo': 'كوسوفو',
    'north macedonia': 'مقدونيا الشمالية', 'macedonia': 'مقدونيا الشمالية',
    'slovenia': 'سلوفينيا',
    'estonia': 'إستونيا',
    'latvia': 'لاتفيا',
    'lithuania': 'ليتوانيا',
    'moldova': 'مولدوفا',
    'cyprus': 'قبرص', 'chypre': 'قبرص', 'chipre': 'قبرص',
    'malta': 'مالطا',
    'luxembourg': 'لوكسمبورغ',

    # ─── Americas ──────────────────────────────────────────────────
    'usa': 'أمريكا', 'u.s.a.': 'أمريكا', 'us': 'أمريكا', 'u.s.': 'أمريكا',
    'united states': 'أمريكا', 'united states of america': 'أمريكا',
    'america': 'أمريكا', 'american': 'أمريكا',
    'etats-unis': 'أمريكا', 'états-unis': 'أمريكا',
    'estados unidos': 'أمريكا',
    'الولايات المتحدة': 'أمريكا', 'الولايات المتحدة الأمريكية': 'أمريكا',

    'canada': 'كندا',
    'mexico': 'المكسيك', 'mexique': 'المكسيك', 'méxico': 'المكسيك',
    'brazil': 'البرازيل', 'bresil': 'البرازيل', 'brésil': 'البرازيل', 'brasil': 'البرازيل',
    'argentina': 'الأرجنتين', 'argentine': 'الأرجنتين', 'الارجنتين': 'الأرجنتين',
    'chile': 'تشيلي', 'chili': 'تشيلي',
    'colombia': 'كولومبيا', 'colombie': 'كولومبيا',
    'peru': 'بيرو', 'pérou': 'بيرو', 'perou': 'بيرو', 'perú': 'بيرو',
    'venezuela': 'فنزويلا',
    'ecuador': 'الإكوادور', 'équateur': 'الإكوادور',
    'bolivia': 'بوليفيا', 'bolivie': 'بوليفيا',
    'paraguay': 'باراغواي',
    'uruguay': 'أوروغواي',
    'cuba': 'كوبا',
    'dominican republic': 'جمهورية الدومينيكان',
    'haiti': 'هايتي',
    'jamaica': 'جامايكا', 'jamaique': 'جامايكا',
    'panama': 'بنما', 'panamá': 'بنما',
    'costa rica': 'كوستاريكا',
    'guatemala': 'غواتيمالا',
    'honduras': 'هندوراس',
    'el salvador': 'السلفادور',
    'nicaragua': 'نيكاراغوا',
    'puerto rico': 'بورتوريكو',

    # ─── Asia ──────────────────────────────────────────────────────
    'china': 'الصين', 'chine': 'الصين', 'prc': 'الصين', "people's republic of china": 'الصين',
    'japan': 'اليابان', 'japon': 'اليابان', 'japón': 'اليابان',
    'south korea': 'كوريا الجنوبية', 'korea': 'كوريا الجنوبية',
    'republic of korea': 'كوريا الجنوبية',
    'coree du sud': 'كوريا الجنوبية', 'corée du sud': 'كوريا الجنوبية',
    'corea del sur': 'كوريا الجنوبية',
    'north korea': 'كوريا الشمالية', 'dprk': 'كوريا الشمالية',
    'india': 'الهند', 'inde': 'الهند',
    'pakistan': 'باكستان',
    'bangladesh': 'بنغلاديش',
    'sri lanka': 'سريلانكا',
    'nepal': 'نيبال', 'népal': 'نيبال',
    'afghanistan': 'أفغانستان', 'الافغانستان': 'أفغانستان',
    'iran': 'إيران', 'islamic republic of iran': 'إيران', 'iran (islamic republic of)': 'إيران', 'persia': 'إيران', 'الايران': 'إيران',
    'turkey': 'تركيا', 'turkiye': 'تركيا', 'türkiye': 'تركيا', 'turquie': 'تركيا', 'turquia': 'تركيا',
    'israel': 'إسرائيل', 'israël': 'إسرائيل',
    'indonesia': 'إندونيسيا', 'indonesie': 'إندونيسيا',
    'malaysia': 'ماليزيا', 'malaisie': 'ماليزيا', 'malasia': 'ماليزيا',
    'singapore': 'سنغافورة', 'singapour': 'سنغافورة', 'singapur': 'سنغافورة',
    'thailand': 'تايلاند', 'thailande': 'تايلاند', 'thaïlande': 'تايلاند', 'tailandia': 'تايلاند',
    'vietnam': 'فيتنام', 'viet nam': 'فيتنام',
    'philippines': 'الفلبين', 'filipinas': 'الفلبين',
    'myanmar': 'ميانمار', 'burma': 'ميانمار', 'birmanie': 'ميانمار',
    'cambodia': 'كمبوديا', 'cambodge': 'كمبوديا',
    'laos': 'لاوس',
    'brunei': 'بروناي',
    'mongolia': 'منغوليا', 'mongolie': 'منغوليا',
    'taiwan': 'تايوان',
    'hong kong': 'هونغ كونغ',
    'macau': 'ماكاو', 'macao': 'ماكاو',
    'kazakhstan': 'كازاخستان',
    'uzbekistan': 'أوزبكستان',
    'turkmenistan': 'تركمانستان',
    'kyrgyzstan': 'قيرغيزستان',
    'tajikistan': 'طاجيكستان',
    'azerbaijan': 'أذربيجان', 'azerbaidjan': 'أذربيجان',
    'armenia': 'أرمينيا', 'armenie': 'أرمينيا',
    'georgia': 'جورجيا', 'géorgie': 'جورجيا',
    'maldives': 'المالديف',
    'bhutan': 'بوتان',

    # ─── Africa ────────────────────────────────────────────────────
    'south africa': 'جنوب أفريقيا', 'afrique du sud': 'جنوب أفريقيا',
    'sudafrica': 'جنوب أفريقيا', 'sudáfrica': 'جنوب أفريقيا',
    'nigeria': 'نيجيريا',
    'kenya': 'كينيا',
    'ethiopia': 'إثيوبيا', 'ethiopie': 'إثيوبيا',
    'ghana': 'غانا',
    'tanzania': 'تنزانيا', 'tanzanie': 'تنزانيا',
    'uganda': 'أوغندا', 'ouganda': 'أوغندا',
    'rwanda': 'رواندا',
    'burundi': 'بوروندي',
    'senegal': 'السنغال', 'sénégal': 'السنغال',
    'ivory coast': 'ساحل العاج', "cote d'ivoire": 'ساحل العاج', "côte d'ivoire": 'ساحل العاج',
    'cameroon': 'الكاميرون', 'cameroun': 'الكاميرون',
    'angola': 'أنغولا',
    'mozambique': 'موزمبيق',
    'zimbabwe': 'زيمبابوي',
    'zambia': 'زامبيا', 'zambie': 'زامبيا',
    'botswana': 'بوتسوانا',
    'namibia': 'ناميبيا', 'namibie': 'ناميبيا',
    'madagascar': 'مدغشقر',
    'mauritius': 'موريشيوس', 'maurice': 'موريشيوس',
    'seychelles': 'سيشل',
    'mali': 'مالي',
    'burkina faso': 'بوركينا فاسو',
    'niger': 'النيجر',
    'chad': 'تشاد', 'tchad': 'تشاد',
    'central african republic': 'جمهورية أفريقيا الوسطى',
    'gabon': 'الغابون',
    'congo': 'الكونغو', 'republic of the congo': 'الكونغو',
    'democratic republic of the congo': 'جمهورية الكونغو الديمقراطية', 'drc': 'جمهورية الكونغو الديمقراطية',
    'guinea': 'غينيا', 'guinee': 'غينيا',
    'sierra leone': 'سيراليون',
    'liberia': 'ليبيريا',
    'togo': 'توغو',
    'benin': 'بنين', 'bénin': 'بنين',
    'eritrea': 'إريتريا',
    'south sudan': 'جنوب السودان',
    'cape verde': 'الرأس الأخضر',
    'gambia': 'غامبيا', 'gambie': 'غامبيا',
    'guinea-bissau': 'غينيا بيساو',
    'lesotho': 'ليسوتو',
    'swaziland': 'إسواتيني', 'eswatini': 'إسواتيني',
    'malawi': 'مالاوي',

    # ─── Oceania ───────────────────────────────────────────────────
    'australia': 'أستراليا', 'australie': 'أستراليا', 'الاسترالي': 'أستراليا', 'استراليا': 'أستراليا',
    'new zealand': 'نيوزيلندا', 'nouvelle-zelande': 'نيوزيلندا', 'nouvelle-zélande': 'نيوزيلندا',
    'fiji': 'فيجي', 'fidji': 'فيجي',
    'papua new guinea': 'بابوا غينيا الجديدة',
    'samoa': 'ساموا',
    'tonga': 'تونغا',
    'vanuatu': 'فانواتو',
    'solomon islands': 'جزر سليمان',

    # ─── International / generic ──────────────────────────────────
    'international': 'دولي', 'world': 'دولي', 'global': 'دولي',
    'worldwide': 'دولي', 'monde': 'دولي', 'mundo': 'دولي',
    'دولى': 'دولي', 'العالم': 'دولي',
}


def _norm_key(s: str) -> str:
    """Normalize alias key for lookup: lowercase, strip accents (Latin),
    collapse whitespace, remove dots, brackets."""
    if not s:
        return ''
    # NFD then drop combining marks (removes Latin accents like é -> e),
    # but preserve Arabic by skipping if input is Arabic.
    s = s.strip()
    # Detect if string contains Arabic; if so don't strip combining marks
    # because Arabic harakat are combining marks we want to remove via the
    # separate _arabic_normalize step.
    has_arabic = any('\u0600' <= ch <= '\u06FF' for ch in s)
    if not has_arabic:
        s = unicodedata.normalize('NFD', s)
        s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = s.lower()
    s = re.sub(r'[().\[\]]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def _is_arabic(s: str) -> bool:
    """True if the string contains at least one Arabic letter and no Latin letters."""
    if not s:
        return False
    has_arabic = any('\u0600' <= ch <= '\u06FF' for ch in s)
    has_latin = any('a' <= ch.lower() <= 'z' for ch in s)
    return has_arabic and not has_latin


# Build a normalized-key lookup table once at import time.
_CURATED_NORM = {_norm_key(k): v for k, v in _CURATED.items()}


def translate_country_to_arabic(
    name: str,
    canonicalizer=None,
    use_google_fallback: bool = True,
) -> Tuple[str, str]:
    """
    Translate (or pass through) a country name to its canonical Arabic form.

    Args:
        name: Raw country name from CSV (any language).
        canonicalizer: Optional callable that takes an Arabic name and
            returns its canonical variant (e.g. app._canonical_country).
        use_google_fallback: If True, attempt Google Translate when the
            input is not Arabic and not in the curated map.

    Returns:
        (arabic_name, source) where source is one of:
            'curated'   — found in curated dictionary
            'canonical' — already Arabic, mapped via canonicalizer
            'arabic'    — already Arabic, no mapping needed
            'google'    — translated via Google Translate
            'asis'      — could not translate; original returned (caller should warn)
    """
    if not name:
        return '', 'asis'

    raw = name.strip()

    # 1. Curated dictionary (covers all common aliases + Arabic variants)
    key = _norm_key(raw)
    if key in _CURATED_NORM:
        ar = _CURATED_NORM[key]
        if canonicalizer:
            ar = canonicalizer(ar) or ar
        return ar, 'curated'

    # 2. Already Arabic? Just canonicalize.
    if _is_arabic(raw):
        if canonicalizer:
            canon = canonicalizer(raw) or raw
            return canon, ('canonical' if canon != raw else 'arabic')
        return raw, 'arabic'

    # 3. Google Translate fallback
    if use_google_fallback:
        try:
            from deep_translator import GoogleTranslator
            translated = GoogleTranslator(source='auto', target='ar').translate(raw)
            if translated and translated.strip():
                translated = translated.strip()
                # Re-check curated map: GT might give us a name we know
                tkey = _norm_key(translated)
                if tkey in _CURATED_NORM:
                    ar = _CURATED_NORM[tkey]
                else:
                    ar = translated
                if canonicalizer:
                    ar = canonicalizer(ar) or ar
                return ar, 'google'
        except Exception as e:
            # Log but don't crash the whole import
            print(f"[country_translator] Google Translate failed for '{raw}': {str(e)[:120]}")

    # 4. Give up — return raw input, flagged
    return raw, 'asis'
