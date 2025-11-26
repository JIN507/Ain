from models import SessionLocal, Source

db = SessionLocal()
sources = db.query(Source).filter(Source.country_name == 'روسيا').all()

print("="*80)
print("SOURCES FROM RUSSIA")
print("="*80)
for s in sources:
    print(f"• {s.name}")
    print(f"  URL: {s.url}")
    print(f"  Enabled: {s.enabled}")
    print()

db.close()
