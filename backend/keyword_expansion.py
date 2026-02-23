"""
Keyword Expansion Service
Translates Arabic keywords to multiple languages using Google Translate

PHASE 2 UPDATE: Translations now stored in DATABASE (keywords.translations_json)
instead of RAM cache. This fixes the "No keyword expansions" error after restarts.
"""
import os
from datetime import datetime, timedelta
from deep_translator import GoogleTranslator
from arabic_utils import normalize_arabic
from proper_noun_rules import get_proper_noun_forms, is_known_proper_noun
import json

# Configuration from environment
# Expanded to cover ALL major languages from our sources (30+ languages)
TRANSLATE_TARGETS = os.getenv(
    'TRANSLATE_TARGETS', 
    'en,fr,es,de,ru,zh-cn,ja,hi,id,pt,tr,ar,ko,it,nl,pl,vi,th,uk,ro,el,cs,sv,hu,fi,da,no,sk,bg,hr,ms,fa,ur'
).split(',')
EXPANSION_TTL_DAYS = int(os.getenv('EXPANSION_TTL_DAYS', '365'))
TRANSLATION_TIMEOUT_S = int(os.getenv('TRANSLATION_TIMEOUT_S', '8'))



def expand_keyword(keyword_ar, keyword_obj=None, db=None):
    """
    Expand Arabic keyword to multiple languages and save to database.
    
    Args:
        keyword_ar: Arabic keyword to expand
        keyword_obj: Optional Keyword model object to save translations to
        db: Optional database session (required if keyword_obj provided)
        
    Returns:
        dict: {
            'original_ar': str,
            'normalized_ar': str,
            'translations': {'en': '...', 'ru': '...', ...},
            'updated_at': str (ISO8601),
            'status': 'success' | 'partial' | 'failed'
        }
    """
    print(f"   🔄 Expanding keyword: {keyword_ar}")
    
    # Normalize Arabic
    normalized_ar = normalize_arabic(keyword_ar)
    
    # Check if this is a known proper noun
    proper_noun_forms = get_proper_noun_forms(keyword_ar)
    is_proper_noun = proper_noun_forms is not None
    
    if is_proper_noun:
        print(f"   📌 Known proper noun - using curated translations")
    
    # Translate to target languages
    translations = {}
    failed_langs = []
    
    for target_lang in TRANSLATE_TARGETS:
        try:
            lang_code = target_lang.strip().lower()
            
            # Use proper noun form if available, otherwise use Google Translate
            if is_proper_noun and lang_code in proper_noun_forms:
                translations[lang_code] = proper_noun_forms[lang_code]
                print(f"      ✅ {lang_code.upper()}: {proper_noun_forms[lang_code]} (curated)")
            else:
                translated = GoogleTranslator(source='ar', target=lang_code).translate(keyword_ar)
                
                if translated:
                    translations[lang_code] = translated
                    print(f"      ✅ {lang_code.upper()}: {translated}")
                else:
                    failed_langs.append(lang_code)
                    print(f"      ❌ {lang_code.upper()}: No result")
                
        except Exception as e:
            failed_langs.append(target_lang)
            print(f"      ❌ {target_lang.upper()}: {str(e)[:50]}")
    
    # Determine status
    if len(translations) == len(TRANSLATE_TARGETS):
        status = 'success'
    elif len(translations) > 0:
        status = 'partial'
    else:
        status = 'failed'
    
    now = datetime.utcnow()
    
    # Create expansion result
    expansion = {
        'original_ar': keyword_ar,
        'normalized_ar': normalized_ar,
        'translations': translations,
        'updated_at': now.isoformat(),
        'status': status,
        'failed_langs': failed_langs if failed_langs else None
    }
    
    # Save to database if keyword object provided
    if keyword_obj and db:
        try:
            keyword_obj.translations_json = json.dumps(translations, ensure_ascii=False)
            keyword_obj.translations_updated_at = now
            # Also update legacy columns for backward compatibility
            keyword_obj.text_en = translations.get('en', '')[:200] if translations.get('en') else None
            keyword_obj.text_fr = translations.get('fr', '')[:200] if translations.get('fr') else None
            keyword_obj.text_es = translations.get('es', '')[:200] if translations.get('es') else None
            keyword_obj.text_ru = translations.get('ru', '')[:200] if translations.get('ru') else None
            keyword_obj.text_tr = translations.get('tr', '')[:200] if translations.get('tr') else None
            keyword_obj.text_zh = translations.get('zh-cn', '')[:200] if translations.get('zh-cn') else None
            keyword_obj.text_ur = translations.get('ur', '')[:200] if translations.get('ur') else None
            db.commit()
            print(f"   💾 Saved translations to database")
        except Exception as e:
            print(f"   ⚠️ Failed to save to database: {e}")
    
    print(f"   ✅ Expansion complete: {status} ({len(translations)}/{len(TRANSLATE_TARGETS)} languages)")
    
    return expansion


