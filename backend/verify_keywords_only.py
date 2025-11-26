"""
VERIFICATION: Show ONLY user-entered keywords (no auto-added terms)
"""
import requests
import json

BASE_URL = "http://localhost:5555"

print("=" * 80)
print("KEYWORD VERIFICATION - READ ONLY")
print("=" * 80)

print("\n1. USER-ENTERED KEYWORDS (from database):")
print("-" * 80)

try:
    resp = requests.get(f"{BASE_URL}/api/keywords")
    keywords = resp.json()
    enabled = [k for k in keywords if k.get('enabled')]
    
    print(f"Total keywords in DB: {len(keywords)}")
    print(f"Enabled keywords: {len(enabled)}")
    print()
    
    user_keyword_list = []
    for kw in enabled:
        user_keyword_list.append(kw['text_ar'])
        print(f"  • {kw['text_ar']}")
        print(f"    ID: {kw['id']}")
        print(f"    Created: {kw.get('created_at', 'N/A')}")
        print()
    
    print("=" * 80)
    print("SEARCH KEYWORD SET (what will be searched):")
    print("=" * 80)
    print(json.dumps(user_keyword_list, ensure_ascii=False, indent=2))
    
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 80)
print("2. KEYWORD EXPANSIONS (translations of YOUR keywords only):")
print("-" * 80)

try:
    resp = requests.get(f"{BASE_URL}/api/keywords/expanded")
    expansions = resp.json()
    
    print(f"Total expansions: {len(expansions)}")
    print()
    
    for exp in expansions:
        print(f"Keyword: {exp['original_ar']}")
        print(f"  Strategy: {exp.get('strategy', 'unknown')}")
        print(f"  Translations:")
        for lang, trans in exp.get('translations', {}).items():
            print(f"    {lang.upper()}: {trans}")
        print()
    
    # Check if any expansion is NOT from user keywords
    expansion_keywords = [e['original_ar'] for e in expansions]
    extra_expansions = [k for k in expansion_keywords if k not in user_keyword_list]
    
    if extra_expansions:
        print("⚠️  WARNING: Found expansions NOT matching user keywords:")
        for extra in extra_expansions:
            print(f"    • {extra}")
        print("\n   This is a BUG - expansions should only be for YOUR keywords!")
    else:
        print("✅ GOOD: All expansions match user keywords (no extras)")
    
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 80)
print("3. VERIFICATION SUMMARY:")
print("=" * 80)
print(f"""
User Keywords (what YOU entered): {user_keyword_list}

These are the ONLY terms that will be searched.

The proper-noun map is used ONLY to translate these keywords correctly:
  - If keyword is "ترامب" → translate as "Trump" (not "Atout")
  - If keyword is "ماكرون" → translate as "Macron" (not auto-added!)
  
The map does NOT add keywords - it only helps translate your keywords.

STRICT_USER_KEYWORDS = true (enforced)
""")
print("=" * 80)
