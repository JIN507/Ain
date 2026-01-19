"""Database models for Ain News Monitor

This file defines all SQLAlchemy ORM models that map to the actual database schema.
All tables in the DB must have a corresponding model here to prevent schema mismatch.

IMPORTANT: Do not modify table structures here without a migration plan.
"""
import os
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
    url = Column(String(2000), nullable=False, unique=True)
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
    
    # Translations in different languages (legacy columns - kept for compatibility)
    text_en = Column(String(200), nullable=True)  # English
    text_fr = Column(String(200), nullable=True)  # French
    text_tr = Column(String(200), nullable=True)  # Turkish
    text_ur = Column(String(200), nullable=True)  # Urdu
    text_zh = Column(String(200), nullable=True)  # Chinese
    text_ru = Column(String(200), nullable=True)  # Russian
    text_es = Column(String(200), nullable=True)  # Spanish
    
    # NEW: All translations as JSON (supports 33+ languages)
    translations_json = Column(Text, nullable=True)  # {"en": "...", "fr": "...", ...}
    translations_updated_at = Column(DateTime, nullable=True)  # When translations were last updated
    
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Article(Base):
    __tablename__ = 'articles'
    
    id = Column(Integer, primary_key=True)
    
    # Source info
    country = Column(String(100), nullable=False)
    source_name = Column(String(200), nullable=False)
    url = Column(String(2000), nullable=False, unique=True)
    
    # Original content
    title_original = Column(Text, nullable=False)
    summary_original = Column(Text, nullable=True)
    original_language = Column(String(10), nullable=True)  # Detected language (en, ar, fr, etc.)
    image_url = Column(String(2000), nullable=True)  # Article image/thumbnail
    
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
    filename = Column(String(255), nullable=True)  # Original filename
    stored_filename = Column(String(255), nullable=True)  # UUID filename on disk
    file_size = Column(Integer, nullable=True)  # File size in bytes
    source_type = Column(String(50), nullable=True)  # dashboard, top_headlines, etc.
    created_at = Column(DateTime, default=datetime.utcnow)


class UserFile(Base):
    """User uploaded files - for 'My Files' feature"""
    __tablename__ = 'user_files'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    filename = Column(String(255), nullable=False)  # Original filename
    stored_filename = Column(String(255), nullable=False)  # UUID-based stored name
    file_type = Column(String(50), nullable=True)  # pdf, xlsx, csv, etc.
    file_size = Column(Integer, default=0)  # Size in bytes
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SearchHistory(Base):
    """Per-user search history tracking"""
    __tablename__ = 'search_history'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    search_type = Column(String(50), nullable=False)  # 'keyword', 'direct', 'headlines'
    query = Column(Text, nullable=True)  # Search query or keyword
    filters_json = Column(Text, nullable=True)  # JSON of applied filters
    results_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


# ==============================================================================
# Junction Tables (for per-user preferences on shared catalog data)
# These tables exist in DB but are currently NOT actively used by app logic.
# Kept here for schema completeness. Future use: per-user source/country prefs.
# ==============================================================================

class UserArticle(Base):
    """Junction table linking users to articles with per-user metadata.
    
    NOTE: Currently NOT used by application code. articles.user_id is the
    active mechanism for article ownership. This table exists in DB with
    historical data but the app reads/writes articles.user_id directly.
    
    Future use: could support shared articles with per-user notes/stars.
    """
    __tablename__ = 'user_articles'
    __table_args__ = (
        UniqueConstraint('user_id', 'article_id', name='uq_user_article'),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    article_id = Column(Integer, ForeignKey('articles.id'), nullable=False, index=True)
    keyword_id = Column(Integer, ForeignKey('keywords.id'), nullable=True)
    keyword_original = Column(String(200), nullable=True)
    keywords_translations = Column(Text, nullable=True)
    sentiment_label = Column(String(50), nullable=True)
    sentiment_score = Column(String(20), nullable=True)
    is_read = Column(Boolean, default=False)
    is_starred = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserCountry(Base):
    """Junction table for per-user country preferences.
    
    NOTE: Currently NOT used by application code. Countries are shared
    catalog data. This table exists in DB with historical data.
    
    Future use: per-user enabled/disabled countries for filtering.
    """
    __tablename__ = 'user_countries'
    __table_args__ = (
        UniqueConstraint('user_id', 'country_id', name='uq_user_country'),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    country_id = Column(Integer, ForeignKey('countries.id'), nullable=False, index=True)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserSource(Base):
    """Junction table for per-user source preferences.
    
    NOTE: Currently NOT used by application code. Sources are shared
    catalog data. This table exists in DB with historical data.
    
    Future use: per-user enabled/disabled sources for monitoring.
    """
    __tablename__ = 'user_sources'
    __table_args__ = (
        UniqueConstraint('user_id', 'source_id', name='uq_user_source'),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    source_id = Column(Integer, ForeignKey('sources.id'), nullable=False, index=True)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ==============================================================================
# Monitor Jobs - Background Job Tracking
# ==============================================================================

class MonitorJob(Base):
    """
    Tracks monitoring job execution for async/background processing.
    
    Status flow: QUEUED → RUNNING → SUCCEEDED/FAILED/CANCELLED
    
    This enables:
    - Non-blocking API responses
    - Per-user job limits (one active job at a time)
    - Job status tracking and progress
    - Persistence across server restarts
    """
    __tablename__ = 'monitor_jobs'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Job status
    status = Column(String(20), nullable=False, default='QUEUED')  # QUEUED, RUNNING, SUCCEEDED, FAILED, CANCELLED
    
    # Progress tracking
    progress = Column(Integer, default=0)  # 0-100
    progress_message = Column(String(255), nullable=True)
    
    # Timing
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    
    # Results
    total_fetched = Column(Integer, default=0)
    total_matched = Column(Integer, default=0)
    total_saved = Column(Integer, default=0)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    
    # Metadata (JSON)
    meta_json = Column(Text, nullable=True)  # Additional stats/info
    
    def to_dict(self):
        """Convert to dictionary for JSON response"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'status': self.status,
            'progress': self.progress,
            'progress_message': self.progress_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
            'total_fetched': self.total_fetched,
            'total_matched': self.total_matched,
            'total_saved': self.total_saved,
            'error_message': self.error_message,
        }


# ==============================================================================
# Database Connection Setup
# ==============================================================================

# Priority: ENV variable > fallback to SQLite for local dev
# For production, set DATABASE_URL env var to PostgreSQL connection string
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///ain_news.db')

# Fix Render's postgres:// to postgresql:// (SQLAlchemy requires postgresql://)
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

# Log which database we're using
_db_type = 'PostgreSQL' if 'postgresql' in DATABASE_URL else 'SQLite'
print(f"[DB] Using {_db_type} database")

# Database-specific settings
_connect_args = {}
if DATABASE_URL.startswith('sqlite'):
    _connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=_connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables.
    
    WARNING: This will create tables that don't exist but won't modify
    existing tables. For schema changes, use migration scripts.
    """
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session.
    
    Usage:
        db = get_db()
        try:
            # ... use db ...
        finally:
            db.close()
    """
    return SessionLocal()
