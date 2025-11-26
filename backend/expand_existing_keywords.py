"""
Pre-expand all existing keywords to 32 languages
Run this ONCE after updating the system to populate the cache
"""
from models import init_db, get_db, Keyword
from keyword_expansion import expand_keyword

# Initialize DB
init_db()
db = get_db()

print("="*80)
print("KEYWORD EXPANSION - One-Time Setup")
print("="*80)
print("\nThis will expand all existing keywords to 32 languages.")
print("This only needs to be run once.\n")

# Get all keywords
keywords = db.query(Keyword).all()

if not keywords:
    print("❌ No keywords found in database!")
    print("   → Add keywords via frontend first")
    db.close()
    exit(0)

print(f"Found {len(keywords)} keywords to expand\n")

success_count = 0
partial_count = 0
failed_count = 0

for i, kw in enumerate(keywords, 1):
    keyword_ar = kw.text_ar
    
    print(f"[{i}/{len(keywords)}] Expanding: {keyword_ar}")
    
    try:
        # Expand to 32 languages
        expansion = expand_keyword(keyword_ar)
        
        if expansion['status'] == 'success':
            print(f"   ✅ Success - {len(expansion['translations'])} languages")
            success_count += 1
        elif expansion['status'] == 'partial':
            print(f"   ⚠️  Partial - {len(expansion['translations'])} languages")
            partial_count += 1
        else:
            print(f"   ❌ Failed")
            failed_count += 1
    except Exception as e:
        print(f"   ❌ Error: {str(e)[:50]}")
        failed_count += 1
    
    print()

print("="*80)
print("SUMMARY")
print("="*80)
print(f"""
✅ Success: {success_count} keywords
⚠️  Partial: {partial_count} keywords
❌ Failed: {failed_count} keywords

Total processed: {len(keywords)}

{f"✅ All keywords expanded successfully!" if success_count == len(keywords) else ""}
{f"⚠️  Some keywords partially expanded - check logs above" if partial_count > 0 else ""}
{f"❌ Some keywords failed - check logs above" if failed_count > 0 else ""}

Next steps:
1. Restart backend: python app.py
2. Run monitoring - should be INSTANT (no translation during runtime!)
3. Monitoring will use cached expansions only
""")

db.close()
