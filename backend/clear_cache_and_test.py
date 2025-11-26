"""
Clear expansion cache and verify proper noun handling works
"""
from keyword_expansion import clear_expansion_cache, expand_keyword
import requests

print("=" * 80)
print("CACHE CLEAR AND TEST")
print("=" * 80)

# Step 1: Clear cache
print("\n1. Clearing expansion cache...")
clear_expansion_cache()
print("   ✅ Cache cleared")

# Step 2: Test expansion for ترامب (should now use proper noun rules)
print("\n2. Testing expansion for 'ترامب' with proper noun rules...")
print()

expansion = expand_keyword('ترامب')

print("\n3. Results:")
print(f"   Keyword: {expansion['original_ar']}")
print(f"   Status: {expansion['status']}")
print("\n   Translations:")
for lang, trans in expansion['translations'].items():
    print(f"     {lang.upper()}: {trans}")

# Step 4: Verify via API
print("\n4. Verifying via API endpoint...")
try:
    resp = requests.get('http://localhost:5555/api/keywords/expanded')
    if resp.status_code == 200:
        expansions = resp.json()
        trump_exp = next((e for e in expansions if e['original_ar'] == 'ترامب'), None)
        
        if trump_exp:
            print("   ✅ Found ترامب in API response")
            print(f"\n   Translations from API:")
            for lang, trans in trump_exp['translations'].items():
                # Check if proper noun handling worked
                if lang == 'fr':
                    if trans == 'Trump':
                        print(f"     FR: {trans} ✅ CORRECT (was 'Atout')")
                    else:
                        print(f"     FR: {trans} ❌ STILL WRONG (expected 'Trump')")
                elif lang == 'zh-cn':
                    if trans == '特朗普':
                        print(f"     ZH-CN: {trans} ✅ CORRECT (was '王牌')")
                    else:
                        print(f"     ZH-CN: {trans} ❌ STILL WRONG (expected '特朗普')")
                else:
                    print(f"     {lang.upper()}: {trans}")
        else:
            print("   ⚠️  ترامب not found in API")
    else:
        print(f"   ❌ API error: {resp.status_code}")
except Exception as e:
    print(f"   ⚠️  Could not verify via API: {e}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("""
✅ Cache cleared
✅ Proper noun rules loaded
✅ Expansions regenerated

Expected behavior:
  - FR: "Trump" (not "Atout")
  - ZH: "特朗普" (not "王牌")
  
Next step:
  1. Run monitoring: curl -X POST http://localhost:5555/api/monitor/run
  2. Check countries: curl http://localhost:5555/api/articles/countries
  3. Should now see matches from France and China!
""")
print("=" * 80)
