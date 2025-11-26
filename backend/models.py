"""Database models for Ain News Monitor"""
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from flask_login import UserMixin

Base = declarative_base()


class User(UserMixin, Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default='USER')  # ADMIN, USER
    is_active = Column(Boolean, default=True)
    must_change_password = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class Country(Base):
    __tablename__ = 'countries'
    
    id = Column(Integer, primary_key=True)
    # Owner (null for legacy/global keywords; backfill to admin)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    name_ar = Column(String(100), nullable=False)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Source(Base):
    __tablename__ = 'sources'
    
    id = Column(Integer, primary_key=True)
    country_id = Column(Integer, nullable=False)
    country_name = Column(String(100), nullable=False)
    name = Column(String(200), nullable=False)
    url = Column(String(500), nullable=False, unique=True)
    enabled = Column(Boolean, default=True)
    last_checked = Column(DateTime, nullable=True)
    fail_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Keyword(Base):
    __tablename__ = 'keywords'
    
    id = Column(Integer, primary_key=True)
    # Owner (null for legacy/global; backfill to admin)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    text_ar = Column(String(200), nullable=False)
    
    # Translations in different languages
    text_en = Column(String(200), nullable=True)  # English
    text_fr = Column(String(200), nullable=True)  # French
    text_tr = Column(String(200), nullable=True)  # Turkish
    text_ur = Column(String(200), nullable=True)  # Urdu
    text_zh = Column(String(200), nullable=True)  # Chinese
    text_ru = Column(String(200), nullable=True)  # Russian
    text_es = Column(String(200), nullable=True)  # Spanish
    
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Article(Base):
    __tablename__ = 'articles'
    
    id = Column(Integer, primary_key=True)
    
    # Source info
    country = Column(String(100), nullable=False)
    source_name = Column(String(200), nullable=False)
    url = Column(String(500), nullable=False, unique=True)
    
    # Original content
    title_original = Column(Text, nullable=False)
    summary_original = Column(Text, nullable=True)
    original_language = Column(String(10), nullable=True)  # Detected language (en, ar, fr, etc.)
    image_url = Column(String(1000), nullable=True)  # Article image/thumbnail
    
    # Arabic translation
    title_ar = Column(Text, nullable=True)
    summary_ar = Column(Text, nullable=True)
    arabic_text = Column(Text, nullable=True)  # Combined Arabic text for analysis
    
    # Keywords
    keyword = Column(String(200), nullable=True)  # OLD - deprecated but kept for compatibility
    keyword_original = Column(String(200), nullable=True)  # NEW - Arabic keyword that matched
    keywords_translations = Column(Text, nullable=True)  # JSON of all translations
    
    # Sentiment
    sentiment = Column(String(50), nullable=True)  # OLD - deprecated but kept for compatibility
    sentiment_label = Column(String(50), nullable=True)  # NEW - إيجابي / سلبي / محايد
    sentiment_score = Column(String(20), nullable=True)  # Optional confidence score
    
    # Language (old column for compatibility)
    language = Column(String(10), nullable=True)  # OLD - deprecated, use original_language
    
    # Timestamps
    published_at = Column(DateTime, nullable=True)  # Article publish time
    fetched_at = Column(DateTime, default=datetime.utcnow)  # When we fetched it
    created_at = Column(DateTime, default=datetime.utcnow)  # DB insert time
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)

class AuditLog(Base):
    __tablename__ = 'audit_log'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    admin_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    action = Column(String(100), nullable=False)
    meta_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ExportRecord(Base):
    __tablename__ = 'exports'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    filters_json = Column(Text, nullable=True)
    article_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

# Database setup
DATABASE_URL = "sqlite:///ain_news.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Get database session - use as context manager or close manually"""
    return SessionLocal()
