"""
Check Egypt sources in database to find duplicate/wrong entries
"""
from models import init_db, get_db, Source

# Initialize DB
init_db()
db = get_db()

# Get all Egypt sources
egypt_sources = db.query(Source).filter(Source.country_name == "مصر").all()

print("="*80)
print("EGYPT SOURCES IN DATABASE")
print("="*80)
print(f"Total sources: {len(egypt_sources)}\n")

for source in egypt_sources:
    print(f"ID: {source.id}")
    print(f"Name: {source.name}")
    print(f"Country: {source.country_name}")
    print(f"URL: {source.url}")
    print(f"Enabled: {source.enabled}")
    print("-" * 40)

print("\n")
print("="*80)
print("CHECKING FOR DUPLICATES")
print("="*80)

# Check for sources that appear in multiple countries
all_sources = db.query(Source).all()
name_countries = {}

for source in all_sources:
    if source.name not in name_countries:
        name_countries[source.name] = []
    name_countries[source.name].append(source.country_name)

# Find duplicates
duplicates = {name: countries for name, countries in name_countries.items() if len(countries) > 1}

if duplicates:
    print(f"\n⚠️  Found {len(duplicates)} sources appearing in multiple countries:\n")
    for name, countries in duplicates.items():
        print(f"📰 {name}")
        print(f"   Countries: {', '.join(set(countries))}")
        print()
else:
    print("✅ No duplicates found!")

# Look for suspicious sources in Egypt
print("\n")
print("="*80)
print("SUSPICIOUS SOURCES IN EGYPT")
print("="*80)

us_keywords = ['washington', 'wall street', 'forbes', 'nbc', 'fox', 'cnn', 'npr', 'abc', 'intercept', 'politico', 'bloomberg', 'cnbc']

suspicious = []
for source in egypt_sources:
    name_lower = source.name.lower()
    if any(keyword in name_lower for keyword in us_keywords):
        suspicious.append(source)

if suspicious:
    print(f"\n⚠️  Found {len(suspicious)} suspicious sources:\n")
    for source in suspicious:
        print(f"ID: {source.id}")
        print(f"Name: {source.name}")
        print(f"URL: {source.url}")
        print()
else:
    print("✅ No suspicious sources found!")