def get_expansion_from_db(keyword_obj):
    """
    Get expansion from database for a Keyword object.
    
    Args:
        keyword_obj: Keyword model object
        
    Returns:
        Expansion dict or None if not available
    """
    # Defensive: Check if column exists (handles pre-migration state)
    translations_json = getattr(keyword_obj, 'translations_json', None)
    translations_updated_at = getattr(keyword_obj, 'translations_updated_at', None)
    
    if not translations_json:
        return None
    
    # Check if translations are still valid (not expired)
    if translations_updated_at:
        try:
            age = datetime.utcnow() - translations_updated_at
            if age > timedelta(days=EXPANSION_TTL_DAYS):
                print(f"   ⏰ Translations expired for: {keyword_obj.text_ar}")
                return None
        except (TypeError, AttributeError):
            pass  # Handle edge cases with datetime comparison
    
    try:
        translations = json.loads(translations_json)
        return {
            'original_ar': keyword_obj.text_ar,
            'normalized_ar': normalize_arabic(keyword_obj.text_ar),
            'translations': translations,
            'updated_at': translations_updated_at.isoformat() if translations_updated_at else None,
            'status': 'success' if len(translations) >= 10 else 'partial'
        }
    except (json.JSONDecodeError, TypeError):
        return None


def get_all_expansions():
    """
    Get all expansions from database.
    
    Returns:
        list of expansion dicts
    """
    from models import get_db, Keyword
    
    db = get_db()
    try:
        keywords = db.query(Keyword).filter(
            Keyword.enabled == True,
            Keyword.translations_json.isnot(None)
        ).all()
        
        expansions = []
        for kw in keywords:
            expansion = get_expansion_from_db(kw)
            if expansion:
                expansions.append(expansion)
        
        return expansions
    finally:
        db.close()


def clear_expansion_cache():
    """Clear all keyword translations in database (use with caution)"""
    from models import get_db, Keyword
    
    db = get_db()
    try:
        db.query(Keyword).update({
            Keyword.translations_json: None,
            Keyword.translations_updated_at: None
        })
        db.commit()
        print("🧹 Cleared all keyword translations from database")
    finally:
        db.close()


def load_expansions_from_keywords(keywords, auto_refresh=True):
    """
    Load expansions from DATABASE for keywords.
    
    If auto_refresh=True and a keyword's translations are missing or expired,
    attempt to re-expand on the fly so monitoring is never silently broken.
    
    Args:
        keywords: List of Keyword objects with text_ar and translations_json fields
        auto_refresh: If True, auto-expand keywords with missing/expired translations
        
    Returns:
        List of expansions (skips keywords only if auto-refresh also fails)
    """
    expansions = []
    skipped = []
    refreshed = []
    
    for kw in keywords:
        # Load from DATABASE
        expansion = get_expansion_from_db(kw)
        
        if expansion:
            expansions.append(expansion)
        elif auto_refresh:
            # Auto-refresh: re-expand the keyword instead of silently dropping it
            print(f"🔄 Auto-refreshing expired/missing translations for: {kw.text_ar}")
            try:
                from models import get_db
                db = get_db()
                try:
                    # Re-fetch the keyword object in this session
                    from models import Keyword as KW
                    kw_fresh = db.query(KW).filter(KW.id == kw.id).first()
                    if kw_fresh:
                        new_expansion = expand_keyword(kw_fresh.text_ar, keyword_obj=kw_fresh, db=db)
                        if new_expansion and new_expansion.get('status') != 'failed':
                            expansions.append(new_expansion)
                            refreshed.append(kw.text_ar)
                            print(f"   ✅ Refreshed '{kw.text_ar}' successfully")
                        else:
                            skipped.append(kw.text_ar)
                            print(f"   ❌ Refresh failed for '{kw.text_ar}'")
                    else:
                        skipped.append(kw.text_ar)
                finally:
                    db.close()
            except Exception as e:
                skipped.append(kw.text_ar)
                print(f"   ❌ Auto-refresh error for '{kw.text_ar}': {str(e)[:80]}")
        else:
            skipped.append(kw.text_ar)
            print(f"⚠️  Keyword '{kw.text_ar}' has no translations (skipping)")
    
    if refreshed:
        print(f"\n🔄 Auto-refreshed {len(refreshed)} keywords: {', '.join(refreshed[:5])}")
    
    if skipped:
        print(f"\n⚠️  {len(skipped)} keywords skipped (no translations in database)")
        print(f"   Skipped: {', '.join(skipped[:5])}")
        if len(skipped) > 5:
            print(f"   ... and {len(skipped) - 5} more")
        print(f"   → To fix: Re-add these keywords via frontend to generate translations\n")
    
    return expansions


# Test function
if __name__ == "__main__":
    print("=" * 80)
    print("KEYWORD EXPANSION TEST")
    print("=" * 80)
    
    test_keywords = [
        "السعودية",
        "الرياض",
        "ترامب",
        "النفط"
    ]
    
    for keyword in test_keywords:
        print(f"\nExpanding: {keyword}")
        expansion = expand_keyword(keyword)
        print(json.dumps(expansion, ensure_ascii=False, indent=2))
        print("-" * 80)
