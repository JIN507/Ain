import requests
import json

print("=" * 80)
print("CHECKING BACKEND API ENDPOINTS")
print("=" * 80)

# Test /api/articles/countries
print("\n1) GET /api/articles/countries")
print("-" * 80)
try:
    r = requests.get('http://localhost:5555/api/articles/countries')
    if r.status_code == 200:
        data = r.json()
        print(f"✅ Status: {r.status_code}")
        print(f"✅ Total countries: {len(data)}")
        print(f"✅ First 10 countries:")
        for i, country in enumerate(data[:10]):
            print(f"   {i+1}. {country}")
    else:
        print(f"❌ Status: {r.status_code}")
        print(f"❌ Response: {r.text}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test /api/articles
print("\n2) GET /api/articles")
print("-" * 80)
try:
    r = requests.get('http://localhost:5555/api/articles')
    if r.status_code == 200:
        data = r.json()
        print(f"✅ Status: {r.status_code}")
        print(f"✅ Total articles: {len(data)}")
        
        # Extract distinct countries
        countries = set()
        first_5_countries = []
        for i, article in enumerate(data):
            country = article.get('country')
            if country:
                countries.add(country)
            if i < 5:
                first_5_countries.append({
                    'id': article.get('id'),
                    'country': country,
                    'title': article.get('title_ar', '')[:50]
                })
        
        print(f"✅ Distinct countries in articles: {len(countries)}")
        print(f"✅ Countries: {sorted(countries)}")
        print(f"\n✅ First 5 articles:")
        for article in first_5_countries:
            print(f"   ID: {article['id']}, Country: {article['country']}, Title: {article['title']}...")
    else:
        print(f"❌ Status: {r.status_code}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test /api/countries (old endpoint)
print("\n3) GET /api/countries (legacy)")
print("-" * 80)
try:
    r = requests.get('http://localhost:5555/api/countries')
    if r.status_code == 200:
        data = r.json()
        print(f"✅ Status: {r.status_code}")
        print(f"✅ Total countries in Country table: {len(data)}")
        for country in data[:5]:
            print(f"   - {country.get('name_ar')} (enabled: {country.get('enabled')})")
    else:
        print(f"❌ Status: {r.status_code}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 80)
